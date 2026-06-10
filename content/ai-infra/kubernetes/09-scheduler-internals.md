<div class="card card-m">
<h3>kube-scheduler 内部机制：为什么这部分放在 K8S</h3>
<p>调度研究里有一类问题是通用算法问题，例如公平性、装箱、抢占和 backfill；另一类问题是 Kubernetes 运行时机制问题，例如调度队列、scheduler cache、assumed pod、plugin lifecycle、binding cycle。后者应该放在 K8S 模块，因为它回答的是：<strong>这些算法在 Kubernetes 里到底挂在哪个扩展点、读什么缓存、写什么状态、失败后如何恢复。</strong></p>
</div>

<div class="card card-s">
<h3>一次调度的内部路径</h3>
<ol>
<li><strong>入队：</strong>未绑定 Pod 先进入 scheduling queue。它能不能立刻被调度，取决于优先级、退避状态、历史失败原因和集群事件。</li>
<li><strong>取快照：</strong>scheduler 从 cache 生成本轮调度使用的 NodeInfo snapshot，避免调度过程中反复访问 API Server。</li>
<li><strong>Scheduling Cycle：</strong>执行 QueueSort、PreFilter、Filter、PostFilter、PreScore、Score、NormalizeScore，选出目标节点。</li>
<li><strong>Assume：</strong>在 scheduler cache 中假定 Pod 已经占用目标节点资源，防止后续 Pod 看到过时资源。</li>
<li><strong>Binding Cycle：</strong>执行 Reserve、Permit、PreBind、Bind、PostBind。绑定阶段可以与后续调度周期并行。</li>
<li><strong>状态回滚：</strong>Reserve、Permit 或 Bind 后续失败时，需要通过 Unreserve 或 cache 过期释放临时占用。</li>
</ol>
</div>

<div class="card card-d">
<h3>调度队列总览图</h3>
<p>这张图要抓住一个核心：<strong>队列系统决定“下一个被尝试调度的是谁”，Filter/Score 才决定“它放到哪里”。</strong>因此队列策略会直接影响等待时间、公平性、吞吐和重试风暴。</p>
<div class="sched-flow queue-flow">
<svg viewBox="0 0 1120 610" role="img" aria-label="kube-scheduler scheduling queue flow">
<defs>
<marker id="queueArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
<path d="M0,0 L0,6 L9,3 z" fill="currentColor"></path>
</marker>
</defs>
<text x="34" y="42" class="k8s-title">kube-scheduler 队列流转</text>
<text x="34" y="64" class="k8s-subtitle">activeQ / backoffQ / unschedulablePods / move request</text>

<rect x="40" y="105" width="180" height="86" class="sched-node sched-api"></rect>
<text x="64" y="137" class="sched-label">New / Updated Pod</text>
<text x="64" y="159" class="sched-desc">未绑定 Pod 进入调度器</text>
<text x="64" y="177" class="sched-desc">带 priority / affinity / PVC</text>

<rect x="310" y="90" width="230" height="112" class="sched-node sched-queue"></rect>
<text x="335" y="125" class="sched-label">ActiveQ</text>
<text x="335" y="150" class="sched-desc">当前可以立即尝试调度</text>
<text x="335" y="169" class="sched-desc">内部按 QueueSort 排序</text>
<text x="335" y="188" class="sched-desc">priority、timestamp、plugin 共同影响顺序</text>

<rect x="645" y="90" width="210" height="112" class="sched-node sched-cache"></rect>
<text x="670" y="125" class="sched-label">Scheduling Cycle</text>
<text x="670" y="150" class="sched-desc">PreFilter / Filter / Score</text>
<text x="670" y="169" class="sched-desc">用 snapshot 判断目标节点</text>
<text x="670" y="188" class="sched-desc">成功后进入 assume / bind</text>

<rect x="930" y="105" width="150" height="86" class="sched-node sched-bind"></rect>
<text x="956" y="137" class="sched-label">Bind</text>
<text x="956" y="159" class="sched-desc">写 API Server</text>
<text x="956" y="177" class="sched-desc">Pod 获得 nodeName</text>

<rect x="310" y="295" width="230" height="112" class="sched-node sched-note"></rect>
<text x="335" y="330" class="sched-label">BackoffQ</text>
<text x="335" y="355" class="sched-desc">刚调度失败，进入指数退避</text>
<text x="335" y="374" class="sched-desc">避免 CPU tight loop</text>
<text x="335" y="393" class="sched-desc">到期后回到 ActiveQ</text>

<rect x="645" y="295" width="250" height="112" class="sched-node sched-queue"></rect>
<text x="670" y="330" class="sched-label">UnschedulableQ</text>
<text x="670" y="355" class="sched-desc">当前没有任何可行节点</text>
<text x="670" y="374" class="sched-desc">等待事件提示重新入队</text>
<text x="670" y="393" class="sched-desc">不是按时间轮询为主</text>

<rect x="645" y="485" width="250" height="78" class="sched-node sched-api"></rect>
<text x="670" y="518" class="sched-label">Move request</text>
<text x="670" y="542" class="sched-desc">Node / Pod / PVC / ResourceClaim 等事件触发</text>

<path d="M220 148 C255 148 275 146 310 146" class="sched-arrow"></path>
<path d="M540 146 C585 146 600 146 645 146" class="sched-arrow"></path>
<path d="M855 146 C890 146 900 148 930 148" class="sched-arrow"></path>
<path d="M760 202 C760 235 720 250 700 295" class="sched-arrow sched-dashed"></path>
<path d="M640 202 C600 245 505 250 470 295" class="sched-arrow sched-dashed"></path>
<path d="M425 295 C425 250 425 238 425 202" class="sched-arrow sched-dashed"></path>
<path d="M770 485 C770 448 770 430 770 407" class="sched-arrow sched-dashed"></path>
<path d="M645 525 C540 525 425 470 425 407" class="sched-arrow sched-dashed"></path>

