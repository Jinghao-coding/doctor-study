<div class="card card-m">
<h3>调度与资源模型：回答“为什么 Pending”的核心模块</h3>
<p>调度和资源模型要一起学。<strong>资源模型定义 Pod 要什么、Node 有什么；调度器决定这个 Pod 放到哪里。</strong>面试中最常见的追问是：Pod 为什么 Pending、requests/limits 如何影响调度、QoS 如何影响驱逐、GPU 这类扩展资源如何被调度。</p>
</div>

<div class="card card-w">
<h3>Scheduler 内部机制 → 见"Scheduler内部机制"标签页</h3>
<p>本模块聚焦<strong>资源模型</strong>（Pod 要什么、Node 有什么）。Scheduler 的内部运行机制（调度队列、Filter/Score 全链路、抢占、Gang Scheduling、自定义插件等）已独立为 <strong>"Scheduler内部机制"</strong> 标签页，避免内容重复。</p>
<p>快速索引：调度队列流转 → 09 标签页"调度队列总览图"；Framework 扩展点 → 09 标签页"Plugin 扩展点与调度研究问题的映射"；抢占机制 → 09 标签页"Preemption 深入"；Gang Scheduling → 09 标签页"Gang Scheduling"。</p>
</div>

<div class="card card-m">
<h3>Requests / Limits / QoS</h3>
<table>
<tr><th>概念</th><th>影响范围</th><th>关键结论</th></tr>
<tr><td>requests</td><td>调度、资源预留、HPA 部分指标</td><td>scheduler 主要根据 requests 判断节点是否放得下</td></tr>
<tr><td>limits</td><td>运行时限制</td><td>CPU limit 可能 throttling，内存超过 limit 通常 OOMKilled</td></tr>
<tr><td>Guaranteed</td><td>驱逐优先级最低</td><td>每个容器 CPU/Memory requests 等于 limits 且都设置</td></tr>
<tr><td>Burstable</td><td>中等驱逐优先级</td><td>至少设置了一个 request，但不完全满足 Guaranteed</td></tr>
<tr><td>BestEffort</td><td>最先被驱逐</td><td>没有设置 CPU/Memory requests 和 limits</td></tr>
</table>
<p>面试中要强调：<strong>调度看 requests，不是看实时使用量；驱逐看 QoS、优先级和资源压力。</strong></p>
</div>

<div class="card card-s">
<h3>Extended Resource 与 Device Plugin</h3>
<p>扩展资源是 Kubernetes 资源模型中的“自定义整数资源”，Device Plugin 是最常见的节点侧上报机制。两者关系可以理解为：<strong>Device Plugin 负责发现和注册设备，Extended Resource 负责在 Pod spec 和 Node allocatable 中表达可调度数量。</strong></p>
<table>
<tr><th>环节</th><th>发生什么</th><th>关键点</th></tr>
<tr><td>资源注册</td><td>Device Plugin 通过 kubelet 注册资源名，例如 <code>nvidia.com/gpu</code></td><td>资源名必须带域名前缀，避免和原生资源冲突</td></tr>
<tr><td>库存暴露</td><td>kubelet 把数量写入 Node <code>capacity</code> / <code>allocatable</code></td><td>scheduler 看到的是整数数量，不是每张卡的详细属性</td></tr>
<tr><td>Pod 申请</td><td>Pod 在 <code>resources.limits</code> 中申请，例如 <code>nvidia.com/gpu: 1</code></td><td>GPU 等扩展资源一般要求 requests 与 limits 相等</td></tr>
<tr><td>节点选择</td><td>scheduler 根据资源数量过滤节点</td><td>默认不理解显存、型号、NVLink、NUMA 等设备属性</td></tr>
<tr><td>设备交付</td><td>Pod 到节点后 kubelet 调用 Device Plugin <code>Allocate</code></td><td>具体 device node、环境变量、mount 在节点侧注入容器</td></tr>
</table>
<p><code>nvidia.com/a100</code>、<code>nvidia.com/v100</code> 也可以通过 Device Plugin 实现，但本质是把“型号”编码进资源名。当还要表达显存、MIG profile、PCIe/SXM、NUMA、NVLink、健康状态时，资源名和 label 组合会迅速爆炸。</p>
</div>

