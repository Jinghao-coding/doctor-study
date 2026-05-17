LLM 推理不要只说「生成 token」，需要拆成两个性能特征完全不同的阶段。

| 阶段 | 核心瓶颈 | 面试说法 |
| --- | --- | --- |
| Prefill | 计算密集 | 一次性处理 prompt，矩阵乘法并行度高，Tensor Core 利用率高。 |
| Decode | 显存带宽密集 | 每步生成一个 token，需要反复读取历史 KV cache，容易受 HBM 带宽限制。 |

常见指标：TTFT 看首 token 延迟，TPOT 看每个输出 token 的生成速度，Throughput 看整体 tokens/s。
