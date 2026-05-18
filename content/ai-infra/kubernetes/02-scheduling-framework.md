<div class="card card-s">
<h3>Kubernetes 调度体系全景</h3>
<p><strong>Scheduling Framework 只是 kube-scheduler 的插件化内核</strong>，不是 Kubernetes 调度体系的全部。完整调度体系还包括：调度器进程、调度队列、调度缓存、Pod 约束语义、优先级与抢占、调度配置/Profile、默认插件、扩展调度器，以及批调度/重调度生态。</p>
<div class="comp-grid">
<div class="comp-item"><div class="comp-name">调度器本体</div><div class="comp-role">kube-scheduler 监听未绑定 Pod，为其选择 Node，并把绑定结果写回 API Server。</div><div class="comp-detail">核心问题是“哪个 Pod 先调度、哪些节点可行、哪个节点最好、失败后怎么处理”。</div></div>
<div class="comp-item"><div class="comp-name">调度输入语义</div><div class="comp-role">PodSpec 中的 requests、nodeSelector、affinity、tolerations、topologySpreadConstraints、priorityClassName 等。</div><div class="comp-detail">这些字段决定 Filter/Score 的约束和偏好，是面试排查 Pending 的重点。</div></div>
<div class="comp-item"><div class="comp-name">Scheduling Framework</div><div class="comp-role">把调度流程拆成 QueueSort、PreFilter、Filter、Score、Reserve、Permit、Bind 等扩展点。</div><div class="comp-detail">它解决“如何扩展调度决策”，但不等于全部调度能力。</div></div>
<div class="comp-item"><div class="comp-name">配置与 Profile</div><div class="comp-role">通过 KubeSchedulerConfiguration 配置 plugins、pluginConfig、profiles、percentageOfNodesToScore 等。</div><div class="comp-detail">多 Profile 可以让不同 Pod 使用不同 schedulerName 和插件组合。</div></div>
<div class="comp-item"><div class="comp-name">失败与抢占</div><div class="comp-role">调度失败后进入队列重试；高优先级 Pod 可触发 PostFilter 抢占。</div><div class="comp-detail">涉及 UnschedulableQ、BackoffQ、nominatedNodeName、PDB、优雅终止。</div></div>
<div class="comp-item"><div class="comp-name">扩展生态</div><div class="comp-role">多调度器、Scheduler Plugins、Descheduler、Kueue、Volcano、Cluster Autoscaler 等。</div><div class="comp-detail">AI Infra 面试通常会追问 GPU 拓扑、Gang Scheduling、多租户队列和资源回收。</div></div>
</div>
</div>

<div class="card card-w">
<h3>面试学习地图：不要只背扩展点</h3>
<table>
<tr><th>层次</th><th>要掌握什么</th><th>典型问题</th><th>推荐入口</th></tr>
<tr><td>基础链路</td><td>kube-scheduler 如何 watch Pod、选 Node、写绑定结果</td><td>Pod 创建后怎么被调度到节点？</td><td><a href="https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/">kube-scheduler</a></td></tr>
<tr><td>约束语义</td><td>requests、亲和性、污点容忍、拓扑分布、优先级</td><td>为什么资源够但 Pod 仍然 Pending？</td><td><a href="https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/">Assigning Pods to Nodes</a></td></tr>
<tr><td>插件框架</td><td>扩展点、默认插件、Filter/Score/Reserve/Permit/Bind</td><td>自定义 GPU 调度插件挂在哪个扩展点？</td><td><a href="https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/">Scheduling Framework</a></td></tr>
<tr><td>调度配置</td><td>KubeSchedulerConfiguration、profiles、插件权重、调度器参数</td><td>如何让不同 Pod 使用不同调度策略？</td><td><a href="https://kubernetes.io/docs/reference/scheduling/config/">Scheduler Configuration</a></td></tr>
<tr><td>高级场景</td><td>抢占、Gang Scheduling、重调度、队列、多租户、公平性</td><td>为什么训练任务要 Volcano/Kueue？</td><td><a href="https://kueue.sigs.k8s.io/docs/overview/">Kueue</a> / <a href="https://volcano.sh/en/docs/">Volcano</a></td></tr>
</table>
</div>

