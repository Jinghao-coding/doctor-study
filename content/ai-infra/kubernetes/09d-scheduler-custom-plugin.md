<div class="card card-m">
<h3>自定义 Scheduler Plugin 实战</h3>
<p>自定义调度逻辑可以运行在 kube-scheduler 进程内、进程外 Extender，或独立 scheduler 中。三种方式能接入的生命周期、状态视图和故障边界不同。</p>
</div>

<div class="card card-s">
<h3>三种实现自定义调度逻辑的方式</h3>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:140px">方式</th><th>原理</th><th>优点</th><th>缺点</th><th>适用场景</th></tr>
</thead>
<tbody>
<tr><td class="q-dim">Scheduling Framework Plugin<br>（进程内）</td><td>实现 Framework 扩展点接口，并编译进自定义 kube-scheduler 二进制</td><td>性能最好，直接使用 FrameworkHandle、Lister 和 NodeInfo；可以接入完整生命周期（QueueSort 到 PostBind）</td><td>不是运行时动态加载；需要维护自定义镜像，并跟随 Kubernetes 版本适配内部接口</td><td>性能敏感的调度逻辑（GPU 拓扑、NUMA、Gang）；需要访问 scheduler 状态或参与 Reserve/Permit</td></tr>
<tr><td class="q-dim">Scheduler Extender<br>(Out-of-tree HTTP)</td><td>独立 HTTP 服务，scheduler 通过 HTTP 调用 Filter / Prioritize / Bind 等接口</td><td>独立部署，不侵入 scheduler 代码；可以用任意语言开发</td><td>HTTP 调用延迟高（ms 级）；无法访问 scheduler cache；只能参与 Filter / Score / Bind 等有限阶段</td><td>简单过滤逻辑（如特殊 label 过滤）；非性能敏感的定制需求；多语言团队</td></tr>
<tr><td class="q-dim">Multiple Scheduler<br>(独立 Scheduler)</td><td>部署另一个完整的 scheduler 实例，Pod 通过 <code>schedulerName</code> 指定</td><td>完全独立，策略隔离；可以用不同版本的 scheduler</td><td>不同 scheduler 之间不共享 cache，可能产生资源竞争；运维复杂（需要维护两套 scheduler）</td><td>业务强隔离（GPU 任务 vs CPU 任务）；需要完全不同的调度策略</td></tr>
</tbody>
</table>
</div>
<div class="qa-summary">三种方式的本质差异是调度逻辑运行位置和可参与的生命周期。需要 Cache、CycleState、Reserve/Permit 时使用进程内 Plugin；只做有限的远端过滤/打分且能接受网络故障时才考虑 Extender；策略与运维边界都必须隔离时再运行独立 Scheduler。</div>
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
<tr><td class="q-dim">PreBind</td><td>绑定</td><td>Bind 之前，执行必须先于绑定完成的准备</td><td>例如 VolumeBinding 完成 PVC 绑定；不负责 kubelet 侧 CNI 配网</td></tr>
<tr><td class="q-dim">Bind</td><td>绑定</td><td>将 Pod 绑定到节点</td><td>自定义绑定逻辑（极少需要）</td></tr>
<tr><td class="q-dim">PostBind</td><td>绑定</td><td>Bind 之后，通知型操作</td><td>记录调度事件、通知外部系统</td></tr>
<tr><td class="q-dim">Unreserve</td><td>回滚</td><td>Reserve 之后失败时</td><td>释放预留的 GPU 设备、清理临时状态</td></tr>
</tbody>
</table>
</div>
</div>

