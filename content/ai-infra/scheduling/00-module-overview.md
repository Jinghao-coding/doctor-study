## 任务调度理论在 AI Infra 中的定位

任务调度理论是 AI Infra 各种**调度系统背后的算法基础**。无论是 K8s 调度器、Volcano 批调度，还是多租户 GPU 配额，本质都是在"有限资源、多个目标（延迟/吞吐/公平/利用率）"之间做权衡。

面试考调度，本质是确认：你是否能把一个具体的工程问题（GPU 碎片、训练排队、抢占）抽象成调度目标和算法，并讲清楚权衡。

<div class="card card-d">
<h3>一句话定位</h3>
<p>调度的核心是 <strong>目标函数 + 约束 + 算法</strong>：先想清楚优化什么（JCT、公平、利用率、SLO），再选算法（FIFO/SJF/DRF/Gang/Backfill），最后讨论抢占和碎片的代价。</p>
</div>

## 与其他模块的关系

| 关联模块 | 关系 | 关键连接点 |
|---|---|---|
| Kubernetes 核心 | K8s 调度器是这些理论的实现 | Scheduling Framework、抢占、优先级 |
| GPU 集群管理 | Volcano/Kueue 落地批调度 | Gang、Elastic Quota、Backfill |
| 分布式训练 | Gang 调度服务于多卡训练 | 全或无、拓扑感知放置 |
| GPU 硬件 | 拓扑感知依赖互联结构 | NVLink/PCIe、NUMA、RDMA |
| 性能预测 | 预测输入用于调度决策 | JCT 预测、资源需求预测 |

## 本模块包含哪些内容

| 板块 | 覆盖内容 | 典型面试问题 |
|---|---|---|
| 理论基础 | FIFO/SJF/SRTF/EDF、DRF、目标函数与指标 | SJF 为什么平均等待最短？怎么衡量调度好坏？ |
| 公平性与批调度 | Max-Min、DRF、Elastic Quota、Gang、Backfill | 多资源公平怎么定义？Gang 调度解决什么问题？ |
| AI 集群与面试 | 拓扑感知调度、GPU 集群调度系统设计 | GPU 碎片怎么处理？抢占的代价是什么？ |
