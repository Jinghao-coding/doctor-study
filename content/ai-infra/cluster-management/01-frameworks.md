## 一句话结论

GPU 集群管理这一节需要服务面试复习：先给结论，再把链路、机制、权衡和回答模板讲清楚。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | GPU 集群管理 |
| 章节类型 | 系统类 |
| 解决问题 | 围绕调度框架、多租户、拓扑通信、故障容错和面试问答建立集群管理答案。 |
| 面试抓手 | 回答时先定范围，再讲核心链路，最后落到工程风险和面试追问。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m">
<h3>GPU 集群调度框架：为什么不能只用 K8S 默认调度器？</h3>
<p>K8S 默认调度器（kube-scheduler）是为微服务设计的：每个 Pod 独立调度、无状态、可随时驱逐。但 GPU 训练任务截然不同：<strong>Gang scheduling</strong>（要么全部启动，要么一个不动）、<strong>长时间运行</strong>（小时到天级）、<strong>拓扑敏感</strong>（NVLink/InfiniBand 通信延迟决定训练速度）、<strong>多租户公平</strong>（不能让一个团队占满所有 GPU）。</p>
<p>所以 GPU 集群需要在 K8S 之上或之外增加"批调度"能力。这就是 Volcano、Yunikorn、Kueue 这类框架存在的意义——它们不是替代 K8S 调度器，而是在其上层补充批处理所需的高级语义。</p>
<p><strong>怎么理解</strong>：K8S 默认调度器像"出租车调度"——每次派一辆车，独立接客。GPU 集群调度像"旅游团调度"——必须一次性派出 8 辆大巴（Gang），路线要优化（拓扑），不同旅行社要公平分配（多租户），中途车坏了要快速替换（弹性）。</p>
</div>

<div class="card card-s">
<h3>框架核心架构详解</h3>

<h4>1. Volcano：K8S 原生批调度器</h4>
<p><strong>定位</strong>：CNCF 孵化项目，K8S 原生的批处理调度器，专为 AI/ML 场景设计。</p>
<p><strong>核心架构</strong>：三个核心 CRD + 一个调度引擎：</p>
<ul>
<li><strong>PodGroup</strong>：定义一组 Pod 的 Gang 语义。关键字段 <code>minMember</code>——至少要同时启动多少个 Pod，任务才算"就绪"。如果集群资源不够同时启动 minMember 个 Pod，所有 Pod 都处于 Pending，不会出现"启动了 3/8 个 worker，剩下 5 个卡在 Pending 导致 NCCL 超时"的情况。</li>
<li><strong>Queue</strong>：多租户配额管理。每个团队/项目对应一个 Queue，Queue 有 <code>capability</code>（最大资源上限）和 <code>guarantee</code>（保障资源量）。Queue 之间可以 reclaim（抢占借用资源）。</li>
<li><strong>Job（vc-job）</strong>：封装一个完整的训练任务，包含多个 task（如 1 个 master + N 个 worker）。Job 关联一个 PodGroup 和一个 Queue。</li>
</ul>
<p><strong>调度流程</strong>：</p>
<ol>
<li>用户提交 Volcano Job → 创建 PodGroup + 一组 Pod</li>
<li>Volcano 调度器检查 PodGroup 的 minMember 是否满足（集群剩余资源 ≥ minMember × 单 Pod 资源）</li>
<li>满足 → 所有 Pod 同时调度（Gang）；不满足 → 全部等待</li>
<li>Queue 检查：该团队是否还有配额？配额不足 → 排队或抢占</li>
</ol>
<p><strong>支持的调度策略</strong>：通过 <code>plugins</code> 配置，可组合使用——<code>gang</code>（Gang scheduling）、<code>drf</code>（主导资源公平）、<code>proportion</code>（按比例分配）、<code>priority</code>（优先级）、<code>sla</code>（等待时间加权）。</p>
<p><strong>怎么理解 PodGroup</strong>：像一个"旅行团的最低成团人数"。一个 8 人团，至少 8 人都买票才出发。如果只有 5 个人到，大巴不开——因为 5 个人去了也没法完成旅行计划（对应 NCCL 需要所有 rank 才能建环）。</p>

