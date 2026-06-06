<div class="card card-m">
<h3>调度与资源模型：回答“为什么 Pending”的核心模块</h3>
<p>调度和资源模型要一起学。<strong>资源模型定义 Pod 要什么、Node 有什么；调度器决定这个 Pod 放到哪里。</strong>面试中最常见的追问是：Pod 为什么 Pending、requests/limits 如何影响调度、QoS 如何影响驱逐、GPU 这类扩展资源如何被调度。</p>
</div>

<div class="card card-s">
<h3>Scheduling Framework 全链路</h3>
<table>
<tr><th>阶段</th><th>作用</th><th>典型插件/逻辑</th><th>面试重点</th></tr>
<tr><td>QueueSort</td><td>决定 Pod 出队顺序</td><td>PrioritySort</td><td>高优先级 Pod 先调度</td></tr>
<tr><td>PreFilter</td><td>预处理 Pod 约束</td><td>NodeResourcesFit、InterPodAffinity</td><td>提前计算亲和性、资源需求</td></tr>
<tr><td>Filter</td><td>过滤不可用节点</td><td>NodeUnschedulable、TaintToleration、NodeAffinity、NodeResourcesFit</td><td>Pending 大多卡在这里</td></tr>
<tr><td>PostFilter</td><td>过滤失败后的补救</td><td>DefaultPreemption</td><td>触发抢占</td></tr>
<tr><td>PreScore / Score</td><td>给可用节点打分</td><td>NodeResourcesBalancedAllocation、ImageLocality、TopologySpread</td><td>不是能放就结束，还要选更优节点</td></tr>
<tr><td>Reserve / Unreserve</td><td>临时预留资源</td><td>VolumeBinding、外部资源插件</td><td>为绑定周期做状态保护</td></tr>
<tr><td>Permit</td><td>允许、拒绝或等待</td><td>Gang Scheduling 插件</td><td>批调度常在这里等待一组 Pod 凑齐</td></tr>
<tr><td>PreBind / Bind / PostBind</td><td>最终绑定和后处理</td><td>DefaultBinder、VolumeBinding</td><td>写 Pod 的 nodeName</td></tr>
</table>
<p>一次调度通常分为 <strong>Scheduling Cycle</strong> 和 <strong>Binding Cycle</strong>。前者串行选择节点，后者可以并行执行绑定相关动作。</p>
</div>

<div class="card card-d">
<h3>调度队列与抢占</h3>
<table>
<tr><th>机制</th><th>作用</th><th>回答要点</th></tr>
<tr><td>ActiveQ</td><td>当前可尝试调度的 Pod 队列</td><td>按优先级和队列排序出队</td></tr>
<tr><td>BackoffQ</td><td>刚失败、需要退避的 Pod</td><td>避免频繁重试打爆 scheduler</td></tr>
<tr><td>UnschedulableQ</td><td>当前没有可行节点的 Pod</td><td>等待节点、资源、Pod 删除等事件触发重新入队</td></tr>
<tr><td>Preemption</td><td>高优先级 Pod 抢占低优先级 Pod</td><td>只解决资源不足等可通过驱逐解决的问题，不解决 nodeSelector 不匹配</td></tr>
<tr><td>PriorityClass</td><td>定义 Pod 优先级</td><td>优先级越高越容易先调度、触发抢占时更有优势</td></tr>
</table>
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

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod Pending 时，调度侧怎么排查？</div>
<div class="qa-a"><p>先看 <code>kubectl describe pod</code> 的 Events，确认是资源不足、污点不容忍、nodeSelector/affinity 不匹配、PVC 未绑定，还是抢占也无法解决。再看节点 allocatable、Pod requests、PriorityClass、scheduler 日志和相关调度插件。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 GPU requests 和 limits 通常要相等？</div>
<div class="qa-a"><p>GPU 属于离散扩展资源，Kubernetes 默认无法像 CPU 那样按时间片细粒度超卖，因此通常只在 limits 中声明，requests 会被视为等于 limits。这样 scheduler 和 kubelet 能按整数设备做一致的分配。</p></div>
</div>
