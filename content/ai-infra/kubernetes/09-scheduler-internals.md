<div class="card card-m">
<h3>kube-scheduler 内部机制：为什么这部分放在 K8S</h3>
<p>调度研究里有一类问题是通用算法问题，例如公平性、装箱、抢占和 backfill；另一类问题是 Kubernetes 运行时机制问题，例如调度队列、scheduler cache、assumed pod、plugin lifecycle、binding cycle。后者应该放在 K8S 模块，因为它回答的是：<strong>这些算法在 Kubernetes 里到底挂在哪个扩展点、读什么缓存、写什么状态、失败后如何恢复。</strong></p>
</div>

<div class="card card-s">
<h3>一次调度的内部路径</h3>
<ol>
<li><strong>入队：</strong>未绑定 Pod 进入 scheduling queue，根据优先级、退避状态和事件提示在不同队列之间流转。</li>
<li><strong>取快照：</strong>scheduler 从 cache 生成当前调度周期使用的 NodeInfo snapshot，避免调度过程中反复访问 API Server。</li>
<li><strong>Scheduling Cycle：</strong>依次执行 QueueSort、PreFilter、Filter、PostFilter、PreScore、Score、NormalizeScore，选出目标节点。</li>
<li><strong>Assume：</strong>在 scheduler cache 中假定 Pod 已经占用目标节点资源，防止后续 Pod 看到过时资源。</li>
<li><strong>Binding Cycle：</strong>执行 Reserve、Permit、PreBind、Bind、PostBind，其中绑定阶段可以与后续调度周期并行。</li>
<li><strong>状态回滚：</strong>如果 Reserve 或 Bind 后续失败，需要通过 Unreserve 或 cache 回滚释放临时占用。</li>
</ol>
</div>

<div class="card card-d">
<h3>调度队列</h3>
<table>
<tr><th>队列</th><th>作用</th><th>研究/面试关注点</th></tr>
<tr><td>ActiveQ</td><td>当前可立即尝试调度的 Pod</td><td>优先级排序、队头阻塞、短作业插队</td></tr>
<tr><td>BackoffQ</td><td>刚失败、需要退避后再试的 Pod</td><td>避免 tight loop；退避过长会增加等待时间</td></tr>
<tr><td>UnschedulableQ</td><td>当前没有可行节点的 Pod</td><td>等待资源、节点、Pod 删除、PVC 绑定等事件重新激活</td></tr>
<tr><td>Move request</td><td>集群事件触发 Pod 重新入队</td><td>事件提示是否精准，决定调度器吞吐和无效重试比例</td></tr>
</table>
<p>调度方向要特别关注：<strong>队列策略决定谁先被调度，Filter/Score 只决定它被放到哪里。</strong></p>
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
