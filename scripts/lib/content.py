from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "content"

MONTHS_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

TYPES_BY_DIR = {
    "experience": "job",
    "projects": "project",
    "education": "education",
    "awards": "award",
}

ALLOWED_KEYS = {
    "type",
    "title",
    "card_title",
    "summary",
    "role",
    "org",
    "start",
    "end",
    "link",
    "repo",
    "demo",
    "image",
    "tags",
    "cv",
    "portfolio",
    "draft",
    "cv_group",
    "cv_group_summary",
    "current",
}

DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2}))?$")
FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", re.S)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
SOFT_RE = re.compile(r"^-\s+\*\*(.+?):\*\*\s*(.+)$")


class ContentError(Exception):
    pass


@dataclass
class Entry:
    path: Path
    type: str
    data: dict
    body: str

    @property
    def slug(self) -> str:
        return self.path.stem

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    @property
    def start(self):
        return parse_date(self.data.get("start"))

    @property
    def end(self):
        return parse_date(self.data.get("end"))

    @property
    def sort_key(self):
        start = self.start
        return (start[0], start[1] or 0)

    def is_public(self) -> bool:
        return not self.data.get("draft", False) and self.data.get("portfolio", True)

    def in_cv(self) -> bool:
        return not self.data.get("draft", False) and self.data.get("cv", True)


