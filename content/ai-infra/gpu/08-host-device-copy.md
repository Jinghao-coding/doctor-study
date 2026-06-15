<div class="card card-m">
<h3>Host-to-Device / Device-to-Host Copy 是什么</h3>
<div class="qa-summary">本节只回答“数据为什么要在 CPU 和 GPU 之间搬、哪些操作会触发搬运、如何减少和诊断搬运”。CUDA stream 的异步队列和多缓冲流水线放在下一节。</div>
<p><strong>Host-to-device copy（H2D）</strong> 是把数据从 CPU 内存拷贝到 GPU 显存；<strong>device-to-host copy（D2H）</strong> 是把数据从 GPU 显存拷贝回 CPU 内存。</p>
<table>
<tr><th>术语</th><th>含义</th><th>典型资源</th><th>方向</th><th>常见场景</th></tr>
<tr><td>Host</td><td>主机端</td><td>CPU、系统内存</td><td>-</td><td>DataLoader、Python 进程、业务服务</td></tr>
<tr><td>Device</td><td>设备端</td><td>GPU、GPU 显存</td><td>-</td><td>CUDA kernel、模型前向/反向、推理引擎</td></tr>
<tr><td>H2D</td><td>CPU 内存到 GPU 显存</td><td>Host memory -> Device memory</td><td>CPU -> GPU</td><td>把 batch 输入拷到 GPU</td></tr>
<tr><td>D2H</td><td>GPU 显存到 CPU 内存</td><td>Device memory -> Host memory</td><td>GPU -> CPU</td><td><code>.cpu()</code>、<code>.numpy()</code>、<code>.item()</code>、日志和后处理</td></tr>
</table>
<div class="qa-summary">一句话：H2D 是 CPU 内存到 GPU 显存，D2H 是 GPU 显存到 CPU 内存。</div>
</div>

<div class="card card-s">
<h3>为什么叫 Host 和 Device</h3>
<p>CUDA / GPU 编程里，一般把 CPU 侧叫 <code>Host</code>，把 GPU 侧叫 <code>Device</code>。Host 负责控制流程、数据读取、任务提交和 kernel launch；Device 负责执行大规模并行计算。</p>
<pre><code>Host memory   = CPU 内存
Device memory = GPU 显存

H2D: Host memory   -> Device memory
D2H: Device memory -> Host memory</code></pre>
<p>这个命名也解释了为什么 CUDA API、Profiler 和 Nsight 里经常看到 <code>Memcpy HtoD</code>、<code>Memcpy DtoH</code>。</p>
</div>

<div class="card card-d">
<h3>训练流程里的 H2D / D2H</h3>
<p>训练时 H2D 通常不可避免，因为样本先在 CPU 侧被读取和预处理，GPU 计算前必须把 batch 放到显存里。D2H 则很多时候可以减少，尤其是频繁把 loss、metric、中间 tensor 拷回 CPU。</p>
<pre><code>1. DataLoader 从磁盘读取图片/样本
2. CPU 做 decode / augmentation / tokenize
3. batch 放在 CPU 内存
4. H2D: batch 从 CPU 拷贝到 GPU
5. GPU 前向计算
6. GPU 反向传播
7. GPU 更新参数
8. 可选 D2H: loss / metric / output 拷回 CPU 打日志或后处理</code></pre>
<table>
<tr><th>操作</th><th>是否常见</th><th>是否可优化</th><th>说明</th></tr>
<tr><td>batch 输入 H2D</td><td>很常见</td><td>可加速/重叠</td><td>用 pinned memory、non_blocking、prefetch</td></tr>
<tr><td>loss.item() D2H</td><td>很常见</td><td>可减少频率</td><td>每 step 多次调用会触发同步和拷贝</td></tr>
<tr><td>tensor.cpu().numpy()</td><td>常见</td><td>应谨慎</td><td>会把 GPU tensor 拷回 CPU，常导致同步</td></tr>
<tr><td>GPU -> CPU -> GPU</td><td>性能反模式</td><td>应避免</td><td>能在 GPU 上做就不要绕回 numpy</td></tr>
</table>
</div>

