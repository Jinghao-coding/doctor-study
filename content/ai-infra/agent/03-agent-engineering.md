## 一句话结论

Agent 工程重点是可靠性、状态、权限、观测、评测和失败恢复。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | AI Agent |
| 章节类型 | 概念类 |
| 解决问题 | 围绕 ReAct、Plan-Execute、记忆、工具调用、RAG、多 Agent 协作和工程风险建立 Agent 面试答案。 |
| 面试抓手 | 把 demo 和生产系统分开讲。 |

<div class="card card-m">
<h3>主流 Agent 框架对比</h3>
<p>面试中经常被问到"你用过哪些 Agent 框架，有什么区别"。以下是当前主流框架的对比。</p>
<table>
<tr><th>框架</th><th>定位</th><th>核心特点</th><th>适用场景</th></tr>
<tr><td>LangChain</td><td>通用 LLM 应用框架</td><td>链式调用、工具集成、记忆管理、丰富的生态</td><td>快速原型、RAG 应用、简单 Agent</td></tr>
<tr><td>LangGraph</td><td>有状态 Agent 框架</td><td>图结构定义流程、支持循环和条件分支、checkpoint</td><td>复杂多步 Agent、人机协作</td></tr>
<tr><td>AutoGen</td><td>多 Agent 对话框架</td><td>多 Agent 对话、代码执行、人机协作</td><td>多 Agent 协作、代码生成</td></tr>
<tr><td>CrewAI</td><td>角色化多 Agent</td><td>角色定义、任务委派、顺序/层级流程</td><td>团队协作模拟</td></tr>
<tr><td>OpenAI Agents SDK</td><td>官方 Agent SDK</td><td>轻量、原生 Function Calling、Guardrails、Tracing</td><td>生产级 Agent 应用</td></tr>
<tr><td>Dify / Coze</td><td>低代码 Agent 平台</td><td>可视化编排、拖拽式工作流、模板市场</td><td>非开发者、快速搭建</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Function Calling 深入</h3>
<p>Function Calling 是 Agent 工具调用的核心机制。面试中要能说清楚完整流程和常见问题。</p>
<div class="qa-section"><div class="qa-section-title">工具定义最佳实践</div><ul><li><strong>名称清晰：</strong>用动词+名词，如 <code>search_web</code>、<code>calculate_math</code>。</li><li><strong>描述精确：</strong>说明工具做什么、什么时候用、什么时候不用。</li><li><strong>参数类型严格：</strong>用 JSON Schema 约束类型、枚举值、必填项。</li><li><strong>返回格式一致：</strong>统一用 JSON，包含 status、data、error 字段。</li></ul></div>
<div class="qa-section"><div class="qa-section-title">并行工具调用</div><p>当多个工具调用之间没有依赖关系时，可以并行执行以减少延迟。例如同时搜索多个关键词、同时读取多个文件。OpenAI 的 parallel tool calls 支持在一次响应中返回多个 tool_call。</p></div>
<div class="qa-section"><div class="qa-section-title">工具调用常见问题</div><ul><li><strong>幻觉调用：</strong>LLM 调用了不存在的工具或传了不合理的参数。</li><li><strong>循环调用：</strong>Agent 反复调用同一工具但得不到满意结果。</li><li><strong>参数错误：</strong>参数类型、格式或取值范围不正确。</li><li><strong>工具描述冲突：</strong>多个工具描述相似，LLM 选错工具。</li></ul></div>
</div>

