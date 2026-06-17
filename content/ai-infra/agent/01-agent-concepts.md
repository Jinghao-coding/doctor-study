## 一句话结论

Agent 的本质是 LLM 驱动的循环决策系统：观察、思考、调用工具、接收反馈、继续行动。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | AI Agent |
| 章节类型 | 概念类 |
| 解决问题 | 围绕 ReAct、Plan-Execute、记忆、工具调用、RAG、多 Agent 协作和工程风险建立 Agent 面试答案。 |
| 面试抓手 | 先讲模式，再讲工程边界。 |

<div class="card card-m">
<h3>什么是 AI Agent</h3>
<p>AI Agent 是一个能<strong>感知环境、自主决策、执行动作</strong>的智能体。和传统 LLM Chat 不同，Agent 不只是回答问题，而是能<strong>使用工具、维护状态、多步推理、在真实环境中完成目标</strong>。</p>
<table>
<tr><th>维度</th><th>LLM Chat</th><th>AI Agent</th></tr>
<tr><td>交互模式</td><td>单轮或多轮对话</td><td>多步推理 + 工具调用 + 环境交互</td></tr>
<tr><td>状态管理</td><td>对话历史（无持久状态）</td><td>短期记忆 + 长期记忆 + 任务状态</td></tr>
<tr><td>能力边界</td><td>仅文本生成</td><td>搜索、计算、代码执行、API 调用、文件操作</td></tr>
<tr><td>错误处理</td><td>依赖用户纠正</td><td>自我反思、重试、fallback 策略</td></tr>
<tr><td>典型产出</td><td>回答、摘要、翻译</td><td>完成任务、生成报告、自动化工作流</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Agent 核心架构</h3>
<p>一个典型的 Agent 由四个核心模块组成，面试中要能画出这个架构并解释每个模块的职责。</p>
<div class="sched-flow">
<svg viewBox="0 0 1000 380" role="img" aria-label="AI Agent architecture">
<defs>
<marker id="agentArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
<path d="M0,0 L0,6 L9,3 z" fill="currentColor"></path>
</marker>
</defs>
<text x="34" y="42" class="k8s-title">AI Agent 核心架构</text>
<text x="34" y="64" class="k8s-subtitle">LLM + 记忆 + 工具 + 规划 = Agent</text>

<rect x="40" y="120" width="200" height="100" class="sched-node sched-api"></rect>
<text x="65" y="155" class="sched-label">LLM 大脑</text>
<text x="65" y="178" class="sched-desc">推理、理解、生成</text>
<text x="65" y="196" class="sched-desc">GPT-4 / Claude / Gemini</text>

<rect x="310" y="90" width="200" height="80" class="sched-node sched-cache"></rect>
<text x="335" y="122" class="sched-label">记忆系统</text>
<text x="335" y="145" class="sched-desc">短期（上下文窗口）</text>
<text x="335" y="160" class="sched-desc">长期（向量库 / DB）</text>

<rect x="310" y="210" width="200" height="80" class="sched-node sched-queue"></rect>
<text x="335" y="242" class="sched-label">工具系统</text>
<text x="335" y="265" class="sched-desc">搜索、计算、API、代码</text>
<text x="335" y="280" class="sched-desc">Function Calling / MCP</text>

<rect x="580" y="120" width="200" height="100" class="sched-node sched-bind"></rect>
<text x="605" y="155" class="sched-label">规划与执行</text>
<text x="605" y="178" class="sched-desc">任务分解、调度</text>
<text x="605" y="196" class="sched-desc">反思、纠错、重试</text>

<rect x="840" y="120" width="120" height="100" class="sched-node sched-kubelet"></rect>
<text x="858" y="155" class="sched-label">环境</text>
<text x="858" y="178" class="sched-desc">Web / OS</text>
<text x="858" y="196" class="sched-desc">API / DB</text>

<path d="M240 170 C270 170 280 130 310 130" class="sched-arrow"></path>
<path d="M240 170 C270 170 280 250 310 250" class="sched-arrow"></path>
<path d="M510 130 C540 130 550 170 580 170" class="sched-arrow"></path>
<path d="M510 250 C540 250 550 170 580 170" class="sched-arrow"></path>
<path d="M780 170 C805 170 810 170 840 170" class="sched-arrow"></path>
<path d="M900 220 C900 260 880 300 510 300 C540 300 510 170 510 170" class="sched-arrow sched-dashed"></path>
</svg>
</div>
</div>

