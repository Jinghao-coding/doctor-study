## 一句话结论

ReAct 只是 Agent 范式的起点：Reflexion 用语言反思实现试错学习，Self-Ask 显式分解问题，ToT/LATS 用搜索探索多条推理路径，Plan-and-Execute 适合长周期任务。选择范式的核心是问题结构——简单任务用 ReAct，需要搜索/规划/迭代的任务用更复杂的范式。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | AI Agent |
| 章节类型 | 机制类 |
| 解决问题 | 系统梳理 ReAct 之外的高级 Agent 范式，对比适用场景，建立范式选择决策能力。 |
| 面试抓手 | 先讲 ReAct 基线，再展开每个范式的核心机制和差异，最后给选型建议。 |

<div class="card card-m">
<h3>ReAct 基线回顾</h3>
<p>ReAct（Reasoning + Acting）将推理和行动交错进行：Thought → Action → Observation 循环，直到任务完成。这是当前 Agent 的基础范式，但它有明显局限：线性推理不回溯、每步决策短视、缺乏自我纠错能力。</p>
<table>
<tr><th>组件</th><th>作用</th><th>局限</th></tr>
<tr><td>Thought</td><td>分析当前状态，决定下一步</td><td>只看当前上下文，无历史反思</td></tr>
<tr><td>Action</td><td>调用工具执行操作</td><td>无法撤销错误行动</td></tr>
<tr><td>Observation</td><td>获取工具返回结果</td><td>失败时缺乏系统性反思</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Reflexion：语言反思试错学习（Shinn et al. 2023）</h3>
<p>Reflexion 的核心洞察：<strong>用自然语言反馈（verbal reinforcement）指导后续推理，不需要更新模型权重</strong>。这是一种「在上下文中学习」的试错机制。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">Trial（尝试）</div><div class="flow-desc">Actor 生成完整轨迹（trajectory）：Thought → Action → Observation 序列，尝试完成任务</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">Evaluation（评估）</div><div class="flow-desc">Evaluator 对轨迹打分：任务是否完成？哪里出错了？生成 reward 信号</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">Self-Reflection（反思）</div><div class="flow-desc">模型生成语言反思：<code>哪里错了？为什么错？下次怎么改？</code>，例如「上一次我误把加法当乘法，下次应该先确认运算符」</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">Memory（记忆）</div><div class="flow-desc">反思存入情景记忆（episodic memory），下次尝试时将历史反思作为上下文注入</div></div>
<div class="flow-step"><div class="flow-index">05</div><div class="flow-title">Next Trial（重试）</div><div class="flow-desc">带着反思重新执行，通常 2-3 次迭代后成功率显著提升</div></div>
</div>
<div class="qa-summary">关键机制：反思是自然语言反馈，不是梯度更新；模型通过「阅读自己之前的错误总结」来改进，不需要微调。</div>
<table>
<tr><th>角色</th><th>职责</th></tr>
<tr><td>Actor</td><td>执行任务，生成轨迹</td></tr>
<tr><td>Evaluator</td><td>判断成败，给出反馈（可以是规则、测试用例或另一个 LLM）</td></tr>
<tr><td>Self-Reflection</td><td>生成具体改进建议，存入记忆</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Self-Ask：显式自问自答分解（Press et al. 2022）</h3>
<p>Self-Ask 让模型在回答主问题前，<strong>显式向自己提出 Follow-up 子问题</strong>，逐个解答后再回答主问题。这是一种显式的问题分解策略。</p>
<p><strong>示例流程：</strong></p>
<ol>
<li><strong>主问题：</strong>「爱迪生发明电灯泡时，谁是当时的美国总统？」</li>
<li><strong>Follow-up 1：</strong>「爱迪生什么时候发明电灯泡？」→ 搜索：1879 年</li>
<li><strong>Follow-up 2：</strong>「1879 年的美国总统是谁？」→ 搜索：Rutherford B. Hayes</li>
<li><strong>最终答案：</strong>Rutherford B. Hayes</li>
</ol>
<div class="qa-section"><div class="qa-section-title">核心优势</div><ul><li><strong>组合泛化：</strong>把复杂组合问题拆解为简单子问题，提升多跳推理能力</li><li><strong>可与搜索结合：</strong>每个子问题可以调用搜索引擎获取答案，不依赖模型记忆</li><li><strong>可解释：</strong>推理路径完全透明，用户能看到每一步分解</li></ul></div>
<div class="qa-section"><div class="qa-section-title">与 ReAct 的区别</div><p>ReAct 在行动中思考，Self-Ask 在行动前先分解问题；Self-Ask 的子问题是显式的「问题」形式，而 ReAct 的 Thought 是自由文本。</p></div>
</div>

