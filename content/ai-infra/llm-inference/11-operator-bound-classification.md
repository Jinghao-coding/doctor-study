## 一句话结论

不能笼统地说 Transformer 是 Compute-bound 或 Memory-bound。相同算子在 Prefill 与 Decode 阶段可能因为矩阵形状和数据复用不同而改变瓶颈类型；多卡通信还需要单独归为 Communication-bound。

## 逐算子分类

| 组件 | Prefill | 小 Batch Decode | 原因 |
|---|---|---|---|
| QKV / 输出投影 | 多偏 Compute-bound | 多偏 Memory-bound | Decode 的 GEMM 变“瘦”，权重复用低 |
| FFN up/gate/down | 多偏 Compute-bound | 多偏 Memory-bound | 大量权重需要反复从 HBM 读取 |
| Attention score | 长序列时计算重 | Memory-bound | Decode 每步扫描历史 K Cache |
| Attention × V | 长序列时计算重 | Memory-bound | Decode 每步扫描历史 V Cache |
| Softmax、Norm、Residual、RoPE | 多偏 Memory-bound | 多偏 Memory-bound | 逐元素或规约操作，FLOPs/Byte 低 |
| KV Cache 写入与读取 | 容量压力 | 带宽与容量压力 | 上下文越长，每步读取越多 |
| AllReduce / AllGather | Communication-bound | Communication-bound | 受链路、拓扑、消息大小和并发影响 |

“多偏”很重要：最终还要结合 Batch、序列长度、精度、硬件平衡点和 Kernel 实现判断，不能把表格当作绝对规则。

## 判断方法

```flow
确认阶段和张量形状 | Prefill 还是 Decode，Batch/Sequence 多大
计算算术强度 | FLOPs ÷ 实际 HBM Bytes
对比机器平衡点 | Peak FLOPs ÷ Peak HBM Bandwidth
检查第三类瓶颈 | Launch、同步、通信、容量、CPU 供给
用 Profiling 验证 | Timeline、SM、Tensor Core、HBM、NCCL
```

## Kernel Fusion 为什么有效

Residual、Activation、Norm 等算子单独执行时需要多次读写 HBM。Fusion 把中间结果留在寄存器或 Shared Memory 中，减少 Kernel Launch 和 HBM 往返，因此主要改善 Memory-bound 与 Launch-bound 问题，而不是凭空增加峰值算力。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 同一个 FFN 为什么 Prefill 偏 Compute-bound，Decode 偏 Memory-bound？</div>
<div class="qa-a"><p>Prefill 一次处理大量 Token，同一份 FFN 权重被许多行输入复用，形成更饱满的 GEMM；小 Batch Decode 每步只有少量 Token，矩阵变瘦，权重几乎每步都要从 HBM 重新读取，算术强度明显下降。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么长上下文会让 Decode 越来越慢？</div>
<div class="qa-a"><p>每生成一个 Token，Attention 都要读取历史 K/V。上下文变长后，KV Cache 的读取量近似线性增加，单步 Decode 的带宽压力随之增大；因此需要 GQA/MQA、KV 量化、分页管理和更好的调度。</p></div>
</div>

## 关联模块

- `LLM 推理 / Prefill 与 Decode`：阶段语义和 TTFT/TPOT。
- `LLM 推理 / FlashAttention`：减少 Attention 中间结果的 HBM I/O。
- `GPU / CUDA 内存模型`：寄存器、Shared Memory、L2 与 HBM。
- `分布式训练 / NCCL`：Communication-bound 的完整诊断链路。