<rect x="40" y="485" width="500" height="78" class="sched-node sched-cache"></rect>
<text x="64" y="518" class="sched-label">面试抓手</text>
<text x="64" y="542" class="sched-desc">ActiveQ 控制机会分配；BackoffQ 控制失败重试节奏；UnschedulableQ 控制事件驱动唤醒；Move request 控制无效重试比例。</text>
</svg>
</div>
</div>

<div class="card card-m">
<h3>一个 Pod 在调度队列里的流转过程</h3>
<p>下面用最直观的文本流程图展示 Pod 从创建到绑定（或失败重试）的完整路径：</p>
<div class="pod-flow-diagram">
<pre class="pod-flow">
<span class="flow-node">新 Pod 创建</span>
    <span class="flow-arrow">↓</span>
<span class="flow-node active">进入 ActiveQ</span>
    <span class="flow-arrow">↓</span>
<span class="flow-node">调度器从 ActiveQ 取出 Pod</span>
    <span class="flow-arrow">↓</span>
<span class="flow-node">尝试调度（Filter → Score → Assume）</span>
    <span class="flow-arrow">↓</span>
    <span class="flow-split">├── 成功 ──→</span> <span class="flow-node success">进入绑定流程（Bind → PostBind）</span>
    <span class="flow-split">│</span>
    <span class="flow-split">└── 失败 ──→</span> <span class="flow-branch">
        <span class="flow-split">├──</span> <span class="flow-node backoff">放入 BackoffQ</span> <span class="flow-note">：等一段时间再试，避免 CPU tight loop</span>
        <span class="flow-split">│</span>    <span class="flow-arrow">↓</span> <span class="flow-note">退避时间到期后回到 ActiveQ</span>
        <span class="flow-split">│</span>
        <span class="flow-split">└──</span> <span class="flow-node unsched">放入 UnschedulableQ</span> <span class="flow-note">：等集群状态变化再试</span>
             <span class="flow-arrow">↓</span> <span class="flow-note">Node/Pod/PVC/ResourceClaim 事件触发 Move request 后回到 ActiveQ</span>
</span>
</pre>
</div>
<div class="qa-summary">核心记忆：ActiveQ 是"现在试试"，BackoffQ 是"过会儿再试"，UnschedulableQ 是"等条件变了再试"。调度器的吞吐和延迟很大程度上取决于这三个队列之间的流转策略。</div>
</div>

<div class="card card-d">
<h3>三个队列分别解决什么问题</h3>
<p>调度器用三个队列管理不同状态的 Pod，而不是把所有 Pod 放在一个队列里轮询。理解这三个队列的<strong>进入条件、退出条件、排序策略和设计意图</strong>，是面试中区分“会用 K8s”和“理解调度器”的关键。</p>
<div class="queue-compare">
<table>
<thead>
<tr><th>维度</th><th class="q-active">ActiveQ</th><th class="q-backoff">BackoffQ</th><th class="q-unsched">UnschedulableQ</th></tr>
</thead>
<tbody>
<tr><td class="q-dim">一句话</td><td>现在试试</td><td>过会儿再试</td><td>等条件变了再试</td></tr>
<tr><td class="q-dim">进入条件</td><td>新 Pod 创建、BackoffQ 到期、事件触发 Move request</td><td>调度失败且失败原因不是“永久不可调度”</td><td>调度失败且当前没有任何节点满足条件</td></tr>
<tr><td class="q-dim">退出条件</td><td>被调度器取出尝试调度</td><td>退避时间到期后移回 ActiveQ</td><td>集群事件（Node/Pod/PVC 变化）触发 Move request</td></tr>
<tr><td class="q-dim">排序策略</td><td>QueueSort 插件：默认按 priority 降序 + 入队时间</td><td>按退避到期时间排序（FIFO）</td><td>不排序，等待事件驱动唤醒</td></tr>
<tr><td class="q-dim">核心问题</td><td>谁先获得调度机会？队头阻塞、饥饿、公平性</td><td>失败后多久重试？退避过短浪费 CPU，过长增加延迟</td><td>什么时候唤醒？事件提示不精准会导致无效重试风暴</td></tr>
<tr><td class="q-dim">AI 场景</td><td>小推理任务、交互式 Notebook 能否插队</td><td>GPU 大作业资源不够时避免频繁扫描节点</td><td>等待 GPU 释放、RDMA 节点加入、PVC 绑定、gang 资源凑齐</td></tr>
<tr><td class="q-dim">面试表达</td><td>Filter/Score 再聪明也只能处理已出队的 Pod；队列排序决定谁先获得机会</td><td>调度器的“冷静期”，把失败重试从忙等变成有节奏的再尝试</td><td>“条件未满足”的等待区；只有相关事件才应触发唤醒</td></tr>
</tbody>
</table>
</div>
<div class="qa-summary">一句话记住：ActiveQ 管“谁先上”，BackoffQ 管“别太急”，UnschedulableQ 管“等时机”。三个队列的流转策略直接影响调度器的吞吐、延迟和公平性。</div>
</div>

