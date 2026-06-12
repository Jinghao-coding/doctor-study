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
<h3>核心定位</h3>
<p>不考虑 Gang Scheduling 时，可以把 DeepShare 的 Kubernetes 实现拆成两层：</p>
<ul>
<li><strong>Controller</strong>：租户级资源治理 — tenant、quota、QAD、Guaranteed/Best-effort 队列、准入、抢占决策。</li>
<li><strong>Scheduler Plugin</strong>：Pod 级调度执行 — 谁先出队、能不能放到某个节点、放哪个节点、是否允许 colocation。</li>
</ul>
<p>面试一句话总结：<span class="hl">Controller 管"资源权益和队列准入"，Scheduler Plugin 管"Pod 出队和节点放置"。</span></p>
<p>调度对象简化：<strong>一个 Job 对应一个 Pod</strong>，不引入 PodGroup / minAvailable / Permit。</p>
</div>

<div class="card card-w">
<h3>5-10 分钟中文论文讲解稿</h3>
<p>这版适合面试时完整介绍，目标是让面试官听完后清楚知道：</p>
<ol>
<li>这篇论文解决什么问题；</li>
<li>为什么这个问题重要；</li>
<li>DeepShare 的核心思想是什么；</li>
<li>QAD 是什么；</li>
<li>DRA、预测调度、colocation 分别做什么；</li>
<li>Kubernetes 实现大概怎么落地；</li>
<li>实验效果说明了什么。</li>
</ol>
<p>你可以按这个版本背，也可以根据面试时间压缩。</p>
</div>

<div class="card card-d">
<h3>开场：论文定位</h3>
<p>我介绍的这篇论文是 <strong>DeepShare: Assurance-Driven Resource Management for Multi-Tenant GPU Clusters</strong>。它主要研究的是 <strong>多租户 GPU 集群中的资源管理问题</strong>。</p>
<p>简单来说，这篇论文想解决的问题是：</p>
<blockquote>
<p><strong>在多个团队共享一批 GPU 的情况下，如何既保证每个租户的 quota 和 QoS，又尽可能提高 GPU 利用率、降低作业排队时间。</strong></p>
</blockquote>
</div>

<div class="card card-d">
<h3>1. 背景和问题</h3>
<p>现在很多 AI 平台或者云平台都会有多租户 GPU 集群。比如不同团队、不同项目共用一批 GPU。为了公平，平台通常会给每个租户分配一个 quota，比如 A 团队 32 张 GPU，B 团队 16 张 GPU。</p>
<p>但是实际使用中会有一个矛盾。</p>
<p>如果我们严格按照 quota 静态隔离资源，那么就会出现资源浪费。比如 B 团队当前没有任务，它的 16 张 GPU quota 是空闲的，但 A 团队有很多任务在排队。如果系统不允许 A 使用 B 暂时空闲的 GPU，那么集群整体利用率就会下降。</p>
<p>反过来，如果系统允许 A 临时借用 B 的 GPU，又会出现另一个问题：当 B 后面提交了 Guaranteed 作业，需要拿回自己的 quota 时，资源可能已经被 A 的作业占住了。如果系统不能及时回收资源，就会破坏 B 的 QoS。</p>
<p>所以这里的核心矛盾是：</p>
<blockquote>
<p><strong>静态 quota 会降低利用率，过度共享又会破坏 QoS。</strong></p>
</blockquote>
<p>论文认为，现有系统的问题不只是某一个调度策略不好，而是 <strong>quota 管理、作业调度、抢占回收和 GPU 共享之间缺少一个统一的控制信号</strong>。</p>
<p>比如：</p>
<ul>
<li>调度器可能只看作业优先级；</li>
<li>quota 模块只看租户有没有超过 quota；</li>
<li>抢占模块只看哪个作业优先级低；</li>
<li>colocation 模块只看 GPU 是否空闲或者干扰是否低。</li>
</ul>
<p>这些模块如果各自决策，就很难同时保证 QoS 和利用率。</p>
</div>

