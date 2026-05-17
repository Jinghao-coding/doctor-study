# doctor-study Agent Guide

## 项目定位

本项目用于毕业期间的面试、项目、简历准备和学习沉淀。当前核心内容是 AI Infra 面试准备，后续会继续扩展到简历、项目深挖、计算机基础、行为面等方向。

## 当前架构

- `content/`：唯一优先编辑的内容源，按 `domain/topic/*.md` 拆分知识点。
- `content/site.json`：站点导航和主题卡片配置。
- `content/**/topic.json`：单个主题页的标题、摘要、输出路径和章节顺序。
- `templates/`：HTML 模板，不要把具体学习内容写在这里。
- `tools/build_site.py`：静态页面生成脚本。
- `pages/`：生成后的可浏览 HTML 页面，默认不要手动编辑。
- `assets/`：全站共享 CSS 和 JS。
- `index.html`：由 `tools/build_site.py` 生成的首页。

## 更新规则

1. 新增或修改学习内容时，优先编辑 `content/` 下的 Markdown 小文件。
2. 一个 Markdown 文件只负责一个小知识点或一个章节，避免再次形成超大文件。
3. 新增主题时，创建 `content/<domain>/<topic>/topic.json`，并在 `content/site.json` 的 `topics` 和 `nav` 中注册。
4. 修改内容后必须运行：

```bash
python3 tools/build_site.py
```

5. 不要直接手改 `pages/**/*.html` 和 `index.html`，除非是在调整生成模板或排查生成结果。
6. 若需要改页面结构或视觉样式，修改 `templates/`、`assets/style.css`、`assets/script.js`，再重新构建。
7. 长页面目录由 `assets/script.js` 自动生成，右下角 `目录` 按钮可打开/关闭目录抽屉。
8. 问答块使用 `.qa` 结构，页面内 `Alt + E` 可展开或折叠全部问答。

## 推荐内容树

```text
content/
  ai-infra/
    papers/
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

## Agent 工作流

1. 先读 `agents.md` 和 `content/site.json`，理解站点结构。
2. 根据用户需求定位到对应 `content/<domain>/<topic>/`。
3. 只编辑相关 Markdown 或 JSON 配置，尽量不要触碰无关主题。
4. 运行 `python3 tools/build_site.py` 生成页面。
5. 检查内部链接和浏览效果。
6. 如用户要求同步远端，再 commit 并 push。
