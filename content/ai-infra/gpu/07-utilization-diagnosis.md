<div class="card card-w">
<h3>先记住一句话：GPU-Util 高，不等于 GPU 真正用得好</h3>
<p>判断一个 GPU “利用率高不高”，不要只看 <code>nvidia-smi</code> 里的 <code>GPU-Util</code>。它只能告诉你采样窗口里 GPU 时间上是否有 kernel 在跑，但不能告诉你 SM 是否铺满、warp 是否真的能发射、Tensor Core 是否用起来、瓶颈到底在计算还是显存。<code>nvidia-smi</code> 本身定位是 NVIDIA System Management Interface，用于监控和管理 NVIDIA GPU，并支持查询 GPU、显存、功耗、温度、时钟等系统级信息[[nvidia-smi Documentation](https://docs.nvidia.com/deploy/nvidia-smi/index.html)]。</p>
<div class="qa-summary">最推荐的判断链路：GPU-Util 看有没有活；SM Active 看活有没有铺满 SM；Occupancy 看 SM 里 warp 是否足够；Warp Stall 看 warp 是否真能执行；Compute/Memory Throughput 看瓶颈在哪；Tensor Core Util 看 AI 算力是否用上；最后用吞吐和延迟判断 GPU 忙得是否有效。</div>
</div>

<div class="card card-w">
<h3>一条排查主线：从系统级到业务级</h3>
<p>你可以把 GPU 利用率诊断想成十层漏斗。越往上越粗，适合快速判断；越往下越细，适合解释为什么慢。面试时不要一上来报一堆指标，而是先说你的排查顺序。</p>
<pre><code>1. GPU 有没有活干？
   看 GPU-Util。

2. 显存只是占着，还是 GPU 真的在计算？
   区分 memory.used 和 utilization.memory。

3. 活有没有铺满 SM？
   看 SM Active。

4. SM 里面挂了多少 warp？
   看 achieved occupancy / active warps。

5. warp 是否真的能发射？
   看 eligible warps、issued warps、stall reasons。

6. 瓶颈在 compute 还是 memory？
   看 compute throughput 和 memory throughput。

7. AI workload 是否用上 Tensor Core？
   看 tensor pipe / tensor instruction。

8. 是否被功耗、温度、时钟限制？
   看 power、clock、temperature、p-state。

9. 端到端 timeline 有没有空洞？
   用 Nsight Systems 看 CPU、CUDA、memcpy、NCCL。

10. GPU 忙得是否有业务价值？
    训练看 tokens/sec、samples/sec、step time、MFU；推理看 QPS、TTFT、TPOT、P99。</code></pre>
<p>这个顺序的好处是：它不会把“设备看起来很忙”和“业务真的跑得快”混为一谈。很多线上问题的本质不是 GPU 不忙，而是 GPU 忙在了不该忙的地方，例如重计算、低效访存、通信等待、碎 kernel、错误 dtype 或无效 batch。</p>
</div>

<div class="card card-w">
<h3>第一层：GPU-Util 只看时间上有没有 kernel</h3>
<p><code>GPU-Util</code> 回答的是一个非常粗的问题：在采样周期内，GPU 上是否有一个或多个 kernel 正在执行。它不是 SM 利用率，不是 CUDA Core 利用率，也不是 Tensor Core 利用率，更不是实际 FLOPS。</p>
<div class="qa-section"><div class="qa-section-title">怎么获取</div><pre><code class="language-bash"># 快速看当前 GPU 状态
nvidia-smi

# 持续刷新，观察利用率、功耗、温度等变化
nvidia-smi dmon

# 查询指定字段
nvidia-smi --query-gpu=timestamp,index,name,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,temperature.gpu --format=csv -l 1</code></pre></div>
<div class="qa-section"><div class="qa-section-title">怎么理解</div><p>如果 <code>GPU-Util</code> 长期低于 30%，大概率是 GPU 没喂饱，可能是数据加载慢、CPU 预处理慢、batch 太小、请求量不足、I/O 慢、kernel launch 间隔大或多卡通信等待。如果 <code>GPU-Util</code> 长期高于 80%，只能说明 GPU 时间上比较忙，后面还要继续判断它是不是忙得有效。</p></div>
<div class="qa-section"><div class="qa-section-title">典型陷阱</div><p>一个很小的 kernel 如果持续运行，也可能让 <code>GPU-Util</code> 接近 100%。例如一张有 108 个 SM 的 A100，如果某个 kernel 只用到少数 SM，但一直不断执行，<code>GPU-Util</code> 可能很高，实际硬件并没有被铺满。</p></div>
</div>

<div class="card card-w">
<h3>第二层：显存占用不等于 GPU 利用率</h3>
<p>显存占用和 GPU 计算利用率是两件事。<code>memory.used</code> 表示显存容量用了多少；<code>utilization.memory</code> 更偏采样周期内 device/global memory 是否在读写。模型参数、KV cache 或缓存 allocator 占着显存，不代表 GPU 正在高效计算。</p>
<div class="qa-section"><div class="qa-section-title">怎么获取</div><pre><code class="language-bash">nvidia-smi --query-gpu=memory.used,memory.total,utilization.memory --format=csv -l 1</code></pre></div>
<div class="qa-section"><div class="qa-section-title">怎么判断</div><p>显存高但 <code>GPU-Util</code> 低，常见于模型已经加载、KV cache 或 tensor 占着显存，但请求流量不足、CPU 没喂上或程序在等待。显存低但 <code>GPU-Util</code> 高，也很常见，例如某些小模型或小 batch 计算忙但显存占用不大。显存接近满说明 batch size、sequence length 或并发可能受限，也有 OOM 风险，但它不是“利用率高”的证据。</p></div>
</div>

<div class="card card-w">
<h3>第三层：SM Active，看活有没有铺满 GPU</h3>
<p><code>SM Active</code> 比 <code>GPU-Util</code> 更接近我们想知道的问题：GPU 上的 SM 有没有被广泛使用。可以粗略理解为，在所有 SM 和所有采样时间里，有多少比例的 SM 至少有 active warp。</p>
<div class="qa-section"><div class="qa-section-title">为什么它比 GPU-Util 更细</div><p><code>GPU-Util</code> 是“这段时间 GPU 有没有 kernel”；<code>SM Active</code> 是“这些 SM 在这些时间里有没有活”。如果某个 kernel 只铺到少数 SM，它仍然可能让 <code>GPU-Util</code> 很高，但 <code>SM Active</code> 会暴露空间利用率不足的问题。</p></div>
<div class="qa-section"><div class="qa-section-title">怎么获取</div><pre><code class="language-bash"># 用 Nsight Compute 采集完整指标
ncu --set full ./your_program

# 只采集 SM Active 相关指标
ncu --metrics sm__cycles_active.avg.pct_of_peak_sustained_elapsed ./your_program</code></pre></div>
<div class="qa-section"><div class="qa-section-title">怎么判断</div><p><code>SM Active</code> 低，通常说明并行度不足，例如 batch 太小、grid 太小、算子规模太小或 kernel 设计没有铺开。<code>SM Active</code> 高但性能仍低，说明大多数 SM 时间上有活，但 warp 可能在 stall，或者计算/访存效率不好，需要继续看 occupancy、eligible warps 和 throughput。</p></div>
</div>

<div class="card card-w">
<h3>第四层：Occupancy，看 SM 里有多少 warp 可调度</h3>
<p><code>Occupancy</code> 可以粗略理解为：一个 SM 上 active warps 数量占该 SM 最大支持 active warps 数量的比例。它的作用是判断 SM 里是否有足够多的 warp 用来隐藏访存、依赖和执行延迟。</p>
<div class="qa-section"><div class="qa-section-title">Theoretical vs Achieved</div><p><strong>Theoretical Occupancy</strong> 可以根据 launch 参数、block size、register 使用、shared memory 使用和 GPU 架构限制静态估算；<strong>Achieved Occupancy</strong> 是运行时真实采集到的结果。前者告诉你理论上最多能挂多少 warp，后者告诉你实际 workload 中挂了多少 warp。</p></div>
<div class="qa-section"><div class="qa-section-title">怎么获取</div><pre><code class="language-bash">ncu --set full ./your_program

# 常看 Nsight Compute 中的这些 section
# Launch Statistics
# Occupancy
# Scheduler Statistics

# 也可以指定 active warps 指标
ncu --metrics sm__warps_active.avg.pct_of_peak_sustained_active ./your_program</code></pre></div>
<div class="qa-section"><div class="qa-section-title">不要误解</div><p><strong>Occupancy 高不等于性能高。</strong>它只是说明 SM 上有足够多的 warp 可用于隐藏 latency。如果 kernel 已经 memory-bound，提高 occupancy 可能没有明显收益；如果为了提高 occupancy 而减少寄存器导致更多访存，反而可能变慢。面试时要强调：occupancy 是诊断指标，不是最终目标。</p></div>
</div>

<div class="card card-w">
<h3>第五层：Warp Stall，看 warp 是否真的能发射</h3>
<p>一个 warp 是 active，不代表它当前周期就能执行。更细地看，一个 warp 可能处于 active、eligible、selected 或 stalled 状态。真正影响吞吐的是：有多少 warp 已经 ready，可以被 scheduler 发射。</p>
<pre><code>active warp：
  驻留在 SM 上，还没结束。

eligible warp：
  当前周期已经准备好，可以发射指令。

selected warp：
  当前周期被 scheduler 选中发射。

stalled warp：
  因为内存、依赖、同步、barrier 等原因暂时不能发射。</code></pre>
<div class="qa-section"><div class="qa-section-title">关键判断</div><p>如果 active warps 很多，但 eligible warps 很少，说明 SM 里看起来挂了很多 warp，但大部分都在等。此时 GPU 可能很忙，但忙得不高效。</p></div>
<div class="qa-section"><div class="qa-section-title">常见 stall 原因</div><ul><li><strong>Long Scoreboard</strong>：通常表示在等 global memory / L2 / DRAM。</li><li><strong>Short Scoreboard</strong>：通常表示在等 shared memory 或短延迟依赖。</li><li><strong>Barrier</strong>：等待 <code>__syncthreads()</code> 或类似同步。</li><li><strong>Wait</strong>：指令依赖等待。</li><li><strong>Not Selected</strong>：有 eligible warp，但本周期没被 scheduler 选中。</li><li><strong>Math Pipe Throttle</strong>：计算管线压力大。</li><li><strong>MIO Throttle</strong>：memory input/output 管线压力大。</li></ul></div>
<div class="qa-section"><div class="qa-section-title">怎么获取</div><pre><code class="language-bash">ncu --set full ./your_program

# 重点看：
# Scheduler Statistics
# Warp State Statistics
# Source Counters</code></pre></div>
</div>

<div class="card card-w">
<h3>第六层：Compute Throughput，看算力侧是否接近峰值</h3>
<p><code>Compute Throughput</code> 或 <code>SM Throughput</code> 更接近“算力有没有打满”这个问题。它回答的是计算侧吞吐达到硬件峰值的多少，而不是 GPU 时间上有没有活。</p>
<div class="qa-section"><div class="qa-section-title">怎么获取</div><pre><code class="language-bash">ncu --set full ./your_program

# 重点看：
# GPU Speed Of Light Throughput
# Compute Workload Analysis

# 示例指标
ncu --metrics sm__throughput.avg.pct_of_peak_sustained_elapsed ./your_program</code></pre></div>
<div class="qa-section"><div class="qa-section-title">怎么判断</div><p><code>Compute Throughput</code> 高，可能是 compute-bound；<code>Compute Throughput</code> 低但 <code>SM Active</code> 高，说明 SM 有活但效率不高，需要看 stall、访存和指令 mix；<code>Compute Throughput</code> 低而 <code>Memory Throughput</code> 高，通常是 memory-bound；两者都低，可能是同步、依赖、分支、launch overhead 或数据不连续。</p></div>
</div>

<div class="card card-w">
<h3>第七层：Memory Throughput，看是不是卡在显存和访问模式</h3>
<p>很多 AI 算子并不是 compute-bound，而是 memory-bound。典型例子包括 LayerNorm、Softmax、Embedding、Gather/Scatter、Elementwise、小 batch inference。它们的共同特点是每读写一批数据，只做相对较少计算，算术强度不高。</p>
<div class="qa-section"><div class="qa-section-title">怎么获取</div><pre><code class="language-bash">ncu --set full ./your_program

# 重点看：
# Memory Workload Analysis
# GPU Speed Of Light Throughput
# L1/TEX、L2、DRAM 相关指标</code></pre></div>
<div class="qa-section"><div class="qa-section-title">怎么判断</div><p>如果 DRAM throughput 高、compute throughput 低，通常是 memory-bound。如果 L2 hit rate 低，说明访问局部性差。如果 global load/store 效率差，说明访存不合并或访问模式不友好。如果 memory util 高但业务吞吐低，可能是带宽被低效访问消耗掉了。</p></div>
<div class="qa-section"><div class="qa-section-title">优化方向</div><p>常见优化包括 coalesced memory access、提高 L2/cache hit、减少 global memory 访问、使用 shared memory 做 tile 复用、融合算子减少中间结果读写，以及调整数据布局让同一个 warp 内访问更连续。</p></div>
</div>

<div class="card card-w">
<h3>第八层：Tensor Core Utilization，看 AI 算力是否用起来</h3>
<p>对于 Transformer、GEMM、Conv、Attention 这类深度学习 workload，判断 GPU 是否用好，还必须看 Tensor Core 是否真正参与。模型跑在 GPU 上，不代表它用了 Tensor Core。</p>
<div class="qa-section"><div class="qa-section-title">怎么获取</div><pre><code class="language-bash">ncu --set full ./your_program

# 重点看：
# GPU Speed Of Light Throughput
# Compute Workload Analysis
# Instruction Statistics

# 示例 tensor 相关指标
ncu --metrics sm__inst_executed_pipe_tensor.sum,sm__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_elapsed ./your_program</code></pre></div>
<div class="qa-section"><div class="qa-section-title">Tensor Core 没用起来的常见原因</div><ul><li>dtype 不合适，例如使用 FP32 但没有允许 TF32。</li><li>矩阵 shape 不友好，无法形成高效 tile。</li><li>没有走 cuBLAS、cuDNN、TensorRT、CUTLASS 等高性能实现。</li><li>框架配置禁用了 TF32 或混合精度。</li><li>算子 fallback 到普通 CUDA Core kernel。</li><li>batch 太小，矩阵规模太小。</li></ul></div>
<div class="qa-section"><div class="qa-section-title">PyTorch 常见检查</div><pre><code class="language-python">import torch

torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True</code></pre></div>
</div>

<div class="card card-w">
<h3>第九层：Power / Clock / Thermal，看是不是被限频</h3>
<p>如果 <code>GPU-Util</code> 高、<code>SM Active</code> 高，但性能仍低，还要检查功耗、温度和时钟。GPU 可能因为 power limit、thermal throttle、p-state、MIG/MPS 资源隔离或容器限制，导致看起来忙但实际频率和吞吐上不去。</p>
<div class="qa-section"><div class="qa-section-title">怎么获取</div><pre><code class="language-bash">nvidia-smi -q -d POWER,CLOCK,TEMPERATURE,PERFORMANCE

nvidia-smi --query-gpu=power.draw,power.limit,clocks.sm,clocks.mem,temperature.gpu,pstate --format=csv -l 1</code></pre></div>
<div class="qa-section"><div class="qa-section-title">怎么判断</div><p>如果 power draw 接近 power limit，可能功耗受限；温度持续很高，可能 thermal throttle；<code>clocks.sm</code> 低，可能被降频；p-state 不理想，可能没有进入高性能状态。训练吞吐突然下降时，除了看代码和通信，也要看这些节点级硬件状态。</p></div>
</div>

<div class="card card-w">
<h3>第十层：端到端业务指标，看 GPU 忙得是否有价值</h3>
<p>GPU 指标高，不代表业务性能好。真正的目标不是让 GPU 看起来忙，而是让训练吞吐、推理吞吐、延迟和成本达到预期。</p>
<div class="qa-section"><div class="qa-section-title">训练场景看什么</div><p>训练中建议看 <code>samples/sec</code>、<code>tokens/sec</code>、<code>step time</code>、<code>MFU</code>、data loading time、communication time。如果 GPU 指标很高但 tokens/sec 低，可能是重计算、通信、低效 kernel 或数据 pipeline 让 GPU 忙在了低价值工作上。</p></div>
<div class="qa-section"><div class="qa-section-title">推理场景看什么</div><p>推理中建议看 QPS、tokens/sec、TTFT、TPOT、P50/P90/P99 latency、batch size、queue time、KV cache memory。LLM 推理尤其要拆开 prefill 和 decode，因为 prefill 更偏计算密集，decode 常受 KV cache 读写、batch 组织和访存影响。</p></div>
</div>

<div class="card card-w">
<h3>工具选择：每个工具解决不同层级的问题</h3>
<p>不要指望一个工具回答所有问题。系统级状态用 <code>nvidia-smi</code> 和 DCGM；timeline 用 Nsight Systems；单 kernel 细节用 Nsight Compute；框架算子归因用 PyTorch Profiler。</p>
<div class="qa-section"><div class="qa-section-title">nvidia-smi：系统级粗看</div><p>适合看 GPU-Util、显存占用、功耗、温度、时钟和进程。优点是方便快速，缺点是不能解释 kernel 为什么慢，也看不到 SM、warp、Tensor Core 细节。</p><pre><code class="language-bash">nvidia-smi
nvidia-smi dmon -s pucvmet
nvidia-smi --query-gpu=timestamp,index,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,clocks.sm,temperature.gpu --format=csv -l 1</code></pre></div>
<div class="qa-section"><div class="qa-section-title">DCGM / Prometheus / Grafana：生产监控</div><p>DCGM 提供 GPU 指标采集、健康检查、作业统计、拓扑等能力，适合集群监控和告警[[Feature Overview — NVIDIA DCGM Documentation](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/feature-overview.html)]。</p><pre><code>DCGM_FI_DEV_GPU_UTIL
DCGM_FI_DEV_FB_USED
DCGM_FI_DEV_POWER_USAGE
DCGM_FI_DEV_GPU_TEMP
DCGM_FI_DEV_SM_CLOCK
DCGM_FI_DEV_MEM_COPY_UTIL</code></pre></div>
<div class="qa-section"><div class="qa-section-title">Nsight Systems：端到端 timeline</div><p>Nsight Systems 适合看 CPU 线程、CUDA API、kernel、memcpy、stream、NCCL 等在时间线上如何交错；官方文档也建议通过 NVTX 或 profiler API 聚焦性能关键代码区域，减少无关数据干扰[[User Guide — Nsight Systems](https://docs.nvidia.com/nsight-systems/UserGuide/index.html)]。</p><pre><code class="language-bash">nsys profile -t cuda,nvtx,osrt,cudnn,cublas -o report ./your_program</code></pre></div>
<div class="qa-section"><div class="qa-section-title">Nsight Compute / NCU：单 kernel 深挖</div><p>Nsight Compute CLI 可以从命令行 profile 应用，并为选定 kernel 采集指标；它支持通过 section 或 metrics 选择采集内容，也支持按 kernel 名称过滤[[Nsight Compute CLI](https://docs.nvidia.com/nsight-compute/NsightComputeCli/index.html)]。</p><pre><code class="language-bash">ncu --set full ./your_program
ncu --kernel-name regex:your_kernel_name --set full ./your_program</code></pre></div>
<div class="qa-section"><div class="qa-section-title">PyTorch Profiler：框架算子归因</div><p>PyTorch Profiler 适合把 Python / PyTorch op 和 CUDA kernel 对齐起来，回答哪个 op 最耗时、CPU 时间多还是 CUDA 时间多、是不是 DataLoader 慢、是不是有大量小 kernel。</p><pre><code class="language-python">import torch
import torch.profiler as profiler

with profiler.profile(
    activities=[
        profiler.ProfilerActivity.CPU,
        profiler.ProfilerActivity.CUDA,
    ],
    record_shapes=True,
    profile_memory=True,
    with_stack=True,
) as prof:
    for step, batch in enumerate(loader):
        output = model(batch)
        loss = output.sum()
        loss.backward()
        if step &gt; 10:
            break

print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=20))</code></pre></div>
</div>

<div class="card card-w">
<h3>实战路径：从 nvidia-smi 到 profiler</h3>
<p>真实排障时，建议按下面的顺序走。先用低成本工具判断方向，再用 profiler 精确定位。</p>
<div class="qa-section"><div class="qa-section-title">Step 1：先看 nvidia-smi</div><pre><code class="language-bash">nvidia-smi</code></pre><p>关注 GPU-Util、Memory-Usage、Power、Temperature 和进程。如果 <code>GPU-Util</code> 长期低，先怀疑数据加载、CPU preprocessing、batch 太小、I/O、请求量不足、kernel launch 太碎或多卡通信等待。如果 <code>GPU-Util</code> 长期高，继续判断是不是高效。</p></div>
<div class="qa-section"><div class="qa-section-title">Step 2：用 Nsight Systems 看 timeline</div><pre><code class="language-bash">nsys profile -t cuda,nvtx,osrt,cudnn,cublas -o report ./your_program</code></pre><p>重点看 GPU timeline 是否有空洞、kernel 是否连续、CPU 是否频繁同步、<code>cudaMemcpy</code> 是否阻塞、NCCL 是否占大量时间。大量小 kernel 往往说明 launch overhead 高或算子太碎。</p></div>
<div class="qa-section"><div class="qa-section-title">Step 3：用 Nsight Compute 看核心 kernel</div><pre><code class="language-bash">ncu --set full ./your_program</code></pre><p>重点看 SM Active、Achieved Occupancy、Compute Throughput、Memory Throughput、Warp Stall Reasons、Tensor Core Utilization。这里才能回答“这个 kernel 为什么慢”。</p></div>
</div>

<div class="card card-w">
<h3>六种典型结论：如何把指标翻译成人话</h3>
<p>面试和排障时，最重要的是把指标组合翻译成清晰结论。</p>
<div class="qa-section"><div class="qa-section-title">A. GPU 没喂饱</div><pre><code>GPU-Util 低
SM Active 低
Nsight Systems 看到 GPU timeline 有空洞</code></pre><p>常见原因是 DataLoader 慢、CPU preprocessing 慢、batch 太小、I/O 慢、请求量不足、kernel launch 太碎或 CPU-GPU 同步。</p></div>
<div class="qa-section"><div class="qa-section-title">B. GPU 时间上忙，但没铺满硬件</div><pre><code>GPU-Util 高
SM Active 低
Achieved Occupancy 低</code></pre><p>常见原因是 kernel grid 太小、batch 太小、并行度不足、算子规模小或 block 配置不合理。</p></div>
<div class="qa-section"><div class="qa-section-title">C. SM 都有活，但效率低</div><pre><code>GPU-Util 高
SM Active 高
Occupancy 高
Compute Throughput 低
Memory Throughput 也低
Warp Stall 高</code></pre><p>常见原因是指令依赖、同步、分支发散、访存模式差、barrier 多或 atomic 多。</p></div>
<div class="qa-section"><div class="qa-section-title">D. Memory-bound</div><pre><code>SM Active 高
Memory Throughput 高
Compute Throughput 低
Long Scoreboard stall 高</code></pre><p>优化方向是访存合并、提高 cache hit、减少 global memory 访问、使用 shared memory、融合算子、减少中间结果读写。</p></div>
<div class="qa-section"><div class="qa-section-title">E. Compute-bound</div><pre><code>SM Active 高
Compute Throughput 高
Memory Throughput 不高</code></pre><p>优化方向是使用 Tensor Core、优化指令 mix、减少冗余计算、提高 tile 效率、使用更合适 dtype。</p></div>
<div class="qa-section"><div class="qa-section-title">F. Tensor Core 没用起来</div><pre><code>GPU-Util 高
SM Active 高
Tensor Pipe / Tensor Core Util 低</code></pre><p>如果 workload 是 GEMM、Conv 或 Attention，需要检查 FP16/BF16/TF32 是否开启，shape 是否对齐，是否使用高性能库，是否 fallback 到普通 CUDA kernel，batch size 是否太小。</p></div>
</div>

<div class="card card-w">
<h3>面试推荐回答：如何判断 GPU 利用率高不高？</h3>
<p>可以这样回答：</p>
<blockquote>我不会只看 <code>nvidia-smi</code> 的 GPU-Util，因为它只是表示采样窗口内 GPU 上是否有 kernel 在执行的时间比例。要判断 GPU 是否真正被充分使用，我会分层看。首先看 GPU-Util、显存、功耗，判断 GPU 时间上是否有活；然后用 Nsight Systems 看 timeline，确认 GPU 有没有空洞、CPU 是否喂得上、kernel launch 和 memcpy 是否阻塞；再用 Nsight Compute 看 kernel 级指标，包括 SM Active、Achieved Occupancy、Warp Stall、Compute Throughput、Memory Throughput。如果是深度学习 workload，还要看 Tensor Core Utilization。最后结合业务指标，比如训练 tokens/sec、samples/sec，或者推理 QPS、latency、tokens/sec，判断 GPU 忙得是否有效。</blockquote>
<div class="qa-summary">短版：nvidia-smi 看是否忙；Nsight Systems 看是否连续；Nsight Compute 看为什么慢；业务指标看忙得值不值。</div>
</div>

<div class="card card-w">
<h3>最后记忆版：一条链路背下来</h3>
<pre><code>GPU-Util：
  时间上有没有 kernel。

SM Active：
  kernel 有没有铺满 SM。

Occupancy：
  SM 里 active warp 是否足够。

Eligible / Issued Warps：
  warp 是否真的能发射。

Warp Stall：
  不能发射是在等什么。

Compute Throughput：
  计算管线是否接近峰值。

Memory Throughput：
  是否被显存带宽或访问模式卡住。

Tensor Core Utilization：
  AI 矩阵算力是否真的用起来。

Power / Clock / Thermal：
  是否被功耗、温度、时钟限制。

业务指标：
  GPU 忙，是否真的换来了 tokens/sec、samples/sec、QPS 和低延迟。</code></pre>
</div>
