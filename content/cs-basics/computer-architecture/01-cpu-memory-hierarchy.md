## 一句话结论

CPU 性能不只看核数，更取决于数据离 CPU 有多近：寄存器、L1/L2/L3、本地 DRAM、远端 NUMA 内存延迟逐级放大、带宽逐级降低。很多"CPU 跑满但吞吐上不去"的问题本质是访存受限而非算力不足。

<div class="card card-m">
<h3>存储层次金字塔</h3>
<table><tr><th>层次</th><th>典型容量</th><th>延迟量级</th><th>带宽</th><th>谁管理</th></tr>
<tr><td>寄存器</td><td>~KB（每 core 几十个）</td><td>1 cycle</td><td>—</td><td>编译器</td></tr>
<tr><td>L1 Cache（I/D 分离）</td><td>32KB + 32KB / core</td><td>~4 cycles</td><td>>1TB/s</td><td>硬件</td></tr>
<tr><td>L2 Cache</td><td>256KB–2MB / core</td><td>~12 cycles</td><td>~500GB/s</td><td>硬件</td></tr>
<tr><td>L3 Cache（LLC）</td><td>数 MB–数百 MB / socket</td><td>~40 cycles</td><td>~100GB/s</td><td>硬件，多 core 共享</td></tr>
<tr><td>本地 DRAM</td><td>几十 GB–几 TB / socket</td><td>~100ns（~300 cycles）</td><td>~50–100GB/s（DDR5）</td><td>OS（虚拟内存）</td></tr>
<tr><td>远端 NUMA DRAM</td><td>其他 socket</td><td>~200ns（1.5–2x）</td><td>~30–50% 本地带宽</td><td>OS + 硬件互联</td></tr></table>
</div>

<div class="card card-s">
<h3>关键规律</h3>
<ul>
<li><strong>越靠近 CPU：</strong>容量越小、延迟越低、带宽越高、成本/bit 越高</li>
<li><strong>延迟差 100x：</strong>L1（1ns）到 DRAM（~100ns），相当于从书桌到楼下超市取东西</li>
<li><strong>带宽差 20x：</strong>L1（&gt;1TB/s）到 DRAM（~50GB/s）</li>
<li><strong>NUMA 惩罚：</strong>跨 socket 访问延迟增加 50–100%，带宽下降 30–50%</li>
</ul>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么加了核数吞吐反而下降？</div>
<div class="qa-a"><p>可能的原因（从硬件到系统）：</p>
<ul>
<li><strong>Cache 污染：</strong>多线程共享 L3，工作集挤掉彼此的热数据</li>
<li><strong>False sharing：</strong>独立变量落在同一 cache line（见 Cache/TLB 章节）</li>
<li><strong>内存带宽饱和：</strong>所有 core 同时打 DRAM，带宽成为瓶颈</li>
<li><strong>NUMA 远端访问：</strong>线程被调度到远端 socket</li>
<li><strong>锁竞争 / 上下文切换：</strong>软件层面串行化</li>
</ul>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 怎么判断程序是算力瓶颈还是访存瓶颈？</div>
<div class="qa-a"><p>几个快速判断方法：</p>
<ul>
<li><code>perf stat</code> 看 <strong>IPC（instructions per cycle）</strong>：高 IPC（>1）说明算力用满了；低 IPC（<0.5）通常是访存/分支等待</li>
<li><strong>Cache miss rate：</strong>L1/L2/LLC miss 高 → 访存瓶颈</li>
<li><strong>Roofline 模型：</strong>计算 Operational Intensity（FLOPs/Byte），看落在算力拐点左侧还是右侧（见性能预测 / Roofline 章节）</li>
<li><strong>缩数据实验：</strong>把工作集缩到 L3 以内，如果吞吐飙升 → 原先是 DRAM 带宽瓶颈</li>
</ul>
</div>
</div>
