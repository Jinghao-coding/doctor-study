## 一句话结论

PagedAttention 把 KV cache 从连续大块分配变成 block table 映射，核心价值是减少碎片和支持 continuous batching。
<div class="card card-m">
<h3>一句话先抓住本质</h3>
<p>PagedAttention <strong>不是一种 attention 算法</strong>，而是 vLLM 给 KV Cache 设计的一套<strong>“虚拟内存”管理系统</strong>。它把 KV Cache 切成固定大小的小块（block），让一个请求逻辑上看到连续的 token 序列，物理显存里却可以散落在任意位置——和操作系统用分页管理内存是同一个思路。</p>
<div class="qa-summary">类比一句话：PagedAttention 之于 KV Cache，就像操作系统分页之于进程内存。</div>
</div>

<div class="card card-r">
<h3>它要解决的痛点：传统连续分配的两种浪费</h3>
<p>传统做法是给每个请求<strong>预分配一整块连续显存</strong>，按支持的最大长度（比如 4096）预留。问题是大多数请求根本用不到最大长度。</p>
<p>下图：系统支持 4096 token，但请求 A 只生成了 800 token。预留的连续大块里，绝大部分是被白白占住、又不能给别人用的浪费。</p>

<div class="pa-fig">
<svg viewBox="0 0 640 220" role="img" aria-label="传统连续分配示意图：请求按最大长度预留显存，实际只用一小部分，其余浪费">
<defs>
<marker id="paArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="var(--border-2)"></path>
</marker>
</defs>
<text x="20" y="30" class="pa-title">传统连续分配（pre-allocation）</text>

<text x="20" y="62" class="pa-label">请求 A 预留的连续显存（按 max_len = 4096 预留）</text>

<rect x="20" y="74" width="120" height="44" class="pa-slot"></rect>
<text x="80" y="101" text-anchor="middle" class="pa-mono" fill="var(--txt)">已用 800</text>

<rect x="140" y="74" width="480" height="44" class="pa-slot-waste"></rect>
<text x="380" y="95" text-anchor="middle" class="pa-mono" fill="var(--danger-h)">预留但未使用 ≈ 3296 token</text>
<text x="380" y="110" text-anchor="middle" class="pa-sub" fill="var(--danger-h)">这段显存被占住，别的请求也用不了 → 内部浪费</text>

<text x="20" y="160" class="pa-label">显存里多个请求结束后：留下大小不一的空洞</text>
<rect x="20" y="172" width="90" height="34" class="pa-slot"></rect>
<text x="65" y="193" text-anchor="middle" class="pa-mono" fill="var(--txt)">占用</text>
<rect x="110" y="172" width="60" height="34" class="pa-slot-free"></rect>
<rect x="170" y="172" width="120" height="34" class="pa-slot"></rect>
<text x="230" y="193" text-anchor="middle" class="pa-mono" fill="var(--txt)">占用</text>
<rect x="290" y="172" width="40" height="34" class="pa-slot-free"></rect>
<rect x="330" y="172" width="80" height="34" class="pa-slot"></rect>
<text x="370" y="193" text-anchor="middle" class="pa-mono" fill="var(--txt)">占用</text>
<rect x="410" y="172" width="70" height="34" class="pa-slot-free"></rect>
<rect x="480" y="172" width="140" height="34" class="pa-slot"></rect>
<text x="550" y="193" text-anchor="middle" class="pa-mono" fill="var(--txt)">占用</text>
<text x="20" y="220" class="pa-sub">虚线是空闲碎片：加起来够大，但不连续，新请求要一大块连续空间时进不来 → 外部碎片</text>
</svg>
</div>

<table>
<tr><th>浪费类型</th><th>怎么产生</th><th>后果</th></tr>
<tr><td>内部浪费</td><td>按 max_len 预留，实际只用一小段</td><td>大量预留显存闲置，并发数被压低</td></tr>
<tr><td>外部碎片</td><td>请求结束释放后留下大小不一的空洞</td><td>空闲总量够、但拼不出连续大块，新请求进不来</td></tr>
</table>
</div>