<div class="card card-w">
<h3>Move request：为什么事件提示很关键</h3>
<p>Move request 可以理解为“某个集群事件可能让一批不可调度 Pod 重新有机会”。调度器会根据失败原因和事件类型，决定是否把 Pod 从 UnschedulableQ 或 BackoffQ 移回 ActiveQ。</p>
<table>
<tr><th>事件</th><th>可能唤醒哪些 Pod</th><th>为什么</th><th>无效唤醒风险</th></tr>
<tr><td>Node 新增或 Node label 变化</td><td>nodeSelector、nodeAffinity、拓扑约束失败的 Pod</td><td>节点集合或标签变了，Filter 结果可能改变</td><td>如果所有 Pod 都唤醒，会造成全量重试</td></tr>
<tr><td>Pod 删除或完成</td><td>资源不足、端口冲突、反亲和失败的 Pod</td><td>CPU/GPU/内存/端口/拓扑位置被释放</td><td>只释放 CPU 却唤醒 GPU 不足的 Pod，收益很低</td></tr>
<tr><td>PVC 绑定完成</td><td>之前因 volume binding 失败的 Pod</td><td>存储条件满足后才可能通过 Filter</td><td>和存储无关的 Pod 不应被大量唤醒</td></tr>
<tr><td>ResourceSlice / ResourceClaim 变化</td><td>DRA 设备匹配失败的 Pod</td><td>设备库存、属性或 claim 状态变化</td><td>设备事件过粗会导致大量 GPU Pod 重试</td></tr>
<tr><td>PodGroup / quota 变化</td><td>Gang、队列配额、批任务准入失败的 Pod</td><td>组资源或配额条件变化</td><td>准入条件未变化时重试只会消耗调度周期</td></tr>
</table>
<div class="qa-summary">队列性能优化不是“多重试几次”，而是“在正确事件发生后，只唤醒可能变得可调度的 Pod”。</div>
</div>

<div class="card card-m">
<h3>调度问题定位：区分 Pod 属性、调度阶段和调度机制</h3>
<p>在分析 Kubernetes Scheduler 时，需要区分三类概念，<strong>这三类概念不能混在一起</strong>：</p>
<ol>
<li><strong>Pod 属性：</strong>Pod 自身携带的信息，例如优先级、资源请求、节点选择约束等。</li>
<li><strong>调度阶段 / 扩展点：</strong>Scheduler Framework 中处理 Pod 的流程位置，例如 QueueSort、Filter、Score、Reserve、Permit。</li>
<li><strong>调度机制 / 策略：</strong>由多个阶段共同完成的行为，例如抢占、退避重试、Gang 调度、回填调度等。</li>
</ol>
<p>例如，<code>priority</code> 是 Pod 的属性，它会影响队列排序和抢占，但它本身不是调度阶段。<code>Preemption</code> 是调度失败后的抢占机制，通常发生在没有可行节点之后，和 <code>PostFilter</code> 等流程有关，但它也不是普通的节点打分阶段。<code>QueueSort</code>、<code>Filter</code>、<code>Score</code>、<code>Reserve</code>、<code>Permit</code> 才是 Scheduler Framework 中更明确的扩展点。</p>
</div>

<div class="card card-s">
<h3>三类概念对照表</h3>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:140px">类型</th><th>示例</th><th>说明</th></tr>
</thead>
<tbody>
<tr><td class="q-dim">Pod 属性</td><td><code>priority</code>、<code>resource requests</code>、<code>nodeSelector</code>、<code>affinity</code>、<code>tolerations</code>、<code>preemptionPolicy</code></td><td>描述 Pod 自身需求或调度约束，<strong>不是调度阶段</strong></td></tr>
<tr><td class="q-dim">调度阶段 / 扩展点</td><td>QueueSort、PreFilter、Filter、PostFilter、Score、Reserve、Permit、Bind、Unreserve</td><td>Scheduler Framework 中的处理流程，<strong>可以开发插件扩展</strong></td></tr>
<tr><td class="q-dim">调度机制 / 策略</td><td>Preemption、Backoff、UnschedulableQ 重新入队、Gang Scheduling、Backfill、Quota 管理</td><td>通常横跨多个阶段，<strong>不一定对应单一扩展点</strong></td></tr>
</tbody>
</table>
</div>
</div>

<div class="card card-d">
<h3>常见问题应该从哪里定位</h3>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:160px">问题</th><th style="width:100px">本质</th><th style="width:160px">主要涉及的调度阶段</th><th>相关 Pod 属性 / 机制</th><th>说明</th></tr>
</thead>
<tbody>
<tr><td>高优先级 Pod 长时间没被调度</td><td>Pod 没有及时获得调度机会，或资源被低优任务占住</td><td>QueueSort、PostFilter</td><td><strong>Pod 属性：</strong>priority<br><strong>机制：</strong>Preemption</td><td>priority 影响队列排序和抢占；如果 Pod 未出队，先看 QueueSort；如果出队后无节点可放，再看抢占</td></tr>
<tr><td>Pod 反复扫描大量节点但失败</td><td>失败 Pod 被无效重新入队</td><td>SchedulingQueue、PreFilter、Filter</td><td><strong>机制：</strong>Backoff、UnschedulableQ、事件提示</td><td>应优化重新入队条件，避免无关事件唤醒无关 Pod</td></tr>
<tr><td>短作业被大作业队头阻塞</td><td>出队顺序不合理</td><td>QueueSort</td><td><strong>机制：</strong>Backfill、多队列</td><td>小作业没机会出队时，Score 不会生效</td></tr>
<tr><td>GPU 拓扑放置不合理</td><td>节点或设备组合选择不好</td><td>Filter、Score、Reserve</td><td><strong>Pod 属性：</strong>resource requests、nodeAffinity、GPU topology</td><td>Pod 已进入调度周期，问题是放到哪里和怎么预留设备</td></tr>
<tr><td>Gang 任务部分 Pod 占住资源但整体无法启动</td><td>缺少整组准入与失败回滚</td><td>Reserve、Permit、Unreserve</td><td><strong>机制：</strong>Gang Scheduling、PodGroup</td><td>需要整组 Pod 要么一起放行，要么一起回滚</td></tr>
<tr><td>高优任务无节点可放，但低优任务占着资源</td><td>资源不足，需要让低优任务让路</td><td>PostFilter</td><td><strong>Pod 属性：</strong>priority、preemptionPolicy<br><strong>机制：</strong>Preemption</td><td>没有可行节点时，Score 没意义，需要抢占制造可行节点</td></tr>
</tbody>
</table>
</div>
<div class="qa-summary">面试表达技巧：先区分"这是 Pod 属性问题、调度阶段问题还是调度机制问题"，再定位到具体扩展点或策略。不要把 priority 说成"调度阶段"，也不要把 Preemption 说成"打分的一部分"。</div>
</div>

