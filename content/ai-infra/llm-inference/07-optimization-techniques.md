## 一句话结论

推理优化是多层组合：batching 提升吞吐，量化降显存和带宽，投机解码降 decode 步数，prefix cache 复用公共前缀。
<div class="card card-m">
<h3>优化技术：用显存、带宽和调度换延迟/吞吐</h3>
<p>LLM 推理优化不是单一技巧，而是围绕三类资源做权衡：算力、显存和调度队列。高频优化包括 batching、KV cache 管理、量化、投机解码、prefix cache、并行切分和 prefill/decode 分离。</p>
</div>

<div class="card card-s">
<h3>优化手段速查</h3>
<table>
<tr><th>技术</th><th>解决什么问题</th><th>代价</th></tr>
<tr><td>Continuous Batching</td><td>decode 阶段请求长短不一导致 GPU 空洞</td><td>调度器复杂度上升</td></tr>
<tr><td>PagedAttention</td><td>KV cache 连续分配和碎片问题</td><td>需要 block table 管理</td></tr>
<tr><td>Quantization</td><td>降低权重显存和带宽压力</td><td>可能有精度损失和 kernel 适配成本</td></tr>
<tr><td>Speculative Decoding</td><td>降低主模型 decode 次数</td><td>需要 draft model，接受率决定收益</td></tr>
<tr><td>Prefix Cache</td><td>复用相同 prompt 前缀</td><td>cache 命中率和失效策略很关键</td></tr>
</table>
</div>

<div class="card card-d">
<h3>量化显存收益</h3>
<p>权重显存可以粗略估算为：</p>
<div class="formula">$$\text{Weight Memory} = \text{Parameters} \times \text{bytes\_per\_parameter}$$</div>
<p>例如 70B 模型，BF16 权重约 140GB；INT8 约 70GB；INT4 约 35GB。实际还要加 scale、zero point、KV cache 和 workspace。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Continuous Batching 为什么比静态 batching 更适合 LLM decode？</div>
<div class="qa-a"><p><strong>回答思路：</strong>解释输出长度不一致导致静态 batch 浪费。</p><div class="qa-section"><div class="qa-section-title">静态 batching 的问题</div><p>同一 batch 中请求结束时间不同，短请求结束后空位不能立刻补新请求，GPU 会被长尾请求拖住。</p></div><div class="qa-section"><div class="qa-section-title">Continuous batching</div><p>每个 decode step 后调度器可以移除已完成请求并补入新请求，让 batch 持续保持较高利用率。</p></div><div class="qa-summary">面试口径：continuous batching 解决 decode 长短不一带来的空洞，是推理引擎调度器的核心能力。</div></div>
</div>

<div class="card card-m">
<h3>Continuous Batching：从请求级 batch 到 token 级调度</h3>
<p>传统静态 batching 是“凑一批请求，一起跑到全部结束”。LLM decode 的问题是每个请求输出长度不同，短请求结束后位置不能立刻补入新请求，batch 会被长尾请求拖住。Continuous Batching 改成“每个 iteration 都重新调度”：完成的请求退出，等待队列里的新请求进入。</p>
<table>
<tr><th>维度</th><th>静态 Batching</th><th>Continuous Batching</th></tr>
<tr><td>调度粒度</td><td>请求级，一批请求生命周期绑定</td><td>iteration/token 级，每步可增删请求</td></tr>
<tr><td>GPU 利用率</td><td>长尾请求导致空洞</td><td>持续补入新请求，空洞更少</td></tr>
<tr><td>显存管理</td><td>常按最大长度预留</td><td>结合 PagedAttention 按 block 动态分配</td></tr>
<tr><td>公平性</td><td>简单但不灵活</td><td>需要处理抢占、优先级、max token budget</td></tr>
</table>
<p>推理调度器每一轮通常要回答：哪些 running request 继续 decode？哪些 waiting request 可以 prefill？本轮 token budget 是否够？KV block 是否够？是否要优先短请求或高优请求？</p>
</div>

