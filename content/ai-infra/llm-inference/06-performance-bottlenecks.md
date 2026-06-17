## 一句话结论

LLM 推理性能不能只看 QPS，要同时看 TTFT、TPOT、tokens/s、显存、P99 和 GPU 利用效率。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | LLM 推理系统 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕请求生命周期、Prefill/Decode、KV Cache、Attention 优化、Serving Engine 和性能瓶颈建立系统化面试答案。 |
| 面试抓手 | 先定义指标，再把 prefill/decode 的瓶颈分开。 |

<div class="card card-m">
<h3>性能指标与瓶颈：先分清 TTFT、TPOT 和吞吐</h3>
<p>LLM 推理性能不能只看 QPS。在线服务通常同时关注首 token 延迟、每 token 延迟、端到端延迟、吞吐、显存占用和稳定性。不同指标对应不同瓶颈：prefill 更偏计算密集，decode 更偏访存和 KV cache 读取。</p>
</div>

<div class="card card-s">
<h3>核心指标表</h3>
<table>
<tr><th>指标</th><th>含义</th><th>主要受什么影响</th><th>常见优化</th></tr>
<tr><td>TTFT</td><td>Time To First Token</td><td>排队、prompt prefill、调度</td><td>prefill batching、prefix cache、拆分 prefill/decode</td></tr>
<tr><td>TPOT</td><td>Time Per Output Token</td><td>decode 逐 token 计算和 KV 读取</td><td>continuous batching、GQA/MQA、KV cache 管理</td></tr>
<tr><td>Throughput</td><td>tokens/s 或 requests/s</td><td>batch size、显存、调度、并行度</td><td>动态 batching、量化、投机解码</td></tr>
<tr><td>显存占用</td><td>权重、KV cache、临时 workspace</td><td>模型大小、上下文长度、并发数</td><td>量化、PagedAttention、KV 压缩</td></tr>
</table>
</div>

<div class="card card-d">
<h3>KV Cache 显存估算</h3>
<p>粗略估算单个请求 KV cache：</p>
<div class="formula">$$\text{KV Cache} = layers \times 2 \times kv_heads \times head_dim \times seq_len \times \text{bytes}$$</div>
<p>如果 batch 中有 B 个请求，近似乘以 B；如果用 GQA/MQA，<code>kv_heads</code> 会显著小于 query heads。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 prefill 和 decode 的瓶颈不同？</div>
<div class="qa-a"><p><strong>回答思路：</strong>从计算形态和内存访问形态解释。</p><div class="qa-section"><div class="qa-section-title">Prefill</div><p>Prefill 一次处理整段 prompt，可以形成较大的矩阵乘，GPU 算力利用更高，通常偏 compute-bound。</p></div><div class="qa-section"><div class="qa-section-title">Decode</div><p>Decode 每次只生成一个 token，但要读取历史 KV cache，batch 小时矩阵规模小，常偏 memory-bound。</p></div><div class="qa-summary">面试口径：prefill 看首 token 和算力，decode 看逐 token 延迟和 KV cache 访存。</div></div>
</div>

## 面试回答

**30 秒版：**

LLM 推理性能不能只看 QPS，要同时看 TTFT、TPOT、tokens/s、显存、P99 和 GPU 利用效率。 先定义指标，再把 prefill/decode 的瓶颈分开。

**2 分钟版：**

LLM 推理性能不能只看 QPS，在线服务要同时盯 TTFT、TPOT、端到端延迟、吞吐、显存占用和 P99 稳定性。我会先把指标和瓶颈对上：TTFT 是首 token 延迟，受排队、prompt prefill 和调度影响，优化靠 prefill batching、prefix cache、拆分 prefill/decode；TPOT 是每 token 延迟，受 decode 逐 token 计算和 KV 读取影响，优化靠 continuous batching、GQA/MQA、KV cache 管理；吞吐看 batch size、显存和并行度，靠动态 batching、量化、投机解码提升。关键是 prefill 和 decode 瓶颈不同：prefill 一次处理整段 prompt，矩阵乘大、算力利用高，偏 compute-bound；decode 每步一个 token 但要读历史 KV cache，batch 小时矩阵规模小，偏 memory-bound。显存上 KV cache ≈ layers × 2 × kv_heads × head_dim × seq_len × bytes，再乘 batch，用 GQA/MQA 能显著减小 kv_heads。面试口径：prefill 看首 token 和算力，decode 看逐 token 延迟和 KV cache 访存。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
