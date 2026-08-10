<div class="card card-m">
<h3>Scheduler 性能与扩展性</h3>
<p>大规模集群（数千节点、数万 Pod）中，scheduler 的性能直接决定 Pod 启动延迟。面试中要能说清楚关键性能参数和优化手段。</p>
<table>
<tr><th>机制</th><th>作用</th><th>默认值</th><th>调优建议</th></tr>
<tr><td>percentageOfNodesToScore</td><td>找到足够可行节点后提前结束 Filter 搜索，并只对这批节点打分</td><td>0 表示使用随集群规模自适应的默认值</td><td>平衡调度延迟和放置质量</td></tr>
<tr><td>nodeScorePluginWeight</td><td>各打分插件的权重</td><td>默认各插件权重 1</td><td>根据业务调整，如提高拓扑分散权重</td></tr>
<tr><td>parallelism</td><td>Filter、Score 等调度算法处理节点集合时的并行度；不是同时推进多个 Pod 调度周期的 worker 数</td><td>默认 16</td><td>结合 CPU、节点规模和插件开销压测，不能只因 CPU 核数多就盲目调高</td></tr>
<tr><td>leaderElection</td><td>多实例 HA，同时只有一个 active</td><td>默认开启</td><td>生产环境必须开启</td></tr>
<tr><td>podInitialBackoffSeconds</td><td>调度失败后的初始退避时间</td><td>1s</td><td>指数退避，最大 10s</td></tr>
<tr><td>podMaxBackoffSeconds</td><td>调度失败后的最大退避间隔</td><td>10s</td><td>限制重复失败 Pod 的最高重试频率</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">percentageOfNodesToScore 的工作原理</div><p>scheduler 遍历 Node 执行 Filter，一旦找到达到阈值数量的 feasible Nodes 就停止继续搜索，再对已找到的节点打分。默认自适应比例约从 100 节点时的 50% 下降到 5000 节点时的 10%，自动值下限为 5%；实现还要求至少寻找 100 个 feasible Nodes，因此小集群通常仍检查全部节点。节点遍历会轮转并跨 zone 交错，避免固定只看同一批节点。</p></div>
<div class="qa-section"><div class="qa-section-title">Scheduler 吞吐量</div><p>吞吐取决于节点数量、约束复杂度、插件实现、可调度成功率以及 API Server 的 Bind 延迟，不能用一个固定 Pod/s 数字代表所有集群。HA 副本通常由 Leader Election 保持一主多备，不会线性增加吞吐；应通过调度尝试 rate、队列长度和扩展点耗时在目标集群压测。</p></div>
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
<tr><td>TaintToleration</td><td>未容忍的 PreferNoSchedule taint 越少分越高</td><td>按软 taint 惩罚节点</td><td>软性节点隔离</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">LeastAllocated vs MostAllocated</div><p>LeastAllocated 偏好 requests 占用较低的节点，让资源使用更均衡；MostAllocated 偏好已经较满但仍可行的节点，提高装箱率并腾出整机。LeastAllocated 本身不保证跨故障域高可用，高可用仍应使用 PodTopologySpread 或 PodAntiAffinity。</p></div>
<div class="qa-section"><div class="qa-section-title">自定义打分权重</div><p>在 <code>KubeSchedulerConfiguration</code> 中可以为每个插件设置权重。例如提高 <code>NodeResourcesFit</code> 权重让资源均衡更重要，提高 <code>ImageLocality</code> 权重让启动速度优先。</p></div>
</div>

<div class="card card-d">
<h3>Scheduler 配置与多 Profile</h3>
<p>Kubernetes 1.19+ 支持通过 <code>KubeSchedulerConfiguration</code> 文件配置 scheduler 行为，包括启用/禁用插件、设置插件权重、定义多个调度 Profile。</p>
<div class="qa-section"><div class="qa-section-title">KubeSchedulerConfiguration 核心字段</div><ul><li><strong>profiles：</strong>定义多个调度 Profile，每个 Profile 可以有独立的插件配置。</li><li><strong>plugins：</strong>按扩展点（Filter、Score、Reserve 等）启用或禁用插件。</li><li><strong>pluginConfig：</strong>为特定插件提供配置参数，如 <code>NodeResourcesFit</code> 的 <code>scoringStrategy</code>。</li><li><strong>leaderElection：</strong>配置 HA 和租约参数。</li></ul></div>
<div class="qa-section"><div class="qa-section-title">多 Profile 场景</div><p>同一个 scheduler 进程可以配置多个 Profile，每个 Profile 必须有唯一的 <code>schedulerName</code>，Pod 通过 <code>spec.schedulerName</code> 选择；不会仅凭 Namespace 或 PriorityClass 自动切换。例如普通 Pod 选择默认 Profile，GPU Pod 由准入层显式写入 GPU Profile 的 schedulerName。</p></div>
<div class="qa-section"><div class="qa-section-title">默认插件</div><p>默认插件集合会随 Kubernetes 版本和 Feature Gate 演进，面试不应背固定数量；重点掌握 <code>NodeResourcesFit</code>、<code>NodeAffinity</code>、<code>TaintToleration</code>、<code>ImageLocality</code>、<code>DefaultPreemption</code>、<code>DefaultBinder</code> 的阶段和边界。</p></div>
</div>

