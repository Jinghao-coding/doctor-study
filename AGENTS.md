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

1. 优先编辑 `content/`，不要直接编辑生成后的 `pages/**/*.html`。
2. 一个 Markdown 文件只负责一个章节或一个小知识点，避免再次形成超大文件。
3. 修改任何内容源、模板或脚本后，都必须运行 `uv run python tools/build_site.py`。
4. `index.html` 和 `pages/**/*.html` 是生成产物，但需要提交到 git，方便 GitHub 静态展示。
5. 删除主题或章节时，要同时删除内容源、配置注册项和旧生成产物。
6. 不要提交 `.venv/`、`__pycache__/`、`*.pyc` 等本地环境文件。
7. 未经用户要求，不要自动 commit、push 或重写历史。

## 当前架构

- `AGENTS.md`：本操作手册，新 agent 进入项目后先读这里。
- `content/`：唯一优先编辑的内容源，按 `domain/topic/*.md` 拆分知识点。
- `content/STYLE_GUIDE.md`：Markdown 内容写作规范，新建或重写内容时必须遵循。
- `content/site.json`：站点导航和首页主题卡片配置。
- `content/**/topic.json`：单个主题页的标题、摘要、输出路径和章节顺序。
- `templates/`：HTML 模板，不要把具体学习内容写在这里。
- `tools/build_site.py`：静态页面生成脚本。
- `pages/`：生成后的可浏览 HTML 页面，默认不要手动编辑。
- `resources/`：项目资料资源目录，用于存放论文、图片、幻灯片、简历附件、原始素材等。
- `assets/style.css`：全站共享样式。
- `assets/script.js`：全站共享交互逻辑，例如夜间模式、目录抽屉和 QA 展开。
- `index.html`：由 `tools/build_site.py` 生成的首页。
- `pyproject.toml`：Python 项目配置。
- `uv.lock`：uv 锁文件。
- `.venv/`：本地虚拟环境，不提交。

## 推荐内容树

```text
content/
  site.json
  ai-infra/
    papers/
      topic.json
      01-*.md
      02-*.md
    gpu/
    llm-inference/
    kubernetes/
    scheduling/
    cluster-management/
    performance-prediction/
    system-design/
  resume/
  projects/
  cs-basics/
  behavior-interview/
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

生成产物对应为：

```text
pages/
  ai-infra/
    papers/index.html
    gpu/index.html
    llm-inference/index.html
    kubernetes/index.html
```

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
- `topics[].slug`：逻辑路径，建议与 `content/<domain>/<topic>` 对齐。
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
  "sections": [
    {
      "title": "GPU 硬件基础",
      "file": "01-hardware.md",
      "card": "card-s"
    }
  ]
}
```

字段含义：

- `title`：主题页主标题。
- `subtitle`：主题页副标题。
- `output`：主题页生成路径，必须和 `content/site.json` 中对应 topic 的 `output` 保持一致。
- `sections`：章节数组，顺序就是页面展示顺序。
- `sections[].title`：章节标题，会生成 `<h2>`。
- `sections[].file`：章节 Markdown 文件名，相对于当前 `topic.json` 所在目录。
- `sections[].card`：可选。填了会把该章节内容包进卡片；不填则直接渲染内容。
- `tags`：可选。主题页 Hero 区显示的标签。
- `goals`：可选。主题页 Hero 区显示的学习目标。
- `layout`：可选。结构化页面布局；如果存在，优先使用 `layout`，否则回退到 `sections` 线性渲染。

可用卡片样式：

- `card-m`：蓝色主线，适合主要概念、核心方案。
- `card-d`：绿色，适合对比、实践经验、正向结论。
- `card-s`：紫色，适合结构化说明、系统组件。
- `card-w`：黄色，适合注意事项、风险、面试重点。
- `card-r`：红色，适合错误案例、反例、危险点。

## 结构化布局组件

推荐新页面优先使用 `layout`，避免页面变成只会向下生长的 Markdown 长文。内容较多的主题优先使用 `tabs`，让用户在同一页面内切换模块，而不是把所有内容一次性纵向铺开。

