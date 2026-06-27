# doctor-study Agent 操作手册

## 项目定位

本项目用于毕业期间的面试、项目、简历准备和学习沉淀。当前核心内容是 AI Infra 面试准备，后续会继续扩展到简历、项目深挖、计算机基础、行为面 STAR 案例等方向。

新 agent 进入项目后，应把本项目视为一个静态学习站点，而不是普通手写 HTML 项目。内容源在 `content/`，HTML 页面由 `tools/build_site.py` 生成。

新 agent 进入项目后必须先读：

1. `AGENTS.md`：项目操作手册。
2. `content/STYLE_GUIDE.md`：Markdown 内容写作模板和章节类型规范。

## 快速启动

```bash
uv run python tools/build_site.py
uv run python -m http.server 8000
```

本地预览地址：

```text
http://localhost:8000/
```

如需进入虚拟环境：

```bash
source .venv/bin/activate
```

## 核心原则

1. 优先编辑 `content/`，不要直接编辑生成后的 `pages/**/*.html` 或 `index.html`。
2. 一个 Markdown 文件只负责一个章节或一个小知识点，避免形成超大文件。
3. 修改任何内容源、模板或脚本后，都必须运行 `uv run python tools/build_site.py`。
4. `index.html` 和 `pages/**/*.html` 是生成产物，但需要提交到 git，方便 GitHub Pages 静态展示。
5. 删除主题或章节时，要同时删除内容源、配置注册项和旧生成产物。
6. 不要提交 `.venv/`、`__pycache__/`、`*.pyc` 等本地环境文件。
7. 每次实质性修改完成并通过验证后，必须将变更 commit 并 push 到远程 GitHub（`main` 分支），保持远程仓库始终是最新状态。commit message 使用中文，简要概括本次改动内容。

## 当前架构

- `AGENTS.md`：本操作手册，新 agent 进入项目后先读这里。
- `content/`：唯一优先编辑的内容源，按 `domain/topic/*.md` 拆分知识点。
- `content/STYLE_GUIDE.md`：Markdown 内容写作规范，新建或重写内容时必须遵循。
- `content/site.json`：站点导航、首页主题卡片配置和 TRACKS 分类入口。
- `content/**/topic.json`：单个主题页的标题、摘要、输出路径、layout 布局和章节顺序。
- `templates/index.html`：首页结构模板（Hero 区、Lanes、Track 卡片列表）。
- `templates/page.html`：主题页结构模板（侧栏、tabs 工作台、内容区）。
- `templates/topic-card.html`：首页主题卡片模板。
- `tools/build_site.py`：静态页面生成脚本（纯 Python 标准库，零外部依赖）。
- `pages/`：生成后的可浏览 HTML 页面，不要手动编辑。
- `resources/`：项目资料资源目录（论文 PDF、图片、slides 等）。
- `assets/style.css`：全站共享样式（含暗色模式、设计 tokens、卡片变体）。
- `assets/script.js`：全站共享交互逻辑（夜间模式、目录抽屉、QA 展开、进度追踪、侧栏折叠）。
- `index.html`：由 `tools/build_site.py` 生成的首页。
- `.github/workflows/pages.yml`：GitHub Pages 自动部署 CI（push 到 main 自动构建+部署）。
- `pyproject.toml`：Python 项目配置（本地开发用 uv 管理）。
- `uv.lock`：uv 锁文件。
- `.venv/`：本地虚拟环境，不提交。

## 外部 CDN 依赖

页面通过 CDN 加载以下资源（在 `templates/page.html` 中引用），GitHub Pages 部署时不需要本地安装：

- **KaTeX**：数学公式渲染（CSS + JS 两个文件）。
- **PrismJS**：代码语法高亮（核心 JS + 多语言组件 + 浅色/暗色两套主题 CSS）。
  - 支持语言：go、python、json、yaml、bash、cpp、sql、markup、css。
  - 暗色模式通过 JS 动态切换 `disabled` 属性实现。

Favicon 使用内联 SVG data URI，不需要额外文件。

## TRACKS 分类体系

构建脚本中定义了 5 条复习主线（TRACKS），首页 Lane 卡片、顶部导航下拉、主题页侧栏三处共用，避免分类逻辑漂移：

1. **计算机基础**（foundation_cards）：`cs-basics`
2. **AI Infra 核心系统**（systems_cards）：`ai-infra/transformer`、`ai-infra/gpu`
3. **调度与集群**（scheduling_cards）：`ai-infra/scheduling`、`ai-infra/kubernetes`、`ai-infra/cluster-management`
4. **推理 / 训练 / 性能**（serving_training_cards）：`ai-infra/llm-inference`、`ai-infra/distributed-training`、`ai-infra/performance-prediction`
5. **论文项目与 Agent**（interview_expression_cards）：`ai-infra/papers`、`ai-infra/agent`

