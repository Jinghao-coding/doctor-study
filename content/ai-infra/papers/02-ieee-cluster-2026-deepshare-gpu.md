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
<div class="formula">$$\mathrm{QAD} = \frac{AG_i(t)}{\min(q_i,\, DG_i(t))}$$</div>
<p>QAD = 1.0 恰好满足，&lt; 1.0 欠缺，&gt; 1.0 使用借来的额外资源。经 EMA 平滑避免瞬时波动。</p>

<div class="comp">
<div class="comp-t">子系统一：弹性配额借用（DRA）</div>
<p>空闲 GPU 可被其他租户借走跑低优先级任务。原主提交新任务导致 QAD 下降时，按 QAD 优先级回收——最欠缺的租户最先被满足。和固定配额的区别：闲置资源不浪费，但需要时保证能收回。</p>
</div>

<div class="comp">
<div class="comp-t">子系统二：预测性调度</div>
<p>Random Forest 预测作业运行时间（MAPE 31.84%，R² = 0.73）。调度排序采用词典序：</p>
<div class="formula">$$\big(\tilde{Q}_i(t)\uparrow,\; \hat{T}(j)\uparrow\big)$$</div>
<p>先按 QAD 升序（优先欠缺的租户），再按预测运行时间升序（短作业优先）。</p>
<p>抢占牺牲者选择：代价基抢占效率</p>
<div class="formula">$$E_j = \frac{R_j \cdot \hat{T}(j)}{1 + \alpha \cdot C_p(j)}$$</div>
<p>综合释放资源量 \(R_j\)、剩余时间 \(\hat{T}(j)\) 和抢占代价 \(C_p(j)\)（已完成进度的浪费 + checkpoint 保存时间）。</p>
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

<div class="card card-d">
<h3>核心定位</h3>
<p>不考虑 Gang Scheduling 时，可以把 DeepShare 的 Kubernetes 实现拆成两层：</p>
<ul>
<li><strong>Controller</strong>：租户级资源治理 — tenant、quota、QAD、Guaranteed/Best-effort 队列、准入、抢占决策。</li>
<li><strong>Scheduler Plugin</strong>：Pod 级调度执行 — 谁先出队、能不能放到某个节点、放哪个节点、是否允许 colocation。</li>
</ul>
<p>面试一句话总结：<span class="hl">Controller 管"资源权益和队列准入"，Scheduler Plugin 管"Pod 出队和节点放置"。</span></p>
<p>调度对象简化：<strong>一个 Job 对应一个 Pod</strong>，不引入 PodGroup / minAvailable / Permit。</p>
</div>

<div class="card card-d">
<h3>总体架构</h3>

<pre><code class="language-text">用户提交 GPU Job / Pod
        |
        v
DeepShare Controller
        |-- 维护 TenantQuota
        |-- 计算 QAD
        |-- 维护租户级 Guaranteed / Best-effort 队列
        |-- 做 quota admission
        |-- 给 Pod 打 annotation / 移除 schedulingGate
        |-- 必要时触发 Best-effort 抢占
        v
kube-scheduler + DeepShare Scheduler Plugins
        |-- QueueSort：QAD-aware 排序
        |-- PreFilter：解析 tenant / class / GPU request
        |-- Filter：quota、节点 GPU、共享可行性
        |-- Score：bin packing、干扰感知、碎片控制
        |-- Reserve / Unreserve：更新资源账本
        |-- PostFilter：资源不足时触发抢占候选选择
        v
Bind Pod 到 Node</code></pre>

</div>

<div class="card card-s">
<h3>为什么要拆成 Controller + Scheduler Plugin</h3>
<p>DeepShare 的核心机制（QAD、弹性配额借用、预测性调度、干扰感知合用、Best-effort 借用与回收、Guaranteed QoS）属于<strong>租户级 / 作业级</strong>逻辑；而 kube-scheduler 默认的调度对象是 <strong>Pod</strong>，原生并不知道：</p>