<div class="card card-m">
<h3>一图看懂调度链路</h3>
<p>Scheduling Framework 的核心价值，是把“给 Pod 选节点”拆成可插拔的多个扩展点。面试时不要只背扩展点名称，更重要的是能说清楚：Pod 如何入队、如何过滤节点、如何打分、如何预占、如何绑定，以及失败后如何重试。</p>
<div class="sched-flow">
<svg viewBox="0 0 900 360" xmlns="http://www.w3.org/2000/svg">
<defs>
<marker id="schedArrow" markerWidth="9" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,9 3.5,0 7" fill="var(--border)"/></marker>
</defs>
<rect x="24" y="38" width="132" height="62" rx="14" class="sched-node sched-api"/>
<text x="90" y="64" text-anchor="middle" class="sched-label">API Server</text>
<text x="90" y="83" text-anchor="middle" class="sched-desc">Pod 写入集群状态</text>
<rect x="194" y="38" width="140" height="62" rx="14" class="sched-node sched-cache"/>
<text x="264" y="64" text-anchor="middle" class="sched-label">Informer / Cache</text>
<text x="264" y="83" text-anchor="middle" class="sched-desc">watch Pod 和 Node</text>
<rect x="372" y="38" width="132" height="62" rx="14" class="sched-node sched-queue"/>
<text x="438" y="64" text-anchor="middle" class="sched-label">ActiveQ</text>
<text x="438" y="83" text-anchor="middle" class="sched-desc">按 QueueSort 出队</text>
<path d="M156 69 L194 69" class="sched-arrow"/>
<path d="M334 69 L372 69" class="sched-arrow"/>
<rect x="54" y="148" width="120" height="58" rx="14" class="sched-node"/>
<text x="114" y="172" text-anchor="middle" class="sched-label">PreFilter</text>
<text x="114" y="190" text-anchor="middle" class="sched-desc">预计算 / 早拒绝</text>
<rect x="210" y="148" width="120" height="58" rx="14" class="sched-node"/>
<text x="270" y="172" text-anchor="middle" class="sched-label">Filter</text>
<text x="270" y="190" text-anchor="middle" class="sched-desc">硬约束预选</text>
<rect x="366" y="148" width="120" height="58" rx="14" class="sched-node"/>
<text x="426" y="172" text-anchor="middle" class="sched-label">Score</text>
<text x="426" y="190" text-anchor="middle" class="sched-desc">软偏好打分</text>
<rect x="522" y="148" width="120" height="58" rx="14" class="sched-node"/>
<text x="582" y="172" text-anchor="middle" class="sched-label">Reserve</text>
<text x="582" y="190" text-anchor="middle" class="sched-desc">缓存中预占资源</text>
<rect x="678" y="148" width="120" height="58" rx="14" class="sched-node"/>
<text x="738" y="172" text-anchor="middle" class="sched-label">Permit</text>
<text x="738" y="190" text-anchor="middle" class="sched-desc">Approve / Wait / Deny</text>
<path d="M438 100 C438 124 114 120 114 148" class="sched-arrow"/>
<path d="M174 177 L210 177" class="sched-arrow"/>
<path d="M330 177 L366 177" class="sched-arrow"/>
<path d="M486 177 L522 177" class="sched-arrow"/>
<path d="M642 177 L678 177" class="sched-arrow"/>
<rect x="210" y="256" width="120" height="58" rx="14" class="sched-node sched-bind"/>
<text x="270" y="280" text-anchor="middle" class="sched-label">PreBind</text>
<text x="270" y="298" text-anchor="middle" class="sched-desc">绑定前准备</text>
<rect x="366" y="256" width="120" height="58" rx="14" class="sched-node sched-bind"/>
<text x="426" y="280" text-anchor="middle" class="sched-label">Bind</text>
<text x="426" y="298" text-anchor="middle" class="sched-desc">写 API Server</text>
<rect x="522" y="256" width="120" height="58" rx="14" class="sched-node sched-bind"/>
<text x="582" y="280" text-anchor="middle" class="sched-label">PostBind</text>
<text x="582" y="298" text-anchor="middle" class="sched-desc">事件 / 指标 / 清理</text>
<rect x="690" y="256" width="140" height="58" rx="14" class="sched-node sched-kubelet"/>
<text x="760" y="280" text-anchor="middle" class="sched-label">kubelet</text>
<text x="760" y="298" text-anchor="middle" class="sched-desc">watch 后启动 Pod</text>
<path d="M738 206 C738 235 270 228 270 256" class="sched-arrow"/>
<path d="M330 285 L366 285" class="sched-arrow"/>
<path d="M486 285 L522 285" class="sched-arrow"/>
<path d="M642 285 L690 285" class="sched-arrow"/>
<rect x="628" y="36" width="238" height="68" rx="14" class="sched-note"/>
<text x="747" y="61" text-anchor="middle" class="sched-label">失败路径</text>
<text x="747" y="80" text-anchor="middle" class="sched-desc">Filter 失败 → PostFilter 抢占</text>
<text x="747" y="96" text-anchor="middle" class="sched-desc">仍失败 → UnschedulableQ / BackoffQ</text>
<path d="M270 148 C354 108 620 100 668 104" class="sched-arrow sched-dashed"/>
</svg>
</div>
</div>

