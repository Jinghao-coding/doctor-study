<h3>常见优化手段</h3>
<table>
<tr><th>技术</th><th>原理</th><th>效果</th></tr>
<tr><td>连续批处理（Continuous Batching）</td><td>请求完成立即释放位置，新请求加入，不等整批结束</td><td>吞吐提升 2-5×</td></tr>
<tr><td>张量并行（Tensor Parallelism）</td><td>单层的矩阵乘法切分到多卡并行计算</td><td>降低延迟，需 NVLink</td></tr>
<tr><td>流水线并行（Pipeline Parallelism）</td><td>不同层放不同卡，请求依次流过</td><td>支持更大模型</td></tr>
<tr><td>投机解码（Speculative Decoding）</td><td>小模型快速生成候选 token，大模型验证</td><td>延迟降低 2-3×</td></tr>
<tr><td>量化（INT8/FP8/INT4）</td><td>降低权重和激活精度</td><td>显存减半，速度提升</td></tr>
<tr><td>前缀缓存（Prefix Caching）</td><td>共享前缀的请求复用 KV 缓存</td><td>减少重复计算</td></tr>
<tr><td>CUDA Graph</td><td>录制 kernel 调用序列为图，一次提交</td><td>减少 CPU-GPU 启动开销</td></tr>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 连续批处理和传统静态批处理的区别？</div>
<div class="qa-a"><p>静态批处理：一批请求同时开始，最慢的请求完成后整批释放。短请求等长请求，GPU 空转。连续批处理（iteration-level scheduling）：每个 decode step 结束后检查，已完成的请求释放位置，等待的请求立即加入。GPU 始终满载。vLLM、TensorRT-LLM 都采用连续批处理。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 投机解码为什么能加速？不是算了两次吗？</div>
<div class="qa-a"><p>关键在于 decode 阶段是内存密集型——GPU 算力大量闲置。小模型（draft model）快速自回归生成 K 个候选 token，大模型（target model）一次性并行验证这 K 个 token（相当于做一次 prefill）。验证比逐个解码快，因为并行利用了算力。如果候选全部接受，等价于一次 forward 生成了 K 个 token。</p></div>
</div>
