"""Versioned template loading and selection."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .errors import ServiceError
from .schemas import PageSize, Region


@dataclass(frozen=True)
class DocumentTemplate:
    id: str
    version: str
    kode_faskes: str
    canonical_size: PageSize
    regions: dict[str, Region]
    row_y: tuple[int, ...]
    row_height: int
    fingerprint_masks: tuple[str, ...]

    def rows(self) -> list[Region]:
        return [(85, y, 1070, self.row_height) for y in self.row_y]

    def signatures(self) -> list[Region]:
        return [(900, y + 6, 250, self.row_height - 12) for y in self.row_y]

    def dates(self) -> list[Region]:
        return [(125, y + 6, 125, self.row_height - 12) for y in self.row_y]

    def services(self) -> list[Region]:
        return [(250, y + 6, 400, self.row_height - 12) for y in self.row_y]

    def total_digit(self) -> Region:
        _, y, _, height = self.regions["total"]
        return (330, y + 5, 65, height - 10)


def _template_directory() -> Path:
    return Path(__file__).resolve().parents[2] / "templates"


@lru_cache(maxsize=1)
def load_templates() -> dict[str, DocumentTemplate]:
    templates: dict[str, DocumentTemplate] = {}
    for path in sorted(_template_directory().glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        template = DocumentTemplate(
            id=raw["id"],
            version=raw["version"],
            kode_faskes=raw["kode_faskes"],
            canonical_size=tuple(raw["canonical_size"]),
            regions={name: tuple(region) for name, region in raw["regions"].items()},
            row_y=tuple(raw["row_y"]),
            row_height=raw["row_height"],
            fingerprint_masks=tuple(raw["fingerprint_masks"]),
        )
        templates[template.id] = template
    if not templates:
        raise RuntimeError("Tidak ada template dokumen yang tersedia.")
    return templates


def resolve_template(template_id: str, kode_faskes: str | None) -> DocumentTemplate:
    templates = load_templates()
    if template_id:
        template = templates.get(template_id)
        if template is None:
            raise ServiceError(422, "template_tidak_didukung", "Template dokumen tidak didukung.")
        return template
    if kode_faskes:
        for template in templates.values():
            if template.kode_faskes == kode_faskes:
                return template
    # The three MVP layouts share the same geometry. This deterministic default
    # is used only when the backend has no template context yet.
    return templates["melati-v1"]