<h4>2. Yunikorn：多租户资源管理器</h4>
<p><strong>定位</strong>：Apache 项目，源自 YARN 设计理念，支持 K8S 和 YARN 双调度，强项是层级队列和应用感知调度。</p>
<p><strong>核心架构</strong>：</p>
<ul>
<li><strong>层级队列（Hierarchical Queue）</strong>：队列可以嵌套——公司 > 部门 > 团队，每层有自己的配额。父队列的配额在子队列之间分配。这比 Volcano 的扁平 Queue 更适合大型组织的资源治理。</li>
<li><strong>Application 级调度</strong>：Yunikorn 把一组相关 Pod 识别为一个 Application，在 Application 内部做 Gang-like 的调度（ask → allocation），而不是逐个 Pod 独立调度。</li>
<li><strong>调度器替换模式</strong>：Yunikorn 可以完全替换 kube-scheduler（作为 K8S 的调度器运行），而不是像 Volcano 那样作为 secondary scheduler。</li>
</ul>
<p><strong>和 Volcano 的本质区别</strong>：Volcano 是"K8S 调度框架的插件"（SchedulingFramework plugin），和默认调度器共存。Yunikorn 是"替换调度器"，自己管理整个调度流程。这带来了不同的运维复杂度和灵活性 trade-off。</p>
<p><strong>怎么理解层级队列</strong>：像一个公司的预算体系。公司总预算 1000 万 → NLP 部门分 400 万 → NLP-1 组分 150 万。如果 NLP-1 组只用了 100 万，剩下的 50 万可以被 NLP-2 组借用。但 NLP 部门总共不能超过 400 万。</p>

<h4>3. Kueue：作业排队管理器</h4>
<p><strong>定位</strong>：K8S SIGs 官方项目（sig-scheduling），聚焦于"作业排队"，不直接做调度决策，而是把排队逻辑从调度器中解耦出来。</p>
<p><strong>核心概念</strong>：</p>
<ul>
<li><strong>ResourceFlavor</strong>：抽象一种"资源口味"。例如 <code>a100-flavor</code> 表示 A100 GPU 节点池，<code>h100-flavor</code> 表示 H100 GPU 节点池。不同 flavor 可以有不同的拓扑、性能、成本。这是 Kueue 对异构资源的关键抽象。</li>
<li><strong>ClusterQueue</strong>：集群级别的队列，关联一个或多个 ResourceFlavor，定义配额（nominal quota + borrowing quota）。每个租户对应一个 ClusterQueue。</li>
<li><strong>LocalQueue</strong>：命名空间级别的队列，用户提交作业到 LocalQueue，LocalQueue 映射到 ClusterQueue。对用户来说只看到 LocalQueue（简单的名字），不需要关心底层的 ClusterQueue 和 ResourceFlavor 配置。</li>
<li><strong>Workload</strong>：Kueue 对"作业"的抽象。一个 Workload 包含一组 PodSet（如 1 个 launcher PodSet + 1 个 worker PodSet），Kueue 为整个 Workload 做准入决策。</li>
</ul>
<p><strong>调度流程</strong>：</p>
<ol>
<li>用户提交 Job（如 PyTorchJob）→ Kueue 的 webhook 自动创建对应的 Workload 对象</li>
<li>Workload 进入 ClusterQueue 排队</li>
<li>Kueue 检查：该 ClusterQueue 在某个 ResourceFlavor 下是否有足够配额？</li>
<li>有配额 → 准入（admit），给 Job 的 Pod 打上 nodeSelector 标签，让 K8S 调度器把 Pod 调到对应 flavor 的节点</li>
<li>没配额 → 排队等待，或检查是否可以 borrowing</li>
</ol>
<p><strong>关键设计：Kueue 不做 Pod 级调度</strong>。它只做"准入决策"（这个 Job 能不能开始？在哪个 flavor 上跑？），具体的 Pod→Node 绑定还是交给 K8S 默认调度器。这种分层设计让 Kueue 不需要重新实现拓扑感知、亲和性等功能，复用 K8S 调度器的能力。</p>
<p><strong>怎么理解 Kueue 的分层</strong>：Kueue 像"电影院的售票系统"——它决定你这个团能不能进场、坐在哪个区域（flavor），但具体的座位（哪个节点）由领位员（K8S 调度器）安排。售票系统和领位员各司其职。</p>

<h4>4. Run:ai：商业 GPU 虚拟化平台</h4>
<p><strong>定位</strong>：商业产品，提供 GPU 分时共享、配额管理、可视化面板等一站式能力。</p>
<p><strong>核心能力</strong>：</p>
<ul>
<li><strong>GPU 分时共享</strong>：一张 GPU 可以时间片轮转给多个任务，适合 I/O 密集型任务（数据加载时空闲的 GPU 时间可以给别人用）。</li>
<li><strong>配额策略</strong>：支持 over-quota borrowing、project-level 配额、优先级调度。</li>
<li><strong>可视化</strong>：GPU 利用率仪表盘、训练任务监控、成本归因。</li>
</ul>
<p><strong>局限</strong>：闭源商业产品，定制化受限。大规模场景下（>1000 GPU）的性能和稳定性不如自研方案。无法深度定制调度策略（如 checkpoint-aware preemption、拓扑感知等）。</p>
</div>

