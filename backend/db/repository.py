"""
Repository - storage-backend-agnostic document store for platform data.
Location: backend/db/repository.py

A lightweight, async, collection-oriented document store. Each "collection"
(e.g. ``organizations``, ``users``, ``assessments``) holds JSON documents keyed
by an ``id`` field. This is intentionally minimal: it gives the platform
services CRUD + filtered queries without coupling them to a specific database.

Backends:
  - JsonRepository: one JSON file per collection under ``data/platform/``.
    Thread/async safe via an asyncio lock per process. Good for dev + the
    free-tier single-instance EC2 deployment.
  - (future) SqlRepository: same interface backed by SQLAlchemy/Postgres.

The public surface is deliberately small so swapping backends is trivial:
    insert, get, update, delete, find, count

Documents are plain dicts. Services own their schema (via Pydantic models)
and (de)serialize at their boundary.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PLATFORM_DIR = Path("data/platform")


class Repository:
    """Abstract async document repository. See module docstring."""

    async def insert(self, collection: str, document: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    async def update(
        self, collection: str, doc_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    async def delete(self, collection: str, doc_id: str) -> bool:
        raise NotImplementedError

    async def find(
        self,
        collection: str,
        where: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        descending: bool = True,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    async def count(
        self, collection: str, where: Optional[Dict[str, Any]] = None
    ) -> int:
        results = await self.find(collection, where=where)
        return len(results)


class JsonRepository(Repository):
    """File-backed repository: one JSON file per collection.

    Each file holds ``{"<id>": {document}, ...}``. An in-memory cache plus a
    per-collection asyncio lock keeps reads fast and writes consistent within
    a single process.
    """

    def __init__(self, base_dir: Path = PLATFORM_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def _path(self, collection: str) -> Path:
        # Guard against path traversal in collection names.
        safe = "".join(c for c in collection if c.isalnum() or c in ("_", "-"))
        return self.base_dir / f"{safe}.json"

    def _lock(self, collection: str) -> asyncio.Lock:
        if collection not in self._locks:
            self._locks[collection] = asyncio.Lock()
        return self._locks[collection]

    def _load(self, collection: str) -> Dict[str, Dict[str, Any]]:
        if collection in self._cache:
            return self._cache[collection]
        path = self._path(collection)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:  # noqa: BLE001
                logger.error("Failed to load collection %s: %s", collection, e)
                data = {}
        else:
            data = {}
        self._cache[collection] = data
        return data

    def _flush(self, collection: str) -> None:
        path = self._path(collection)
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._cache[collection], f, indent=2, default=str)
        os.replace(tmp, path)  # atomic on POSIX & Windows

    @staticmethod
    def _matches(doc: Dict[str, Any], where: Dict[str, Any]) -> bool:
        for key, expected in where.items():
            actual = doc.get(key)
            if isinstance(expected, (list, tuple, set)):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    async def insert(self, collection: str, document: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in document:
            raise ValueError("Document must contain an 'id' field")
        async with self._lock(collection):
            data = self._load(collection)
            doc = dict(document)
            doc.setdefault("created_at", datetime.utcnow().isoformat())
            doc["updated_at"] = datetime.utcnow().isoformat()
            data[doc["id"]] = doc
            self._flush(collection)
            return doc

    async def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock(collection):
            return self._load(collection).get(doc_id)

    async def update(
        self, collection: str, doc_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        async with self._lock(collection):
            data = self._load(collection)
            existing = data.get(doc_id)
            if existing is None:
                return None
            existing.update(updates)
            existing["updated_at"] = datetime.utcnow().isoformat()
            self._flush(collection)
            return existing

    async def delete(self, collection: str, doc_id: str) -> bool:
        async with self._lock(collection):
            data = self._load(collection)
            if doc_id in data:
                del data[doc_id]
                self._flush(collection)
                return True
            return False

    async def find(
        self,
        collection: str,
        where: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        descending: bool = True,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        async with self._lock(collection):
            data = self._load(collection)
            results = [
                dict(doc)
                for doc in data.values()
                if not where or self._matches(doc, where)
            ]
        if order_by:
            results.sort(
                key=lambda d: (d.get(order_by) is None, d.get(order_by)),
                reverse=descending,
            )
        if limit is not None:
            results = results[:limit]
        return results


_repository: Optional[Repository] = None


def get_repository() -> Repository:
    """Return the process-wide repository instance (backend per env var)."""
    global _repository
    if _repository is not None:
        return _repository

    backend = os.environ.get("STORAGE_BACKEND", "json").lower()
    if backend == "sql":
        try:
            from db.sql_repository import SqlRepository  # noqa: WPS433

            _repository = SqlRepository()
            logger.info("Using SQL repository backend")
            return _repository
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "SQL backend requested but unavailable (%s); falling back to JSON",
                e,
            )

    _repository = JsonRepository()
    logger.info("Using JSON repository backend at %s", PLATFORM_DIR)
    return _repository