<div class="card card-d">
<h3>ReAct：推理 + 行动</h3>
<p>ReAct（Reasoning + Acting）是当前最主流的 Agent 范式，由 Google 在 2022 年提出。核心思想是让 LLM 交替进行<strong>思考（Thought）→ 行动（Action）→ 观察（Observation）</strong>，直到任务完成。</p>
<table>
<tr><th>步骤</th><th>说明</th><th>示例</th></tr>
<tr><td>Thought</td><td>分析当前状态，决定下一步做什么</td><td>"我需要先查一下今天的天气"</td></tr>
<tr><td>Action</td><td>调用工具或执行操作</td><td>search("北京今天天气")</td></tr>
<tr><td>Observation</td><td>获取工具返回结果</td><td>"北京今天晴，25°C"</td></tr>
<tr><td>...循环...</td><td>重复直到任务完成或达到最大步数</td><td>"天气不错，可以推荐户外活动"</td></tr>
<tr><td>Final Answer</td><td>汇总所有信息，给出最终答案</td><td>"今天北京晴，适合去颐和园"</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">ReAct 的优势</div><ul><li><strong>可解释性：</strong>每一步的 Thought 让用户看到推理过程。</li><li><strong>错误恢复：</strong>Observation 不理想时可以调整策略重试。</li><li><strong>减少幻觉：</strong>通过工具获取真实信息，而非纯靠模型记忆。</li><li><strong>灵活组合：</strong>可以在一次任务中调用多种工具。</li></ul></div>
<div class="qa-section"><div class="qa-section-title">ReAct 的局限</div><ul><li>每步都需要 LLM 调用，延迟高、成本大。</li><li>长链推理可能累积错误，中间步骤的偏差会放大。</li><li>对复杂任务的分解能力有限，容易陷入局部循环。</li></ul></div>
</div>

<div class="card card-s">
<h3>Plan-and-Execute：先规划再执行</h3>
<p>Plan-and-Execute 将 Agent 流程分为两个阶段：<strong>规划阶段</strong>生成完整执行计划，<strong>执行阶段</strong>按计划逐步调用工具。适合步骤明确、依赖关系清晰的任务。</p>
<table>
<tr><th>对比维度</th><th>ReAct</th><th>Plan-and-Execute</th></tr>
<tr><td>决策方式</td><td>每步实时决策</td><td>先全局规划，再逐步执行</td></tr>
<tr><td>全局最优</td><td>可能陷入局部最优</td><td>有机会找到全局较优路径</td></tr>
<tr><td>灵活性</td><td>高，可随时调整</td><td>低，计划变更成本高</td></tr>
<tr><td>延迟</td><td>每步一次 LLM 调用</td><td>规划一次 + 执行 N 次</td></tr>
<tr><td>适用场景</td><td>探索性、不确定性高</td><td>结构化、步骤明确</td></tr>
</table>
</div>

<div class="card card-w">
<h3>思维链与思维树</h3>
<p>CoT（Chain-of-Thought）和 ToT（Tree-of-Thoughts）是提升 LLM 推理能力的两种提示技术，也是 Agent 规划能力的基础。</p>
<table>
<tr><th>技术</th><th>核心思想</th><th>适用场景</th><th>局限</th></tr>
<tr><td>CoT</td><td>让模型在输出答案前先写出推理步骤</td><td>数学、逻辑、多步推理</td><td>线性推理，不会回溯</td></tr>
<tr><td>CoT-SC</td><td>多次采样 CoT，取多数结果（Self-Consistency）</td><td>有明确答案的推理任务</td><td>成本翻倍，不适用于开放式任务</td></tr>
<tr><td>ToT</td><td>维护推理树，在多个分支间搜索最优路径</td><td>规划、创作、需要探索的任务</td><td>计算成本极高，需要评估函数</td></tr>
<tr><td>GoT</td><td>Graph-of-Thoughts，将推理建模为有向图</td><td>复杂多步推理，信息融合</td><td>工程复杂度高</td></tr>
</table>
<div class="qa-summary">面试要点：CoT 是推理增强，ReAct 是推理+行动。Agent 通常需要两者结合：用 CoT 做内部推理，用 ReAct 做外部交互。</div>
</div>

## 面试回答

**30 秒版：**

Agent 是 LLM 驱动的自主循环系统：感知环境、思考决策、调用工具、接收反馈、再决策，直到完成目标。相比一问一答的 LLM Chat，它多了工具使用、记忆管理和多步规划三种能力。主流范式是 ReAct，即 Thought-Action-Observation 交替循环。

**2 分钟版：**

我会先把 Agent 和 LLM Chat 区分开：Chat 是单轮或多轮对话、只生成文本、状态就是对话历史；Agent 是「感知→决策→行动→观察→再决策」的自主循环，能用工具、维护短期/长期记忆和任务状态、并有自我反思和重试的错误处理。架构上拆四块：LLM 大脑负责推理生成，记忆系统分上下文窗口的短期记忆和向量库的长期记忆，工具系统通过 Function Calling 或 MCP 接外部能力，规划与执行模块做任务分解和纠错。范式我会重点讲 ReAct——Thought 分析现状、Action 调工具、Observation 拿结果，交替循环到 Final Answer，好处是可解释、能用真实信息纠正幻觉、能错误恢复，局限是每步都要 LLM 调用、延迟高成本大、长链推理会累积误差。对比之下 Plan-and-Execute 先全局规划再逐步执行，适合步骤明确的结构化任务，而 ReAct 更适合探索性、不确定性高的场景。实际系统通常组合：用 CoT 做内部推理、ReAct 做外部交互、再叠加层次化规划和自我反思。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
