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


def render_chip_list(items: list[str]) -> str:
    return "".join(f"<span>{html.escape(item)}</span>" for item in items)


def render_topic_hero(topic: dict) -> str:
    tags = render_chip_list(topic.get("tags", []))
    goals = topic.get("goals", [])
    goal_html = ""
    if goals:
        goal_html = '<div class="hero-goals">' + "".join(f"<div>{apply_inline(goal)}</div>" for goal in goals) + "</div>"
    hero_class = "topic-hero" if goals else "topic-hero compact"
    return (
        f'<section class="{hero_class}">'
        '<div class="hero-copy">'
        f'<div class="hero-kicker">{html.escape(topic.get("kicker", "Study Module"))}</div>'
        f'<h1>{html.escape(topic["title"])}</h1>'
        f'<p class="sub">{html.escape(topic.get("subtitle", ""))}</p>'
        f'<div class="hero-tags">{tags}</div>'
        "</div>"
        f"{goal_html}"
        "</section>"
    )


def render_overview(block: dict) -> str:
    items = block.get("items", [])
    cards = []
    for item in items:
        cards.append(
            '<div class="insight-card">'
            f'<div class="insight-label">{html.escape(item.get("label", ""))}</div>'
            f'<div class="insight-value">{apply_inline(item.get("value", ""))}</div>'
            "</div>"
        )
    return f'<section class="component-block"><h2>{html.escape(block.get("title", "本页概览"))}</h2><div class="overview-grid">{"".join(cards)}</div></section>'


def render_path(block: dict) -> str:
    items = block.get("items", [])
    steps = []
    for index, item in enumerate(items, 1):
        if isinstance(item, dict):
            title = item.get("title", "")
            desc = item.get("desc", "")
        else:
            title = str(item)
            desc = ""
        steps.append(
            '<div class="path-step">'
            f'<div class="path-index">{index}</div>'
            f'<div><div class="path-title">{html.escape(title)}</div>'
            f'<div class="path-desc">{apply_inline(desc)}</div></div>'
            "</div>"
        )
    return f'<section class="component-block"><h2>{html.escape(block.get("title", "学习路径"))}</h2><div class="path-list">{"".join(steps)}</div></section>'


def render_callout(block: dict) -> str:
    tone = html.escape(block.get("tone", "note"))
    title = html.escape(block.get("title", "提示"))
    items = block.get("items", [])
    text = block.get("text", "")
    body = markdown_to_html(text) if text else ""
    if items:
        body += "<ul>" + "".join(f"<li>{apply_inline(item)}</li>" for item in items) + "</ul>"
    return f'<section class="callout callout-{tone}"><div class="callout-title">{title}</div>{body}</section>'


def render_resources(block: dict, output: Path) -> str:
    items = block.get("items", [])
    resources = []
    for item in items:
        href = item.get("href", "#")
        if not href.startswith(("http://", "https://", "#")):
            href = rel_link(output, href)
        resources.append(
            '<a class="resource-card" href="{href}">'
            '<div class="resource-type">{rtype}</div>'
            '<div class="resource-title">{title}</div>'
            '<div class="resource-desc">{desc}</div>'
            "</a>".format(
                href=html.escape(href),
                rtype=html.escape(item.get("type", "resource")),
                title=html.escape(item.get("title", "")),
                desc=html.escape(item.get("desc", "")),
            )
        )
    return f'<section class="component-block"><h2>{html.escape(block.get("title", "相关资源"))}</h2><div class="resource-grid">{"".join(resources)}</div></section>'


def render_section(block: dict, topic_path: Path) -> str:
    md_path = topic_path.parent / block["file"]
    body = markdown_to_html(md_path.read_text(encoding="utf-8"))
    title = f'<h2>{html.escape(block["title"])}</h2>'
    card = block.get("card")
    if card:
        return f'{title}\n<div class="card {html.escape(card)}">\n{body}\n</div>'
    return f"{title}\n{body}"


def render_grid(block: dict, topic_path: Path) -> str:
    cards = []
    for item in block.get("items", []):
        body = ""
        if item.get("file"):
            body = markdown_to_html((topic_path.parent / item["file"]).read_text(encoding="utf-8"))
        elif item.get("text"):
            body = markdown_to_html(item["text"])
        card_class = html.escape(item.get("card", "card-m"))
        cards.append(
            f'<article class="content-card {card_class}">'
            f'<h3>{html.escape(item.get("title", ""))}</h3>'
            f'<p class="content-card-desc">{html.escape(item.get("description", ""))}</p>'
            f'{body}'
            "</article>"
        )
    return f'<section class="component-block"><h2>{html.escape(block.get("title", "核心模块"))}</h2><div class="content-grid">{"".join(cards)}</div></section>'


def render_tabs(block: dict, topic_path: Path) -> str:
    items = block.get("items", [])
    if not items:
        return ""
    nav = []
    panels = []
    group = html.escape(block.get("id", "topic-tabs"))
    for index, item in enumerate(items):
        tab_id = f"{group}-tab-{index + 1}"
        panel_id = f"{group}-panel-{index + 1}"
        active = index == 0
        title = item.get("title", f"模块 {index + 1}")
        desc = item.get("description", "")
        body = ""
        if item.get("file"):
            body = markdown_to_html((topic_path.parent / item["file"]).read_text(encoding="utf-8"))
        elif item.get("text"):
            body = markdown_to_html(item["text"])
        nav.append(
            '<button class="tab-button{active}" type="button" role="tab" id="{tab_id}" '
            'aria-controls="{panel_id}" aria-selected="{selected}">'
            '<span class="tab-title">{title}</span>'
            '<span class="tab-desc">{desc}</span>'
            '</button>'.format(
                active=" active" if active else "",
                tab_id=tab_id,
                panel_id=panel_id,
                selected="true" if active else "false",
                title=html.escape(title),
                desc=html.escape(desc),
            )
        )
        panels.append(
            '<article class="tab-panel{active}" role="tabpanel" id="{panel_id}" '
            'aria-labelledby="{tab_id}" {hidden}>'
            '<div class="tab-panel-head">'
            '<div class="tab-panel-kicker">内容模块</div>'
            '<h2>{title}</h2>'
            '</div>'
            '<div class="tab-panel-body">{body}</div>'
            '</article>'.format(
                active=" active" if active else "",
                panel_id=panel_id,
                tab_id=tab_id,
                hidden="" if active else "hidden",
                title=html.escape(title),
                body=body,
            )
        )
    return (
        '<section class="tabs-shell" data-tabs>'
        f'<div class="tabs-nav" role="tablist" aria-label="{html.escape(block.get("title", "内容模块"))}">{"".join(nav)}</div>'
        f'<div class="tabs-panels">{"".join(panels)}</div>'
        "</section>"
    )


def render_layout_block(block: dict, topic_path: Path, output: Path) -> str:
    block_type = block.get("type", "section")
    if block_type == "tabs":
        return render_tabs(block, topic_path)
    if block_type == "overview":
        return render_overview(block)
    if block_type == "path":
        return render_path(block)
    if block_type == "grid":
        return render_grid(block, topic_path)
    if block_type == "callout":
        return render_callout(block)
    if block_type == "resources":
        return render_resources(block, output)
    return render_section(block, topic_path)


def render_topic(topic_path: Path) -> Path:
    topic = json.loads(topic_path.read_text(encoding="utf-8"))
    output = ROOT / topic["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    blocks = [render_topic_hero(topic)]
    layout = topic.get("layout") or [{"type": "section", **section} for section in topic.get("sections", [])]
    blocks.extend(render_layout_block(block, topic_path, output) for block in layout)
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
