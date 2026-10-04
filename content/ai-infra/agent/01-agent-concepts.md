<div class="card card-m">
<h3>什么是基于 LLM 的 Agent</h3>
<p>基于 LLM 的 Agent 是以大语言模型为决策核心、围绕给定目标与环境交互的软件系统。它根据当前任务状态和环境反馈选择下一步行动，由运行时执行行动，再利用结果继续决策，直到完成任务、遇到阻塞或触发停止条件。</p>
<p><strong>关键特征是目标驱动的决策—行动—反馈闭环。</strong>Agent 的定义并不完全统一；这里采用工程上常用的区分：预定义代码决定主要执行路径的是工作流，LLM 根据运行中的反馈动态选择行动的是 Agent。两者可以组合使用。</p>
<div class="table-scroll">
<table>
<tr><th>形式</th><th>谁决定下一步</th><th>示例</th></tr>
<tr><td>普通 LLM 调用</td><td>调用方提供输入，模型生成本次输出</td><td>解释报错含义、生成一段代码</td></tr>
<tr><td>固定 LLM 工作流</td><td>预定义代码决定步骤与分支</td><td>固定执行检索 → 摘要 → 格式检查</td></tr>
<tr><td>LLM Agent</td><td>模型结合目标、状态和反馈选择后续行动</td><td>读取报错后选择检查文件、修改代码或继续测试</td></tr>
</table>
</div>
<p>聊天是一种交互界面，背后既可以是普通模型调用，也可以是 Agent。工具调用、多轮对话或保存历史记录，单独出现时都不足以证明系统具备自主控制流程的能力。</p>
</div>

<div class="card card-s">
<h3>核心组件及其职责</h3>
<p>组件拆分方式没有统一标准。可以按以下六项职责理解一个典型系统；这些职责可以由同一个模块承担。</p>
<div class="table-scroll">
<table>
<tr><th>组件 / 职责</th><th>作用</th><th>修复代码示例</th></tr>
<tr><td>目标与指令</td><td>定义任务、完成标准、约束和权限</td><td>修复指定测试，不修改无关功能</td></tr>
<tr><td>LLM 决策与规划</td><td>理解观察、选择行动，必要时拆解任务或调整计划</td><td>根据堆栈决定先读取哪个函数</td></tr>
<tr><td>上下文与状态 / 记忆</td><td>保存目标、已知事实、执行记录和当前进度</td><td>记录改过哪些文件、哪些测试仍失败</td></tr>
<tr><td>工具与执行器</td><td>提供环境交互接口并执行实际操作</td><td>读取文件、应用补丁、运行测试</td></tr>
<tr><td>观察与结果检查</td><td>收集环境反馈，依据任务标准判断进展</td><td>读取退出码、失败用例和测试输出</td></tr>
<tr><td>运行时控制</td><td>驱动循环，执行参数校验、权限检查、超时和预算限制</td><td>限制重试次数，遇到权限不足时暂停</td></tr>
</table>
</div>
<p>常见的“LLM + 规划 + 记忆 + 工具”便于记忆，但还需要解释这些能力如何通过运行时形成闭环。模型负责提出工具调用及参数，宿主程序负责校验和执行；模型生成一段命令并不代表命令已经运行。</p>
<p>长期记忆、向量数据库、独立规划器、自我反思模块和多 Agent 协作都是可选扩展。简单 Agent 可以只维护当前任务上下文，并逐步决定行动。跨会话存储也不意味着模型权重得到更新。</p>
</div>

<div class="card card-d">
<h3>一次任务如何形成闭环</h3>
<pre><code>目标与当前状态 → LLM 选择行动 → 运行时校验并执行工具
       ↑                                  ↓
       └──── 更新状态，继续决策 ← 读取执行结果
完成任务 / 需要用户输入 / 达到预算上限 → 返回结果或暂停</code></pre>
<p>例如“修复这个测试失败”：Agent 先读取错误和相关代码，提出补丁，由工具修改文件并运行测试。测试仍失败时，它根据新的错误选择下一步；通过相关检查后，报告修改和验证结果。若只生成一段修复建议，尚未构成这个执行闭环。</p>
<p>结果检查应尽量依据测试、查询结果或环境状态等外部证据。LLM 自称“已经完成”不能替代验证；预算耗尽而停止也不等于任务成功。</p>
<p>定义与工作流区分参考：<a href="https://www.anthropic.com/engineering/building-effective-agents">Anthropic：Building effective agents</a>。上述组件表按工程职责展开，并非统一的行业分类标准。</p>
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
