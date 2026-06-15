## 一句话结论

自定义调度逻辑优先用 Scheduling Framework Plugin，复杂系统再考虑 extender 或独立 scheduler。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Kubernetes 核心 |
| 章节类型 | 系统类 |
| 解决问题 | 围绕控制面、调度资源模型、Workload Controller、网络存储、安全多租户、排障和 AI Infra GPU/DRA 建立平台面试答案。 |
| 面试抓手 | 用 GPU 拓扑感知 Filter/Score 举例。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m">
<h3>自定义 Scheduler Plugin 实战</h3>
<p>面试中经常被问到"你有没有写过自定义调度插件"。回答时应该先讲清楚<strong>有哪些实现方式</strong>，再深入 Framework Plugin 的开发流程，最后给出具体代码示例。</p>
</div>

<div class="card card-s">
<h3>三种实现自定义调度逻辑的方式</h3>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:140px">方式</th><th>原理</th><th>优点</th><th>缺点</th><th>适用场景</th></tr>
</thead>
<tbody>
<tr><td class="q-dim">Scheduling Framework Plugin<br>(In-tree)</td><td>实现 Framework 扩展点接口，编译进 scheduler 二进制</td><td>性能最好，直接访问 scheduler cache 和 NodeInfo；可以接入完整生命周期（QueueSort 到 PostBind）</td><td>需要重新编译 scheduler；升级 K8s 版本时需要适配接口变化</td><td>性能敏感的调度逻辑（GPU 拓扑、NUMA、Gang）；需要访问 cache 或参与 Reserve/Permit 等状态阶段</td></tr>
<tr><td class="q-dim">Scheduler Extender<br>(Out-of-tree HTTP)</td><td>独立 HTTP 服务，scheduler 通过 HTTP 调用 Filter / Prioritize / Bind 等接口</td><td>独立部署，不侵入 scheduler 代码；可以用任意语言开发</td><td>HTTP 调用延迟高（ms 级）；无法访问 scheduler cache；只能参与 Filter / Score / Bind 等有限阶段</td><td>简单过滤逻辑（如特殊 label 过滤）；非性能敏感的定制需求；多语言团队</td></tr>
<tr><td class="q-dim">Multiple Scheduler<br>(独立 Scheduler)</td><td>部署另一个完整的 scheduler 实例，Pod 通过 <code>schedulerName</code> 指定</td><td>完全独立，策略隔离；可以用不同版本的 scheduler</td><td>不同 scheduler 之间不共享 cache，可能产生资源竞争；运维复杂（需要维护两套 scheduler）</td><td>业务强隔离（GPU 任务 vs CPU 任务）；需要完全不同的调度策略</td></tr>
</tbody>
</table>
</div>
<div class="qa-summary">面试要点：三种方式的本质区别是<strong>"调度逻辑跑在 scheduler 进程内还是进程外"</strong>。Framework Plugin 跑在进程内，性能最好、能力最强，是 K8s 官方推荐方式。Extender 和 Multiple Scheduler 是历史兼容方案，新功能应优先考虑 Framework Plugin。</div>
</div>

<div class="card card-m">
<h3>Scheduling Framework Plugin 开发详解</h3>
<p>Scheduler Framework 定义了从 Pod 入队到绑定的完整生命周期，每个阶段都是一个<strong>扩展点（Extension Point）</strong>。开发自定义插件就是实现一个或多个扩展点接口。</p>