<div class="card card-w">
<h3>Scheduler Cache 与 Assume 机制</h3>
<p>scheduler 不会每调度一个 Pod 都从 API Server 重新拉全量 Node 和 Pod。它维护本地 cache，并在调度周期开始时生成 snapshot。选中节点后，scheduler 会先在本地 cache 中 assume 该 Pod 已经占用资源，然后异步绑定。</p>
<table>
<tr><th>机制</th><th>解决什么问题</th><th>风险</th></tr>
<tr><td>NodeInfo</td><td>缓存节点资源、Pod、镜像、本地状态</td><td>cache 与 API Server 存在短暂不一致</td></tr>
<tr><td>Snapshot</td><td>给一个调度周期提供稳定视图</td><td>不是强一致，只是调度器本地视角</td></tr>
<tr><td>Assumed Pod</td><td>绑定完成前先占住资源，避免过度分配</td><td>Bind 失败后必须过期或回滚</td></tr>
<tr><td>Nominated Pod</td><td>抢占时记录候选节点</td><td>被抢占 Pod 退出前，高优先级 Pod 仍可能等待</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Plugin 扩展点与调度研究问题的映射</h3>
<table>
<tr><th>研究问题</th><th>适合扩展点</th><th>说明</th></tr>
<tr><td>短作业优先 / SLA 排序</td><td>QueueSort</td><td>改变 Pod 出队顺序，影响全局等待时间</td></tr>
<tr><td>Gang Scheduling</td><td>PreFilter + Permit + Reserve</td><td>先识别 PodGroup，再在 Permit 阶段等待同组 Pod 凑齐</td></tr>
<tr><td>拓扑感知放置</td><td>PreFilter + Filter + Score</td><td>基于 NUMA、NVLink、机架、RDMA 等约束过滤和打分</td></tr>
<tr><td>多资源公平</td><td>QueueSort + Score + PostFilter</td><td>排序决定谁先获得机会，抢占决定如何回收资源</td></tr>
<tr><td>代价基抢占</td><td>PostFilter</td><td>调度失败后选择 victim，考虑 checkpoint、运行时长和释放资源量</td></tr>
<tr><td>DRA 设备匹配</td><td>PreFilter + Filter + Reserve</td><td>基于 ResourceClaim 和 ResourceSlice 做设备级匹配与预留</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Preemption 深入</h3>
<p>抢占不是简单地“杀掉低优先级 Pod 后马上运行高优先级 Pod”。scheduler 会先寻找通过移除低优先级 Pod 后可满足高优先级 Pod 的节点，选择 victim 后设置 <code>nominatedNodeName</code>，等待被抢占 Pod 优雅退出。期间如果集群状态变化，调度结果仍可能改变。</p>
<ul>
<li><strong>PDB：</strong>PodDisruptionBudget 会影响 victim 选择，减少对高可用服务的破坏。</li>
<li><strong>Graceful termination：</strong>被抢占 Pod 有终止宽限期，高优先级 Pod 不能立刻拿到资源。</li>
<li><strong>不可抢占约束：</strong>nodeSelector 不匹配、PVC 约束不满足、硬亲和性不满足，抢占也解决不了。</li>
<li><strong>训练任务代价：</strong>AI 训练抢占要考虑 checkpoint 新鲜度、已运行时间、重启成本和 gang 语义。</li>
</ul>
</div>

<div class="card card-w">
<h3>Gang Scheduling → 见"任务调度理论"页面</h3>
<p>Gang Scheduling 的理论基础（partial allocation、PodGroup/minAvailable、Backfill、弹性训练）和 K8s 实现细节（Coscheduling Plugin / Volcano / Kueue、Framework 扩展点落点、边界情况）已统一归并到 <strong>"任务调度理论" → "批调度、Gang 与 Backfill"</strong> 标签页。</p>
<p>快速索引：Gang 概念与 partial allocation → 任务调度理论 / 批调度、Gang 与 Backfill；Framework 扩展点落点 → 同上；Coscheduling / Volcano / Kueue 对比 → 同上；边界情况与坑 → 同上。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么说调度算法不能脱离 scheduler cache 和 binding cycle 讨论？</div>
<div class="qa-a"><p>因为算法给出的只是“应该放哪里”，而 Kubernetes 还要解决并发绑定、缓存一致性、资源临时预留、失败回滚和 API Server 写入延迟。一个理论上最优的策略，如果不能处理 assume、reserve、unreserve、permit timeout 和抢占等待，在真实 kube-scheduler 中就不可落地。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Scheduler Extender、Scheduler Plugin、多个 scheduler 怎么选？</div>
<div class="qa-a"><p>新能力优先用 Scheduling Framework Plugin，因为它能接入完整生命周期和 scheduler cache；Extender 更像外部 HTTP 过滤/打分，延迟和一致性控制较弱；多个 scheduler 适合业务强隔离，但要避免不同 scheduler 同时竞争同一批资源造成策略冲突。</p></div>
</div>

