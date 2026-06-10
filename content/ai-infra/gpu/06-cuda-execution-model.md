<div class="card card-w">
<h3>先建立一张脑图：从一次 kernel launch 到 GPU 硬件执行</h3>
<p>这一页不要先背表格。你可以先记住一条主线：CPU 端发起一次 <code>kernel launch</code>，CUDA runtime 把它描述成一个 <code>grid</code>；grid 里面有很多 <code>block</code>；block 里面有很多 <code>thread</code>；GPU 硬件把 block 分配到不同的 <code>SM</code> 上执行；SM 内部再把 thread 按 <code>warp</code> 组织和调度。CUDA 官方文档把 CUDA 描述为 NVIDIA 的并行计算平台和编程模型，用来让程序利用 GPU 的计算能力[[CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html)]。</p>
<div class="qa-summary">一句话：你写的是 kernel，启动的是 grid，组织单位是 block 和 thread，硬件执行单位是 SM 和 warp。</div>
</div>

<div class="card card-w">
<h3>层级图：软件概念和硬件概念怎么对应</h3>
<p>理解 CUDA 最容易混乱的地方，是把软件层级和硬件层级混在一起。<code>grid / block / thread</code> 是 CUDA 编程模型里的逻辑层级；<code>GPU / SM / CUDA Core / Tensor Core / HBM</code> 是硬件层级；<code>warp</code> 介于两者之间，它是硬件实际调度 thread 的基本方式。</p>
<pre><code>CPU Host 代码
  |
  |  kernel&lt;&lt;&lt;gridDim, blockDim&gt;&gt;&gt;(args)
  v
CUDA Kernel Launch
  |
  v
Grid：一次 kernel launch 对应一个 grid
  |
  +-- Block 0  ---- threads: 0, 1, 2, ...
  +-- Block 1  ---- threads: 0, 1, 2, ...
  +-- Block 2  ---- threads: 0, 1, 2, ...
  |
  v
GPU 硬件调度
  |
  +-- SM 0 执行若干 blocks
  +-- SM 1 执行若干 blocks
  +-- SM 2 执行若干 blocks
       |
       v
     每个 block 内的 threads 被切成多个 warp
     一个 warp 通常包含 32 个 threads</code></pre>
<p>注意这里的“对应”不是一一绑定。一个 grid 可以有很多 block；一个 SM 可以先后执行很多 block；一个 block 在运行期间通常只会被放到一个 SM 上；一个 SM 上也可能同时驻留多个 block。理解这一点后，很多性能问题就能解释清楚：block 太少会导致 SM 吃不饱，block 太大可能导致寄存器或 shared memory 压力过高，warp 内分支发散会降低执行效率。</p>
</div>

<div class="card card-w">
<h3>GPU Core 到底是什么：不要把它等同于 CPU Core</h3>
<p>面试里经常会问：“GPU 有很多 core，是什么意思？”这里最重要的是：<strong>不要把 GPU core 直接类比成 CPU core。</strong></p>

<p>CPU core 通常是一个功能完整、控制能力很强的通用核心，擅长：</p>
<ul>
<li>复杂控制流；</li>
<li>分支预测；</li>
<li>乱序执行；</li>
<li>低延迟响应；</li>
<li>单线程性能。</li>
</ul>

<p>而 GPU 的所谓 “core”，通常指的是大量相对简单的计算执行单元。它们不是独立运行复杂程序的通用核心，而是被组织在 <strong>SM（Streaming Multiprocessor）</strong> 里面，用来服务大规模并行计算。</p>

<p>更准确地说：</p>
<blockquote><strong>NVIDIA GPU 的核心调度和资源管理单位是 SM，而不是单个 CUDA Core。</strong></blockquote>

<p>一个 SM 里面会包含多类执行和存储资源，例如：</p>
<ul>
<li><strong>CUDA Core</strong>：执行常规 FP32 / INT 等标量或向量计算；</li>
<li><strong>Tensor Core</strong>：执行矩阵乘加类计算，常用于 GEMM、卷积、Attention；</li>
<li><strong>Load / Store Unit</strong>：负责访存指令；</li>
<li><strong>Special Function Unit</strong>：处理特殊数学函数；</li>
<li><strong>Register File</strong>：保存线程寄存器状态；</li>
<li><strong>Shared Memory / L1 Cache</strong>：供同一个 SM 内的线程块共享和缓存数据；</li>
<li><strong>Warp Scheduler</strong>：以 warp 为单位调度指令。</li>
</ul>