新增主题时需注意分配到正确的 TRACK（通过 `content/site.json` 中 topic 的 `slug` 字段匹配）。

## 推荐内容树

```text
content/
  site.json
  ai-infra/
    papers/
    gpu/
    transformer/
    llm-inference/
    kubernetes/
    scheduling/
    cluster-management/
    distributed-training/
    performance-prediction/
    agent/
  cs-basics/
    golang/
    os/
    networking/
    computer-architecture/
    programming-systems/
    linux-container/
    distributed-ai/
    linux-kernel-ai/
```

## 资源目录约定

`resources/` 用于存放内容源之外的资料文件。Markdown 中可以用相对路径引用这些资料，例如从生成页引用站点根目录下的 `resources/papers/example.pdf`。

推荐结构：

```text
resources/
  papers/      # 论文 PDF、arXiv 版本、会议论文原文
  books/       # 书籍、教材、长文档
  slides/      # PPT、PDF slides、答辩材料
  images/      # 截图、示意图、照片、页面配图
  diagrams/    # drawio、svg、架构图源文件
  datasets/    # 小型样例数据、表格、实验摘要
  resume/      # 简历 PDF、岗位 JD、简历素材
  raw/         # 临时原始输入材料，等待整理进 content/
  exports/     # 导出产物、临时报告、可分享附件
  private/     # 隐私材料，本目录被 .gitignore 忽略
```

提交规则：

- 可以提交公开或可分享资料，例如论文 PDF、公开 slides、自己绘制的图片。
- 不要提交隐私资料，例如身份证明、未公开简历版本、内部文档、含 token 的文件。
- 隐私资料统一放入 `resources/private/`，该目录被 `.gitignore` 忽略。
- 大文件进入仓库前要谨慎；如果资料过大，优先只在 `content/` 中记录来源链接或说明本地路径。
- 空资源目录通过 `.gitkeep` 保留，方便后续直接放文件。

## `content/site.json` 字段说明

`content/site.json` 控制首页、导航和主题卡片。

```json
{
  "title": "doctor-study",
  "subtitle": "毕业准备 · 面试 / 项目 / 简历 / 学习笔记总入口",
  "nav": [
    {"title": "首页", "href": "index.html"},
    {"title": "GPU", "href": "pages/ai-infra/gpu/index.html"}
  ],
  "topics": [
    {
      "title": "GPU 硬件与资源共享",
      "slug": "ai-infra/gpu",
      "source": "content/ai-infra/gpu/topic.json",
      "output": "pages/ai-infra/gpu/index.html",
      "description": "首页卡片描述",
      "tags": ["gpu", "hardware"],
      "color": "c2"
    }
  ]
}
```

字段含义：

- `title`：站点标题。
- `subtitle`：首页副标题。
- `nav`：所有页面顶部导航。`href` 必须指向真实存在的生成页面或首页。
- `topics`：首页主题卡片列表，也是构建脚本遍历生成页面的入口。
- `topics[].title`：首页卡片标题和主题页标题来源之一。
- `topics[].slug`：逻辑路径，建议与 `content/<domain>/<topic>` 对齐，同时用于 TRACKS 分类匹配。
- `topics[].source`：该主题的 `topic.json` 路径。
- `topics[].output`：生成后的 HTML 输出路径。
- `topics[].description`：首页卡片描述。
- `topics[].tags`：首页卡片标签。
- `topics[].color`：首页卡片颜色 class，可选 `c1`、`c2`、`c3`、`c4`、`c5`。

## `topic.json` 字段说明

每个主题目录都必须有一个 `topic.json`。

```json
{
  "title": "GPU 硬件与资源共享",
  "subtitle": "硬件架构 · 显存带宽 · GPU 互联",
  "output": "pages/ai-infra/gpu/index.html",
  "tags": ["gpu", "hardware"],
  "goals": ["理解 GPU 架构差异", "掌握 MIG/MPS 区别"],
  "layout": [
    {"type": "tabs", "title": "GPU 内容模块", "items": [...]}
  ]
}
```

字段含义：

- `title`：主题页主标题。
- `subtitle`：主题页副标题。
- `output`：主题页生成路径，必须和 `content/site.json` 中对应 topic 的 `output` 保持一致。
- `tags`：可选。主题页 Hero 区显示的标签。
- `goals`：可选。主题页 Hero 区显示的学习目标。
- `sections`：兼容字段。章节数组，当 `layout` 不存在时回退为线性渲染。
- `layout`：推荐使用。结构化页面布局；如果存在，优先使用 `layout`，否则回退到 `sections`。