<div class="card card-w">
<h3>DRA 与传统资源模型的边界</h3>
<p>DRA 不是把 <code>resources.requests</code> 简单增强成更复杂的字段，而是引入 <code>resource.k8s.io</code> API，用 <code>ResourceClaim</code> 表达需求、用 <code>ResourceSlice</code> 发布设备库存、用 <code>DeviceClass</code> 抽象设备类别。传统 Extended Resource 适合“资源名 + 整数数量”，DRA 更适合“设备属性 + 容量 + 拓扑 + 共享关系”。</p>
<table>
<tr><th>维度</th><th>Device Plugin / Extended Resource</th><th>DRA</th></tr>
<tr><td>资源表达</td><td>资源名 + 整数数量</td><td>结构化设备属性、容量、拓扑、选择条件</td></tr>
<tr><td>调度可见性</td><td>scheduler 主要看到数量</td><td>scheduler 可基于 ResourceSlice 做设备级匹配</td></tr>
<tr><td>适合场景</td><td>同质 GPU、简单整卡分配</td><td>异构 GPU/NPU/DPU、MIG、拓扑、共享设备</td></tr>
<tr><td>复杂度</td><td>简单成熟，生态广</td><td>能力强，但依赖 API 版本和 DRA driver 生态</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Node Affinity / Anti-Affinity 与 Pod Affinity / Anti-Affinity</h3>
<p>这里有三组概念容易混：<strong>Node Affinity、Node Anti-Affinity、Pod Affinity / Pod Anti-Affinity</strong>。一句话区分：</p>
<p><strong>Node Affinity / Anti-Affinity：Pod 和节点之间的关系。Pod Affinity / Anti-Affinity：Pod 和 Pod 之间的关系。</strong></p>
</div>

<div class="card card-s">
<h3>Node Affinity：Pod 对节点有偏好</h3>
<p>Node Affinity 解决的是：<strong>这个 Pod 应该去什么样的机器上？</strong>它是比 nodeSelector 更强大的节点选择机制，支持软约束（preferred）和硬约束（required），以及基于节点标签的复杂表达式。</p>
<table>
<tr><th>类型</th><th>行为</th><th>典型场景</th></tr>
<tr><td>requiredDuringSchedulingIgnoredDuringExecution</td><td>硬约束，Pod 必须调度到满足条件的节点，否则 Pending</td><td>必须是 A100 节点、必须在北京机房</td></tr>
<tr><td>preferredDuringSchedulingIgnoredDuringExecution</td><td>软约束，优先调度到满足条件的节点，但不强制</td><td>最好在 SSD 节点、最好在北京机房（但上海也可以）</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">IgnoredDuringExecution 的含义</div><p>调度时会检查这个规则；Pod 已经运行后，如果节点标签变化了，Kubernetes 默认不会因为这个规则再把 Pod 驱逐掉。这是设计选择：避免运行时驱逐造成服务中断。如果需要运行时驱逐，用 Taint 的 NoExecute 效果。</p></div>
<div class="qa-section"><div class="qa-section-title">Node Anti-Affinity</div><p>Kubernetes 里严格说没有一个和 <code>nodeAffinity</code> 同级的字段叫 <code>nodeAntiAffinity</code>，但可以通过 <code>nodeAffinity</code> 里的 <code>NotIn</code>、<code>DoesNotExist</code> 等表达"不要去某些节点"。例如：不要调度到 V100 节点、不要调度到 spot 节点。</p></div>
</div>

