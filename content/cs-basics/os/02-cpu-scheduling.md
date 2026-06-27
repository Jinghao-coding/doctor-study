## 一句话结论

CPU 调度回答的是"下一个时间片给谁"。FIFO/SJF/RR/优先级/CFS 这套单机算法，会原样迁移到 K8s、HPC 和 AI 集群里：SJF 对应短任务优先，RR 对应租户轮转，优先级对应抢占，CFS 对应公平份额。记住 CFS 靠 vruntime 选"最没跑够"的任务，目标是公平和响应而非吞吐。
<div class="card card-m">
<h3>CPU 调度算法：从单机 OS 到集群调度的共同语言</h3>
<p>CPU 调度回答“下一个时间片给谁”。这些算法也会迁移到 K8s、HPC 和 AI 集群里：FIFO 对应队列顺序，SJF 对应短任务优先，RR 对应租户轮转，优先级对应抢占，CFS 对应公平份额。</p>
</div>

<div class="card card-d">
<h3>常见调度算法对比</h3>
<table>
<tr><th>算法</th><th>规则</th><th>是否抢占</th><th>优点</th><th>缺点</th><th>AI Infra 类比</th></tr>
<tr><td>FIFO / FCFS</td><td>先到先服务</td><td>通常非抢占</td><td>简单、按到达顺序公平</td><td>队头阻塞</td><td>训练队列按提交时间排队</td></tr>
<tr><td>SJF</td><td>运行时间短的先跑</td><td>通常非抢占</td><td>降低平均等待时间</td><td>需要预测，长任务可能饥饿</td><td>短实验优先、预测驱动调度</td></tr>
<tr><td>SRTF</td><td>剩余时间最短优先</td><td>抢占式</td><td>动态到达下等待时间更低</td><td>抢占成本高</td><td>checkpoint-aware preemption</td></tr>
<tr><td>Round Robin</td><td>按时间片轮转</td><td>抢占式</td><td>响应性好，避免独占</td><td>时间片难选，切换开销</td><td>队列/租户轮转</td></tr>
<tr><td>优先级调度</td><td>高优先级先运行</td><td>可抢占或非抢占</td><td>表达业务重要性</td><td>低优任务可能饥饿</td><td>PriorityClass、队列优先级</td></tr>
<tr><td>CFS</td><td>按虚拟运行时间公平分配 CPU</td><td>抢占式</td><td>兼顾公平和交互响应</td><td>不是硬实时</td><td>公平份额、quota、dominant share</td></tr>
</table>
</div>

<div class="card card-w">
<h3>抢占式调度 vs 非抢占式调度</h3>
<table>
<tr><th>维度</th><th>抢占式</th><th>非抢占式</th></tr>
<tr><td>定义</td><td>调度器可以打断正在运行的任务</td><td>任务主动阻塞、退出或让出 CPU 才切换</td></tr>
<tr><td>响应性</td><td>高，适合交互和高优任务</td><td>低，可能被长任务卡住</td></tr>
<tr><td>开销</td><td>上下文切换更频繁</td><td>切换少，实现简单</td></tr>
<tr><td>集群类比</td><td>抢占低优训练任务，可能回滚 checkpoint</td><td>不抢占更稳定，但高优任务等待更久</td></tr>
</table>
</div>

<div class="card card-m">
<h3>CFS 深挖：vruntime、权重和 runqueue</h3>
<p>CFS（Completely Fair Scheduler）的核心思想是：不要只按固定时间片轮转，而是持续维护每个 runnable task 已经获得的“公平份额”。它用 <code>vruntime</code> 表示加权后的虚拟运行时间，倾向于选择 <code>vruntime</code> 最小的任务运行。</p>
<table>
<tr><th>概念</th><th>含义</th><th>面试解释</th></tr>
<tr><td><code>vruntime</code></td><td>加权虚拟运行时间</td><td>越小表示相对越“没跑够”，越应该获得 CPU</td></tr>
<tr><td>nice / weight</td><td>优先级权重</td><td>权重越高，同样真实运行时间带来的 <code>vruntime</code> 增长越慢</td></tr>
<tr><td>runqueue</td><td>可运行任务队列</td><td>每个 CPU 有自己的可运行任务集合，CFS 按 <code>vruntime</code> 组织任务</td></tr>
<tr><td>抢占</td><td>打断当前任务</td><td>新唤醒任务或更小 <code>vruntime</code> 任务可能触发重新调度</td></tr>
<tr><td>上下文切换</td><td>保存/恢复执行状态</td><td>线程过多、频繁阻塞唤醒会让 CPU 时间浪费在切换上</td></tr>
</table>
<p>CFS 的目标是公平和响应性，而不是让某一个任务吞吐最大。这个点和 GPU 的 warp/block 调度形成鲜明对比：GPU kernel 内部通常不追求每个 CUDA thread 的公平时间片，而是追求 SM 吞吐、occupancy 和隐藏内存延迟。</p>
</div>

<div class="card card-s">
<h3>和 CUDA 调度的层次区别</h3>
<p>Linux CFS 调度的是 OS task；CUDA Stream/Event 管的是 GPU 任务队列和依赖；CUDA block/warp 调度管的是 kernel 内部如何映射到 SM。这三层经常被混淆。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">CFS</div><div class="flow-desc">进程/线程共享 CPU 时间，强调公平和响应性</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">Stream/Event</div><div class="flow-desc">组织 H2D、kernel、D2H 的异步顺序和依赖</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">Block → SM</div><div class="flow-desc">GPU 把 grid 里的 block 分配到 SM 执行</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">Warp Scheduler</div><div class="flow-desc">SM 选择 ready warp 发射指令，隐藏访存延迟</div></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 SJF 可以降低平均等待时间？有什么问题？</div>
<div class="qa-a"><p><strong>直觉：</strong>短任务放前面，只会让长任务多等一个短任务时间；长任务放前面，会让所有短任务都等一个长任务时间。因此短任务优先能降低平均等待。</p><div class="qa-section"><div class="qa-section-title">问题</div><p>SJF 需要知道或预测运行时间，并且会让长任务饥饿。工程上通常用 aging、配额保障或最大等待时间兜底。</p></div><div class="qa-summary">面试口径：说最优性时必须补前提和饥饿问题。</div></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Linux CFS 和 CUDA thread block 调度有什么区别？</div>
<div class="qa-a"><p>CFS 是 CPU 上的操作系统调度器，调度对象是进程或线程，目标是公平性、响应性和 CPU 时间共享；CUDA thread block 调度是 GPU kernel 内部的硬件执行机制，调度对象是 grid 中的 block/CTA，目标是把 block 分配到 SM、让 warp scheduler 用 ready warp 隐藏访存延迟。CFS 通过 <code>vruntime</code>、权重、抢占和上下文切换决定哪个 task 运行；CUDA block 一旦驻留 SM 通常运行到完成，SM 内部以 warp 为单位发射指令，更强调吞吐而不是公平时间片。</p><div class="qa-summary">一句话：CFS 管 OS task 的公平 CPU 时间，CUDA block/warp 调度管 kernel 内部的高吞吐并行执行。</div></div>
</div>