<div class="card card-d">
<h3>框架深度对比</h3>
<table>
<tr><th>维度</th><th>Volcano</th><th>Yunikorn</th><th>Kueue</th><th>Run:ai</th></tr>
<tr><td>定位</td><td>K8S 批调度插件</td><td>多租户资源管理器</td><td>作业排队管理器</td><td>GPU 虚拟化平台</td></tr>
<tr><td>调度器关系</td><td>与 K8S 调度器共存（SchedulingFramework plugin）</td><td>替换 K8S 调度器</td><td>在 K8S 调度器之上做准入</td><td>替换 + 扩展</td></tr>
<tr><td>Gang Scheduling</td><td>PodGroup + minMember</td><td>Application Gang</td><td>Workload PodSet（配合调度器 gang 插件）</td><td>支持</td></tr>
<tr><td>队列模型</td><td>扁平 Queue</td><td>层级 Queue（嵌套）</td><td>ClusterQueue + LocalQueue</td><td>Project Queue</td></tr>
<tr><td>异构资源表达</td><td>Queue capability</td><td>Node partition</td><td>ResourceFlavor（核心优势）</td><td>GPU 类型标签</td></tr>
<tr><td>配额模型</td><td>静态 min/max</td><td>guaranteed/max + borrowing</td><td>nominal + borrowing</td><td>over-quota borrowing</td></tr>
<tr><td>公平性</td><td>DRF / proportion</td><td>FIFO / Fair / FIFO</td><td>BestEffortFIFO / FairSharing</td><td>优先级 + 公平</td></tr>
<tr><td>GPU 拓扑感知</td><td>有限（需配合 device plugin）</td><td>有限</td><td>复用 K8S 调度器</td><td>基础支持</td></tr>
<tr><td>社区活跃度</td><td>高（CNCF 孵化）</td><td>中（Apache）</td><td>高（K8S SIGs）</td><td>商业</td></tr>
<tr><td>成熟度</td><td>生产可用</td><td>生产可用</td><td>快速成熟中</td><td>生产可用</td></tr>
<tr><td>核心局限</td><td>配额弹性不够灵活、无干扰感知</td><td>GPU 拓扑支持有限、学习曲线陡</td><td>较新，生态发展中</td><td>闭源、大规模定制受限</td></tr>
</table>

<h4>怎么选择？</h4>
<table>
<tr><th>场景</th><th>推荐</th><th>原因</th></tr>
<tr><td>纯 K8S 环境 + 训练为主</td><td>Volcano</td><td>Gang scheduling 成熟，社区大，和 K8S 集成最深</td></tr>
<tr><td>大型组织 + 层级资源治理</td><td>Yunikorn</td><td>层级队列天然匹配组织结构，跨 K8S/YARN</td></tr>
<tr><td>异构 GPU 集群 + 渐进式采用</td><td>Kueue</td><td>ResourceFlavor 精准表达异构，不动调度器只加排队层</td></tr>
<tr><td>快速 PoC + 可视化需求</td><td>Run:ai</td><td>开箱即用，不需要自研</td></tr>
<tr><td>大规模（>1000 GPU）+ 深度定制</td><td>自研调度器</td><td>上述框架都有限，需要原生构建</td></tr>
</table>
</div>

<div class="card card-w">
<h3>框架与 K8S Scheduling Framework 的映射</h3>
<p>理解一个框架的实现，关键是看它用了 Scheduling Framework 的哪些扩展点：</p>
<table>
<tr><th>扩展点</th><th>Volcano 用了什么</th><th>Kueue 用了什么</th><th>作用</th></tr>
<tr><td>QueueSort</td><td>优先级 + DRF 排序</td><td>不使用（自己管理队列）</td><td>决定 Pod 的调度顺序</td></tr>
<tr><td>PreFilter</td><td>Gang 检查（minMember 是否可能满足）</td><td>不使用</td><td>快速排除不可调度的 Pod</td></tr>
<tr><td>Filter</td><td>Queue 配额检查</td><td>不使用（准入在调度前完成）</td><td>排除不满足约束的节点</td></tr>
<tr><td>Score</td><td>Bin Packing / Spread / DRF 打分</td><td>不使用</td><td>给候选节点打分排序</td></tr>
<tr><td>Reserve</td><td>Gang reserve（占位但未绑定）</td><td>不使用</td><td>预留资源等待 Gang 成员</td></tr>
<tr><td>Permit</td><td>Gang 等待（等所有成员 reserve）</td><td>不使用</td><td>批准或拒绝绑定</td></tr>
<tr><td>Preempt</td><td>优先级抢占</td><td>不使用（自己管理抢占）</td><td>驱逐低优先级 Pod</td></tr>
<tr><td>Bind</td><td>自定义绑定逻辑</td><td>不使用</td><td>绑定 Pod 到 Node</td></tr>
</table>
<p><strong>关键洞察</strong>：Volcano 深度嵌入 Scheduling Framework，几乎用了所有扩展点。Kueue 完全不嵌入——它通过 webhook 在 Pod 创建前做准入，通过 nodeSelector 影响调度，自己的逻辑和 K8S 调度器完全解耦。这是两种截然不同的架构选择，各有 trade-off：</p>
<ul>
<li><strong>Volcano 方式</strong>：控制力强，能精细控制调度流程每个步骤。但和 K8S 调度器强耦合，升级风险大。</li>
<li><strong>Kueue 方式</strong>：解耦，升级安全，复用 K8S 调度器的能力。但无法控制调度内部细节（如 Permit 阶段的 Gang 等待逻辑）。</li>
</ul>
</div>