<p>所以讨论 GPU 性能时，不能只看“有多少 CUDA Core”。更重要的是看：</p>
<ul>
<li>有多少 SM；</li>
<li>kernel 能不能把 SM 铺满；</li>
<li>每个 SM 里有多少 active warps；</li>
<li>访存是否连续、高效；</li>
<li>Tensor Core 是否被用起来；</li>
<li>显存带宽、L2 cache、通信是否成为瓶颈。</li>
</ul>

<div class="qa-section"><div class="qa-section-title">一个好记的类比：GPU 是工厂</div>
<p>可以把 GPU 想成一个工厂：</p>
<table>
<tr><th>GPU 组件</th><th>类比</th><th>作用</th></tr>
<tr><td>GPU</td><td>整个工厂</td><td>承接大规模并行任务</td></tr>
<tr><td>SM</td><td>车间</td><td>GPU 的主要调度和执行单元</td></tr>
<tr><td>CUDA Core</td><td>普通工位</td><td>做常规数值计算</td></tr>
<tr><td>Tensor Core</td><td>矩阵乘专用产线</td><td>加速 GEMM、卷积、Attention 等</td></tr>
<tr><td>Warp Scheduler</td><td>车间调度员</td><td>决定哪个 warp 发射指令</td></tr>
<tr><td>Register File</td><td>工位旁边的小储物格</td><td>保存线程局部数据</td></tr>
<tr><td>Shared Memory / L1</td><td>车间内共享缓存</td><td>供同一 SM 内线程快速共享数据</td></tr>
<tr><td>L2 Cache</td><td>工厂级中转仓</td><td>多个 SM 共享的数据缓存</td></tr>
<tr><td>HBM / 显存</td><td>大仓库</td><td>存放模型参数、激活、输入输出数据</td></tr>
</table>
<p>用这个类比来记：</p>
<blockquote><strong>SM 是车间，CUDA Core 是普通工位，Tensor Core 是矩阵乘专用产线。</strong></blockquote>
<p>所以真正关心的不是“工位数量”本身，而是：</p>
<ul>
<li>任务是否能拆成足够多的并行工作；</li>
<li>数据是否能及时送到工位；</li>
<li>专用产线是否被用起来；</li>
<li>车间之间是否需要频繁等待或通信。</li>
</ul>
</div>

<div class="qa-section"><div class="qa-section-title">面试官常问</div>

<p><strong>Q：GPU core 和 CPU core 有什么区别？</strong></p>
<p>CPU core 是复杂的通用核心，擅长复杂控制流、分支预测、乱序执行和低延迟单线程任务。GPU core 更轻量，数量更多，主要服务于高吞吐的数据并行计算。NVIDIA GPU 里更核心的组织单位是 SM，CUDA Core、Tensor Core、load/store unit、register file、shared memory 等资源都组织在 SM 内。GPU 不是靠少数强核心跑得快，而是靠大量线程、warp 调度、高带宽显存和专用矩阵计算单元把吞吐做上去。</p>

<p><strong>Q：为什么不能只看 CUDA Core 数量判断 GPU 性能？</strong></p>
<p>因为 CUDA Core 数量只反映了一部分标量计算资源。实际性能还取决于 SM 数量、频率、显存带宽、L2 cache、Tensor Core 能力、kernel 并行度、occupancy、访存模式、warp stall、算子是否能用 Tensor Core 等。尤其在深度学习里，GEMM、卷积和 Attention 是否跑到 Tensor Core 上，往往比单看 CUDA Core 数量更关键。</p>

<p><strong>Q：Tensor Core 和 CUDA Core 有什么区别？</strong></p>
<p>CUDA Core 主要执行常规标量或向量计算，例如 FP32、INT 等指令；Tensor Core 是专门为矩阵乘加设计的硬件单元，适合 FP16、BF16、TF32、INT8 等矩阵计算。深度学习中的 GEMM、卷积、Attention 等如果能使用 Tensor Core，性能会显著提升。但 elementwise、索引、gather/scatter、部分归约类算子不一定能用到 Tensor Core。</p>
</div>
</div>