### 可用卡片样式

- `card-m`：蓝色主线，适合主要概念、核心方案。
- `card-d`：绿色，适合对比、实践经验、正向结论。
- `card-s`：紫色，适合结构化说明、系统组件。
- `card-w`：黄色，适合注意事项、风险、面试重点。
- `card-r`：红色，适合错误案例、反例、危险点。

## 结构化布局组件

推荐新页面优先使用 `layout`，避免页面变成只会向下生长的 Markdown 长文。内容较多的主题优先使用 `tabs`，让用户在同一页面内切换模块，而不是把所有内容一次性纵向铺开。

可用组件：

- **`tabs`**：标签页工作台，大主题的主内容组织方式。一次只展示一个内容模块，支持进度追踪（localStorage）、模块搜索、难度/耗时标签、上一个/下一个导航、标记已完成。
  - `tabs.items[].file`：当前主题目录下的 Markdown 文件。
  - `tabs.items[].level`：难度标签，可选 `"基础"`、`"进阶"`、`"精通"`。
  - `tabs.items[].priority`：重要程度星级（1-3）。
  - `tabs.items[].time`：预计阅读时间（分钟）。
  - `tabs.items[].subtabs`：可选二级标签页，在一个模块内再做分组（如"核心概念"、"面试题"）。
  - `tabs.groups`：可选分组信息，按组将模块归类显示。
- **`overview`**：概览卡片区，适合核心概念、面试重点、易错点、关联页面。
- **`path`**：学习路径，适合展示推荐阅读顺序。
- **`grid`**：模块网格，适合把多个 Markdown 内容块并排展示。
- **`section`**：普通章节，适合完整长文内容。
- **`callout`**：提示块，适合面试建议、注意事项、风险点。`tone` 可选 `note`、`warn`、`danger`。
- **`resources`**：资料区，适合链接到 `resources/` 中的论文、图片、slides。`href` 可以是外部链接，也可以是项目内路径。

组件规则：

- `tabs.items[].file` 和 `grid.items[].file` 都指向当前主题目录下的 Markdown 文件。
- `grid.items[].card` 可使用 `card-m`、`card-d`、`card-s`、`card-w`、`card-r`。
- 如果 `layout` 存在，生成器不会自动渲染 `sections`；`sections` 可保留作为兼容索引。
- 不要为了凑页面效果默认添加"本页重点""推荐学习路径"等摘要块；只有用户明确需要时再加。

### tabs 模块进度追踪

`tabs` 工作台自动支持：

- 模块完成状态（勾选圆圈）写入 localStorage。
- 顶部进度条显示已完成/总数。
- 模块搜索过滤。
- 难度（基础/进阶/精通）、重要度（★☆☆）、预计时间（⌚ 8 min）三种 chip 标签。
- Prev/Next 导航按钮在模块间跳转。
- 侧边栏 TRACK 图标导航，点击展开/折叠可切换侧栏宽度。

## Markdown 内容约定

生成器支持常用轻量 Markdown：

- 段落：普通文本，空行分段。
- 加粗：`**重点**`。
- 行内代码：`` `code` ``。
- 无序列表：`- item` 或 `* item`。
- 有序列表：`1. item`。
- 表格：标准 Markdown 表格（需包裹在 `.table-scroll` div 中适配移动端）。
- 代码块：三反引号代码块，支持语言标注（go/python/cpp/sql/yaml/bash/json/markup/css）。
- 原始 HTML：允许直接写 HTML，例如 `.qa` 问答块、复杂表格或特殊布局。

问答块示例：

```html
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 这里写问题？</div>
<div class="qa-a"><p>这里写回答。</p></div>
</div>
```

页面内按 `Alt + E` 可展开或折叠全部 `.qa`。

## 新增主题流程

例如新增 `content/ai-infra/networking/`：

1. 创建目录：

```bash
mkdir -p content/ai-infra/networking
```

2. 创建章节文件：

```text
content/ai-infra/networking/
  topic.json
  01-overview.md
  02-rdma.md
```

3. 编写 `topic.json`，推荐使用 `layout` + `tabs`：

```json
{
  "title": "AI Infra 网络基础",
  "subtitle": "RDMA · NCCL · 拓扑 · 拥塞控制",
  "output": "pages/ai-infra/networking/index.html",
  "tags": ["networking", "rdma", "nccl"],
  "layout": [
    {
      "type": "tabs",
      "title": "网络基础模块",
      "items": [
        {"title": "网络基础总览", "file": "01-overview.md", "level": "基础"},
        {"title": "RDMA 与 NCCL", "file": "02-rdma.md", "level": "进阶"}
      ]
    }
  ]
}
```