<div class="card card-m">
<h3>Tree of Thoughts（ToT）：树状搜索推理</h3>
<p>CoT 是线性推理，一旦走错就无法回头；ToT 把推理建模为<strong>树结构搜索</strong>，维护多个候选路径，评估后选择最有前景的分支继续探索，不 promising 的分支可以剪枝回溯。</p>
<table>
<tr><th>组件</th><th>说明</th></tr>
<tr><td>Thought 生成</td><td>从当前状态生成多个候选下一步（BFS 宽度或 DFS 深度）</td></tr>
<tr><td>状态评估</td><td>用 LLM 给每个 thought 打分（「这个思路能解决问题吗？0-10 分」）</td></tr>
<tr><td>搜索算法</td><td>BFS（逐层扩展）或 DFS（深度优先 + 剪枝）</td></tr>
<tr><td>回溯</td><td>某条路径分数低则回退到上一分支点，探索其他分支</td></tr>
</table>
<div class="qa-summary">面试对比：CoT 是单链路「一条路走到黑」，ToT 是「多路径并行探索 + 评估剪枝」。ToT 适合需要规划、搜索、试错的问题（如 24 点游戏、创意写作、数学证明），但计算成本高（需要多次 LLM 调用生成和评估）。</div>
</div>

<div class="card card-d">
<h3>LATS（Language Agent Tree Search）：蒙特卡洛树搜索 + LLM</h3>
<p>LATS 将传统游戏 AI 中的 MCTS（Monte Carlo Tree Search）与 LLM 结合，比 ToT 更有原则性（principled）的探索。</p>
<table>
<tr><th>MCTS 阶段</th><th>LATS 实现</th></tr>
<tr><td>Selection（选择）</td><td>从根节点用 UCB 策略选择最有价值的子节点，平衡探索与利用</td></tr>
<tr><td>Expansion（扩展）</td><td>LLM 生成多个候选动作（thought/action），扩展叶子节点</td></tr>
<tr><td>Simulation（模拟）</td><td>从新节点用 LLM 做 rollout（快速走子），估计未来回报</td></tr>
<tr><td>Backpropagation（回传）</td><td>将轨迹最终结果（成功/失败）回传更新路径上所有节点的价值估计</td></tr>
<tr><td>Reflection（反思）</td><td>失败轨迹后生成反思，在下一次选择时避免相同错误</td></tr>
</table>
<div class="qa-summary">LATS 的优势：LLM 同时充当价值函数（评估状态）和策略（生成动作），反思机制让失败经验转化为后续搜索的指导。比 ToT 的 BFS/DFS 有更坚实的探索-利用平衡理论。</div>
</div>

