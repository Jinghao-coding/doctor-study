<div class="card card-m">
<h3>调度研究路线图</h3>
<p>如果你的研究方向是调度，建议把学习重心从"知道系统组件"提升到"能建模问题、定义指标、提出策略、解释权衡、设计实验"。下面这条路线可以作为后续补充论文、项目和面试表达的主线。</p>
</div>

<div class="card card-s">
<h3>四层知识结构</h3>
<p>调度方向的知识可以分为四层。每一层解决不同的问题，面试时也需要在不同层之间切换。</p>

<table>
<tr><th>层次</th><th>要掌握什么</th><th>面试期望</th><th>放在哪个模块</th><th>学习方式</th></tr>
<tr><td>理论层</td><td>FIFO/SJF/SRTF/EDF、DRF、Max-Min、bin packing、backfill</td><td>能手推算法、说清楚性质和局限</td><td>任务调度理论</td><td>推演例题 + 对比分析</td></tr>
<tr><td>机制层</td><td>Scheduling Framework、队列、cache、preemption、plugin</td><td>能画出调度流程、说清楚每个扩展点的作用</td><td>Kubernetes 核心</td><td>读源码 + 画流程图</td></tr>
<tr><td>AI 集群层</td><td>Gang、Kueue、Volcano、拓扑、GPU sharing、多租户</td><td>能说清楚为什么 K8S 默认不够、怎么扩展</td><td>GPU 集群管理</td><td>读论文 + 用框架</td></tr>
<tr><td>系统设计层</td><td>多租户 GPU 调度器、训练平台、推理调度、容错系统</td><td>能从零设计一个调度系统、说清楚架构权衡</td><td>系统设计题</td><td>模拟面试 + 画架构图</td></tr>
</table>

<h4>怎么理解四层的关系</h4>
<p><strong>理论层</strong>是"为什么这样做"——算法的数学基础和性质保证。</p>
<p><strong>机制层</strong>是"怎么在 K8S 里实现"——框架提供的扩展点和数据流。</p>
<p><strong>AI 集群层</strong>是"GPU 训练场景需要什么"——K8S 默认不支持的语义和策略。</p>
<p><strong>系统设计层</strong>是"怎么从头搭建一个完整系统"——从需求到架构到实现。</p>
<p>面试时，好的回答会在四层之间自然切换：从理论出发，落在机制实现，结合 AI 集群场景，最后上升到系统设计。</p>
</div>

<div class="card card-d">
<h3>论文/项目分析模板</h3>
<p>读调度论文或做调度项目时，用这个 7 维框架分析。面试时如果被问"你最近读了什么调度论文"，按这个框架回答会非常清晰。</p>

<h4>7 个维度详解</h4>

<p><strong>1. Workload（负载类型）</strong></p>
<p>这篇论文/项目针对什么类型的负载？在线推理、离线训练、HPC、混部、实验平台？不同负载的调度需求完全不同。</p>
<p><strong>面试中怎么用</strong>：先说 workload 类型，再说策略。因为策略好不好取决于 workload 是否匹配。一个对推理有效的策略用在训练上可能适得其反。</p>

<p><strong>2. Resource（资源模型）</strong></p>
<p>考虑了哪些资源维度？CPU、内存、GPU、显存、网络、存储、拓扑、异构型号？资源模型决定了调度问题的复杂度。</p>
<p><strong>面试中怎么用</strong>：说清楚"论文假设了什么资源模型"和"这个假设在真实集群里是否成立"。</p>

<p><strong>3. Constraint（约束条件）</strong></p>
<p>任务有哪些硬约束和软约束？gang、deadline、quota、affinity、checkpoint、故障域？约束决定了可行解空间。</p>
<p><strong>面试中怎么用</strong>：约束越多，问题越难，但也越有优化空间。说清楚论文考虑了哪些约束、忽略了哪些。</p>