<div class="card card-m">
<h3>Scheduler 性能与扩展性</h3>
<p>大规模集群（数千节点、数万 Pod）中，scheduler 的性能直接决定 Pod 启动延迟。面试中要能说清楚关键性能参数和优化手段。</p>
<table>
<tr><th>机制</th><th>作用</th><th>默认值</th><th>调优建议</th></tr>
<tr><td>percentageOfNodesToScore</td><td>控制 Score 阶段扫描的节点比例</td><td>集群规模自适应（0-50%）</td><td>集群越大比例越低，平衡精度和性能</td></tr>
<tr><td>nodeScorePluginWeight</td><td>各打分插件的权重</td><td>默认各插件权重 1</td><td>根据业务调整，如提高拓扑分散权重</td></tr>
<tr><td>parallelism</td><td>并行调度的 worker 数量</td><td>默认 16</td><td>CPU 核数多可适当调高</td></tr>
<tr><td>leaderElection</td><td>多实例 HA，同时只有一个 active</td><td>默认开启</td><td>生产环境必须开启</td></tr>
<tr><td>podInitialBackoffSeconds</td><td>调度失败后的初始退避时间</td><td>1s</td><td>指数退避，最大 10s</td></tr>
<tr><td>podMaxBackoffSeconds</td><td>调度失败后的最大退避时间</td><td>10s</td><td>防止无限等待</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">percentageOfNodesToScore 的工作原理</div><p>scheduler 在 Score 阶段找到所有可用节点后，按比例只对部分节点打分（选最高分的），而不是对所有节点打分。这在大集群中显著减少计算量。公式：<code>numNodes = max(100, min(集群节点数 × 比例, 集群节点数))</code>。找到的节点会按 zone 分散，避免全部集中在同一可用区。</p></div>
<div class="qa-section"><div class="qa-section-title">Scheduler 吞吐量估算</div><p>一个 scheduler 实例通常可以处理 100-500 Pod/s 的调度吞吐。瓶颈通常在 API Server 的写吞吐（Bind 操作）和 scheduler cache 的更新频率。多 scheduler 实例（HA 模式）不会提升吞吐，因为同一时刻只有一个 active。</p></div>
</div>

<div class="card card-s">
<h3>Node 打分算法详解</h3>
<p>Filter 阶段只是"能用"，Score 阶段才是"优选"。面试中要能说出至少 3 个打分插件的算法逻辑。</p>
<table>
<tr><th>插件</th><th>打分逻辑</th><th>公式/策略</th><th>适用场景</th></tr>
<tr><td>NodeResourcesFit</td><td>资源越充足分越高</td><td>LeastAllocated：<code>(capacity - request) / capacity</code> 越大越好；MostAllocated：相反</td><td>装箱（MostAllocated）或分散（LeastAllocated）</td></tr>
<tr><td>NodeResourcesBalancedAllocation</td><td>CPU 和内存使用比例越接近分越高</td><td><code>1 - |cpuFrac - memFrac|</code>，避免资源碎片</td><td>防止 CPU 用满但内存空闲的碎片节点</td></tr>
<tr><td>ImageLocality</td><td>节点已有镜像越多分越高</td><td>镜像大小加权求和</td><td>减少镜像拉取时间，加速 Pod 启动</td></tr>
<tr><td>InterPodAffinity</td><td>满足 Pod 亲和性规则加分</td><td>匹配的 Pod 越多分越高</td><td>数据本地性、缓存亲和</td></tr>
<tr><td>NodeAffinity</td><td>满足 preferred 规则加分</td><td>每条规则加权累加</td><td>节点优选</td></tr>
<tr><td>TaintToleration</td><td>容忍 PreferNoSchedule 加分</td><td>容忍越多分越高</td><td>软性节点隔离</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">LeastAllocated vs MostAllocated</div><p>LeastAllocated 把 Pod 分散到不同节点，适合需要高可用、避免单点故障的场景。MostAllocated 把 Pod 集中到少数节点，适合需要装箱率高、节省成本的场景。可以通过 <code>NodeResourcesFit</code> 插件的 <code>scoringStrategy</code> 配置切换。</p></div>
<div class="qa-section"><div class="qa-section-title">自定义打分权重</div><p>在 <code>KubeSchedulerConfiguration</code> 中可以为每个插件设置权重。例如提高 <code>NodeResourcesFit</code> 权重让资源均衡更重要，提高 <code>ImageLocality</code> 权重让启动速度优先。</p></div>
</div>

<div class="card card-d">
<h3>Scheduler 配置与多 Profile</h3>
<p>Kubernetes 1.19+ 支持通过 <code>KubeSchedulerConfiguration</code> 文件配置 scheduler 行为，包括启用/禁用插件、设置插件权重、定义多个调度 Profile。</p>
<div class="qa-section"><div class="qa-section-title">KubeSchedulerConfiguration 核心字段</div><ul><li><strong>profiles：</strong>定义多个调度 Profile，每个 Profile 可以有独立的插件配置。</li><li><strong>plugins：</strong>按扩展点（Filter、Score、Reserve 等）启用或禁用插件。</li><li><strong>pluginConfig：</strong>为特定插件提供配置参数，如 <code>NodeResourcesFit</code> 的 <code>scoringStrategy</code>。</li><li><strong>leaderElection：</strong>配置 HA 和租约参数。</li></ul></div>
<div class="qa-section"><div class="qa-section-title">多 Profile 场景</div><p>同一个 scheduler 可以为不同 namespace 或不同 PriorityClass 的 Pod 使用不同的调度策略。例如：默认 Pod 用 LeastAllocated 分散，批处理 Pod 用 MostAllocated 装箱，GPU Pod 用自定义拓扑感知 Profile。</p></div>
<div class="qa-section"><div class="qa-section-title">默认启用的插件</div><p>Kubernetes 默认 scheduler 启用了约 20 个插件，覆盖所有扩展点。面试中不需要全背，但要能说出核心几个：<code>NodeResourcesFit</code>、<code>NodeAffinity</code>、<code>TaintToleration</code>、<code>ImageLocality</code>、<code>DefaultPreemption</code>、<code>DefaultBinder</code>。</p></div>
</div>