<div class="card card-d">
<h3>2. DeepShare 的核心思想</h3>
<p>DeepShare 的核心思想是引入一个统一指标，叫 <strong>QAD，Quota Assurance Degree</strong>，也就是 <strong>配额保障程度</strong>。</p>
<p>它用来衡量：</p>
<blockquote>
<p><strong>一个租户当前 Guaranteed 资源需求中，有多少已经被满足。</strong></p>
</blockquote>
<p>也就是说，QAD 不是简单看一个租户用了多少 GPU，而是看它 <strong>应该被保障的资源有没有被保障到</strong>。</p>
<p>论文中 QAD 的作用是连接三个关键模块：</p>
<ol>
<li><strong>Elastic Quota Regulation，也就是弹性 quota 调节 / DRA</strong>；</li>
<li><strong>Predictive Scheduling，也就是基于预测的调度</strong>；</li>
<li><strong>Interference-Aware Colocation，也就是干扰感知的 GPU 共享</strong>。</li>
</ol>
<p>这三个模块都围绕 QAD 来做决策。</p>
<p>可以简单理解为：</p>
<blockquote>
<p><strong>QAD 低，说明租户保障不足，系统应该优先恢复它的 Guaranteed 作业；QAD 高，说明租户保障充分，系统可以更积极地允许资源借用和 GPU 共享。</strong></p>
</blockquote>
</div>

<div class="card card-s">
<h3>3. QAD 是什么？</h3>
<p>QAD 的直观定义是：</p>
<pre><code>QAD = 已满足的 Guaranteed 资源 / 当前应该被保障的 Guaranteed 资源</code></pre>
<p>更具体一点，瞬时 QAD 可以理解为：</p>
<pre><code>如果租户当前没有 Guaranteed demand：
    QAD = 1

否则：
    QAD = 当前已分配的 Guaranteed GPU / min(租户 quota, 当前 Guaranteed demand)</code></pre>
<p>这里分母用 <code>min(quota, demand)</code> 很关键。</p>
<p>举个例子，一个租户 quota 是 32 张 GPU。</p>
<p>如果它当前只需要 8 张 GPU，那么系统只需要保障它 8 张。只要它拿到 8 张，QAD 就是 1，而不是 8/32。</p>
<p>如果它当前提交了 100 张 GPU 的需求，但 quota 只有 32，那么系统只承诺保障 32 张，不会因为它提交了 100 张就认为系统欠它 100 张。</p>
<p>所以 QAD 避免了两个问题：</p>
<ol>
<li>租户不能通过提交超大 demand 来放大资源缺口；</li>
<li>租户当前需求小于 quota 时，也不会因为没用满 quota 而被错误认为保障不足。</li>
</ol>
<p>论文还对 QAD 做了平滑处理，因为瞬时 QAD 会因为短任务完成、突发任务到来、资源释放等事件频繁波动。</p>
<p>平滑公式是：</p>
<pre><code>Q̃_i(t) = λ Q_i(t) + (1 - λ) Q̃_i(t - 1)</code></pre>
<p>默认 <code>λ = 0.3</code>。</p>
<p>也就是说：</p>
<pre><code>当前平滑 QAD = 30% 当前瞬时 QAD + 70% 上一轮平滑 QAD</code></pre>
<p>这样系统不会因为短期波动频繁重排队列或者抢占 Best-effort 作业，但如果一个租户持续保障不足，平滑 QAD 仍然会逐步下降，从而提高它的恢复优先级。</p>
</div>

<div class="card card-m">
<h3>4. 模块一：Elastic Quota Regulation / DRA</h3>
<p>第一个模块是 <strong>DRA，弹性 quota 调节</strong>。</p>
<p>它解决的是：</p>
<blockquote>
<p><strong>怎么允许租户借用别人暂时不用的资源，同时保证这些资源之后能被回收。</strong></p>
</blockquote>
<p>DeepShare 把作业分成两类：</p>
<pre><code>Guaranteed 作业
Best-effort 作业</code></pre>
<p>Guaranteed 作业是 quota 内应该被保障的作业。它们会计入租户的 quota，并且在调度时优先级更高。</p>
<p>Best-effort 作业是机会型作业。它们可以使用集群中暂时空闲的 GPU，或者其他租户当前没有用到的 surplus capacity，但它们是可回收的。</p>
<p>这里的关键是：</p>
<blockquote>
<p><strong>Best-effort 可以借资源，但不能破坏 Guaranteed QoS。</strong></p>
</blockquote>
<p>当某个租户 Guaranteed 需求回来，导致它的 QAD 降低时，系统会优先回收 Best-effort 作业占用的资源。</p>
<p>所以 DRA 的核心逻辑是：</p>
<pre><code>有空闲资源时，提高利用率；
Guaranteed 保障不足时，回收借出去的资源。</code></pre>
<p>这就是 DeepShare 同时提升利用率和保证 QoS 的基础。</p>
</div>