<div class="card card-m">
<h3>核心概念：两个周期</h3>
<table>
<tr><th>阶段</th><th>包含步骤</th><th>并发特点</th><th>面试要点</th></tr>
<tr><td>Scheduling Cycle</td><td>QueueSort、PreFilter、Filter、PostFilter、PreScore、Score、Reserve</td><td>对一个 Pod 的调度决策通常串行执行</td><td>负责“选哪个节点”，需要保证调度器缓存中的资源预占一致性</td></tr>
<tr><td>Binding Cycle</td><td>Permit、PreBind、Bind、PostBind</td><td>不同 Pod 的绑定可以并行</td><td>负责“把选择写回 API Server”，绑定慢不应阻塞后续调度决策</td></tr>
</table>
<p><strong>一句话回答</strong>：Scheduling Cycle 做决策，Binding Cycle 做落盘；前者要谨慎维护调度器内部状态，后者可以并行提高吞吐。</p>
</div>

<div class="card card-m">
<h3>扩展点与插件应该怎么记</h3>
<p>K8s 官方常说 Scheduling Framework 有 11 个主要扩展点。实际学习时可以按“排序、预处理、过滤、失败补救、打分、预占、准入、绑定”来记。<strong>NormalizeScore</strong> 是 Score 插件可实现的归一化接口，常和 Score 放在一起讲，不必单独当作主扩展点背。</p>
<table>
<tr><th>扩展点</th><th>作用</th><th>典型插件/场景</th><th>面试记忆点</th></tr>
<tr><td>QueueSort</td><td>决定 ActiveQ 中 Pod 的出队顺序</td><td>PrioritySort</td><td>通常按优先级和时间排序，一个调度 profile 只能有一个 QueueSort 插件</td></tr>
<tr><td>PreFilter</td><td>提前计算 Pod 资源需求或校验硬条件</td><td>NodeResourcesFit、InterPodAffinity</td><td>减少后续每个节点重复计算，失败可直接拒绝</td></tr>
<tr><td>Filter</td><td>筛掉不满足硬约束的节点</td><td>资源不足、NodeAffinity、Taint/Toleration、VolumeBinding</td><td>硬约束，不满足就是不能调度</td></tr>
<tr><td>PostFilter</td><td>Filter 找不到节点时的补救</td><td>DefaultPreemption</td><td>最重要场景是抢占，但抢占也可能失败</td></tr>
<tr><td>PreScore / Score</td><td>对可行节点按软偏好打分</td><td>NodeResourcesBalancedAllocation、ImageLocality、NodeAffinity</td><td>软偏好，分数会归一化并加权求和</td></tr>
<tr><td>Reserve / Unreserve</td><td>在调度器缓存中预占资源，失败时回滚</td><td>资源预留、Gang 调度辅助状态</td><td>不是写 API Server，而是保护调度器内部一致性</td></tr>
<tr><td>Permit</td><td>最终准入，可批准、拒绝或等待</td><td>Gang Scheduling、容量门控</td><td>Wait 适合等一组 Pod 凑齐后一起放行</td></tr>
<tr><td>PreBind / Bind / PostBind</td><td>绑定前准备、写 API Server、绑定后清理</td><td>VolumeBinding、自定义 Binder、指标事件</td><td>Bind 之后 kubelet 才会 watch 到已绑定 Pod 并启动</td></tr>
</table>
</div>