@dataclass
class Content:
    profile: dict
    sections: dict
    soft_skills: list
    skills: list
    entries: list
    errors: list = field(default_factory=list)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_markdown(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = FM_RE.match(text)
    if not match:
        raise ContentError(f"{rel(path)}: falta el frontmatter (--- ... ---)")
    raw, body = match.groups()
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise ContentError(f"{rel(path)}: frontmatter YAML inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise ContentError(f"{rel(path)}: el frontmatter debe ser un objeto")
    return data, body.strip()


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str):
        raise ContentError(f"fecha inválida: {value!r}")
    match = DATE_RE.match(value.strip())
    if not match:
        raise ContentError(f"fecha inválida: {value!r} (usa YYYY o YYYY-MM)")
    year, month = match.groups()
    month = int(month) if month else None
    if month is not None and not 1 <= month <= 12:
        raise ContentError(f"mes inválido: {value!r}")
    return (int(year), month)


def date_key(value):
    parsed = parse_date(value)
    if parsed is None:
        return None
    return (parsed[0], parsed[1] or 0)


def format_cv_date(value) -> str:
    year, month = parse_date(value)
    if month is None:
        return str(year)
    return f"{year} {MONTHS_ES[month - 1].capitalize()}"


def format_portfolio_date(value) -> str:
    year, month = parse_date(value)
    if month is None:
        return str(year)
    return f"{MONTHS_ES[month - 1].capitalize()} {year}"


def cv_period(start, end, current: bool = False) -> str:
    if current:
        return f"{format_cv_date(start)} - Actual"
    if end and date_key(end) != date_key(start):
        return f"{format_cv_date(start)} - {format_cv_date(end)}"
    return format_cv_date(start)


def portfolio_period(start, end, current: bool = False) -> str:
    if current:
        return f"{format_portfolio_date(start)} - Actualidad"
    if end and date_key(end) != date_key(start):
        return f"{format_portfolio_date(start)} - {format_portfolio_date(end)}"
    return format_portfolio_date(start)


def split_sections(body: str) -> dict:
    sections = {}
    current = None
    buffer = []
    for line in body.splitlines():
        match = SECTION_RE.match(line)
        if match:
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = match.group(1)
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def parse_soft_skills(section: str) -> list:
    items = []
    for line in section.splitlines():
        match = SOFT_RE.match(line.strip())
        if match:
            items.append({"title": match.group(1).strip(), "text": match.group(2).strip()})
    return items


def normalize_skill_item(item, errors, where):
    if isinstance(item, str):
        return {"name": item.strip()}
    if isinstance(item, dict):
        name = item.get("name")
        if not name:
            errors.append(f"{where}: cada skill necesita un 'name'")
            return None
        unknown = set(item) - {"name", "icon", "skillicon"}
        if unknown:
            errors.append(f"{where}: claves no reconocidas en skill {name}: {sorted(unknown)}")
        icon = item.get("icon")
        if icon is not None and not isinstance(icon, str):
            errors.append(f"{where}: 'icon' de {name} debe ser texto")
        skillicon = item.get("skillicon")
        if skillicon is not None:
            if not isinstance(skillicon, str):
                errors.append(f"{where}: 'skillicon' de {name} debe ser texto")
            elif not (
                skillicon.startswith(("http://", "https://"))
                or skillicon.endswith(".svg")
                or re.fullmatch(r"[A-Za-z0-9._-]+", skillicon)
            ):
                errors.append(
                    f"{where}: 'skillicon' de {name} debe ser un slug de skillicons "
                    "o una URL http(s)"
                )
        return {
            "name": str(name).strip(),
            **({"icon": item["icon"]} if item.get("icon") else {}),
            **({"skillicon": item["skillicon"]} if item.get("skillicon") else {}),
        }
    errors.append(f"{where}: skill con formato inválido: {item!r}")
    return None


def load_skills(errors: list) -> list:
    path = CONTENT_DIR / "skills.yml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"{rel(path)}: {exc}")
        return []

    groups = data.get("groups")
    if not isinstance(groups, list) or not groups:
        errors.append(f"{rel(path)}: falta la lista 'groups'")
        return []

    seen_ids = set()
    seen_names = set()
    result = []
    for index, group in enumerate(groups):
        where = f"{rel(path)}: groups[{index}]"
        if not isinstance(group, dict):
            errors.append(f"{where}: debe ser un objeto")
            continue
        group_id = group.get("id")
        label = group.get("label")
        items = group.get("items")
        if not group_id:
            errors.append(f"{where}: falta 'id'")
        elif group_id in seen_ids:
            errors.append(f"{where}: id duplicado {group_id!r}")
        else:
            seen_ids.add(group_id)
        if not label:
            errors.append(f"{where}: falta 'label'")
        if not isinstance(items, list) or not items:
            errors.append(f"{where}: falta la lista 'items'")
            continue
        normalized = []
        for item in items:
            normalized_item = normalize_skill_item(item, errors, where)
            if not normalized_item:
                continue
            name = normalized_item["name"]
            if name in seen_names:
                errors.append(f"{where}: skill duplicada {name!r}")
                continue
            seen_names.add(name)
            normalized.append(normalized_item)
        result.append({"id": group_id, "label": label, "items": normalized})
    return result


def load_profile(errors: list):
    path = CONTENT_DIR / "profile.md"
    try:
        data, body = read_markdown(path)
    except ContentError as exc:
        errors.append(str(exc))
        return {}, {}, []

    for key in ("name", "display_name", "headline", "email", "links"):
        if not data.get(key):
            errors.append(f"{rel(path)}: falta '{key}'")

    links = data.get("links") or {}
    if not isinstance(links, dict):
        errors.append(f"{rel(path)}: 'links' debe ser un objeto")
        links = {}
    for key in ("portfolio", "github", "linkedin"):
        if not links.get(key):
            errors.append(f"{rel(path)}: falta links.{key}")

    sections = split_sections(body)
    if "CV" not in sections:
        errors.append(f"{rel(path)}: falta la sección '## CV'")
    if "Portfolio" not in sections:
        errors.append(f"{rel(path)}: falta la sección '## Portfolio'")

    soft = parse_soft_skills(sections.get("Soft skills", ""))
    if not soft:
        errors.append(f"{rel(path)}: falta la sección '## Soft skills' con bullets '- **Título:** texto'")

    data["links"] = links
    return data, sections, soft


def load_entries(errors: list) -> list:
    entries = []
    for directory, expected_type in TYPES_BY_DIR.items():
        folder = CONTENT_DIR / directory
        if not folder.exists():
            errors.append(f"content/{directory}: carpeta inexistente")
            continue
        for path in sorted(folder.glob("*.md")):
            try:
                data, body = read_markdown(path)
            except ContentError as exc:
                errors.append(str(exc))
                continue

            where = rel(path)
            unknown = set(data) - ALLOWED_KEYS
            if unknown:
                errors.append(f"{where}: claves no reconocidas: {sorted(unknown)}")

            entry_type = data.get("type")
            if entry_type is None:
                data["type"] = expected_type
                entry_type = expected_type
            if entry_type != expected_type:
                errors.append(
                    f"{where}: type {entry_type!r} no coincide con la carpeta "
                    f"(se esperaba {expected_type!r})"
                )

            for key in ("title", "start"):
                if not data.get(key):
                    errors.append(f"{where}: falta '{key}'")

            if entry_type in ("job", "education") and not data.get("org"):
                errors.append(f"{where}: falta 'org'")

            try:
                start = parse_date(data.get("start"))
                end = parse_date(data.get("end"))
            except ContentError as exc:
                errors.append(f"{where}: {exc}")
                start = end = None

            if start and end:
                start_key = (start[0], start[1] or 0)
                end_key = (end[0], end[1] or 0)
                if end_key < start_key:
                    errors.append(f"{where}: 'end' es anterior a 'start'")

            for key in ("cv", "portfolio", "draft", "current"):
                if key in data and not isinstance(data[key], bool):
                    errors.append(f"{where}: '{key}' debe ser booleano")

            tags = data.get("tags", [])
            if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
                errors.append(f"{where}: 'tags' debe ser una lista de textos")
                tags = data["tags"] = []

            for key in ("link", "repo", "demo"):
                value = data.get(key)
                if value and not str(value).startswith(("http://", "https://")):
                    errors.append(f"{where}: '{key}' debe ser una URL http(s)")

            entries.append(Entry(path=path, type=entry_type, data=data, body=body))

    skill_names = set()
    skills_file = CONTENT_DIR / "skills.yml"
    if skills_file.exists():
        try:
            raw = yaml.safe_load(skills_file.read_text(encoding="utf-8")) or {}
            for group in raw.get("groups") or []:
                for item in group.get("items") or []:
                    name = item if isinstance(item, str) else (item or {}).get("name")
                    if name:
                        skill_names.add(name)
        except yaml.YAMLError:
            pass

    for entry in entries:
        for tag in entry.data.get("tags", []):
            if tag not in skill_names:
                errors.append(
                    f"{rel(entry.path)}: tag {tag!r} no existe en content/skills.yml"
                )

    return entries


def load() -> Content:
    errors: list = []
    profile, sections, soft = load_profile(errors)
    skills = load_skills(errors)
    entries = load_entries(errors)
    return Content(
        profile=profile,
        sections=sections,
        soft_skills=soft,
        skills=skills,
        entries=entries,
        errors=errors,
    )


def source_commit() -> str:
    import os

    sha = os.environ.get("GITHUB_SHA", "")
    if sha:
        return sha[:7]
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def public_entries(content: Content) -> list:
    return sorted(
        [e for e in content.entries if e.is_public()],
        key=lambda e: e.sort_key,
        reverse=True,
    )


def cv_entries(content: Content) -> list:
    return sorted(
        [
            e
            for e in content.entries
            if e.in_cv() and e.type in ("job", "project")
        ],
        key=lambda e: e.sort_key,
        reverse=True,
    )