<div class="card card-d">
<h3>Pod Affinity / Anti-Affinity：Pod 之间的关系</h3>
<p>Pod Affinity 解决的是：<strong>这个 Pod 希望和哪些已有 Pod 放近一点？</strong>判断对象不是节点标签，而是<strong>已有 Pod 的标签</strong>。Pod Anti-Affinity 则相反：不希望和某些 Pod 放得太近。</p>
<table>
<tr><th>类型</th><th>判断对象</th><th>典型场景</th></tr>
<tr><td>Pod Affinity</td><td>已有 Pod 的标签</td><td>训练任务靠近数据缓存 Pod（降低延迟）；Worker 靠近 Parameter Server</td></tr>
<tr><td>Pod Anti-Affinity</td><td>已有 Pod 的标签</td><td>同服务副本不要在同一节点（高可用）；两个大 GPU 任务不要在同一台机器（避免资源竞争）</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">topologyKey 是什么？</div><p>Pod Affinity / Anti-Affinity 中 <code>topologyKey</code> 表示"靠近"或"远离"是按什么范围来定义的：<code>kubernetes.io/hostname</code> 表示同一节点，<code>topology.kubernetes.io/zone</code> 表示同一可用区，<code>rack</code> 表示同一机架。</p></div>
<div class="qa-section"><div class="qa-section-title">性能影响</div><p>Pod Affinity/Anti-Affinity 需要在调度时扫描大量 Pod，大规模集群中可能显著增加调度延迟。建议限制 <code>topologyKey</code> 的粒度，避免在超大集群中使用跨节点的 Pod Anti-Affinity。</p></div>
</div>

<div class="card card-w">
<h3>Node Affinity 和 Pod Affinity 的区别（面试核心）</h3>
<table>
<tr><th>类型</th><th>判断对象</th><th>例子</th></tr>
<tr><td>Node Affinity</td><td>节点的标签</td><td>我要去 A100 节点</td></tr>
<tr><td>Node Anti-Affinity</td><td>节点的标签</td><td>我不要去 spot 节点</td></tr>
<tr><td>Pod Affinity</td><td>已有 Pod 的标签</td><td>我要靠近 redis Pod</td></tr>
<tr><td>Pod Anti-Affinity</td><td>已有 Pod 的标签</td><td>我不要和同服务副本在同一节点</td></tr>
</table>
<p>一句话：<strong>Node Affinity 看节点标签，Pod Affinity 看已有 Pod 标签。</strong>硬约束（required）主要在 Filter 阶段起作用，不满足就直接过滤掉节点；软偏好（preferred）主要在 Score 阶段起作用，满足偏好的节点得分更高。</p>
</div>

<div class="card card-d">
<h3>Topology Spread Constraints</h3>
<p>Topology Spread Constraints 控制 Pod 在拓扑域（可用区、节点、机架等）上的<strong>均匀分布程度</strong>。它比 Pod Anti-Affinity 更灵活，可以表达"每个可用区的 Pod 数量差距不超过 1"这类需求。</p>
<table>
<tr><th>字段</th><th>含义</th><th>示例</th></tr>
<tr><td>topologyKey</td><td>拓扑域的标签键</td><td><code>topology.kubernetes.io/zone</code>（可用区）、<code>kubernetes.io/hostname</code>（节点）</td></tr>
<tr><td>maxSkew</td><td>允许的最大不均衡度</td><td>maxSkew=1 表示各拓扑域 Pod 数量最多差 1</td></tr>
<tr><td>whenUnsatisfiable</td><td>无法满足时的行为</td><td>DoNotSchedule（硬约束）或 ScheduleAnyway（软约束）</td></tr>
<tr><td>labelSelector</td><td>参与计算的 Pod 范围</td><td>只统计同 Service 的 Pod</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">与 Pod Anti-Affinity 的区别</div><ul><li>Anti-Affinity 是"每对 Pod 不能在一起"，约束数量随 Pod 数量平方增长。</li><li>Topology Spread 是"每个域的 Pod 数量差距不超过 N"，约束数量与域数量相关，更适合大规模均匀分布。</li></ul></div>
<div class="qa-section"><div class="qa-section-title">常见坑</div><ul><li>如果某个拓扑域没有匹配的节点，<code>DoNotSchedule</code> 会导致 Pod 无法调度。</li><li>多个 Spread Constraints 可能互相冲突，导致没有节点满足所有约束。</li><li>滚动更新时，新旧 Pod 同时存在可能导致 skew 暂时超标。</li></ul></div>
</div>