<ul>
<li>这个 Pod 属于哪个 tenant</li>
<li>这个 Pod 是 Guaranteed 还是 Best-effort</li>
<li>这个 tenant quota 是多少</li>
<li>这个 tenant 当前 QAD 是多少</li>
<li>这个 Pod 是否借用了别人的空闲资源</li>
<li>这个 Pod 是否应该被抢占</li>
<li>这个 Pod 与已有 GPU workload 是否会互相干扰</li>
</ul>

<table>
<thead><tr><th>模块</th><th>适合处理的问题</th></tr></thead>
<tbody>
<tr><td>Controller</td><td>租户状态、quota、QAD、队列、准入、抢占策略</td></tr>
<tr><td>Scheduler Plugin</td><td>Pod 级排序、节点过滤、节点打分、资源预留、绑定前决策</td></tr>
</tbody>
</table>
</div>

<div class="card card-m">
<h3>系统里需要的 K8S 对象</h3>

<div class="comp">
<div class="comp-t">TenantQuota CRD</div>
<p>表示每个租户的 GPU quota 与当前状态：</p>

<pre><code class="language-yaml">apiVersion: deepshare.io/v1
kind: TenantQuota
metadata:
  name: team-a
spec:
  gpuQuota: 32
  bestEffortMultiplier: 2
status:
  guaranteedDemand: 40
  guaranteedAllocated: 20
  bestEffortUsed: 8
  qad: 0.625</code></pre>

<ul>
<li><code>gpuQuota</code>：租户 Guaranteed 配额。</li>
<li><code>bestEffortMultiplier</code>：Best-effort 借用上限 η（如 η=2）。</li>
<li><code>guaranteedDemand</code>：当前 Guaranteed 需求。</li>
<li><code>guaranteedAllocated</code>：当前已满足的 Guaranteed 资源。</li>
<li><code>bestEffortUsed</code>：当前 Best-effort 使用量。</li>
<li><code>qad</code>：当前租户保障程度。</li>
</ul>
</div>

<div class="comp">
<div class="comp-t">GPU Job / Pod 的两种表达方式</div>
<p><strong>方式 A：DeepShareJob CRD</strong>（推荐，更工程化，便于做租户级排队和准入）</p>

<pre><code class="language-yaml">apiVersion: deepshare.io/v1
kind: DeepShareJob
metadata:
  name: train-a
spec:
  tenant: team-a
  class: Guaranteed
  gpu: 4
  estimatedRuntime: 3600
  preemptible: false</code></pre>

<p><strong>方式 B：原生 Pod / Job + label</strong>（轻量化）</p>

<pre><code class="language-yaml">apiVersion: v1
kind: Pod
metadata:
  name: train-a
  labels:
    deepshare.io/tenant: team-a
    deepshare.io/class: guaranteed
  annotations:
    deepshare.io/estimated-runtime: "3600"
spec:
  schedulerName: deepshare-scheduler
  containers:
  - name: train
    image: train:latest
    resources:
      limits:
        nvidia.com/gpu: 4</code></pre>

</div>

<div class="comp">
<div class="comp-t">Pod Annotation / Label（Controller 写入，调度路径读取）</div>

<pre><code class="language-yaml">metadata:
  labels:
    deepshare.io/tenant: team-a
    deepshare.io/class: guaranteed
  annotations:
    deepshare.io/qad: "0.625"
    deepshare.io/estimated-runtime: "3600"
    deepshare.io/admitted: "true"
    deepshare.io/preemptible: "false"</code></pre>

<p>Scheduler Plugin 通过这些字段做 QueueSort、Filter、Score。</p>
</div>
</div>

<div class="card card-s">
<h3>两级队列具体在哪里实现</h3>
<p>论文里的队列结构：</p>

<pre><code class="language-text">每个 tenant 有：
  Q_i^G：Guaranteed 队列
  Q_i^B：Best-effort 队列
集群级有：
  Q^G：全局 Guaranteed 候选队列
  Q^B：全局 Best-effort 候选队列</code></pre>

<div class="comp">
<div class="comp-t">第一级（租户队列）：Controller 内显式维护</div>
<p>这是 tenant/job 级语义，必须在 Controller 里：</p>

