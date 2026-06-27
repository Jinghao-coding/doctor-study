## 一句话结论

多核 CPU 中每个 core 有私有的 L1/L2，共享 L3，必然面临 cache coherence（缓存一致性）问题：MESI 协议保证各 core 看到一致的数据。但一致性不等于顺序性，CPU 和编译器都会重排指令，多线程编程必须靠内存屏障和 atomic 保证顺序。

<div class="card card-m">
<h3>Cache Coherence：MESI 协议</h3>
<p>每个 cache line 处于四种状态之一：</p>
<table><tr><th>状态</th><th>全称</th><th>含义</th></tr>
<tr><td><strong>M</strong>odified</td><td>已修改</td><td>本 core 独有，且被修改（脏），写回前其他 core 不能读</td></tr>
<tr><td><strong>E</strong>xclusive</td><td>独占</td><td>本 core 独有，且和内存一致（干净）</td></tr>
<tr><td><strong>S</strong>hared</td><td>共享</td><td>多个 core 都有副本，和内存一致（干净）</td></tr>
<tr><td><strong>I</strong>nvalid</td><td>无效</td><td>该 cache line 无效/不存在</td></tr>
</table>
<ul>
<li><strong>读请求：</strong>如果本地是 I，向总线发 Read，其他 core 或内存响应；根据是否有其他 core 持有进入 S 或 E</li>
<li><strong>写请求：</strong>必须先获得所有权（Read For Ownership），向其他 core 发 Invalidate，其他 core 置 I；写后进入 M</li>
<li><strong>核间通信：</strong>通过 invalidate/response 消息（Ring Bus / Mesh 网络）维护一致性</li>
</ul>
<p>MESIF（Intel）/ MOESI（AMD）在 MESI 基础上增加 F（Forward）/ O（Owned）优化共享数据转发。</p>
</div>

<div class="card card-w">
<h3>伪共享与 Coherence Traffic</h3>
<ul>
<li>多 core 同时写同一 cache line → 反复 Invalidate + 重新获取所有权 → cache line 在 core 间"弹跳"</li>
<li><strong>现象：</strong>CPU 利用率高但吞吐上不去</li>
<li><strong>perf 观测：</strong><code>perf stat -e cache-misses,mem_load_retired.l3_miss</code>，或 <code>perf c2c</code>（cache-to-cache）</li>
</ul>
</div>

<div class="card card-s">
<h3>内存一致性模型</h3>
<p>Cache coherence 保证"所有 core 最终看到相同的值"，但不保证"看到的顺序"。</p>
<table><tr><th>模型</th><th>含义</th><th>代表架构</th></tr>
<tr><td>SC（Sequential Consistency）</td><td>所有 core 的读写像按某个全局顺序执行</td><td>理想模型，无硬件实现</td></tr>
<tr><td>TSO（Total Store Order）</td><td>Store 按序、Store→Load 可能重排（允许 Store Buffer）</td><td><strong>x86</strong>（最强内存模型）</td></tr>
<tr><td>弱内存模型（Weak/Relaxed）</td><td>Load/Store 可随意重排，需显式屏障</td><td>ARM、RISC-V、PowerPC、GPU（PTX）</td></tr>
</table>
<p><strong>x86-TSO 下的重排规则：</strong>本质上只有 StoreLoad 重排（写后读可能越过写），其他三种（LoadLoad、LoadStore、StoreStore）都是保序的。所以 x86 只需要 <code>mfence</code>（或 <code>lock</code> 前缀指令）作为完整屏障。</p>
</div>

<div class="card card-d">
<h3>内存屏障与 C++ Atomic</h3>
<table><tr><th>屏障</th><th>作用</th><th>典型场景</th></tr>
<tr><td>Write memory barrier（smp_wmb）</td><td>保证屏障前的写先于屏障后的写</td><td>发布数据（先写数据，再写 ready 标志）</td></tr>
<tr><td>Read memory barrier（smp_rmb）</td><td>保证屏障前的读先于屏障后的读</td><td>依赖读取（先读 ready 标志，再读数据）</td></tr>
<tr><td>Full memory barrier（smp_mb）</td><td>双向全屏障</td><td>StoreLoad 重排防护</td></tr>
</table>
<p>C++ <code>std::atomic</code> 提供 6 种 memory order：</p>
<ul>
<li><code>memory_order_seq_cst</code>：顺序一致（最强，默认）</li>
<li><code>memory_order_acq_rel</code>：Acquire-Release（用于 CAS）</li>
<li><code>memory_order_acquire</code>：读侧屏障（后续读不越过）</li>
<li><code>memory_order_release</code>：写侧屏障（前面写不越过）</li>
<li><code>memory_order_consume</code>：数据依赖序（极少使用，多数编译器升级为 acquire）</li>
<li><code>memory_order_relaxed</code>：无顺序保证（只保证原子性），用于计数器</li>
</ul>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MESI 能解决多线程可见性问题吗？为什么还需要 volatile / atomic？</div>
<div class="qa-a"><p><strong>不能完全解决。</strong>MESI 保证 cache 一致性（最终所有 core 看到一致值），但存在两个问题：(1) <strong>Store Buffer</strong>：core 写数据先放入 store buffer，立即继续执行后续指令，其他 core 此时看不到新值——这是 x86 TSO 允许 StoreLoad 重排的根源；(2) <strong>Load Buffer</strong>：乱序执行让读操作可能提前执行。<code>volatile</code> 只保证编译器不优化掉访问（不重排、不缓存到寄存器），但不插入 CPU 内存屏障；<code>atomic</code> 同时约束编译器和 CPU。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 ARM 上的无锁代码比 x86 更容易出 bug？</div>
<div class="qa-a"><p>x86 是 TSO（强内存模型），硬件帮你保证了 LoadLoad/LoadStore/StoreStore 顺序，只有 StoreLoad 一种重排，很多"错误"的代码在 x86 上碰巧能跑。ARM/RISC-V 是弱内存模型，四种重排都可能发生，必须用正确的 memory order（acquire/release）才能保证正确性。C++ atomic 如果都用 seq_cst 是可移植的，但性能差；精细调优时要用对 acq/rel。</p></div>
</div>
