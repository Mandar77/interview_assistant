"""
Culture crawler + vector store - scrape public culture pages and ground
question generation in company values (Phase 12).
Location: backend/services/culture_service/crawler.py

Scrapes ONLY public pages (about/values/careers/CEO letters/CSR/blog),
respecting robots.txt. Extracted text is chunked, embedded via Ollama
(nomic-embed-text), and indexed in a per-org FAISS store on disk. Retrieval
feeds the existing question generator and (optionally) value-alignment
relevance scoring.

Degrades gracefully: if embeddings (Ollama) are unavailable, it falls back to
keyword retrieval so the crawl + grounding still works offline.
"""

from __future__ import annotations

import logging
import re
import urllib.robotparser
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

CULTURE_DIR = Path("data/platform/culture")
CULTURE_DIR.mkdir(parents=True, exist_ok=True)

# Paths we consider "culture" pages worth crawling from a root domain.
CULTURE_HINTS = (
    "about",
    "values",
    "culture",
    "career",
    "jobs",
    "mission",
    "csr",
    "responsibility",
    "blog",
    "team",
    "leadership",
    "ceo",
)

CHUNK_SIZE = 800  # characters per chunk
USER_AGENT = "InterviewAssistantCultureBot/1.0 (+respect-robots)"


def _allowed_by_robots(url: str) -> bool:
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:  # noqa: BLE001
        # If robots.txt can't be read, be conservative but allow the root page.
        return True


def _extract_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def _discover_culture_links(base_url: str, html: str, limit: int = 8) -> List[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    base_netloc = urlparse(base_url).netloc
    found: List[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        parsed = urlparse(href)
        if parsed.netloc != base_netloc:
            continue
        path = parsed.path.lower()
        if any(hint in path for hint in CULTURE_HINTS):
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean not in found:
                found.append(clean)
        if len(found) >= limit:
            break
    return found


def _chunk(text: str, size: int = CHUNK_SIZE) -> List[str]:
    words = text.split()
    chunks, current, length = [], [], 0
    for word in words:
        current.append(word)
        length += len(word) + 1
        if length >= size:
            chunks.append(" ".join(current))
            current, length = [], 0
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if len(c) > 40]


def crawl_culture(root_url: str, max_pages: int = 6) -> Tuple[List[str], List[str]]:
    """Crawl a company's public culture pages.

    Returns (chunks, source_urls). Network/parse failures are tolerated;
    whatever was fetched is returned.
    """
    visited: List[str] = []
    chunks: List[str] = []
    headers = {"User-Agent": USER_AGENT}

    try:
        with httpx.Client(timeout=15, headers=headers, follow_redirects=True) as client:
            if not _allowed_by_robots(root_url):
                logger.warning("robots.txt disallows %s", root_url)
                return [], []
            resp = client.get(root_url)
            resp.raise_for_status()
            root_html = resp.text
            visited.append(root_url)
            chunks.extend(_chunk(_extract_text(root_html)))

            for link in _discover_culture_links(root_url, root_html):
                if len(visited) >= max_pages:
                    break
                if link in visited or not _allowed_by_robots(link):
                    continue
                try:
                    r = client.get(link)
                    r.raise_for_status()
                    visited.append(link)
                    chunks.extend(_chunk(_extract_text(r.text)))
                except Exception as e:  # noqa: BLE001
                    logger.info("Skip %s: %s", link, e)
    except Exception as e:  # noqa: BLE001
        logger.error("Crawl failed for %s: %s", root_url, e)

    return chunks, visited


# =============================================================================
# Vector store (FAISS per org, with keyword fallback)
# =============================================================================

def _embed(texts: List[str]) -> Optional["object"]:
    """Embed texts via Ollama. Returns a numpy array or None if unavailable."""
    try:
        import numpy as np

        from utils.llm_client import get_llm_client

        client = get_llm_client()
        vectors = [client.get_embeddings(t) for t in texts]
        return np.array(vectors, dtype="float32")
    except Exception as e:  # noqa: BLE001
        logger.info("Embeddings unavailable (%s); using keyword fallback", e)
        return None


class CultureStore:
    """Per-org culture knowledge: FAISS index if embeddings available, else text."""

    def __init__(self, org_id: str):
        self.org_id = org_id
        self.dir = CULTURE_DIR / org_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.chunks_path = self.dir / "chunks.txt"
        self.index_path = self.dir / "index.faiss"

    def build(self, chunks: List[str]) -> dict:
        self.chunks_path.write_text("\n<<<CHUNK>>>\n".join(chunks), encoding="utf-8")
        vectors = _embed(chunks)
        embedded = False
        if vectors is not None and len(chunks) > 0:
            try:
                import faiss

                index = faiss.IndexFlatL2(vectors.shape[1])
                index.add(vectors)
                faiss.write_index(index, str(self.index_path))
                embedded = True
            except Exception as e:  # noqa: BLE001
                logger.warning("FAISS index build failed: %s", e)
        return {"chunks": len(chunks), "embedded": embedded}

    def _load_chunks(self) -> List[str]:
        if not self.chunks_path.exists():
            return []
        return self.chunks_path.read_text(encoding="utf-8").split("\n<<<CHUNK>>>\n")

    def query(self, text: str, k: int = 4) -> List[str]:
        chunks = self._load_chunks()
        if not chunks:
            return []
        # Try FAISS semantic search first.
        if self.index_path.exists():
            vectors = _embed([text])
            if vectors is not None:
                try:
                    import faiss

                    index = faiss.read_index(str(self.index_path))
                    _, ids = index.search(vectors, min(k, len(chunks)))
                    return [chunks[i] for i in ids[0] if 0 <= i < len(chunks)]
                except Exception as e:  # noqa: BLE001
                    logger.info("FAISS query failed (%s); keyword fallback", e)
        # Keyword fallback: rank chunks by query-term overlap.
        terms = {w.lower() for w in re.findall(r"\w+", text) if len(w) > 3}
        scored = sorted(
            chunks,
            key=lambda c: sum(c.lower().count(t) for t in terms),
            reverse=True,
        )
        return scored[:k]

    def summary(self) -> dict:
        chunks = self._load_chunks()
        return {
            "org_id": self.org_id,
            "chunk_count": len(chunks),
            "embedded": self.index_path.exists(),
            "preview": chunks[0][:300] if chunks else "",
        }
