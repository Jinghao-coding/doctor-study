## 一句话结论

KV Cache 显存预算决定推理并发上限，单 token、单请求、并发请求要逐级放大计算。
<div class="card card-d">
<h3>单 token KV Cache 到底多大：Llama-2-70B 实算</h3>
<p>KV Cache 大小公式：</p>
<p>$$\text{每 token 字节数} = \text{layers} \times \text{kv\_heads} \times \text{head\_dim} \times 2 \times \text{bytes}$$</p>
<p>公式里的 <code>2</code> 是 K 和 V 各一份。代入 Llama-2-70B（FP16）：</p>
<table>
<tr><th>项</th><th>含义</th><th>取值</th></tr>
<tr><td>layers</td><td>Transformer 层数</td><td>80</td></tr>
<tr><td>kv_heads</td><td>KV head 数（GQA）</td><td>8</td></tr>
<tr><td>head_dim</td><td>每个 head 维度</td><td>128</td></tr>
<tr><td>2</td><td>K 和 V 两份</td><td>2</td></tr>
<tr><td>bytes</td><td>FP16 每元素</td><td>2</td></tr>
</table>
<p>$$80 \times 8 \times 128 \times 2 \times 2 = 327{,}680\ \text{bytes} \approx 320\ \text{KB/token}$$</p>
<div class="qa-summary">关键：这只是<strong>一个 token</strong> 的 KV Cache，而且这是已经用 GQA（8 个 KV head）压过的结果。</div>
</div>

<div class="card card-w">
<h3>从单 token 放大到并发服务：显存压力来源</h3>
<p>把单 token 乘上序列长度和并发请求数，显存占用迅速膨胀：</p>
<table>
<tr><th>规模</th><th>计算</th><th>KV Cache</th></tr>
<tr><td>1 token</td><td>—</td><td>320 KB</td></tr>
<tr><td>1 请求 · 4096 上下文</td><td>$4096 \times 320\ \text{KB}$</td><td>≈ 1.3 GB</td></tr>
<tr><td>32 并发请求</td><td>$32 \times 1.3\ \text{GB}$</td><td>≈ 41.6 GB</td></tr>
</table>
<p>也就是说，仅 32 个 4096 上下文的请求，KV Cache 就能吃掉一张 A100/H100 的大半显存。模型权重之外，<strong>KV Cache 容量往往才是决定能并发多少请求的真正瓶颈</strong>，这也是 GQA/量化/PagedAttention 都在围绕它做文章的原因。</p>
</div>

<div class="card card-s">
<h3>架构层定量收益：MQA / GQA 缩小多少</h3>
<p>KV Cache 大小正比于 <strong>KV head 数</strong>，所以减少 KV head 直接按比例省显存。以 64 个 query head 为例：</p>
<table>
<tr><th>机制</th><th>KV head 数</th><th>相比 MHA</th><th>权衡</th></tr>
<tr><td>MHA</td><td>64（每个 query head 独享）</td><td>1×（基准）</td><td>质量最好，显存压力最大</td></tr>
<tr><td>GQA（Llama-2-70B）</td><td>8（每 8 个 query head 共享 1 组）</td><td>$\frac{8}{64} = \frac{1}{8}$，省 8 倍</td><td>主流折中，质量与效率平衡</td></tr>
<tr><td>MQA</td><td>1（全部 query head 共享 1 组）</td><td>$\frac{1}{64}$，最省</td><td>显存最省，表达力下降可能影响质量</td></tr>
</table>
<p>Llama-2-70B 用 GQA：64 个 query head 共享 8 个 KV head，KV Cache 比标准 MHA 小 8 倍——上面 320 KB/token 若退回 MHA 会膨胀到约 2.5 MB/token。</p>
</div>

<div class="card card-r">
<h3>数值层定量收益：KV Cache 量化的 trade-off</h3>
<p>量化按元素字节数直接缩小 KV Cache：</p>
<table>
<tr><th>精度</th><th>每元素</th><th>相比 FP16</th><th>1.3 GB 请求量化后</th><th>风险</th></tr>
<tr><td>FP16</td><td>2 bytes</td><td>1×</td><td>1.3 GB</td><td>精度稳定，显存大</td></tr>
<tr><td>INT8</td><td>1 byte</td><td>1/2</td><td>≈ 0.65 GB</td><td>显存减半，可能轻微影响质量</td></tr>
<tr><td>INT4</td><td>0.5 byte</td><td>1/4</td><td>≈ 0.33 GB</td><td>降到 1/4，质量风险更高</td></tr>
</table>
<p>难点：decode 每一步都要用历史 K/V 做 attention，误差会沿生成步累积，量化太激进会扰动注意力分布、拉低生成质量。所以 KV 量化是典型 trade-off——通常 INT8 较安全，INT4 需配合 per-channel/group 量化和敏感层保护。</p>
<div class="qa-summary">和权重量化不同：权重量化误差是静态的，KV 量化误差会随 decode 步累积，所以 attention 对 KV 精度更敏感。</div>
</div>

<div class="card card-m">
<h3>三层优化串起来记</h3>
<table>
<tr><th>层面</th><th>方法</th><th>作用</th><th>定量直觉</th></tr>
<tr><td>架构层</td><td>MQA / GQA</td><td>减少 KV head 数</td><td>GQA 省 8 倍，MQA 省 64 倍</td></tr>
<tr><td>数值层</td><td>KV Cache 量化</td><td>降低每元素字节数</td><td>INT8 省 1/2，INT4 省 3/4</td></tr>
<tr><td>系统层</td><td>PagedAttention</td><td>消除预分配浪费和碎片</td><td>按 block 按需分配，逼近真实显存上限</td></tr>
</table>
<p>三者正交、可叠加：先用 GQA 把结构性 KV 降下来，再用量化压每元素字节，最后用 PagedAttention 把分配效率拉满（PagedAttention 细节见「KV Cache 与 Attention」子页）。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: KV Cache 为什么占这么多显存？给个量化的例子。</div>
<div class="qa-a"><p>因为每一层、每个 KV head、每个 token 都要存 K 和 V。大小约为 layers × kv_heads × head_dim × 2 × bytes × seq_len × 并发数。对 Llama-2-70B（80 层、8 个 KV head、head_dim 128、FP16），单 token ≈ 320 KB；4096 上下文一个请求 ≈ 1.3 GB；并发 32 个就 ≈ 41.6 GB。所以 KV Cache 容量常常比权重更先成为并发上限。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 KV Cache 量化比权重量化更需要小心？</div>
<div class="qa-a"><p>权重量化误差是静态的、一次性的；而 KV 在 decode 阶段每一步都被反复读出来做 attention，量化误差会沿生成步累积并扰动注意力分布，越长的序列影响越明显。所以 KV 一般 INT8 较稳，INT4 要配合 per-channel/group 量化、保护敏感层，否则容易掉点。</p></div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
