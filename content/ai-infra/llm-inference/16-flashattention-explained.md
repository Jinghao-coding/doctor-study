## 一句话结论

FlashAttention 的本质是 tiling + online softmax，让 attention 中间大矩阵不落 HBM。
<div class="card card-m">
<h3>一句话先抓住本质</h3>
<p>FlashAttention <strong>不减少 attention 的计算量（FLOPs 一点没少，甚至略增）</strong>，它减少的是 GPU 显存（HBM）的读写次数。因为标准 attention 是 <strong>memory-bound</strong>——瓶颈在搬数据而不是算数据，所以“少搬数据”比“少算”更能加速。它是<strong>精确</strong>的，结果和标准 attention 完全一致，不是近似。</p>
<div class="qa-summary">记忆口径：不省计算、只省 HBM 读写；精确而非近似；手段是 tiling + online softmax + kernel fusion。</div>
</div>

<div class="card card-r">
<h3>先讲清楚标准 Attention 慢在哪</h3>
<p>标准实现里，<code>QKᵀ</code> 会先算出一个 <code>seq_len × seq_len</code> 的注意力分数矩阵。长序列下这个矩阵非常大（比如 seq_len=4096 就是 4096×4096）。它要被<strong>写到 HBM</strong>，Softmax 再<strong>从 HBM 读回来</strong>处理、写回去，最后再读出来跟 V 做矩阵乘。中间这个大矩阵在 HBM 上来回读写好几趟。</p>
<p>问题是 attention 本身<strong>算术强度低</strong>：相对于要搬运的数据量，真正做的浮点运算并不多。于是时间几乎全花在 HBM 读写上，GPU 的算力单元大量空闲。</p>

<div class="pa-fig">
<svg viewBox="0 0 640 230" role="img" aria-label="标准 Attention 示意图：巨大的 QK^T 中间矩阵在 HBM 上反复读写">
<defs>
<marker id="faArrowHot" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="var(--danger)"></path>
</marker>
</defs>
<text x="20" y="28" class="pa-title">标准 Attention：大矩阵在 HBM 来回读写</text>

<rect x="30" y="60" width="150" height="120" class="pa-slot"></rect>
<text x="105" y="50" text-anchor="middle" class="pa-label">HBM（显存，大但慢）</text>
<rect x="50" y="80" width="110" height="36" class="pa-slot-waste"></rect>
<text x="105" y="98" text-anchor="middle" class="pa-mono" fill="var(--danger-h)">S = QKᵀ</text>
<text x="105" y="111" text-anchor="middle" class="pa-sub" fill="var(--danger-h)">seq×seq 巨大矩阵</text>
<rect x="50" y="128" width="110" height="36" class="pa-slot-waste"></rect>
<text x="105" y="150" text-anchor="middle" class="pa-mono" fill="var(--danger-h)">softmax(S)</text>

<rect x="420" y="80" width="190" height="80" class="pa-slot-sram"></rect>
<text x="515" y="70" text-anchor="middle" class="pa-label">计算单元 / SRAM（小但快）</text>
<text x="515" y="118" text-anchor="middle" class="pa-mono" fill="var(--sec-h)">算一步就把结果</text>
<text x="515" y="134" text-anchor="middle" class="pa-mono" fill="var(--sec-h)">写回 HBM，再读回</text>

<path class="fa-arrow-hot" d="M180,100 L418,100"></path>
<path class="fa-arrow-hot" d="M418,140 L182,140"></path>
<text x="300" y="92" text-anchor="middle" class="pa-sub" fill="var(--danger-h)">写出 S / softmax 结果 →</text>
<text x="300" y="158" text-anchor="middle" class="pa-sub" fill="var(--danger-h)">← 再读回做下一步</text>

<text x="20" y="208" class="pa-sub">红色箭头是昂贵的 HBM 读写。大矩阵被反复搬运，时间花在搬数据上 → memory-bound。</text>
<text x="20" y="225" class="pa-sub">显存占用也是 O(seq²)：要保存整个分数矩阵，长序列下显存压力很大。</text>
</svg>
</div>
</div>

