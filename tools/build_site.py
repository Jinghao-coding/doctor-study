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

# 单一分类数据源：首页 Track、顶部导航、侧栏「学习主题」三处共用，避免分类逻辑漂移。
TRACKS = [
    {
        "key": "foundation_cards",
        "label": "计算机与系统基础",
        "short_label": "系统基础",
        "eyebrow": "Foundation",
        "description": "操作系统、组成原理、网络、Linux/容器、编程工程与分布式系统，建立 AI Infra 面试所需的系统底座。",
        "slugs": [
            "cs-basics",
            "cs-basics/os",
            "cs-basics/computer-architecture",
            "cs-basics/networking",
            "cs-basics/programming-systems",
            "cs-basics/golang",
            "cs-basics/linux-container",
            "cs-basics/linux-kernel-ai",
            "cs-basics/distributed-ai",
        ],
        "home_max": 1,
    },
    {
        "key": "systems_cards",
        "label": "AI Infra 核心系统",
        "short_label": "核心系统",
        "eyebrow": "Core Systems",
        "description": "从 Transformer、GPU/CUDA 到算力资源模型，建立大模型系统最核心的硬件与模型执行直觉。",
        "slugs": [
            "ai-infra/transformer",
            "ai-infra/gpu",
        ],
    },
    {
        "key": "scheduling_cards",
        "label": "调度与集群",
        "short_label": "调度集群",
        "eyebrow": "Scheduling",
        "description": "任务调度理论、Kubernetes 与 GPU 集群管理，覆盖多租户、拓扑、队列和稳定性治理。",
        "slugs": [
            "ai-infra/scheduling",
            "ai-infra/kubernetes",
            "ai-infra/cluster-management",
        ],
    },
    {
        "key": "serving_training_cards",
        "label": "推理 / 训练 / 性能",
        "short_label": "推理训练",
        "eyebrow": "Serving & Training",
        "description": "LLM 推理、分布式训练与性能预测建模，聚焦吞吐、延迟、显存、通信和容量判断。",
        "slugs": [
            "ai-infra/llm-inference",
            "ai-infra/distributed-training",
            "ai-infra/performance-prediction",
        ],
    },
    {
        "key": "interview_expression_cards",
        "label": "论文项目与 Agent",
        "short_label": "项目表达",
        "eyebrow": "Projects & Interview",
        "description": "论文工作和 Agent 工程表达，服务自我介绍、项目深挖和高频追问；综合设计题已归入各专题专栏。",
        "slugs": [
            "ai-infra/papers",
            "ai-infra/agent",
        ],
    },
]


def track_of(topic: dict) -> dict | None:
    slug = topic.get("slug", "")
    for track in TRACKS:
        if slug in track["slugs"]:
            return track
    return None


def topics_in_track(track: dict) -> list[dict]:
    """按 site.json 中 topics 的出现顺序返回属于该 track 的主题。"""
    return [t for t in SITE.get("topics", []) if t.get("slug") in track["slugs"]]


def rel_link(output: Path, target: str) -> str:
    target_path = ROOT / target
    return Path("." if output.parent == ROOT else Path(*([".."] * len(output.parent.relative_to(ROOT).parts)))).joinpath(target_path.relative_to(ROOT)).as_posix()


def asset_link(output: Path, target: str) -> str:
    """Append a mtime version so browsers do not keep stale CSS/JS."""
    target_path = ROOT / target
    version = int(target_path.stat().st_mtime)
    return f"{rel_link(output, target)}?v={version}"


_REL_URL_RE = re.compile(r'(src|href)\s*=\s*"([^"]+)"')


def read_md(md_path: Path, output: Path) -> str:
    """Read markdown file, rewriting relative src/href paths to be correct for output location."""
    text = md_path.read_text(encoding="utf-8")
    md_dir = md_path.parent

    def _rewrite(m: re.Match) -> str:
        attr, url = m.group(1), m.group(2)
        if url.startswith(("#", "http:", "https:", "mailto:", "javascript:", "data:")):
            return m.group(0)
        if url.startswith("/"):
            abs_target = ROOT / url.lstrip("/")
        else:
            abs_target = (md_dir / url).resolve()
        try:
            rel = abs_target.relative_to(ROOT)
        except ValueError:
            return m.group(0)
        depth = len(output.parent.relative_to(ROOT).parts)
        prefix = "." if depth == 0 else "/".join([".."] * depth)
        new_url = (prefix + "/" + rel.as_posix()) if prefix != "." else rel.as_posix()
        return f'{attr}="{new_url}"'

    return _REL_URL_RE.sub(_rewrite, text)