<div class="card card-s">
<h3>三个队列：调度失败后 Pod 去哪里</h3>
<div class="queue-grid">
<div class="queue-item"><div class="queue-name">ActiveQ</div><div class="queue-desc">活跃队列。新 Pod、退避结束的 Pod、被事件激活的 Pod 会进入这里，按 QueueSort 排序后等待调度。</div></div>
<div class="queue-item"><div class="queue-name">BackoffQ</div><div class="queue-desc">退避队列。调度失败但可重试的 Pod 会先等待指数退避，避免反复占用调度器 CPU。</div></div>
<div class="queue-item"><div class="queue-name">UnschedulableQ</div><div class="queue-desc">不可调度队列。当前集群状态下无解的 Pod 会在这里等待集群事件，例如节点加入、Pod 删除、PV 变化。</div></div>
</div>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod 调度失败后的完整流转过程？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">正常尝试</div><p>Pod 从 ActiveQ 出队后进入调度流程，依次经过 Filter、Score、Reserve、Bind 等阶段。</p></div>
<div class="qa-section"><div class="qa-section-title">失败处理</div><ol><li>如果 Filter 找不到可行节点，进入 PostFilter。</li><li>PostFilter 默认尝试抢占低优先级 Pod。</li><li>抢占成功时设置 nominatedNodeName，并等待被抢占 Pod 终止。</li><li>抢占失败或没有合适牺牲者时，Pod 进入 UnschedulableQ。</li></ol></div>
<div class="qa-section"><div class="qa-section-title">重新入队</div><p>节点新增、Pod 删除、PV 绑定变化等事件会重新激活 Pod，使其进入 BackoffQ 或 ActiveQ，再次尝试调度。</p></div>
<div class="qa-summary">面试记忆：ActiveQ 出队调度，失败先抢占，仍失败进不可调度队列，等集群事件触发重试。</div>
</div>
</div>
</div>

<div class="card card-w">
<h3>抢占机制：高优先级 Pod 为什么也可能 Pending</h3>
<ol>
<li><strong>触发条件</strong>：高优先级 Pod 无法通过 Filter 找到可行节点，PostFilter 尝试抢占低优先级 Pod。</li>
<li><strong>候选节点模拟</strong>：调度器在缓存中模拟移除低优先级 Pod，看该节点是否能满足高优先级 Pod 的资源和约束。</li>
<li><strong>牺牲者选择</strong>：优先选择违反 PDB 更少、驱逐 Pod 更少、牺牲者优先级更低的方案。</li>
<li><strong>nominatedNodeName</strong>：抢占成功后先标记候选节点，但不会立即绑定，因为被抢占 Pod 还要优雅终止。</li>
<li><strong>不保证成功</strong>：等待过程中节点状态可能变化，或者 PDB/亲和性/新 Pod 干扰导致最终仍然调度失败。</li>
</ol>
</div>

<div class="card card-m">
<h3>实际场景：实现 GPU 拓扑感知调度插件</h3>
<p>假设我们有一个 AI 训练集群，节点上有不同 GPU 拓扑：有些节点 8 张 GPU 之间有 NVLink，有些节点只有 PCIe；多卡训练任务更希望调度到 NVLink 更好的节点，否则 AllReduce 通信会慢。这个场景很适合用 Scheduling Framework 说明“插件应该放在哪里”。</p>

