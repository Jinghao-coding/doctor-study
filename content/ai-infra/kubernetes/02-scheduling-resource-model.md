## 一句话结论

K8S 调度的核心是 requests/limits、QoS、过滤打分、抢占和扩展资源模型。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Kubernetes 核心 |
| 章节类型 | 系统类 |
| 解决问题 | 围绕控制面、调度资源模型、Workload Controller、网络存储、安全多租户、排障和 AI Infra GPU/DRA 建立平台面试答案。 |
| 面试抓手 | AI Infra 场景要补 GPU extended resource 和 device plugin。 |

<div class="card card-m">
<h3>调度与资源模型：回答“为什么 Pending”的核心模块</h3>
<p>调度和资源模型要一起学。<strong>资源模型定义 Pod 要什么、Node 有什么；调度器决定这个 Pod 放到哪里。</strong>面试中最常见的追问是：Pod 为什么 Pending、requests/limits 如何影响调度、QoS 如何影响驱逐、GPU 这类扩展资源如何被调度。</p>
</div>

## 先看这张地图

| 层次 | 你要回答的问题 | 典型字段 / 机制 | 出问题时的现象 |
|---|---|---|---|
| 资源需求 | Pod 需要多少 CPU、内存、GPU、PVC | `requests`、`limits`、Extended Resource、ResourceClaim | `Insufficient cpu/memory/nvidia.com/gpu` |
| 放置约束 | Pod 允许放到哪些节点、应该靠近或远离谁 | `nodeSelector`、NodeAffinity、PodAffinity、Taint/Toleration、TopologySpread | 节点很多但都被 affinity/taint 过滤 |
| 节点库存 | Node 真正还有多少可分配资源和设备 | Node `allocatable`、Device Plugin、DaemonSet 占用、系统预留 | 看似 8 卡机器，实际 allocatable 不足或设备不可用 |
| 调度执行 | scheduler 如何用上述信息做过滤和打分 | Filter、Score、Reserve、Bind | Pending 事件里出现具体 plugin 失败原因 |

阅读顺序建议：

1. 先理解 `requests/limits`：这是 Pod 资源声明和调度判断入口。
2. 再理解 `QoS`：它是由 CPU/Memory requests/limits 推导出的驱逐等级，不是调度资源本身。
3. 再理解放置约束速览，解释“资源够但为什么不能放”。
4. GPU / DRA / Affinity 的深入实现不要在本页展开，分别转到对应专题。
5. 最后再进入 `Scheduler 主链路` 和 `Scheduler 插件与扩展`，理解这些约束在 Framework 中挂到哪个扩展点。

<div class="card card-w">
<h3>本页边界：只讲资源模型，不讲插件实现</h3>
<p>本页回答 <strong>Pod 要什么、Node 有什么、哪些约束会让节点不可用</strong>。Scheduler Framework 的内部队列、cache、assume、binding cycle 放在「Scheduler 主链路」；自定义 Plugin、Extender、QueueingHint、可观测性放在「Scheduler 插件与扩展」。</p>
<table>
<tr><th>问题类型</th><th>应该看哪里</th></tr>
<tr><td>requests/limits、QoS、资源需求和放置约束总览</td><td>本页：调度与资源模型</td></tr>
<tr><td>Extended Resource、Device Plugin、DRA、MIG/MPS</td><td>AI Infra：GPU / 批调度 / DRA</td></tr>
<tr><td>NodeAffinity、PodAffinity、TaintToleration 的插件行为</td><td>Scheduler 插件与扩展 → 设计理念与经典插件</td></tr>
<tr><td>ActiveQ/BackoffQ/UnschedulableQ、Assume、Preemption</td><td>Scheduler 主链路</td></tr>
<tr><td>PreFilter/Filter/Score、QueueingHint、Extender、自定义插件</td><td>Scheduler 插件与扩展</td></tr>
<tr><td>Gang、Backfill、抢占代价、队列公平</td><td>任务调度理论</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Resource Requests / Limits：资源声明与运行时上限</h3>
<p><code>requests</code> 和 <code>limits</code> 是 Pod / Container 的资源声明。它们首先回答的是：<strong>调度时预留多少资源，运行时最多允许用多少资源。</strong></p>
<table>
<tr><th>概念</th><th>影响范围</th><th>关键结论</th><th>常见误区</th></tr>
<tr><td><code>requests</code></td><td>调度、资源预留、HPA 部分指标</td><td>scheduler 主要根据 requests 判断节点是否放得下</td><td>不是实时使用量；Pod 用得少也会按 request 占调度容量</td></tr>
<tr><td><code>limits</code></td><td>运行时限制</td><td>CPU limit 可能 throttling，内存超过 limit 通常 OOMKilled</td><td>limits 不是调度依据；内存 limit 过低会直接影响稳定性</td></tr>
</table>
<div class="qa-summary">面试口径：调度看 requests，不是看实时使用量；limits 主要管运行时上限，CPU 超限是 throttling，内存超限通常是 OOMKilled。</div>
</div>