<div class="card card-w">
<h3>Kernel 是什么：你写的一段 GPU 函数</h3>
<p><code>kernel</code> 是运行在 GPU 上的一段函数。普通 C/C++ 函数通常由 CPU 调用并在 CPU 上执行；CUDA kernel 则由 CPU 端发起，但实际在 GPU 上并行执行。你可以把 kernel 理解成“一份要在很多线程上同时执行的程序模板”。每个 thread 执行同一份 kernel 代码，但通过自己的 <code>threadIdx</code>、<code>blockIdx</code> 计算出不同的数据位置，从而处理不同元素。</p>
<pre><code class="language-cpp">__global__ void add_kernel(float* a, float* b, float* c, int n) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i &lt; n) {
    c[i] = a[i] + b[i];
  }
}

int threads_per_block = 256;
int blocks = (n + threads_per_block - 1) / threads_per_block;
add_kernel&lt;&lt;&lt;blocks, threads_per_block&gt;&gt;&gt;(a, b, c, n);</code></pre>
<p>这段代码里，<code>add_kernel</code> 是 kernel；<code>&lt;&lt;&lt;blocks, threads_per_block&gt;&gt;&gt;</code> 是 kernel launch 配置；<code>blocks</code> 决定 grid 里有多少个 block；<code>threads_per_block</code> 决定每个 block 有多少 thread。CUDA 编程模型要求开发者用 grid、block、thread 这样的层级组织并行工作，官方文档也强调理解 CUDA 编程模型有助于理解 GPU 如何执行代码[[CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html)]。</p>
<div class="qa-section"><div class="qa-section-title">学习者理解</div><p>不要把 kernel 理解成“启动一个线程”。一次 kernel launch 往往会启动成千上万个逻辑 thread。每个 thread 做的事情通常很小，比如处理一个数组元素、一个矩阵 tile 的一部分、一个 attention block 的一部分。GPU 的优势来自这些小工作被大规模并行执行。</p></div>
</div>

<div class="card card-w">
<h3>Grid：一次 kernel launch 的全部工作</h3>
<p><code>grid</code> 是一次 kernel launch 产生的全部 block 的集合。你在代码里写的 <code>kernel&lt;&lt;&lt;gridDim, blockDim&gt;&gt;&gt;</code> 中，<code>gridDim</code> 描述 grid 的形状，可以是一维、二维或三维。为什么需要二维、三维？因为很多数据天然是二维或三维的，比如图像、矩阵、卷积特征图、三维仿真网格。用二维 grid 可以让代码更贴近数据结构。</p>
<pre><code>一维 grid：处理向量
blockIdx.x * blockDim.x + threadIdx.x

二维 grid：处理矩阵
row = blockIdx.y * blockDim.y + threadIdx.y
col = blockIdx.x * blockDim.x + threadIdx.x

三维 grid：处理体数据或更复杂的张量切片
x/y/z 三个方向分别映射到数据维度</code></pre>
<p>grid 是逻辑概念，不是说 GPU 上真的有一个叫 grid 的硬件。GPU driver/runtime 会把这个 grid 中的 block 交给硬件调度，硬件再把 block 分派到 SM 上执行。block 的数量通常应该足够多，这样不同 SM 都能拿到活干，某些 block 等待访存时，SM 还能切换到其他 warp 做计算。</p>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：一次 kernel launch、grid、block 三者是什么关系？</strong></p><p>可以这样答：一次 kernel launch 会启动一个 grid，grid 是这次启动的全部 block 集合；每个 block 又包含多个 thread。grid 和 block 是软件层面的并行组织方式，GPU 硬件会把 block 调度到 SM 上执行。调优时要让 grid 里有足够多的 block，否则 SM 数量再多也可能吃不满。</p></div>
</div>

