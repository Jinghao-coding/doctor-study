## 一句话结论

GPU 面试不要只背硬件名词，要把问题落到三条主线：**数据怎么流动**、**计算怎么铺满**、**资源怎么共享和诊断**。能把这三条讲清楚，就能自然连接 LLM 推理、分布式训练、K8S GPU 调度和性能预测。

## 30 秒回答模板

GPU 适合 AI 的核心原因是矩阵计算密集、数据并行度高、显存带宽高。面试回答时我会先区分 CPU 和 GPU：CPU 擅长控制流和低延迟串行逻辑，GPU 擅长用大量 SM、warp 和 Tensor Core 做吞吐型计算。然后补充三类工程问题：第一，数据路径上要关注 HBM、PCIe、NVLink、RDMA 和 NUMA；第二，执行模型上要关注 kernel、grid/block/thread、warp、stream 和 occupancy；第三，性能诊断上要用 `nvidia-smi`、Nsight Systems、Nsight Compute、DCGM 去判断是计算、显存、通信、数据加载还是 kernel launch 瓶颈。

## 2 分钟展开模板

如果面试官继续追问，可以按下面顺序展开：

1. **硬件层**：GPU 由多个 SM 组成，SM 内有 CUDA Core、Tensor Core、register file、shared memory 等资源；显存是 HBM，带宽远高于 CPU DDR，但容量更小。
2. **执行层**：CPU 负责 host 侧控制和 kernel launch，GPU 执行 device 侧 kernel。Kernel 被组织成 grid、block、thread，warp 是硬件调度的基本执行单元。
3. **内存层**：global memory 容量大但慢，shared memory/register 更快但容量小。优化目标是提高数据复用、访存连续性和 Tensor Core 利用率。
4. **数据路径**：单机内优先走 NVLink/NVSwitch，CPU-GPU 和 GPU-NIC 通常走 PCIe，跨机训练依赖 RDMA/InfiniBand/RoCE 和 GPUDirect RDMA。
5. **共享隔离**：MIG 是硬件切分，隔离强但粒度粗；MPS 是软件并发，灵活但有干扰；time-slicing 主要解决调度复用，不保证性能隔离。
6. **诊断层**：GPU-Util 只能说明时间上是否有活，不能说明是否高效；要结合 SM Active、Occupancy、Memory Throughput、Tensor Core Util、Warp Stall 和业务吞吐延迟判断。

## 高频追问压缩表

<table>
<tr><th>问题</th><th>回答抓手</th><th>不要踩的坑</th></tr>
<tr><td>GPU-Util 100% 为什么还慢？</td><td>继续看 SM Active、Occupancy、Memory Throughput、Tensor Core、kernel launch、NCCL timeline</td><td>不要把 GPU-Util 等同于 GPU 高效利用</td></tr>
<tr><td>Occupancy 越高越好吗？</td><td>Occupancy 是隐藏延迟的条件，但寄存器/shared memory 竞争会让 100% occupancy 反而变慢</td><td>不要把 occupancy 当唯一优化目标</td></tr>
<tr><td>Prefill 和 decode 谁更吃 GPU？</td><td>Prefill 更像大 GEMM，容易 compute-bound；decode 每 token 读大量 KV cache，常见 memory-bound</td><td>不要把 LLM 推理所有阶段混成同一种瓶颈</td></tr>
<tr><td>MIG、MPS、time-slicing 怎么选？</td><td>MIG 看强隔离，MPS 看并发与配额，time-slicing 看低成本复用和开发/低负载场景</td><td>不要说 time-slicing 能保证固定 1/N 算力</td></tr>
<tr><td>多机训练为什么慢？</td><td>看 NCCL 路径、NVLink/PCIe/RDMA、NUMA/NIC 亲和、bucket size、通信计算重叠</td><td>不要只看单卡 TFLOPS</td></tr>
<tr><td>H2D/D2H 怎么优化？</td><td>减少 D2H、批量拷贝、pinned memory、non_blocking、DataLoader 预取、stream 重叠</td><td>不要频繁 .item()/.cpu().numpy()</td></tr>
</table>

## 排障 / 设计决策树

