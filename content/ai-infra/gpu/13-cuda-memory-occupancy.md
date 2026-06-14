<div class="card card-s">
<h3>CUDA 内存模型：硬件视角 vs 软件视角</h3>
<p><strong>硬件视角</strong>：基本单位是 SP（Streaming Processor，也叫 CUDA Core），每个 SP 有自己的 register 和 local memory（片下内存，应对寄存器不足），只能被自己访问；多个 SP + 一块 shared memory 构成一个 SM，shared memory 被 SM 内所有 SP 共享；多个 SM + 一块全局内存构成 GPU，global memory 被所有线程访问。</p>
<p><strong>软件视角对应关系</strong>：</p>
<table>
<tr><th>软件</th><th>硬件</th><th>可见的内存</th></tr>
<tr><td>thread</td><td>SP</td><td>私有 register + local memory</td></tr>
<tr><td>block</td><td>SM</td><td>block 内共享 shared memory，可用原子操作和 barrier 同步</td></tr>
<tr><td>grid（device）</td><td>GPU</td><td>所有 thread 共享 global memory</td></tr>
</table>
<div class="qa-summary">一句话：register/local 私有，shared memory 是 block 内协作的关键，global memory 全局共享但最慢；不同 block 的线程不能直接协作。</div>
</div>

<div class="card card-m">
<h3>如何确定 grid size 和 block size</h3>
<p><strong>block size</strong>：</p>
<ul>
<li>范围 1–1024。</li>
<li>取 32（warp 大小）的倍数，避免最后一个 warp 只有部分线程有效。</li>
<li>考虑 occupancy：要能整除 SM 最大活跃线程数。主流架构 SM 最大线程数的公约数是 512，常选 <strong>128、256、512</strong>。</li>
<li>考虑 register 数量：block 太大会占用过多寄存器、降低同时驻留的 block 数，所以常折中选 <strong>128、256</strong>。</li>
</ul>
<p><strong>grid size</strong>：element-wise 程序通常让 grid size = 数据量 / block size 向上取整，并保证 block 数足够多铺满所有 SM。</p>
<pre><code class="language-cpp">int block = 256;
int grid = (n + block - 1) / block;   // 向上取整
kernel&lt;&lt;&lt;grid, block&gt;&gt;&gt;(...);</code></pre>
</div>

<div class="card card-d">
<h3>SM 利用率 vs GPU 利用率（简化口径）</h3>
<table>
<tr><th>指标</th><th>定义</th><th>含义</th></tr>
<tr><td>SM 利用率 occupancy</td><td>有效活跃线程数 / SM 最大线程数</td><td>单个 SM 内 warp 是否够多，能否隐藏访存延迟</td></tr>
<tr><td>GPU 利用率 utilization</td><td>有效 SM 数 / 总 SM 数</td><td>kernel 是否把所有 SM 都铺满</td></tr>
</table>
<p>两者结合才能判断 GPU 是否真用满：block 数太少 → GPU utilization 低（SM 吃不满）；block 内 warp 太少 / 寄存器占用过高 → occupancy 低（单 SM 隐藏延迟能力差）。</p>
</div>

<div class="card card-w">
<h3>内存墙（Memory Wall）</h3>
<p>内存墙指<strong>处理器速度与内存访问速度的不匹配</strong>：处理器算力增长远快于内存访问速度，导致内存成为瓶颈。在 CUDA 里，内存墙通常指 global memory 的高延迟、相对低带宽会拖慢 GPU。</p>
<p>缓解手段：利用 <strong>shared memory</strong> 把频繁访问的数据缓存到片上，减少对 global memory 的访问次数（典型如矩阵乘 tiling、FlashAttention 的分块），从而提升性能。这也是很多 GPU kernel 优化的核心思路——不是算得更快，而是少搬数据。</p>
</div>

<div class="card card-s">
<h3>用 PyTorch 自定义 CUDA 算子</h3>
<p>三个步骤：①编写 CUDA 算子和对应的 launch 调用函数；②编写 torch cpp 函数建立 PyTorch 与 CUDA 的联系，用 pybind11 封装；③用 PyTorch 的 cpp 扩展库编译调用。</p>
<table>
<tr><th>方式</th><th>说明</th><th>入口</th></tr>
<tr><td>JIT 编译</td><td>Python 运行时再编译 cpp/cuda 文件</td><td><code>from torch.utils.cpp_extension import load</code></td></tr>
<tr><td>SETUP 编译</td><td>setup.py 提前编译</td><td><code>from torch.utils.cpp_extension import BuildExtension, CUDAExtension</code></td></tr>
<tr><td>CMAKE 编译</td><td>编译生成 .so，运行时加载</td><td><code>torch.ops.load_library("build/libxxx.so")</code> → <code>torch.ops.xxx.torch_launch_xxx()</code></td></tr>
</table>
</div>

<div class="card card-w">
<h3>TensorCore 的输入输出数据</h3>
<p>Tensor Core 是专门做矩阵乘加（GEMM、卷积、Attention）的硬件单元。在 <strong>Volta / Turing / Ampere</strong> 架构上，计算所需输入输出数据都放在与 CUDA Core 共享的<strong>寄存器</strong>上；在 <strong>Hopper</strong> 架构上，为了获得更好的带宽，计算所需输入数据可以直接存放在<strong>共享内存</strong>上。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 block size 常取 128 / 256 / 512？</div>
<div class="qa-a"><p>一是必须是 32 的倍数（warp 大小），避免尾部 warp 浪费；二是要能整除 SM 最大活跃线程数以拿到高 occupancy（主流架构公约数 512）；三是 block 太大占用寄存器过多会减少同时驻留 block 数，所以常折中到 128 或 256。最终值要结合寄存器/shared memory 用量和实际 profiling 决定。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是内存墙，CUDA 里怎么缓解？</div>
<div class="qa-a"><p>内存墙是处理器算力增长远快于内存访问速度造成的瓶颈。CUDA 里 global memory 延迟高、带宽相对有限，容易成为瓶颈。缓解办法是把频繁复用的数据搬到 shared memory（片上）做缓存复用，减少 global memory 访问次数，例如矩阵乘 tiling 和 FlashAttention 的分块计算。</p></div>
</div>