def apply_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def apply_inline_in_html(text: str) -> str:
    """Apply inline markdown to text already inside HTML blocks.
    First unescape any existing HTML entities, then escape + apply markdown,
    so existing entities like &lt; are preserved without double-escaping,
    and raw < or & in markdown text are properly escaped."""
    text = html.unescape(text)
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def render_table(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(rows) >= 2 and all(set(cell) <= {"-", ":", " "} for cell in rows[1]):
        head, body = rows[0], rows[2:]
    else:
        head, body = [], rows
    parts = ['<div class="table-scroll"><table>']
    if head:
        parts.append("<tr>" + "".join(f"<th>{apply_inline(cell)}</th>" for cell in head) + "</tr>")
    for row in body:
        parts.append("<tr>" + "".join(f"<td>{apply_inline(cell)}</td>" for cell in row) + "</tr>")
    parts.append("</table></div>")
    return "\n".join(parts)


def render_flow(lines: list[str]) -> str:
    steps = []
    for index, line in enumerate(lines, 1):
        text = line.strip()
        if not text:
            continue
        if "|" in text:
            title, desc = [part.strip() for part in text.split("|", 1)]
        else:
            title, desc = text, ""
        desc_html = f'<div class="flow-desc">{apply_inline(desc)}</div>' if desc else ""
        steps.append(
            '<div class="flow-step">'
            f'<div class="flow-index">{index:02d}</div>'
            f'<div class="flow-title">{apply_inline(title)}</div>'
            f'{desc_html}'
            '</div>'
        )
    if not steps:
        return ""
    return '<div class="flow" role="list">' + "".join(steps) + "</div>"


def render_code_block(lines: list[str], lang: str) -> str:
    if lang.lower() == "flow":
        return render_flow(lines)
    if lang.lower() in {"math", "latex", "tex"}:
        formula = "\n".join(lines).strip()
        return f'<div class="formula">$$\n{html.escape(formula)}\n$$</div>'
    class_attr = f' class="language-{html.escape(lang)}"' if lang else ""
    return f"<pre><code{class_attr}>" + html.escape("\n".join(lines)) + "</code></pre>"


def markdown_to_html(markdown: str) -> str:
    out: list[str] = []
    para: list[str] = []
    list_items: list[str] = []
    list_type: str | None = None
    table_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False
    code_lang = ""
    raw_html_lines: list[str] = []
    raw_html_tag: str | None = None
    raw_html_depth = 0
    html_in_code = False
    html_code_lang = ""
    html_code_lines: list[str] = []
    html_in_pre = 0
    html_in_table = False
    html_table_lines: list[str] = []

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

    def flush_html_table() -> None:
        nonlocal html_in_table, html_table_lines
        if html_in_table and html_table_lines:
            raw_html_lines.append(render_table(html_table_lines))
            html_table_lines = []
            html_in_table = False

    def _inline_html_line(line: str) -> str:
        """Apply inline markdown processing to text segments within an HTML line,
        preserving HTML tags and their attributes. Does NOT modify html_in_pre state;
        caller tracks that."""
        if html_in_pre > 0:
            return line
        if not line.strip():
            return line
        if line.lstrip().startswith("<") and ">" in line:
            parts = re.split(r"(<[^>]+>)", line)
            processed = []
            for part in parts:
                if part.startswith("<") and part.endswith(">"):
                    processed.append(part)
                elif part:
                    processed.append(apply_inline_in_html(part))
            return "".join(processed)
        return apply_inline_in_html(line)

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if raw_html_tag:
            lower = line.lower()
            old_html_in_pre = html_in_pre
            pre_open = len(re.findall(r"<\s*pre[\s>]", lower)) if not html_in_code else 0
            pre_close = len(re.findall(r"<\s*/\s*pre\s*>", lower)) if not html_in_code else 0
            new_html_in_pre = old_html_in_pre + pre_open - pre_close
            should_parse_div = not html_in_code and (old_html_in_pre <= 0 or pre_close > 0)
            if should_parse_div:
                if old_html_in_pre > 0 and pre_close > 0:
                    div_open_count = 0
                    div_close_count = 0
                    for m in re.finditer(rf"<\s*{raw_html_tag}(?:\s|>|/)", lower):
                        if m.start() > lower.rfind("</pre>"):
                            div_open_count += 1
                    for m in re.finditer(rf"<\s*/\s*{raw_html_tag}\s*>", lower):
                        if m.start() > lower.rfind("</pre>"):
                            div_close_count += 1
                    raw_html_depth += div_open_count - div_close_count
                else:
                    raw_html_depth += len(re.findall(rf"<\s*{raw_html_tag}(?:\s|>|/)", lower))
                    raw_html_depth -= len(re.findall(rf"<\s*/\s*{raw_html_tag}\s*>", lower))
            if html_in_code:
                if line.strip().startswith("```"):
                    flush_html_table()
                    raw_html_lines.append(render_code_block(html_code_lines, html_code_lang))
                    html_code_lines = []
                    html_in_code = False
                    html_code_lang = ""
                    post_pre_open = len(re.findall(r"<\s*pre[\s>]", lower))
                    post_pre_close = len(re.findall(r"<\s*/\s*pre\s*>", lower))
                    html_in_pre = html_in_pre + post_pre_open - post_pre_close
                    post_div_open = len(re.findall(rf"<\s*{raw_html_tag}(?:\s|>|/)", lower))
                    post_div_close = len(re.findall(rf"<\s*/\s*{raw_html_tag}\s*>", lower))
                    raw_html_depth += post_div_open - post_div_close
                else:
                    html_code_lines.append(line)
                if raw_html_depth <= 0:
                    flush_html_table()
                    if html_in_code and html_code_lines:
                        raw_html_lines.append(render_code_block(html_code_lines, html_code_lang))
                        html_code_lines = []
                        html_in_code = False
                    out.append("\n".join(raw_html_lines))
                    raw_html_lines = []
                    raw_html_tag = None
                    raw_html_depth = 0
                    html_in_pre = 0
                    html_in_table = False
                    html_table_lines = []
                continue
            if old_html_in_pre <= 0 and line.strip().startswith("```"):
                flush_html_table()
                html_in_code = True
                html_code_lang = line.strip()[3:].strip()
                html_code_lines = []
                if raw_html_depth <= 0:
                    out.append("\n".join(raw_html_lines))
                    raw_html_lines = []
                    raw_html_tag = None
                    raw_html_depth = 0
                    html_in_pre = 0
                    html_in_table = False
                    html_table_lines = []
                else:
                    html_in_pre = new_html_in_pre
                continue
            is_table_line = old_html_in_pre <= 0 and line.strip().startswith("|") and line.strip().endswith("|")
            if old_html_in_pre <= 0 and is_table_line:
                html_in_table = True
                html_table_lines.append(line)
            else:
                if html_in_table:
                    flush_html_table()
                raw_html_lines.append(_inline_html_line(line))
            html_in_pre = new_html_in_pre
            if raw_html_depth <= 0:
                flush_html_table()
                out.append("\n".join(raw_html_lines))
                raw_html_lines = []
                raw_html_tag = None
                raw_html_depth = 0
                html_in_pre = 0
                html_in_table = False
                html_table_lines = []
            continue
        if line.startswith("```"):
            flush_para(); flush_list(); flush_table()
            if in_code:
                out.append(render_code_block(code_lines, code_lang))
                code_lines = []
                in_code = False
                code_lang = ""
            else:
                in_code = True
                code_lang = line[3:].strip()
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_para(); flush_list(); flush_table()
            continue
        stripped_lower = line.lstrip().lower()
        m_html_block = re.match(r"<\s*(div|section|article|table|pre|script|style|svg)(?:\s|>|/)", stripped_lower)
        if m_html_block:
            flush_para(); flush_list(); flush_table()
            raw_html_tag = m_html_block.group(1)
            raw_html_lines = [line]
            raw_html_depth = len(re.findall(rf"<\s*{raw_html_tag}(?:\s|>|/)", stripped_lower))
            raw_html_depth -= len(re.findall(rf"<\s*/\s*{raw_html_tag}\s*>", stripped_lower))
            html_in_pre = len(re.findall(r"<\s*pre[\s>]", stripped_lower)) - len(re.findall(r"<\s*/\s*pre\s*>", stripped_lower))
            if raw_html_depth <= 0:
                out.append("\n".join(raw_html_lines))
                raw_html_lines = []
                raw_html_tag = None
                raw_html_depth = 0
                html_in_pre = 0
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
    if in_code and code_lines:
        out.append(render_code_block(code_lines, code_lang))
    if html_in_table and html_table_lines:
        flush_html_table()
    if raw_html_lines:
        out.append("\n".join(raw_html_lines))
    return "\n".join(out)


def render_top_nav(output: Path) -> str:
    def topic_link(topic: dict) -> str:
        return (
            f'<a href="{rel_link(output, topic["output"])}">'
            f'<span>{html.escape(topic["title"])}</span>'
            f'<small>{html.escape(" / ".join(topic.get("tags", [])[:3]))}</small>'
            "</a>"
        )

    menus = []
    for track in TRACKS:
        topics = topics_in_track(track)
        if not topics:
            continue
        links = "".join(topic_link(topic) for topic in topics)
        label = html.escape(track.get("short_label", track["label"]))
        full_label = html.escape(track["label"])
        menus.append(
            '<details class="nav-menu">'
            f'<summary title="{full_label}">{label}</summary>'
            f'<div class="nav-menu-panel">{links}</div>'
            '</details>'
        )

    return (
        '<a class="nav-brand" href="{home}">'
        '<span class="brand-mark">DS</span>'
        '<span><strong>doctor-study</strong><small>AI Infra interview desk</small></span>'
        '</a>'
        '<div class="nav-primary">'
        '<a class="nav-pill" href="{home}">首页</a>'
        '{menus}'
        '<button class="nav-search" type="button" data-focus-tabs>搜索模块</button>'
        '</div>'
        '<button class="side-toggle" type="button" aria-pressed="false">折叠主题</button>'
    ).format(home=rel_link(output, "index.html"), menus="".join(menus))


def render_side_nav(output: Path, current_output: Path) -> str:
    sections = []
    for track in TRACKS:
        topics = topics_in_track(track)
        if not topics:
            continue
        group_name = track.get("short_label", track["label"])
        group_title = track["label"]
        links = []
        for topic in topics:
            active = (ROOT / topic["output"]).resolve() == current_output.resolve()
            tags = " · ".join(topic.get("tags", [])[:2])
            initial = topic.get("title", "T").strip()[:2]
            links.append(
                '<a class="side-link{active}" href="{href}" data-initial="{initial}" title="{title}">'
                '<span>{title}</span>'
                '<small>{tags}</small>'
                '</a>'.format(
                    active=" active" if active else "",
                    href=rel_link(output, topic["output"]),
                    initial=html.escape(initial),
                    title=html.escape(topic["title"]),
                    tags=html.escape(tags),
                )
            )
        sections.append(
            '<div class="side-section">'
            f'<div class="side-section-title" title="{html.escape(group_title)}">{html.escape(group_name)}</div>'
            f'{"".join(links)}'
            '</div>'
        )
    return (
        '<aside class="app-sidebar">'
        '<div class="side-head">'
        '<div><div class="side-kicker">Study Map</div>'
        '<div class="side-title">学习主题</div></div>'
        '<button class="side-collapse" type="button" aria-pressed="false" title="折叠学习主题">‹</button>'
        '</div>'
        f'{"".join(sections)}'
        '</aside>'
        '<div class="side-resizer" role="separator" aria-orientation="vertical" '
        'aria-label="拖动调整学习主题宽度" title="拖动调整学习主题宽度"></div>'
    )


def render_topic_hero(topic: dict) -> str:
    subtitle = topic.get("subtitle", "")
    subtitle_html = f'<p class="sub">{html.escape(subtitle)}</p>' if subtitle else ""
    return (
        '<section class="topic-hero" aria-label="主题概览">'
        '<div class="hero-copy">'
        f'<h1>{html.escape(topic["title"])}</h1>'
        f'{subtitle_html}'
        "</div>"
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


def render_section(block: dict, topic_path: Path, output: Path) -> str:
    md_path = topic_path.parent / block["file"]
    body = markdown_to_html(read_md(md_path, output))
    title = f'<h2>{html.escape(block["title"])}</h2>'
    card = block.get("card")
    if card:
        return f'{title}\n<div class="card {html.escape(card)}">\n{body}\n</div>'
    return f"{title}\n{body}"


def render_grid(block: dict, topic_path: Path, output: Path) -> str:
    cards = []
    for item in block.get("items", []):
        body = ""
        if item.get("file"):
            body = markdown_to_html(read_md(topic_path.parent / item["file"], output))
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


LEVEL_CLASSES = {
    "基础": "level-basic",
    "进阶": "level-mid",
    "精通": "level-pro",
}


def _stable_mid(item: dict, group_id: str, idx: int) -> str:
    """基于源文件路径生成稳定 mid，避免章节顺序调整导致进度错位。"""
    src = item.get("file")
    if not src:
        files = item.get("files") or []
        src = files[0] if files else None
    if src:
        slug = re.sub(r"[^a-z0-9]+", "-", src.lower()).strip("-")
        return f"{group_id}::{slug}"
    return f"{group_id}::idx-{idx + 1}"


def _normalize_groups(block: dict) -> list[dict]:
    """统一返回 groups 结构。旧的扁平 items 包成单一隐式 group。"""
    if block.get("groups"):
        return [
            {"title": grp.get("title", ""), "items": grp.get("items", [])}
            for grp in block["groups"]
            if grp.get("items")
        ]
    if block.get("items"):
        return [{"title": "", "items": block["items"]}]
    return []


def _render_item_chips(item: dict) -> str:
    chips = []
    level = item.get("level")
    if level:
        cls = LEVEL_CLASSES.get(level, "level-basic")
        chips.append(f'<span class="chip chip-{cls}">{html.escape(level)}</span>')
    priority = item.get("priority")
    if priority:
        try:
            p = int(priority)
        except (TypeError, ValueError):
            p = 0
        if 1 <= p <= 3:
            stars = "★" * p + "☆" * (3 - p)
            chips.append(f'<span class="chip chip-priority" title="优先级 {p}/3">{stars}</span>')
    time_min = item.get("time")
    if time_min:
        chips.append(f'<span class="chip chip-time">⏱ {html.escape(str(time_min))} min</span>')
    if not chips:
        return ""
    return f'<span class="tab-chips">{"".join(chips)}</span>'


def _render_subtabs(subtabs: list, topic_path: Path, parent_id: str, output: Path) -> str:
    if not subtabs:
        return ""
    nav_buttons: list[str] = []
    panels: list[str] = []
    for idx, sub in enumerate(subtabs):
        sub_id = f"{parent_id}-sub-{idx + 1}"
        panel_sub_id = f"{parent_id}-subpanel-{idx + 1}"
        active = idx == 0
        title = sub.get("title", f"子模块 {idx + 1}")
        desc = sub.get("description", "")
        body = ""
        if sub.get("file"):
            body = markdown_to_html(read_md(topic_path.parent / sub["file"], output))
        elif sub.get("files"):
            body = "\n".join(
                markdown_to_html(read_md(topic_path.parent / file, output))
                for file in sub["files"]
            )
        elif sub.get("text"):
            body = markdown_to_html(sub["text"])
        desc_html = f'<span class="subtab-desc">{html.escape(desc)}</span>' if desc else ""
        nav_buttons.append(
            '<button class="subtab-button{active}" type="button" role="tab" id="{sid}" '
            'aria-controls="{pid}" aria-selected="{sel}" title="{title}">'
            '<span class="subtab-title">{title}</span>'
            '{desc_html}'
            '</button>'.format(
                active=" active" if active else "",
                sid=sub_id,
                pid=panel_sub_id,
                sel="true" if active else "false",
                title=html.escape(title),
                desc_html=desc_html,
            )
        )
        panels.append(
            '<div class="subtab-panel{active}" role="tabpanel" id="{pid}" aria-labelledby="{sid}" {hidden}>'
            '{body}'
            '</div>'.format(
                active=" active" if active else "",
                pid=panel_sub_id,
                sid=sub_id,
                hidden="" if active else "hidden",
                body=body,
            )
        )
    return (
        '<div class="subtabs" data-subtabs>'
        '<div class="subtabs-nav" role="tablist" aria-label="子模块">{buttons}</div>'
        '<div class="subtabs-panels">{panels}</div>'
        '</div>'
    ).format(buttons="".join(nav_buttons), panels="".join(panels))


def render_tabs(block: dict, topic_path: Path, output: Path) -> str:
    groups = _normalize_groups(block)
    if not groups:
        return ""

    flat_items: list[dict] = []
    for grp in groups:
        for item in grp["items"]:
            flat_items.append(item)
    if not flat_items:
        return ""

    group_id = html.escape(block.get("id", "topic-tabs"))
    nav_groups: list[str] = []
    panels: list[str] = []

    flat_index = 0
    for grp_idx, grp in enumerate(groups):
        nav_buttons: list[str] = []
        for item in grp["items"]:
            index = flat_index
            tab_id = f"{group_id}-tab-{index + 1}"
            panel_id = f"{group_id}-panel-{index + 1}"
            active = index == 0
            title = item.get("title", f"模块 {index + 1}")
            desc = item.get("description", "")
            initial = f"{index + 1:02d}"
            body = ""
            if item.get("subtabs"):
                body = _render_subtabs(item["subtabs"], topic_path, panel_id, output)
            elif item.get("file"):
                body = markdown_to_html(read_md(topic_path.parent / item["file"], output))
            elif item.get("files"):
                body = "\n".join(
                    markdown_to_html(read_md(topic_path.parent / file, output))
                    for file in item["files"]
                )
            elif item.get("text"):
                body = markdown_to_html(item["text"])

            chip_html = _render_item_chips(item)
            mid = _stable_mid(item, group_id, index)
            level_attr = f' data-level="{html.escape(item.get("level", ""))}"' if item.get("level") else ""

            nav_buttons.append(
                '<button class="tab-button{active}" type="button" role="tab" id="{tab_id}" '
                'data-initial="{initial}" data-mid="{mid}"{level_attr} title="{title}" '
                'aria-controls="{panel_id}" aria-selected="{selected}">'
                '<span class="tab-progress" aria-hidden="true"></span>'
                '<span class="tab-text">'
                '<span class="tab-title">{title}</span>'
                '<span class="tab-desc">{desc}</span>'
                '</span>'
                '{chip_html}'
                '</button>'.format(
                    active=" active" if active else "",
                    tab_id=tab_id,
                    panel_id=panel_id,
                    mid=html.escape(mid),
                    level_attr=level_attr,
                    selected="true" if active else "false",
                    initial=html.escape(initial),
                    title=html.escape(title),
                    desc=html.escape(desc),
                    chip_html=chip_html,
                )
            )

            # 上一篇/下一篇（按扁平顺序）
            prev_btn = ""
            next_btn = ""
            if index > 0:
                prev_title = flat_items[index - 1].get("title", f"模块 {index}")
                prev_btn = (
                    '<button type="button" class="tab-step tab-step-prev" data-step-target="{i}">'
                    '<span class="tab-step-label">上一篇</span>'
                    '<span class="tab-step-title">{title}</span>'
                    '</button>'.format(i=index - 1 + 1, title=html.escape(prev_title))
                )
            if index < len(flat_items) - 1:
                next_title = flat_items[index + 1].get("title", f"模块 {index + 2}")
                next_btn = (
                    '<button type="button" class="tab-step tab-step-next" data-step-target="{i}">'
                    '<span class="tab-step-label">下一篇</span>'
                    '<span class="tab-step-title">{title}</span>'
                    '</button>'.format(i=index + 1 + 1, title=html.escape(next_title))
                )
            done_btn = (
                '<button type="button" class="tab-done" data-mid="{mid}" aria-pressed="false">'
                '<span class="tab-done-icon" aria-hidden="true">✓</span>'
                '<span class="tab-done-label">标记为已浏览</span>'
                '</button>'.format(mid=html.escape(mid))
            )
            last_seen = (
                '<div class="tab-last-seen" data-mid="{mid}" hidden>'
                '<span class="tab-last-seen-label">上次学习</span>'
                '<span class="tab-last-seen-value"></span>'
                '</div>'.format(mid=html.escape(mid))
            )
            chip_panel = chip_html.replace('class="tab-chips"', 'class="tab-panel-chips"', 1) if chip_html else ""

            panels.append(
                '<article class="tab-panel{active}" role="tabpanel" id="{panel_id}" '
                'aria-labelledby="{tab_id}" data-mid="{mid}" {hidden}>'
                '<div class="tab-panel-head">'
                '<div class="tab-panel-kicker">内容模块</div>'
                '<h2>{title}</h2>'
                '{chip_panel}'
                '</div>'
                '<div class="tab-panel-body">{body}</div>'
                '<div class="tab-panel-footer">'
                '{done_btn}'
                '{last_seen}'
                '<div class="tab-step-row">{prev_btn}{next_btn}</div>'
                '</div>'
                '</article>'.format(
                    active=" active" if active else "",
                    panel_id=panel_id,
                    tab_id=tab_id,
                    mid=html.escape(mid),
                    hidden="" if active else "hidden",
                    title=html.escape(title),
                    chip_panel=chip_panel,
                    body=body,
                    done_btn=done_btn,
                    last_seen=last_seen,
                    prev_btn=prev_btn,
                    next_btn=next_btn,
                )
            )
            flat_index += 1

        if grp.get("title"):
            grp_id = f"{group_id}-grp-{grp_idx + 1}"
            nav_groups.append(
                '<details class="tab-group" open data-group-id="{gid}">'
                '<summary class="tab-group-summary">'
                '<span class="tab-group-caret" aria-hidden="true">▾</span>'
                '<span class="tab-group-title">{title}</span>'
                '<span class="tab-group-meta"><span class="tab-group-count">{count}</span></span>'
                '</summary>'
                '<div class="tab-group-items">{buttons}</div>'
                '</details>'.format(
                    gid=html.escape(grp_id),
                    title=html.escape(grp["title"]),
                    count=len(grp["items"]),
                    buttons="".join(nav_buttons),
                )
            )
        else:
            nav_groups.append(f'<div class="tab-group tab-group-flat">{"".join(nav_buttons)}</div>')

    has_levels = any(item.get("level") for item in flat_items)
    level_filter = ""
    if has_levels:
        level_filter = (
            '<div class="tabs-level-filter" role="group" aria-label="按级别筛选">'
            '<button type="button" class="level-chip active" data-level="all">全部</button>'
            '<button type="button" class="level-chip" data-level="基础">基础</button>'
            '<button type="button" class="level-chip" data-level="进阶">进阶</button>'
            '<button type="button" class="level-chip" data-level="精通">精通</button>'
            '</div>'
        )

    return (
        '<section class="tabs-shell" data-tabs data-tabs-id="{gid}">'
        '<div class="tabs-toolbar">'
        '<button class="module-toggle" type="button" aria-pressed="false">折叠模块</button>'
        '<div class="module-current"><span>当前模块</span><strong></strong></div>'
        '<div class="module-progress"><span class="module-progress-label">学习进度</span>'
        '<span class="module-progress-bar"><span class="module-progress-fill" style="width:0%"></span></span>'
        '<span class="module-progress-text">0 / {total}</span></div>'
        '<div class="module-actions">'
        '<button type="button" class="module-action" data-action="export" title="导出本页学习进度为 JSON">导出</button>'
        '<button type="button" class="module-action" data-action="import" title="从 JSON 文件导入学习进度">导入</button>'
        '<button type="button" class="module-action module-action-danger" data-action="reset" title="清空本页学习进度">重置</button>'
        '<input type="file" class="module-import-input" accept="application/json,.json" hidden>'
        '</div>'
        '</div>'
        '<div class="tabs-nav">'
        '<div class="module-resizer" role="separator" aria-orientation="vertical" aria-label="拖动调整模块导航宽度" title="拖动调整宽度"></div>'
        '<button class="module-collapse" type="button" aria-pressed="false" title="折叠模块导航">‹</button>'
        '<div class="tabs-nav-head">'
        '<div><div class="tabs-kicker">Module Switcher</div><div class="tabs-title">{title}</div></div>'
        '<input class="tabs-filter" type="search" placeholder="搜索模块..." aria-label="搜索内容模块">'
        '{level_filter}'
        '</div>'
        '<div class="tabs-list" role="tablist" aria-label="{title}">{groups}</div>'
        '</div>'
        '<div class="tabs-panels">{panels}</div>'
        "</section>"
    ).format(
        gid=group_id,
        total=len(flat_items),
        title=html.escape(block.get("title", "内容模块")),
        level_filter=level_filter,
        groups="".join(nav_groups),
        panels="".join(panels),
    )


def render_layout_block(block: dict, topic_path: Path, output: Path) -> str:
    block_type = block.get("type", "section")
    if block_type == "tabs":
        return render_tabs(block, topic_path, output)
    if block_type == "overview":
        return render_overview(block)
    if block_type == "path":
        return render_path(block)
    if block_type == "grid":
        return render_grid(block, topic_path, output)
    if block_type == "callout":
        return render_callout(block)
    if block_type == "resources":
        return render_resources(block, output)
    return render_section(block, topic_path, output)


def _topic_progress_meta(topic: dict) -> tuple[str, int]:
    """返回该 topic 对应的 (progressKey, totalItems)，用于首页跨页面汇总。"""
    topic_path = ROOT / topic["source"]
    try:
        data = json.loads(topic_path.read_text(encoding="utf-8"))
    except Exception:
        return "", 0
    layout = data.get("layout") or []
    total = 0
    tabs_id = ""
    for block in layout:
        if block.get("type") != "tabs":
            continue
        if not tabs_id:
            tabs_id = block.get("id", "topic-tabs")
        for grp in (block.get("groups") or []):
            total += len(grp.get("items") or [])
        total += len(block.get("items") or [])
    output = topic.get("output", "")
    pathname = "/" + output if output and not output.startswith("/") else output
    progress_key = f"doctor-study-progress::{pathname}#{tabs_id or 'tabs'}"
    return progress_key, total


def _render_home_nav() -> str:
    links = [
        '<a href="#study-tracks">5 条主线</a>',
        '<a href="pages/cs-basics/index.html">计算机与系统基础</a>',
        '<a href="pages/ai-infra/gpu/index.html">GPU</a>',
        '<a href="pages/ai-infra/llm-inference/index.html">LLM 推理</a>',
        '<a href="pages/ai-infra/papers/index.html">论文项目</a>',
    ]
    return "\n".join(links)


def _render_home_lanes() -> str:
    lanes = []
    for index, track in enumerate(TRACKS, 1):
        topics = topics_in_track(track)
        topic_titles = " / ".join(topic["title"] for topic in topics)
        lanes.append(
            '<article>'
            f'<span>{index:02d}</span>'
            f'<h3>{html.escape(track["label"])}</h3>'
            f'<p>{html.escape(track.get("description", ""))}</p>'
            f'<div class="idx-lane-links">{html.escape(topic_titles)}</div>'
            '</article>'
        )
    return "\n".join(lanes)


def _render_home_tracks(card_template: str) -> str:
    sections = []
    for track in TRACKS:
        all_topics = topics_in_track(track)
        home_max = track.get("home_max", 0)
        if home_max and len(all_topics) > home_max:
            visible_topics = all_topics[:home_max]
            more_href = track.get("home_more_href", all_topics[0]["output"])
            more_label = track.get("home_more_label", f"查看全部 {len(all_topics)} 个模块 →")
        else:
            visible_topics = all_topics
            more_href = ""
            more_label = ""
        cards = "\n\n".join(topic_card_from_template(topic, card_template) for topic in visible_topics)
        if not cards:
            continue
        more_link = f'<a class="idx-track-more" href="{html.escape(more_href)}">{html.escape(more_label)}</a>' if more_href else ""
        sections.append(
            '<section class="idx-track" aria-label="{label}">'
            '<div class="idx-track-head">'
            '<span>{eyebrow}</span>'
            '<h2>{label}</h2>'
            '<p>{description}</p>'
            '</div>'
            '<div class="idx-track-cards">'
            '{cards}'
            '</div>'
            '{more}'
            '</section>'.format(
                label=html.escape(track["label"]),
                eyebrow=html.escape(track.get("eyebrow", "")),
                description=html.escape(track.get("description", "")),
                cards=cards,
                more=more_link,
            )
        )
    return "\n\n".join(sections)


def topic_card_from_template(topic: dict, card_template: str) -> str:
    tags = "".join(f"<span>{html.escape(tag)}</span>" for tag in topic.get("tags", []))
    progress_key, progress_total = _topic_progress_meta(topic)
    card = card_template.replace("{{color}}", html.escape(topic.get("color", "c1")))
    card = card.replace("{{href}}", html.escape(topic["output"]))
    card = card.replace("{{title}}", html.escape(topic["title"]))
    card = card.replace("{{description}}", html.escape(topic.get("description", "")))
    card = card.replace("{{tags}}", tags)
    card = card.replace("{{progress_key}}", html.escape(progress_key))
    card = card.replace("{{progress_total}}", str(progress_total))
    return card


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
    page = page.replace("{{top_nav}}", render_top_nav(output))
    page = page.replace("{{side_nav}}", render_side_nav(output, output))
    page = page.replace("{{home_path}}", rel_link(output, "index.html"))
    page = page.replace("{{css_path}}", asset_link(output, "assets/style.css"))
    page = page.replace("{{script_path}}", asset_link(output, "assets/script.js"))
    output.write_text(page, encoding="utf-8")
    return output


def _count_qa_blocks() -> int:
    """统计所有 Markdown 内容文件中的 QA 问答块数量。"""
    count = 0
    qa_re = re.compile(r'<div\s+class="qa"', re.IGNORECASE)
    for md_file in CONTENT.rglob("*.md"):
        if md_file.name == "STYLE_GUIDE.md":
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            count += len(qa_re.findall(text))
        except Exception:
            continue
    return count


def _count_total_modules() -> int:
    """统计所有 topic 中 tabs 的模块总数。"""
    total = 0
    for topic in SITE.get("topics", []):
        _, n = _topic_progress_meta(topic)
        total += n
    return total


def render_index() -> Path:
    output = ROOT / "index.html"
    card_template = (TEMPLATES / "topic-card.html").read_text(encoding="utf-8")

    topics = SITE.get("topics", [])
    cards = [topic_card_from_template(topic, card_template) for topic in topics]
    qa_count = _count_qa_blocks()
    module_count = _count_total_modules()
    template = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    page = template.replace("{{title}}", html.escape(SITE["title"]))
    page = page.replace("{{subtitle}}", html.escape(SITE.get("subtitle", "")))
    page = page.replace("{{topic_cards}}", "\n\n".join(cards))
    page = page.replace("{{home_nav}}", _render_home_nav())
    page = page.replace("{{track_count}}", str(len(TRACKS)))
    page = page.replace("{{topic_count}}", str(len(topics)))
    page = page.replace("{{qa_count}}", str(qa_count))
    page = page.replace("{{module_count}}", str(module_count))
    page = page.replace("{{home_lanes}}", _render_home_lanes())
    page = page.replace("{{home_tracks}}", _render_home_tracks(card_template))
    page = page.replace("{{css_path}}", asset_link(output, "assets/style.css"))
    page = page.replace("{{script_path}}", asset_link(output, "assets/script.js"))
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