<div class="card card-w">
<h3>Block：资源分配和协作的关键边界</h3>
<p><code>block</code> 是 CUDA 里非常重要的边界。一个 block 里的 thread 可以通过 shared memory 共享数据，也可以用 <code>__syncthreads()</code> 做 block 内同步。不同 block 之间通常不能直接同步，也不能直接共享 shared memory。这个设计让 GPU 可以把不同 block 灵活分配到不同 SM 上，甚至用任意顺序执行，从而提高可调度性。</p>
<p>一个 block 在运行时会占用 SM 上的一部分资源，例如 thread slots、register、shared memory。一个 SM 能同时驻留多少个 block，取决于 block 大小、每个 thread 用多少 register、每个 block 用多少 shared memory，以及 GPU 架构限制。很多性能问题的根源就在这里：block 太小，单个 block 并行度不足；block 太大，资源占用过高，导致 SM 上同时驻留的 block/warp 变少。</p>
<div class="qa-section"><div class="qa-section-title">怎么理解 block size</div><p>常见的 <code>threads_per_block = 128</code>、<code>256</code>、<code>512</code> 不是随便写的。因为 warp 通常是 32 个 thread，所以 block size 一般会取 32 的倍数，避免最后一个 warp 只有部分 thread 有效。比如 256 threads/block 就是 8 个 warp。这个值不是越大越好，要结合 register、shared memory、访存模式和 occupancy 分析。</p></div>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：为什么不同 block 之间不能随便同步？</strong></p><p>因为 CUDA 希望 block 之间尽量独立，这样硬件可以自由调度 block 到任意 SM 上。如果 block 之间需要频繁全局同步，调度复杂度和硬件成本都会上升。通常一个 kernel 内只做 block 内同步；如果需要全局同步，最常见的方式是拆成多个 kernel launch，因为不同 kernel 之间天然有顺序边界。当然 CUDA 也有 cooperative groups 等高级能力，但面试基础题先讲清楚 block 独立性即可。</p></div>
</div>

<div class="card card-w">
<h3>Thread：逻辑上的最小并行工作单元</h3>
<p><code>thread</code> 是 CUDA 编程模型里最小的逻辑执行单元。每个 thread 有自己的 <code>threadIdx</code>，有自己的寄存器和局部变量。写 kernel 时，你通常会让每个 thread 根据自己的编号算出要处理的数据下标。</p>
<pre><code class="language-cpp">int global_id = blockIdx.x * blockDim.x + threadIdx.x;
if (global_id &lt; n) {
  // 当前 thread 处理第 global_id 个元素
}</code></pre>
<p>这里的 <code>if (global_id &lt; n)</code> 很常见，因为总线程数通常会向上取整到 block size 的倍数，最后一个 block 可能有一些 thread 超出真实数据范围。这个边界判断能防止越界访问。</p>
<div class="qa-section"><div class="qa-section-title">学习者理解</div><p>thread 不是越多越好。线程太少，GPU 吃不满；线程足够多以后，性能主要取决于访存是否连续、是否有分支发散、是否能复用数据、是否能用上 Tensor Core、是否被通信或同步拖慢。</p></div>
</div>

<div class="card card-w">
<h3>Warp：硬件真正调度的一组 thread</h3>
<p><code>warp</code> 是理解 GPU 执行效率的核心概念。CUDA 里你写的是 thread，但 NVIDIA GPU 硬件通常按 warp 调度执行，一个 warp 通常包含 32 个 thread。也就是说，SM 不是完全独立地一个 thread 一个 thread 执行，而是把一组 thread 作为调度单位。</p>
<p>这会带来两个非常重要的性能现象。第一是 <strong>分支发散</strong>：如果同一个 warp 里的不同 thread 走了不同的 <code>if/else</code> 分支，硬件通常需要分批执行不同路径，等价于一部分 thread 先闲着，另一部分执行，然后再反过来，所以效率会下降。第二是 <strong>访存合并</strong>：如果同一个 warp 里的 thread 访问连续内存，硬件可以更高效地合并内存请求；如果访问很散，带宽利用率会变差。</p>
<pre><code>理想情况：同一个 warp 的 threads 访问连续地址
thread 0 -> a[0]
thread 1 -> a[1]
thread 2 -> a[2]
...
thread31 -> a[31]

较差情况：同一个 warp 的 threads 访问分散地址
thread 0 -> a[0]
thread 1 -> a[1024]
thread 2 -> a[17]
...
thread31 -> a[99999]</code></pre>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：什么是 warp divergence？为什么会影响性能？</strong></p><p>可以这样答：warp divergence 指同一个 warp 内的 thread 因为条件分支走了不同路径。由于 warp 是硬件调度单位，不同路径往往需要被串行执行，导致部分 thread 暂时 inactive，所以有效并行度下降。优化时要尽量让同一个 warp 内 thread 执行相似路径，或者把分支改写成更规则的数据布局和计算方式。</p></div>
</div>