<div class="qa-section"><div class="qa-section-title">开发、注册与启用</div>
<ol>
<li><strong>固定版本：</strong>插件会编译进 scheduler 进程，并依赖 Kubernetes Scheduler Framework 接口；插件依赖、构建源码和目标集群版本必须配套。</li>
<li><strong>实现扩展点接口：</strong>根据需求选择实现 <code>FilterPlugin</code>、<code>ScorePlugin</code>、<code>ReservePlugin</code> 等接口。每个接口有固定的方法签名。</li>
<li><strong>实现工厂函数：</strong>构造函数接收 runtime 配置和 <code>framework.Handle</code>，解析参数并创建插件实例；<code>Name()</code> 返回配置中引用的稳定名称。</li>
<li><strong>注册插件：</strong>自定义 scheduler 的 <code>main()</code> 调用 <code>app.NewSchedulerCommand(app.WithPlugin(name, factory))</code>，把工厂加入 Registry。</li>
<li><strong>编译部署：</strong>编译自定义 scheduler 二进制和镜像；不能只把一个 <code>.so</code> 或配置文件挂进官方镜像就完成动态加载。</li>
<li><strong>配置启用：</strong>在 <code>KubeSchedulerConfiguration</code> 的 <code>profiles[].plugins</code> 中启用插件，必要时在 <code>pluginConfig</code> 中传入参数。</li>
</ol>
<pre><code class="language-go">package main

import (
    "os"

    "k8s.io/component-base/cli"
    "k8s.io/kubernetes/cmd/kube-scheduler/app"
    "example.com/scheduler/pkg/myplugin"
)

func main() {
    cmd := app.NewSchedulerCommand(
        app.WithPlugin(myplugin.Name, myplugin.New),
    )
    os.Exit(cli.Run(cmd))
}</code></pre>
<pre><code class="language-yaml">apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: gpu-scheduler
  plugins:
    filter:
      enabled:
      - name: MyGPUPlugin
    score:
      enabled:
      - name: MyGPUPlugin
        weight: 5
  pluginConfig:
  - name: MyGPUPlugin
    args:
      maxMetricAgeSeconds: 15</code></pre>
<p>Pod 只有在 <code>spec.schedulerName: gpu-scheduler</code> 时才会选择这个 Profile。部署后还应检查启动日志中的插件 Registry/Profile、配置版本、RBAC 和 leader election，而不是只确认进程存活。</p>
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
<li><strong>Reserve：</strong>在插件账本中记录所选 Node 的逻辑 GPU 拓扑名额，防止 Bind 完成前被后续调度周期重复使用。普通 <code>nvidia.com/gpu</code> 的具体 device ID 仍由节点侧 Device Plugin / kubelet Allocate 路径决定。</li>
</ol>
</div>