<div class="card card-d">
<h3>RAG：检索增强生成</h3>
<p>RAG（Retrieval-Augmented Generation）是 Agent 获取外部知识的核心手段。面试中要能说清楚 RAG 的完整流程和优化方向。</p>
<div class="qa-section"><div class="qa-section-title">RAG 标准流程</div><ol><li><strong>文档预处理：</strong>解析 PDF/网页/数据库 → 分块（chunking）→ 向量化（embedding）→ 存入向量数据库。</li><li><strong>检索：</strong>用户问题向量化 → 向量相似度搜索 → 返回 Top-K 相关文档块。</li><li><strong>增强：</strong>将检索到的文档块拼入 prompt，作为 LLM 的参考上下文。</li><li><strong>生成：</strong>LLM 基于问题和检索到的上下文生成答案。</li></ol></div>
<div class="qa-section"><div class="qa-section-title">RAG 优化方向</div><table>
<tr><th>阶段</th><th>优化点</th><th>技术方案</th></tr>
<tr><td>分块</td><td>块大小、重叠、语义边界</td><td>语义分块、句子级分块、递归分块</td></tr>
<tr><td>嵌入</td><td>嵌入模型选择、维度</td><td>text-embedding-3、bge、jina</td></tr>
<tr><td>检索</td><td>召回率、精确率</td><td>混合检索（向量+关键词）、重排序（rerank）</td></tr>
<tr><td>增强</td><td>上下文质量、信息密度</td><td>上下文压缩、去重、相关性过滤</td></tr>
<tr><td>生成</td><td>引用准确性、幻觉控制</td><td>强制引用、答案验证、事实核查</td></tr>
</table></div>
<div class="qa-section"><div class="qa-section-title">Agentic RAG</div><p>传统 RAG 是"检索→生成"的单向流程。Agentic RAG 让 Agent 主动决策：是否需要检索、检索什么、检索结果是否足够、是否需要重新检索。这是 RAG 从"被动增强"到"主动获取"的升级。</p></div>
</div>

<div class="card card-w">
<h3>Agent 评估</h3>
<p>评估 Agent 比评估单次 LLM 调用复杂得多，因为 Agent 涉及多步决策、工具调用和环境交互。</p>
<table>
<tr><th>评估维度</th><th>指标</th><th>说明</th></tr>
<tr><td>任务成功率</td><td>Task Success Rate</td><td>Agent 是否完成了指定任务</td></tr>
<tr><td>效率</td><td>平均步数、Token 消耗、耗时</td><td>完成任务需要多少步、多少成本</td></tr>
<tr><td>工具使用准确性</td><td>Tool Selection Accuracy</td><td>是否选择了正确的工具和参数</td></tr>
<tr><td>鲁棒性</td><td>错误恢复率</td><td>遇到错误后能否自行恢复</td></tr>
<tr><td>安全性</td><td>有害操作率</td><td>是否执行了危险或违规操作</td></tr>
<tr><td>用户满意度</td><td>人工评分、A/B 测试</td><td>最终用户体验</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">评估框架</div><ul><li><strong>GAIA：</strong>Meta 提出的 Agent 基准，测试多步推理和工具使用能力。</li><li><strong>SWE-bench：</strong>测试 Agent 解决真实 GitHub Issue 的能力。</li><li><strong>WebArena：</strong>测试 Agent 在真实网站上的操作能力。</li><li><strong>AgentBench：</strong>多维度 Agent 能力评估基准。</li></ul></div>
</div>

<div class="card card-m">
<h3>Agent 部署与安全</h3>
<div class="qa-section"><div class="qa-section-title">部署架构</div><ul><li><strong>无状态部署：</strong>每次请求独立处理，状态存外部。简单但每次都要重建上下文。</li><li><strong>有状态部署：</strong>Agent 实例保持会话状态。复杂但延迟低、体验好。</li><li><strong>微服务化：</strong>将 LLM、记忆、工具执行拆成独立服务。灵活但运维复杂。</li></ul></div>
<div class="qa-section"><div class="qa-section-title">安全防护</div><ul><li><strong>Prompt Injection 防护：</strong>用户输入可能包含恶意指令，需要输入过滤和指令隔离。</li><li><strong>工具调用权限控制：</strong>限制 Agent 可以调用的工具范围，敏感操作需要人工确认。</li><li><strong>输出审核：</strong>对 Agent 的输出做内容安全检查，防止泄露敏感信息。</li><li><strong>沙箱执行：</strong>代码执行、文件操作等高风险操作在隔离环境中运行。</li><li><strong>速率限制：</strong>防止 Agent 过度调用 API 或消耗过多资源。</li></ul></div>
<div class="qa-section"><div class="qa-section-title">可观测性</div><ul><li><strong>链路追踪：</strong>记录每一步的 Thought、Action、Observation，方便调试。</li><li><strong>成本监控：</strong>统计每次任务的 Token 消耗和 API 调用费用。</li><li><strong>质量监控：</strong>自动检测任务成功率、工具调用准确率等指标。</li></ul></div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