<div class="qa-section"><div class="qa-section-title">Framework 扩展点全景</div>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:100px">扩展点</th><th style="width:60px">类型</th><th>触发时机</th><th>典型用途</th></tr>
</thead>
<tbody>
<tr><td class="q-dim">QueueSort</td><td>排序</td><td>Pod 进入 ActiveQ 时</td><td>自定义出队顺序（如短作业优先、SLA 排序）</td></tr>
<tr><td class="q-dim">PreFilter</td><td>过滤</td><td>Filter 之前，预处理 Pod 信息</td><td>计算 Pod 的调度约束、检查 PodGroup 完整性</td></tr>
<tr><td class="q-dim">Filter</td><td>过滤</td><td>对每个候选节点判断是否可用</td><td>GPU 拓扑匹配、NUMA 亲和、自定义资源检查</td></tr>
<tr><td class="q-dim">PostFilter</td><td>过滤</td><td>Filter 后无可用节点时</td><td>Preemption 抢占逻辑（选择 victim）</td></tr>
<tr><td class="q-dim">PreScore</td><td>打分</td><td>Score 之前，预处理打分数据</td><td>预计算节点统计信息</td></tr>
<tr><td class="q-dim">Score</td><td>打分</td><td>对每个候选节点打分</td><td>基于实时负载打分、拓扑分散打分</td></tr>
<tr><td class="q-dim">NormalizeScore</td><td>打分</td><td>Score 之后，归一化分数</td><td>将分数映射到统一范围</td></tr>
<tr><td class="q-dim">Reserve</td><td>预留</td><td>选中节点后，Bind 之前</td><td>预留 GPU 设备、标记资源已占用</td></tr>
<tr><td class="q-dim">Permit</td><td>许可</td><td>Reserve 之后，等待条件满足</td><td>Gang Scheduling 等待同组 Pod 凑齐</td></tr>
<tr><td class="q-dim">PreBind</td><td>绑定</td><td>Bind 之前，执行绑定前操作</td><td>挂载 Volume、分配 IP</td></tr>
<tr><td class="q-dim">Bind</td><td>绑定</td><td>将 Pod 绑定到节点</td><td>自定义绑定逻辑（极少需要）</td></tr>
<tr><td class="q-dim">PostBind</td><td>绑定</td><td>Bind 之后，通知型操作</td><td>记录调度事件、通知外部系统</td></tr>
<tr><td class="q-dim">Unreserve</td><td>回滚</td><td>Reserve 之后失败时</td><td>释放预留的 GPU 设备、清理临时状态</td></tr>
</tbody>
</table>
</div>
</div>

<div class="qa-section"><div class="qa-section-title">开发步骤（面试标准回答）</div>
<ol>
<li><strong>创建 Go 项目：</strong>初始化 Go module，引入 <code>k8s.io/kubernetes</code> 依赖（或使用 <code>scheduler-plugins</code> 仓库作为模板）。</li>
<li><strong>实现扩展点接口：</strong>根据需求选择实现 <code>FilterPlugin</code>、<code>ScorePlugin</code>、<code>ReservePlugin</code> 等接口。每个接口有固定的方法签名。</li>
<li><strong>实现 <code>Name()</code> 方法：</strong>返回插件名称，用于在配置文件中引用。</li>
<li><strong>注册插件：</strong>在 <code>main()</code> 中通过 <code>app.NewSchedulerCommand()</code> 注册自定义插件到 Framework。</li>
<li><strong>编译部署：</strong>编译为自定义 scheduler 二进制或镜像，替换默认 scheduler。</li>
<li><strong>配置启用：</strong>在 <code>KubeSchedulerConfiguration</code> 的 <code>profiles[].plugins</code> 中启用插件，必要时在 <code>pluginConfig</code> 中传入参数。</li>
</ol>
</div>

<div class="qa-section"><div class="qa-section-title">关键接口签名（面试要能写出）</div>
<p>以下是最常用的三个接口签名，面试中如果被问到"写过什么插件"，至少能写出 Filter 和 Score 的签名：</p>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:100px">接口</th><th>方法签名</th><th>返回值含义</th></tr>
</thead>
<tbody>
<tr><td class="q-dim">FilterPlugin</td><td><code>Filter(ctx, state, pod, nodeInfo) *Status</code></td><td><code>Success</code> 表示节点可用；<code>Unschedulable</code> 表示不可用</td></tr>
<tr><td class="q-dim">ScorePlugin</td><td><code>Score(ctx, state, pod, nodeName) (int64, *Status)</code></td><td>返回 0-100 的分数，分数越高越优先</td></tr>
<tr><td class="q-dim">ReservePlugin</td><td><code>Reserve(ctx, state, pod, nodeName) *Status</code></td><td><code>Success</code> 表示预留成功；失败会触发 Unreserve</td></tr>
</tbody>
</table>
</div>
<p>注意：<code>CycleState</code> 是单次调度周期内的临时状态存储，可以在 PreFilter 中写入数据，在 Filter/Score/Reserve 中读取，避免重复计算。</p>
</div>
</div>