<div class="card card-w">
<h3>Scheduler HA 与 Leader Election</h3>
<p>生产环境中通常部署多个 scheduler 实例实现高可用，但同一时刻只有一个 active 实例在工作。</p>
<table>
<tr><th>概念</th><th>说明</th><th>关键参数</th></tr>
<tr><td>Leader Election</td><td>通过 etcd 的 Lease 机制选举 leader</td><td><code>leaderElection.leaseDuration</code>（默认 15s）</td></tr>
<tr><td>Lease 续约</td><td>Leader 定期续约，证明自己还活着</td><td><code>leaderElection.renewDeadline</code>（默认 10s）</td></tr>
<tr><td>故障转移</td><td>Leader 失联后，其他实例竞争成为新 leader</td><td><code>leaderElection.retryPeriod</code>（默认 2s）</td></tr>
<tr><td>非 Leader 行为</td><td>Standby 实例不执行调度，只等待成为 leader</td><td>不消耗调度计算资源</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">故障转移时间</div><p>最坏情况下故障转移时间 ≈ <code>leaseDuration + renewDeadline + retryPeriod</code>，默认约 27s。可以通过调小这些参数降低故障转移时间，但会增加 etcd 压力。</p></div>
<div class="qa-section"><div class="qa-section-title">多 Scheduler 模式</div><p>除了 HA 部署，Kubernetes 还支持运行多个不同配置的 scheduler（通过 <code>schedulerName</code> 指定）。例如默认 scheduler 处理普通 Pod，GPU scheduler 处理 GPU Pod。注意：不同 scheduler 之间不共享 cache，可能产生资源竞争。</p></div>
</div>

<div class="card card-m">
<h3>自定义 Scheduler Plugin 实战</h3>
<p>面试中经常被问到"你有没有写过自定义调度插件"。回答时应该先讲清楚<strong>有哪些实现方式</strong>，再深入 Framework Plugin 的开发流程，最后给出具体代码示例。</p>
</div>

<div class="card card-s">
<h3>三种实现自定义调度逻辑的方式</h3>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:140px">方式</th><th>原理</th><th>优点</th><th>缺点</th><th>适用场景</th></tr>
</thead>
<tbody>
<tr><td class="q-dim">Scheduling Framework Plugin<br>(In-tree)</td><td>实现 Framework 扩展点接口，编译进 scheduler 二进制</td><td>性能最好，直接访问 scheduler cache 和 NodeInfo；可以接入完整生命周期（QueueSort 到 PostBind）</td><td>需要重新编译 scheduler；升级 K8s 版本时需要适配接口变化</td><td>性能敏感的调度逻辑（GPU 拓扑、NUMA、Gang）；需要访问 cache 或参与 Reserve/Permit 等状态阶段</td></tr>
<tr><td class="q-dim">Scheduler Extender<br>(Out-of-tree HTTP)</td><td>独立 HTTP 服务，scheduler 通过 HTTP 调用 Filter / Prioritize / Bind 等接口</td><td>独立部署，不侵入 scheduler 代码；可以用任意语言开发</td><td>HTTP 调用延迟高（ms 级）；无法访问 scheduler cache；只能参与 Filter / Score / Bind 等有限阶段</td><td>简单过滤逻辑（如特殊 label 过滤）；非性能敏感的定制需求；多语言团队</td></tr>
<tr><td class="q-dim">Multiple Scheduler<br>(独立 Scheduler)</td><td>部署另一个完整的 scheduler 实例，Pod 通过 <code>schedulerName</code> 指定</td><td>完全独立，策略隔离；可以用不同版本的 scheduler</td><td>不同 scheduler 之间不共享 cache，可能产生资源竞争；运维复杂（需要维护两套 scheduler）</td><td>业务强隔离（GPU 任务 vs CPU 任务）；需要完全不同的调度策略</td></tr>
</tbody>
</table>
</div>
<div class="qa-summary">面试要点：三种方式的本质区别是<strong>"调度逻辑跑在 scheduler 进程内还是进程外"</strong>。Framework Plugin 跑在进程内，性能最好、能力最强，是 K8s 官方推荐方式。Extender 和 Multiple Scheduler 是历史兼容方案，新功能应优先考虑 Framework Plugin。</div>
</div>

<div class="card card-m">
<h3>Scheduling Framework Plugin 开发详解</h3>
<p>Scheduler Framework 定义了从 Pod 入队到绑定的完整生命周期，每个阶段都是一个<strong>扩展点（Extension Point）</strong>。开发自定义插件就是实现一个或多个扩展点接口。</p>

