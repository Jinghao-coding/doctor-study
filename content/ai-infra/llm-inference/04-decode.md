## 一句话结论

Decode 阶段的核心是逐 token 生成和 KV cache 访存，batch 小时常见 memory-bound。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | LLM 推理系统 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕请求生命周期、Prefill/Decode、KV Cache、Attention 优化、Serving Engine 和性能瓶颈建立系统化面试答案。 |
| 面试抓手 | 把 TPOT 拆成调度、KV 读取、单步 forward、采样和流式返回。 |

## Decode 阶段

Decode 阶段负责自回归生成。模型每一步只生成一个新 token，但每一步都需要读取历史 KV Cache，所以它通常是推理服务中最容易受到显存带宽限制的阶段。

## 输入与输出

| 项目 | 内容 |
|---|---|
| 输入 | 上一步生成的 token、历史 KV Cache、采样参数 |
| 计算 | 单 token 前向、读取历史 K/V、生成 logits |
| 输出 | 下一个 token、新增 K/V、更新后的序列 |
| 关键指标 | TPOT、tokens/s、P95/P99 延迟 |

## 为什么访存密集

Decode 每步只处理一个新 token，矩阵乘规模小，无法充分吃满 GPU 算力；但它要读取历史所有 token 的 K/V，序列越长、batch 越大，读取量越高。

| 资源 | Decode 中的表现 |
|---|---|
| 算力 | 单 token 计算量小，Tensor Core 利用率不高 |
| 显存带宽 | 每步读取模型权重和 KV Cache，容易成为瓶颈 |
| 显存容量 | KV Cache 随上下文长度和并发数线性增长 |
| 调度 | batch 组织决定权重读取能否被多请求摊销 |

## TPOT 拆解

```text
TPOT = 单步模型计算 + KV Cache 读取 + 采样 + 流式返回
```

Decode 阶段的用户感知不是“第一个 token 多快”，而是“后续 token 是否稳定、连续、不卡顿”。

## 优化重点

| 目标 | 手段 | 说明 |
|---|---|---|
| 降低单 token 延迟 | CUDA Graph、Kernel Fusion | 减少 CPU-GPU 调度和中间读写 |
| 提高吞吐 | Continuous Batching | 多请求共享权重读取成本 |
| 降低 KV 读取压力 | GQA/MQA、KV Cache 量化 | 减少每步读取的数据量 |
| 减少显存碎片 | PagedAttention | 按需分配 KV block |
| 降低长尾延迟 | 优先级调度、抢占、分离式推理 | 避免长请求拖垮短请求 |

## 易错点

Decode 的 GPU 利用率低不一定是实现差，根因通常是 memory-bound。增大 batch 可以摊销权重读取，但 KV Cache 读取也会随 batch 和序列长度增长，所以 batch 不是无限增大的。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