<h4>1. 场景输入</h4>
<table>
<tr><th>输入</th><th>示例</th><th>作用</th></tr>
<tr><td>Pod 资源请求</td><td>requests: nvidia.com/gpu: 4</td><td>判断是不是多 GPU 任务，以及需要几张 GPU</td></tr>
<tr><td>节点标签</td><td>gpu.topology/nvlink: "true"</td><td>快速区分 NVLink 节点和普通 PCIe 节点</td></tr>
<tr><td>节点扩展资源</td><td>nvidia.com/gpu allocatable</td><td>由 device plugin 上报，调度器按 requests 做资源判断</td></tr>
<tr><td>拓扑元数据</td><td>GPU 卡组、NUMA、NVLink fabric</td><td>生产中可由节点 agent 写入 CRD、annotation 或 scheduler cache</td></tr>
</table>

<h4>2. 扩展点选择</h4>
<table>
<tr><th>扩展点</th><th>做什么</th><th>为什么</th></tr>
<tr><td>PreFilter</td><td>解析 Pod 是否请求 GPU、请求几张 GPU，并写入 CycleState</td><td>避免每个节点重复解析 Pod 资源请求</td></tr>
<tr><td>Filter</td><td>过滤没有足够 GPU、没有目标 GPU 型号、没有可用卡组的节点</td><td>硬约束必须放 Filter，不满足就不能调度</td></tr>
<tr><td>Score</td><td>给 NVLink 更完整、跨 NUMA 更少、模型缓存更近的节点更高分</td><td>拓扑好坏通常是软偏好，适合 Score</td></tr>
<tr><td>Reserve / Unreserve</td><td>在调度器缓存里预占具体 GPU 卡组，后续失败则回滚</td><td>防止两个 Pod 同时选中同一组 GPU</td></tr>
<tr><td>Permit</td><td>如果是一组训练 Worker，可等待全部 Worker 都可调度后再放行</td><td>Gang Scheduling 场景需要整体准入</td></tr>
</table>

<h4>3. 最小可行实现思路</h4>
<ol>
<li><strong>先做 Filter</strong>：没有 GPU、GPU 数量不足、节点标签不满足的节点直接排除。</li>
<li><strong>再做 Score</strong>：对所有可行节点打分，NVLink 节点高分，PCIe 节点低分。</li>
<li><strong>最后加 Reserve</strong>：如果需要选择具体 GPU 卡组，就在 Reserve 阶段预占，失败时 Unreserve 回滚。</li>
<li><strong>不要一开始就做复杂 Gang Scheduling</strong>：如果只是单个多卡 Pod，Filter + Score 通常已经能解释清楚。</li>
</ol>

<h4>4. 伪代码</h4>
```go
// PreFilter: 解析 Pod 的 GPU 请求，并写入 CycleState。
func PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) *framework.Status {
    gpuCount := getGPURequest(pod)
    state.Write("gpuRequest", gpuCount)
    return framework.NewStatus(framework.Success)
}

// Filter: 硬约束，不满足就不能调度。
func Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    gpuCount := state.Read("gpuRequest")
    if nodeFreeGPU(nodeInfo) < gpuCount {
        return framework.NewStatus(framework.Unschedulable, "insufficient gpu")
    }
    if gpuCount >= 4 && nodeInfo.Node().Labels["gpu.topology/nvlink"] != "true" {
        return framework.NewStatus(framework.Unschedulable, "large gpu job requires nvlink")
    }
    return framework.NewStatus(framework.Success)
}

// Score: 软偏好，节点仍然可用，只是优先级不同。
func Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    node := getNode(nodeName)
    if node.Labels["gpu.topology/nvlink"] == "true" {
        return 100, framework.NewStatus(framework.Success)
    }
    return 30, framework.NewStatus(framework.Success)
}
```

<h4>5. 调度器配置示例</h4>
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: gpu-aware-scheduler
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
            weight: 50
      reserve:
        enabled:
          - name: GPUTopology