<div class="card card-m">
<h3>调度框架面试问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Volcano 的核心设计？它的局限性？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>Volcano 的核心是 <strong>PodGroup + Queue + Policy</strong> 三件套：</p>
<ol>
<li><strong>PodGroup</strong> 定义 Gang 语义——minMember 个 Pod 必须同时就绪，任务才算启动。这解决了 NCCL 初始化需要所有 rank 在线的问题。</li>
<li><strong>Queue</strong> 管理多租户配额——每个团队一个 Queue，有 capability（上限）和 guarantee（保障），支持 reclaim 抢占。</li>
<li><strong>Policy</strong> 定义调度策略——支持 gang、drf、proportion、priority 等插件，可组合使用。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">局限性</div><p>(1) <strong>配额是静态 min/max</strong>：不支持连续保障度信号（如 QAD ≥ 0.95），配额弹性不够灵活。(2) <strong>没有干扰感知合用</strong>：多个任务共享 GPU 时无法感知性能干扰。(3) <strong>不做运行时间预测</strong>：无法基于预测做更优的排序或 backfill。(4) <strong>抢占是简单优先级抢占</strong>：不考虑沉没成本（checkpoint 年龄、已运行时间），可能抢占一个训练了 20 小时的任务。(5) <strong>Gang 调度的 Partial Allocation 问题</strong>：当资源不够一个完整的 Gang 时，所有资源闲置等待，无法做 backfill。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"Volcano 解决了 K8S 做 GPU 批调度的核心缺失——Gang + Queue，但它的配额和抢占模型偏简单。在需要弹性配额、代价感知抢占、运行时间预测等能力时，需要从 Scheduling Framework 原生构建。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Kueue 的 ResourceFlavor 是什么？为什么重要？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>ResourceFlavor 抽象了"一种类型的资源池"。例如：</p>
<ul>
<li><code>a100-flavor</code>：A100 80GB GPU 节点池，带 NVLink + InfiniBand</li>
<li><code>h100-flavor</code>：H100 GPU 节点池，更新一代</li>
<li><code>v100-spot-flavor</code>：V100 抢占式 GPU，便宜但可能被回收</li>
</ul>
<p>每个 ClusterQueue 关联多个 ResourceFlavor，每个 flavor 有独立的配额。Workload 提交时可以指定偏好顺序，Kueue 根据配额和排队情况分配最优 flavor。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么重要</div><p>异构 GPU 集群是现实。一个集群可能同时有 A100、H100、V100，它们的计算能力、显存、拓扑都不同。如果调度器只看到"1 张 GPU"，就会把需要大显存的训练任务调度到 V100（显存不够），或者把轻量推理放到 H100（浪费算力）。ResourceFlavor 让调度器能感知资源的"质"，而不只是"量"。</p></div>
<div class="qa-section"><div class="qa-section-title">和 Volcano 的对比</div><p>Volcano 的 Queue 用 capability 表达配额，但不区分资源类型——一个 Queue 的 capability 写了 16 GPU，但调度器不知道这 16 GPU 是 A100 还是 V100。Kueue 的 ResourceFlavor 在配额层面就区分了，调度决策更精准。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"ResourceFlavor 解决的是异构集群中'量相同但质不同'的调度问题。没有 Flavor，调度器只知道多少张 GPU；有了 Flavor，调度器还知道什么类型的 GPU。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Volcano 和 Kueue 的架构有什么本质区别？各适合什么场景？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>本质区别是<strong>和 K8S 调度器的关系</strong>：</p>
<ul>
<li><strong>Volcano</strong>：嵌入 K8S Scheduling Framework，作为插件运行，控制调度的每一步（QueueSort、Filter、Score、Permit、Bind）。深度耦合，控制力强。</li>
<li><strong>Kueue</strong>：在 K8S 调度器之上做准入控制，通过 webhook + nodeSelector 影响 Pod 的创建和放置。完全解耦，复用调度器能力。</li>
</ul></div>
<div class="qa-section"><div class="qa-section-title">为什么这很重要</div><p>嵌入式的优势是能精细控制：Volcano 可以在 Permit 阶段等待 Gang 成员，在 Preempt 阶段选择牺牲者。但代价是和 K8S 调度器强耦合——K8S 升级可能破坏 Volcano 的行为。解耦式的优势是安全升级，但无法控制调度内部细节——Kueue 不能做"等 Gang 成员 5 秒再决定"这种操作。</p></div>
<div class="qa-section"><div class="qa-section-title">场景选择</div><p>(1) 需要 Gang scheduling 的精细控制（如 Permit 等待、部分分配处理）→ Volcano。(2) 异构 GPU 集群 + 渐进式采用（不想替换调度器）→ Kueue。(3) 大型组织需要层级队列 → Yunikorn。(4) 大规模 + 深度定制 → 自研（基于 Scheduling Framework）。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"Volcano 是嵌入式架构，深度耦合但控制力强；Kueue 是旁路式架构，解耦但依赖调度器能力。选择取决于你对调度细节的控制需求和对升级稳定性的容忍度。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果让你设计一个 GPU 集群调度器，你会怎么选？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>分三个阶段：</p>
<ol>
<li><strong>MVP 阶段</strong>（<100 GPU）：直接用 Volcano，开箱即用的 Gang + Queue + DRF，够用。</li>
<li><strong>规模化阶段</strong>（100-1000 GPU）：基于 K8S Scheduling Framework 自研插件。借鉴 Volcano 的 Gang 实现，但自己实现配额弹性（ElasticQuota 或 QAD）、代价感知抢占、运行时间预测等高级能力。这个规模下，Volcano 的静态配额和简单抢占开始不够用。</li>
<li><strong>超大规模</strong>（>1000 GPU）：考虑独立调度器（不走 K8S Scheduling Framework），直接 watch etcd 做全局调度决策。K8S 调度器的单点调度模型（一个 Pod 一个 cycle）在大规模下成为瓶颈。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">为什么这样选</div><p>每阶段的瓶颈不同。小规模瓶颈是"有没有 Gang scheduling"，Volcano 解决了。中规模瓶颈是"配额弹性和抢占代价"，需要自研。大规模瓶颈是"调度器吞吐"，K8S 调度器架构本身需要改变。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"调度器的设计不是一次性选型，而是随规模演进的。每个规模阶段的瓶颈不同，需要不同的架构选择。关键是说清楚为什么当前阶段选这个架构，以及下一个阶段的演进方向。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Yunikorn 的层级队列有什么优势？什么场景下需要？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>层级队列允许队列嵌套：root → department → team → project。每层有独立的配额，父队列配额在子队列间分配。核心优势是<strong>组织结构的自然映射</strong>。</p></div>
<div class="qa-section"><div class="qa-section-title">具体优势</div><p>(1) <strong>资源治理</strong>：公司 GPU 总量 1000 张 → NLP 部门 400 张 → NLP-1 组 150 张。如果 NLP-1 只用了 100 张，多出的 50 张可以被 NLP-2 借用，但 NLP 部门总量不超过 400 张。(2) <strong>动态调整</strong>：组织结构调整只需要修改队列层级，不需要重新分配每个团队。(3) <strong>公平保证</strong>：父队列的 guarantee 保证子队列的最低资源，borrowing 不影响其他部门的保障。</p></div>
<div class="qa-section"><div class="qa-section-title">什么场景需要</div><p>大型组织（多部门、多团队）的 GPU 共享集群。扁平 Queue 在小团队（5-10 个）够用，但组织层级多了之后，扁平 Queue 的配额管理会变成运维噩梦——每次组织调整都要手动重配所有 Queue。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"层级队列的本质是把组织结构映射到资源治理。不是技术上的刚需，而是管理上的刚需。组织越复杂，层级队列的价值越大。"</p></div>
</div>
</div>
</div>

## 面试回答

**30 秒版：**

GPU 集群管理这一节需要先定范围，再把机制和工程边界讲清楚。 按结论、链路、权衡、风险回答。

**2 分钟版：**

我会先说明这个问题在 GPU 集群管理 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