<div class="qa-section"><div class="qa-section-title">Filter 核心代码骨架</div>
<pre><code class="language-go">func (p *GPUTopologyPlugin) Filter(
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
<pre><code class="language-go">func (p *GPUTopologyPlugin) Score(
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
<pre><code class="language-yaml">apiVersion: kubescheduler.config.k8s.io/v1
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
<h3>案例：AIJob 驱动的预测调度插件</h3>
<p>面试官常追问："如果让你做一个预测调度器，既预测任务运行时间，又预测多个任务共置时的干扰程度，你怎么落到 Kubernetes Scheduler Framework 里？" 推荐统一回答成 <strong>AIJob CRD + AIJob Operator + Scheduler Plugin</strong> 三层架构：AIJob 表达深度学习任务，AIJob Operator 管生命周期和预测子控制器，scheduler plugin 只读辅助 CRD。</p>
<table>
<tr><th>层次</th><th>组件</th><th>职责</th><th>边界</th></tr>
<tr><td>任务表达层</td><td><code>AIJob</code> CRD</td><td>表达模型、batch size、replica、GPU 需求、checkpoint、共置容忍度</td><td>不直接做节点选择</td></tr>
<tr><td>节点采集层</td><td>DCGM Exporter / Node GPU Collector</td><td>采集 SM、HBM、PCIe/NVLink、显存、进程级 GPU memory、训练 step time</td><td>只采集和暴露指标，不做调度决策</td></tr>
<tr><td>任务控制面</td><td>AIJob Operator</td><td>创建 PodGroup / Pods，维护任务状态，并通过预测子控制器写 <code>PredictionResult</code> 与 <code>NodeGpuProfile</code></td><td>不在 scheduler 进程内运行模型</td></tr>
<tr><td>调度热路径</td><td>Predictive Scheduler Plugin</td><td>通过 Informer 本地缓存 CRD，在 QueueSort / Filter / Score / Reserve 中查表决策</td><td>Filter / Score 绝不发 RPC，不拉 Prometheus</td></tr>
</table>
<div class="qa-summary">核心边界：AIJob Operator 负责"任务生命周期 + 预测状态生产"；scheduler plugin 负责"读取预测状态并做放置决策"。</div>
</div>

<div class="card card-s">
<h3>① 控制面数据流：统一走 CRD</h3>
<p>这条链路避免了大对象写入 Pod annotation，也让预测结果有独立生命周期、状态、GC 和权限控制。</p>
<table>
<tr><th>步骤</th><th>动作</th><th>产物</th></tr>
<tr><td>1. 提交任务</td><td>用户提交 <code>AIJob</code>，声明模型、GPU、replica、checkpoint、共置容忍度</td><td>AIJob 对象</td></tr>
<tr><td>2. 采集</td><td>节点侧 DCGM Exporter 暴露 GPU counter，训练框架暴露 throughput / step time</td><td>Prometheus / TSDB 中的历史样本</td></tr>
<tr><td>3. 建模</td><td>AIJob Operator 的预测子控制器周期训练 runtime 模型和共置 retention 矩阵</td><td>模型文件、特征版本、job-signature 聚类</td></tr>
<tr><td>4. 写 CRD</td><td>AIJob Operator 为 AIJob 写 <code>PredictionResult</code>，为节点写 <code>NodeGpuProfile</code></td><td>结构化预测状态</td></tr>
<tr><td>5. 本地缓存</td><td>Scheduler Plugin 在初始化时建立 Informer</td><td><code>jobUID → PredictionResult</code>、<code>nodeName → NodeGpuProfile</code></td></tr>
<tr><td>6. 调度决策</td><td>QueueSort / PreFilter / Filter / Score / Reserve 只查本地 map</td><td>微秒级读路径</td></tr>
</table>
</div>

<div class="card card-d">
<h3>② CRD 设计：AIJob、PredictionResult 与 NodeGpuProfile</h3>
<pre><code class="language-yaml">apiVersion: scheduling.predictor.io/v1
kind: AIJob
metadata:
  name: resnet50-train
  namespace: train
spec:
  framework: pytorch
  replicas:
    workers: 8
  resources:
    gpu:
      count: 8
      type: A100
  workload:
    model: resnet50
    batchSize: 256
    precision: fp16
  scheduling:
    queue: research
    minAvailable: 8
    allowColocation: true
    minRetention: 0.90
  checkpoint:
    enabled: true
    intervalSeconds: 600
status:
  phase: Pending
  predictionRef:
    name: pred-resnet50-train</code></pre>

<pre><code class="language-yaml">apiVersion: scheduling.predictor.io/v1
kind: PredictionResult
metadata:
  name: pred-resnet50-train
  namespace: train
spec:
  jobRef:
    kind: AIJob
    name: resnet50-train
    uid: "aijob-uid-1234"
status:
  jobSignature: "resnet50-bs256-fp16"
  predictedRuntimeSeconds: 3600
  confidence: 0.86
  minRetention: 0.90
  interferenceProfile:
    bert-large:
      retention: 0.92
      slowdown: 1.08
    gpt2-medium:
      retention: 0.78
      slowdown: 1.28</code></pre>

<pre><code class="language-yaml">apiVersion: scheduling.predictor.io/v1
kind: NodeGpuProfile
metadata:
  name: gpu-node-42
status:
  nodeName: gpu-node-42
  gpuUtilization: 0.62
  hbmBandwidthUtilization: 0.48
  colocatedJobSignatures:
    - bert-large
    - gpt2-medium
  avgRetentionIfAdd: 0.84
  updatedAt: "2026-06-15T15:00:00Z"</code></pre>

<table>
<tr><th>对象</th><th>谁写</th><th>谁读</th><th>生命周期</th></tr>
<tr><td><code>AIJob</code></td><td>用户 / 平台</td><td>AIJob Operator、Scheduler Plugin</td><td>训练任务生命周期</td></tr>
<tr><td><code>PredictionResult</code></td><td>AIJob Operator 的预测子控制器</td><td>Scheduler Plugin</td><td>跟随 AIJob 创建和删除，可 ownerReference 绑定 AIJob</td></tr>
<tr><td><code>NodeGpuProfile</code></td><td>AIJob Operator / Node collector controller</td><td>Scheduler Plugin</td><td>跟随 Node，周期更新状态</td></tr>
</table>
</div>

<div class="card card-m">
<h3>③ PredictionResult 的生命周期与消费路径</h3>
<p><code>PredictionResult</code> 不是用户手写的主资源，而是 AIJob Operator 为调度器准备的辅助状态。它的核心作用是把“深度学习任务画像”转换成 scheduler plugin 能低延迟读取的结构化字段。</p>
<table>
<tr><th>阶段</th><th>什么时候发生</th><th>谁做</th><th>结果怎么被感知</th></tr>
<tr><td>创建</td><td>AIJob 创建后，Operator 第一次 Reconcile，解析 spec 中的模型、batch size、GPU、replica、checkpoint、共置容忍度</td><td>AIJob Operator 的预测子控制器</td><td>创建 <code>PredictionResult</code>，并把 <code>AIJob.status.predictionRef</code> 指过去</td></tr>
<tr><td>初始预测</td><td>AIJob 还没运行时，基于历史任务、模型画像和资源请求估计 runtime / retention</td><td>预测子控制器</td><td>更新 <code>PredictionResult.status</code>，scheduler plugin 的 Informer 收到 update</td></tr>
<tr><td>调度消费</td><td>Pod 进入调度队列并执行 QueueSort / PreFilter / Filter / Score</td><td>Scheduler Plugin</td><td>从本地 cache 按 <code>jobUID</code> 读取，不访问 API Server，不调模型</td></tr>
<tr><td>运行中校准</td><td>Pod 绑定后，训练框架上报 step time，DCGM 上报 GPU counters</td><td>AIJob Operator / metric collector</td><td>异步修正 <code>PredictionResult.status.confidence</code>、runtime 或 retention</td></tr>
<tr><td>完成回收</td><td>AIJob Succeeded / Failed / Deleted</td><td>AIJob Operator</td><td>把真实 runtime / throughput 写入训练样本；通过 ownerReference GC PredictionResult</td></tr>
</table>

<div class="qa-section"><div class="qa-section-title">用户怎么使用它</div>
<p>用户通常不直接创建 <code>PredictionResult</code>，只提交 <code>AIJob</code>。如果要排查，可以通过 <code>kubectl get/describe predictionresult</code> 看预测运行时间、置信度、共置风险和更新时间。它更像 PVC 的绑定状态：用户关心结果，但不手写细节。</p>
</div>

<div class="qa-section"><div class="qa-section-title">调度器怎么使用它</div>
<p>Scheduler Plugin 在初始化时建立 Informer，把 <code>PredictionResult</code> 放进本地索引，例如 <code>jobUID → PredictionResult</code>。调度时从 Pod ownerReference / label 找到所属 AIJob，再查本地 cache。这样 QueueSort / Filter / Score 都是内存读取，不会阻塞调度周期。</p>
</div>

<pre><code class="language-go">func (r *AIJobReconciler) reconcilePrediction(ctx context.Context, job *aiv1.AIJob) error {
    // 1. 从 AIJob spec 提取任务画像：模型、batch size、GPU、replica、checkpoint。
    features := buildFeatures(job.Spec)

    // 2. 调用预测模块；这是控制面异步逻辑，不在 scheduler 热路径。
    pred := r.predictor.Predict(ctx, features)

    // 3. Upsert PredictionResult，并通过 ownerReference 绑定 AIJob 生命周期。
    result := buildPredictionResult(job, pred)
    if err := controllerutil.SetControllerReference(job, result, r.Scheme); err != nil {
        return err
    }
    return r.Client.Status().Update(ctx, result)
}</code></pre>

<div class="qa-summary">PredictionResult 在 AIJob 创建后的 Reconcile 中产生，运行中异步校准；用户用它排查预测状态，scheduler plugin 用它做本地查表决策。</div>
</div>

<div class="card card-w">
<h3>外部指标与预测服务不能成为调度热路径依赖</h3>
<p>Scheduling Cycle 对 Pod 串行推进。Filter/Score 虽然能并行处理 Node，但任何同步 DCGM 查询、Prometheus 查询或预测 RPC 都会把网络尾延迟、限流和故障传播到整个调度主循环；如果在每个 Node 的 Filter/Score 中调用一次，还会把请求量放大为“Pod 数 × Node 数”。</p>
<table>
<tr><th>风险</th><th>控制方式</th><th>降级语义</th></tr>
<tr><td>RPC 慢、超时或服务不可用</td><td>Operator/collector 异步计算并写 CRD；Plugin 只读 Informer 本地缓存</td><td>按配置选择保守拒绝、回退默认分或进入可重试 Error，不能临时随机决定</td></tr>
<tr><td>指标陈旧或抖动</td><td>状态携带 <code>observedAt</code>、模型版本、confidence 和 TTL；使用滑动窗口与安全余量</td><td>超过最大年龄后不把旧值当实时事实，低置信度禁止高风险共置</td></tr>
<tr><td>缓存尚未同步</td><td>启动时等待 Informer <code>HasSynced</code>；缺失数据使用明确的 Status reason</td><td>避免把“未同步”误判为“节点满足条件”</td></tr>
<tr><td>插件锁竞争或计算过重</td><td>不可变快照、读多写少索引、PreFilter/PreScore 预计算、限制候选节点</td><td>超预算时回退简单策略，并通过指标暴露降级次数</td></tr>
<tr><td>模型判断错误</td><td>运行期用 DCGM/step time 对账，设置 SLO 阈值和解除共置动作</td><td>调度决策可重算，但已绑定 Pod 不会被 Score 自动迁移，需要 Controller 执行后续处置</td></tr>
</table>
<p>若确实必须远程调用，应使用严格的 context deadline、连接池、熔断、并发上限和结果缓存，并把调用次数控制在每个 scheduling cycle 一次，而不是每个候选 Node 一次。即使如此，它仍会降低可用性，异步物化状态通常更稳妥。</p>
</div>

<div class="card card-m">
<h3>④ 各扩展点职责与 Go 骨架</h3>
<p>下面代码只展示关键路径。真实实现中还需要错误处理、metrics、并发保护、feature gate 和配置化权重。</p>

<h4>QueueSort：预测运行时间只做第三排序键</h4>
<pre><code class="language-go">func (pl *PredictivePlugin) Less(p1, p2 *framework.QueuedPodInfo) bool {
    // 1. PriorityClass 仍然是第一优先级，避免预测策略破坏 K8s 语义。
    if *p1.Pod.Spec.Priority != *p2.Pod.Spec.Priority {
        return *p1.Pod.Spec.Priority &gt; *p2.Pod.Spec.Priority
    }

    // 2. 租户公平性第二优先级，QAD 越低表示越需要补偿资源。
    qad1 := pl.fairness.QAD(p1.Pod.Namespace)
    qad2 := pl.fairness.QAD(p2.Pod.Namespace)
    if qad1 != qad2 {
        return qad1 &lt; qad2
    }

    // 3. 运行时间预测来自 AIJob 对应的 PredictionResult，本地 cache 读取。
    rt1 := pl.predStore.RuntimeSeconds(jobUID(p1.Pod))
    rt2 := pl.predStore.RuntimeSeconds(jobUID(p2.Pod))
    if rt1 != rt2 {
        return rt1 &lt; rt2
    }

    // 4. 最后用入队时间打破平局，避免不稳定排序。
    return p1.Timestamp.Before(p2.Timestamp)
}</code></pre>

<h4>PreFilter：把 CRD 预测值写入 CycleState</h4>
<pre><code class="language-go">func (pl *PredictivePlugin) PreFilter(
    ctx context.Context,
    state *framework.CycleState,
    pod *v1.Pod,
) (*framework.PreFilterResult, *framework.Status) {
    pred := pl.predStore.GetByJobUID(jobUID(pod))
    if pred == nil {
        // 冷启动兜底：AIJob 还没有 PredictionResult 时走保守策略。
        pred = conservativePrediction(pod)
    }

    // CycleState 只在本次 scheduling cycle 内有效，避免后续阶段重复查 CRD cache。
    state.Write(stateKeyPrediction, &amp;PodPredictionState{
        RuntimeSeconds:      pred.RuntimeSeconds,
        JobSignature:        pred.JobSignature,
        MinRetention:        pred.MinRetention,
        InterferenceProfile: pred.InterferenceProfile,
    })
    return nil, framework.NewStatus(framework.Success)
}</code></pre>

<h4>Filter：共置干扰超过阈值就拒绝节点</h4>
<pre><code class="language-go">func (pl *PredictivePlugin) Filter(
    ctx context.Context,
    state *framework.CycleState,
    pod *v1.Pod,
    nodeInfo *framework.NodeInfo,
) *framework.Status {
    pred := readPredictionState(state)
    nodeName := nodeInfo.Node().Name
    nodeProfile := pl.nodeProfileStore.Get(nodeName)

    // 节点画像缺失时走保守策略：Guaranteed 任务拒绝共置，BestEffort 可降级打分。
    if nodeProfile == nil &amp;&amp; isGuaranteed(pod) {
        return framework.NewStatus(framework.Unschedulable, "missing NodeGpuProfile")
    }

    retention := minPredictedRetention(pred, nodeProfile.ColocatedJobSignatures)
    if retention &lt; pred.MinRetention {
        return framework.NewStatus(
            framework.Unschedulable,
            fmt.Sprintf("predicted retention %.2f below threshold %.2f", retention, pred.MinRetention),
        )
    }
    return framework.NewStatus(framework.Success)
}</code></pre>

<h4>Score：在可行节点里选择更低干扰、更好装箱的节点</h4>
<pre><code class="language-go">func (pl *PredictivePlugin) Score(
    ctx context.Context,
    state *framework.CycleState,
    pod *v1.Pod,
    nodeName string,
) (int64, *framework.Status) {
    pred := readPredictionState(state)
    nodeProfile := pl.nodeProfileStore.Get(nodeName)

    // interferenceScore 越高表示共置越安全。
    retention := minPredictedRetention(pred, nodeProfile.ColocatedJobSignatures)
    interferenceScore := int64(retention * 100)

    // MostAllocated 风格：优先填补已有 GPU 利用率较高但仍安全的节点。
    binPackScore := int64(nodeProfile.GPUUtilization * 100)
    topologyScore := pl.topology.Score(pod, nodeName)

    score := interferenceScore*5 + binPackScore*2 + topologyScore*3
    return normalize(score), framework.NewStatus(framework.Success)
}</code></pre>

<h4>Reserve / Unreserve：维护插件自己的共置账本</h4>
<pre><code class="language-go">func (pl *PredictivePlugin) Reserve(
    ctx context.Context,
    state *framework.CycleState,
    pod *v1.Pod,
    nodeName string,
) *framework.Status {
    pred := readPredictionState(state)
    // scheduler cache 只知道整数资源；共置 signature 账本由插件自己维护。
    pl.ledger.Add(nodeName, pod.UID, pred.JobSignature)
    return framework.NewStatus(framework.Success)
}

func (pl *PredictivePlugin) Unreserve(
    ctx context.Context,
    state *framework.CycleState,
    pod *v1.Pod,
    nodeName string,
) {
    // Bind / Permit / PreBind 失败时必须回滚，避免后续 Pod 看到假的共置状态。
    pl.ledger.Remove(nodeName, pod.UID)
}</code></pre>
</div>

<div class="card card-d">
<h3>⑤ 干扰信号怎么形成闭环</h3>
<table>
<tr><th>阶段</th><th>输入</th><th>输出</th><th>为什么不放在 scheduler 内</th></tr>
<tr><td>单跑画像</td><td>任务单独运行时的 throughput、step time、GPU counters</td><td>job-signature 的 baseline</td><td>需要历史窗口和聚合计算</td></tr>
<tr><td>共置画像</td><td>两个 job-signature 共置时的 throughput 变化</td><td>retention / slowdown 矩阵</td><td>需要离线统计和异常值清洗</td></tr>
<tr><td>在线更新</td><td>Pod 绑定后的真实 runtime、实际 retention、驱逐事件</td><td>更新 PredictionResult / 训练样本</td><td>异步闭环，不能阻塞调度</td></tr>
<tr><td>调度使用</td><td>本地 Informer cache 中的 CRD 状态</td><td>QueueSort / Filter / Score 决策</td><td>热路径只查内存，保证 P99</td></tr>
</table>
<div class="qa-summary">面试要点：干扰不是 scheduler 实时测的，而是 Operator 用历史和在线反馈维护 CRD；scheduler 看到的是已经算好的结构化状态。</div>
</div>

<div class="card card-w">
<h3>⑥ 设计边界与故障处理</h3>
<table>
<tr><th>设计问题</th><th>处理机制</th></tr>
<tr><td>为什么用 AIJob，而不是只有 PredictionResult？</td><td>AIJob 表达训练任务语义：模型、batch size、replica、GPU、checkpoint、minAvailable、共置容忍度。PredictionResult 只是 AIJob 的调度辅助状态。</td></tr>
<tr><td>为什么不用 Pod annotation？</td><td>预测结果是结构化状态，可能包含 runtime、confidence、干扰矩阵、版本和更新时间；CRD 可独立 watch、GC、鉴权和演进，不污染 Pod 对象。</td></tr>
<tr><td>为什么不在 Filter 里直接 gRPC 调模型？</td><td>Filter 是节点级并行热路径，节点数越多 RPC 越多；scheduler P99 必须稳定，所以只读 Informer 本地 cache。</td></tr>
<tr><td>预测不准怎么办？</td><td>用 confidence 和安全 margin；低置信度走保守策略；PostBind 后回收真实 runtime 和 retention；SLO 破坏时驱逐低优共置伙伴。</td></tr>
<tr><td>冷启动没有 PredictionResult 怎么办？</td><td>Guaranteed 任务保守拒绝高风险共置；BestEffort 可用 namespace / AIJob 类型历史中位数和默认 retention；同时 AIJob Operator 尽快补齐 CRD。</td></tr>
<tr><td>怎么证明有效？</td><td>看调度延迟、JCT、waiting time、GPU 利用率、SLO violation、实际 retention；做 ablation：去掉 runtime 排序、去掉 interference Filter、去掉 interference Score。</td></tr>
</table>
<div class="qa-summary">预测运行时间作用于“先调谁”，共置干扰预测作用于“能不能放和放哪里”；预测值由 Operator 异步写 CRD，scheduler plugin 通过 Informer 本地缓存读取。</div>
</div>
