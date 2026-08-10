<div class="card card-d">
<h3>DeepShare 高频问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: QAD 和 DRF（Dominant Resource Fairness）的区别？</div>
<div class="qa-a"><p>DRF 用 dominant share 在多资源之间追求 max-min fairness；QAD 则衡量单个租户当前 Guaranteed 权益的<strong>兑现率</strong>。QAD 的分子只算 Guaranteed allocation，Best-effort 借用单独记账，因此 QAD 位于 0 到 1，不用 QAD&gt;1 表示超额资源。QAD 还能同时驱动租户恢复排序、colocation 准入和 QoS 报告，而 DRF 主要回答公平分配问题。</p></div>
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

<div class="card card-d">
<h3>实现细节高频问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: QAD 存在哪里？调度路径如何读？</div>
<div class="qa-a"><p>论文实现中，<strong>Scheduler Plugin 在内存里维护瞬时 <code>Q_i(t)</code> 和平滑 <code>Q̃_i(t)</code></strong>。原始状态来自 informer cache 中的运行 Pod，因此故障切主后可以重建，并用首轮瞬时 QAD warm-start EMA，不需要把每轮 QAD 写回 CRD。Controller 只把 <code>TenantQuota</code> 和作业 class annotation 整理成 quota 元数据，不承担实时 QAD 控制环。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Controller 和 Scheduler Plugin 到底怎么分工？</div>
<div class="qa-a"><p><strong>Controller 管配置态，Plugin 管决策态。</strong>Controller reconcile <code>TenantQuota</code> CRD 和 <code>deepshare.io/class</code> annotation，形成租户 quota、Best-effort cap 和作业类别元数据；Scheduler Plugin 维护实时队列与 QAD，完成排序、Filter、Score、Reserve、PostFilter 抢占和 Permit 等待 resize。这样实时信号和所有放置决策留在同一个调度控制环里。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不全放 Controller？</div>
<div class="qa-a"><p>Controller 是异步 reconcile 配置态的组件，不拥有单次 scheduling cycle 的节点快照、候选打分和 assumed state。DeepShare 的 QAD、队列排序、干扰准入和抢占必须和 Filter / Score / Reserve / PostFilter 处在同一个实时控制环里，所以由 Scheduler Plugin 完成；Controller 只提供 quota 与 class 元数据。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Best-effort 是怎么借用和归还的？</div>
<div class="qa-a"><p>Scheduler 仅在没有可放置的 Guaranteed 作业、且租户 Best-effort 用量满足 <code>U_i^B + R_j ≤ η·q_i</code> 时考虑 Best-effort。Guaranteed 作业放置失败后，PostFilter 才按低代价策略选择 Best-effort victims；所以 QAD 负责决定谁更急需恢复，真正触发 GPU 抢占的是 placement failure。本质：<span class="hl">可借、单独记账、需要时可回收</span>。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 不考虑 Gang Scheduling 后流程能简化什么？</div>
<div class="qa-a"><p>不需要讲 PodGroup、minAvailable、等待全部 worker 到齐或整组回滚。论文的五个扩展点是 <strong>Filter / Score / Reserve / PostFilter / Permit</strong>；其中 Permit 只在 CPU/Memory in-place resize 发起后等待 Pod 状态更新，不用于 Gang Scheduling。如果以后支持多 worker 训练，才需要给 Permit 增加 PodGroup 级等待语义。</p></div>
</div>
</div>