<div class="card card-d">
<h3>典型示例：GPU 拓扑感知 Filter + Score 插件</h3>
<p>这是 AI Infra 面试中最常见的自定义插件场景。下面给出完整的实现思路和关键代码骨架。</p>

<div class="qa-section"><div class="qa-section-title">场景描述</div>
<p>集群中有多种 GPU 拓扑的节点（如 NVLink 互联的 8 卡节点、PCIe 互联的 4 卡节点）。训练任务需要 4 张 NVLink 互联的 GPU，不能分配到 PCIe 节点上，也不能分配到 NVLink 域不够 4 卡的节点上。</p>
</div>

<div class="qa-section"><div class="qa-section-title">实现思路</div>
<ol>
<li><strong>PreFilter：</strong>从 Pod annotation 中解析 GPU 拓扑需求（如 <code>gpu-topology: nvlink-4</code>），写入 CycleState。</li>
<li><strong>Filter：</strong>从 Node label 中读取 GPU 拓扑信息（如 <code>nvidia.com/gpu-topology: nvlink-8</code>），判断是否满足 Pod 需求。不满足则返回 <code>Unschedulable</code>。</li>
<li><strong>Score：</strong>对满足条件的节点，根据 NVLink 域剩余 GPU 数量打分：刚好满足需求（如剩余 4 卡域）给高分，碎片化严重的给低分。</li>
<li><strong>Reserve：</strong>在 scheduler cache 中标记具体哪些 GPU 被预留，防止后续 Pod 重复分配。</li>
</ol>
</div>

<div class="qa-section"><div class="qa-section-title">Filter 核心代码骨架</div>
<pre><code>func (p *GPUTopologyPlugin) Filter(
    ctx context.Context,
    state *framework.CycleState,
    pod *v1.Pod,
    nodeInfo *framework.NodeInfo,
) *framework.Status {
    // 1. 从 CycleState 读取 PreFilter 阶段解析的 GPU 需求
    data, err := state.Read(stateKeyGPURequirement)
    if err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }
    requirement := data.(*GPURequirement) // topology=nvlink, count=4

    // 2. 从 Node label 读取 GPU 拓扑信息
    node := nodeInfo.Node()
    topoLabel, ok := node.Labels["nvidia.com/gpu-topology"]
    if !ok {
        return framework.NewStatus(framework.Unschedulable, "node has no GPU topology label")
    }

    // 3. 判断拓扑是否匹配
    if topoLabel != requirement.Topology {
        return framework.NewStatus(framework.Unschedulable,
            fmt.Sprintf("GPU topology mismatch: need %s, got %s",
                requirement.Topology, topoLabel))
    }

    // 4. 检查可用 GPU 数量（从 nodeInfo 或 annotation 获取）
    availableGPUs := getAvailableGPUs(node, nodeInfo)
    if availableGPUs < requirement.Count {
        return framework.NewStatus(framework.Unschedulable,
            fmt.Sprintf("insufficient GPUs: need %d, available %d",
                requirement.Count, availableGPUs))
    }

    return framework.NewStatus(framework.Success)
}</code></pre>
</div>

<div class="qa-section"><div class="qa-section-title">Score 核心代码骨架</div>
<pre><code>func (p *GPUTopologyPlugin) Score(
    ctx context.Context,
    state *framework.CycleState,
    pod *v1.Pod,
    nodeName string,
) (int64, *framework.Status) {
    // 从 CycleState 读取 GPU 需求
    data, _ := state.Read(stateKeyGPURequirement)
    requirement := data.(*GPURequirement)

    // 获取该节点上剩余 GPU 的拓扑分布
    node := getNodeByName(nodeName)
    freeGPUDomains := getFreeNVLinkDomains(node)

    // 打分策略：刚好满足需求的域越多，分数越高
    // 避免把 Pod 放到"只剩最后一个 4 卡域"的节点上
    matchingDomains := 0
    for _, domain := range freeGPUDomains {
        if domain.FreeGPUs >= requirement.Count {
            matchingDomains++
        }
    }

    // 分数范围 0-100
    score := int64(matchingDomains * 25)
    if score > 100 {
        score = 100
    }
    return score, framework.NewStatus(framework.Success)
}</code></pre>
</div>