<div class="card card-w">
<h3>SM：block 被放到哪里执行</h3>
<p><code>SM</code> 是 Streaming Multiprocessor，是 GPU 上最关键的计算组织单元。一个 GPU 有多个 SM；一次 kernel launch 产生很多 block；GPU 会把这些 block 分配到各个 SM 上。每个 SM 内部有 warp scheduler、register file、shared memory、L1/cache 相关结构、CUDA Core、Tensor Core 等资源。</p>
<p>一个 block 被调度到某个 SM 后，它里面的 thread 会被切成多个 warp，由 SM 内部的 warp scheduler 调度执行。当某个 warp 等待 HBM 访存时，SM 可以切换去执行另一个 ready 的 warp，用大量并发来隐藏访存延迟。这也是为什么 GPU 需要很多 thread/warp：不是每个时刻所有 thread 都在算，而是通过足够多的可调度 warp 把硬件流水线填满。</p>
<div class="qa-section"><div class="qa-section-title">学习者理解</div><p>SM 像车间，block 像一个被派到车间的任务包，warp 像车间班组，thread 像班组里的工人。车间要高效运转，需要任务包足够多、班组排班合理、材料供应及时、不要有太多工人因为分支或等待内存而闲着。</p></div>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：block 和 SM 是什么关系？</strong></p><p>block 是 CUDA 编程模型里的逻辑任务块，SM 是 GPU 硬件里的执行单元。运行时，block 会被调度到 SM 上执行；一个 block 在运行期间通常不会跨多个 SM；一个 SM 可以同时驻留多个 block，具体数量受 thread 数、register、shared memory 等资源限制。</p></div>
</div>

<div class="card card-w">
<h3>CUDA 内存层级：为什么“数据怎么搬”比“怎么算”还重要</h3>
<p>很多 GPU 性能问题不是算力不够，而是数据搬不动。CUDA 程序里常见的内存层级包括 register、shared memory、L1/L2 cache、global memory/HBM。越靠近计算单元，速度越快、容量越小、使用约束越多；越远离计算单元，容量越大、延迟越高。</p>
<div class="qa-section"><div class="qa-section-title">按距离理解</div><p><strong>register</strong> 是每个 thread 私有的最快存储，适合放局部变量，但使用太多会降低 occupancy。<strong>shared memory</strong> 是 block 内 thread 共享的片上存储，适合做 tile 和数据复用。<strong>L2 cache</strong> 是多个 SM 共享的缓存，可以缓解重复访问。<strong>global memory / HBM</strong> 容量最大，模型参数、activation、KV cache 大多在这里，但访问延迟和带宽压力也最大。</p></div>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：为什么 shared memory 能加速矩阵乘？</strong></p><p>因为矩阵乘有大量数据复用。如果每个 thread 都直接从 HBM 反复读取元素，会浪费显存带宽。更好的做法是把矩阵分块，把一个 tile 先搬到 shared memory，block 内多个 thread 复用这块数据，再进行多次乘加。这样可以减少 HBM 访问，把更多时间花在计算上。</p></div>
</div>

<div class="card card-w">
<h3>把概念串起来：一个向量加法 kernel 怎么跑</h3>
<p>假设我们要计算 <code>c[i] = a[i] + b[i]</code>，数组长度是 1,000,000。CPU 端决定每个 block 256 个 thread，于是需要大约 3907 个 block。一次 kernel launch 会创建一个包含 3907 个 block 的 grid。GPU 运行时把这些 block 分派给多个 SM。每个 SM 同时驻留若干 block；每个 block 的 256 个 thread 会被切成 8 个 warp；warp scheduler 选择 ready 的 warp 执行 load、add、store。</p>
<pre><code>向量加法的执行链路：