<div class="card card-s">
<h3>Plan-and-Execute：先规划再执行</h3>
<p>Plan-and-Execute 将 Agent 分为两个独立阶段：<strong>Planner 先生成完整计划（步骤列表），Executor 逐步执行；执行中如果失败，触发 Replanner 重新规划</strong>。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">Plan（规划）</div><div class="flow-desc">LLM 分析任务，生成完整步骤列表：<code>1. 搜索用户信息 2. 查询订单 3. 计算金额 4. 生成报告</code></div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">Execute（执行）</div><div class="flow-desc">按顺序执行每一步，每步调用对应工具，记录结果</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">Replan（重规划）</div><div class="flow-desc">某步失败或发现新信息时，重新生成/更新剩余步骤计划</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">Finish（完成）</div><div class="flow-desc">所有步骤完成后汇总结果</div></div>
</div>
<div class="qa-section"><div class="qa-section-title">与 ReAct 对比</div><table><tr><th>维度</th><th>ReAct</th><th>Plan-and-Execute</th></tr><tr><td>决策粒度</td><td>每步独立决策，短视</td><td>全局规划，视野更长</td></tr><tr><td>灵活性</td><td>高，随时调整</td><td>较低，需要触发重规划</td></tr><tr><td>成本</td><td>每步都调用 LLM 决策</td><td>规划调用一次，执行步骤较简单</td></tr><tr><td>适用场景</td><td>探索性、动态环境、简单任务</td><td>长周期、步骤明确、复杂 API 工作流</td></tr></table></div>
</div>

<div class="card card-m">
<h3>范式对比与选型</h3>
<table>
<tr><th>范式</th><th>记忆</th><th>搜索</th><th>自我批判</th><th>最适合场景</th></tr>
<tr><td>ReAct</td><td>对话历史</td><td>无（线性）</td><td>无</td><td>简单 QA、工具调用、快速原型</td></tr>
<tr><td>Reflexion</td><td>情景记忆（反思）</td><td>多次尝试</td><td>显式语言反思</td><td>代码生成、数学推理、需要迭代改进</td></tr>
<tr><td>Self-Ask</td><td>子问题答案</td><td>无（分解）</td><td>无</td><td>组合式 QA、多跳推理、事实核查</td></tr>
<tr><td>ToT</td><td>树状态</td><td>BFS/DFS</td><td>状态评估打分</td><td>规划问题、创意生成、需要搜索的推理</td></tr>
<tr><td>LATS</td><td>MCTS 树 + 反思</td><td>MCTS（UCB）</td><td>失败轨迹反思</td><td>复杂决策、游戏、需要探索-利用平衡</td></tr>
<tr><td>Plan-and-Execute</td><td>计划状态</td><td>有限（重规划）</td><td>失败重规划</td><td>长周期 API 工作流、ETL、明确步骤任务</td></tr>
</table>
<div class="qa-summary">选型口诀：简单 QA→ReAct；多步数学→ToT/LATS；迭代改进→Reflexion；复杂 API→Plan-Execute；组合 QA→Self-Ask。实际系统中常混合使用（如 Plan-and-Execute 内每步用 ReAct，加上 Reflexion 反思机制）。</div>
</div>

<div class="card card-w">
<h3>范式选择的工程考量</h3>
<p>理论范式和生产系统之间有很大距离。选择范式时除了问题结构，还要考虑以下工程约束：</p>
<table>
<tr><th>约束</th><th>影响</th><th>建议</th></tr>
<tr><td>LLM 调用成本</td><td>ToT/LATS 每步多次调用，成本是 ReAct 的 5-20 倍</td><td>简单任务不要过度工程化，先用 ReAct 基线</td></tr>
<tr><td>延迟要求</td><td>多路径搜索和迭代反思显著增加延迟</td><td>在线低延迟场景用 ReAct/Plan-Execute；离线任务可用 ToT/Reflexion</td></tr>
<tr><td>确定性要求</td><td>搜索类范式（ToT/LATS）输出路径不确定</td><td>需要可复现的工作流用 Plan-and-Execute，规划阶段可人工审核</td></tr>
<tr><td>工具可靠性</td><td>工具返回错误时，ReAct 容易陷入死循环</td><td>加最大迭代次数限制 + Reflexion 式错误反思</td></tr>
<tr><td>可观测性</td><td>多分支搜索难以 debug</td><td>记录完整 thought/action/observation 轨迹，支持 replay</td></tr>
</table>
</div>

