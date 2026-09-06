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
<p>$$80 \times 8 \times 128 \times 2 \times 2 = 327{,}680\ \text{bytes} \approx 320\ \text{KiB/token}$$</p>
<div class="qa-summary">关键：这只是<strong>一个 token</strong> 的 KV Cache，而且这是已经用 GQA（8 个 KV head）压过的结果。</div>
</div>

<div class="card card-w">
<h3>从单 token 放大到并发服务：显存压力来源</h3>
<p>把单 token 乘上序列长度和并发请求数，显存占用迅速膨胀：</p>
<table>
<tr><th>规模</th><th>计算</th><th>KV Cache</th></tr>
<tr><td>1 token</td><td>—</td><td>320 KiB</td></tr>
<tr><td>1 请求 · 4096 上下文</td><td>$4096 \times 320\ \text{KiB}$</td><td>1.25 GiB</td></tr>
<tr><td>32 并发请求</td><td>$32 \times 1.25\ \text{GiB}$</td><td>40 GiB</td></tr>
</table>
<p>使用二进制单位精确计算，每 token 为 320 KiB，4096 token 为 1.25 GiB，32 个请求共 40 GiB（约 42.95 GB）。这里是模型全层、所有 KV heads 的总量，不一定落在一张卡上。若 TP=8 且 KV heads 均匀分片、没有复制，每卡约 5 GiB；还要另算权重、激活和工作区。<strong>并发容量应按最吃紧的 rank 计算。</strong></p>
</div>

<div class="card card-s">
<h3>架构层定量收益：MQA / GQA 缩小多少</h3>
<p>KV Cache 大小正比于 <strong>KV head 数</strong>，所以减少 KV head 直接按比例省显存。以 64 个 query head 为例：</p>
<table>
<tr><th>机制</th><th>KV head 数</th><th>相比 MHA</th><th>权衡</th></tr>
<tr><td>MHA</td><td>64（每个 query head 独享）</td><td>1×（基准）</td><td>表达容量较大，显存压力大；质量依赖模型与训练</td></tr>
<tr><td>GQA（Llama-2-70B）</td><td>8（每 8 个 query head 共享 1 组）</td><td>$\frac{8}{64} = \frac{1}{8}$，省 8 倍</td><td>主流折中，质量与效率平衡</td></tr>
<tr><td>MQA</td><td>1（全部 query head 共享 1 组）</td><td>$\frac{1}{64}$，最省</td><td>显存最省，表达力下降可能影响质量</td></tr>
</table>
<p>Llama-2-70B 用 GQA：64 个 query head 共享 8 个 KV head，KV Cache 比标准 MHA 小 8 倍——上面 320 KiB/token 若退回 MHA 会膨胀到2.5 MiB/token。</p>
</div>

<div class="card card-r">
<h3>数值层定量收益：KV Cache 量化的 trade-off</h3>
<p>量化按元素字节数直接缩小 KV Cache：</p>
<table>
<tr><th>精度</th><th>每元素</th><th>相比 FP16</th><th>1.25 GiB 请求量化后</th><th>风险</th></tr>
<tr><td>FP16</td><td>2 bytes</td><td>1×</td><td>1.25 GiB</td><td>精度稳定，显存大</td></tr>
<tr><td>INT8</td><td>1 byte</td><td>1/2</td><td>0.625 GiB</td><td>显存减半，可能轻微影响质量</td></tr>
<tr><td>INT4</td><td>0.5 byte</td><td>1/4</td><td>0.3125 GiB</td><td>降到 1/4，质量风险更高</td></tr>
</table>
<p>难点：decode 每一步都要用历史 K/V 做 attention，误差会沿生成步累积，量化太激进会扰动注意力分布、拉低生成质量。所以 KV 量化是典型 trade-off——通常 INT8 较安全，INT4 需配合 per-channel/group 量化和敏感层保护。</p>
<p>权重和 KV 的量化误差都会影响后续前向与生成，不能仅凭“静态权重、动态 KV”判断谁必然更敏感。应结合精度、量化粒度、kernel 和任务质量评测；参见 <a href="https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/">vLLM KV 量化说明</a>。</p>
</div>

<div class="card card-m">
<h3>三层优化串起来记</h3>
<table>
<tr><th>层面</th><th>方法</th><th>作用</th><th>定量直觉</th></tr>
<tr><td>架构层</td><td>MQA / GQA</td><td>减少 KV head 数</td><td>GQA 省 8 倍，MQA 省 64 倍</td></tr>
<tr><td>数值层</td><td>KV Cache 量化</td><td>降低每元素字节数</td><td>INT8 省 1/2，INT4 省 3/4</td></tr>
<tr><td>系统层</td><td>PagedAttention</td><td>减少预分配浪费和碎片</td><td>按 block 按需分配，逼近真实显存上限</td></tr>
</table>
<p>三者正交、可叠加：先用 GQA 把结构性 KV 降下来，再用量化压每元素字节，最后用 PagedAttention 把分配效率拉满。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: KV Cache 为什么占这么多显存？给个量化的例子。</div>
<div class="qa-a"><p>因为每一层、每个 KV head、每个 token 都要存 K 和 V。大小约为 layers × kv_heads × head_dim × 2 × bytes × seq_len × 并发数。对 Llama-2-70B（80 层、8 个 KV head、head_dim 128、FP16），单 token ≈ 320 KiB；4096 上下文一个请求 1.25 GiB；并发 32 个就 40 GiB。这是全模型 KV 总量，单卡占用还取决于 TP/PP 分片和复制；并发预算须加上权重与运行时开销。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 KV Cache 量化比权重量化更需要小心？</div>
<div class="qa-a"><p>不能笼统说 KV 一定比权重量化更敏感。K 的误差可能改变注意力分布，V 的误差影响加权输出，而权重量化也影响每一步前向。需要在目标上下文长度和任务上比较质量、显存与延迟，结合量化尺度、异常值和后端支持选择精度，不能默认 INT8 无损或 INT4 必然不可用。</p></div>
</div>