<div class="card card-w">
<h3>为什么数据拷贝会影响性能</h3>
<p>GPU 计算很快，但 CPU 内存和 GPU 显存之间要经过 PCIe、NVLink 等互联。它们通常比 GPU 内部 HBM 访问慢，也比 GPU 内部计算更容易成为流水线瓶颈。如果每个 step 都频繁做 CPU -> GPU -> CPU -> GPU，GPU 就可能在等数据，而不是在计算。</p>
<table>
<tr><th>现象</th><th>可能原因</th><th>典型证据</th></tr>
<tr><td>GPU utilization 低</td><td>DataLoader 或 H2D 太慢</td><td>timeline 中 kernel 之间有空洞</td></tr>
<tr><td>step time 抖动</td><td>CPU 预处理、磁盘 I/O 或拷贝不稳定</td><td>Profiler 里 DataLoader 时间波动</td></tr>
<tr><td>CPU 等 GPU</td><td>D2H 触发同步</td><td><code>cudaStreamSynchronize</code>、<code>Memcpy DtoH</code></td></tr>
<tr><td>带宽利用差</td><td>大量小 tensor 小拷贝</td><td>很多短小 <code>Memcpy HtoD</code></td></tr>
</table>
<div class="qa-summary">性能问题的关键不是“有没有拷贝”，而是拷贝是否频繁、是否小而碎、是否阻塞、是否能和计算重叠。</div>
</div>

<div class="card card-m">
<h3>优化 1：减少不必要的 D2H</h3>
<p>D2H 操作经常比你想象中更隐蔽。PyTorch 里的 <code>.item()</code>、<code>.cpu()</code>、<code>.numpy()</code>、打印 GPU tensor，都可能把 GPU 上的数据拷回 CPU，并触发同步。</p>
<table>
<tr><th>触发操作</th><th>问题</th><th>优化方式</th></tr>
<tr><td><code>loss.item()</code></td><td>GPU loss 拷回 CPU，可能同步</td><td>每 N step 记录一次，或聚合后再取</td></tr>
<tr><td><code>tensor.cpu()</code></td><td>显式 D2H</td><td>只在必要输出/保存时调用</td></tr>
<tr><td><code>tensor.numpy()</code></td><td>需要先回 CPU</td><td>尽量用 PyTorch GPU tensor 操作替代 numpy</td></tr>
<tr><td><code>print(gpu_tensor)</code></td><td>为了显示内容可能触发同步</td><td>少打印，打印 shape/dtype/device 等元信息</td></tr>
</table>
<pre><code class="language-python"># 不推荐：每步都强制 D2H + 同步
loss_value = loss.item()

# 更好：降低频率，或多个指标聚合后再拷贝
if step % 100 == 0:
    loss_value = loss.detach().item()</code></pre>
</div>

<div class="card card-d">
<h3>优化 2：Pinned Memory + Non-blocking Copy</h3>
<p>Pinned memory，也叫 page-locked memory，表示这块 CPU 内存固定在物理内存里，不会被操作系统换出。GPU DMA 从 pinned memory 做 H2D 拷贝更高效，也更容易和计算异步重叠。</p>
<pre><code class="language-python">loader = DataLoader(
    dataset,
    batch_size=128,
    shuffle=True,
    num_workers=8,
    pin_memory=True,
    persistent_workers=True,
    prefetch_factor=2,
)

for batch, label in loader:
    batch = batch.to("cuda", non_blocking=True)
    label = label.to("cuda", non_blocking=True)
    output = model(batch)</code></pre>
<table>
<tr><th>参数</th><th>作用</th><th>注意点</th></tr>
<tr><td><code>pin_memory=True</code></td><td>DataLoader 把 batch 放到 pinned CPU memory</td><td>占用不可换出的物理内存，不能无限开</td></tr>
<tr><td><code>non_blocking=True</code></td><td>允许异步 H2D</td><td>通常需要 pinned memory 才更有效</td></tr>
<tr><td><code>num_workers</code></td><td>多进程并行读数据/预处理</td><td>过大可能 CPU 争用或内存压力大</td></tr>
<tr><td><code>prefetch_factor</code></td><td>提前准备后续 batch</td><td>增大可提升流水线，但会占更多内存</td></tr>
<tr><td><code>persistent_workers</code></td><td>跨 epoch 保持 worker</td><td>减少 worker 重启开销</td></tr>
</table>
</div>