<div class="card card-d">
<h3>Prefill 与 Decode 共存时如何平衡延迟和吞吐？</h3>
<p>Prefill 和 Decode 的资源特征不同：Prefill 处理完整 prompt，矩阵乘大，更偏 compute-bound，影响 TTFT；Decode 每步生成一个 token，读取 KV Cache 和权重，更偏 memory-bound，影响 TPOT 和流式体验。两者混跑时，长 prefill 会阻塞 decode，导致正在生成的用户卡顿；只服务 decode 又会让新请求 TTFT 过高。</p>
<table>
<tr><th>策略</th><th>做法</th><th>解决问题</th><th>代价</th></tr>
<tr><td>Chunked Prefill</td><td>把长 prompt prefill 切成多个 chunk，在 decode iteration 间穿插执行</td><td>避免长 prefill 独占 GPU，降低 decode 抖动</td><td>prefill 总完成时间可能变长，调度更复杂</td></tr>
<tr><td>Token Budget</td><td>每轮限制 prefill tokens + decode tokens 的总量</td><td>控制单轮延迟，避免某类请求挤占全部预算</td><td>预算设太小会降低吞吐</td></tr>
<tr><td>Decode 优先</td><td>优先保证 running requests 的 decode step，再塞 prefill</td><td>保护 TPOT/P99，流式输出更稳定</td><td>新请求 TTFT 可能上升</td></tr>
<tr><td>Prefill/Decode 分离</td><td>不同 GPU 池分别处理 prefill 和 decode，通过网络传 KV Cache</td><td>按阶段特征独立扩缩容</td><td>KV cache 迁移依赖 RDMA/高速网络</td></tr>
<tr><td>优先级队列</td><td>短 prompt、高优用户、交互式请求优先</td><td>改善 P95/P99 体验</td><td>低优长请求可能饥饿，需要 aging</td></tr>
</table>
<p>面试口径：<strong>Prefill 优化 TTFT，Decode 优化 TPOT。调度策略要避免长 prefill 破坏 decode 的稳定节奏，所以常用 chunked prefill + decode-prioritized token budget。</strong></p>
</div>

<div class="card card-s">
<h3>Speculative Decoding 下的调度变化</h3>
<p>Speculative Decoding 用小 draft model 先生成多个候选 token，再由大 target model 一次性验证。它减少 target model 的 decode step 数，但会引入新的调度问题：draft 与 target 的资源怎么配比？接受率低时是否值得继续 spec？验证 batch 如何与普通 decode 混排？</p>
<table>
<tr><th>问题</th><th>调度关注点</th></tr>
<tr><td>Draft model 放哪里</td><td>可以和 target 共卡，也可以独立小卡；共卡会抢显存和算力，独立部署增加通信</td></tr>
<tr><td>一次 draft 几个 token</td><td>k 越大，潜在加速越高，但验证失败浪费越多</td></tr>
<tr><td>接受率波动</td><td>接受率低时 spec 收益下降，调度器可动态降低 spec 长度或回退普通 decode</td></tr>
<tr><td>KV Cache 管理</td><td>被拒绝 token 的临时 KV 需要回收；接受 token 才提交到正式序列</td></tr>
<tr><td>公平性</td><td>spec 请求一次可能推进多个 token，普通请求一次只推进一个 token，需要 token-level 公平</td></tr>
</table>
<p>回答时可以说：Speculative Decoding 把调度单位从“每请求每轮 1 token”扩展成“draft 多 token + target 验证”，所以调度器要看接受率、draft/target 资源占用和 token-level fairness。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: vLLM 的 Continuous Batching 为什么依赖 PagedAttention？</div>
<div class="qa-a"><p>Continuous Batching 每一轮都会让请求进入和退出。如果 KV Cache 必须连续预留，频繁进出会造成严重显存碎片，并且新请求可能因为没有连续空间而无法进入。PagedAttention 把 KV Cache 切成固定 block，请求退出后释放 block，新请求按需拿 block，不要求物理连续，因此能支撑高频 iteration-level scheduling。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Chunked Prefill 会不会牺牲 TTFT？为什么还要用？</div>
<div class="qa-a"><p>会有可能。长 prompt 被切成多个 chunk 后，单个请求的 prefill 完成时间可能变长；但它避免一个长 prefill 独占 GPU，保护其他 running request 的 decode TPOT 和 P99。在线服务通常不是只优化单个请求 TTFT，而是同时优化全局吞吐、TTFT 和流式 decode 稳定性。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Prefill/Decode 调度策略怎么设计？</div>
<div class="qa-a"><p>可以设计一个 decode-prioritized token budget：每轮先给 running requests 分配 decode token，保证 TPOT；剩余预算给 waiting requests 做 prefill。长 prompt 走 chunked prefill，避免阻塞；高优请求或短 prompt 可以提高 prefill 优先级；当 decode 队列过长时暂停新 prefill，防止流式输出抖动。</p></div>
</div>

<div class="card card-s">
<h3>参考资料</h3>
<ul>
<li>vLLM 官方 Anatomy 文章：覆盖 scheduler、PagedAttention、continuous batching、chunked prefill、prefix cache、speculative decoding 和 disaggregated P/D。</li>
<li>vLLM internals 资料：解释 waiting/running 队列、SchedulerOutput、KV block pool 和 continuous batching 的具体机制。</li>
</ul>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