<p><strong>4. Objective（优化目标）</strong></p>
<p>优化什么指标？JCT、SLO、利用率、公平性、抢占成本、能耗？多目标之间的优先级是什么？</p>
<p><strong>面试中怎么用</strong>：目标函数是调度的灵魂。说不清优化什么，算法就是空中楼阁。</p>

<p><strong>5. Strategy（调度策略）</strong></p>
<p>用什么方法？排序、过滤、打分、准入、抢占、回收、backfill、预测？策略是目标函数的具体实现。</p>
<p><strong>面试中怎么用</strong>：说清楚策略和目标的对应关系——每个策略组件优化了什么指标，牺牲了什么。</p>

<p><strong>6. Implementation（落地方式）</strong></p>
<p>怎么在系统里实现？K8S plugin、operator、queue controller、DRA driver、sidecar、agent？</p>
<p><strong>面试中怎么用</strong>：只谈策略不谈落地是"纸上谈兵"。说清楚怎么在 K8S 生态里实现。</p>

<p><strong>7. Experiment（实验验证）</strong></p>
<p>怎么证明有效？baseline、ablation、指标、trace、规模、失败案例？</p>
<p><strong>面试中怎么用</strong>：好的实验设计比好的策略更能打动面试官——因为它展示了你的科学思维。</p>
</div>

<div class="card card-w">
<h3>调度方向面试表达</h3>
<p>面试中关于调度的问答，核心是展示三个能力：(1) 能建模问题——说清楚场景、约束和目标；(2) 能解释权衡——没有银弹，每个策略都有代价；(3) 能设计系统——从理论到落地。</p>

<h4>5 个高频问题的回答框架</h4>

<p><strong>Q1: 你为什么关注调度？</strong></p>
<ul>
<li><strong>切入点</strong>：资源昂贵 + workload 差异大 + 目标冲突明显，调度决定成本、性能和公平性。</li>
<li><strong>展开</strong>：GPU 集群的调度和传统 CPU 调度有三个本质区别——Gang 语义、拓扑敏感、抢占代价高。这些区别让通用调度器不够用，需要专门的 AI 集群调度。</li>
</ul>

<p><strong>Q2: 你如何设计调度策略？</strong></p>
<ul>
<li><strong>框架</strong>：先定义 workload 和指标，再拆成排序、准入、放置、抢占、回收五个决策点。</li>
<li><strong>展开</strong>：排序决定谁先调度（QueueSort/SJF/DRF），准入决定是否放行（Gang/Quota），放置决定放哪（Score/拓扑），抢占决定谁让位（代价感知），回收决定怎么拿回借用资源（QAD 驱动）。</li>
</ul>

<p><strong>Q3: 你如何评价调度系统？</strong></p>
<ul>
<li><strong>指标体系</strong>：JCT、等待时间、利用率、公平性、SLO、抢占损失和调度器吞吐。</li>
<li><strong>展开</strong>：不同场景的指标优先级不同。推理看 SLO 和吞吐，训练看 JCT 和利用率，实验平台看等待时间和公平性。关键是说清楚你优化了什么、牺牲了什么。</li>
</ul>

<p><strong>Q4: K8S 默认调度器哪里不够？</strong></p>
<ul>
<li><strong>核心回答</strong>：默认调度器偏通用 Pod 放置，对 gang、队列公平、GPU 拓扑、训练弹性和设备属性表达不足。</li>
<li><strong>展开</strong>：(1) 不支持 gang——每个 Pod 独立调度，partial allocation 导致 GPU 空转。(2) 不支持队列公平——只有优先级，没有 DRF/Elastic Quota。(3) 不理解 GPU 拓扑——只看资源数量，不看设备连接关系。(4) 不支持弹性训练——world size 固定。(5) 设备属性表达不足——Device Plugin 只报告数量，不报告拓扑和 MIG 归属。</li>
</ul>

