## 调度框架全景图

下面这张是 `kubernetes/enhancements/keps/sig-scheduling/624-scheduling-framework` 设计文档给出的官方流程图。

官方资料：[Scheduling Framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/) · [Scheduler Configuration](https://kubernetes.io/docs/reference/scheduling/config/)

<div class="figure">
<img src="../../../resources/images/k8s-scheduler/02-scheduling-framework.png" alt="Kubernetes Scheduling Framework 流程图" loading="lazy">
<p class="caption">PreEnqueue → Scheduling Cycle（PreFilter / Filter / PreScore / Score / NormalizeScore / Reserve / Permit）→ Binding Cycle（WaitOnPermit / PreBind / Bind / PostBind）。Scheduling Cycle 串行，Binding Cycle 可与下一个 Pod 的 Scheduling Cycle 并发。</p>
</div>

## QueueSort：全局队列只能有一套顺序

<div class="card card-s">
<h3><code>Less(p1, p2)</code> 决定谁先获得调度机会</h3>
<p>QueueSort 不选择节点，而是比较 ActiveQ 中两个 Pod 的先后顺序。默认 <code>PrioritySort</code> 先比较 Priority，优先级相同时再比较入队时间。自定义实现可以加入租户公平性、deadline 或预测运行时间，但必须保留确定的 tie-breaker，并满足传递性；否则优先队列可能出现不稳定顺序。</p>
<table>
<tr><th>规则</th><th>原因</th></tr>
<tr><td>同一时刻只能启用一个 QueueSort Plugin</td><td>一个优先队列只能依赖一套比较关系维护堆序</td></tr>
<tr><td>同一 kube-scheduler 的所有 Profile 必须使用相同插件和相同参数</td><td>多个 Profile 共享同一个 pending Pods queue，而不是各自维护 ActiveQ</td></tr>
<tr><td>比较器必须有稳定的最终 tie-breaker</td><td>避免两个 Pod 在多次比较中前后关系漂移，并降低饥饿风险</td></tr>
<tr><td>排序状态必须能低成本读取</td><td><code>Less</code> 位于队列热路径，外部 RPC 会直接放大入队和出队延迟</td></tr>
</table>
</div>

## PreFilter vs Filter：为什么必须拆开

<div class="card card-m">
<h3>核心差异表</h3>
<table>
<tr><th>维度</th><th>PreFilter</th><th>Filter</th></tr>
<tr><td>阶段目标</td><td><strong>数据预处理 + 全局状态检查</strong></td><td><strong>节点级过滤</strong>，逐节点检查条件</td></tr>
<tr><td>数据流</td><td>写入共享数据到 <code>CycleState</code></td><td>从 <code>CycleState</code> 读取数据并过滤节点</td></tr>
<tr><td>执行顺序</td><td>所有 PreFilter 插件按配置顺序执行</td><td>候选 Node 可以并行评估；同一 Node 内的 Filter 插件按配置顺序执行</td></tr>
<tr><td>终止能力</td><td>可以提前终止整个调度周期（如 Pod 不合法、PodGroup 不齐）</td><td>仅排除当前节点，不影响其它节点判断</td></tr>
<tr><td>调用次数</td><td>每个调度周期调用一次</td><td>每个候选节点调用一次（节点数 × 插件数）</td></tr>
<tr><td>典型工作</td><td>解析 Pod annotation、查 PodGroup 状态、构建拓扑索引、计算资源需求</td><td>检查节点资源、Taint、Affinity、Volume、自定义约束</td></tr>
</table>
<div class="qa-summary">设计哲学：<strong>能在 PreFilter 算一次的事，绝不在 Filter 里对每个节点重复算</strong>。这是 Filter 阶段并行化的前提。</div>
</div>

<div class="card card-d">
<h3>为什么要这样切：一个具体例子</h3>
<p>假设你写一个「<strong>Pod 必须放在和它的 PodGroup 其他成员同 zone 的节点上</strong>」插件：</p>
<ul>
<li>查 PodGroup 当前已绑定到哪些 zone：<strong>这是一次集群级查询，所有节点都用同一个结果</strong>。如果放在 Filter 里，N 个节点会查 N 次，性能爆炸。</li>
<li>正确做法：<code>PreFilter</code> 里查一次写入 <code>CycleState["targetZones"] = [...]</code>；<code>Filter</code> 里只做 <code>node.zone in targetZones</code> 这种 O(1) 判断。</li>
</ul>
<p>这同时解释了为什么不同 Node 的 Filter 计算可以并行：每个 goroutine 只读本轮准备好的 <code>CycleState</code> 和当前 NodeInfo。插件若在 Filter 中修改共享状态，必须自行保证并发安全。</p>
</div>

<div class="card card-w">
<h3>Filter 的短路与失败语义</h3>
<p>对一个候选 Node，scheduler 按配置顺序调用 Filter 插件。只要某个插件把该 Node 判为 infeasible，后续 Filter 插件就不再为这个 Node 执行；其他 Node 的评估不受影响，并可继续并行。</p>
<table>
<tr><th>返回状态</th><th>含义</th><th>后续影响</th></tr>
<tr><td><code>Success</code></td><td>当前插件允许该 Node</td><td>继续执行该 Node 的下一个 Filter 插件</td></tr>
<tr><td><code>Unschedulable</code></td><td>当前条件下不可行，但状态变化后可能恢复</td><td>该 Node 短路；失败插件进入 Diagnosis，后续事件可通过 QueueingHint 唤醒 Pod</td></tr>
<tr><td><code>UnschedulableAndUnresolvable</code></td><td>当前约束很难由普通集群事件解决</td><td>该 Node 短路，并减少无意义的抢占或重试</td></tr>
<tr><td><code>Error</code></td><td>插件执行或依赖发生内部错误</td><td>不是普通“不满足约束”，本次调度按错误路径失败并重试</td></tr>
</table>
<p>短路意味着 FailedScheduling 事件不保证列出每个 Node 上所有潜在失败原因；它记录的是实际执行到的诊断结果。调整 Filter 插件顺序既影响性能，也可能影响首先暴露给用户的失败原因。</p>
</div>

## PreScore vs Score：同样的设计套路

<div class="card card-s">
<h3>核心差异表</h3>
<table>
<tr><th>维度</th><th>PreScore</th><th>Score</th></tr>
<tr><td>阶段目标</td><td>全局数据准备，避免重复计算</td><td>节点级打分，按策略生成优先级</td></tr>
<tr><td>数据粒度</td><td>集群级 / 候选节点列表级</td><td>单节点级</td></tr>
<tr><td>执行频率</td><td>每个调度周期一次</td><td>每个候选节点一次</td></tr>
<tr><td>输出影响</td><td>不直接参与最终决策，只准备中间数据</td><td>直接影响节点排名（0–100）</td></tr>
</table>
<p>典型例子：<code>PodTopologySpread</code> 在 PreScore 里统计每个拓扑域当前已有多少 Pod；Score 里只做「这个节点所在域是不是欠的最多」的查表打分。</p>
</div>

## NormalizeScore：被忽略的第三段

`Score` 出来的原始分可能不在 `[0, MaxNodeScore]` 区间内。`NormalizeScore` 是**同一个插件的最后机会**对自己所有节点的分数做一次归一化（线性缩放、对数压缩等），保证不同插件的分数能加权合并。

| 阶段 | 单位 | 跨节点视野 |
|---|---|---|
| PreScore | 一次 | 全局 |
| Score | 节点 | 单节点 |
| NormalizeScore | 一次 | **本插件的所有节点分数列表** |

每个 Score 插件先完成自己的节点打分和可选归一化，Framework 再校验分数范围并乘以该插件在 `KubeSchedulerConfiguration` 中配置的 weight，最后对同一 Node 求和：

```text
FinalScore(node) = Σ Normalize(pluginScore(node)) × pluginWeight
```

某个 Score 插件返回错误时，本次调度周期按错误处理，而不是忽略它后继续用不完整的总分选 Node。并列最高分节点由 scheduler 再做选择，不能假定总会固定命中同一个节点。

## Plugin 与 Hook 的多对多结构

K8s scheduler 框架的优雅之处：**一个插件可以挂多个 Hook，一个 Hook 可以挂多个插件，一个 Hook 内可以注册多种策略**。下面三段代码是 `kube-scheduler` 源码里的真实写法。

### 1. 一个插件挂多个 Hook（NodeAffinity）

```go
// pkg/scheduler/framework/plugins/nodeaffinity/node_affinity.go
var _ framework.PreFilterPlugin    = &NodeAffinity{}
var _ framework.FilterPlugin       = &NodeAffinity{}
var _ framework.PreScorePlugin     = &NodeAffinity{}
var _ framework.ScorePlugin        = &NodeAffinity{}
var _ framework.EnqueueExtensions  = &NodeAffinity{}
```

<div class="card card-w">
<h3>这五行 <code>var _ = ...</code> 是什么写法</h3>
<p>这是 Go 里一个常见的<strong>编译期接口实现校验</strong>技巧：</p>
<ul>
<li><code>var _ framework.FilterPlugin = &NodeAffinity{}</code> 这一行不引入任何运行时变量（<code>_</code> 是空标识符），但会强制编译器检查 <code>*NodeAffinity</code> 是否实现了 <code>framework.FilterPlugin</code> 接口的所有方法。</li>
<li>少写一个方法 → <strong>编译失败</strong>，不会等到运行时才报错。</li>
<li>面试可以答："这是一种零运行时开销的接口契约校验，K8s、etcd、Docker 等大型 Go 项目都在用。"</li>
</ul>
</div>

### 2. 一个 Hook 挂多个插件（ScorePlugin）

```go
// 这些都在不同的 plugin 目录里，全部实现了 ScorePlugin
var _ framework.ScorePlugin = &NodeAffinity{}        // nodeaffinity
var _ framework.ScorePlugin = &Fit{}                 // noderesources（默认 LeastAllocated）
var _ framework.ScorePlugin = &BalancedAllocation{}  // noderesources（CPU/Mem 均衡）
var _ framework.ScorePlugin = &TaintToleration{}     // tainttoleration
var _ framework.ScorePlugin = &PodTopologySpread{}   // podtopologyspread
```

调度器最终给某个节点的总分 = `Σ (插件分 × 插件权重)`。权重在 `KubeSchedulerConfiguration` 里配置，**不重新编译就能改**。

### 3. 一个插件在一个 Hook 里挂多种策略（NodeResourcesFit）

```go
// pkg/scheduler/framework/plugins/noderesources/resource_allocation.go
var nodeResourceStrategyTypeMap = map[config.ScoringStrategyType]scorer{
    config.LeastAllocated: func(args *config.NodeResourcesFitArgs) *resourceAllocationScorer {
        return &resourceAllocationScorer{
            Name:      string(config.LeastAllocated),
            scorer:    leastResourceScorer(args.ScoringStrategy.Resources),
            resources: args.ScoringStrategy.Resources,
        }
    },
    config.MostAllocated: func(args *config.NodeResourcesFitArgs) *resourceAllocationScorer {
        return &resourceAllocationScorer{
            Name:      string(config.MostAllocated),
            scorer:    mostResourceScorer(args.ScoringStrategy.Resources),
            resources: args.ScoringStrategy.Resources,
        }
    },
    config.RequestedToCapacityRatio: func(args *config.NodeResourcesFitArgs) *resourceAllocationScorer {
        return &resourceAllocationScorer{
            Name:      string(config.RequestedToCapacityRatio),
            scorer:    requestedToCapacityRatioScorer(args.ScoringStrategy.Resources, args.ScoringStrategy.RequestedToCapacityRatio.Shape),
            resources: args.ScoringStrategy.Resources,
        }
    },
}
```

<div class="qa-summary">三种策略对应三种目标：<strong>LeastAllocated 倾向分散、MostAllocated 倾向 bin packing、RequestedToCapacityRatio 使用自定义利用率—分数曲线</strong>。</div>

## kube-scheduler 源码目录职责

`framework/interface.go` 定义扩展点契约，`runtime/framework.go` 负责插件注册、配置与调用，`schedule_one.go` 把这些 Hook 串入单 Pod 调度和绑定主循环。

```
kubernetes/pkg/scheduler/
├── apis/                       # KubeSchedulerConfiguration 结构、参数校验
├── framework/                  # 调度框架核心
│   ├── interface.go            # 所有扩展点接口定义（必读起点）
│   ├── cycle_state.go          # CycleState 线程安全状态读写
│   ├── types.go                # NodeInfo、PodInfo、QueuedPodInfo
│   ├── events.go               # 调度事件记录
│   ├── extender.go             # 外部 Extender 的 HTTP 通信
│   ├── listers.go              # 本地 Node/Pod cache 查询
│   ├── parallelize/            # 并行 Filter 工具（默认 16 协程）
│   ├── preemption/             # 抢占公共逻辑（PostFilter 复用）
│   ├── plugins/                # 内置插件（nodeaffinity、noderesources、…）
│   ├── runtime/                # 插件注册、配置加载、依赖解析
│   └── autoscaler_contract/    # 与 Cluster Autoscaler 交互的协议
├── backend/                    # SchedulingQueue、Scheduler Cache 实现
├── profile/                    # 多 Profile 支持（一台 scheduler 跑多套配置）
├── schedule_one.go             # 单 Pod 调度主循环（schedulingCycle / bindingCycle）
└── scheduler.go                # Scheduler 结构体、Run() 入口
```

核心数据载体：

```go
// pkg/scheduler/scheduler.go
type Scheduler struct {
    Cache             internalcache.Cache         // 实时 Node / Pod 状态，pod 中心设计
    SchedulingQueue   internalqueue.SchedulingQueue // 待调度 Pod 队列
    // ...
}

// pkg/scheduler/schedule_one.go 主流程
// Scheduler.schedulingCycle()
//   ├── Scheduler.schedulePod()
//   │   ├── findNodesThatFitPod()
//   │   │   ├── Framework.RunPreFilterPlugins()
//   │   │   └── findNodesThatPassFilters()
//   │   │       └── Framework.RunFilterPluginsWithNominatedPods()
//   │   └── prioritizeNodes()
//   │       ├── Framework.RunPreScorePlugins()
//   │       └── Framework.RunScorePlugins()
//   ├── Framework.RunReservePluginsReserve()
//   └── Framework.RunPermitPlugins()
// Scheduler.bindingCycle()
//   ├── Framework.WaitOnPermit()
//   ├── Framework.RunPreBind()
//   └── Scheduler.bind() → Framework.RunBindPlugins() → Framework.RunPostBindPlugins()
```