<div class="qa-section"><div class="qa-section-title">Framework 扩展点全景</div>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:100px">扩展点</th><th style="width:60px">类型</th><th>触发时机</th><th>典型用途</th></tr>
</thead>
<tbody>
<tr><td class="q-dim">QueueSort</td><td>排序</td><td>Pod 进入 ActiveQ 时</td><td>自定义出队顺序（如短作业优先、SLA 排序）</td></tr>
<tr><td class="q-dim">PreFilter</td><td>过滤</td><td>Filter 之前，预处理 Pod 信息</td><td>计算 Pod 的调度约束、检查 PodGroup 完整性</td></tr>
<tr><td class="q-dim">Filter</td><td>过滤</td><td>对每个候选节点判断是否可用</td><td>GPU 拓扑匹配、NUMA 亲和、自定义资源检查</td></tr>
<tr><td class="q-dim">PostFilter</td><td>过滤</td><td>Filter 后无可用节点时</td><td>Preemption 抢占逻辑（选择 victim）</td></tr>
<tr><td class="q-dim">PreScore</td><td>打分</td><td>Score 之前，预处理打分数据</td><td>预计算节点统计信息</td></tr>
<tr><td class="q-dim">Score</td><td>打分</td><td>对每个候选节点打分</td><td>基于实时负载打分、拓扑分散打分</td></tr>
<tr><td class="q-dim">NormalizeScore</td><td>打分</td><td>Score 之后，归一化分数</td><td>将分数映射到统一范围</td></tr>
<tr><td class="q-dim">Reserve</td><td>预留</td><td>选中节点后，Bind 之前</td><td>预留 GPU 设备、标记资源已占用</td></tr>
<tr><td class="q-dim">Permit</td><td>许可</td><td>Reserve 之后，等待条件满足</td><td>Gang Scheduling 等待同组 Pod 凑齐</td></tr>
<tr><td class="q-dim">PreBind</td><td>绑定</td><td>Bind 之前，执行绑定前操作</td><td>挂载 Volume、分配 IP</td></tr>
<tr><td class="q-dim">Bind</td><td>绑定</td><td>将 Pod 绑定到节点</td><td>自定义绑定逻辑（极少需要）</td></tr>
<tr><td class="q-dim">PostBind</td><td>绑定</td><td>Bind 之后，通知型操作</td><td>记录调度事件、通知外部系统</td></tr>
<tr><td class="q-dim">Unreserve</td><td>回滚</td><td>Reserve 之后失败时</td><td>释放预留的 GPU 设备、清理临时状态</td></tr>
</tbody>
</table>
</div>
</div>

<div class="qa-section"><div class="qa-section-title">开发步骤（面试标准回答）</div>
<ol>
<li><strong>创建 Go 项目：</strong>初始化 Go module，引入 <code>k8s.io/kubernetes</code> 依赖（或使用 <code>scheduler-plugins</code> 仓库作为模板）。</li>
<li><strong>实现扩展点接口：</strong>根据需求选择实现 <code>FilterPlugin</code>、<code>ScorePlugin</code>、<code>ReservePlugin</code> 等接口。每个接口有固定的方法签名。</li>
<li><strong>实现 <code>Name()</code> 方法：</strong>返回插件名称，用于在配置文件中引用。</li>
<li><strong>注册插件：</strong>在 <code>main()</code> 中通过 <code>app.NewSchedulerCommand()</code> 注册自定义插件到 Framework。</li>
<li><strong>编译部署：</strong>编译为自定义 scheduler 二进制或镜像，替换默认 scheduler。</li>
<li><strong>配置启用：</strong>在 <code>KubeSchedulerConfiguration</code> 的 <code>profiles[].plugins</code> 中启用插件，必要时在 <code>pluginConfig</code> 中传入参数。</li>
</ol>
</div>

<div class="qa-section"><div class="qa-section-title">关键接口签名（面试要能写出）</div>
<p>以下是最常用的三个接口签名，面试中如果被问到"写过什么插件"，至少能写出 Filter 和 Score 的签名：</p>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:100px">接口</th><th>方法签名</th><th>返回值含义</th></tr>
</thead>
<tbody>
<tr><td class="q-dim">FilterPlugin</td><td><code>Filter(ctx, state, pod, nodeInfo) *Status</code></td><td><code>Success</code> 表示节点可用；<code>Unschedulable</code> 表示不可用</td></tr>
<tr><td class="q-dim">ScorePlugin</td><td><code>Score(ctx, state, pod, nodeName) (int64, *Status)</code></td><td>返回 0-100 的分数，分数越高越优先</td></tr>
<tr><td class="q-dim">ReservePlugin</td><td><code>Reserve(ctx, state, pod, nodeName) *Status</code></td><td><code>Success</code> 表示预留成功；失败会触发 Unreserve</td></tr>
</tbody>
</table>
</div>
<p>注意：<code>CycleState</code> 是单次调度周期内的临时状态存储，可以在 PreFilter 中写入数据，在 Filter/Score/Reserve 中读取，避免重复计算。</p>
</div>
</div>

<div class="card card-d">
<h3>典型示例：GPU 拓扑感知 Filter + Score 插件</h3>
<p>这是 AI Infra 面试中最常见的自定义插件场景。下面给出完整的实现思路和关键代码骨架。</p>

<div class="qa-section"><div class="qa-section-title">场景描述</div>
<p>集群中有多种 GPU 拓扑的节点（如 NVLink 互联的 8 卡节点、PCIe 互联的 4 卡节点）。训练任务需要 4 张 NVLink 互联的 GPU，不能分配到 PCIe 节点上，也不能分配到 NVLink 域不够 4 卡的节点上。</p>
</div>