<div class="card card-s">
<h3>什么是 tiling（分块）</h3>
<p>tiling 就是<strong>把一个大矩阵切成一格一格的小块，分批处理，而不是一次性整体处理</strong>。这个词来自“铺瓷砖”——一面大墙不是一整块，而是用许多小瓷砖拼起来。</p>
<p>为什么要切？因为 SRAM 容量极小（KB~MB 级），整个 <code>seq×seq</code> 的注意力矩阵（4096×4096 可能上百 MB）根本塞不进去。但如果只取 Q 的一小段行、K/V 的一小段，它们的乘积就是一个<strong>能装进 SRAM 的小块</strong>。于是把大矩阵乘法拆成“逐个小块计算、累加结果”：每次只搬一小块进 SRAM 算，算完丢弃中间结果、只留累加值，再搬下一块。</p>

<div class="pa-fig">
<svg viewBox="0 0 640 230" role="img" aria-label="tiling 示意图：把大的 QK 矩阵切成小块，每次只处理一块">
<text x="20" y="26" class="pa-title">tiling：把大矩阵切成能塞进 SRAM 的小块逐块算</text>

<text x="70" y="56" text-anchor="middle" class="pa-label">整块大矩阵 S = QKᵀ</text>
<rect x="40" y="66" width="120" height="120" class="pa-slot-waste"></rect>
<text x="100" y="120" text-anchor="middle" class="pa-mono" fill="var(--danger-h)">seq × seq</text>
<text x="100" y="138" text-anchor="middle" class="pa-sub" fill="var(--danger-h)">太大，装不进 SRAM</text>

<text x="300" y="120" text-anchor="middle" class="pa-title">切块</text>
<path class="fa-arrow" d="M250,126 L350,126"></path>

<text x="500" y="56" text-anchor="middle" class="pa-label">切成小块，逐块进 SRAM 算</text>
<rect x="420" y="66" width="38" height="38" class="pa-blk-b"></rect>
<rect x="462" y="66" width="38" height="38" class="pa-blk-b"></rect>
<rect x="504" y="66" width="38" height="38" class="pa-blk-c"></rect>
<rect x="546" y="66" width="38" height="38" class="pa-slot-free"></rect>
<rect x="420" y="108" width="38" height="38" class="pa-blk-c"></rect>
<rect x="462" y="108" width="38" height="38" class="pa-slot-free"></rect>
<rect x="504" y="108" width="38" height="38" class="pa-blk-b"></rect>
<rect x="546" y="108" width="38" height="38" class="pa-blk-c"></rect>
<rect x="420" y="150" width="38" height="38" class="pa-slot-free"></rect>
<rect x="462" y="150" width="38" height="38" class="pa-blk-c"></rect>
<rect x="504" y="150" width="38" height="38" class="pa-blk-b"></rect>
<rect x="546" y="150" width="38" height="38" class="pa-blk-b"></rect>
<text x="500" y="210" text-anchor="middle" class="pa-sub">每个小块单独装进 SRAM，算完只保留累加结果，再换下一块</text>
</svg>
</div>
<div class="qa-summary">一句话：tiling = 把装不下的大矩阵乘法，拆成一格一格装得下的小块，逐块算、累加。它是几乎所有 GPU 高性能 kernel（不只 attention）的通用手段。</div>
</div>

<div class="card card-d">
<h3>核心做法：tiling + online softmax，让大矩阵永不落 HBM</h3>
<p>FlashAttention 把 Q、K、V 切成小块（tile），每次只把一小块加载进 <strong>SRAM</strong>（GPU 片上缓存，带宽比 HBM 高一到两个数量级），在 SRAM 里就地算完这一块的局部 attention。靠 <strong>online softmax</strong>（在线增量更新 softmax 的最大值和分母）的数学技巧，<strong>不需要先算出完整 QKᵀ 再做 softmax</strong>，而是一块一块累加出最终结果。</p>
<p>于是那个巨大的中间矩阵<strong>从头到尾不写回 HBM</strong>，始终在 SRAM 上被就地消费掉。HBM 上只读一次 Q/K/V、写一次输出。</p>

