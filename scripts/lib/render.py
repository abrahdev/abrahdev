from __future__ import annotations

import html
import re

from .content import (
    Content,
    cv_entries,
    cv_period,
    date_key,
    parse_date,
    portfolio_period,
    public_entries,
    source_commit,
)

LINK_ORDER = [
    ("portfolio", "Porfolio"),
    ("linkedin", "LinkedIn"),
    ("github", "GitHub"),
    ("notion", "Notion"),
]


def inline(text: str) -> str:
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\w)_([^_]+?)_(?!\w)", r"<em>\1</em>", text)
    return text


def md_to_html(text: str) -> str:
    blocks = re.split(r"\n\s*\n", text.strip())
    out = []
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        if lines and all(line.strip().startswith("- ") for line in lines):
            items = "".join(
                f"<li>{inline(line.strip()[2:])}</li>" for line in lines
            )
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{inline(' '.join(line.strip() for line in lines))}</p>")
    return "\n".join(out)


def host(url: str) -> str:
    return re.sub(r"^https?://", "", url).rstrip("/")


def entry_payload(entry, date_format: str) -> dict:
    payload = {
        "type": entry.type,
        "slug": entry.slug,
        "title": entry.get("title"),
        "date": date_format(
            entry.get("start"), entry.get("end"), bool(entry.get("current"))
        ),
        "start": str(entry.get("start")) if entry.get("start") is not None else None,
        "end": str(entry.get("end")) if entry.get("end") is not None else None,
        "current": bool(entry.get("current")),
        "body": entry.body,
        "bodyHtml": md_to_html(entry.body) if entry.body else "",
    }
    for key in ("card_title", "summary", "role", "org", "link", "repo", "demo", "image"):
        if entry.get(key):
            payload[key] = entry.get(key)
    if entry.get("tags"):
        payload["tags"] = entry.get("tags")
    if entry.get("cv_group"):
        payload["cvGroup"] = entry.get("cv_group")
    return payload


def render_profile_json(content: Content) -> dict:
    profile = content.profile
    return {
        "schemaVersion": 1,
        "sourceCommit": source_commit(),
        "profile": {
            "name": profile.get("name"),
            "displayName": profile.get("display_name"),
            "handle": profile.get("handle"),
            "headline": profile.get("headline"),
            "email": profile.get("email"),
            "avatar": profile.get("avatar"),
            "links": profile.get("links", {}),
            "about": {
                "cv": content.sections.get("CV", ""),
                "portfolio": content.sections.get("Portfolio", ""),
                "readme": content.sections.get("README", ""),
            },
            "softSkills": content.soft_skills,
        },
        "skills": content.skills,
        "timeline": [
            entry_payload(entry, portfolio_period)
            for entry in public_entries(content)
            if entry.type != "project"
        ],
        "projects": [
            entry_payload(entry, portfolio_period)
            for entry in public_entries(content)
            if entry.type == "project"
        ],
    }


def render_skills_table(content: Content) -> str:
    technical = []
    for group in content.skills:
        items = ", ".join(item["name"] for item in group["items"])
        technical.append(
            f'        <li><strong>{html.escape(group["label"])}:</strong> {html.escape(items)}.</li>'
        )
    soft = [
        f'        <li><strong>{html.escape(item["title"])}:</strong> {inline(item["text"])}</li>'
        for item in content.soft_skills
    ]
    return "\n".join(
        [
            '<table style="width:100%; border:none; border-collapse:collapse;">',
            '  <tr style="border:none;">',
            '    <td style="width:50%; vertical-align:top; border:none; padding-right:20px;">',
            "      <strong>Technical Skills</strong>",
            "      <ul>",
            *technical,
            "      </ul>",
            "    </td>",
            '    <td style="width:50%; vertical-align:top; border:none; padding-left:20px;">',
            "      <strong>Soft Skills</strong>",
            "      <ul>",
            *soft,
            "      </ul>",
            "    </td>",
            "  </tr>",
            "</table>",
        ]
    )


def cv_heading(entry) -> str:
    title = entry.get("title")
    org = entry.get("org")
    role = entry.get("role")
    if role:
        return f"{role} - {title} ({org})" if org else f"{role} - {title}"
    if org:
        return f"{title} - {org}"
    return title


