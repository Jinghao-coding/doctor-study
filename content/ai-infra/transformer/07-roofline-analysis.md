<div class="card card-m">
<h3>Roofline 在 Transformer 算子中的用法</h3>
<p>Roofline 用算术强度与机器平衡点判断 Transformer 算子更可能 compute-bound 还是 memory-bound。</p>
<table>
<tr><th>概念</th><th>Transformer 分析方法</th></tr>
<tr><td>算术强度</td><td>判断一个 Transformer kernel 的数据复用程度</td></tr>
<tr><td>机器平衡点</td><td>A100 约 156 FLOPs/Byte，低于它通常更偏 memory-bound</td></tr>
<tr><td>优化方向</td><td>memory-bound 优先减少 HBM 读写；compute-bound 优先提高 Tensor Core 利用率</td></tr>
</table>
<div class="qa-summary">算术强度低于机器平衡点时优先减少 HBM 读写，高于平衡点时优先提高 Tensor Core 利用率。</div>
</div>

<div class="card card-d">
<h3>哪些操作 compute-bound，哪些 memory-bound</h3>
<table>
<tr><th>操作</th><th>瓶颈</th><th>原因</th></tr>
<tr><td>大 batch 矩阵乘（QKV、FFN）</td><td>compute-bound</td><td>计算量随 batch 增长快，数据搬运增长慢，算术强度高</td></tr>
<tr><td>逐 token decode（batch 小）</td><td>memory-bound</td><td>矩阵乘退化成 GEMV，算术强度低，瓶颈是读权重带宽</td></tr>
<tr><td>Softmax、LayerNorm 等 element-wise</td><td>memory-bound</td><td>计算量相对访存量很小</td></tr>
</table>
</div>

<div class="card card-s">
<h3>串到 Prefill / Decode</h3>
<table>
<tr><th>阶段</th><th>计算形态</th><th>瓶颈</th><th>关键指标</th></tr>
<tr><td>Prefill</td><td>多 token 并行，大矩阵乘</td><td>compute-bound</td><td>TTFT</td></tr>
<tr><td>Decode</td><td>batch 小，GEMV，反复读权重</td><td>memory-bound</td><td>TPOT</td></tr>
</table>
<p>两阶段瓶颈相反，优化手段也相反：prefill 靠 chunked prefill、提高 TensorCore 利用率；decode 靠 continuous batching 摊销权重读取、靠 KV cache 量化和 PagedAttention 降带宽与显存压力。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 怎么判断一个 kernel 是 compute-bound 还是 memory-bound？</div>
<div class="qa-a"><p>算它的算术强度（FLOPs ÷ 访存 bytes），和机器平衡点（峰值算力 ÷ 峰值带宽）比较。高于平衡点就是 compute-bound，低于就是 memory-bound。比如 A100 平衡点 ≈ 312 TFLOPS / 2 TB/s ≈ 156 FLOP/byte，而 batch=1 decode 算术强度约为 1，远低于平衡点，是典型 memory-bound。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Roofline 模型在面试中怎么完整回答？</div>
<div class="qa-a">
<p>我会先定义横轴和纵轴：横轴是算术强度 <code>FLOPs/Byte</code>，纵轴是实际性能 <code>FLOPs/s</code>。然后给公式：可达性能上限等于 <code>min(峰值算力, 峰值带宽 × 算术强度)</code>。图上斜线是 memory roof，水平线是 compute roof，交点 ridge point 是机器平衡点。如果 kernel 落在斜线区域，优化方向是减少访存、提高数据复用、融合算子；如果落在水平线区域，优化方向是提高 Tensor Core 利用率、优化 tile、使用低精度或减少 FLOPs。</p>
<div class="qa-summary">Roofline 用 FLOPs/Byte 判断 kernel 是缺数据还是缺算力。</div>
</div>
</div>