1. CPU 调用 add_kernel&lt;&lt;&lt;3907, 256&gt;&gt;&gt;(a, b, c, n)
2. CUDA runtime 创建一个 grid，里面有 3907 个 block
3. GPU 把 block 分配给不同 SM
4. 每个 block 的 256 个 thread 被组织成 8 个 warp
5. 每个 thread 计算自己的 global_id
6. 每个 thread 从 HBM 读取 a[i] 和 b[i]
7. CUDA Core 执行加法
8. 结果写回 c[i]
9. 所有 block 完成后，这次 kernel 结束</code></pre>
<p>这个例子也说明：不是所有 GPU kernel 都能很好利用 GPU。向量加法每个元素只做一次加法，却要读两个数、写一个数，所以很容易是 memory-bound；矩阵乘每读入一块数据可以做很多乘加，更容易提高算术强度并利用 Tensor Core。</p>
</div>

<div class="card card-d">
<h3>面试标准题：CUDA kernel 的执行模型是什么？</h3>
<p><strong>标准回答：</strong>CUDA kernel 由 CPU Host 端发起，一次 kernel launch 会创建一个 grid。grid 由多个 block 组成，block 由多个 thread 组成。block 是被调度到 SM 上执行的基本单位；thread 是程序员看到的逻辑执行单元；硬件实际通常以 warp 为单位执行，一个 warp 通常包含 32 个 thread。SM 内部的 warp scheduler 会选择 ready warp 发射指令，通过让多个 warp 同时驻留来隐藏访存延迟。</p>
<table>
<tr><th>层级</th><th>属于什么</th><th>作用</th><th>面试重点</th></tr>
<tr><td>Host</td><td>CPU 端</td><td>分配显存、准备参数、发起 kernel launch</td><td><code>kernel&lt;&lt;&lt;gridDim, blockDim&gt;&gt;&gt;(args)</code></td></tr>
<tr><td>Grid</td><td>CUDA 逻辑层级</td><td>一次 kernel launch 的全部 block 集合</td><td>grid 不是硬件，而是任务组织方式</td></tr>
<tr><td>Block</td><td>CUDA 逻辑层级 + 调度边界</td><td>一组 thread，调度到某个 SM 上执行</td><td>block 内可用 shared memory 和 <code>__syncthreads()</code></td></tr>
<tr><td>Thread</td><td>CUDA 逻辑执行单元</td><td>运行同一份 kernel 代码，处理不同数据</td><td>用 <code>blockIdx</code>、<code>blockDim</code>、<code>threadIdx</code> 计算全局下标</td></tr>
<tr><td>Warp</td><td>硬件执行单位</td><td>通常 32 个 thread 一组执行同一条指令</td><td>关注 warp divergence 和 memory coalescing</td></tr>
<tr><td>SM</td><td>GPU 硬件执行单元</td><td>承载 block，调度 warp，提供 register/shared memory/CUDA Core/Tensor Core</td><td>关注 occupancy、warp stall、register pressure、shared memory</td></tr>
</table>
<div class="qa-summary">一句话背诵：Host 启动 kernel，kernel 形成 grid，grid 拆成 block，block 调度到 SM，block 内 thread 被组织成 warp，SM 以 warp 为单位执行并通过多 warp 并发隐藏内存延迟。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CUDA kernel 的执行模型是什么？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答主线</div><p>从 <code>kernel launch</code> 开始讲：CPU Host 发起 kernel，CUDA runtime 创建 grid；grid 中有多个 block；block 中有多个 thread；block 被调度到 SM 上执行；SM 把 thread 组织成 warp，并由 warp scheduler 调度 ready warp 执行。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么 block 是关键边界</div><p>block 内 thread 可以共享 shared memory，也可以用 <code>__syncthreads()</code> 同步。不同 block 默认不能直接同步，因为 block 可能被调度到不同 SM，执行顺序也不确定。如果需要全局同步，通常拆成多个 kernel launch。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么 warp 是性能关键</div><p>硬件实际按 warp 调度。一个 warp 通常 32 个 thread，同一 warp 内如果分支不同，会出现 warp divergence；如果访存地址连续对齐，可以 memory coalescing，显著提升有效带宽。</p></div>
<div class="qa-section"><div class="qa-section-title">如何联系性能优化</div><p>理解执行模型后，优化方向就很清楚：让 grid/block 足够多以铺满 SM；控制 register/shared memory 避免 occupancy 过低；减少 warp divergence；让 global memory 访问 coalesced；用 shared memory 做数据复用；能用 Tensor Core 的算子尽量满足 dtype 和 shape 条件。</p></div>
<div class="qa-summary">面试口径：CUDA 执行模型的关键不是“线程很多”，而是 grid/block/thread 的逻辑组织如何映射到 SM/warp 的硬件执行。</div>
</div>
</div>