<div class="pa-fig">
<svg viewBox="0 0 640 250" role="img" aria-label="FlashAttention 示意图：Q/K/V 分块加载进 SRAM，中间矩阵不写回 HBM">
<defs>
<marker id="faArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="var(--border-2)"></path>
</marker>
</defs>
<text x="20" y="28" class="pa-title">FlashAttention：分块进 SRAM，中间矩阵就地消费</text>

<rect x="30" y="60" width="150" height="150" class="pa-slot"></rect>
<text x="105" y="50" text-anchor="middle" class="pa-label">HBM（只读 Q/K/V，写一次输出）</text>
<rect x="48" y="74" width="50" height="30" class="pa-blk-a"></rect>
<text x="73" y="93" text-anchor="middle" class="pa-blk-txt-a">Q块</text>
<rect x="104" y="74" width="50" height="30" class="pa-blk-b"></rect>
<text x="129" y="93" text-anchor="middle" class="pa-blk-txt-b">K块</text>
<rect x="48" y="110" width="50" height="30" class="pa-blk-c"></rect>
<text x="73" y="129" text-anchor="middle" class="pa-blk-txt-c">V块</text>
<rect x="104" y="156" width="50" height="30" class="pa-slot"></rect>
<text x="129" y="175" text-anchor="middle" class="pa-mono" fill="var(--txt)">输出</text>

<rect x="400" y="60" width="210" height="150" class="pa-slot-sram"></rect>
<text x="505" y="50" text-anchor="middle" class="pa-label">SRAM（片上，极快）</text>
<text x="505" y="100" text-anchor="middle" class="pa-mono" fill="var(--sec-h)">局部 QKᵀ → 局部 softmax</text>
<text x="505" y="120" text-anchor="middle" class="pa-mono" fill="var(--sec-h)">→ 乘局部 V → 在线累加</text>
<text x="505" y="148" text-anchor="middle" class="pa-sub" fill="var(--sec-h)">大矩阵只在这里出现，</text>
<text x="505" y="164" text-anchor="middle" class="pa-sub" fill="var(--sec-h)">永不写回 HBM</text>

<path class="fa-arrow" d="M180,110 L398,110"></path>
<text x="290" y="102" text-anchor="middle" class="pa-sub">逐块加载 Q/K/V →</text>
<path class="fa-arrow" d="M398,170 L182,170"></path>
<text x="290" y="188" text-anchor="middle" class="pa-sub">← 全部块累加完，只写一次输出</text>

<text x="20" y="238" class="pa-sub">HBM 读写从“反复搬大矩阵”降到“读一遍 Q/K/V + 写一遍输出”，显存占用从 O(seq²) 降到 O(seq)。</text>
</svg>
</div>
</div>

<div class="card card-s">
<h3>为什么 SRAM 这么关键：GPU 存储层级</h3>
<p>FlashAttention 的全部收益建立在“SRAM 比 HBM 快得多”这个事实上。GPU 存储是金字塔：越靠近计算单元越快、越小。</p>
<table>
<tr><th>层级</th><th>速度/带宽</th><th>容量</th><th>角色</th></tr>
<tr><td>寄存器 / SRAM（片上）</td><td>极快（比 HBM 高 1–2 个数量级）</td><td>很小（KB~MB 级）</td><td>FlashAttention 在这里算局部 attention</td></tr>
<tr><td>HBM（显存）</td><td>快但远不如 SRAM</td><td>大（GB 级）</td><td>放权重、KV Cache、输入输出</td></tr>
</table>
<p>把中间矩阵留在 SRAM、避免落 HBM，就是把工作从“慢通道”挪到“快通道”。这种“针对数据搬运而非计算做优化”的思路，论文里叫 <strong>IO-Awareness</strong>。</p>
</div>

