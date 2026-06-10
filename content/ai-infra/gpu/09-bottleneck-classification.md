<div class="card card-m">
<h3>GPU 三大瓶颈分类</h3>
<p>GPU 性能问题最终都可以归到三类瓶颈：<strong>计算瓶颈</strong>、<strong>显存瓶颈</strong>、<strong>通信瓶颈</strong>。判断属于哪一类，决定了优化方向完全不同。</p>
</div>

<div class="card card-s">
<h3>计算瓶颈（Compute-bound）</h3>
<p><strong>定义</strong>：GPU 的计算单元（CUDA Core / Tensor Core）是瓶颈，计算请求已满，但数据供给充足。</p>
<table>
<tr><th>特征</th><th>表现</th></tr>
<tr><td>Compute Throughput</td><td>高，接近硬件峰值</td></tr>
<tr><td>Memory Throughput</td><td>相对不高</td></tr>
<tr><td>SM Active</td><td>高</td></tr>
<tr><td>Roofline 位置</td><td>落在 Compute Roof 附近</td></tr>
</table>
<p><strong>典型场景</strong>：大矩阵乘法（GEMM）、大 batch 的卷积、大 batch 的 prefill 阶段 Attention。</p>
<p><strong>优化方向</strong>：</p>
<ul>
<li>使用 Tensor Core（确保 dtype、shape 对齐）</li>
<li>降低精度（FP16/BF16/FP8/INT8）</li>
<li>优化 tile 大小和指令 mix</li>
<li>投机解码（用小模型生成候选，大模型并行验证）</li>
</ul>
</div>

<div class="card card-w">
<h3>显存瓶颈（Memory-bound）</h3>
<p><strong>定义</strong>：GPU 的显存带宽是瓶颈，计算单元在等数据，大量时间花在 HBM 读写上。</p>
<table>
<tr><th>特征</th><th>表现</th></tr>
<tr><td>Memory Throughput</td><td>高，接近 HBM 带宽峰值</td></tr>
<tr><td>Compute Throughput</td><td>低</td></tr>
<tr><td>Long Scoreboard Stall</td><td>高</td></tr>
<tr><td>Roofline 位置</td><td>落在 Memory Roof（斜线区域）</td></tr>
</table>
<p><strong>典型场景</strong>：LLM decode 阶段、Elementwise 算子、LayerNorm、Softmax、Embedding lookup、Gather/Scatter、小 batch 推理。</p>
<p><strong>为什么 LLM decode 是显存瓶颈</strong>：每生成一个 token，需要从 HBM 加载全部模型权重（几十 GB），但只做极少量计算。算术强度约 2 FLOPs/Byte，远低于 A100 的 Ridge Point 153，所以必然 memory-bound。</p>
<p><strong>优化方向</strong>：</p>
<ul>
<li>提高算术强度：增大 batch size、融合算子</li>
<li>减少 HBM 读写：FlashAttention（分块+重计算）、shared memory 数据复用</li>
<li>压缩数据量：KV cache 量化、权重 INT8/FP8 量化</li>
<li>改善访问模式：memory coalescing、提高 L2 cache hit rate</li>
<li>PagedAttention：按需分配 KV cache 物理页，减少显存浪费</li>
</ul>
</div>

<div class="card card-r">
<h3>显存容量瓶颈（Memory Capacity-bound）</h3>
<p>和带宽瓶颈不同，<strong>容量瓶颈</strong>是指显存不够放——放不下模型权重、KV cache 或足够的 batch 数据。</p>
<p><strong>典型表现</strong>：OOM（Out of Memory）、被迫降低 batch size / seq_len、KV cache 容量不足导致并发请求数受限。</p>
<p><strong>优化方向</strong>：</p>
<ul>
<li>张量并行：模型分片到多卡</li>
<li>量化：FP16→INT8→INT4 减少权重和 KV cache 占用</li>
<li>ZeRO / FSDP：切分参数、梯度、优化器状态</li>
<li>Offload：不活跃数据放到 CPU/NVMe</li>
<li>PagedAttention + KV cache 压缩：显存超配 + 按需分配</li>
</ul>
</div>

