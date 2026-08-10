## 诊断入口

```flow
业务指标异常
  -> nvidia-smi / DCGM 看 GPU-Util、显存、功耗、PCIe/NVLink
  -> Nsight Systems 看 timeline：kernel / memcpy / NCCL / 空洞 / 同步
  -> Nsight Compute 看热点 kernel：compute、memory、occupancy、stall
  -> 扩展性实验：单卡、多卡、不同 batch、不同 seq_len 对比
```

## 指标解释

| 瓶颈类型 | 主要证据 | 常见误判 |
|---|---|---|
| Compute-bound | Compute Throughput 高、Tensor Core Util 高、Roofline 靠近 compute roof | 只看 GPU-Util 高就说 compute-bound |
| Memory-bandwidth-bound | Memory Throughput 高、Long Scoreboard 高、Roofline 落在 memory roof | 把显存容量不足和显存带宽不足混为一谈 |
| Memory-capacity-bound | OOM、batch/seq_len/并发受限、KV cache 放不下 | 只看显存占用高就说带宽瓶颈 |
| Communication-bound | NCCL/memcpy 占比高、多卡扩展效率差、拓扑敏感 | 通信 kernel 也会让 GPU-Util 高，容易误判为计算忙 |

## 排查路径

### 计算瓶颈（Compute-bound）

**定义**：GPU 的计算单元（CUDA Core / Tensor Core）是瓶颈，计算请求已满，但数据供给充足。

<table>
<tr><th>特征</th><th>表现</th></tr>
<tr><td>Compute Throughput</td><td>高，接近硬件峰值</td></tr>
<tr><td>Memory Throughput</td><td>相对不高</td></tr>
<tr><td>SM Active</td><td>高</td></tr>
<tr><td>Roofline 位置</td><td>落在 Compute Roof 附近</td></tr>
</table>

典型场景：大矩阵乘法（GEMM）、大 batch 的卷积、大 batch 的 prefill 阶段 Attention。

优化方向：

- 使用 Tensor Core，确保 dtype、shape 和 layout 对齐。
- 降低精度，例如 FP16/BF16/FP8/INT8。
- 优化 tile 大小和指令 mix。
- 对 decode 类任务考虑 speculative decoding，用小模型生成候选，大模型并行验证。

### 显存带宽瓶颈（Memory-bandwidth-bound）

**定义**：GPU 的显存带宽是瓶颈，计算单元在等数据，大量时间花在 HBM 读写上。

<table>
<tr><th>特征</th><th>表现</th></tr>
<tr><td>Memory Throughput</td><td>高，接近 HBM 带宽峰值</td></tr>
<tr><td>Compute Throughput</td><td>低</td></tr>
<tr><td>Long Scoreboard Stall</td><td>高</td></tr>
<tr><td>Roofline 位置</td><td>落在 Memory Roof（斜线区域）</td></tr>
</table>

典型场景：LLM decode 阶段、elementwise 算子、LayerNorm、Softmax、Embedding lookup、Gather/Scatter、小 batch 推理。

为什么 LLM decode 常是显存瓶颈：每生成一个 token，需要从 HBM 加载大量模型权重和 KV cache，但新增 token 的计算量相对少，算术强度低，容易落在 Roofline 的 memory-bound 区域。

优化方向：

- 提高算术强度：增大 batch size、融合算子。
- 减少 HBM 读写：FlashAttention、shared memory 数据复用、算子融合。
- 压缩数据量：KV cache 量化、权重量化。
- 改善访问模式：memory coalescing、提高 L2 cache hit rate。
- 用 PagedAttention 按需分配 KV cache 物理页，减少显存浪费。

### 显存容量瓶颈（Memory-capacity-bound）

容量瓶颈是指显存不够放，放不下模型权重、KV cache、activation、optimizer state 或足够的 batch 数据。它和带宽瓶颈不同：容量问题首先表现为 OOM 或并发受限，带宽问题表现为算子在等数据。

典型表现：

