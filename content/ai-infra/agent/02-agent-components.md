## 一句话结论

Agent 组件要拆成模型、提示词、记忆、工具、规划器、执行器和状态管理。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | AI Agent |
| 章节类型 | 概念类 |
| 解决问题 | 围绕 ReAct、Plan-Execute、记忆、工具调用、RAG、多 Agent 协作和工程风险建立 Agent 面试答案。 |
| 面试抓手 | 不要只说 Function Calling。 |

<div class="card card-m">
<h3>记忆系统：Agent 的上下文管理</h3>
<p>记忆是 Agent 区别于单次 LLM 调用的关键。一个合格的 Agent 需要管理<strong>短期记忆、长期记忆和工作记忆</strong>，面试中要能说清楚三者的区别和实现方式。</p>
<table>
<tr><th>记忆类型</th><th>存储位置</th><th>生命周期</th><th>实现方式</th><th>典型容量</th></tr>
<tr><td>感官记忆</td><td>当前对话上下文</td><td>单次交互</td><td>直接拼入 prompt</td><td>受 context window 限制</td></tr>
<tr><td>短期记忆</td><td>会话内历史</td><td>当前会话</td><td>滑动窗口、摘要压缩</td><td>几轮～几十轮对话</td></tr>
<tr><td>长期记忆</td><td>外部存储</td><td>跨会话持久化</td><td>向量数据库 + RAG 检索</td><td>理论上无限</td></tr>
<tr><td>工作记忆</td><td>任务状态</td><td>当前任务</td><td>结构化状态对象</td><td>任务相关</td></tr>
</table>
</div>

<div class="card card-s">
<h3>记忆管理策略</h3>
<div class="qa-section"><div class="qa-section-title">滑动窗口</div><p>只保留最近 N 轮对话。简单但会丢失早期重要信息。适合短任务。</p></div>
<div class="qa-section"><div class="qa-section-title">摘要压缩</div><p>定期对历史对话做摘要，用摘要替代原始对话。节省 token 但可能丢失细节。适合长会话。</p></div>
<div class="qa-section"><div class="qa-section-title">向量检索</div><p>将历史交互存入向量数据库，需要时按语义相似度检索最相关的记忆。适合大量历史信息。</p></div>
<div class="qa-section"><div class="qa-section-title">混合策略</div><p>近期对话保留原文 + 远期对话做摘要 + 关键信息向量检索。是工程中最常用的方案。</p></div>
<div class="qa-section"><div class="qa-section-title">反思记忆（Reflexion）</div><p>Agent 在任务完成后对自己的表现做反思，将经验教训存入长期记忆，供后续任务参考。这是 Agent 自我进化的基础。</p></div>
</div>

<div class="card card-d">
<h3>工具调用（Tool Use / Function Calling）</h3>
<p>工具调用是 Agent 能力的放大器。LLM 本身只能生成文本，但通过工具调用可以<strong>搜索网页、执行代码、操作文件、调用 API、查询数据库</strong>。</p>
<table>
<tr><th>工具类型</th><th>示例</th><th>实现方式</th></tr>
<tr><td>搜索工具</td><td>Google Search、Bing、Wikipedia</td><td>API 调用，返回结构化结果</td></tr>
<tr><td>代码执行</td><td>Python REPL、Shell、SQL</td><td>沙箱环境执行，返回 stdout/stderr</td></tr>
<tr><td>文件操作</td><td>读、写、搜索、编辑文件</td><td>文件系统 API</td></tr>
<tr><td>API 调用</td><td>天气、股票、邮件、日历</td><td>REST API / SDK</td></tr>
<tr><td>数据库查询</td><td>SQL、向量搜索、图谱查询</td><td>数据库连接 + 查询执行</td></tr>
<tr><td>浏览器操作</td><td>点击、输入、截图、读取页面</td><td>Playwright / Selenium</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">Function Calling 流程</div><ol><li>定义工具的 JSON Schema（名称、描述、参数类型）</li><li>将 Schema 注入 system prompt 或作为 API 参数传给 LLM</li><li>LLM 决定是否调用工具，输出工具名和参数 JSON</li><li>Agent 框架解析 JSON，执行实际工具调用</li><li>将工具返回结果拼回对话上下文，LLM 继续推理</li></ol></div>
<div class="qa-section"><div class="qa-section-title">MCP（Model Context Protocol）</div><p>Anthropic 提出的开放协议，标准化 LLM 与外部工具的交互方式。类似"AI 的 USB-C 接口"，让不同 Agent 框架和工具可以互操作。核心概念：MCP Server 暴露工具，MCP Client（Agent）发现并调用工具。</p></div>
</div>

