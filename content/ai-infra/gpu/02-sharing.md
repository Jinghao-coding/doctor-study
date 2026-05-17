<div class="card card-s">
<table>
<tr><th>方式</th><th>隔离级别</th><th>原理</th><th>适用场景</th></tr>
<tr><td>MIG</td><td>硬件切片</td><td>物理切分 GPU 为独立实例，各有独立显存和 SM</td><td>推理、多租户强隔离</td></tr>
<tr><td>MPS</td><td>进程级复用</td><td>多进程共享 GPU 上下文，并行执行 kernel</td><td>训练合用、I/O 互补</td></tr>
<tr><td>时间片</td><td>时间级复用</td><td>CUDA 调度器轮换上下文</td><td>轻量共享、交互式</td></tr>
<tr><td>CUDA VMM</td><td>虚拟内存</td><td>虚拟地址空间超配，物理页按需映射</td><td>KV 缓存弹性管理</td></tr>
<tr><td>vGPU</td><td>虚拟化</td><td>Hypervisor 层虚拟化 GPU</td><td>云服务多租户</td></tr>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MIG 和 MPS 的本质区别？</div>
<div class="qa-a"><p><strong>MIG</strong> 是硬件级切分——GPU 被物理切成若干独立实例，每个实例有自己的 SM、显存控制器和缓存，互相完全隔离，类似物理分区。<strong>MPS</strong> 是软件级复用——多个进程共享同一个 GPU 上下文，kernel 可以并行执行在不同 SM 上，但共享显存和缓存，有干扰风险。MIG 安全但粒度粗（A100 最多 7 个实例），MPS 灵活但需要干扰控制。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CUDA VMM 的虚拟内存超配原理？</div>
<div class="qa-a"><p>类似操作系统的虚拟内存：用 cuMemAddressReserve 分配大块虚拟地址（如 122GB），再用 cuMemMap 按需映射物理页。物理显存只有 40GB，但虚拟地址空间 122GB。应用看到连续大内存，实际物理页按需分配和回收。</p></div>
</div>
</div>