<div class="card card-d">
<h3>核心做法：切成 block + 用 block table 做映射</h3>
<p>PagedAttention 把 KV Cache 切成<strong>固定大小的 block</strong>（vLLM 默认每块放 16 个 token 的 K/V）。请求需要多少 token，就按需领多少 block，不要求这些 block 在显存里连续。一张 <strong>block table</strong>（相当于页表）记录“逻辑第几块 → 物理哪个 block”。</p>

<div class="pa-fig">
<svg viewBox="0 0 640 300" role="img" aria-label="PagedAttention 映射示意图：逻辑连续的 token 序列经 block table 映射到物理上不连续的 KV block">
<defs>
<marker id="paArrowAcc" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="var(--acc)"></path>
</marker>
</defs>

<text x="20" y="28" class="pa-title">逻辑视图（请求看到的连续 KV 序列）</text>
<rect x="20" y="40" width="100" height="40" class="pa-blk-a"></rect>
<text x="70" y="60" text-anchor="middle" class="pa-blk-txt-a">逻辑块 0</text>
<text x="70" y="74" text-anchor="middle" class="pa-sub">token 0–15</text>
<rect x="124" y="40" width="100" height="40" class="pa-blk-a"></rect>
<text x="174" y="60" text-anchor="middle" class="pa-blk-txt-a">逻辑块 1</text>
<text x="174" y="74" text-anchor="middle" class="pa-sub">token 16–31</text>
<rect x="228" y="40" width="100" height="40" class="pa-blk-a"></rect>
<text x="278" y="60" text-anchor="middle" class="pa-blk-txt-a">逻辑块 2</text>
<text x="278" y="74" text-anchor="middle" class="pa-sub">token 32–47</text>

<text x="360" y="28" class="pa-title">block table（页表）</text>
<rect x="360" y="40" width="260" height="40" class="pa-slot"></rect>
<text x="370" y="58" class="pa-mono" fill="var(--txt)">逻辑0→物理7  逻辑1→物理2</text>
<text x="370" y="73" class="pa-mono" fill="var(--txt)">逻辑2→物理5</text>

<text x="20" y="150" class="pa-title">物理显存（GPU 上的 KV block 池，顺序无所谓）</text>
<rect x="20" y="165" width="70" height="44" class="pa-slot-free"></rect>
<text x="55" y="191" text-anchor="middle" class="pa-mono" fill="var(--muted)">#1 空</text>
<rect x="94" y="165" width="70" height="44" class="pa-blk-a"></rect>
<text x="129" y="187" text-anchor="middle" class="pa-blk-txt-a">#2</text>
<text x="129" y="200" text-anchor="middle" class="pa-sub">逻辑1</text>
<rect x="168" y="165" width="70" height="44" class="pa-slot-free"></rect>
<text x="203" y="191" text-anchor="middle" class="pa-mono" fill="var(--muted)">#3 空</text>
<rect x="242" y="165" width="70" height="44" class="pa-slot-free"></rect>
<text x="277" y="191" text-anchor="middle" class="pa-mono" fill="var(--muted)">#4 空</text>
<rect x="316" y="165" width="70" height="44" class="pa-blk-a"></rect>
<text x="351" y="187" text-anchor="middle" class="pa-blk-txt-a">#5</text>
<text x="351" y="200" text-anchor="middle" class="pa-sub">逻辑2</text>
<rect x="390" y="165" width="70" height="44" class="pa-slot-free"></rect>
<text x="425" y="191" text-anchor="middle" class="pa-mono" fill="var(--muted)">#6 空</text>
<rect x="464" y="165" width="70" height="44" class="pa-blk-a"></rect>
<text x="499" y="187" text-anchor="middle" class="pa-blk-txt-a">#7</text>
<text x="499" y="200" text-anchor="middle" class="pa-sub">逻辑0</text>
<rect x="538" y="165" width="70" height="44" class="pa-slot-free"></rect>
<text x="573" y="191" text-anchor="middle" class="pa-mono" fill="var(--muted)">#8 空</text>

<path class="pa-arrow-map" d="M70,80 C70,120 499,120 499,163"></path>
<path class="pa-arrow-map" d="M174,80 C174,115 129,120 129,163"></path>
<path class="pa-arrow-map" d="M278,80 C278,118 351,120 351,163"></path>