<div class="card card-s">
<h3>优化 3：让拷贝和计算重叠</h3>
<p>理想训练流水线是：GPU 正在计算 batch N，CPU 同时准备 batch N+1，H2D 同时拷贝 batch N+1。这样 GPU 不需要在 batch 边界长时间等待数据。</p>
<pre><code>理想流水线：

时间轴 ---->
CPU/DataLoader:  prepare batch N+1   prepare batch N+2
H2D copy:              copy N+1           copy N+2
GPU compute: compute batch N     compute batch N+1</code></pre>
<p>如果 timeline 里看到 GPU compute 结束后才开始 H2D，并且中间有明显空洞，说明数据准备或拷贝没有很好重叠。</p>
</div>

<div class="card card-m">
<h3>优化 4：批量拷贝，减少小拷贝</h3>
<p>大量小 tensor 分别 <code>.to("cuda")</code> 会产生很多小 H2D copy，每次拷贝都有固定开销，带宽利用率也差。更好的方式是先在 CPU 侧合并成 batch，再一次性拷贝到 GPU。</p>
<pre><code class="language-python"># 不推荐：很多小 H2D
for x in list_of_tensors:
    x = x.to("cuda")

# 更好：先合并，再一次 H2D
batch = torch.stack(list_of_tensors)
batch = batch.to("cuda", non_blocking=True)</code></pre>
</div>

<div class="card card-d">
<h3>优化 5：避免 CPU/GPU 来回转换</h3>
<p>下面这种链路非常浪费：</p>
<pre><code class="language-python">x = x.cuda()
y = x.cpu().numpy()
z = torch.tensor(y).cuda()</code></pre>
<p>它会产生 <code>GPU -> CPU -> GPU</code>，既浪费带宽，又可能触发同步。原则是：能在 GPU 上做的计算就留在 GPU 上；能用 PyTorch GPU tensor 操作，就不要中途转 numpy。</p>
</div>

<div class="card card-s">
<h3>优化 6：预处理流水线和数据格式</h3>
<p>很多训练瓶颈不在 H2D 本身，而在 H2D 前面的 CPU decode、augmentation、tokenizer、磁盘 I/O 和小文件读取。优化方向包括更快的数据格式、更好的预取、更少的小文件和更靠近 GPU 的预处理。</p>
<table>
<tr><th>瓶颈</th><th>优化方式</th></tr>
<tr><td>图片 decode / resize / crop / normalization 慢</td><td>NVIDIA DALI、GPU augmentation、离线预处理、cache 结果</td></tr>
<tr><td>小文件太多</td><td>WebDataset、TFRecord、mmap、顺序读取格式</td></tr>
<tr><td>Tokenizer 慢</td><td>批量 tokenizer、预 tokenize、cache token ids</td></tr>
<tr><td>磁盘/网络存储慢</td><td>本地 NVMe cache、数据预热、分布式缓存</td></tr>
</table>
</div>

<div class="card card-w">
<h3>多 GPU 场景：避免 Host 中转</h3>
<p>多 GPU 通信最好直接走 GPU-GPU 或 GPU-NIC-GPU，而不是绕回 CPU。否则会出现低效路径：</p>
<pre><code>差：GPU0 -> CPU -> GPU1
好：GPU0 -> GPU1
好：GPU -> NIC -> GPU</code></pre>
<table>
<tr><th>机制</th><th>作用</th><th>典型场景</th></tr>
<tr><td>NVLink / NVSwitch</td><td>节点内 GPU-GPU 高带宽互联</td><td>TP、AllReduce、P2P copy</td></tr>
<tr><td>NCCL</td><td>多 GPU collective 通信库</td><td>DDP、ZeRO、张量并行</td></tr>
<tr><td>GPUDirect RDMA</td><td>GPU 显存和 NIC 直接通信，减少 CPU 参与</td><td>跨节点训练、RDMA 网络</td></tr>
<tr><td>P2P copy</td><td>GPU 间直接拷贝</td><td>同机多卡数据交换</td></tr>
</table>
</div>