<div class="card card-m">
<h3>5. 模块二：Predictive Scheduling</h3>
<p>第二个模块是 <strong>预测调度</strong>。</p>
<p>论文使用预测模型，比如 random forest，去预测作业完成时间或者剩余运行时间。这个预测信息主要有两个用途。</p>
<p>第一个用途是 <strong>队列排序</strong>。</p>
<p>DeepShare 的排序不是简单 FIFO，也不是单纯短任务优先，而是：</p>
<pre><code>Guaranteed 优先于 Best-effort；
同一类作业里，平滑 QAD 低的租户优先；
QAD 接近时，预测运行时间短的作业优先。</code></pre>
<p>也就是：</p>
<pre><code>先恢复保障不足的租户，再用短任务优先降低平均排队时间。</code></pre>
<p>这点很重要。预测运行时间只是第二排序键，它不能覆盖 QAD。也就是说，一个已经保障充分的租户，不能仅仅因为它的作业更短，就排到一个保障不足的租户前面。</p>
<p>第二个用途是 <strong>抢占代价估计</strong>。</p>
<p>如果需要回收 Best-effort 资源，系统不应该随便杀任务，而要考虑：</p>
<ul>
<li>这个任务已经运行了多久；</li>
<li>剩余运行时间大概多长；</li>
<li>是否有 checkpoint；</li>
<li>重启成本多高；</li>
<li>抢占它能不能真正释放足够 GPU；</li>
<li>抢占后能不能提升低 QAD 租户的保障程度。</li>
</ul>
<p>所以这里是一个 cost-aware preemption，而不是简单 priority-based preemption。</p>
</div>

<div class="card card-m">
<h3>6. 模块三：Interference-Aware Colocation</h3>
<p>第三个模块是 <strong>干扰感知的 GPU colocation</strong>。</p>
<p>它解决的是：</p>
<blockquote>
<p><strong>很多 GPU 作业并不能一直打满一张 GPU，如果让它们完全独占 GPU，会造成利用率浪费；但如果随便共享，又可能互相干扰，破坏 QoS。</strong></p>
</blockquote>
<p>GPU 共享的干扰来源很多，比如：</p>
<ul>
<li>显存容量；</li>
<li>显存带宽；</li>
<li>SM 算力；</li>
<li>L2 cache；</li>
<li>PCIe / NVLink；</li>
<li>CPU dataloader；</li>
<li>网络通信。</li>
</ul>
<p>所以 DeepShare 不只是看 GPU 有没有空，而是预测两个作业放在一起会不会产生过大 slowdown。</p>
<p>论文中提到使用 random forest 模型预测 colocation 干扰。如果预测干扰低于阈值，才允许 colocation。</p>
<p>而且这个阈值不是固定的，会受到 QAD 影响。</p>
<p>如果某个租户 QAD 很低，说明它的 Guaranteed 资源已经保障不足，那系统会更保守，避免它的作业受到共享干扰。</p>
<p>如果租户 QAD 较高，说明保障比较充分，系统可以更激进地允许 colocation，提高 GPU 利用率。</p>
<p>所以 colocation admission 是：</p>
<pre><code>干扰感知 + QAD 感知</code></pre>
<p>而不是单纯基于利用率。</p>
</div>