<div class="card card-s">
<h3>通信瓶颈（Communication-bound）</h3>
<p><strong>定义</strong>：GPU 间的数据同步和传输成为瓶颈，GPU 时间花在等待通信完成上。</p>
<table>
<tr><th>特征</th><th>表现</th></tr>
<tr><td>NCCL 时间占比</td><td>高（Nsight Systems timeline 上 NCCL 占比大）</td></tr>
<tr><td>GPU-Util</td><td>可能高（通信 kernel 在跑），但 SM Active 可能低</td></tr>
<tr><td>扩展效率</td><td>多卡吞吐远低于线性扩展</td></tr>
</table>
<p><strong>典型场景</strong>：大规模张量并行的 all-reduce、流水线并行的跨卡激活传递、跨节点训练的梯度同步、KV cache 跨卡/跨节点迁移。</p>
<p><strong>优化方向</strong>：</p>
<ul>
<li>通信与计算重叠：NCCL 和 kernel 在不同 stream 上并行</li>
<li>梯度压缩 / 量化：减少通信数据量</li>
<li>拓扑优化：NVLink 全互联 > NVSwitch > PCIe > IB</li>
<li>减少通信次数：梯度累积、增大 bucket size</li>
<li>Ring Attention / 序列并行：减少跨卡通信量</li>
</ul>
</div>

<div class="card card-w">
<h3>如何快速判断属于哪种瓶颈？</h3>
<table>
<tr><th>判断方法</th><th>计算瓶颈</th><th>显存瓶颈</th><th>通信瓶颈</th></tr>
<tr><td>nvidia-smi</td><td>GPU-Util 高，Power 高</td><td>GPU-Util 可能不高，Memory Util 高</td><td>GPU-Util 可能高但吞吐低</td></tr>
<tr><td>Nsight Systems</td><td>kernel 密集，无空洞</td><td>kernel 可能有间隙或很短</td><td>NCCL / memcpy 占比大</td></tr>
<tr><td>Nsight Compute</td><td>Compute Throughput 高</td><td>Memory Throughput 高，Long Scoreboard 高</td><td>需结合 Nsight Systems</td></tr>
<tr><td>Roofline</td><td>落在水平区域</td><td>落在斜线区域</td><td>不直接适用</td></tr>
<tr><td>扩展性测试</td><td>单卡和多卡都慢</td><td>单卡和多卡都慢</td><td>单卡快，多卡反而慢</td></tr>
</table>

<div class="qa-summary">排查顺序：先用 nvidia-smi 看有没有活 → Nsight Systems 看谁占时间 → Nsight Compute 看单个 kernel 瓶颈在哪 → 扩展性测试判断是否通信瓶颈。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU-Util 100% 但推理 QPS 很低，怎么排查？</div>
<div class="qa-a"><p>先判断是哪类瓶颈。第一步看 Memory Throughput：如果 HBM 带宽打满、Compute Throughput 低，是显存带宽瓶颈（常见于 LLM decode）。第二步看 Nsight Systems timeline：如果 NCCL 占大量时间，是通信瓶颈。第三步看 Tensor Core Util：如果低，可能没用上 Tensor Core 或 shape 不友好。第四步看 kernel 碎片度：大量小 kernel 导致 launch overhead 高。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 计算瓶颈和显存瓶颈能同时存在吗？</div>
<div class="qa-a"><p>在同一个 kernel 上通常不会——Roofline 模型里一个点要么在斜线区域（memory-bound），要么在水平区域（compute-bound）。但在端到端场景中，不同 kernel 可以是不同瓶颈：prefill 阶段 compute-bound，decode 阶段 memory-bound，某些小算子 launch-bound。所以优化时需要针对不同阶段不同策略，这也是为什么推理引擎会把 prefill 和 decode 分开调度。</p></div>
</div>
