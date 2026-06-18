## 一句话结论

Transformer Explainer 是一个适合“建立动态直觉”的交互式可视化项目，建议配合本站的 Attention、FLOPs/Roofline 和推理系统章节使用：它负责看懂 token 如何流过模型，我们负责补齐公式、系统瓶颈和面试回答。

## 资源入口

<div class="resource-grid">
<a class="resource-card" href="https://poloclub.github.io/transformer-explainer/">
<div class="resource-type">visual</div>
<div class="resource-title">Transformer Explainer</div>
<div class="resource-desc">Georgia Tech Polo Club 的交互式 Transformer 可视化，可逐步观察 token、attention、MLP、logits 和生成过程。</div>
</a>
</div>

## 怎么用它学习

| 你要理解什么 | 在 Explainer 里看什么 | 回到本站补什么 |
|---|---|---|
| Token 怎么进入模型 | 输入 token、embedding、position 的变化 | `输入处理`：Tokenizer、Embedding、位置编码边界 |
| Attention 怎么混合信息 | attention heads 对不同 token 的权重 | `Attention 机制`：Q/K/V、mask、multi-head 公式 |
| 每层在做什么 | residual stream、attention block、MLP block 的变化 | `整体架构`：残差主干、Norm、FFN 职责 |
| 生成为何逐 token 进行 | next-token logits 和采样过程 | `LLM 推理系统`：prefill/decode、KV cache、TPOT |
| 为什么算子有不同瓶颈 | attention/MLP 的结构和张量形状 | `计算分析`：FLOPs、Roofline、memory-bound 判定 |

## 推荐学习路径

1. 先打开 Transformer Explainer，输入一句短文本，观察 token 如何逐层变化。
2. 重点看 attention head 是否关注不同位置，不要急着背公式。
3. 回到本站 `Attention 机制`，把可视化里的权重矩阵对应到：

<div class="formula">$$
\operatorname{Attention}(Q,K,V)
= \operatorname{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right)V
$$</div>

4. 再看 `计算分析`，理解为什么同样是 Transformer，prefill 更像大 GEMM，decode 更容易被 HBM/KV cache 限制。
5. 最后用 `面试高频题` 把可视化直觉压缩成可复述答案。

## 常见误区

| 误区 | 正确理解 |
|---|---|
| 看懂可视化就等于懂 Transformer | 可视化建立直觉，但还要补张量形状、复杂度、mask、KV cache 和系统瓶颈。 |
| attention head 的颜色就是固定语义 | head 的行为是 learned pattern，不要过度解释某个 head 的单次可视化。 |
| 可视化里的小模型能代表线上 LLM 性能 | 小模型适合理解机制，线上 LLM 还要看显存、并行、batching、KV cache 和 serving engine。 |
| Transformer 架构图已经够了 | 架构图是静态结构，Explainer 补动态过程，本站补工程和面试表达。 |

## 关联模块

- `整体架构`：静态结构和 Encoder/Decoder/Decoder-only 边界。
- `Attention 机制`：Q/K/V、Multi-Head、causal mask 和手撕代码。
- `计算分析`：FLOPs、Roofline、逐算子 compute/memory-bound 分类。
- `LLM 推理系统`：Prefill/Decode、KV Cache、Serving Engine 和线上性能。
