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