<div class="qa-section"><div class="qa-section-title">KubeSchedulerConfiguration 配置示例</div>
<pre><code>apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: gpu-scheduler
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
            weight: 10   # 权重越高，拓扑因素越重要
      reserve:
        enabled:
          - name: GPUTopology
    pluginConfig:
      - name: GPUTopology
        args:
          topologyTypes:
            - nvlink
            - pcie
          defaultCount: 1</code></pre>
</div>

<div class="qa-summary">面试表达结构：先说明"有三种实现方式，我选择 Framework Plugin 因为性能最好、能力最全" → 再讲"我实现了 PreFilter + Filter + Score + Reserve 四个扩展点" → 最后给出 Filter/Score 的核心逻辑和配置。如果能写出接口签名和关键代码骨架，会大幅加分。</div>
</div>

<div class="card card-m">
<h3>案例：感知共置干扰的预测调度插件</h3>
<p>面试官常追问的一个开放题："如果让你做一个预测调度器，能预测<strong>任务运行时间</strong>，又能预测<strong>多任务共置时的干扰程度</strong>，你怎么落到 Kubernetes Scheduler Framework 里？" 这道题考的是<strong>把预测结果变成调度决策的工程链路</strong>，不是模型本身。下面给出可以直接答的工程方案，关键在于讲清四件事：</p>
<ol>
<li><strong>预测值存在哪</strong>：模型不能跑在 scheduler 热路径上 → 必须有"在哪生产、在哪存储、scheduler 在哪读"的明确链路。</li>
<li><strong>QueueSort 在算什么</strong>：基于 Pod 上的哪个字段排序、为什么不能只按运行时间排。</li>
<li><strong>Filter 在过滤什么</strong>：节点级的预测值从哪来、什么场景返回 Unschedulable。</li>
<li><strong>干扰是怎么感知的</strong>：信号是 DCGM 还是 cgroup？是节点上报还是 scheduler 拉？</li>
</ol>
</div>

<div class="card card-s">
<h3>① 系统总览：训练在外、推理可选、读取必须本地</h3>
<p>scheduler 调度周期 P99 必须 &lt; 100ms，所以模型训练 / 推理一般都不能塞进 plugin。标准做法是<strong>三层数据流</strong>：</p>

<pre><code>[ 节点 ]                       [ 控制面 ]                          [ Scheduler 进程内 ]
 DCGM Exporter                 PredictorService (CRD controller)    Plugin (in-tree)
 ─ SM utilization              ─ 离线训练 runtime / interference     ─ Informer 监听 CRD / Pod annotation
 ─ HBM bandwidth               ─ 在线推理 (gRPC, 100ms 超时)          ─ 写入 Plugin local cache
 ─ NVLink/PCIe counters        ─ 把预测结果写回:                      ─ Filter/Score/QueueSort 仅查 cache
 ─ 进程级 GPU memory             • Pod annotation                     ─ μs 级延迟
                                 • 自定义 CRD: PredictionResult       ─ 模型不可用时 fallback 到默认值
                                 • Node annotation (节点画像)
</code></pre>

<table>
<tr><th>层</th><th>组件</th><th>职责</th><th>不做什么</th></tr>
<tr><td>数据采集层</td><td>每节点 DCGM Exporter + 自定义 collector</td><td>采集 SM 利用率、HBM 带宽、NVLink/PCIe 流量、显存 / 进程粒度 GPU memory</td><td>不做预测，只上报</td></tr>
<tr><td>预测控制面</td><td>独立 Deployment：<code>predictor-service</code></td><td>1) 从 Prometheus 拉历史 → 训练模型 2) gRPC 在线推理 3) 把结果回写到 Pod annotation 或 CRD</td><td>不在 scheduler 进程里跑模型；不影响调度延迟</td></tr>
<tr><td>调度热路径</td><td>scheduler plugin（编译进 kube-scheduler）</td><td>通过 Informer 监听 CRD / annotation，写本地 map；调度时只查 map，永不阻塞 RPC</td><td>绝对不在 Filter/Score 里调用 gRPC</td></tr>
</table>
<div class="qa-summary">关键边界：<strong>scheduler plugin 永远不调模型</strong>。预测结果就像 Pod 的 label/annotation 一样，是<strong>事先准备好的数据</strong>，plugin 只读不写。</div>
</div>

<div class="card card-d">
<h3>② 预测值落地：写在哪、读在哪</h3>
<p>这是面试里最容易被追问的细节。给出两个具体的数据落点：</p>