def as_bullet(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    lines = [line for line in text.splitlines() if line.strip()]
    if lines and all(line.strip().startswith("- ") for line in lines):
        return text
    return f"- {text}"


def cv_group_blocks(content: Content):
    groups = {}
    for entry in cv_entries(content):
        group = entry.get("cv_group")
        if group:
            groups.setdefault(group, []).append(entry)

    blocks = []
    grouped_ids = set()
    for name, members in groups.items():
        members.sort(key=lambda e: e.sort_key, reverse=True)
        starts = [e.get("start") for e in members if e.get("start")]
        ends = [e.get("end") for e in members if e.get("end")]
        start = min(starts, key=date_key) if starts else None
        end = max(ends, key=date_key) if ends else None
        if len(ends) < len(members):
            end = None
        start_parsed = parse_date(start)
        sort_key = (start_parsed[0], start_parsed[1] or 0) if start_parsed else (0, 0)
        body_parts = [as_bullet(e.body) for e in members if e.body]
        ongoing = any(e.get("current") for e in members)
        summary = next(
            (e.get("cv_group_summary") for e in members if e.get("cv_group_summary")),
            None,
        )
        block_body = summary.strip() if summary else "\n".join(body_parts)
        blocks.append(
            (
                sort_key,
                f"**{cv_period(start, end, ongoing)} | {name}**\n\n{block_body}",
            )
        )
        grouped_ids.update(id(e) for e in members)

    for entry in cv_entries(content):
        if id(entry) in grouped_ids:
            continue
        blocks.append(
            (
                entry.sort_key,
                f"**{cv_period(entry.get('start'), entry.get('end'), bool(entry.get('current')))} | "
                f"{cv_heading(entry)}**\n\n{entry.body}",
            )
        )

    blocks.sort(key=lambda item: item[0], reverse=True)
    return [text for _, text in blocks]


def cv_section(content: Content, kind: str) -> list:
    entries = [
        e
        for e in content.entries
        if e.in_cv() and e.type == kind
    ]
    entries.sort(key=lambda e: e.sort_key, reverse=True)
    blocks = []
    for entry in entries:
        org = entry.get("org")
        header = f"**{cv_period(entry.get('start'), entry.get('end'), bool(entry.get('current')))} | {entry.get('title')}**"
        if org:
            header += f"\n_{org}_"
        body = entry.body
        blocks.append(f"{header}\n\n{body}" if body else header)
    return blocks


README_BADGES = {
    "cv": ("CV", "Descargar", "2EA44F", None, "101010"),
    "portfolio": ("Portfolio", "abrah.dev", "5B47ED", "vercel", "101010"),
    "github": ("GitHub", "Mi_perfil", "5B47ED", "github", "101010"),
    "linkedin": ("Linkedin", "Perfil_Profesional", "2867B2", "linkedin", "101010"),
    "tiktok": ("TikTok", "Tutoriales%20rapidos", "ff0050", "tiktok", "000000"),
    "twitch": ("Twitch", "Directos", "9146FF", "twitch", "101010"),
    "discord": ("Discord", "Comunidad", "5865F2", "discord", "101010"),
}

CV_RAW_URL = (
    "https://raw.githubusercontent.com/abrahdev/abrahdev/main/"
    "CV_Abraham_Escalona.pdf"
)


def badge(key: str, url: str) -> str:
    name, label, color, logo, label_color = README_BADGES[key]
    params = "?style=for-the-badge"
    if logo:
        params += f"&logo={logo}&logoColor=white"
    params += f"&labelColor={label_color}"
    return (
        f"[![{name}](https://img.shields.io/badge/{name}-{label}-{color}"
        f"{params})]({url})"
    )


def is_url(value: str) -> bool:
    return value.startswith(("http://", "https://")) or value.endswith(".svg")


SKILLICONS_BASE = "https://skillicons.dev/icons?i="


def skillicon_images(label: str, items: list) -> list:
    runs = []
    for item in items:
        icon = item.get("skillicon")
        if not icon:
            continue
        source = "url" if is_url(icon) else "slug"
        if runs and runs[-1]["source"] == source:
            runs[-1]["entries"].append((item["name"], icon))
        else:
            runs.append({"source": source, "entries": [(item["name"], icon)]})

    images = []
    for run in runs:
        if run["source"] == "slug":
            slugs = ",".join(value for _, value in run["entries"])
            images.append(f'![{label}]({SKILLICONS_BASE}{slugs})')
        else:
            for name, url in run["entries"]:
                images.append(f'![{name}]({url})')
    return images


def render_readme(content: Content) -> str:
    profile = content.profile
    links = profile.get("links", {})
    roles = [part.strip() for part in profile.get("headline", "").split(",", 1)]

    lines = ["<!-- Generado desde content/ por scripts/build.py. No editar a mano. -->"]

    headline = f'<h1>Hi, I\'m {profile.get("display_name")}!'
    if roles:
        headline += f' <br/><a href="{links.get("github", "#")}">{roles[0]}</a>'
        if len(roles) > 1:
            headline += f', <a href="{links.get("linkedin", "#")}">{roles[1]}</a>'
    headline += "</h1>"
    lines.append(headline)

    current = sorted(
        [
            entry
            for entry in content.entries
            if entry.type == "project" and entry.get("current") and entry.is_public()
        ],
        key=lambda entry: entry.sort_key,
        reverse=True,
    )
    if current:
        lines.extend(["", "<h2>🔭 I'm currently working on</h2>", ""])
        for entry in current:
            lines.append(f'- {entry.get("card_title") or entry.get("title")}')

    about = content.sections.get("README") or content.sections.get("Portfolio", "")
    if about:
        lines.extend(["", "<h2>🔍 About me</h2>", "", about])

    skill_groups = []
    for group in content.skills:
        images = skillicon_images(group["label"], group["items"])
        if images:
            skill_groups.append((group["label"], images))

    if skill_groups:
        lines.extend(["", "<h2>🐍 Skills</h2>", ""])
        for label, images in skill_groups:
            lines.append(f"#### {label}")
            lines.append(" ".join(images))
            lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    lines.extend(["", "---", ""])
    primary = [badge("cv", CV_RAW_URL)]
    if links.get("portfolio"):
        primary.append(badge("portfolio", links["portfolio"]))
    if links.get("github"):
        primary.append(badge("github", links["github"]))
    lines.extend([" ".join(primary), ""])

    socials = [key for key in ("linkedin", "tiktok", "twitch") if links.get(key)]
    if socials:
        lines.extend(
            ["### Redes:", "", " ".join(badge(key, links[key]) for key in socials) + ".", ""]
        )

    if links.get("discord"):
        lines.extend(["### Comunidad:", "", badge("discord", links["discord"]), ""])

    return "\n".join(lines).rstrip() + "\n"


def render_cv(content: Content) -> str:
    profile = content.profile
    links = profile.get("links", {})

    contact = [profile.get("name")]
    if profile.get("phone"):
        contact.append(profile.get("phone"))
    if profile.get("email"):
        contact.append(profile.get("email"))
    if links.get("portfolio"):
        contact.append(
            f'Porfolio: [{host(links["portfolio"])}]({links["portfolio"]})'
        )

    lines = [
        "<!-- Generado desde content/ por scripts/build.py. No editar a mano. -->",
        f'<img src="{profile.get("avatar", "assets/me.jpg")}" alt="{profile.get("display_name")}" '
        'width="150" height="150" style="float: right; border-radius: 10%; '
        'width: 150px; height: 150px;" />',
        "",
        f'# {profile.get("display_name")}',
        "",
        f'**{profile.get("headline")}**',
        "",
        f'<small>{" | ".join(contact)}</small>',
        "",
        "## OBJETIVO",
        "",
        content.sections.get("CV", "").strip(),
        "",
        "## SKILLS",
        "",
        render_skills_table(content),
        "",
        "## EXPERIENCIA Y PROYECTOS",
        "",
    ]

    for block in cv_group_blocks(content):
        lines.extend([block, ""])

    lines.extend(["## EDUCACIÓN", ""])
    for block in cv_section(content, "education"):
        lines.extend([block, ""])

    lines.extend(["## RECONOCIMIENTOS", ""])
    for block in cv_section(content, "award"):
        lines.extend([block, ""])

    links_line = " | ".join(
        f'[{label}]({links[key]})' for key, label in LINK_ORDER if links.get(key)
    )
    lines.extend(["## ENLACES", "", links_line, ""])

    return "\n".join(lines).rstrip() + "\n"