<div class="card card-w">
<h3>Scheduler HA 与 Leader Election</h3>
<p>同一套 scheduler 部署多个副本时，通常通过 Leader Election 做单活高可用；这与运行多个不同 <code>schedulerName</code> 的独立 scheduler 是两种架构。</p>
<table>
<tr><th>概念</th><th>说明</th><th>关键参数</th></tr>
<tr><td>Leader Election</td><td>多个实例竞争 API Server 中的 <code>coordination.k8s.io/v1 Lease</code></td><td><code>leaderElection.leaseDuration</code>（默认 15s）</td></tr>
<tr><td>Lease 续约</td><td>Leader 定期续约，证明自己还活着</td><td><code>leaderElection.renewDeadline</code>（默认 10s）</td></tr>
<tr><td>故障转移</td><td>Leader 失联后，其他实例竞争成为新 leader</td><td><code>leaderElection.retryPeriod</code>（默认 2s）</td></tr>
<tr><td>非 Leader 行为</td><td>Standby 实例不执行调度，只等待成为 leader</td><td>不消耗调度计算资源</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">故障转移时间</div><p>Standby 需要观察现有 Lease 过期后再竞争，切换时间主要受 leaseDuration、API/网络抖动、retryPeriod 和新 leader Cache 同步影响，不能简单把三个配置相加得到固定最坏值。参数过小会造成误切主和更高控制面写压力，过大则延长调度停顿。</p></div>
<div class="qa-section"><div class="qa-section-title">切主时的状态恢复</div><p>如果旧 Leader 已成功 Bind，绑定结果已经进入 API Server，新 Leader 同步 Cache 后会看到 Pod 的 <code>spec.nodeName</code>，不会再把它当成未调度 Pod。如果旧 Leader 只完成内存 Assume、尚未 Bind，Assume 状态会随进程丢失，Pod 仍保持未绑定并由新 Leader 重新调度。旧、新实例的 Bind 请求短暂重叠时，API Server 中同一个 Pod 最终只能形成一个持久绑定；但 Reserve 插件的外部副作用不会因此自动获得 exactly-once，仍需幂等、TTL 或对账恢复。</p></div>
</div>

<div class="card card-r">
<h3>多个独立 Scheduler 如何避免争抢同一批节点资源</h3>
<p><code>spec.schedulerName</code> 只划分“哪个 scheduler 处理哪个 Pod”，不会自动划分 Node。两个独立 scheduler 拥有各自的 Cache，可能同时基于稍旧视图判断同一节点还有资源；API Server 的 Bind 操作也不会重新执行整套 Filter 来替它们做跨 scheduler 资源预留。</p>
<table>
<tr><th>方案</th><th>一致性</th><th>代价与适用边界</th></tr>
<tr><td>同一 kube-scheduler 的多个 Profile</td><td>共享 pending queue、Cache 和 Assume 账本</td><td>优先选择；适合策略不同但仍能运行在同一二进制中的工作负载</td></tr>
<tr><td>用 taint/label/affinity 划分互斥 Node 池</td><td>从资源域上消除竞争</td><td>隔离明确，但降低跨池借用和整体利用率</td></tr>
<tr><td>统一 Reservation/Claim 控制面</td><td>通过 API 对象的 resourceVersion、唯一约束或设备 Claim 串行化稀缺资源分配</td><td>实现复杂，适合 GPU slice、许可证等必须跨 scheduler 协调的资源</td></tr>
<tr><td>仅依赖 ResourceQuota</td><td>限制租户总量，但不锁定某个 Node 的瞬时空闲资源</td><td>不能单独解决两个 scheduler 对同一节点的并发放置</td></tr>
</table>
<p>如果只是为了给 CPU Pod 和 GPU Pod 配置不同插件，多个 Profile 通常比两个完全独立的 scheduler 更容易维持一致的资源视图。只有确实需要版本、进程或故障域隔离时，才承担独立 Cache 和跨 scheduler 协调成本。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: percentageOfNodesToScore 是什么？怎么调？</div>
<div class="qa-a"><p><code>percentageOfNodesToScore</code> 控制找到多少 feasible Nodes 后停止继续做 Filter，并对已找到的节点打分。默认值随规模自适应：约 100 节点时为 50%，5000 节点时为 10%，自动值最低 5%；实现至少寻找 100 个 feasible Nodes，所以小集群通常检查全部节点。调大提高看到全局优选节点的概率，调小降低节点级插件调用，但可能恶化拓扑、装箱和碎片结果。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何保证 scheduler 的高可用？</div>
<div class="qa-a"><p>通过部署多个 scheduler 实例并竞争 API Server 中的 Lease 实现。同一时刻通常只有一个 active 实例执行调度，其他 standby 等待；leader 失联且 Lease 过期后重新选举。<code>leaseDuration</code>、<code>renewDeadline</code>、<code>retryPeriod</code> 共同影响误切主风险与恢复速度，但不能简单相加成固定故障转移时间。HA 提升可用性，不提升正常时吞吐。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: LeastAllocated 和 MostAllocated 分别适合什么场景？</div>
<div class="qa-a"><p>LeastAllocated 偏好 requests 占用率低的节点，使资源使用更均衡；MostAllocated 偏好已经较满但仍可行的节点，提高装箱率并腾出整机。它们是资源放置策略，不直接等于在线/离线或高可用策略；跨故障域分散还需要 PodTopologySpread/PodAntiAffinity。可通过 <code>NodeResourcesFit.scoringStrategy.type</code> 配置。</p></div>
</div>
