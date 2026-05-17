GPU 是面试里最容易被追问到底层的部分。建议按「计算单元、显存系统、互联拓扑、调度隔离」四层理解，而不是只背 A100/H100 参数。

| 概念 | 面试解释 |
| --- | --- |
| SM | GPU 基本执行单元，包含 CUDA Core、Tensor Core、寄存器和 shared memory。 |
| Tensor Core | 矩阵乘加专用硬件，是深度学习吞吐的核心来源。 |
| HBM | 高带宽显存，LLM decode 往往更受 HBM 带宽限制。 |
| NVLink / NVSwitch | 多 GPU 高速互联，决定张量并行、流水线并行和 all-reduce 的通信效率。 |

面试回答可以先给结论：训练和 prefill 更偏计算密集，decode 更偏显存带宽密集，所以同一张 GPU 在不同阶段的瓶颈完全不同。