4. 在 `content/site.json` 的 `nav` 中追加导航项：

```json
{"title": "网络基础", "href": "pages/ai-infra/networking/index.html"}
```

5. 在 `content/site.json` 的 `topics` 中追加主题卡片：

```json
{
  "title": "AI Infra 网络基础",
  "slug": "ai-infra/networking",
  "source": "content/ai-infra/networking/topic.json",
  "output": "pages/ai-infra/networking/index.html",
  "description": "RDMA、NCCL、拓扑、拥塞控制等 AI Infra 网络知识。",
  "tags": ["networking", "rdma", "nccl"],
  "color": "c4"
}
```

6. 如需将主题归入已有 TRACK，在 `tools/build_site.py` 的 `TRACKS` 常量对应 track 的 `slugs` 中添加 slug。

7. 构建并预览：

```bash
uv run python tools/build_site.py
uv run python -m http.server 8000
```

## 新增章节流程

1. 在对应主题目录新增章节 Markdown，例如：

```text
content/ai-infra/gpu/03-topology.md
```

2. 如果使用 `sections` 模式，在对应 `topic.json` 的 `sections` 末尾追加：

```json
{"title": "GPU 拓扑", "file": "03-topology.md", "card": "card-s"}
```

3. 如果使用 `layout` + `tabs` 模式，在 `tabs.items` 数组中追加模块。

4. 运行构建：

```bash
uv run python tools/build_site.py
```

5. 打开对应页面确认目录和内容展示正常。

## 修改内容流程

1. 根据用户需求定位到 `content/<domain>/<topic>/`。
2. 修改对应 Markdown 文件。
3. 如果新增、删除或调整章节/模块顺序，同时修改 `topic.json`。
4. 运行：

```bash
uv run python tools/build_site.py
```

5. 检查生成后的页面。

不要直接修改生成后的 `pages/**/*.html` 或 `index.html`。如果发现生成 HTML 不符合预期，应修改内容源、模板或生成脚本。

## 删除章节流程

1. 从对应 `topic.json.sections` 或 `layout[].items` 中删除该章节/模块记录。
2. 删除对应 Markdown 文件。
3. 运行：

```bash
uv run python tools/build_site.py
```

4. 检查页面目录中不再出现该章节。

## 删除主题流程

1. 从 `content/site.json.nav` 删除导航项。
2. 从 `content/site.json.topics` 删除主题项。
3. 如果主题在 `tools/build_site.py` 的 TRACKS 中，从对应 track 的 `slugs` 列表移除。
4. 删除 `content/<domain>/<topic>/` 源目录。
5. 删除旧生成产物目录，例如：

```bash
rm -rf pages/ai-infra/networking
```

6. 运行：

```bash
uv run python tools/build_site.py
```

7. 检查首页卡片、顶部导航和内部链接。

注意：当前 `tools/build_site.py` 不会自动清理已删除主题的旧 HTML 产物，所以删除主题时必须手动清理对应 `pages/...` 目录。

## 修改页面结构或样式

只在以下文件中修改结构和样式：

- `templates/index.html`：首页结构模板（Hero、Lanes、Track 卡片、Footer）。
- `templates/page.html`：主题页结构模板（侧栏、tabs 工作台、代码高亮主题切换）。
- `templates/topic-card.html`：首页主题卡片模板。
- `assets/style.css`：视觉样式（CSS 自定义属性、暗色模式、卡片、响应式）。
- `assets/script.js`：夜间模式、目录抽屉、QA 展开、进度追踪、侧栏折叠等交互。
- `tools/build_site.py`：生成逻辑、TRACKS 定义、markdown 解析。

修改后运行：

```bash
uv run python tools/build_site.py
```

## 目录和交互规则

- 夜间模式按钮由 `assets/script.js` 自动注入顶部导航。
- 主题选择会写入 `localStorage`，键名为 `doctor-study-theme`。
- 未手动选择时，页面跟随系统 `prefers-color-scheme`。
- 代码高亮（PrismJS）的浅色/暗色主题与全站夜间模式同步切换。
- 长页面目录由 `assets/script.js` 自动从 `<h2>` 或 `<h3>` 生成。
- 目录默认隐藏，通过右下角 `目录` 按钮打开。
- 点击目录链接、遮罩或关闭按钮会关闭目录。
- 按 `Escape` 会关闭目录。
- 问答块 `.qa` 可点击展开。
- 按 `Alt + E` 可展开或折叠当前页面全部 `.qa`。
- tabs 模块进度（完成状态）写入 localStorage，键名为 `doctor-study-progress`。
- 侧栏折叠状态写入 localStorage，键名为 `doctor-study-sidebar`。

