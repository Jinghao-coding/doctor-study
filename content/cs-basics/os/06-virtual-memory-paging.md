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
