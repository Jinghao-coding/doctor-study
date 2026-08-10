<div class="card card-m">
<h3>Cache 工作机制</h3>
<table><tr><th>概念</th><th>核心含义</th><th>面试关键词</th></tr>
<tr><td>Cache Line</td><td>缓存的最小单位，x86 典型 64 字节</td><td>64B、spatial locality、对齐</td></tr>
<tr><td>映射方式</td><td>直接映射 / N 路组相联 / 全相联</td><td>现代 CPU 多为 N-way set associative</td></tr>
<tr><td>写策略</td><td>Write-through（直写）vs Write-back（回写）</td><td>现代 L1/L2/L3 多用 write-back + write-allocate</td></tr>
<tr><td>包含策略</td><td>Inclusive（L3 包含 L2）vs Exclusive / NINE</td><td>Intel 多用 inclusive，AMD Zen 多用 non-inclusive</td></tr>
<tr><td>时间局部性</td><td>刚访问的数据很快再次访问</td><td>循环变量、热路径代码</td></tr>
<tr><td>空间局部性</td><td>相邻地址的数据很快被访问</td><td>数组顺序遍历比链表快</td></tr>
</table>
</div>

<div class="card card-s">
<h3>TLB：地址翻译缓存</h3>
<ul>
<li><strong>作用：</strong>缓存虚拟页→物理页帧（PFN）映射，避免每次访存都查多级页表</li>
<li><strong>层级：</strong>L1 ITLB/DTLB（每 core，小而快）→ L2 TLB（shared，更大）</li>
<li><strong>Page size：</strong>4KB 常规页；2MB/1GB 大页（HugePage）减少 TLB entry 数量</li>
<li><strong>TLB Miss 代价：</strong>页表遍历（page walk）需多次访存（x86 4级页表≈4次DRMA访问），~100–200 cycles</li>
</ul>
</div>

<div class="card card-w">
<h3>False Sharing（伪共享）</h3>
<p><strong>现象：</strong>多线程修改逻辑独立的变量，但它们落在同一 64B cache line 上 → cache coherence 协议在 core 间反复 invalidate + transfer → 实际变成串行访问。</p>
<p><strong>检测：</strong><code>perf c2c</code>（cache-to-cache）定位热点 cache line。</p>
<p><strong>解决：</strong></p>
<ul>
<li>Padding：在变量间填充字节，让它们落在不同 cache line</li>
<li><code>alignas(64)</code>：C++11 标准属性按 cache line 对齐</li>
<li>线程本地分片：每线程独立计数，最后汇总</li>
<li>减少共享写：共享读无问题，共享写才会触发 coherence traffic</li>
</ul>
</div>

<div class="card card-d">
<h3>写友好代码的原则</h3>
<table><tr><th>原则</th><th>做法</th><th>反例</th></tr>
<tr><td>顺序访问</td><td>数组行优先遍历</td><td>列优先遍历（cache miss 暴增）</td></tr>
<tr><td>数据对齐</td><td>结构体按 cache line 对齐热点字段</td><td>跨 cache line 的未对齐访问</td></tr>
<tr><td>减小工作集</td><td>分块（tiling/blocking）处理大矩阵</td><td>对整个大矩阵随机访问</td></tr>
<tr><td>用大页</td><td>2MB HugePage 减少 TLB miss</td><td>随机访问大内存用 4KB 页</td></tr>
<tr><td>避免 false sharing</td><td>Padding + thread-local</td><td>多个线程写相邻的计数器</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么遍历数组比链表快？</div>
<div class="qa-a"><p>数组元素在内存中连续存放，遍历时 cache 每次 miss 会预取后续 64B（一个 cache line 含 ~8 个 8 字节元素），空间局部性好。链表节点分散在堆中，每次访问几乎都 cache miss，还可能造成 TLB miss。实测差距可达 10–50x。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: HugePage 为什么能提升性能？</div>
<div class="qa-a"><p>以 2MB 大页 vs 4KB 常规页为例：2MB = 512 × 4KB，同样的虚拟地址范围需要的 TLB entry 数减少到 1/512。大内存随机访问场景（如大模型 KV cache、数据库 buffer pool）TLB miss 率显著下降。1GB 大页更激进，但需预留连续物理内存，适合长期运行的大进程。</p></div>
</div>
