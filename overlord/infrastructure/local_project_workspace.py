from __future__ import annotations

import re
import shutil
from pathlib import Path


class LocalProjectWorkspace:
    def __init__(self, root: Path):
        self.root = root

    def _project_root(self, project_id: int) -> Path:
        if project_id <= 0:
            raise ValueError("Project id must be positive.")
        return self.root / str(project_id)

    def _resolve(self, project_id: int, relative_path: str) -> Path:
        project_root = self._project_root(project_id).resolve()
        target = (project_root / relative_path).resolve()
        if target != project_root and project_root not in target.parents:
            raise ValueError("Project workspace path escapes its Project directory.")
        return target

    def write_note(self, project_id: int, title: str, content: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "note"
        relative = f"notes/{slug}.md"
        suffix = 2
        while self._resolve(project_id, relative).exists():
            relative = f"notes/{slug}-{suffix}.md"
            suffix += 1
        target = self._resolve(project_id, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return relative

    def read_text(self, project_id: int, relative_path: str) -> str:
        target = self._resolve(project_id, relative_path)
        return target.read_text(encoding="utf-8") if target.exists() else ""

    def import_file(self, project_id: int, source: Path) -> tuple[str, int]:
        resolved_source = source.resolve(strict=True)
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", resolved_source.name).strip("-") or "file"
        relative = f"files/{safe_name}"
        suffix = 2
        while self._resolve(project_id, relative).exists():
            stem = Path(safe_name).stem
            extension = Path(safe_name).suffix
            relative = f"files/{stem}-{suffix}{extension}"
            suffix += 1
        target = self._resolve(project_id, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolved_source, target)
        return relative, target.stat().st_size

    def remove(self, project_id: int, relative_path: str) -> None:
        self._resolve(project_id, relative_path).unlink(missing_ok=True)
