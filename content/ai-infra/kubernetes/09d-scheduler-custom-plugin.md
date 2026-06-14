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