```

<h4>6. Pod 使用示例</h4>
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: train-4gpu
spec:
  schedulerName: gpu-aware-scheduler
  containers:
    - name: trainer
      image: pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime
      resources:
        requests:
          nvidia.com/gpu: "4"
        limits:
          nvidia.com/gpu: "4"
```

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试中怎么讲这个案例？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">业务目标</div><p>多 GPU 训练任务希望优先使用 NVLink 拓扑更好的节点，减少 AllReduce 通信开销。</p></div>
<div class="qa-grid"><div class="qa-mini"><strong>Filter</strong>GPU 数量、型号、租户隔离是硬约束，不满足直接排除。</div><div class="qa-mini"><strong>Score</strong>NVLink 更优、跨 NUMA 更少、模型缓存更近是软偏好，用分数表达。</div><div class="qa-mini"><strong>Reserve</strong>需要绑定具体 GPU 卡组时，在调度器缓存中预占并支持回滚。</div><div class="qa-mini"><strong>Permit</strong>一组分布式训练 Worker 需要整体准入时使用，或直接选 Volcano/Kueue。</div></div>
<div class="qa-summary">面试总结：先讲业务目标，再讲硬约束放 Filter、软偏好放 Score、具体卡组放 Reserve、分布式训练考虑 Gang Scheduling。</div>
</div>
</div>
</div>

<div class="card card-d">
<h3>面试高频追问</h3>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Filter 和 Score 的区别是什么？</div>
<div class="qa-a">
<div class="qa-grid"><div class="qa-mini"><strong>Filter</strong>硬约束，决定节点能不能用。典型例子：资源不足、NodeSelector 不匹配、Taint 不能容忍。</div><div class="qa-mini"><strong>Score</strong>软偏好，决定可行节点中哪个更好。典型例子：资源更均衡、镜像已存在、亲和性更高。</div></div>
<div class="qa-summary">关键点：Filter 不通过的节点不会进入 Score；Filter 是可行性，Score 是优先级。</div>
</div>
</div>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么调度器只看 requests，不看实时利用率？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">为什么看 requests</div><p>requests 是 Kubernetes 的资源承诺和调度依据，稳定、可预测，并能和 ResourceQuota、QoS、驱逐机制对齐。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么不直接看实时利用率</div><p>实时利用率波动很大，直接用于调度容易导致抖动、迁移冲动和决策不稳定。</p></div>
<div class="qa-section"><div class="qa-section-title">生产增强方式</div><p>如果要引入实时负载，通常通过自定义 Score 插件、Descheduler、离线画像或预测模型增强，而不是替代 requests。</p></div>
</div>
</div>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 拓扑感知调度应该放在哪些扩展点？</div>
<div class="qa-a">
<div class="qa-grid"><div class="qa-mini"><strong>Filter</strong>节点是否有足够 GPU、是否满足 MIG/整卡需求、是否满足同机硬约束。</div><div class="qa-mini"><strong>Score</strong>优先选择 NVLink 拓扑更好、跨 NUMA 更少、模型缓存更近的节点。</div><div class="qa-mini"><strong>Reserve</strong>需要预占具体 GPU 组合时维护调度器侧状态。</div><div class="qa-mini"><strong>Unreserve</strong>后续阶段失败时回滚预占，避免缓存状态泄漏。</div></div>
<div class="qa-summary">判断方式：不能违反的是 Filter；更好但不是必须的是 Score；涉及具体卡组并发冲突的是 Reserve。</div>
</div>
</div>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Gang Scheduling 为什么常用 Volcano/Kueue，而不是只靠原生调度器？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">原生调度器局限</div><p>默认 kube-scheduler 更擅长逐 Pod 做调度决策，缺少“这一组 Pod 必须一起满足”的队列语义。</p></div>
<div class="qa-section"><div class="qa-section-title">训练任务需求</div><p>分布式训练要求一组 Worker 同时达到最小可运行规模，否则部分 Pod 先启动也无法有效训练。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么用 Volcano/Kueue</div><p>Gang Scheduling 需要 PodGroup、最小成员数、队列、公平性、整体准入和资源回收等能力，Volcano/Kueue 已经提供成熟抽象。</p></div>
</div>
</div>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一个 Pod 一直 Pending，怎么排查？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">第一步：看直接原因</div><p>先看 Pod Events 和 scheduler 日志，确认 Pending 是资源不足、亲和性/反亲和性、taint/toleration、PVC 未绑定、配额限制还是调度器异常。</p></div>
<div class="qa-section"><div class="qa-section-title">第二步：看集群状态</div><p>检查节点 allocatable、已有 Pod requests 占用、Pod priority、PDB、namespace quota、节点污点和标签。</p></div>
<div class="qa-section"><div class="qa-section-title">GPU 专项</div><p>检查 device plugin 是否运行、nvidia.com/gpu 是否上报、MIG 配置是否正确、扩展资源是否已被占满。</p></div>
<div class="qa-summary">排查顺序：Events → scheduler 日志 → 节点资源/约束 → 配额/PDB → GPU device plugin。</div>
</div>
</div>
</div>


