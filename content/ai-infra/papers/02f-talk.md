<div class="card card-s">
<h3>运行时间与共享干扰的预测</h3>
<div class="table-scroll">
<table>
<thead><tr><th>维度</th><th>运行时间预测</th><th>干扰预测</th></tr></thead>
<tbody>
<tr><td>回答的问题</td><td>这个作业还要运行多久？</td><td>两个作业放在同一张 GPU 上会慢多少？</td></tr>
<tr><td>论文模型</td><td><strong>Per-tenant gradient boosting regressor</strong></td><td><strong>Random Forest</strong></td></tr>
<tr><td>输入</td><td>租户历史作业；新租户使用 cluster-wide fallback</td><td>DCGM 硬件遥测，如 SM activity、显存带宽、L2、PCIe、Tensor Core、功耗等</td></tr>
<tr><td>输出</td><td>预测剩余运行时间 T̂(j)</td><td>预测吞吐保持率 ρ̂ = t_shared / t_excl</td></tr>
<tr><td>调度用途</td><td>QAD 之后的第二排序键；估计抢占收益与代价</td><td>Filter / Score 阶段判断能否合用以及放到哪张 GPU</td></tr>
<tr><td>安全边界</td><td>预测不覆盖 QAD；错了主要影响效率，不改变租户保障顺序</td><td>动态阈值准入；运行时连续 3 个窗口异常就驱逐 Best-effort 伙伴</td></tr>
<tr><td>论文结果</td><td>MAPE 31.84%，R² = 0.7286</td><td>R² = 0.902，推理延迟为亚毫秒级</td></tr>
</tbody>
</table>
</div>
<p><strong>记忆口诀：</strong>运行时间预测解决<strong>时间顺序</strong>，干扰预测解决<strong>空间放置</strong>；前者是 Gradient Boosting，后者才是 Random Forest。</p>
<p><strong>论文边界：</strong>原文给出了运行时间预测器的按租户训练方式、冷启动 fallback 和准确率，但没有展开它的具体特征向量。面试时不要自行补成“也使用 DCGM 特征”；DCGM 硬件计数器属于干扰预测器。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不把两个预测任务合并成一个模型？</div>
<div class="qa-a"><p>因为它们的决策对象、数据和错误后果都不同。运行时间预测面向单个作业和租户历史，回答“还要多久”，主要影响队列顺序和抢占收益；干扰预测面向作业对和硬件遥测，回答“放在一起会慢多少”，直接决定共享准入。拆开后可以独立训练、独立回退，也能分别设置安全边界。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 运行时间预测误差有 31.84%，会不会破坏公平性？</div>
<div class="qa-a"><p>不会直接破坏租户公平性，因为调度是词典序：先比较平滑 QAD，再比较 T̂(j)。预测错误只会让同一保障层级内的短作业排序不够理想，不能让一个高 QAD 租户越过一个低 QAD 租户。也就是说，QAD 决定保障顺序，运行时间用于这一顺序之内的效率优化。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 干扰预测错了怎么办？</div>
<div class="qa-a"><p>预测只负责准入，运行时监控负责兜底。系统持续根据 DCGM 指标估计吞吐保持率，连续 3 个窗口低于动态阈值就降级这对合用，并抢占 Best-effort 伙伴。这个“离线预测 + 在线纠偏”闭环，比只相信模型输出更适合生产调度系统。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你认为这项工作里最重要的设计判断是什么？</div>
<div class="qa-a"><p>最重要的判断是把预测放在保障机制之下，而不是让预测结果直接定义公平性。QAD 负责表达租户权益是否兑现，两个预测器只在不越过这条边界的前提下优化时间和空间效率。这样即使模型存在冷启动、分布漂移或预测误差，系统仍然有可解释的保障顺序和在线回退路径。</p></div>
</div>

<div class="card card-r">
<h3>容易说错的六个口径</h3>
<div class="table-scroll">
<table>
<thead><tr><th>不要这样说</th><th>正确说法</th></tr></thead>
<tbody>
<tr><td>两个模块都是 Random Forest</td><td>运行时间是 per-tenant gradient boosting；干扰预测才是 Random Forest</td></tr>
<tr><td>短作业优先决定全局顺序</td><td>QAD 是第一排序键，预测运行时间是第二排序键</td></tr>
<tr><td>预测干扰低就一定安全</td><td>还要经过动态阈值，并由连续 3 个窗口的在线监控兜底</td></tr>
<tr><td>借得越多，QAD 可以大于 1</td><td>Best-effort 借用不进入 QAD 分子，QAD 位于 0 到 1</td></tr>
<tr><td>QAD 一下降就立即杀掉 Best-effort</td><td>先按保障顺序尝试放置；Guaranteed 无法放置时才进入抢占回收</td></tr>
<tr><td>Controller 实时计算和维护 QAD</td><td>Controller 管 quota 元数据；Scheduler Plugin 维护实时 QAD 控制环</td></tr>
</tbody>
</table>
</div>
</div>