<pre><code class="language-flow">GPU-Util 长期低 | 先怀疑数据加载、CPU preprocessing、H2D、batch 太小、请求量不足
GPU-Util 高但业务慢 | 看 Nsight Systems timeline，判断 kernel、memcpy、NCCL、同步谁占时间
Kernel 占主时间 | 用 Nsight Compute 看 SM Active、Occupancy、Memory Throughput、Tensor Core、Warp Stall
Memory Throughput 高且 Compute 低 | memory-bound，优化访存、KV cache、算子融合、FlashAttention/PagedAttention
Compute Throughput 高且 Tensor Core 高 | compute-bound，考虑更低精度、更大 batch、算子选择和并行策略
NCCL/通信占比高 | 查拓扑、NVLink/RDMA、NUMA/NIC 亲和、bucket、overlap、并行策略
Memcpy 或同步很多 | 查 .item()/.cpu()、DataLoader、pinned memory、stream、CPU-GPU 来回转换</code></pre>

## 跨模块关联

<table>
<tr><th>关联页面</th><th>GPU 这里要带过去的知识</th><th>面试连接方式</th></tr>
<tr><td>LLM 推理系统</td><td>HBM 带宽、KV cache、decode memory-bound、FlashAttention、PagedAttention</td><td>解释为什么 decode 阶段容易卡在显存带宽和 KV 读取，而不是纯算力</td></tr>
<tr><td>分布式训练</td><td>NVLink/NVSwitch、RDMA、NCCL、GPUDirect RDMA、通信计算重叠</td><td>解释多卡训练吞吐为什么受拓扑和 collective 通信影响</td></tr>
<tr><td>Kubernetes 核心</td><td>Device Plugin、Extended Resource、MIG/MPS/time-slicing、DRA</td><td>说明 K8S 调度看到的是资源抽象，不等价于硬件隔离语义</td></tr>
<tr><td>调度与集群</td><td>拓扑感知、碎片、GPU 共享、干扰、Gang scheduling</td><td>把单卡性能问题升级成集群调度和多租户治理问题</td></tr>
<tr><td>性能预测与建模</td><td>MFU、SM Active、Occupancy、Memory Throughput、Active Memory</td><td>说明哪些指标可以做特征，哪些指标适合作为预测标签</td></tr>
<tr><td>论文项目</td><td>干扰建模、QAD、共享策略、性能画像</td><td>把 GPU 基础知识连接到 DeepShare/Maestro 的项目叙事</td></tr>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果只给你 1 分钟讲 GPU，你会怎么讲？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答</div><p>我会从三层讲：硬件层，GPU 用大量 SM、warp 和 Tensor Core 提供高吞吐，HBM 提供高带宽；执行层，CPU 发起 kernel，GPU 以 grid/block/thread/warp 组织并行，stream/event 负责异步流水线；系统层，要关注数据路径和资源共享，单机看 PCIe/NVLink，跨机看 RDMA/NCCL，K8S 里看 device-plugin、MIG、MPS、time-slicing。性能问题不能只看 GPU-Util，要结合 Nsight timeline、SM Active、Occupancy、Memory Throughput、Tensor Core 和业务指标判断瓶颈。</p></div>
<div class="qa-summary">短版：硬件吞吐、执行模型、数据路径、共享隔离、性能诊断。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官问“怎么系统性排查 GPU 慢”，你怎么回答？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答</div><p>我会先确认业务指标，比如训练 step time、推理 QPS/TPOT/TTFT，然后从粗到细排查。第一步用 nvidia-smi/DCGM 看 GPU-Util、显存、功耗、PCIe/NVLink 计数和进程。第二步用 Nsight Systems 看端到端 timeline，确认空洞、Memcpy、同步、NCCL、kernel 碎片和 CPU 等待。第三步对热点 kernel 用 Nsight Compute，看 SM Active、Achieved Occupancy、Memory Throughput、Tensor Core Util、Warp Stall。最后结合模型阶段判断：prefill 可能 compute-bound，decode 常 memory-bound，多卡训练可能 communication-bound，数据加载慢则 input pipeline-bound。</p></div>
<div class="qa-summary">排查顺序：业务指标 → nvidia-smi/DCGM → Nsight Systems → Nsight Compute → 阶段化判断瓶颈。</div>
</div>
</div>