<pre><code class="language-go">type TenantQueue struct {
    TenantID         string
    GuaranteedQueue  PriorityQueue
    BestEffortQueue  PriorityQueue
}

tenantQueues map[string]*TenantQueue</code></pre>

<p>Controller watch 到新 Job 后，根据 <code>tenant</code> / <code>class</code> / <code>submitTime</code> / <code>estimatedRuntime</code> 放入对应租户队列。</p>
</div>

<div class="comp">
<div class="comp-t">第二级（全局队列）：Controller 生成候选集 + Scheduler Plugin QueueSort</div>
<p>建议回答：<strong>Controller 生成全局候选集，Scheduler Plugin 的 QueueSort 实现最终全局排序。</strong></p>

<pre><code class="language-text">Controller 不显式维护长期存在的 Q^G/Q^B 物理队列；
它周期性从各 tenant 队列里挑出 admitted jobs；
这些 admitted Pods 进入 kube-scheduler；
然后 QueueSort 按 DeepShare 规则排序。</code></pre>

<p>所以 <code>Q^G / Q^B</code> 是<strong>逻辑队列</strong>，由"admitted Pod 集合 + QueueSort 排序规则"共同体现。</p>
</div>

<div class="comp">
<div class="comp-t">为什么不完全放 Controller 排好顺序再逐个放行</div>
<ul>
<li>kube-scheduler 内部仍有自己的 ActiveQ。</li>
<li>Pod 进入 scheduler 后还会经历 backoff / unschedulable。</li>
<li>节点状态变化后，顺序需要重新评估。</li>
<li>QAD 是动态的，会持续变化。</li>
<li>调度还要结合 Filter / Score 的结果。</li>
</ul>
<p>所以更自然：<strong>Controller 控制 admission，Scheduler Plugin 控制 scheduler 内部排序和落点。</strong></p>
</div>
</div>

<div class="card card-m">
<h3>Controller 具体工作流</h3>

<div class="comp">
<div class="comp-t">Step 1 — watch Job / Pod，放入租户队列</div>
<p>用户提交 <code>team-a, Guaranteed, 4 GPU</code>，Controller 将其放入 <code>Q_a^G</code>；Best-effort 任务放入 <code>Q_a^B</code>。</p>
</div>

<div class="comp">
<div class="comp-t">Step 2 — 计算 QAD</div>
<div class="formula">$$\mathrm{QAD} = \frac{\text{Allocated GPU time}}{\text{Guaranteed GPU time}}$$</div>
<p>简化实现：</p>
<div class="formula">$$\mathrm{QAD} = \frac{\text{已满足 Guaranteed GPU}}{\min(\text{quota},\, \text{当前 Guaranteed demand})}$$</div>
<p>例：team-a quota = 32，Guaranteed demand = 40，Guaranteed allocated = 16 → QAD = 16 / min(32, 40) = 0.5。<strong>QAD 越低，租户保障越不足。</strong></p>
</div>

<div class="comp">
<div class="comp-t">Step 3 — Guaranteed admission</div>
<p>对 Guaranteed job 检查：</p>
<div class="formula">$$U_i^G + R_j \le q_i$$</div>
<p>满足则进入调度候选集；否则继续留在 <code>Q_i^G</code> 中等待。</p>
</div>

<div class="comp">
<div class="comp-t">Step 4 — Best-effort admission（更保守）</div>
<p>需同时满足：</p>
<div class="formula">$$\text{没有可放置的 Guaranteed job}\quad\text{且}\quad U_i^B + R_j \le \eta \cdot q_i$$</div>
<p><strong>含义：</strong>Best-effort 可借用空闲资源，但不能无限借，也不能挡住 Guaranteed 作业。</p>
</div>

<div class="comp">
<div class="comp-t">Step 5 — 释放 admitted Pod 到调度器</div>
<p><strong>方法 A（推荐）：移除 schedulingGate</strong></p>

<pre><code class="language-yaml">spec:
  schedulingGates:
  - name: deepshare.io/admission</code></pre>

