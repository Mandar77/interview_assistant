"""
Platform persistence layer.

Provides a storage-backend-agnostic repository abstraction used by all
Phase 9+ platform services (auth, assessments, proctoring, culture, etc.).

Two backends are supported, selected via the ``STORAGE_BACKEND`` env var:
  - ``json`` (default): file-backed collections under ``data/platform/`` —
    zero external dependencies, mirrors the original project's file storage.
  - ``sql``: Postgres/Supabase via SQLAlchemy async (prod). Falls back to
    JSON automatically if SQL deps/connection are unavailable.

Services depend only on :class:`Repository`; they never touch files or the DB
directly. This keeps the existing anonymous mock flow untouched while adding
multi-tenant persistence for the hiring platform.
"""

from db.repository import Repository, get_repository

__all__ = ["Repository", "get_repository"]