<div class="card card-d">
<h3>官方资料与扩展链接</h3>
<div class="resource-grid">
<a class="resource-card" href="https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/"><div class="resource-type">official</div><div class="resource-title">kube-scheduler</div><div class="resource-desc">官方对 kube-scheduler 职责、调度过程和基本机制的说明。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/"><div class="resource-type">official</div><div class="resource-title">Scheduling Framework</div><div class="resource-desc">插件扩展点、调度周期、绑定周期、Reserve/Permit/Bind 等核心概念。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/reference/scheduling/config/"><div class="resource-type">official</div><div class="resource-title">Scheduler Configuration</div><div class="resource-desc">KubeSchedulerConfiguration、Profiles、插件启停、插件权重等配置入口。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/reference/config-api/kube-scheduler-config.v1/"><div class="resource-type">api</div><div class="resource-title">kube-scheduler config API</div><div class="resource-desc">调度器配置 API 字段定义，适合查 profiles、plugins、pluginConfig。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/"><div class="resource-type">official</div><div class="resource-title">Assigning Pods to Nodes</div><div class="resource-desc">nodeSelector、nodeAffinity、pod affinity/anti-affinity 等节点选择语义。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/"><div class="resource-type">official</div><div class="resource-title">Taints and Tolerations</div><div class="resource-desc">污点和容忍机制，常用于专用节点、GPU 节点和隔离场景。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/"><div class="resource-type">official</div><div class="resource-title">Pod Topology Spread Constraints</div><div class="resource-desc">跨 zone、node、rack 等拓扑域均匀分布 Pod 的官方机制。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/"><div class="resource-type">official</div><div class="resource-title">Pod Priority and Preemption</div><div class="resource-desc">PriorityClass、抢占、nominatedNodeName、PDB 影响等高频面试点。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/scheduling-eviction/pod-scheduling-readiness/"><div class="resource-type">official</div><div class="resource-title">Pod Scheduling Readiness</div><div class="resource-desc">Scheduling Gates：让 Pod 在满足外部条件前不进入调度。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/"><div class="resource-type">official</div><div class="resource-title">Device Plugins</div><div class="resource-desc">GPU 等扩展资源如何上报到 kubelet，并被调度器按 extended resource 使用。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/tasks/extend-kubernetes/configure-multiple-schedulers/"><div class="resource-type">official</div><div class="resource-title">Configure Multiple Schedulers</div><div class="resource-desc">多个调度器并存和 Pod 使用 schedulerName 指定调度器。</div></a>
<a class="resource-card" href="https://github.com/kubernetes-sigs/scheduler-plugins"><div class="resource-type">sig</div><div class="resource-title">kubernetes-sigs/scheduler-plugins</div><div class="resource-desc">社区维护的调度插件集合，适合理解高级插件与示例实现。</div></a>
<a class="resource-card" href="https://github.com/kubernetes-sigs/descheduler"><div class="resource-type">sig</div><div class="resource-title">Descheduler</div><div class="resource-desc">重调度/再平衡工具，解决集群状态长期漂移后的优化问题。</div></a>
<a class="resource-card" href="https://kueue.sigs.k8s.io/docs/overview/"><div class="resource-type">batch</div><div class="resource-title">Kueue</div><div class="resource-desc">Kubernetes 原生队列管理，适合 batch、ML training、多租户 quota 场景。</div></a>
<a class="resource-card" href="https://volcano.sh/en/docs/"><div class="resource-type">batch</div><div class="resource-title">Volcano</div><div class="resource-desc">批调度系统，提供 PodGroup、Gang Scheduling、队列、公平性等能力。</div></a>
</div>
</div>
