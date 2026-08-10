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
