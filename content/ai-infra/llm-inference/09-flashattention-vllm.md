<div class="card card-m">
<h3>FlashAttention V1 的三个特性</h3>
<table>
<tr><th>特性</th><th>含义</th></tr>
<tr><td>Fast（IO-Awareness）计算快</td><td>它没有减少总计算量（FLOPs），而是发现卡点不在算力而在显存读写。通过分块计算（tiling）和核函数融合（kernel fusion）降低对 HBM 的访问次数，从而加快整体速度。这种思路被称为 IO-Awareness。</td></tr>
<tr><td>Memory-Efficient 省显存</td><td>标准 attention 前向要计算并保存 N×N 注意力矩阵，反向再读取做梯度，造成 O(N²) 存储压力。FlashAttention 用 online softmax 避开保存完整矩阵，把存储压力降到 O(N)。</td></tr>
<tr><td>Exact 精确</td><td>之前的加速方法（如稀疏 attention）是近似，结果不等于标准 attention。FlashAttention 的结果与标准 attention 完全等同。</td></tr>
</table>
<div class="qa-summary">面试口径：FlashAttention 不减少计算量，而是减少 HBM 读写；它是精确的，不是近似的；核心手段是分块 + online softmax + kernel fusion。</div>
</div>

<div class="card card-d">
<h3>标准 Attention vs FlashAttention V1 复杂度对比</h3>
<table>
<tr><th>指标</th><th>标准 Attention</th><th>FlashAttention V1</th></tr>
<tr><td>计算复杂度</td><td colspan="2">两者相同，均为 $O(N^2 d)$</td></tr>
<tr><td>IO 复杂度</td><td>$O(Nd + N^2)$</td><td>$O\!\left(\dfrac{N^2 d^2}{M}\right)$（M 为 SRAM 大小，通常更小）</td></tr>
<tr><td>显存占用</td><td>$O(N^2)$</td><td>$O(N)$</td></tr>
</table>
<p>关键差别：计算量没变，但 FlashAttention 通过分块让中间矩阵不落 HBM，把 IO 和显存占用都显著降低。当 SRAM 容量 M 越大，需要的 HBM 访问越少。</p>
</div>

<div class="card card-s">
<h3>FlashAttention V2 的三点改进</h3>
<ul>
<li><strong>置换内外循环位置</strong>，同时减少非矩阵乘（non-matmul）的计算量——GPU 上非矩阵乘运算吞吐远低于矩阵乘，减少它能提速。</li>
<li><strong>优化 thread blocks 的并行化</strong>：新增 seq_len 维度的并行，让 SM 利用率尽量打满（与内外循环置换配套）。</li>
<li><strong>优化 block 内部 warp 级别的工作模式</strong>：尽量减少 warp 间通讯和读取 shared memory 的次数。</li>
</ul>
</div>

<div class="card card-m">
<h3>vLLM 抢占（preemption）：显存打满了怎么办</h3>
<p>动态分配显存能同时处理更多 prompt，但没有为每个 prompt 预留充足空间。如果某一刻显存被打满、而所有 prompt 都还没推理完，vLLM 的处理策略：</p>
<ol>
<li><strong>FCFS（First-Come-First-Serve）</strong>：优先处理最早到来的请求。</li>
<li><strong>抢占后到请求</strong>：GPU 资源不足时，为让先来的请求尽快完成，vLLM 对后到的请求执行"抢占"，暂时终止它们的执行。</li>
<li>一旦决定抢占，vLLM 会<strong>暂停处理新到来的请求</strong>，把被抢占请求的 KV block 全部 swap 到 CPU，交换完成后才继续处理新请求。</li>
<li>当 GPU 资源充足时，把 CPU 上的 KV block 重新加载回 GPU，恢复被抢占请求（或走 recomputation 重算）。</li>
</ol>
</div>

<div class="card card-w">
<h3>vLLM Swapping 策略：释放哪些、放到哪里</h3>
<p><strong>问题 1：该释放哪些 KV cache？</strong> 一个请求可能对应多个 block，理论上可以释放部分、全部，或预测低频 block 释放（实现难、性价比低）。vLLM 采取 <strong>all-or-nothing 策略</strong>：释放被抢占请求的<strong>所有</strong> block。</p>
<p><strong>问题 2：释放到哪里？</strong> 直接丢弃太浪费，vLLM 把这些 KV block 从 GPU <strong>swap 到 CPU</strong>，等 GPU 显存充足时再从 CPU 重载回来。</p>
</div>

<div class="card card-s">
<h3>vLLM Recomputation 策略</h3>
<p>知道 swapping 后，重计算就好理解了：对于某些任务（比如 parallel sampling 中并行采样数 n=1 的任务），被抢占时可以<strong>不做 swap，而是直接释放它们的物理块</strong>，把请求重新放回等待队列，等资源充足时<strong>从 prefill 阶段重新开始推理</strong>。</p>
<div class="qa-summary">Swapping 用"空间换时间"（KV 搬到 CPU 再搬回），Recomputation 用"时间换空间"（丢掉 KV 重新算）。vLLM 根据请求特征选择更划算的一种。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: LLM 推理有什么瓶颈？</div>
<div class="qa-a"><p>从算子看：decode 阶段主要算子是 GEMV（矩阵×向量），属于 memory-bound，受限于显存带宽而非算力。从内存容量看：大的 KV cache、长上下文和复杂解码算法都吃显存，KV cache 容量往往决定能并发多少请求。所以推理优化既要降低带宽压力（量化、GQA/MQA、KV cache 量化），也要提高显存利用率（PagedAttention）。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: vLLM swapping 和 recomputation 怎么选？</div>
<div class="qa-a"><p>Swapping 把被抢占请求的全部 KV block（all-or-nothing）搬到 CPU 内存，恢复时再搬回 GPU，适合 KV 较大、重算代价高的情况。Recomputation 直接丢弃 KV，把请求放回等待队列从 prefill 重算，适合 KV 较小、重算便宜的情况（如 n=1 的采样）。本质是空间换时间 vs 时间换空间的权衡。</p></div>
</div>