## GitHub Pages 部署

项目通过 `.github/workflows/pages.yml` 自动部署到 GitHub Pages：

- **触发条件**：push 到 `main` 分支，或手动触发（workflow_dispatch）。
- **构建环境**：ubuntu-latest + Python 3.13，纯标准库（不需要 uv 或 pip install）。
- **CI 步骤**：
  1. `python tools/build_site.py` — 生成 HTML。
  2. `python -m py_compile tools/build_site.py` — Python 语法检查。
  3. 内部链接检查 — 验证所有 `<a href>` 指向的文件存在。
  4. 产物存在性检查 — 确认 index.html、assets/、pages/ 都已生成。
  5. 准备 artifact — 复制 index.html、assets/、pages/、resources/ 到 `_site/`，添加 `.nojekyll`。
  6. 上传 artifact 并通过 `actions/deploy-pages@v4` 部署。
- **所有 run 步骤均使用 `set -euo pipefail`**，任何一步失败立即终止构建。
- 本地验证后再 push，避免 CI 失败。

## 验证清单

每次实质性修改后至少执行：

```bash
uv run python tools/build_site.py
git status --short
```

涉及 Python 脚本修改时执行：

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python -m py_compile tools/build_site.py
```

建议执行内部链接检查（与 CI 中一致）：

```bash
uv run python - <<'PY'
from pathlib import Path
from html.parser import HTMLParser

root = Path('.')
missing = []

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get('href') if tag == 'a' else None
        if href and not href.startswith(('#', 'http:', 'https:', 'mailto:', 'javascript:', 'data:')):
            self.hrefs.append(href.split('#', 1)[0])

for path in [root / 'index.html', *sorted((root / 'pages').rglob('*.html'))]:
    parser = Parser()
    parser.feed(path.read_text(encoding='utf-8'))
    for href in parser.hrefs:
        target = (path.parent / href).resolve()
        if not target.exists():
            missing.append(f'{path} -> {href}')

if missing:
    print('\n'.join(missing))
    raise SystemExit(1)
print('all html links ok')
PY
```

启动预览：

```bash
uv run python -m http.server 8000
```

## Git 与发布规则

- 修改完成、构建验证通过后，主动执行 `git add -A && git commit -m "中文描述" && git push`，推送到远程 `main` 分支。
- commit message 使用中文，简洁概括本次改动要点（如"feat: 补充论文面试问答"、"fix: 修复表格溢出"）。
- 提交前先查看：

```bash
git status --short
git diff --stat
```

- `.venv/`、`__pycache__/`、`*.pyc` 不应出现在 git 中。
- `content/`、`templates/`、`tools/`、`assets/`、`resources/`、`index.html`、`pages/`、`.github/workflows/` 都需要提交。
- `pages/` 和 `index.html` 虽然是生成产物，但当前静态站点展示依赖它，因此不要加入 `.gitignore`。
- 不要运行 `git reset --hard`、`git push --force` 等破坏性命令，除非用户明确要求。

## 禁止事项

- 不要把新内容直接写进 `pages/**/*.html` 或 `index.html`。
- 不要把具体学习内容写进 `templates/`。
- 不要让单个 Markdown 文件无限膨胀；内容多时继续拆文件。
- 不要删除用户未确认要删除的内容。
- 不要运行 `git reset --hard`、`git push --force` 等破坏性命令，除非用户明确要求。
- 不要提交 `.venv/` 或 Python 缓存。
- 不要在不更新 `content/site.json` 和 TRACKS 的情况下新增主题。
- 不要在修改模板或 CSS 后忘记重新构建。

## Agent 标准工作流

1. 先读 `AGENTS.md` 和 `content/site.json`。
2. 涉及内容新增、重写、重组或 Markdown 格式统一时，先读 `content/STYLE_GUIDE.md`。
3. 判断需求属于新增主题、新增章节、修改内容、删除内容、样式调整还是构建发布。
4. 定位并编辑 `content/`、`templates/`、`assets/` 或 `tools/` 中的最小必要文件。
5. 运行 `uv run python tools/build_site.py` 重新生成。
6. 运行 Python 语法检查和内部链接检查。
7. 检查生成页面、预览效果和 `git status --short`。
8. 用简短总结告诉用户改了什么、如何预览。
9. 执行 `git add -A && git commit -m "中文描述" && git push`，将所有变更推送到远程 `main` 分支。
