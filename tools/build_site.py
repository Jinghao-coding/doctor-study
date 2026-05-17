#!/usr/bin/env python3
"""Build generated HTML pages from small markdown/json content files."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
SITE = json.loads((CONTENT / "site.json").read_text(encoding="utf-8"))


def rel_link(output: Path, target: str) -> str:
    target_path = ROOT / target
    return Path("." if output.parent == ROOT else Path(*([".."] * len(output.parent.relative_to(ROOT).parts)))).joinpath(target_path.relative_to(ROOT)).as_posix()


def apply_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def render_table(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(rows) >= 2 and all(set(cell) <= {"-", ":", " "} for cell in rows[1]):
        head, body = rows[0], rows[2:]
    else:
        head, body = [], rows
    parts = ["<table>"]
    if head:
        parts.append("<tr>" + "".join(f"<th>{apply_inline(cell)}</th>" for cell in head) + "</tr>")
    for row in body:
        parts.append("<tr>" + "".join(f"<td>{apply_inline(cell)}</td>" for cell in row) + "</tr>")
    parts.append("</table>")
    return "\n".join(parts)


def markdown_to_html(markdown: str) -> str:
    out: list[str] = []
    para: list[str] = []
    list_items: list[str] = []
    list_type: str | None = None
    table_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def flush_para() -> None:
        nonlocal para
        if para:
            out.append(f"<p>{apply_inline(' '.join(para))}</p>")
            para = []

    def flush_list() -> None:
        nonlocal list_items, list_type
        if list_items:
            tag = list_type or "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{apply_inline(item)}</li>" for item in list_items) + f"</{tag}>")
            list_items = []
            list_type = None

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            out.append(render_table(table_lines))
            table_lines = []

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            flush_para(); flush_list(); flush_table()
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_para(); flush_list(); flush_table()
            continue
        if line.lstrip().startswith("<"):
            flush_para(); flush_list(); flush_table()
            out.append(line)
            continue
        if line.startswith("#"):
            flush_para(); flush_list(); flush_table()
            level = min(len(line) - len(line.lstrip("#")), 4)
            text = line[level:].strip()
            out.append(f"<h{level}>{apply_inline(text)}</h{level}>")
            continue
        if line.startswith("|") and line.endswith("|"):
            flush_para(); flush_list()
            table_lines.append(line)
            continue
        m = re.match(r"^[-*]\s+(.+)$", line)
        if m:
            flush_para(); flush_table()
            if list_type not in (None, "ul"):
                flush_list()
            list_type = "ul"
            list_items.append(m.group(1))
            continue
        m = re.match(r"^\d+\.\s+(.+)$", line)
        if m:
            flush_para(); flush_table()
            if list_type not in (None, "ol"):
                flush_list()
            list_type = "ol"
            list_items.append(m.group(1))
            continue
        para.append(line.strip())

    flush_para(); flush_list(); flush_table()
    return "\n".join(out)


def render_nav(output: Path) -> str:
    links = []
    for item in SITE.get("nav", [])[1:]:
        links.append(f'  <a href="{rel_link(output, item["href"])}">{html.escape(item["title"])}</a>')
    return "\n".join(links)


def render_topic(topic_path: Path) -> Path:
    topic = json.loads(topic_path.read_text(encoding="utf-8"))
    output = ROOT / topic["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    for section in topic.get("sections", []):
        md_path = topic_path.parent / section["file"]
        body = markdown_to_html(md_path.read_text(encoding="utf-8"))
        card = section.get("card")
        section_title = f'<h2>{html.escape(section["title"])}</h2>'
        if card:
            blocks.append(f'{section_title}\n<div class="card {card}">\n{body}\n</div>')
        else:
            blocks.append(f'{section_title}\n{body}')
    template = (TEMPLATES / "page.html").read_text(encoding="utf-8")
    page = template.replace("{{title}}", html.escape(topic["title"]))
    page = page.replace("{{subtitle}}", html.escape(topic.get("subtitle", "")))
    page = page.replace("{{content}}", "\n\n".join(blocks))
    page = page.replace("{{nav_links}}", render_nav(output))
    page = page.replace("{{home_path}}", rel_link(output, "index.html"))
    page = page.replace("{{css_path}}", rel_link(output, "assets/style.css"))
    page = page.replace("{{script_path}}", rel_link(output, "assets/script.js"))
    output.write_text(page, encoding="utf-8")
    return output


def render_index() -> Path:
    output = ROOT / "index.html"
    card_template = (TEMPLATES / "topic-card.html").read_text(encoding="utf-8")
    cards = []
    for topic in SITE.get("topics", []):
        tags = "".join(f"<span>{html.escape(tag)}</span>" for tag in topic.get("tags", []))
        card = card_template.replace("{{color}}", html.escape(topic.get("color", "c1")))
        card = card.replace("{{href}}", html.escape(topic["output"]))
        card = card.replace("{{title}}", html.escape(topic["title"]))
        card = card.replace("{{description}}", html.escape(topic.get("description", "")))
        card = card.replace("{{tags}}", tags)
        cards.append(card)
    template = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    page = template.replace("{{title}}", html.escape(SITE["title"]))
    page = page.replace("{{subtitle}}", html.escape(SITE.get("subtitle", "")))
    page = page.replace("{{topic_cards}}", "\n\n".join(cards))
    output.write_text(page, encoding="utf-8")
    return output


def main() -> None:
    generated = [render_index()]
    for topic in SITE.get("topics", []):
        generated.append(render_topic(ROOT / topic["source"]))
    for path in generated:
        print(f"generated {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