<div class="card card-s">
<h3>混合范式：生产系统的真实架构</h3>
<p>实际 Agent 系统几乎不会只用单一范式，而是多层嵌套组合。典型的混合架构：</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">外层：Plan-and-Execute</div><div class="flow-desc">接收用户任务后，Planner 生成高层步骤计划，确定需要哪些子任务</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">中层：Self-Ask 分解</div><div class="flow-desc">每个复杂子任务用 Self-Ask 分解为更小的可执行单元</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">内层：ReAct 执行</div><div class="flow-desc">每个原子步骤用 ReAct 循环：思考→调用工具→观察结果，直到子任务完成</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">失败：Reflexion 反思</div><div class="flow-desc">子任务失败时，触发 Reflexion 生成反思，调整策略重试（最多 N 次）</div></div>
<div class="flow-step"><div class="flow-index">05</div><div class="flow-title">重规划</div><div class="flow-desc">如果某步反复失败或发现计划不合理，回到 Planner 更新剩余步骤</div></div>
</div>
<div class="qa-summary">LangGraph、AutoGPT、MetaGPT 等框架本质上都是在实现这种混合范式：外层规划 + 内层 ReAct + 失败反思 + 重规划。理解各范式的职责边界比记住单个范式更重要。</div>
</div>

<div class="card card-d">
<h3>记忆如何增强各范式</h3>
<table>
<tr><th>记忆类型</th><th>内容</th><th>增强的范式</th></tr>
<tr><td>短期记忆（上下文）</td><td>当前对话/任务的 thought/action/observation 历史</td><td>所有范式都依赖</td></tr>
<tr><td>情景记忆（Episodic）</td><td>过去的任务轨迹、成功/失败经验、Reflexion 反思</td><td>Reflexion（核心依赖）、LATS</td></tr>
<tr><td>语义记忆（Semantic）</td><td>领域知识、工具文档、API 说明、事实知识</td><td>所有范式（通过 RAG 注入）</td></tr>
<tr><td>程序记忆（Procedural）</td><td>技能、策略、SOP、常见任务的标准流程</td><td>Plan-and-Execute（从程序记忆生成计划）</td></tr>
</table>
<p>Reflexion 的情景记忆是关键创新——它让 Agent 能「从自己的错误中学习」，而不依赖模型微调。每次失败后的语言反思，本质上是在程序记忆中积累「什么情况下不要做什么」的策略知识。</p>
</div>

