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
<div class="formula">KV Cache = layers × 2 × kv_heads × head_dim × seq_len × bytes</div>
<p>如果 batch 中有 B 个请求，近似乘以 B；如果用 GQA/MQA，<code>kv_heads</code> 会显著小于 query heads。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 prefill 和 decode 的瓶颈不同？</div>
<div class="qa-a"><p><strong>回答思路：</strong>从计算形态和内存访问形态解释。</p><div class="qa-section"><div class="qa-section-title">Prefill</div><p>Prefill 一次处理整段 prompt，可以形成较大的矩阵乘，GPU 算力利用更高，通常偏 compute-bound。</p></div><div class="qa-section"><div class="qa-section-title">Decode</div><p>Decode 每次只生成一个 token，但要读取历史 KV cache，batch 小时矩阵规模小，常偏 memory-bound。</p></div><div class="qa-summary">面试口径：prefill 看首 token 和算力，decode 看逐 token 延迟和 KV cache 访存。</div></div>
</div>
