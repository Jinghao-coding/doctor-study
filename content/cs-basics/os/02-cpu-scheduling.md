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

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 SJF 可以降低平均等待时间？有什么问题？</div>
<div class="qa-a"><p><strong>直觉：</strong>短任务放前面，只会让长任务多等一个短任务时间；长任务放前面，会让所有短任务都等一个长任务时间。因此短任务优先能降低平均等待。</p><div class="qa-section"><div class="qa-section-title">问题</div><p>SJF 需要知道或预测运行时间，并且会让长任务饥饿。工程上通常用 aging、配额保障或最大等待时间兜底。</p></div><div class="qa-summary">面试口径：说最优性时必须补前提和饥饿问题。</div></div>
</div>