<p>Controller 判断可以调度后移除 gate，Pod 才进入 kube-scheduler。</p>
<p><strong>方法 B：annotation 兜底</strong> — Pod 已存在但 plugin 仅放行 <code>deepshare.io/admitted: "true"</code> 的 Pod；不推荐完全依赖，因为 Pod 已进入 scheduler 后可能造成无效调度循环。</p>
</div>
</div>

<div class="card card-m">
<h3>Scheduler Plugin 的扩展点实现</h3>
<p>运行自定义调度器：<code>schedulerName: deepshare-scheduler</code>，复用 Kubernetes Scheduler Framework 加载 DeepShare 插件。</p>

<div class="comp">
<div class="comp-t">QueueSort — DeepShare 全局排序</div>
<p>排序 key（按优先级从高到低）：</p>
<ol>
<li><strong>class</strong>：Guaranteed 优先于 Best-effort。</li>
<li><strong>tenant QAD</strong>：QAD 低优先。</li>
<li><strong>predicted runtime</strong>：短任务优先。</li>
<li><strong>submit time</strong>：早提交优先（tie-breaker）。</li>
</ol>

<table>
<thead><tr><th>Pod</th><th>class</th><th>tenant</th><th>QAD</th><th>runtime</th></tr></thead>
<tbody>
<tr><td>pod-a</td><td>Guaranteed</td><td>team-a</td><td>0.4</td><td>2h</td></tr>
<tr><td>pod-b</td><td>Guaranteed</td><td>team-b</td><td>0.9</td><td>10min</td></tr>
<tr><td>pod-c</td><td>Best-effort</td><td>team-c</td><td>1.0</td><td>5min</td></tr>
</tbody>
</table>

<p>排序：<code>pod-a → pod-b → pod-c</code>。即使 pod-b 更短，team-a QAD 更低也优先。<span class="hl">先恢复保障不足的租户，再用预测运行时间优化局部顺序。</span></p>
</div>

<div class="comp">
<div class="comp-t">PreFilter — 解析调度上下文</div>

<pre><code class="language-text">读取 tenant / class / GPU request
读取 estimated runtime / QAD / preemptible
写入 cycle state，供后续插件复用</code></pre>

</div>

<div class="comp">
<div class="comp-t">Filter — 节点可放置性</div>
<ul>
<li>节点是否有足够 GPU；GPU 型号是否满足。</li>
<li>node affinity / taint toleration 是否满足。</li>
<li>共享 GPU 是否超过共享上限。</li>
<li>colocation 干扰是否在阈值内（对应论文 interference-aware colocation）。</li>
<li>Best-effort 是否会影响 Guaranteed 的资源恢复能力。</li>
</ul>
</div>

<div class="comp">
<div class="comp-t">Score — 节点打分</div>
<ul>
<li><strong>bin packing</strong>：减少碎片，2-GPU 任务优先放到刚好剩 2 张 GPU 的节点；不要打散完整 8-GPU 节点。</li>
<li><strong>GPU utilization</strong>：优先利用空闲碎片。</li>
<li><strong>interference score</strong>：选择干扰更小的 colocated 节点。</li>
<li><strong>reserved capacity</strong>：避免破坏 Guaranteed 恢复能力。</li>
<li>Best-effort 优先放到可回收、低干扰位置；Guaranteed 优先放到稳定、低干扰位置。</li>
</ul>
</div>

<div class="comp">
<div class="comp-t">Reserve / Unreserve — 维护资源账本</div>
<p>选定节点但未 Bind 时更新 DeepShare 账本：</p>

<pre><code class="language-text">tenant guaranteedUsed += gpuRequest
node   allocatedGpu  += gpuRequest
if Best-effort:
    tenant bestEffortUsed += gpuRequest</code></pre>

<p>Bind 失败时 Unreserve 回滚。<strong>很重要：</strong>避免 DeepShare 账本与 kube-scheduler assumed state 不一致。</p>
</div>

