"""
High-level helpers around pyoverleaf.ProjectIO.
These functions do NOT print anything and do NOT exit the program;
they raise Python exceptions instead.  This makes them reusable.
"""

from __future__ import annotations

import pyoverleaf
from pathlib import PurePosixPath


class OverleafClient:
    def __init__(self, project_name: str):
        self.api = pyoverleaf.Api()
        self.api.login_from_browser()

        # Resolve project-id once
        projects = {p.name: p.id for p in self.api.get_projects()}
        try:
            self.project_id = projects[project_name]
        except KeyError:  # pragma: no cover
            raise ValueError(f"Project '{project_name}' not found")

        # Lazily create IO wrapper
        self.io = pyoverleaf.ProjectIO(self.api, self.project_id)

    def refresh(self):
        # Re-create the ProjectIO object to refresh file tree
        self.io = pyoverleaf.ProjectIO(self.api, self.project_id)

    # ---------- file-system-like helpers ----------

    def listdir(self, path: str | PurePosixPath = "") -> list[pyoverleaf.ProjectEntity]:
        """Return list of entities in `path` (ProjectFile or ProjectFolder)."""
        return list(self.io.listdir(str(path)))

    def exists(self, path: str | PurePosixPath) -> bool:
        return self.io.exists(str(path))

    def mkdir(
        self, path: str | PurePosixPath, parents: bool = True, exist_ok: bool = True
    ) -> None:
        self.io.mkdir(str(path), parents=parents, exist_ok=exist_ok)

    def read(self, path: str | PurePosixPath, encoding: str = "utf-8") -> str:
        with self.io.open(str(path), "rb") as f:  # read raw bytes
            return f.read().decode(encoding)  # decode once, here

    def read_bytes(self, path: str | PurePosixPath) -> bytes:
        with self.io.open(str(path), "rb") as f:
            return f.read()

    def write(
        self, path: str | PurePosixPath, data: str | bytes, encoding: str = "utf-8"
    ) -> None:
        if isinstance(data, str):
            data = data.encode(encoding)  # encode ONCE
        with self.io.open(str(path), "wb") as f:  # always binary mode
            f.write(data)

    def create_file(self, path: str | PurePosixPath, content: str | bytes = "") -> None:
        self.write(path, content)  # delegates to safe write

    def remove(self, path: str | PurePosixPath) -> None:
        """Removes a file or empty directory from the project."""
        self.io.remove(str(path))

    # ---------- NEW: project listing ----------

    @staticmethod
    def list_projects() -> list[dict]:
        """
        Returns a list of dicts: [{"name": <project_name>, "id": <project_id>}, ...]
        """
        api = pyoverleaf.Api()
        api.login_from_browser()
        return [{"name": p.name, "id": p.id} for p in api.get_projects()]
