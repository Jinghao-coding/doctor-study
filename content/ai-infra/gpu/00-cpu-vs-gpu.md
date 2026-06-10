<div class="card card-m">
<h3>CPU vs GPU：设计哲学的根本差异</h3>
<p>CPU 和 GPU 的架构差异，本质上源于设计目标不同：CPU 追求<strong>单线程低延迟</strong>，GPU 追求<strong>大规模吞吐</strong>。</p>
<table>
<tr><th>维度</th><th>CPU</th><th>GPU</th></tr>
<tr><td>设计目标</td><td>低延迟、强控制流、通用</td><td>高吞吐、数据并行、专用</td></tr>
<tr><td>核心数量</td><td>少量（4–128），每个核心强大</td><td>大量（数千 CUDA Core），每个核心轻量</td></tr>
<tr><td>核心复杂度</td><td>复杂：分支预测、乱序执行、深流水线、大缓存</td><td>简单：ALU 为主，控制逻辑极简</td></tr>
<tr><td>时钟频率</td><td>高（3–5 GHz）</td><td>较低（1–2 GHz）</td></tr>
<tr><td>缓存</td><td>L1/L2/L3 很大，单核 L1 可达 64KB+</td><td>L1/Shared Memory 小（每 SM 128–228KB），L2 中等</td></tr>
<tr><td>内存</td><td>DDR，容量大（数百 GB），带宽中等（~100 GB/s）</td><td>HBM，容量小（40–141 GB），带宽极高（2–4.8 TB/s）</td></tr>
<tr><td>延迟容忍</td><td>靠预测、缓存和乱序隐藏延迟</td><td>靠大量并发 warp 切换隐藏延迟</td></tr>
<tr><td>编程模型</td><td>串行 + 少量并行（线程/进程）</td><td>SPMD：同一 kernel 在数千线程上同时执行</td></tr>
</table>
</div>

<div class="card card-s">
<h3>为什么 GPU 适合深度学习？</h3>
<p>深度学习的计算特征恰好匹配 GPU 的设计优势：</p>
<ol>
<li><strong>大量矩阵乘法</strong>：神经网络的核心运算是 GEMM（通用矩阵乘法），天然高度并行。GPU 的 Tensor Core 专门加速矩阵乘加，一个周期完成 m×n×k 小矩阵 tile 的乘加。</li>
<li><strong>数据并行度高</strong>：训练时 batch 中每个样本的计算独立，可以轻松映射到数千线程。推理时多请求并发、多 token 并行处理，也是数据并行。</li>
<li><strong>高带宽显存</strong>：模型参数、激活值、KV cache 的频繁读写需要极高带宽。A100 的 2 TB/s、H100 的 3.35 TB/s 远超 CPU DDR 带宽。</li>
<li><strong>延迟可容忍</strong>：单个线程的延迟不如 CPU，但深度学习不需要单线程低延迟——它需要的是整体吞吐。GPU 通过大量并发线程让整体计算量在时间上铺满。</li>
</ol>
<div class="qa-summary">一句话：深度学习的核心是大量矩阵乘法 + 高数据并行 + 高带宽需求，GPU 恰好在这三方面有硬件级加速。</div>
</div>

<div class="card card-w">
<h3>一个类比：CPU 像几个博士，GPU 像一万个中学生</h3>
<p>CPU 像几个博士，每人能独立解决复杂问题，但人数少，总产出有限。GPU 像一万个中学生，每人只能做简单计算，但可以同时开工，如果任务能拆成一万个简单步骤，总产出远超几个博士。</p>
<p>深度学习正好是这样的任务：矩阵乘法可以拆成海量独立的乘加操作，每个操作都很简单，但数量巨大。所以 GPU 的"人多力量大"策略远比 CPU 的"少而精"策略高效。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CPU 能不能做深度学习训练？</div>
<div class="qa-a"><p>能，但非常慢。CPU 缺乏大规模并行计算单元和 Tensor Core，显存带宽也远低于 GPU。同样一个 GEMM，GPU 可能几微秒完成，CPU 需要几十到几百微秒。对于小模型或调试可以用 CPU，但生产训练和推理几乎都用 GPU 或其他加速器。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 为什么不能替代 CPU？</div>
<div class="qa-a"><p>GPU 不擅长复杂控制流、分支预测、操作系统调度、IO 处理和低延迟串行任务。它需要 CPU 来发起 kernel launch、准备数据、处理逻辑和控制流程。CPU 和 GPU 是协作者，不是替代关系。</p></div>
</div>