<div class="card card-w">
<h3>Taints & Tolerations</h3>
<p>Taint 是打在<strong>节点上</strong>的"排斥标记"，Toleration 是 Pod 的"容忍声明"。只有 Pod 容忍了节点的所有 Taint，才能被调度到该节点。这是 Kubernetes 中最常用的节点隔离机制。</p>
<table>
<tr><th>Effect</th><th>行为</th><th>典型场景</th></tr>
<tr><td>NoSchedule</td><td>不容忍的 Pod 不会被调度到该节点</td><td>GPU 节点只跑 GPU Pod、专用节点池</td></tr>
<tr><td>PreferNoSchedule</td><td>尽量不调度，但不强制</td><td>软性隔离，优先使用其他节点</td></tr>
<tr><td>NoExecute</td><td>不容忍的 Pod 会被驱逐（已在运行的也会被赶走）</td><td>节点故障预隔离、维护前驱逐</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">与 nodeSelector / Affinity 的区别</div><ul><li>nodeSelector / Affinity 是 Pod "选择"节点（拉模型），Taint 是节点"拒绝" Pod（推模型）。</li><li>两者配合使用：Taint 防止无关 Pod 调度到 GPU 节点，nodeSelector 让 GPU Pod 找到 GPU 节点。</li><li>生产最佳实践：GPU 节点同时打 Taint + 标签，GPU Pod 同时配 Toleration + nodeSelector。</li></ul></div>
<div class="qa-section"><div class="qa-section-title">自动 Taint</div><p>kubelet 会在节点异常时自动打 Taint：<code>node.kubernetes.io/not-ready</code>、<code>node.kubernetes.io/unreachable</code>、<code>node.kubernetes.io/out-of-disk</code>、<code>node.kubernetes.io/memory-pressure</code> 等。这些 Taint 的 Effect 是 NoExecute，会导致不容忍的 Pod 被驱逐。</p></div>
</div>

<div class="card card-m">

<h3>调度与资源模型高频问答</h3>

<p>本模块的问答按“概念 → 作用 → 链路/排查 → 面试口径”组织，避免只背一段结论。</p>

