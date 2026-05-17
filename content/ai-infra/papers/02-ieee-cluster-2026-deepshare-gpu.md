<div class="card card-d">
<h3>问题背景</h3>
<p>多团队共享 GPU 集群的核心矛盾：</p>
<ul>
<li><strong>配额闲置</strong>：某个团队暂时没有训练任务时 GPU 空转浪费，实测集群平均利用率只有 40%。</li>
<li><strong>配额不够</strong>：另一个团队赶 deadline 想多用几块卡，却因超配额被拒。</li>
</ul>
<p>固定配额简单但浪费严重，完全共享利用率高但无法保障 SLA。问题本质：<strong>在保障每个租户配额的前提下，把闲置资源借给需要的人，原主需要时及时收回。</strong></p>
<p>额外问题：即使 GPU 被分配出去了，很多训练任务在 I/O 或 CPU 预处理阶段 GPU 是空闲的。两个任务合用同一块 GPU 可以提升利用率，但会互相干扰——抢占 SM 和显存带宽，搞不好两个任务都变慢。</p>
</div>

<div class="card card-d">
<h3>系统设计</h3>
<p>统一控制信号——<span class="hl">配额保障度 QAD</span>，同时驱动三个子系统：</p>
<div class="formula">QAD = AG_i(t) / min(q_i, DG_i(t))</div>
<p>QAD = 1.0 恰好满足，&lt; 1.0 欠缺，&gt; 1.0 使用借来的额外资源。经 EMA 平滑避免瞬时波动。</p>

<div class="comp">
<div class="comp-t">子系统一：弹性配额借用（DRA）</div>
<p>空闲 GPU 可被其他租户借走跑低优先级任务。原主提交新任务导致 QAD 下降时，按 QAD 优先级回收——最欠缺的租户最先被满足。和固定配额的区别：闲置资源不浪费，但需要时保证能收回。</p>
</div>

<div class="comp">
<div class="comp-t">子系统二：预测性调度</div>
<p>Random Forest 预测作业运行时间（MAPE 31.84%，R² = 0.73）。调度排序采用词典序：</p>
<div class="formula">(Q̃_i(t)↑, T̂(j)↑) — 先按 QAD 升序（优先欠缺的租户），再按预测运行时间升序（短作业优先）</div>
<p>抢占牺牲者选择：代价基抢占效率</p>
<div class="formula">E_j = R_j · T̂(j) / (1 + α · C_p(j))</div>
<p>综合释放资源量 R_j、剩余时间 T̂(j) 和抢占代价 C_p(j)（已完成进度的浪费 + checkpoint 保存时间）。</p>
</div>

<div class="comp">
<div class="comp-t">子系统三：干扰感知 GPU 合用</div>
<p>Random Forest 预测两个任务共享同一块 GPU 时的性能保持率（R² = 0.902）。特征来自硬件计数器（SM activity、memory bandwidth），而非模型架构，保证跨框架泛化。只有预测保持率高于动态容忍阈值时才允许合用。运行时持续监控，实际性能下降超过容忍度时立即驱逐低优先级伙伴。</p>
</div>

<p>整个系统实现为 <strong>Kubernetes scheduler plugin</strong>，覆盖 Filter → Score → Reserve → PostFilter → Permit 五个扩展点，端到端调度延迟 &lt; 50ms。</p>

<h3>核心结果</h3>
<div class="grid">
<div class="gi"><div class="gv g">70.58%</div><div class="gl">GPU 利用率 (基线 39.64%)</div></div>
<div class="gi"><div class="gv g">−46%</div><div class="gl">排队延迟</div></div>
<div class="gi"><div class="gv g">−34%</div><div class="gl">作业完成时间</div></div>
<div class="gi"><div class="gv g">93%</div><div class="gl">QoS 合规 (QAD≥0.95)</div></div>
</div>
</div>

<div class="card card-d">
<h3>DeepShare 高频问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: QAD 和 DRF（Dominant Resource Fairness）的区别？</div>
<div class="qa-a"><p>DRF 追求均等分配，不区分保障和尽力而为。QAD 量化"距离保障配额有多远"——允许过量分配（QAD &gt; 1），但超额可回收。QAD 同时服务调度优先级、合用准入、QoS 报告三个子系统，是一个统一控制信号；DRF 只做资源分配。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 JCT 只改善 6.3% 但排队延迟改善 46%？</div>
<div class="qa-a"><p>JCT = 排队时间 + 执行时间。执行时间由计算量决定，对所有调度策略相同。调度只能影响排队部分。当执行时间占 JCT 主要部分时，排队大幅改善只带来 JCT 小幅改善。这恰好说明调度的优化空间集中在排队环节。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: nvidia.com/gpu 不可修改，GPU 共享怎么实现？</div>
<div class="qa-a"><p>K8s Extended Resource admit 后不能修改。GPU 共享通过 NVIDIA MPS 在驱动层做多路复用，设 per-client 内存限制。每块 GPU 部署一个 MPS control daemon（DaemonSet 方式）。CPU 和内存可通过 InPlacePodVerticalScaling 动态调整，但 GPU 分配必须在调度时确定。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 干扰模型为什么选 Random Forest 而不用深度学习？</div>
<div class="qa-a"><p>三个原因：(1) 推理延迟——RF 推理 &lt; 1ms，满足实时调度预算；对比 GAN-based 方法需要 50-200ms。(2) 精度足够——R² = 0.902。(3) 硬件计数器特征跨框架泛化，不需要针对每种模型架构重新训练。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 过载时怎么表现？</div>
<div class="qa-a"><p>大约 8% 高峰时段过载：按 QAD 升序优先最欠缺租户；最坏 QAD = 0.72，过载消退后 3.2 个周期（约 160ms）恢复到 ≥ 0.95。Best-effort 排队延迟增加 2.1 倍，Guaranteed 仅增加 14%，体现服务分级。</p></div>
</div>
</div>

<hr class="div">
