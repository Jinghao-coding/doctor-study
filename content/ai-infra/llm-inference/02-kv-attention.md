<h3>KV 缓存机制</h3>
<p>自回归解码时，每步需要之前所有 token 的 Key 和 Value 向量。如果每步重新计算，代价是 O(n²)。KV 缓存把之前算过的 K/V 存下来，每步只计算新 token 的 K/V 并追加。</p>
<div class="formula">KV 缓存大小 = 2 × num_layers × num_heads × head_dim × seq_len × dtype_size</div>
<p>以 LLaMA-70B 为例：2 × 80 × 8 × 128 × 4096 × 2（FP16）≈ 10.7GB（单个请求）。</p>
<p><strong>为什么 KV 缓存是瓶颈？</strong>GPU 显存有限（80GB），模型权重占 140GB（FP16）需要张量并行到多卡。剩余显存被 KV 缓存瓜分，决定了能同时服务多少请求。</p>

<h3>PagedAttention（vLLM）</h3>
<p>传统 KV 缓存预分配连续内存，最大长度固定，短请求浪费严重。PagedAttention 借鉴操作系统虚拟内存的分页思想：</p>
<ul>
<li>把 KV 缓存切成固定大小的 block（如 16 token 一块）</li>
<li>用 block table 维护逻辑到物理的映射</li>
<li>按需分配，请求结束释放，消除内部碎片</li>
<li>支持 copy-on-write，多个 beam 可共享公共前缀</li>
</ul>

<h3>Attention 变体</h3>
<table>
<tr><th>变体</th><th>KV Head 数</th><th>KV 缓存大小</th><th>代表模型</th></tr>
<tr><td>MHA（Multi-Head Attention）</td><td>= Query Head 数</td><td>最大</td><td>GPT-3, LLaMA-1</td></tr>
<tr><td>GQA（Grouped-Query Attention）</td><td>Query Head 数 / G</td><td>缩小 G 倍</td><td>LLaMA-2/3, Mixtral</td></tr>
<tr><td>MQA（Multi-Query Attention）</td><td>1</td><td>最小</td><td>Falcon, StarCoder</td></tr>
</table>
<p>GQA 是实际部署的主流选择——在质量和效率之间取得平衡。</p>

<h3>FlashAttention</h3>
<p>标准 attention 的显存占用 O(N²)，FlashAttention 通过 tiling（分块计算）+ 重计算（不存中间 softmax 矩阵）将显存降到 O(N)，同时利用 GPU SRAM 提速。核心思想：用计算换显存，避免 HBM 的反复读写。</p>