<h4>方案 A：用 Pod annotation（轻量、无需 CRD）</h4>

<pre><code>metadata:
  annotations:
    predictor.io/runtime-seconds: "3600"          # 预测运行时间
    predictor.io/runtime-confidence: "0.85"        # 置信度
    predictor.io/job-signature: "resnet50-bs256-fp16-v2"  # 用于查节点干扰画像
    predictor.io/interference-tolerance: "0.9"     # 这个任务能接受的最低 retention
</code></pre>

<p>predictor-service 在 Pod 进入 Pending 后 watch 到事件，给 Pod patch 这些 annotation。scheduler plugin 在 PreFilter 里读取。</p>

<h4>方案 B：自定义 CRD <code>PredictionResult</code>（适合复杂模型）</h4>

<pre><code>apiVersion: scheduling.predictor.io/v1
kind: PredictionResult
metadata:
  name: pod-resnet50-xxx
  namespace: train
spec:
  podRef: {name: resnet50-xxx, uid: 1234}
status:
  predictedRuntimeSeconds: 3600
  confidence: 0.85
  interferenceProfile:           # 和节点上常见 job-signature 共置时的预测 retention
    "bert-large":  {retention: 0.92, slowdown: 1.08}
    "gpt2-medium": {retention: 0.78, slowdown: 1.28}
    "llama-7b":    {retention: 0.55, slowdown: 1.81}
  nodeProfile:                   # 节点已有任务的干扰画像（可选: 节点级 CRD）
    nodeName: gpu-node-42
    coLocatedJobs: ["bert-large", "gpt2-medium"]
    aggregatedSlowdownIfAdd: 1.35
</code></pre>

<table>
<tr><th>选型</th><th>优势</th><th>劣势</th><th>典型场景</th></tr>
<tr><td>annotation</td><td>无需 CRD；scheduler 直接通过 PodInformer 拿到</td><td>大对象会污染 etcd；无法独立生命周期</td><td>简单运行时间预测</td></tr>
<tr><td>独立 CRD</td><td>结构化字段、可独立 Watch、可独立 GC</td><td>需要写 CRD controller、Informer</td><td>多模型组合 / 干扰矩阵</td></tr>
</table>
<div class="qa-summary">无论选哪种，<strong>plugin 的 Init 阶段都必须建立 Informer</strong>：annotation 走 SharedInformer 监听 Pod；CRD 走 Dynamic Informer 监听 PredictionResult。Filter/Score 时只从本地 store 读，绝不发起远程调用。</div>
</div>

<div class="card card-m">
<h3>③ 各扩展点职责（含代码骨架）</h3>

<h4>QueueSort：决定"先调谁"</h4>

<p>QueueSort 比较两个 Pod 的优先级，决定 ActiveQ 出队顺序。<strong>关键点：runtime 不是排序的最高维度</strong>，必须先看 PriorityClass 和租户公平性，否则会饿死长任务。</p>

<pre><code>func (pl *PredictivePlugin) Less(p1, p2 *framework.QueuedPodInfo) bool {
    // 1. 优先级：硬规则
    if *p1.Pod.Spec.Priority != *p2.Pod.Spec.Priority {
        return *p1.Pod.Spec.Priority &gt; *p2.Pod.Spec.Priority
    }
    // 2. 租户公平性：欠资源越多越优先（QAD = Quota Allocation Deviation）
    qad1 := pl.fairness.QAD(p1.Pod.Namespace)
    qad2 := pl.fairness.QAD(p2.Pod.Namespace)
    if qad1 != qad2 {
        return qad1 &gt; qad2
    }
    // 3. 预测运行时间：短任务优先（SJF），从 annotation 读
    rt1 := readPredictedRuntime(p1.Pod)  // 读 predictor.io/runtime-seconds
    rt2 := readPredictedRuntime(p2.Pod)
    if rt1 != rt2 {
        return rt1 &lt; rt2  // 短的先调
    }
    // 4. 提交时间：兜底
    return p1.Timestamp.Before(p2.Timestamp)
}
</code></pre>

<h4>PreFilter：把 Pod 侧预测值写入 CycleState（每周期算一次）</h4>

