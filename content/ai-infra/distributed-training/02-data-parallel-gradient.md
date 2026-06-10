<div class="card card-m">
<h3>数据并行：最常见、也最容易被低估的并行方式</h3>
<p>数据并行（Data Parallelism, DP）的核心是：每张 GPU 持有一份完整模型，处理不同数据分片，每个 step 后同步梯度，保证所有副本参数一致。它的优点是实现简单、扩展直观；缺点是模型和优化器状态仍然需要每卡完整保存，通信瓶颈集中在梯度同步。</p>
</div>

<div class="card card-s">
<h3>DP / DDP 基础链路</h3>
<table>
<tr><th>阶段</th><th>每张卡做什么</th><th>通信行为</th><th>面试重点</th></tr>
<tr><td>Forward</td><td>用本地 mini-batch 计算 loss</td><td>通常无跨卡通信</td><td>每卡模型副本完整</td></tr>
<tr><td>Backward</td><td>计算本地梯度</td><td>梯度 bucket ready 后启动 AllReduce</td><td>DDP 会按 bucket 重叠通信和反向计算</td></tr>
<tr><td>Optimizer Step</td><td>用同步后的梯度更新参数</td><td>无额外通信或少量状态同步</td><td>所有副本参数保持一致</td></tr>
<tr><td>Next Step</td><td>读取下一批数据</td><td>重复上述过程</td><td>DataLoader/I/O 也可能成为瓶颈</td></tr>
</table>
</div>

<div class="card card-d">
<h3>梯度同步通信量</h3>
<p>如果模型参数量为 P，每个梯度用 FP32 表示，即 4 bytes/parameter，则一次梯度张量大小约为：</p>
<div class="formula">Gradient Size = P × 4 bytes</div>
<p>Ring AllReduce 中，每张卡的网络收发总量近似为：</p>
<div class="formula">Traffic per GPU = 2 × (N - 1) / N × Gradient Size</div>
<p>当 N 很大时，近似为：</p>
<div class="formula">Traffic per GPU ≈ 2 × P × 4 bytes</div>
</div>

<div class="card card-w">
<h3>通信-计算重叠：DDP 性能的关键</h3>
<p>DDP 不会等所有梯度都算完才统一通信，而是把参数分成多个 bucket。某个 bucket 的梯度 ready 后就立刻 AllReduce，同时后面的层继续反向计算。</p>
<table>
<tr><th>机制</th><th>作用</th><th>风险</th></tr>
<tr><td>bucket</td><td>把小梯度合并成较大通信块</td><td>bucket 太小启动开销高，太大重叠差</td></tr>
<tr><td>overlap</td><td>通信隐藏在 backward 计算后面</td><td>如果网络慢或模型小，仍然暴露通信尾巴</td></tr>
<tr><td>gradient accumulation</td><td>多次 backward 后再同步</td><td>有效 batch 变大，可能影响收敛</td></tr>
<tr><td>no_sync</td><td>累积期间禁用 DDP 同步</td><td>忘记恢复同步会导致参数不一致</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 数据并行为什么需要 AllReduce？AllReduce 同步的到底是什么？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说明每卡看到的数据不同，再说明梯度平均的数学意义，最后解释 AllReduce 的工程价值。</p>
<div class="qa-section"><div class="qa-section-title">1. 每张卡的梯度不同</div><p>DP 中每张卡处理不同 mini-batch，算出的本地梯度只代表本地数据。如果直接各自更新，模型副本会逐渐发散。</p></div>
<div class="qa-section"><div class="qa-section-title">2. AllReduce 做全局平均</div><p>AllReduce 会把所有 GPU 的梯度求和并广播回每张卡，通常再除以 world size，得到等价于更大 batch 上的平均梯度。</p><div class="formula">g = (g₁ + g₂ + ... + gₙ) / N</div></div>
<div class="qa-section"><div class="qa-section-title">3. 为什么不是 Parameter Server</div><p>AllReduce 是去中心化集合通信，没有单点参数服务器瓶颈，适合 GPU 间高带宽同步。</p></div>
<div class="qa-summary">面试口径：DP 同步的是梯度，AllReduce 让每张卡拿到全局平均梯度，从而保持模型副本一致。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 梯度累积和增大 batch size 是一回事吗？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先讲等价条件，再讲差异和副作用。</p>
<div class="qa-section"><div class="qa-section-title">1. 计算上接近等价</div><p>如果累积 k 个 micro-batch 后再做 optimizer step，在不考虑 BatchNorm、dropout 随机性和数值误差时，接近于把 batch size 扩大 k 倍。</p><div class="formula">Global Batch = micro_batch × gradient_accumulation_steps × data_parallel_size</div></div>
<div class="qa-section"><div class="qa-section-title">2. 通信频率下降</div><p>累积期间可以不做 AllReduce，等 k 次 backward 后再同步一次，通信频率降低为原来的 1/k。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 收敛可能变化</div><p>有效 batch 变大后，学习率、warmup、梯度裁剪、loss scale 都可能需要重新调参。</p></div>
<div class="qa-summary">面试口径：梯度累积是用时间换显存和通信频率，数学上接近增大 batch，但优化动态可能变化。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一个 7B 模型做 DP 训练，8 卡，每步梯度 AllReduce 的通信量大约是多少？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>明确参数量、梯度 dtype、Ring AllReduce 公式，再代入计算。</p>
<div class="qa-section"><div class="qa-section-title">1. 梯度大小</div><p>7B 参数，如果梯度用 FP32 保存，则梯度张量约为：</p><div class="formula">7 × 10⁹ × 4 bytes = 28 GB</div></div>
<div class="qa-section"><div class="qa-section-title">2. Ring AllReduce 每卡流量</div><p>8 卡 Ring AllReduce 每张卡收发总量约为：</p><div class="formula">2 × (8 - 1) / 8 × 28 GB = 49 GB</div></div>
<div class="qa-section"><div class="qa-section-title">3. 解释结果</div><p>这不是总集群流量，而是每张 GPU 网卡/互联上的近似收发量；如果网络带宽不足，这部分会成为 step time 的尾部。</p></div>
<div class="qa-summary">面试口径：7B FP32 梯度约 28GB，8 卡 Ring AllReduce 每卡约 49GB 收发量。</div>
</div>
</div>
