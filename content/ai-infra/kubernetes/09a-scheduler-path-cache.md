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

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么说调度算法不能脱离 scheduler cache 和 binding cycle 讨论？</div>
<div class="qa-a"><p>因为算法给出的只是“应该放哪里”，而 Kubernetes 还要解决并发绑定、缓存一致性、资源临时预留、失败回滚和 API Server 写入延迟。一个理论上最优的策略，如果不能处理 assume、reserve、unreserve、permit timeout 和抢占等待，在真实 kube-scheduler 中就不可落地。</p></div>
</div>