示例：

```json
{
  "title": "LLM 推理系统",
  "subtitle": "Prefill/Decode · KV 缓存 · 推理引擎",
  "tags": ["llm", "inference", "kv-cache"],
  "goals": ["理解 prefill/decode 差异", "掌握 KV cache 瓶颈"],
  "layout": [
    {
      "type": "overview",
      "title": "本页重点",
      "items": [
        {"label": "核心链路", "value": "请求进入 → prefill → decode → 流式返回"}
      ]
    },
    {
      "type": "path",
      "title": "推荐学习路径",
      "items": [
        {"title": "先拆推理流程", "desc": "理解 prefill 与 decode 的性能差异。"}
      ]
    },
    {
      "type": "grid",
      "title": "核心模块",
      "items": [
        {"title": "KV 缓存", "description": "理解 KV cache 资源模型。", "file": "02-kv.md", "card": "card-w"}
      ]
    },
    {
      "type": "callout",
      "tone": "warn",
      "title": "高频易错点",
      "items": ["不要把 prefill 和 decode 的瓶颈混为一谈。"]
    }
  ]
}
```

可用组件：

- `tabs`：标签页工作台，适合大主题的主内容组织；一次只展示一个内容模块。
- `overview`：概览卡片区，适合核心概念、面试重点、易错点、关联页面。
- `path`：学习路径，适合展示推荐阅读顺序。
- `grid`：模块网格，适合把多个 Markdown 内容块并排展示。
- `section`：普通章节，适合完整长文内容。
- `callout`：提示块，适合面试建议、注意事项、风险点。
- `resources`：资料区，适合链接到 `resources/` 中的论文、图片、slides。

组件规则：

- `tabs.items[].file` 指向当前主题目录下的 Markdown 文件；默认推荐用 `tabs` 承载真实学习内容。
- `grid.items[].file` 指向当前主题目录下的 Markdown 文件。
- `grid.items[].card` 可使用 `card-m`、`card-d`、`card-s`、`card-w`、`card-r`。
- `callout.tone` 可使用 `note`、`warn`、`danger`。
- `resources.items[].href` 可以是外部链接，也可以是项目内路径，如 `resources/papers/example.pdf`。
- 如果 `layout` 存在，生成器不会自动渲染 `sections`；`sections` 可保留作为兼容索引。
- 不要为了凑页面效果默认添加“本页重点”“推荐学习路径”等摘要块；只有用户明确需要时再加。

## Markdown 内容约定

生成器支持常用轻量 Markdown：

- 段落：普通文本，空行分段。
- 加粗：`**重点**`。
- 行内代码：`` `code` ``。
- 无序列表：`- item` 或 `* item`。
- 有序列表：`1. item`。
- 表格：标准 Markdown 表格。
- 代码块：三反引号代码块。
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

3. 编写 `topic.json`：

