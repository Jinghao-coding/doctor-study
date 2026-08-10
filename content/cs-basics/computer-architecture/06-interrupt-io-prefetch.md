<div class="card card-m">
<h3>I/O 方式演进</h3>
<table><tr><th>方式</th><th>原理</th><th>CPU 参与</th><th>适用场景</th></tr>
<tr><td>轮询（PIO / Programmed I/O）</td><td>CPU 不断读设备状态寄存器</td><td>极高（CPU 100% 忙等）</td><td>早期简单设备、低延迟专用场景（DPDK 轮询模式）</td></tr>
<tr><td>中断驱动 I/O</td><td>设备准备好后发中断，CPU 响应处理</td><td>低（等待时 CPU 可做别的事）</td><td>键盘、磁盘、低吞吐网络</td></tr>
<tr><td>DMA</td><td>DMA 控制器（或设备自身作为 bus master）直接在设备和内存间搬数据</td><td>仅启动和收尾（初始化 DMA 描述符）</td><td>网卡、GPU、SSD、高性能存储</td></tr>
</table>
</div>

<div class="card card-s">
<h3>DMA 工作流程（以网卡收包为例）</h3>
<ol>
<li><strong>初始化：</strong>驱动在内存中分配环形缓冲区（RX ring），将 buffer 物理地址写入网卡 DMA 描述符</li>
<li><strong>收包：</strong>网卡收到数据包，通过 DMA 直接写入 RX ring 的 buffer（不需 CPU 参与）</li>
<li><strong>通知：</strong>网卡发中断（或 NAPI 轮询模式下中断触发后轮询）通知 CPU 有包可处理</li>
<li><strong>处理：</strong>CPU（内核协议栈 / DPDK 用户态轮询）读取 buffer 处理数据</li>
<li><strong>归还：</strong>buffer 处理完后还给驱动，重新挂到 RX ring</li>
</ol>
<p><strong>GPU DMA：</strong>GPU 通过 PCIe 直接访问 Host 内存（cudaMemcpy 等），GPUDirect P2P 允许 GPU↔GPU 或 GPU↔NIC 直接传输不经过 Host 内存。</p>
</div>

<div class="card card-d">
<h3>中断与上下文切换</h3>
<ul>
<li><strong>中断处理分两部分：</strong>
  <ul>
    <li><strong>上半部（HardIRQ）：</strong>立即响应，关中断，做最紧急的事（如从 NIC 取数据），必须快</li>
    <li><strong>下半部（SoftIRQ / tasklet / workqueue）：</strong>开中断，延迟处理重活（如协议栈解析）</li>
  </ul>
</li>
<li><strong>中断亲和性（IRQ Affinity）：</strong>将中断绑定到特定 CPU core，避免跨核 cache miss；高性能场景下每个 RX 队列中断绑一个 core（RSS + RPS/RFS）</li>
<li><strong>中断风暴：</strong>高吞吐下中断过于频繁，CPU 全在处理中断来不及干活 → NAPI（New API）：中断触发后切换到轮询，一次性处理多个包后再开中断</li>
<li><strong>DPDK/SPDK：</strong>完全绕过内核中断，用户态轮询驱动（PMD），零中断零拷贝，极低延迟但占满 CPU</li>
</ul>
</div>

<div class="card card-w">
<h3>Hardware Prefetching（硬件预取）</h3>
<p>CPU 检测内存访问模式，提前把数据加载到 cache，减少 cache miss。</p>
<ul>
<li><strong>Stream prefetcher：</strong>检测顺序访问（步长固定），向前预取多个 cache line（最常见）</li>
<li><strong>Stride prefetcher：</strong>检测固定步长（如每 4 个元素访问一个）</li>
<li><strong>NL prefetcher（Next-line）：</strong>总是预取下一个 cache line</li>
<li><strong>IP-based / Delta prefetcher：</strong>按 PC 历史记录预取</li>
<li><strong>局限性：</strong>预取只对规则访问有效；随机访问（链表、哈希表）无法预取；预取过度会污染 cache</li>
<li><strong>软件预取：</strong><code>__builtin_prefetch(&amp;x)</code> / <code>PREFETCHT0</code> 指令手动提示 CPU 提前加载，对不规则但可预测的访问有帮助（如 B-Tree 遍历）</li>
</ul>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 DPDK 要轮询而不用中断？</div>
<div class="qa-a"><p>线速 100Gbps 下，一个 64 字节小包每 6.7ns 就到达一个，中断频率 ~148Mpps，中断处理开销（上下文切换 + cache miss + 中断路由）远超轮询。DPDK 采用用户态 PMD 轮询模式：(1) 绕过内核，零 syscall 开销；(2) 大页 + 物理地址连续内存减少 TLB miss；(3) 每个 core 独占一个 RX 队列，无锁；(4) 轮询模式没有中断延迟。代价是 CPU 100% 占用，但在低延迟/高吞吐场景这是可接受的 tradeoff。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: NUMA、PCIe 拓扑和 GPU/NIC 亲和性是什么关系？</div>
<div class="qa-a"><p>在多路服务器上，PCIe 插槽直接挂在特定 socket（NUMA node）上。GPU 和 NIC 如果在同一个 socket 上，它们之间 DMA 通过本地 PCIe root complex，延迟低、带宽高；跨 socket 则必须走 UPI/QPI 链路，延迟增加、带宽受互联带宽限制。AI 训练多机多卡场景中：GPU 直接接在 CPU0 socket 的 PCIe 上，NIC 最好也插在 CPU0 上，GPUDirect RDMA 才能走最短路径。<code>nvidia-smi topo -m</code> 和 <code>lstopo</code> 可以查看拓扑。</p></div>
</div>
