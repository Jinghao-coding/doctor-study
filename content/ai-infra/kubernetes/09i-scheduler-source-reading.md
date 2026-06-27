## 一句话结论

读 kube-scheduler 源码不要从插件细节开始，而要先抓住启动链路、Informer/Cache、调度循环、过滤打分、绑定循环这五条主线。Lark 文档提供的是源码阅读视角，适合作为 Scheduler 主链路和插件扩展内容的补充。
## 来源与使用方式

本页整理自 Lark 文档《万字长文详解 Kubernetes 调度器：kube-scheduler 实现》，重点吸收其源码阅读顺序和函数链路。原文更偏长篇源码剖析；本站保留面试复习需要的主线，不复制长代码。

## 源码阅读主线

| 主线 | 关键问题 | 关键入口 |
|---|---|---|
| 应用启动 | kube-scheduler 二进制怎么启动，配置怎么进入 scheduler | `cmd/kube-scheduler/scheduler.go`、`NewSchedulerCommand`、`runCommand`、`Setup` |
| Informer / Cache | scheduler 从哪里拿 Pod/Node/PV/PVC 状态 | `InformerFactory`、`DynInformerFactory`、`WaitForCacheSync`、scheduler cache |
| 调度循环 | 未绑定 Pod 怎么被不断消费 | `Scheduler.Run`、`SchedulingQueue.Run`、`scheduleOne` |
| 选节点 | 怎么从所有 Node 找 feasible nodes 并打分 | `schedulePod`、`findNodesThatFitPod`、`prioritizeNodes`、`selectHost` |
| 绑定循环 | 选中节点后怎么写回 API Server | `bindingCycle`、`WaitOnPermit`、`PreBind`、`Bind`、`PostBind` |

## 启动链路

```flow
main | `cmd/kube-scheduler/scheduler.go` 创建 cobra command
NewSchedulerCommand | 构造 Options、flags、配置文件入口
runCommand | 校验配置并调用 Setup
Setup | 创建 CompletedConfig、Framework profile、scheduler 实例
Run | 启动 informer/cache、Leader Election、最终调用 `sched.Run(ctx)`
```

面试里不需要背所有 flags，但要知道：scheduler 是通过 `KubeSchedulerConfiguration`、profiles、pluginConfig、extenders、parallelism、percentageOfNodesToScore 等配置组装出 Framework 和调度器实例的。

## 核心运行循环

Lark 文档里强调的主入口是：

```go
func (sched *Scheduler) Run(ctx context.Context) {
    sched.SchedulingQueue.Run(logger)
    go wait.UntilWithContext(ctx, sched.scheduleOne, 0)
    <-ctx.Done()
    sched.SchedulingQueue.Close()
}
```

这段代码说明三件事：

- scheduler 不是被动 RPC 服务，而是一个持续消费调度队列的控制循环。
- `SchedulingQueue` 负责存储和唤醒待调度 Pod。
- `scheduleOne` 是单个 Pod 调度的主流程。

## scheduleOne 的函数链路

```flow
scheduleOne | 从 SchedulingQueue 取一个 Pod
schedulingCycle | 串行运行，为 Pod 选择一个节点
schedulePod | 找可行节点、打分、选最高分节点
assume | 在 scheduler cache 里先假定 Pod 占用资源
bindingCycle | 并发执行 WaitOnPermit / PreBind / Bind / PostBind
failureHandler | 失败时回队列、记录 FailedScheduling、触发抢占或退避
```

关键点：**Scheduling Cycle 串行，Binding Cycle 可以和下一个 Pod 的 Scheduling Cycle 并发。**这也是为什么 `Reserve/Unreserve` 和 `Assume` 很重要：绑定还没写 API Server 前，scheduler 本地 cache 必须先看到资源已被占用，避免后续 Pod 过度分配。

## schedulePod 的三段式

Lark 文档中源码链路可以压缩成：

| 函数 | 对应扩展点 | 作用 |
|---|---|---|
| `findNodesThatFitPod` | `PreFilter`、`Filter`、Extender Filter | 找出 feasible nodes，并产出 `Diagnosis` / `NodeToStatus` |
| `prioritizeNodes` | `PreScore`、`Score`、`NormalizeScore`、Extender Prioritize | 对 feasible nodes 打分并加权汇总 |
| `selectHost` | 非插件，最终选择 | 在最高分节点中选择一个，得分相同会做随机化，避免固定偏置 |

## Diagnosis / FitError 为什么重要

调度失败时，`findNodesThatFitPod` 会把每个节点为什么不可行写到 `Diagnosis.NodeToStatusMap` 中。`FitError` 最终会变成 `FailedScheduling` 事件的一部分。

```flow
Filter 失败 | 每个 Node 记录失败 plugin 和原因
Diagnosis | 聚合 NodeToStatusMap、UnschedulablePlugins、PreFilterMsg
FitError | 没有 feasible node 时返回
Event | 用户通过 `kubectl describe pod` 看到 FailedScheduling
QueueingHint | 后续事件是否应该唤醒这个 Pod，依赖失败 plugin 的判断
```

这解释了为什么排查 Pending 不能只说“资源不足”：真实事件通常是多个 plugin 的聚合结果，例如 `NodeResourcesFit`、`NodeAffinity`、`TaintToleration`、`VolumeBinding`、`PodTopologySpread`。

## 与本站现有章节的关系

| 你想解决的问题 | 应该看 |
|---|---|
| Pod 为什么 Pending | `调度与资源模型` + 本页的 `Diagnosis / FitError` |
| 调度队列怎么流转 | `Scheduler 主链路 / 调度路径与三个队列` |
| PreFilter/Filter/Score 为什么这么拆 | `Scheduler 插件与扩展 / 扩展点设计差异` |
| 写自定义 GPU 拓扑插件 | `Scheduler 插件与扩展 / 自定义 Plugin 实战` |
| 如何观测哪个 plugin 卡住 | `Scheduler 插件与扩展 / Scheduler 可观测性` |

## 关联模块

- `调度与资源模型`：理解 Pod 需求和 Node 资源/约束。
- `Scheduler 主链路`：理解队列、cache、assume、抢占和 HA。
- `Scheduler 插件与扩展`：理解 Framework 扩展点和插件开发。
- `任务调度理论`：理解 Gang、Backfill、抢占代价这些策略为什么需要挂到 scheduler 上。