```json
{
  "title": "AI Infra 网络基础",
  "subtitle": "RDMA · NCCL · 拓扑 · 拥塞控制",
  "output": "pages/ai-infra/networking/index.html",
  "sections": [
    {"title": "网络基础", "file": "01-overview.md", "card": "card-s"},
    {"title": "RDMA 与 NCCL", "file": "02-rdma.md", "card": "card-m"}
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

6. 构建并预览：

```bash
uv run python tools/build_site.py
uv run python -m http.server 8000
```

## 新增章节流程

1. 在对应主题目录新增章节 Markdown，例如：

```text
content/ai-infra/gpu/03-topology.md
```

2. 在对应 `topic.json` 的 `sections` 末尾追加：

```json
{"title": "GPU 拓扑", "file": "03-topology.md", "card": "card-s"}
```

3. 运行构建：

```bash
uv run python tools/build_site.py
```

4. 打开对应页面确认目录和内容展示正常。

## 修改内容流程

1. 根据用户需求定位到 `content/<domain>/<topic>/`。
2. 修改对应 Markdown 文件。
3. 如果新增、删除或调整章节顺序，同时修改 `topic.json`。
4. 运行：

```bash
uv run python tools/build_site.py
```

5. 检查生成后的页面。

不要直接修改生成后的 `pages/**/*.html`。如果发现生成 HTML 不符合预期，应修改内容源、模板或生成脚本。

## 删除章节流程

1. 从对应 `topic.json.sections` 删除该章节记录。
2. 删除对应 Markdown 文件。
3. 运行：

```bash
uv run python tools/build_site.py
```

4. 检查页面目录中不再出现该章节。

## 删除主题流程

1. 从 `content/site.json.nav` 删除导航项。
2. 从 `content/site.json.topics` 删除主题项。
3. 删除 `content/<domain>/<topic>/` 源目录。
4. 删除旧生成产物目录，例如：

```bash
rm -rf pages/ai-infra/networking
```

5. 运行：

```bash
uv run python tools/build_site.py
```

6. 检查首页卡片、顶部导航和内部链接。

注意：当前 `tools/build_site.py` 不会自动清理已删除主题的旧 HTML 产物，所以删除主题时必须手动清理对应 `pages/...` 目录。

## 修改页面结构或样式

只在以下文件中修改结构和样式：

- `templates/index.html`：首页结构模板。
- `templates/page.html`：主题页结构模板。
- `templates/topic-card.html`：首页主题卡片模板。
- `assets/style.css`：视觉样式。
- `assets/script.js`：夜间模式、目录抽屉、QA 展开等交互。
- `tools/build_site.py`：生成逻辑。

修改后运行：

```bash
uv run python tools/build_site.py
```

## 目录和交互规则

- 夜间模式按钮由 `assets/script.js` 自动注入顶部导航。
- 主题选择会写入 `localStorage`，键名为 `doctor-study-theme`。
- 未手动选择时，页面跟随系统 `prefers-color-scheme`。
- 长页面目录由 `assets/script.js` 自动从 `<h2>` 或 `<h3>` 生成。
- 目录默认隐藏，通过右下角 `目录` 按钮打开。
- 点击目录链接、遮罩或关闭按钮会关闭目录。
- 按 `Escape` 会关闭目录。
- 问答块 `.qa` 可点击展开。
- 按 `Alt + E` 可展开或折叠当前页面全部 `.qa`。

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

建议执行内部链接检查：

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
        if href and not href.startswith(('#', 'http:', 'https:', 'mailto:', 'javascript:')):
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

- 用户没有明确要求时，不要自动 commit 或 push。
- 提交前先查看：

```bash
git status --short
git diff --stat
```

- `.venv/`、`__pycache__/`、`*.pyc` 不应出现在 git 中。
- `content/`、`templates/`、`tools/`、`assets/`、`resources/`、`index.html`、`pages/` 都需要提交。
- `pages/` 虽然是生成产物，但当前静态站点展示依赖它，因此不要加入 `.gitignore`。

## 禁止事项

- 不要把新内容直接写进 `pages/**/*.html`。
- 不要把具体学习内容写进 `templates/`。
- 不要让单个 Markdown 文件无限膨胀；内容多时继续拆文件。
- 不要删除用户未确认要删除的内容。
- 不要运行 `git reset --hard`、`git checkout --` 等破坏性命令，除非用户明确要求。
- 不要提交 `.venv/` 或 Python 缓存。

## Agent 标准工作流

1. 先读 `AGENTS.md` 和 `content/site.json`。
2. 涉及内容新增、重写、重组或 Markdown 格式统一时，先读 `content/STYLE_GUIDE.md`。
3. 判断需求属于新增主题、新增章节、修改内容、删除内容、样式调整还是构建发布。
4. 定位并编辑 `content/`、`templates/`、`assets/` 或 `tools/` 中的最小必要文件。
5. 运行 `uv run python tools/build_site.py`。
6. 检查生成页面、内部链接和 `git status --short`。
7. 用简短总结告诉用户改了什么、如何预览、是否需要 commit / push。
