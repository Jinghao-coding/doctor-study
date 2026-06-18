## 一句话结论

这一节用高频问答澄清 DeepShare 的关键设计点：QAD 与 DRF 的本质区别、为何 JCT 仅改善 6.3% 而排队延迟降 46%、GPU 共享靠 NVIDIA MPS 而非改 Extended Resource、干扰模型选 RF 的延迟与泛化考量，以及 Controller 与 Scheduler Plugin 的职责切分。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 论文工作 |
| 章节类型 | 论文项目类 |
| 解决问题 | 围绕 Maestro 与 DeepShare 的问题背景、系统设计、实现细节、实验结果和高频追问建立项目叙事。 |
| 面试抓手 | 按背景、方案、实现、结果、局限回答。 |

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

<div class="card card-d">
<h3>实现细节高频问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: QAD 存在哪里？调度路径如何读？</div>
<div class="qa-a"><p>QAD 由 Controller 计算，写入 <code>TenantQuota.status.qad</code>。Scheduler Plugin 通过 informer cache 订阅这份状态，本地维护 <code>tenantID → qad</code> 映射。QueueSort 与 Filter 不直接 RPC Controller，只读本地 cache，避免调度热路径阻塞。结果是<strong>低延迟、最终一致、调度路径不阻塞</strong>。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不全放 Scheduler Plugin？</div>
<div class="qa-a"><p>Scheduler Plugin 是 Pod 调度热路径上的组件，适合做快速决策（排序、过滤、打分）；但租户队列、quota 统计、QAD 计算、job admission、Best-effort cap 这些是<strong>全局状态管理</strong>，放在 Controller 更合适。Controller 可以异步 watch 集群状态并维护租户级资源账本，避免把复杂全局逻辑塞进调度热路径。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不全放 Controller？</div>
<div class="qa-a"><p>Controller 可以决定哪些 Pod 被释放，但 Pod 进入 kube-scheduler 后，真正的<strong>出队顺序、节点过滤、节点打分、抢占</strong>都是 scheduler 决定。DeepShare 需要影响 Pod 级调度过程（QAD-aware QueueSort、interference-aware Filter/Score、Reserve 账本更新、PostFilter 抢占），所以必须 Scheduler Plugin 与 Controller 配合。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Best-effort 是怎么借用和归还的？</div>
<div class="qa-a"><p>Best-effort Pod 由 Controller 做准入，<strong>仅当没有可放置的 Guaranteed 作业，且租户 Best-effort 使用量未超过 cap（η·q_i）</strong> 时才允许进入调度。当某租户 Guaranteed 需求回来导致 QAD 下降，Controller 或 PostFilter 会触发资源回收：优先选择 Best-effort、可抢占、抢占代价低的 Pod 作为 victim，抢占后释放 GPU，低 QAD 租户的 Guaranteed Pod 重新进入调度。本质：<span class="hl">可借但可回收</span>。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 不考虑 Gang Scheduling 后流程能简化什么？</div>
<div class="qa-a"><p>不需要讲 PodGroup / minAvailable / Permit waiting / Reserve 多 Pod 后统一放行 / 超时整体回滚。流程简化为"一个 Pod 满足条件 → 直接调度"。Scheduler Plugin 先实现 <strong>QueueSort / PreFilter / Filter / Score / Reserve / Unreserve / PostFilter</strong> 即可，不重点讲 Permit。如果面试官追问分布式训练，再补充：<em>"如果后续要支持多 worker 训练，再引入 PodGroup 和 Permit 扩展点做 Gang Scheduling。"</em></p></div>
</div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