<pre><code>func (pl *PredictivePlugin) PreFilter(ctx context.Context, state *framework.CycleState,
    pod *v1.Pod) (*framework.PreFilterResult, *framework.Status) {

    pred := pl.predCache.Get(pod.UID)  // 从本地 Informer cache 读
    if pred == nil {
        // fallback：模型未就绪时给保守值
        pred = &amp;Prediction{Runtime: defaultRuntime, Tolerance: 1.0}
    }
    state.Write(stateKey, &amp;PodPredictionState{
        Runtime:        pred.Runtime,
        Tolerance:      pred.Tolerance,
        JobSignature:   pred.JobSignature,
        InterferenceProfile: pred.InterferenceProfile,
    })
    return nil, framework.NewStatus(framework.Success)
}
</code></pre>

<h4>Filter：硬约束 —— 节点上的共置预测干扰超过容忍线就拒绝</h4>

<p><strong>关键：Filter 不调模型</strong>。它从 CycleState（Pod 侧）+ NodeInfo（节点侧已有任务）查表算 retention。节点侧"已有哪些 job_signature"通过 NodeInfo.Pods 遍历得到。</p>

<pre><code>func (pl *PredictivePlugin) Filter(ctx context.Context, state *framework.CycleState,
    pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {

    s, _ := state.Read(stateKey)
    podPred := s.(*PodPredictionState)

    // 1. 收集该节点已有任务的 job-signature
    coLocatedSigs := make([]string, 0)
    for _, p := range nodeInfo.Pods {
        if sig := p.Pod.Annotations["predictor.io/job-signature"]; sig != "" {
            coLocatedSigs = append(coLocatedSigs, sig)
        }
    }

    // 2. 查表：本任务和这些已有任务共置后的 retention
    //    InterferenceProfile 是预测控制面提前算好写入 Pod 的二元矩阵
    minRetention := 1.0
    for _, sig := range coLocatedSigs {
        if entry, ok := podPred.InterferenceProfile[sig]; ok {
            if entry.Retention &lt; minRetention {
                minRetention = entry.Retention
            }
        }
    }

    // 3. 硬阈值判断
    if minRetention &lt; podPred.Tolerance {
        return framework.NewStatus(framework.Unschedulable,
            fmt.Sprintf("predicted retention %.2f &lt; tolerance %.2f on node %s",
                minRetention, podPred.Tolerance, nodeInfo.Node().Name))
    }
    return nil
}
</code></pre>

<h4>PreScore + Score：在可行节点里挑最优</h4>

<p>PreScore 把候选节点的实时 GPU counters（DCGM exporter 通过 Node annotation 或独立 NodeMetric CRD 暴露）批量加载到 CycleState；Score 查表算分。</p>

<pre><code>func (pl *PredictivePlugin) Score(ctx context.Context, state *framework.CycleState,
    pod *v1.Pod, nodeName string) (int64, *framework.Status) {

    podPred := readPodState(state)
    nodeFeat := pl.nodeCache.Get(nodeName)  // 来自 NodeMetric CRD / DCGM annotation

    // 综合三个信号：干扰小 / 装箱紧凑 / 拓扑亲和
    interferenceScore := 100 - int64((1.0 - nodeFeat.AvgRetention) * 100)
    binPackScore     := int64(nodeFeat.GPUUtilization * 100)  // MostAllocated 风格
    topoScore        := pl.topology.Score(pod, nodeName)

    final := interferenceScore*5 + binPackScore*2 + topoScore*3  // 权重可配置
    return final, nil
}
</code></pre>

<h4>Reserve / Unreserve：维护共置账本</h4>

<p>scheduler 内置 cache 只跟踪整数资源（cpu/memory/extended）。MIG slot、MPS share、共置 job-signature 集合这些<strong>插件特有的状态</strong>必须在 Reserve 时落入插件自己的账本（map nodeName → set&lt;jobSignature&gt;），Bind 失败由 Unreserve 回滚。</p>

<pre><code>func (pl *PredictivePlugin) Reserve(ctx context.Context, state *framework.CycleState,
    pod *v1.Pod, nodeName string) *framework.Status {
    pl.ledger.Add(nodeName, pod.UID, podJobSignature(pod))
    return nil
}

func (pl *PredictivePlugin) Unreserve(ctx context.Context, state *framework.CycleState,
    pod *v1.Pod, nodeName string) {
    pl.ledger.Remove(nodeName, pod.UID)
}
</code></pre>
</div>

<div class="card card-d">
<h3>④ 干扰信号怎么感知（端到端链路）</h3>

<pre><code>[ Pod 进程 ]
  └─ NVIDIA driver / cgroup
        ↓ DCGM 采样 (1s 粒度)
[ Node ] DCGM Exporter (DaemonSet)
  └─ 暴露 metric: dcgm_sm_active, dcgm_fb_used, dcgm_pcie_tx_bytes ...
        ↓ Prometheus scrape
[ Cluster ] Prometheus / VictoriaMetrics
        ↓ predictor-service 拉数据
[ Predictor ] 训练干扰矩阵 InterferenceProfile[sig_a][sig_b] = retention
        ↓ 写回 Pod annotation 或 PredictionResult CRD
[ Scheduler ] Plugin Informer 监听 → 本地 cache → Filter/Score 查表
</code></pre>

<table>
<tr><th>层</th><th>信号来源</th><th>典型字段</th><th>采样频率</th></tr>
<tr><td>硬件/驱动</td><td>NVIDIA DCGM</td><td>SM activity、HBM 带宽、PCIe Tx/Rx、NVLink utilization、显存占用</td><td>每秒</td></tr>
<tr><td>cgroup / 容器</td><td>kubelet cAdvisor</td><td>每容器 CPU、内存、IO（不含 GPU 内部细节）</td><td>每 10 秒</td></tr>
<tr><td>应用</td><td>训练框架自带 metric（如 step time、tokens/s）</td><td>实际 throughput、step latency</td><td>每 step</td></tr>
<tr><td>聚合</td><td>Prometheus + recording rules</td><td>按 namespace × job-signature 聚合的平均 SM、retention</td><td>每分钟</td></tr>
</table>

<p><strong>"干扰画像"如何形成：</strong>predictor-service 离线扫历史 Prometheus，找出"任务 A 单跑 throughput vs 任务 A 与 B 共置时 throughput"，比值就是 retention。把所有 (sig_a, sig_b) 对存成矩阵，新任务进来时查这个矩阵就能预测它在某个节点上的干扰。</p>

<div class="qa-summary">面试要点：干扰**不是 scheduler 实时测的**，而是**离线训练 + 在线查表**。scheduler 看到的永远是预先算好的数字，调度路径上没有任何 GPU profiling 调用。</div>
</div>

<div class="card card-w">
<h3>⑤ 30 秒 / 2 分钟 / 追问应答</h3>

<h4>30 秒</h4>
<p>预测调度器拆三层：节点 DCGM 采集 → 控制面 predictor-service 训练并把结果写回 Pod annotation 或 PredictionResult CRD → scheduler plugin 通过 Informer 缓存到本地。<strong>QueueSort</strong> 按 priority &gt; 租户公平性 &gt; 预测运行时间排序；<strong>PreFilter</strong> 把 Pod 预测值写入 CycleState；<strong>Filter</strong> 用"本任务 vs 节点已有任务"的预测 retention 卡硬阈值；<strong>PreScore + Score</strong> 综合干扰、装箱、拓扑打分；<strong>Reserve/Unreserve</strong> 维护 MIG/MPS/共置账本。模型推理永远不在调度热路径里跑。</p>

<h4>2 分钟</h4>
<p>整个系统三层：(1) 每个节点跑 DCGM Exporter 把 SM、HBM、PCIe 等 GPU counter 暴露给 Prometheus；(2) predictor-service（独立 Deployment）做两件事：从 Prometheus 拉历史训练 runtime / interference 模型，再用 gRPC 在线推理把预测结果写回 Pod annotation 或自定义 PredictionResult CRD；(3) scheduler plugin 在 Init 时建立 Informer 监听这些 annotation/CRD，把结果缓存到内存 map，调度路径上只查 map。</p>
<p>QueueSort 决定"先调谁"，但短任务优先不能压过 priority 和租户公平性，所以排序是"priority &gt; QAD &gt; predicted runtime &gt; submitTime"。PreFilter 从本地 cache 读出 Pod 的 predicted runtime、tolerance、interference profile 写入 CycleState。Filter 遍历节点上的已有 Pod 拿 job-signature，从 InterferenceProfile 里查到 retention，低于 tolerance 就返回 Unschedulable —— 注意这里是查表，不是调模型。PreScore 加载节点 GPU counters（来自 NodeMetric CRD），Score 综合 interference / bin packing / topology 打分。Reserve 把这次调度结果加入插件自己维护的"node → job-signature 集合"账本，下个 Pod 的 Filter 才能读到正确的"已有任务"。Bind 失败用 Unreserve 回滚。</p>
<p>干扰感知是离线训练 + 在线查表的混合：predictor-service 扫描历史 Prometheus 算出 (sig_a, sig_b) → retention 矩阵；调度时根据节点上已有任务的 sig 直接查矩阵。任务结束后 PostBind 触发样本回收 controller 把实际 runtime 和 throughput 写回训练集，闭环校准。</p>

<h4>面试官可能追问</h4>
<table>
<tr><th>追问</th><th>回答抓手</th></tr>
<tr><td>为什么不在 Filter 里直接 gRPC 调模型？</td><td>Filter 是节点级并行热路径，5000 节点会被放大成 5000 次 RPC；scheduler 周期 P99 必须 &lt; 100ms。所以模型推理一律提前在 predictor-service 里完成、写回 annotation/CRD，plugin 只查表。</td></tr>
<tr><td>预测不准怎么办？</td><td>三道防线：① tolerance 字段设安全 margin（默认 0.9） ② 在 PostBind 后用 NodeProblemDetector 监控真实 retention，超阈值触发驱逐 ③ predictor 训练集闭环（PostBind 收 runtime、controller 收 throughput）。</td></tr>
<tr><td>新任务（cold start）没有预测怎么办？</td><td>plugin 在 PreFilter 用 fallback：runtime 用 namespace 历史中位数；interference 假设 retention=1.0（最保守，等价于不加权重）。同时 predictor-service 在 Pod 跑起来 5 分钟后用 online inference 反写。</td></tr>
<tr><td>InterferenceProfile 矩阵会不会太大？</td><td>job-signature 是聚类后的标签（resnet50-bs256-fp16），生产里一般几百个；矩阵 O(n²) 也只有几万项；只在 predictor-service 全量保存，写回 Pod 时只挑当前节点上存在的 sig。</td></tr>
<tr><td>怎么证明这个插件有效？</td><td>核心指标四组：① 调度延迟（plugin_execution_duration P99 &lt; 10ms） ② JCT / queue waiting time 同比下降 ③ 集群 GPU 利用率上升、SLO violation 不上升 ④ ablation：分别关掉 runtime SJF、interference Filter、interference Score 看回退。</td></tr>
</table>
<div class="qa-summary">收束：<strong>运行时间预测决定"先调谁"（QueueSort），共置干扰预测决定"能不能放 + 放哪里"（Filter + Score）；预测一律在 scheduler 外算好写回 Pod/CRD，plugin 通过 Informer 缓存只读不算。Reserve/Unreserve 维护插件特有的共置账本。</strong></div>
</div>

## 面试回答

**30 秒版：**

自定义调度逻辑优先用 Scheduling Framework Plugin，复杂系统再考虑 extender 或独立 scheduler。基础例子可以讲 GPU 拓扑感知 Filter/Score；如果面试官追问预测调度器，就把运行时间预测放到 QueueSort，把共置干扰预测放到 PreScore / Filter / Score，把资源账本放到 Reserve / Unreserve。

**2 分钟版：**

我会先说明自定义调度逻辑有 Framework Plugin、Extender 和独立 Scheduler 三种方式。AI Infra 里的 GPU 拓扑、预测调度、共置干扰判断都在 scheduler 热路径上，所以优先选 Framework Plugin。普通拓扑感知插件可以实现 PreFilter / Filter / Score / Reserve；预测调度器则进一步把运行时间预测用于 QueueSort 和抢占成本，把共置干扰预测用于 Filter 的硬阈值和 Score 的软打分。模型训练、样本回收和在线校准放在 scheduler 外部，plugin 通过本地 cache 或 annotation 读取结果，避免拖慢调度周期。最后用 Reserve / Unreserve 保证 GPU 共置账本和 scheduler assumed state 一致，并用 plugin latency、JCT、GPU 利用率、SLO violation 和实际 slowdown 验证效果。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