<div class="card card-m">
<h3>推理服务里的拷贝优化</h3>
<p>在线推理也会被拷贝拖慢，尤其是请求小、batch 小、后处理重、输出频繁回 CPU 的场景。优化时要减少输入输出 buffer 抖动，让预处理、推理、后处理尽量流水线化。</p>
<ul>
<li>请求批处理，合并小输入。</li>
<li>输入预处理尽量批量化或放到 GPU。</li>
<li>输出后处理尽量在 GPU 上完成。</li>
<li>使用 zero-copy 或共享内存减少业务进程和推理进程之间的数据复制。</li>
<li>避免频繁把中间 tensor 拷回 CPU。</li>
<li>使用 TensorRT 管理输入输出 buffer，减少反复分配和拷贝。</li>
<li>使用 CUDA Graph 降低固定 shape 推理的 launch overhead。</li>
</ul>
</div>

<div class="card card-r">
<h3>如何判断是不是数据拷贝瓶颈</h3>
<p>如果 GPU utilization 低、CPU utilization 高、DataLoader 慢、每个 step 中间有明显空洞，就要怀疑数据加载或 H2D/D2H 拷贝瓶颈。</p>
<table>
<tr><th>工具</th><th>看什么</th></tr>
<tr><td>Nsight Systems</td><td>timeline 中的 <code>Memcpy HtoD</code>、<code>Memcpy DtoH</code>、kernel 空洞、stream 同步</td></tr>
<tr><td>PyTorch Profiler</td><td>DataLoader 时间、<code>aten::to</code>、<code>cudaMemcpyAsync</code>、CPU/GPU timeline</td></tr>
<tr><td>nvidia-smi / DCGM</td><td>GPU 利用率、显存、PCIe/NVLink 相关指标</td></tr>
<tr><td>torch.cuda.Event</td><td>测量 GPU 侧时间，区分 CPU wall time 和 GPU elapsed time</td></tr>
<tr><td>TensorBoard Profiler</td><td>训练 step 拆解和输入 pipeline 分析</td></tr>
</table>
<pre><code>重点关注：
Memcpy HtoD
Memcpy DtoH
cudaStreamSynchronize
cudaDeviceSynchronize
kernel 之间的大空洞</code></pre>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是 host-to-device / device-to-host copy？怎么优化？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">标准回答</div><p>Host 指 CPU 侧，Device 指 GPU 侧。Host-to-device copy 是把数据从 CPU 内存拷贝到 GPU 显存，例如训练时把 batch 输入拷到 GPU；device-to-host copy 是把 GPU 上的结果拷回 CPU，例如 <code>.cpu()</code>、<code>.numpy()</code>、<code>.item()</code>、日志和后处理。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么影响性能</div><p>这类拷贝需要走 PCIe、NVLink 等互联，相比 GPU 内部计算和 HBM 访问慢很多。而且很多 D2H 操作会触发同步，破坏 CUDA 异步执行，让 CPU 等 GPU 或 GPU 等数据。</p></div>
<div class="qa-section"><div class="qa-section-title">优化思路</div><p>第一，减少不必要的拷贝，尤其避免频繁 <code>.cpu()</code>、<code>.numpy()</code>、<code>.item()</code>；第二，用 pinned memory 和 <code>non_blocking=True</code> 加速 H2D；第三，用 DataLoader 多 worker、prefetch、persistent workers 让数据准备和 GPU 计算重叠；第四，尽量把预处理和后处理放在 GPU 上；第五，合并小 tensor 做批量拷贝；第六，多 GPU 场景使用 NCCL、NVLink、GPUDirect，避免 GPU 通信绕回 CPU。</p></div>
<div class="qa-summary">一句话：少拷贝、批量拷贝、异步拷贝、拷贝计算重叠，避免 GPU -> CPU -> GPU 来回搬。</div>
</div>
</div>