<text x="20" y="246" class="pa-sub">逻辑上 token 0→47 是连着的；物理上它们落在 #7 / #2 / #5 三个不相邻的 block。</text>
<text x="20" y="266" class="pa-sub">attention kernel 读 KV 时先查 block table，再去对应物理 block 取数，所以“不连续”不影响正确性。</text>
<text x="20" y="286" class="pa-sub">请求每多写满 16 个 token，就再领一个空闲 block；请求结束，三个 block 直接还回池子，立刻能给别人用。</text>
</svg>
</div>
</div>

<div class="card card-s">
<h3>和操作系统分页一一对应</h3>
<p>如果你学过操作系统的虚拟内存，PagedAttention 几乎就是把同一套机制搬到了 GPU 显存上：</p>
<table>
<tr><th>操作系统虚拟内存</th><th>PagedAttention</th></tr>
<tr><td>进程看到的连续虚拟地址空间</td><td>请求看到的连续 KV / token 序列</td></tr>
<tr><td>物理内存页（page）</td><td>固定大小的 KV block（默认 16 token）</td></tr>
<tr><td>页表（page table）</td><td>block table</td></tr>
<tr><td>按需分配物理页（缺页时分配）</td><td>写满一块才领下一个 block</td></tr>
<tr><td>分页消除外部碎片</td><td>非连续 block 可组合，消除 KV 显存碎片</td></tr>
<tr><td>共享内存页 / copy-on-write</td><td>多请求共享公共 prompt 前缀（prefix cache、引用计数 + COW）</td></tr>
</table>
</div>

<div class="card card-w">
<h3>一个具体例子：从 800 token 看收益</h3>
<p>设 block = 16 token，请求 A 实际生成 800 token：</p>
<ul>
<li><strong>传统连续分配</strong>：按 max_len 4096 预留连续显存，相当于占住 256 个 block 的空间，但只用了其中约 50 个，<strong>约 80% 预留显存被浪费</strong>，且整段必须连续。</li>
<li><strong>PagedAttention</strong>：只领 <code>⌈800 / 16⌉ = 50</code> 个 block，其余显存留给别的请求；这 50 个 block 还不必相邻。生成超过 800 时再继续领，结束后 50 个 block 全部还池。</li>
</ul>
<div class="qa-summary">同样的显存，PagedAttention 能塞下多得多的并发请求——因为没有人再为“可能用到的最大长度”提前占坑。这正是 vLLM 吞吐高的关键基础之一。</div>
</div>

<div class="card card-m">
<h3>为什么它是 continuous batching 的地基</h3>
<p>continuous batching 要让请求<strong>每一轮 decode 都能动态进出 batch</strong>。如果 KV Cache 还要求连续预留，请求频繁进出会立刻把显存搅成碎片，新请求常常因为“没有连续空间”而进不来。PagedAttention 把分配粒度降到固定大小的 block：请求退出就还 block，新请求按需领 block，<strong>永远不需要连续大块</strong>，于是高频的 iteration-level 调度才跑得稳。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 用一句话解释 PagedAttention，再说它解决什么问题。</div>
<div class="qa-a"><p>PagedAttention 是 vLLM 借鉴操作系统分页、给 KV Cache 做的虚拟内存管理：把 KV Cache 切成固定大小的 block，逻辑连续、物理可不连续，用 block table 维护映射。它解决两件事——预分配按最大长度预留造成的<strong>内部浪费</strong>，以及请求进出留下空洞造成的<strong>外部碎片</strong>，从而提升显存利用率和并发数，并支撑 continuous batching 和前缀共享。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: block 切小或切大有什么影响？</div>
<div class="qa-a"><p>block 越小，内部浪费越少（最后一块尾部空余更小），但 block table 项更多、管理和查表开销更大；block 越大，管理开销小，但每个请求最后一块的尾部浪费更明显，前缀共享的粒度也更粗。vLLM 默认 16 token 一块，是浪费和开销之间的折中。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 物理 block 不连续，attention 计算会不会变慢或出错？</div>
<div class="qa-a"><p>不会出错：kernel 读 KV 时先查 block table 找到每个逻辑块对应的物理 block，再去取数，逻辑顺序由映射保证。性能上确实多了查表和非连续访问的开销，但服务场景的瓶颈通常是 KV Cache 容量和调度空洞，而不是单次 attention 的极限带宽，所以换来更高并发和吞吐是划算的。</p></div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