- OOM。
- 被迫降低 batch size、sequence length 或并发请求数。
- KV cache 容量不足导致 decode 阶段可服务请求数受限。

优化方向：

- 张量并行：模型分片到多卡。
- 量化：FP16 到 INT8/INT4，减少权重和 KV cache 占用。
- ZeRO / FSDP：切分参数、梯度、优化器状态。
- Offload：不活跃数据放到 CPU/NVMe。
- PagedAttention + KV cache 压缩：显存超配 + 按需分配。

### 通信瓶颈（Communication-bound）

**定义**：GPU 间的数据同步和传输成为瓶颈，GPU 时间花在等待通信完成上。

<table>
<tr><th>特征</th><th>表现</th></tr>
<tr><td>NCCL 时间占比</td><td>高（Nsight Systems timeline 上 NCCL 占比大）</td></tr>
<tr><td>GPU-Util</td><td>可能高（通信 kernel 在跑），但 SM Active 可能低</td></tr>
<tr><td>扩展效率</td><td>多卡吞吐远低于线性扩展</td></tr>
</table>

典型场景：大规模张量并行 all-reduce、流水线并行跨卡激活传递、跨节点训练梯度同步、KV cache 跨卡/跨节点迁移。

优化方向：

- 通信与计算重叠：NCCL 和 kernel 在不同 stream 上并行。
- 梯度压缩或量化：减少通信数据量。
- 拓扑优化：优先利用 NVLink/NVSwitch，再考虑 PCIe/RDMA。
- 减少通信次数：梯度累积、增大 bucket size。
- Ring Attention / 序列并行：减少跨卡通信量。

## 典型现象

<table>
<tr><th>判断方法</th><th>计算瓶颈</th><th>显存瓶颈</th><th>通信瓶颈</th></tr>
<tr><td>nvidia-smi</td><td>GPU-Util 高，Power 高</td><td>GPU-Util 可能不高，Memory Util 高</td><td>GPU-Util 可能高但吞吐低</td></tr>
<tr><td>Nsight Systems</td><td>kernel 密集，无空洞</td><td>kernel 可能有间隙或很短</td><td>NCCL / memcpy 占比大</td></tr>
<tr><td>Nsight Compute</td><td>Compute Throughput 高</td><td>Memory Throughput 高，Long Scoreboard 高</td><td>需结合 Nsight Systems</td></tr>
<tr><td>Roofline</td><td>落在水平区域</td><td>落在斜线区域</td><td>不直接适用</td></tr>
<tr><td>扩展性测试</td><td>单卡和多卡都慢</td><td>单卡和多卡都慢</td><td>单卡快，多卡反而慢</td></tr>
</table>

排查顺序：先用 `nvidia-smi` 看有没有活，再用 Nsight Systems 看谁占时间，然后用 Nsight Compute 看单个 kernel 瓶颈在哪，最后用扩展性测试判断是否通信瓶颈。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU-Util 100% 但推理 QPS 很低，怎么排查？</div>
<div class="qa-a"><p>先判断是哪类瓶颈。第一步看 Memory Throughput：如果 HBM 带宽打满、Compute Throughput 低，是显存带宽瓶颈（常见于 LLM decode）。第二步看 Nsight Systems timeline：如果 NCCL 占大量时间，是通信瓶颈。第三步看 Tensor Core Util：如果低，可能没用上 Tensor Core 或 shape 不友好。第四步看 kernel 碎片度：大量小 kernel 导致 launch overhead 高。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 计算瓶颈和显存瓶颈能同时存在吗？</div>
<div class="qa-a"><p>在同一个 kernel 上通常不会——Roofline 模型里一个点要么在斜线区域（memory-bound），要么在水平区域（compute-bound）。但在端到端场景中，不同 kernel 可以是不同瓶颈：prefill 阶段 compute-bound，decode 阶段 memory-bound，某些小算子 launch-bound。所以优化时需要针对不同阶段不同策略，这也是为什么推理引擎会把 prefill 和 decode 分开调度。</p></div>
</div>
