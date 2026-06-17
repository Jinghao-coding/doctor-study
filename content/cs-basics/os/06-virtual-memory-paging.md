## 一句话结论

虚拟内存让每个进程都以为独占连续地址空间，CPU 访问虚拟地址、MMU 通过页表翻译成物理地址，带来隔离、超额使用和按需分配。一句最该记的话：虚拟内存是"承诺"，物理内存是"兑现"，兑现发生在第一次写入触发缺页时——所以 malloc 1GB 不会立刻占物理内存。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 操作系统基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕进程线程、调度、虚拟内存、IO、多路复用、死锁、观测和 AI Infra OS 问题建立系统基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m">
<h3>虚拟内存：每个进程一套“假地址”</h3>
<p>虚拟内存让每个进程都以为自己独占一整块连续地址空间。CPU 访问的是<strong>虚拟地址</strong>，由 MMU 通过页表翻译成<strong>物理地址</strong>。这带来三个核心价值：进程间隔离、地址空间比物理内存大（靠换页）、按需分配与共享。</p>
<table>
<tr><th>能力</th><th>机制</th><th>意义</th></tr>
<tr><td>隔离</td><td>每进程独立页表</td><td>一个进程访问不到另一个进程内存</td></tr>
<tr><td>超额使用</td><td>page fault + swap</td><td>虚拟空间可大于物理内存</td></tr>
<tr><td>按需/延迟</td><td>lazy allocation、COW</td><td>malloc 不立刻占物理页，fork 不立刻拷贝</td></tr>
<tr><td>共享</td><td>多进程映射同一物理页</td><td>共享库、共享内存</td></tr>
</table>
</div>

<div class="card card-s">
<h3>分页与地址翻译</h3>
<p>内存被切成固定大小的<strong>页</strong>（通常 4KB），物理内存切成同样大小的<strong>页框</strong>。页表记录“虚拟页 → 物理页框”的映射。现代 64 位系统用<strong>多级页表</strong>（如 x86-64 四级）避免单级页表过大。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">虚拟地址</div><div class="flow-desc">拆成 页号 + 页内偏移</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">查 TLB</div><div class="flow-desc">命中则直接得到物理页框（快）</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">查页表</div><div class="flow-desc">TLB miss 时逐级走页表（page walk）</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">物理地址</div><div class="flow-desc">页框号 + 偏移，访问物理内存</div></div>
</div>
<div class="qa-summary">TLB 是页表的缓存。TLB miss 要走多级页表，代价高；这也是大页（HugePage）能提速的原因——同样内存用更少的页表项，TLB 覆盖更大。</div>
</div>

<div class="card card-d">
<h3>缺页中断（Page Fault）三种类型</h3>
<table>
<tr><th>类型</th><th>触发</th><th>处理</th><th>代价</th></tr>
<tr><td>Minor（软）</td><td>页在内存但未建立映射（如 COW、共享页）</td><td>内核补页表项</td><td>低</td></tr>
<tr><td>Major（硬）</td><td>页不在内存，需从磁盘/swap 读入</td><td>发起磁盘 I/O 换入</td><td>高（毫秒级）</td></tr>
<tr><td>Invalid</td><td>访问非法地址</td><td>发 SIGSEGV，进程崩溃</td><td>段错误</td></tr>
</table>
<p>排查信号：<code>vmstat</code> 的 si/so 列、<code>/proc/&lt;pid&gt;/stat</code> 的 majflt、<code>perf stat</code> 的 page-faults。Major fault 暴涨通常意味着内存不足开始 swap，P99 会剧烈抖动。</p>
</div>

<div class="card card-w">
<h3>页面置换算法</h3>
<table>
<tr><th>算法</th><th>思想</th><th>问题</th></tr>
<tr><td>FIFO</td><td>先进先出</td><td>可能换出热点页，有 Belady 异常</td></tr>
<tr><td>LRU</td><td>淘汰最久未使用</td><td>精确实现成本高</td></tr>
<tr><td>Clock / 近似 LRU</td><td>用访问位环形扫描近似 LRU</td><td>Linux 实际采用的近似方案</td></tr>
</table>
<div class="qa-summary">Linux 用基于 active/inactive 链表的近似 LRU（带 second chance），而不是教科书纯 LRU，因为纯 LRU 维护开销太大。</div>
</div>

<div class="card card-m">
<h3>和 AI Infra 的联系</h3>
<p>虚拟内存机制直接影响大模型系统：<strong>① pinned memory</strong>（页锁定内存）禁止换页，才能让 GPU DMA 安全直传，是 H2D/D2H 拷贝提速的关键；<strong>② mmap 加载权重</strong>用按需缺页避免一次性读入巨大文件；<strong>③ HugePage/THP</strong> 减少 TLB miss，对大块连续访问的训练/推理负载有收益；<strong>④ 避免 swap</strong>，训练进程一旦触发 major fault 换页，吞吐会断崖式下降，所以训练节点通常关 swap。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: malloc 申请了 1GB 内存，物理内存马上就被占用了吗？</div>
<div class="qa-a"><p>不会。malloc 通常只是扩大虚拟地址空间（建立映射区），并不立刻分配物理页。只有当你真正<strong>写入</strong>某一页时，才触发缺页中断由内核分配物理页框（lazy allocation / demand paging）。所以 <code>top</code> 里 VIRT（虚拟）远大于 RES（实际驻留物理）是正常的。</p><div class="qa-summary">面试口径：虚拟内存是“承诺”，物理内存是“兑现”，兑现发生在第一次写入触发缺页时。</div></div>
</div>

## 面试回答

**30 秒版：**

虚拟内存让每个进程看到一套独立连续的地址空间，CPU 用虚拟地址、MMU 查页表翻译成物理地址，实现进程隔离、地址空间大于物理内存、按需分配和共享。核心记忆点：虚拟内存是承诺、物理内存是兑现，malloc 只扩虚拟空间，第一次写入才触发缺页分配物理页（lazy allocation）。TLB 是页表缓存，miss 要走多级页表，这也是大页能提速的原因。

**2 分钟版：**

虚拟内存让每个进程都以为独占一整块连续地址空间，CPU 访问的是虚拟地址，由 MMU 通过页表翻译成物理地址，带来三个价值：进程隔离、地址空间可大于物理内存（靠换页）、按需分配与共享。地址翻译流程是：虚拟地址拆成页号加偏移，先查 TLB，命中直接拿物理页框，miss 才逐级走多级页表做 page walk，所以 TLB 是关键缓存，大页能用更少页表项覆盖更大内存、减少 TLB miss。缺页分三种：minor fault 是页在内存但没建映射（COW、共享页），内核补页表项、代价低；major fault 是页不在内存要从磁盘或 swap 读、毫秒级、暴涨意味着开始 swap、P99 剧烈抖动；invalid 是访问非法地址、发 SIGSEGV。一个高频追问是 malloc 1GB 不会立刻占物理内存，只有写入某页才触发缺页分配，所以 top 里 VIRT 远大于 RES 是正常的。落到 AI Infra：pinned memory 禁止换页让 GPU DMA 安全直传、提速 H2D；mmap 加载权重靠按需缺页避免一次性读入；HugePage 减少 TLB miss；训练节点通常关 swap，因为一旦 major fault 换页吞吐会断崖。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