<div class="card card-w">
<h3>面试经典追问（区分“背答案”和“真懂”的试金石）</h3>
<div class="qa-summary">追问：“FlashAttention 实际 FLOPs 比标准 Attention 还高（反向传播要重计算），为什么反而更快？”</div>
<p>标准答法：<strong>因为 attention 是 memory-bound 操作，瓶颈在数据搬运量而不是计算量。</strong>FlashAttention 用少量额外计算，换来大幅减少的 HBM 读写；在 memory-bound 场景下，这笔买卖是划算的。</p>
<p>能这样回答，说明你真正理解了 <strong>Roofline 模型</strong>的思维：compute-bound 的操作想办法提高计算效率，memory-bound 的操作想办法减少数据搬运。AI Infra 里绝大部分优化，本质都是先用 Roofline 分析瓶颈，再对症下药。更完整的 FLOPs 推导、算术强度和逐算子 bound 分类已经迁到「Transformer 与大模型基础」里的「计算分析」分组。</p>
</div>

<div class="card card-m">
<h3>FlashAttention-2 相比 V1 的改进</h3>
<ul>
<li><strong>减少非矩阵乘运算 + 置换内外循环</strong>：GPU 上非 matmul 运算吞吐远低于 matmul，减少它能提速；配合调整循环顺序减少重复 rescaling。</li>
<li><strong>增加并行维度</strong>：在 seq_len 维度上也做并行，让 SM（流多处理器）利用率打满，不只在 batch×head 上并行。</li>
<li><strong>优化 warp 级工作划分</strong>：减少 warp 之间的通信和对 shared memory 的读写次数。</li>
</ul>
<p>一句话：V1 解决“要不要落 HBM”，V2 在“怎么把 GPU 算得更满”上继续抠。</p>
</div>

<div class="card card-d">
<h3>三个易混技术的边界</h3>
<table>
<tr><th>技术</th><th>解决什么</th><th>作用对象</th></tr>
<tr><td>FlashAttention</td><td>降低 attention 中间矩阵的 HBM 读写</td><td>attention kernel 的计算与访存</td></tr>
<tr><td>PagedAttention</td><td>降低 KV Cache 的显存浪费和碎片</td><td>KV Cache 的存储与分配</td></tr>
<tr><td>GQA / MQA</td><td>从模型结构上减少 KV head 数</td><td>KV Cache 的总量</td></tr>
</table>
<p>三者正交、可同时使用：FlashAttention 优化“算 attention 时怎么访存”，PagedAttention 优化“KV Cache 怎么存放”，GQA/MQA 优化“KV Cache 有多大”。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 用一句话讲 FlashAttention 的原理，以及它为什么能加速。</div>
<div class="qa-a"><p>标准 attention 要把巨大的 QKᵀ 中间矩阵反复写读 HBM，而 attention 是 memory-bound 的，瓶颈在搬数据。FlashAttention 用 tiling 把 Q/K/V 分块加载进 SRAM，靠 online softmax 增量计算，让中间矩阵永不落 HBM，从而把 HBM 读写从 O(seq²) 级降下来。它没减少 FLOPs（甚至略增），但大幅减少了 HBM 访问，所以在 memory-bound 场景下更快；并且结果精确，不是近似。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: FlashAttention 和 PagedAttention 是一回事吗？</div>
<div class="qa-a"><p>不是。FlashAttention 是 attention kernel 的计算/访存优化，目标是减少中间矩阵的 HBM 读写；PagedAttention 是 KV Cache 的存储管理（虚拟内存式分页），目标是减少显存浪费和碎片。两者解决不同问题、作用在不同环节，可以同时使用。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: online softmax 为什么能让 attention 增量计算？</div>
<div class="qa-a"><p>普通 softmax 要先看到一整行分数才能算分母（所有 exp 之和）和最大值。online softmax 维护“当前见过的最大值”和“当前累计分母”，每来一个新块就按数值稳定的方式更新这两个量，并对已累加的输出做相应 rescale。这样不需要先凑齐整行，就能一块一块累加出和标准 softmax 完全相同的结果——这是中间矩阵不必落 HBM 的数学前提。</p></div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