<div class="card card-w">
<h3>QoS：由 requests / limits 推导出的驱逐等级</h3>
<p>QoS 不是一个用户随便填写的字段，而是 kubelet 根据 CPU / Memory 的 requests 和 limits 推导出的等级。它主要影响节点资源压力下的<strong>驱逐优先级</strong>，而不是决定调度器能不能把 Pod 放到节点上。</p>
<table>
<tr><th>QoS 等级</th><th>判定条件</th><th>驱逐倾向</th><th>典型场景</th></tr>
<tr><td>Guaranteed</td><td>每个容器 CPU/Memory requests 等于 limits 且都设置</td><td>驱逐优先级最低</td><td>核心在线服务、强 SLO 服务</td></tr>
<tr><td>Burstable</td><td>至少设置了一个 CPU/Memory request，但不完全满足 Guaranteed</td><td>中等驱逐优先级</td><td>大多数普通服务</td></tr>
<tr><td>BestEffort</td><td>没有设置 CPU/Memory requests 和 limits</td><td>最先被驱逐</td><td>临时任务、低优实验、开发测试</td></tr>
</table>
<div class="qa-summary">面试口径：QoS 看的是 CPU/Memory requests/limits 组合；驱逐还会结合 PriorityClass、资源压力和实际使用量。</div>
</div>

<div class="card card-s">
<h3>Requests / Limits 与 QoS 的关系</h3>
<table>
<tr><th>问题</th><th>看什么</th><th>一句话</th></tr>
<tr><td>Pod 能不能调度到某个节点？</td><td>Pod requests vs Node allocatable</td><td>调度阶段主要看 requests</td></tr>
<tr><td>容器运行中最多能用多少？</td><td>limits</td><td>运行时由 cgroup / runtime 限制</td></tr>
<tr><td>节点压力下谁先被赶走？</td><td>QoS + PriorityClass + 实际资源压力</td><td>QoS 是驱逐排序的重要输入</td></tr>
<tr><td>GPU request/limit 怎么理解？</td><td>Extended Resource</td><td>普通 GPU 扩展资源通常 requests = limits，按整数设备调度</td></tr>
</table>
<div class="qa-summary">收束：requests/limits 是输入字段，QoS 是推导结果；调度主要看 requests，驱逐主要看 QoS、优先级和资源压力。</div>
</div>

<div class="card card-s">
<h3>放置约束速览：资源够也可能 Pending</h3>
<p>本页只保留调度资源模型视角：Pod 除了要资源，还会声明“能去哪里、应该靠近谁、要不要均匀分布、能不能容忍节点排斥”。这些约束最终会映射到 scheduler 的 Filter / Score 插件。</p>
<table>
<tr><th>机制</th><th>解决什么问题</th><th>深入位置</th></tr>
<tr><td>nodeSelector / Node Affinity</td><td>Pod 选择什么样的节点，例如 GPU 型号、机房、磁盘类型</td><td>Scheduler 插件与扩展 → 设计理念与经典插件</td></tr>
<tr><td>Pod Affinity / Anti-Affinity</td><td>Pod 和已有 Pod 靠近或远离，例如靠近 cache、分散同服务副本</td><td>Scheduler 插件与扩展 → 设计理念与经典插件</td></tr>
<tr><td>Topology Spread Constraints</td><td>控制副本在 zone、node、rack 等拓扑域内均匀分布</td><td>本页保留核心语义</td></tr>
<tr><td>Taint / Toleration</td><td>节点拒绝普通 Pod，Pod 显式声明自己能容忍</td><td>本页保留核心语义；插件行为见经典插件</td></tr>
</table>
<div class="qa-summary">本页记入口即可：资源不足看 requests/allocatable；资源够但不能放，通常看 Affinity、Taint、Topology Spread、PVC/ResourceClaim 和自定义插件。</div>
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

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
