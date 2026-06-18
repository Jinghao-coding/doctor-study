## 一句话结论

AI Infra 的可观测性要把业务指标、模型指标、系统指标和调度指标连起来；容量规划要从 SLO 反推 GPU、显存、网络、存储和队列余量。面试不要只说 Prometheus，要说**指标分层、告警归因、容量模型和成本权衡**。

## 指标分层

| 层级 | 训练场景 | 推理场景 | 调度 / 平台场景 |
|---|---|---|---|
| 业务指标 | 任务成功率、训练完成时间、有效吞吐 | QPS、成功率、TTFT、TPOT、P95/P99 | 提交成功率、准入延迟、排队时长 |
| 模型指标 | loss、gradient norm、tokens/s、MFU | 输出 token/s、cache hit、acceptance rate | 不直接看模型质量，但要关联模型大小和资源需求 |
| GPU 指标 | GPU-Util、SM Active、HBM、显存、ECC、功耗 | HBM、KV cache、batch size、kernel timeline | 卡健康、碎片率、MIG/MPS 归因 |
| 网络指标 | NCCL 带宽、重传、RDMA error、AllReduce 时间 | P/D 分离 KV 传输、跨节点延迟 | 节点拓扑、交换机拥塞、机架放置 |
| 存储指标 | 数据加载吞吐、checkpoint 时间、元数据延迟 | 权重加载、模型分发、日志写入 | PVC attach、对象存储吞吐、缓存命中 |
| 控制面指标 | Operator reconcile、API error、队列 depth | 发布状态、endpoint 健康 | scheduler latency、binding error、quota ledger |

## SLO 设计

<div class="card card-m">
<h3>推理 SLO</h3>
<p>常见目标是可用性、错误率、TTFT、TPOT、P99、吞吐和成本。交互式服务通常优先保护 TTFT 和 TPOT；离线批处理更关注吞吐和单位成本。</p>
</div>

<div class="card card-d">
<h3>训练 SLO</h3>
<p>训练不一定有请求级延迟，但有任务级 SLO：排队时间、启动时间、失败恢复时间、checkpoint 保存时间、tokens/s、MFU、任务完成率和资源浪费率。</p>
</div>

<div class="card card-w">
<h3>告警要避免只看单点指标</h3>
<p><code>GPU-Util</code> 低不能直接说明 GPU 问题，可能是 DataLoader、H2D、NCCL、存储、调度队列或应用同步点。告警应该带上上下文指标，方便直接归因。</p>
</div>

## 容量规划

```flow
确定 SLO | QPS、TTFT/TPOT、训练完成时间、排队时间
建立单模型画像 | 参数量、KV cache、tokens/s、显存、网络和存储需求
估算峰值负载 | 日峰值、活动峰值、长 prompt 比例、训练提交波峰
映射资源池 | GPU 型号、显存、互联、CPU、内存、NVMe、网络
加入安全余量 | N+1、故障域、升级窗口、碎片、冷启动、抢占恢复
持续校准 | 用线上 metrics 和 profile 修正容量模型
```

| 问题 | 估算方法 | 风险 |
|---|---|---|
| 推理需要多少 GPU | 单卡 tokens/s、batch 策略、TTFT/TPOT SLO、峰值 QPS | 长 prompt 和 KV cache 可能比权重更先打满显存 |
| 训练队列需要多少 GPU | 到达率、平均训练时长、资源规格、目标排队时间 | Gang 作业和拓扑约束导致碎片 |
| 该买哪类 GPU | 模型大小、精度、显存容量、HBM 带宽、互联、功耗 | 只看 TFLOPS 会忽略 memory-bound 和通信瓶颈 |
| 成本如何衡量 | GPU 小时、tokens/J、tokens/$、利用率、失败重跑率 | 平均利用率高不代表 P99 和用户体验好 |

## 排查路径

```flow
先看用户症状 | 慢请求、失败、排队、训练停滞、成本异常
对齐 SLO 指标 | 错误率、TTFT、TPOT、JCT、queue time、MFU
分层定位 | 应用、模型、GPU、网络、存储、调度、控制面
拿证据 | metrics、logs、trace、profile、events、scheduler state
修复复测 | 限流、扩容、调度策略、模型参数、数据路径、发布回滚
```

## 关联模块

- `GPU 利用率诊断`：提供 SM、HBM、Occupancy 和 Warp Stall 的底层解释。
- `LLM 推理系统`：提供 TTFT、TPOT、KV cache 和 serving scheduler 语境。
- `分布式训练`：提供 MFU、NCCL、checkpoint 和 hang 排查语境。
- `任务调度理论 / GPU 集群管理`：提供排队、配额、碎片和公平性语境。