<p><strong>Q5: AI 训练调度难在哪里？</strong></p>
<ul>
<li><strong>核心回答</strong>：组调度、拓扑敏感、故障恢复、checkpoint、异构 GPU、多租户公平同时存在。</li>
<li><strong>展开</strong>：每个维度都增加了约束，约束越多问题越难。但约束越多也意味着有更多优化空间——如果所有约束都处理好了，调度效果可以比通用调度器好 2-5 倍。</li>
</ul>
</div>

<div class="card card-m">
<h3>学习路线建议</h3>
<p>如果你刚开始学调度，按这个顺序推进：</p>

<h4>Phase 1：理论基础（1-2 周）</h4>
<ol>
<li>掌握经典调度算法：FIFO、SJF、SRTF、EDF、Round Robin——能手推、能说优劣</li>
<li>掌握 DRF 和 Max-Min Fairness——能手推分配过程</li>
<li>掌握评价指标：JCT、Waiting Time、Makespan、Throughput、Utilization、Fairness——能说清楚定义、场景和冲突</li>
</ol>

<h4>Phase 2：K8S 机制（1-2 周）</h4>
<ol>
<li>理解 Scheduling Framework 的 8 个扩展点——能画出调度流程</li>
<li>理解三个队列（ActiveQ、BackoffQ、UnschedulableQ）——能说清楚 Pod 的流转</li>
<li>理解 scheduler cache、assumed pod、binding cycle——能解释并发调度</li>
<li>理解 preemption 流程——能说清楚 PostFilter + Nominate</li>
</ol>

<h4>Phase 3：AI 集群调度（2-3 周）</h4>
<ol>
<li>理解 Gang Scheduling 和 Backfill——能推演场景</li>
<li>理解拓扑感知调度——能说清不同并行策略的拓扑偏好</li>
<li>理解 GPU sharing（MIG、MPS、time-slicing）——能说清适用场景</li>
<li>理解多租户公平（Elastic Quota、QAD）——能设计队列系统</li>
<li>读 2-3 篇调度论文，用 7 维框架分析</li>
</ol>

<h4>Phase 4：系统设计（1-2 周）</h4>
<ol>
<li>练习"从零设计一个多租户 GPU 调度器"</li>
<li>练习"设计一个训练平台调度系统"</li>
<li>练习"设计一个推理调度系统"</li>
<li>对每个设计，说清楚架构、策略、权衡和验证</li>
</ol>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 哪些内容不应该塞进 K8S 模块？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>通用调度算法、公平性理论、backfill、评价指标和研究方法不应全部放进 K8S；它们应放在"任务调度理论"。K8S 模块只承载 Kubernetes 的实现机制和扩展点。GPU 拓扑、训练任务、队列治理应放在"GPU 集群管理"。这样结构更清晰，也更符合你的调度研究方向。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么这样分</div><p>K8S 是"怎么做"（实现机制），调度理论是"为什么这样做"（算法基础），GPU 集群管理是"在什么场景下做"（领域约束）。三层各司其职，面试时可以从任何一层切入，自然延伸到其他层。</p></div>
<div class="qa-summary">面试要点：模块划分反映的是思考层次——理论、机制、场景三层，不要混在一起。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试时被问到调度论文，怎么回答最有区分度？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答框架</div><p>用 7 维框架组织回答：</p>
<ol>
<li><strong>Workload</strong>：这篇论文针对什么负载？和你的场景有什么关系？</li>
<li><strong>Objective</strong>：优化了什么指标？牺牲了什么？</li>
<li><strong>Strategy</strong>：核心策略是什么？为什么比 baseline 好？</li>
<li><strong>Limitation</strong>：论文的假设在真实集群里是否成立？你觉得哪里不 work？</li>
<li><strong>如果你来做</strong>：你会怎么改进？</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">区分度在哪</div><p>大多数候选人只会总结论文内容。如果你能指出"这个假设不成立"或"这个策略在我的场景里不适用"，并给出改进思路，这比论文本身更有价值。</p></div>
<div class="qa-summary">面试金句："论文的价值不只是它解决了什么问题，更是它暴露了什么假设。能指出假设的局限，比能复述结论更有区分度。"</div>
</div>
</div>
