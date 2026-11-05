"""The ONLY module allowed to touch the filesystem (architecture §5.1 control 1).

Every path is resolved (symlinks followed) and must stay inside DATA_ROOT.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO, Iterator


class StorageGuardError(PermissionError):
    """Raised when a path would escape DATA_ROOT."""


class Storage:
    def __init__(self, data_root: Path):
        self._root = Path(data_root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def safe_path(self, relative: str | os.PathLike[str]) -> Path:
        rel = Path(relative)
        if rel.is_absolute():
            raise StorageGuardError(f"absolute paths are not allowed: {rel}")
        candidate = (self._root / rel).resolve()  # follows symlinks
        if candidate != self._root and self._root not in candidate.parents:
            raise StorageGuardError(f"path escapes DATA_ROOT: {relative}")
        return candidate

    def read_bytes(self, relative: str | os.PathLike[str]) -> bytes:
        return self.safe_path(relative).read_bytes()

    def read_text(self, relative: str | os.PathLike[str], encoding: str = "utf-8") -> str:
        return self.safe_path(relative).read_text(encoding=encoding)

    def write_bytes(self, relative: str | os.PathLike[str], data: bytes) -> Path:
        path = self.safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def open_binary(self, relative: str | os.PathLike[str], mode: str = "rb") -> BinaryIO:
        if "b" not in mode:
            raise ValueError("open_binary requires a binary mode")
        path = self.safe_path(relative)
        if any(m in mode for m in "wa+"):
            path.parent.mkdir(parents=True, exist_ok=True)
        return open(path, mode)  # noqa: SIM115 - the one sanctioned open()

    def exists(self, relative: str | os.PathLike[str]) -> bool:
        return self.safe_path(relative).exists()

    def iter_files(self, relative_dir: str | os.PathLike[str]) -> Iterator[str]:
        base = self.safe_path(relative_dir)
        if not base.exists():
            return
        for p in sorted(base.rglob("*")):
            if p.is_file():
                resolved = p.resolve()
                if self._root not in resolved.parents:
                    raise StorageGuardError(f"file escapes DATA_ROOT via symlink: {p}")
                yield str(resolved.relative_to(self._root))