<div class="card card-r">
<h3>范式使用的失败模式与防护</h3>
<p>高级范式带来能力提升的同时，也引入新的失败模式，工程中必须做防护：</p>
<table>
<tr><th>范式</th><th>典型失败模式</th><th>防护措施</th></tr>
<tr><td>ReAct</td><td>无限循环（同样的 Action-Observation 重复）、动作空间爆炸</td><td>最大迭代次数限制（如 15 步）、检测重复动作强制终止、超时控制</td></tr>
<tr><td>Reflexion</td><td>反思本身错误、过度反思导致上下文膨胀、反思记忆冲突</td><td>限制反思次数（通常 2-3 次）、记忆只保留最近 N 条最相关反思、反思后要有 evaluator 验证改进</td></tr>
<tr><td>ToT/LATS</td><td>搜索树爆炸、评估器偏差导致错误剪枝、计算成本失控</td><td>限制搜索宽度（每步最多 3-5 个分支）和深度（最多 5-8 层）、总 token 预算控制、beam search 替代全搜索</td></tr>
<tr><td>Plan-and-Execute</td><td>初始计划质量差导致反复重规划、计划步骤粒度不均、重规划震荡</td><td>Planner 输出后用 Critic 审核计划、限制最大重规划次数、步骤粒度标准化</td></tr>
<tr><td>Self-Ask</td><td>子问题无限递归、子问题答案错误级联</td><td>限制子问题深度（最多 3 层）、子问题答案验证、避免重复问相同问题</td></tr>
</table>
<div class="qa-summary">所有搜索/迭代类范式都必须有「熔断机制」：步数限制、token 预算、超时时间。不要让 Agent 无限循环烧钱。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Reflexion 的反思存在哪里？</div>
<div class="qa-a">
<p>Reflexion 的反思存在<strong>情景记忆（episodic memory）</strong>里，通常是一个持久化的列表结构（内存或向量库）。每次尝试失败后，模型生成一段自然语言反思文本，描述「这次错在哪、为什么错、下次怎么做」，然后追加到记忆中。</p>
<p>下一次尝试时，系统会把历史反思（最近几次最相关的）作为额外上下文注入 prompt，模型「读到自己之前的错误总结」，从而避免重蹈覆辙。注意这是<strong>在上下文中学习（in-context learning）</strong>，不更新模型权重。</p>
<div class="qa-summary">存在 episodic memory，以自然语言文本形式追加，下次尝试时作为上下文注入，属于 in-context 改进而非微调。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ToT 和 CoT 的区别？</div>
<div class="qa-a">
<table><tr><th>维度</th><th>CoT（思维链）</th><th>ToT（思维树）</th></tr><tr><td>结构</td><td>线性链，单路径</td><td>树结构，多路径</td></tr><tr><td>回溯</td><td>无，错了就错了</td><td>可以剪枝回溯到上一分支</td></tr><tr><td>评估</td><td>不评估，直接走到底</td><td>每个 thought 用 LLM 打分</td></tr><tr><td>搜索</td><td>无</td><td>BFS/DFS 搜索最优路径</td></tr><tr><td>成本</td><td>低（1 次 LLM 调用）</td><td>高（生成+评估多轮 LLM 调用）</td></tr><tr><td>适用</td><td>有明确解法的问题</td><td>需要规划/探索/试错的问题</td></tr></table>
<p>类比：CoT 是「闭着眼睛走直线」，ToT 是「每到岔路口就评估哪条路好，走错了退回来换路」。</p>
<div class="qa-summary">CoT 线性单路径无回溯，ToT 树状多路径可回溯剪枝有状态评估；CoT 成本低适合简单推理，ToT 成本高适合复杂规划搜索。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Plan-and-Execute vs ReAct 什么时候用哪个？</div>
<div class="qa-a">
<p><strong>用 ReAct 当：</strong></p>
<ul><li>任务简单、步骤少（1-5 步）</li><li>环境动态变化，需要实时响应</li><li>不确定需要多少步，需要探索</li><li>快速原型开发</li></ul>
<p><strong>用 Plan-and-Execute 当：</strong></p>
<ul><li>任务复杂、步骤多（5 步以上）</li><li>步骤依赖关系明确（先做 A 再做 B 再做 C）</li><li>需要全局最优（如旅行规划、多步骤 API 编排）</li><li>需要可审计、可预测的执行路径</li></ul>
<p><strong>工程实践：</strong>实际系统中常见混合模式——Plan-and-Execute 作为外层框架，每个步骤内部用 ReAct 处理子任务；执行失败时触发 Replanner 重新规划剩余步骤，而不是从头开始。</p>
<div class="qa-summary">简单动态探索任务用 ReAct；长周期结构化工作流用 Plan-and-Execute；复杂系统可外层 Plan 内层 ReAct + 失败重规划。</div>
</div>
</div>

## 关联模块

- `01-agent-concepts.md`：Agent 基础概念与 ReAct 入门
- `02-agent-components.md`：Agent 记忆、工具、规划组件详解
- `03-agent-engineering.md`：Agent 工程化实践
- `07-function-calling-api.md`：Function Calling 底层机制
