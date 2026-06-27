## 一句话结论

Prefill/Decode 是 LLM 推理最核心的阶段划分：prefill 负责一次性读完 prompt 并建立 KV cache，decode 负责逐 token 生成并持续读写 KV cache。
## LLM 推理是什么

LLM 推理是模型接收用户输入，并逐步生成回复的过程。一次完整请求通常包含请求调度、Prompt 预处理、Prefill 计算、Decode 逐 token 生成和结果返回几个阶段。

推理可以拆成两个核心阶段：`Prefill` 一次性处理完整 Prompt，生成初始 KV Cache；`Decode` 基于已有上下文逐 token 生成回复，并持续更新 KV Cache。

核心判断：Prefill 更偏计算密集，主要受输入长度、模型规模和 GPU 算力影响；Decode 更偏访存密集，主要受 KV Cache 读写、显存带宽和 batch 调度影响。

## 核心概念

| 概念 | 说明 |
|---|---|
| Prompt | 用户输入给模型的上下文 |
| Token | 模型处理和生成文本的基本单位 |
| Prefill | 处理完整输入，生成首 token 所需上下文和 KV Cache |
| Decode | 每次生成一个新 token，并更新 KV Cache |
| KV Cache | 缓存历史 token 的 Key 和 Value，避免重复计算 |
| TTFT | Time To First Token，首 token 延迟 |
| TPOT | Time Per Output Token，单 token 生成耗时 |

## Prefill 与 Decode

| 维度 | Prefill | Decode |
|---|---|---|
| 输入 | 完整 Prompt token 序列 | 上一步生成的 token 和历史 KV Cache |
| 输出 | 初始上下文、KV Cache、首 token 分布 | 下一个 token 和新增 KV Cache |
| 计算模式 | 并行处理多个 token | 串行逐 token 生成 |
| 主要瓶颈 | 矩阵计算、长上下文 attention | KV Cache 读取、显存带宽 |
| 关键指标 | TTFT | TPOT、吞吐、P99 延迟 |

## 记忆框架

LLM 推理系统的主线可以按“请求怎么流动、每个阶段做什么、瓶颈在哪里、如何优化、用什么引擎落地”来理解。

后续模块按这个顺序展开：先讲请求生命周期，再分别拆 Prefill 和 Decode，然后解释 KV Cache 与 Attention，最后落到性能指标、优化技术和推理引擎选型。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