<div class="comp">
<div class="comp-t">PostFilter — 抢占</div>
<p>Guaranteed Pod 调度失败且 tenant QAD 很低时触发。Victim 选择优先级：</p>

<pre><code class="language-text">Best-effort Pod
低优先级 Pod
可抢占 Pod
抢占代价低的 Pod</code></pre>

<p>对应论文 predictive scheduling 与 preemption cost：综合 progress loss、checkpoint 状况、restart overhead，确认抢占后能真正释放足够 GPU 并提升低 QAD 租户保障。</p>
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

<div class="card card-w">
<h3>面试版完整回答（背诵展开版）</h3>
<p>如果先不考虑 Gang Scheduling，我会把 DeepShare 在 Kubernetes 里的实现拆成 Controller 和 Scheduler Plugin 两部分。<strong>Controller 负责租户级资源治理，Scheduler Plugin 负责 Pod 级调度。</strong></p>
<p>Controller 维护每个租户的 Guaranteed 队列和 Best-effort 队列，也就是论文里的 <code>Q_i^G</code> 和 <code>Q_i^B</code>。它 watch 用户提交的 GPU Job 或 Pod，读取 tenant、class、GPU request 和预测运行时间，然后放入对应租户队列。Controller 还会周期性统计每个租户的 quota 使用量，计算 QAD，并维护 TenantQuota 的 status。</p>
<p>Controller 还负责准入。对于 Guaranteed 作业，只有满足 <code>U_i^G + R_j ≤ q_i</code> 时才允许进入调度候选集；对于 Best-effort 作业，只有在没有可放置的 Guaranteed 作业，并且 <code>U_i^B + R_j ≤ η·q_i</code> 时才允许进入候选集。被准入的 Pod 通过移除 schedulingGate，或打上 admitted annotation 进入 kube-scheduler。</p>
<p>第二级集群队列由 Scheduler Plugin 的 QueueSort 实现：Controller 负责生成 admitted Pod 集合，QueueSort 在 kube-scheduler 内部按 DeepShare 规则排序——Guaranteed 优先于 Best-effort；同一类中 QAD 低的租户优先；QAD 接近时预测运行时间短的作业优先；最后用提交时间作为 tie-breaker。</p>
<p>后续 Scheduler Plugin 负责真正的节点决策。PreFilter 解析 tenant、class、GPU 需求和预测时间；Filter 检查节点 GPU 是否足够、是否满足共享和干扰约束；Score 做 bin packing、碎片控制和干扰感知打分；Reserve/Unreserve 维护 DeepShare 自己的资源账本；PostFilter 在 Guaranteed 作业调度失败且租户 QAD 很低时，选择低代价 Best-effort Pod 进行抢占。</p>
<p><strong>两个队列的实现总结：</strong>第一级租户队列在 Controller 中显式维护；第二级全局队列不一定是单独物理队列，而是<strong>由 Controller 准入后的 Pod 集合 + Scheduler Plugin 的 QAD-aware QueueSort 共同实现</strong>。这样既保留 Kubernetes-native 的调度框架，又能实现 DeepShare 的 QAD 驱动资源管理。</p>
</div>

<div class="card card-d">
<h3>面试版 60 秒背诵版</h3>
<p>不考虑 Gang Scheduling 时，Controller + Scheduler Plugin 的分工是：<strong>Controller 管 tenant/job 级逻辑，Scheduler Plugin 管 Pod/node 级逻辑。</strong></p>
<p>Controller 维护每个租户的 Guaranteed / Best-effort 队列，计算 QAD，做 quota admission 和 Best-effort cap 控制。通过准入的 Pod 才进入 scheduler。</p>
<p>Scheduler Plugin 通过 QueueSort 实现全局排序：<em>Guaranteed first，QAD low first，runtime short first</em>。然后用 Filter/Score 做节点选择和 colocation 判断，用 Reserve/Unreserve 更新资源账本，用 PostFilter 做 Best-effort 抢占。</p>
<p><span class="hl">第一级队列在 Controller 里，第二级队列由 admitted Pod 集合 + QueueSort 逻辑实现。</span></p>
</div>

<hr class="div">