</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod Pending 时，调度侧怎么排查？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 先看事件</div><p>先用 <code>kubectl describe pod</code> 看 Events，确认是否是 <code>FailedScheduling</code>，不要一上来就猜 kubelet 或 CNI。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 资源类原因</div><p>对比 Pod requests 和 Node allocatable，关注 CPU、内存、GPU 扩展资源、DaemonSet 占用、系统预留和资源碎片。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 约束类原因</div><p>检查 nodeSelector、nodeAffinity、podAffinity/anti-affinity、topologySpreadConstraints、taints/tolerations 是否让可选节点变少。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 外部依赖原因</div><p>如果事件提到 PVC、ResourceClaim、Quota 或队列准入，就分别转到存储、DRA、ResourceQuota、Kueue/Volcano 链路排查。</p></div>
<div class="qa-summary">面试口径：Pending 先看 Events，再按资源、约束、存储、配额、GPU/DRA、调度器插件逐层排查。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: requests 和 limits 有什么区别？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. requests 的概念</div><p><code>requests</code> 是 Pod 对资源的最低需求和调度依据，scheduler 用它判断节点是否放得下。</p></div>
<div class="qa-section"><div class="qa-section-title">2. limits 的概念</div><p><code>limits</code> 是运行时上限，CPU 超过 limit 通常被 throttling，内存超过 limit 通常触发 OOMKilled。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 对 QoS 的作用</div><p>CPU/Memory 的 requests 和 limits 组合决定 QoS：Guaranteed、Burstable、BestEffort，进而影响节点压力下的驱逐顺序。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 常见误区</div><p>调度器默认不看实时使用量，而是看 requests；limits 不是资源预留，设置过低会影响稳定性。</p></div>
<div class="qa-summary">面试口径：requests 主要管调度和预留，limits 主要管运行时限制，QoS 决定资源压力下谁更容易被驱逐。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 GPU requests 和 limits 通常要相等？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. GPU 的资源属性</div><p>GPU 是离散扩展资源，默认按整数设备分配，不像 CPU 那样天然支持细粒度超卖。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 调度一致性</div><p>scheduler 根据 Pod 申请的扩展资源数量过滤节点，kubelet 也按同样数量调用 Device Plugin Allocate，二者需要一致。</p></div>
<div class="qa-section"><div class="qa-section-title">3. Kubernetes 约定</div><p>扩展资源通常只允许设置 limits，requests 会被视为等于 limits，避免“调度申请少、运行占用多”的不一致。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 例外场景</div><p>MIG、MPS、time-slicing、vGPU 或 DRA 可以表达更复杂共享，但那是额外机制，不是普通 GPU limit 的默认语义。</p></div>
<div class="qa-summary">面试口径：普通 GPU 扩展资源按整数设备调度和分配，所以 requests/limits 通常保持一致，保证 scheduler 与 kubelet 看到同一个资源需求。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Node Affinity 和 nodeSelector 有什么区别？什么时候用哪个？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. nodeSelector</div><p>最简单的节点选择方式，只支持精确匹配（key=value），AND 逻辑。适合简单场景：GPU 节点打标签 <code>gpu=true</code>，Pod 配 <code>nodeSelector: gpu: "true"</code>。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Node Affinity</div><p>支持更丰富的表达式：In、NotIn、Exists、DoesNotExist、Gt、Lt。支持软约束（preferred）和硬约束（required）。适合复杂场景：优先选 SSD 节点，但 HDD 也可以接受。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 选择建议</div><p>简单标签匹配用 nodeSelector，需要表达式或软约束用 Node Affinity。两者可以同时使用，都满足才调度。</p></div>
<div class="qa-summary">面试口径：nodeSelector 是简单版，Node Affinity 是增强版。需要软约束、复杂表达式或多条件组合时用 Affinity。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Topology Spread Constraints 和 Pod Anti-Affinity 有什么区别？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 约束模型不同</div><p>Pod Anti-Affinity 是"每对 Pod 之间"的约束，Pod 数量越多，需要检查的配对越多，复杂度 O(n²)。Topology Spread 是"每个拓扑域 Pod 数量差距不超过 N"，复杂度与域数量相关。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 表达能力不同</div><p>Anti-Affinity 只能表达"不能在一起"，Spread 可以表达"尽量均匀分布"且允许一定的 skew。Spread 的 maxSkew 参数让约束更灵活。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 大规模场景</div><p>大规模 Deployment（数百 Pod）用 Anti-Affinity 会导致调度器性能问题，推荐用 Topology Spread Constraints。</p></div>
<div class="qa-summary">面试口径：Anti-Affinity 是二元的"不能在一起"，Spread 是量化的"差距不超过 N"。大规模均匀分布优先用 Spread。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Taint 和 Toleration 的工作原理是什么？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 工作机制</div><p>Taint 是打在节点上的"排斥标记"，包含 key、value 和 effect。Toleration 是 Pod 的"容忍声明"。scheduler 在 Filter 阶段检查 Pod 是否容忍节点的所有 Taint，不容忍则过滤掉该节点。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 三种 Effect</div><p>NoSchedule 阻止新 Pod 调度；PreferNoSchedule 尽量阻止但不强制；NoExecute 会驱逐已在运行的 Pod。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 典型场景</div><p>GPU 节点打 <code>nvidia.com/gpu:NoSchedule</code>，GPU Pod 配对应 Toleration。节点维护前打 <code>maintenance:NoExecute</code> 驱逐 Pod。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 与 Affinity 配合</div><p>Taint 是"推"（节点拒绝 Pod），Affinity 是"拉"（Pod 选择节点）。生产环境通常两者配合：Taint 做隔离，Affinity 做优选。</p></div>
<div class="qa-summary">面试口径：Taint 是节点说"不"，Toleration 是 Pod 说"我可以"。两者配合实现节点隔离和专用节点池。</div>
</div>
</div>