<div class="card card-w">
<h3>面试官怎么问：从概念题到排障题</h3>
<p>如果面试官问 CUDA 层级，通常不是为了考你背定义，而是想确认你能不能从执行模型解释性能现象。建议回答时使用这个顺序：先讲 kernel launch，再讲 grid/block/thread，再讲 warp/SM，再讲内存层级，最后联系性能问题。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 请你解释一次 CUDA kernel launch 之后 GPU 上发生了什么。</div>
<div class="qa-a">
<p>一次 kernel launch 会从 CPU host 端发起，形如 <code>kernel&lt;&lt;&lt;gridDim, blockDim&gt;&gt;&gt;(args)</code>。这次 launch 对应一个 grid，grid 由多个 block 组成，每个 block 又由多个 thread 组成。GPU 会把 block 调度到 SM 上执行；block 内 thread 被组织成 warp，warp 是硬件调度的重要单位。每个 thread 运行同一份 kernel 代码，但通过 <code>blockIdx</code> 和 <code>threadIdx</code> 计算不同数据下标，从而并行处理不同数据。</p>
<div class="qa-summary">答题结构：CPU launch → grid → block → thread → block 调度到 SM → thread 组成 warp → 并行处理数据。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: grid、block、thread、warp、SM 哪些是软件概念，哪些是硬件概念？</div>
<div class="qa-a">
<p><code>grid</code>、<code>block</code>、<code>thread</code> 是 CUDA 编程模型中的逻辑概念，是程序员组织并行任务的方式。<code>SM</code> 是 GPU 硬件上的计算单元。<code>warp</code> 是硬件实际调度 thread 的重要执行单位，连接了逻辑 thread 和硬件执行。回答时可以补充：block 会被调度到 SM 上，thread 会被组成 warp 执行，一个 SM 上可以驻留多个 block/warp。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 block size 通常设置成 32 的倍数？</div>
<div class="qa-a">
<p>因为 NVIDIA GPU 通常以 warp 为单位调度 thread，一个 warp 通常是 32 个 thread。如果 block size 不是 32 的倍数，最后一个 warp 可能只有部分 thread 有效，造成执行资源浪费。当然 block size 不是只看 32 的倍数，还要看 register 使用、shared memory 使用、occupancy、访存模式和具体 kernel 的计算特征。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是 occupancy？是不是越高越好？</div>
<div class="qa-a">
<p>occupancy 可以粗略理解为 SM 上活跃 warp 数相对理论最大 warp 数的比例。它反映 SM 有多少可调度工作可以用来隐藏访存或执行延迟。但 occupancy 不是越高越好：如果一个 kernel 已经受 HBM 带宽限制，提高 occupancy 未必有用；如果为了提高 occupancy 降低单线程寄存器使用，反而导致重复访存或指令变多，也可能变慢。所以 occupancy 是诊断指标，不是最终目标。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么同一个 warp 内分支不同会变慢？</div>
<div class="qa-a">
<p>因为 warp 是硬件调度单位。同一个 warp 里的 thread 如果走不同分支，硬件通常需要分别执行不同路径：走 A 分支时，走 B 分支的 thread 暂时 inactive；再执行 B 分支时，A 分支的 thread 暂时 inactive。这样虽然逻辑上还是并行程序，但有效并行度下降了，这就是 warp divergence。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果一个 CUDA kernel 很慢，你会从哪些层级分析？</div>
<div class="qa-a">
<p>我会按执行链路分层分析。第一看 launch 配置：grid/block 是否足够让 SM 吃满；第二看 warp 层面：是否有严重分支发散、访存是否连续；第三看 SM 资源：register 和 shared memory 是否限制 occupancy；第四看内存层级：是否频繁访问 HBM、是否可以用 shared memory 做复用；第五看计算路径：是否用上 Tensor Core、shape 是否适合高性能 kernel；最后看端到端是否被 CPU 数据准备、kernel launch overhead 或多卡通信拖慢。</p>
</div>
</div>