<div class="card card-s">
<h3>7. Kubernetes 实现怎么落地？</h3>
<p>论文说 DeepShare 是 Kubernetes-native，也就是它不是重新造一个集群系统，而是集成到 Kubernetes 生态里。</p>
<p>我理解比较合理的实现方式是：</p>
<pre><code>Controller + Scheduler Plugin</code></pre>
<p>Controller 负责租户级状态管理，比如：</p>
<ul>
<li>TenantQuota；</li>
<li>Guaranteed / Best-effort 队列；</li>
<li>QAD 计算；</li>
<li>DRA 准入；</li>
<li>Best-effort 回收策略。</li>
</ul>
<p>Scheduler Plugin 负责调度路径，比如：</p>
<ul>
<li>QueueSort：按 Guaranteed first、QAD low first、runtime short first 排序；</li>
<li>Filter：检查节点 GPU 是否足够、是否允许 colocation；</li>
<li>Score：做 bin packing、碎片控制和干扰最小化；</li>
<li>Reserve / Unreserve：维护资源账本；</li>
<li>PostFilter：当 Guaranteed 作业调度失败时，选择低代价 Best-effort 作业进行抢占。</li>
</ul>
<p>这里有一个关键点：</p>
<blockquote>
<p><strong>Kubernetes 默认调度器是 Pod 级的，但 DeepShare 的核心是 tenant/job 级资源保障，所以需要 Controller 维护租户级语义，再通过 Scheduler Plugin 影响 Pod 级调度。</strong></p>
</blockquote>
</div>

<div class="card card-d">
<h3>8. 实验结果</h3>
<p>论文做了两类实验。</p>
<p>第一类是 trace-driven simulation，基于 23,859 个作业的 trace。</p>
<p>结果显示：</p>
<ul>
<li>平均 GPU 利用率达到 <strong>70.58%</strong>；</li>
<li>比 Lucid 高 <strong>29.5%</strong>；</li>
<li>排队延迟降低 <strong>46%</strong>；</li>
<li>per-tenant QoS compliance 达到 <strong>93%</strong>。</li>
</ul>
<p>第二类是在 16-GPU Kubernetes 集群上的部署实验。</p>
<p>结果显示：</p>
<ul>
<li>Job Completion Time 降低 <strong>34%</strong>；</li>
<li>吞吐和资源利用都有明显提升；</li>
<li>说明系统不只是模拟有效，在 Kubernetes 原型上也有实际效果。</li>
</ul>
<p>论文还做了 ablation study。</p>
<p>比如：</p>
<ul>
<li>DRA 能降低排队延迟；</li>
<li>predictive scheduling 能进一步优化调度顺序；</li>
<li>interference-aware colocation 对降低排队延迟也有明显贡献；</li>
<li>DRA 和 colocation 结合后效果更好。</li>
</ul>
<p>这说明 DeepShare 的收益不是来自单个技巧，而是来自：</p>
<blockquote>
<p><strong>QAD 统一控制下，资源借用、预测调度和干扰感知共享的协同。</strong></p>
</blockquote>
</div>

<div class="card card-w">
<h3>9. 论文贡献总结</h3>
<p>我理解这篇论文的核心贡献有三个。</p>
<p>第一，提出了 <strong>QAD</strong> 这个连续的租户保障指标。它不是简单 quota，也不是简单资源使用率，而是衡量租户当前 Guaranteed 需求被满足的程度。</p>
<p>第二，用 QAD 把多个原本分散的资源管理决策统一起来，包括 quota 借用和回收、队列排序、抢占、colocation admission 和 QoS reporting。</p>
<p>第三，做了一个 Kubernetes-native 的资源管理系统，把 DRA、预测调度和干扰感知 colocation 结合起来，在保证 tenant QoS 的同时提高 GPU 利用率。</p>
<p>所以如果用一句话总结 DeepShare：</p>
<blockquote>
<p><strong>DeepShare 不是单纯追求更高 GPU 利用率，也不是单纯做静态 quota 隔离，而是用 QAD 这个统一指标，在多租户 GPU 集群里动态平衡 QoS 保障和资源效率。</strong></p>
</blockquote>
</div>

<div class="card card-w">
<h3>10. 面试时的收尾版本</h3>
<blockquote>
<p>我认为这篇论文最有价值的地方在于，它抓住了多租户 GPU 集群里的核心矛盾：资源空闲时希望共享，提高利用率；资源紧张时又必须恢复租户 quota 保障。DeepShare 用 QAD 把这个矛盾形式化，然后用 DRA 解决资源借用和回收，用预测调度降低排队和抢占成本，用干扰感知 colocation 提高共享效率，同时通过 Kubernetes Scheduler Framework 落地。</p>
<p>所以这篇论文的核心不是某一个单点调度算法，而是一个围绕租户资源保障的统一资源管理框架。</p>
</blockquote>
</div>
