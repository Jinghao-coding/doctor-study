## Prefill 阶段

Prefill 阶段一次性处理完整 Prompt，计算所有输入 token 的 attention，并生成后续 Decode 所需的 KV Cache。它主要影响 `TTFT`，也就是用户看到第一个 token 前的等待时间。

## 输入与输出

| 项目 | 内容 |
|---|---|
| 输入 | 完整 Prompt token 序列 |
| 计算 | Embedding、QKV 投影、Attention、FFN、Logits |
| 输出 | 首 token 分布、完整 Prompt 的 KV Cache |
| 关键指标 | TTFT、Prefill tokens/s、排队等待时间 |

## 为什么计算密集

Prefill 会并行处理多个 token，矩阵乘规模大，能够较好地利用 Tensor Core。长 Prompt 下 attention 的计算和显存访问都会增加，但整体通常更偏 compute-bound。

| 影响因素 | 影响方式 | 优化方向 |
|---|---|---|
| Prompt 长度 | 输入越长，attention 和 FFN 计算越多 | Prompt 压缩、Prefix Cache |
| 模型参数量 | 模型越大，前向计算越重 | 量化、模型裁剪、并行 |
| Batch 大小 | 大 batch 提升吞吐，也可能增加排队 | 动态 batch、优先级调度 |
| Attention 实现 | 标准 attention 中间读写开销高 | FlashAttention、算子融合 |
| 长 Prompt | 单次 Prefill 时间过长 | Chunked Prefill |

## TTFT 拆解

```text
TTFT = 排队等待 + Tokenization + Prefill 计算 + 首 token 采样 + 网络返回
```

其中 Prefill 计算通常是主要部分，但在高并发服务中，排队等待也可能成为 TTFT 的主要来源。

## 优化重点

| 目标 | 手段 | 说明 |
|---|---|---|
| 降低首 token 延迟 | FlashAttention、算子融合 | 减少 attention 中间读写 |
| 减少重复计算 | Prefix Cache | 复用相同 system prompt 或历史上下文 |
| 防止长 Prompt 阻塞 | Chunked Prefill | 把长 Prompt 拆块，穿插 Decode 执行 |
| 提升吞吐 | Continuous Batching | 调度器动态填充 batch |
| 降低显存占用 | 量化、KV Cache 管理 | 给更多并发请求留空间 |

## 易错点

Prefill 不等于“生成阶段”，它主要处理输入上下文。Prefill 慢不一定是模型本身慢，也可能是排队、Prompt 过长、batch 组织不合理或前缀缓存没有命中。
