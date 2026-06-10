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

<div class="card card-d">
<h3>三个队列分别解决什么问题</h3>
<div class="queue-detail-grid">
<div class="queue-detail active"><h4>ActiveQ：谁先获得调度机会</h4><p>ActiveQ 是调度器真正取 Pod 的地方。Pod 进入 ActiveQ 后，会经过 QueueSort 插件排序，默认主要受 priority 和入队时间影响。</p><ul><li><strong>研究重点：</strong>短作业优先、SLA 优先、队头阻塞、饥饿避免、公平性。</li><li><strong>面试表达：</strong>Filter/Score 再聪明，也只能处理已经出队的 Pod；如果队列排序不合理，高价值任务可能长期拿不到尝试机会。</li><li><strong>AI 场景：</strong>小推理任务、交互式 Notebook、训练恢复任务是否能插队，主要是队列策略问题。</li></ul></div>
<div class="queue-detail backoff"><h4>BackoffQ：失败后别立刻自旋</h4><p>BackoffQ 保存刚失败但还没到重试时间的 Pod。它的目标是避免调度器对同一个明显失败的 Pod 反复 Filter，造成 CPU tight loop。</p><ul><li><strong>研究重点：</strong>退避时间过短会浪费调度吞吐，过长会增加排队等待。</li><li><strong>面试表达：</strong>BackoffQ 是调度器的“冷静期”，把失败重试从忙等变成有节奏地再尝试。</li><li><strong>AI 场景：</strong>GPU 大作业如果资源暂时不够，频繁重试会扫描大量节点，影响整个调度器吞吐。</li></ul></div>
<div class="queue-detail unsched"><h4>UnschedulableQ：等事件，而不是盲目轮询</h4><p>UnschedulableQ 保存当前没有任何节点可满足的 Pod。它不是简单睡眠队列，而是等待可能改变可调度性的集群事件。</p><ul><li><strong>研究重点：</strong>事件提示是否精准，决定无效唤醒比例。</li><li><strong>面试表达：</strong>UnschedulableQ 是“条件未满足”的等待区；只有节点、Pod、PVC、ResourceClaim 等事件可能改变结论时，才应该被移动回来。</li><li><strong>AI 场景：</strong>等待 GPU 释放、等待 RDMA 节点加入、等待 PVC 绑定、等待 gang 资源凑齐。</li></ul></div>
</div>
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

<div class="card card-s">
<h3>队列策略与 Filter/Score 的边界</h3>
<table>
<tr><th>问题</th><th>应该主要改哪里</th><th>原因</th></tr>
<tr><td>高优先级 Pod 等太久</td><td>QueueSort / Priority / Preemption</td><td>这是“谁先获得机会”的问题，不是节点打分问题</td></tr>
<tr><td>Pod 总是扫描大量节点但失败</td><td>UnschedulableQ 事件提示 / PreFilter</td><td>应该减少无效调度周期，而不是继续扩大扫描</td></tr>
<tr><td>短作业被大作业队头阻塞</td><td>QueueSort / 多队列 / backfill</td><td>需要改变出队顺序或允许小作业利用碎片</td></tr>
<tr><td>GPU 拓扑放置不合理</td><td>Filter / Score / Reserve</td><td>Pod 已经获得调度机会，问题是放到哪个节点和设备组合</td></tr>
<tr><td>Gang 任务部分 Pod 占住资源</td><td>Permit / Reserve / Unreserve</td><td>需要同组准入和失败回滚，而不是单 Pod 独立调度</td></tr>
</table>
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

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么说调度算法不能脱离 scheduler cache 和 binding cycle 讨论？</div>
<div class="qa-a"><p>因为算法给出的只是“应该放哪里”，而 Kubernetes 还要解决并发绑定、缓存一致性、资源临时预留、失败回滚和 API Server 写入延迟。一个理论上最优的策略，如果不能处理 assume、reserve、unreserve、permit timeout 和抢占等待，在真实 kube-scheduler 中就不可落地。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Scheduler Extender、Scheduler Plugin、多个 scheduler 怎么选？</div>
<div class="qa-a"><p>新能力优先用 Scheduling Framework Plugin，因为它能接入完整生命周期和 scheduler cache；Extender 更像外部 HTTP 过滤/打分，延迟和一致性控制较弱；多个 scheduler 适合业务强隔离，但要避免不同 scheduler 同时竞争同一批资源造成策略冲突。</p></div>
</div>
