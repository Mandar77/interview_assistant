"""
Culture Service API Routes - org culture crawl + grounded retrieval (Phase 12).
Location: backend/services/culture_service/routes.py
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.platform_schemas import PublicUser
from services.auth_service.dependencies import get_employer_user
from services.culture_service.crawler import CultureStore, crawl_culture

logger = logging.getLogger(__name__)

router = APIRouter()


class CrawlRequest(BaseModel):
    root_url: str
    max_pages: int = 6


class QueryRequest(BaseModel):
    query: str
    k: int = 4


@router.post("/crawl")
async def crawl(req: CrawlRequest, user: PublicUser = Depends(get_employer_user)):
    """Crawl the org's public culture pages and build a per-org vector store."""
    chunks, sources = crawl_culture(req.root_url, max_pages=req.max_pages)
    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No content extracted (page blocked, empty, or robots-disallowed)",
        )
    store = CultureStore(user.org_id)
    result = store.build(chunks)
    return {
        "org_id": user.org_id,
        "sources_crawled": sources,
        "chunks_indexed": result["chunks"],
        "embedded": result["embedded"],
    }


@router.get("/summary")
async def summary(user: PublicUser = Depends(get_employer_user)):
    """Summary of what's indexed for this org."""
    return CultureStore(user.org_id).summary()


@router.post("/query")
async def query(req: QueryRequest, user: PublicUser = Depends(get_employer_user)):
    """Retrieve the most relevant culture chunks for a query (debug/inspection)."""
    chunks = CultureStore(user.org_id).query(req.query, k=req.k)
    return {"results": chunks, "count": len(chunks)}


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "culture"}
