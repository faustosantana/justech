"""Explorer navigation state — browser-like stack + breadcrumbs + compares."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ViewKind = Literal[
    "root",
    "analizar",
    "tabla1",
    "tabla2",
    "companeros",
    "vecinos",
    "historico",
    "coincidencias",
    "estadisticas",
    "comparar",
    "relacion",
]


class ExplorerCrumb(BaseModel):
    model_config = {"extra": "ignore"}

    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    label: str
    number: str | None = None
    view: ViewKind | str = "root"
    at: datetime = Field(default_factory=_utcnow)


class ExplorerNavState(BaseModel):
    """Client/server shared explorer memory (not full chat history)."""

    model_config = {"extra": "ignore"}

    stack: list[ExplorerCrumb] = Field(default_factory=list)
    index: int = -1
    compare: list[str] = Field(default_factory=list)
    favorites: list[str] = Field(default_factory=list)
    recent_numbers: list[str] = Field(default_factory=list)
    origin: str | None = None  # chat | click | compare | breadcrumb | back | forward
    started_at: datetime | None = None
    view: ViewKind | str = "root"

    def to_store(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_store(cls, data: dict[str, Any] | None) -> "ExplorerNavState":
        if not data or not isinstance(data, dict):
            return cls()
        try:
            return cls.model_validate(data)
        except Exception:  # noqa: BLE001
            return cls()

    @property
    def current(self) -> ExplorerCrumb | None:
        if self.index < 0 or self.index >= len(self.stack):
            return None
        return self.stack[self.index]

    @property
    def breadcrumbs(self) -> list[dict[str, Any]]:
        # Show path from start to current index (browser trail)
        if self.index < 0:
            return [{"id": "home", "label": "Inicio", "view": "root", "number": None}]
        crumbs = [
            {"id": "home", "label": "Inicio", "view": "root", "number": None},
        ]
        for c in self.stack[: self.index + 1]:
            crumbs.append(
                {
                    "id": c.id,
                    "label": c.label,
                    "view": c.view,
                    "number": c.number,
                }
            )
        return crumbs

    def _touch_recent(self, number: str | None) -> None:
        if not number:
            return
        n = str(int(number)) if str(number).isdigit() else str(number)
        self.recent_numbers = [n] + [x for x in self.recent_numbers if x != n]
        self.recent_numbers = self.recent_numbers[:12]

    def push(
        self,
        *,
        number: str | None,
        view: ViewKind | str = "root",
        label: str | None = None,
        origin: str = "click",
    ) -> ExplorerCrumb:
        n = None
        if number is not None and str(number).strip():
            raw = str(number).strip()
            n = str(int(raw)) if raw.isdigit() else raw
        view_s = str(view or "root")
        if label:
            lab = label
        elif view_s in {"tabla1", "Tabla 1"}:
            lab = "Tabla 1"
        elif view_s in {"tabla2", "Tabla 2"}:
            lab = "Tabla 2"
        elif view_s == "companeros":
            lab = "Compañeros"
        elif view_s == "vecinos":
            lab = "Vecinos"
        elif view_s == "historico":
            lab = "Histórico"
        elif view_s == "coincidencias":
            lab = "Coincidencias"
        elif view_s == "estadisticas":
            lab = "Estadísticas"
        elif view_s == "comparar":
            lab = "Comparar"
        elif n:
            lab = n
        else:
            lab = "Inicio"
        # Truncate forward history like a browser
        if self.index >= 0 and self.index < len(self.stack) - 1:
            self.stack = self.stack[: self.index + 1]
        crumb = ExplorerCrumb(label=lab, number=n, view=view_s)
        self.stack.append(crumb)
        self.index = len(self.stack) - 1
        self.view = view_s
        self.origin = origin
        if self.started_at is None:
            self.started_at = _utcnow()
        self._touch_recent(n)
        return crumb

    def back(self) -> ExplorerCrumb | None:
        if self.index <= 0:
            return self.current
        self.index -= 1
        self.origin = "back"
        cur = self.current
        if cur:
            self.view = cur.view
            self._touch_recent(cur.number)
        return cur

    def forward(self) -> ExplorerCrumb | None:
        if self.index < 0 or self.index >= len(self.stack) - 1:
            return self.current
        self.index += 1
        self.origin = "forward"
        cur = self.current
        if cur:
            self.view = cur.view
            self._touch_recent(cur.number)
        return cur

    def jump_to(self, crumb_id: str) -> ExplorerCrumb | None:
        if crumb_id == "home":
            self.index = -1
            self.view = "root"
            self.origin = "breadcrumb"
            return None
        for i, c in enumerate(self.stack):
            if c.id == crumb_id:
                self.index = i
                self.view = c.view
                self.origin = "breadcrumb"
                self._touch_recent(c.number)
                return c
        return self.current

    def toggle_compare(self, number: str) -> list[str]:
        n = str(int(number)) if str(number).isdigit() else str(number)
        if n in self.compare:
            self.compare = [x for x in self.compare if x != n]
        else:
            self.compare = (self.compare + [n])[:6]
        self._touch_recent(n)
        return list(self.compare)

    def toggle_favorite(self, number: str) -> list[str]:
        n = str(int(number)) if str(number).isdigit() else str(number)
        if n in self.favorites:
            self.favorites = [x for x in self.favorites if x != n]
        else:
            self.favorites = ([n] + self.favorites)[:20]
        return list(self.favorites)

    def can_back(self) -> bool:
        return self.index > 0 or (self.index == 0 and len(self.stack) > 0)

    def can_forward(self) -> bool:
        return 0 <= self.index < len(self.stack) - 1

    def public(self) -> dict[str, Any]:
        cur = self.current
        return {
            "stack": [c.model_dump(mode="json") for c in self.stack],
            "index": self.index,
            "current": cur.model_dump(mode="json") if cur else None,
            "breadcrumbs": self.breadcrumbs,
            "compare": list(self.compare),
            "favorites": list(self.favorites),
            "recent_numbers": list(self.recent_numbers),
            "origin": self.origin,
            "view": self.view,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "can_back": self.index > 0,
            "can_forward": self.can_forward(),
        }
