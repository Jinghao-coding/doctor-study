# doctor-study

毕业准备用的静态学习站点，当前主线是 AI Infra 面试准备，内容源维护在 `content/`，页面由 `tools/build_site.py` 生成到仓库根目录的 `index.html` 和 `pages/`。

## 在线访问

- GitHub Pages 访问链接：<https://jinghao-coding.github.io/doctor-study/>
- 论文模块示例：<https://jinghao-coding.github.io/doctor-study/pages/ai-infra/papers/index.html>

## GitHub Pages 配置

本项目已内置 GitHub Actions 自动发布配置：`.github/workflows/pages.yml`。

首次启用时建议检查：

1. 打开 GitHub 仓库：`Settings`
2. 进入：`Pages`
3. `Build and deployment` 选择：`GitHub Actions`
4. 确认默认分支为 `main`
5. push 到 `main` 后等待 `Deploy GitHub Pages` workflow 完成

发布完成后，站点首页访问地址应为：

- <https://jinghao-coding.github.io/doctor-study/>

## 本地构建

```bash
uv run python tools/build_site.py
uv run python -m http.server 8000
```

本地预览：

- <http://localhost:8000/>

## 内容维护约定

- 优先编辑 `content/`，不要直接修改生成后的 `pages/**/*.html`
- 修改内容、模板或生成脚本后，重新运行 `uv run python tools/build_site.py`
- `index.html` 和 `pages/` 是 GitHub Pages 展示依赖的生成产物，需要一并提交