<div class="card card-w">
<h3>规划能力</h3>
<p>规划是 Agent 处理复杂任务的核心能力。面试中要区分<strong>固定流程规划、动态规划和层次化规划</strong>。</p>
<table>
<tr><th>规划方式</th><th>说明</th><th>优点</th><th>缺点</th></tr>
<tr><td>固定流程</td><td>预定义步骤，Agent 按顺序执行</td><td>可控、可预测</td><td>不灵活，无法应对意外</td></tr>
<tr><td>ReAct 动态</td><td>每步根据观察决定下一步</td><td>灵活、适应性强</td><td>可能偏离目标、效率低</td></tr>
<tr><td>Plan-Execute</td><td>先生成完整计划，再逐步执行</td><td>全局视角、步骤清晰</td><td>计划可能不准确，调整成本高</td></tr>
<tr><td>层次化规划</td><td>高层目标 → 子目标 → 具体步骤</td><td>适合超复杂任务</td><td>工程复杂度高</td></tr>
<tr><td>自我反思</td><td>执行后评估结果，调整后续策略</td><td>持续改进、减少重复错误</td><td>增加延迟和成本</td></tr>
</table>
<div class="qa-summary">面试要点：实际系统中通常是组合使用。例如 ReAct 做单步决策 + 层次化规划做任务分解 + 自我反思做质量保证。</div>
</div>

<div class="card card-m">
<h3>多 Agent 协作</h3>
<p>当单个 Agent 无法处理复杂任务时，需要多个 Agent 分工协作。面试中要能说清楚常见的多 Agent 架构模式。</p>
<table>
<tr><th>模式</th><th>说明</th><th>典型场景</th><th>代表框架</th></tr>
<tr><td>顺序流水线</td><td>Agent A 的输出作为 Agent B 的输入</td><td>写作→审校→发布</td><td>LangChain Chain</td></tr>
<tr><td>辩论模式</td><td>多个 Agent 对同一问题给出不同观点，汇总后决策</td><td>代码审查、策略讨论</td><td>ChatDev、Multi-Agent Debate</td></tr>
<tr><td>角色扮演</td><td>每个 Agent 扮演特定角色（PM、工程师、测试）</td><td>软件开发全流程</td><td>ChatDev、MetaGPT</td></tr>
<tr><td>层级结构</td><td>管理者 Agent 分配任务给执行者 Agent</td><td>复杂项目管理</td><td>AutoGen、CrewAI</td></tr>
<tr><td>共享记忆</td><td>多个 Agent 共享同一个记忆空间</td><td>协作研究、知识积累</td><td>MemGPT、Letta</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">多 Agent 的核心挑战</div><ul><li><strong>通信协议：</strong>Agent 之间如何交换信息？结构化 JSON 还是自然语言？</li><li><strong>任务分配：</strong>谁来决定哪个 Agent 做什么？集中式调度还是协商？</li><li><strong>冲突解决：</strong>多个 Agent 意见不一致时如何决策？投票、仲裁还是层级决策？</li><li><strong>上下文共享：</strong>哪些信息需要共享？如何避免上下文爆炸？</li><li><strong>错误传播：</strong>上游 Agent 的错误如何影响下游？如何隔离和恢复？</li></ul></div>
</div>

## 面试回答

**30 秒版：**

Agent 不只是 Function Calling。我会拆成记忆、工具、规划、多 Agent 协作四块：记忆分短期（上下文窗口）、长期（向量库+RAG）和工作记忆，工具靠 Function Calling 或 MCP 接外部能力，规划有 ReAct 动态、Plan-Execute、层次化和自我反思，复杂任务再上多 Agent 分工。

**2 分钟版：**

我会按模块讲。记忆是 Agent 区别于单次调用的关键：感官记忆是当前上下文、短期记忆用滑动窗口或摘要压缩管理会话历史、长期记忆靠向量库跨会话持久化、工作记忆用结构化对象存任务状态，工程上最常用混合策略——近期原文+远期摘要+关键信息向量检索，再配 Reflexion 反思记忆做自我进化。工具调用是能力放大器，让只能生成文本的 LLM 能搜索、执行代码、操作文件、调 API；流程是定义 JSON Schema → 注入 prompt → LLM 输出 tool_call → 框架执行 → 结果拼回上下文，MCP 则是 Anthropic 提出的标准化协议、相当于 AI 的 USB-C 接口。规划要区分固定流程、ReAct 动态、Plan-Execute、层次化和自我反思，实际是组合使用。最后是多 Agent 协作：顺序流水线、辩论、角色扮演、层级结构、共享记忆，核心挑战在通信协议、任务分配、冲突解决、上下文共享和错误传播。落到 infra，这些直接对应记忆的存储成本、工具执行的沙箱隔离和多 Agent 的调度编排。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
