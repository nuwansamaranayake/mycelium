"""Keyless connector 1: a filesystem folder of text files.

Reads every .txt / .md file in a folder (non-recursive, sorted for determinism). A
manifest.json beside the files may pin per-file title, timestamp, and allowed_principals;
without a manifest entry the file falls back to its stem as title, its mtime (UTC) as the
document timestamp, and a private ACL (empty — absence never grants access). The manifest
is the deterministic path; mtime is the live-ingest convenience. No LLM anywhere: ingest is
a deterministic product feature, not a fallback (Standard 3).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class FolderDocument(BaseModel):
    external_id: str
    title: str
    text: str
    doc_timestamp: datetime
    allowed_principals: list[str] = Field(default_factory=list)


def ingest_folder(path: str) -> list[FolderDocument]:
    folder = Path(path)
    if not folder.is_dir():
        raise FileNotFoundError(f"folder connector: {path!r} is not a directory")
    manifest: dict = {}
    manifest_path = folder / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    docs: list[FolderDocument] = []
    for file in sorted(folder.iterdir()):
        if file.suffix.lower() not in (".txt", ".md") or not file.is_file():
            continue
        meta = manifest.get(file.name, {})
        ts = meta.get("timestamp")
        docs.append(FolderDocument(
            external_id=file.name,
            title=meta.get("title", file.stem),
            text=file.read_text(encoding="utf-8"),
            doc_timestamp=(datetime.fromisoformat(ts) if ts else
                           datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)),
            allowed_principals=list(meta.get("allowed_principals", [])),
        ))
    if not docs:
        raise FileNotFoundError(
            f"folder connector: no .txt/.md files in {path!r}; refusing to ingest nothing")
    return docs