<div class="qa-section"><div class="qa-section-title">实现思路</div>
<ol>
<li><strong>PreFilter：</strong>从 Pod annotation 中解析 GPU 拓扑需求（如 <code>gpu-topology: nvlink-4</code>），写入 CycleState。</li>
<li><strong>Filter：</strong>从 Node label 中读取 GPU 拓扑信息（如 <code>nvidia.com/gpu-topology: nvlink-8</code>），判断是否满足 Pod 需求。不满足则返回 <code>Unschedulable</code>。</li>
<li><strong>Score：</strong>对满足条件的节点，根据 NVLink 域剩余 GPU 数量打分：刚好满足需求（如剩余 4 卡域）给高分，碎片化严重的给低分。</li>
<li><strong>Reserve：</strong>在 scheduler cache 中标记具体哪些 GPU 被预留，防止后续 Pod 重复分配。</li>
</ol>
</div>

<div class="qa-section"><div class="qa-section-title">Filter 核心代码骨架</div>
<pre><code>func (p *GPUTopologyPlugin) Filter(
    ctx context.Context,
    state *framework.CycleState,
    pod *v1.Pod,
    nodeInfo *framework.NodeInfo,
) *framework.Status {
    // 1. 从 CycleState 读取 PreFilter 阶段解析的 GPU 需求
    data, err := state.Read(stateKeyGPURequirement)
    if err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }
    requirement := data.(*GPURequirement) // topology=nvlink, count=4

    // 2. 从 Node label 读取 GPU 拓扑信息
    node := nodeInfo.Node()
    topoLabel, ok := node.Labels["nvidia.com/gpu-topology"]
    if !ok {
        return framework.NewStatus(framework.Unschedulable, "node has no GPU topology label")
    }

    // 3. 判断拓扑是否匹配
    if topoLabel != requirement.Topology {
        return framework.NewStatus(framework.Unschedulable,
            fmt.Sprintf("GPU topology mismatch: need %s, got %s",
                requirement.Topology, topoLabel))
    }

    // 4. 检查可用 GPU 数量（从 nodeInfo 或 annotation 获取）
    availableGPUs := getAvailableGPUs(node, nodeInfo)
    if availableGPUs < requirement.Count {
        return framework.NewStatus(framework.Unschedulable,
            fmt.Sprintf("insufficient GPUs: need %d, available %d",
                requirement.Count, availableGPUs))
    }

    return framework.NewStatus(framework.Success)
}</code></pre>
</div>

<div class="qa-section"><div class="qa-section-title">Score 核心代码骨架</div>
<pre><code>func (p *GPUTopologyPlugin) Score(
    ctx context.Context,
    state *framework.CycleState,
    pod *v1.Pod,
    nodeName string,
) (int64, *framework.Status) {
    // 从 CycleState 读取 GPU 需求
    data, _ := state.Read(stateKeyGPURequirement)
    requirement := data.(*GPURequirement)

    // 获取该节点上剩余 GPU 的拓扑分布
    node := getNodeByName(nodeName)
    freeGPUDomains := getFreeNVLinkDomains(node)

    // 打分策略：刚好满足需求的域越多，分数越高
    // 避免把 Pod 放到"只剩最后一个 4 卡域"的节点上
    matchingDomains := 0
    for _, domain := range freeGPUDomains {
        if domain.FreeGPUs >= requirement.Count {
            matchingDomains++
        }
    }

    // 分数范围 0-100
    score := int64(matchingDomains * 25)
    if score > 100 {
        score = 100
    }
    return score, framework.NewStatus(framework.Success)
}</code></pre>
</div>

<div class="qa-section"><div class="qa-section-title">KubeSchedulerConfiguration 配置示例</div>
<pre><code>apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: gpu-scheduler
    plugins:
      preFilter:
        enabled:
          - name: GPUTopology
      filter:
        enabled:
          - name: GPUTopology
      score:
        enabled:
          - name: GPUTopology
            weight: 10   # 权重越高，拓扑因素越重要
      reserve:
        enabled:
          - name: GPUTopology
    pluginConfig:
      - name: GPUTopology
        args:
          topologyTypes:
            - nvlink
            - pcie
          defaultCount: 1</code></pre>
</div>

<div class="qa-summary">面试表达结构：先说明"有三种实现方式，我选择 Framework Plugin 因为性能最好、能力最全" → 再讲"我实现了 PreFilter + Filter + Score + Reserve 四个扩展点" → 最后给出 Filter/Score 的核心逻辑和配置。如果能写出接口签名和关键代码骨架，会大幅加分。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: percentageOfNodesToScore 是什么？怎么调？</div>
<div class="qa-a"><p><code>percentageOfNodesToScore</code> 控制 scheduler 在 Score 阶段扫描的节点比例。默认值随集群规模自适应：100 节点以下扫全部，5000 节点以上扫 5%。调大可以提高调度精度（找到更优节点），但增加计算开销；调小可以提升性能，但可能错过最优节点。建议集群小于 500 节点时保持默认，超大集群按需调整。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何保证 scheduler 的高可用？</div>
<div class="qa-a"><p>通过部署多个 scheduler 实例 + Leader Election 实现。同一时刻只有一个 active 实例执行调度，其他 standby 等待。Leader 通过 etcd Lease 续约，失联后自动触发重新选举。关键参数：<code>leaseDuration</code>（默认 15s）、<code>renewDeadline</code>（默认 10s）、<code>retryPeriod</code>（默认 2s）。故障转移时间最坏约 27s。注意：HA 只保证可用性，不提升吞吐。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: LeastAllocated 和 MostAllocated 分别适合什么场景？</div>
<div class="qa-a"><p>LeastAllocated 把 Pod 分散到不同节点，资源使用率更均匀，适合在线服务（需要 buffer 应对流量波动）。MostAllocated 把 Pod 集中到少数节点，装箱率更高，适合批处理任务（可以腾出整机做下线维护）。可以通过 <code>NodeResourcesFit</code> 插件的 <code>scoringStrategy.type</code> 切换。</p></div>
</div>
