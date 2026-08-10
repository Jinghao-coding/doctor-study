<div class="card card-w">
<h3>先记住这条七步主线</h3>
<p><strong>背景冲突 → 现有缺口 → QAD → 弹性借用 → 预测调度 → 干扰感知合用 → 实现与结果</strong></p>
<p>正常语速讲 4～5 分钟；面试官打断后，再进入公式、预测器或 Kubernetes 实现细节。</p>
</div>

<div class="card card-s">
<h3>两个预测模块先彻底分开</h3>
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

<div class="qa open" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 请挑一个你最熟悉的工作介绍一下。</div>
<div class="qa-a">

<h3>1. 背景：固定配额和资源共享存在天然矛盾</h3>

<p>我想介绍一下 DeepShare，这是我们面向多租户 GPU 集群设计的、以配额保障为核心的资源管理系统。</p>

<p>它的背景是，企业里的 GPU 集群通常由多个团队共享。平台会给每个租户一个 quota 来保证公平，例如 A 团队 32 张卡、B 团队 16 张卡。但是各团队的需求具有明显的突发性：B 当前没有任务时，如果它的 16 张卡仍被静态保留，A 的作业即使在排队也不能使用，集群利用率会很低；如果允许 A 借用，B 的 Guaranteed 作业回来时，又必须及时拿回自己的资源，否则 quota 只是纸面承诺。</p>

<p>GPU 内部还有第二层浪费。很多训练作业受数据加载、CPU 或通信阶段影响，并不会一直打满 SM 和显存带宽。把两个作业放在同一张 GPU 上可以提升利用率，但盲目合用会产生不可控干扰，反而拖慢 Guaranteed 作业。</p>

<p>因此核心矛盾是：<strong>既想通过跨租户借用和卡内合用提升利用率，又必须把租户的配额保障真正兑现出来。</strong></p>

<h3>2. 动机：现有方法分别优化局部，却没有统一保障语义</h3>

<p>现有工作往往只解决其中一个局部问题：固定 quota 能保证隔离但浪费资源；短作业优先能降低平均等待，却可能让某些租户长期得不到保障；GPU sharing 能提高利用率，却不一定知道当前能否承受干扰。</p>

<p>所以我们的判断是，问题不只是缺少一个更复杂的调度算法，而是 quota 借用、队列排序、抢占回收和 GPU 合用之间，缺少一个统一的反馈信号。系统需要随时回答：<strong>哪个租户当前最欠保障？</strong></p>

<h3>3. 核心设计：用 QAD 表示配额兑现程度</h3>

<p>DeepShare 引入 QAD，也就是 Quota Assurance Degree：</p>

<div class="formula">$$Q_i(t)=\frac{A_i^G(t)}{\min\!\left(q_i,D_i^G(t)\right)}$$</div>

<p>分子 A_i^G(t) 是已经分给租户 i 的 Guaranteed GPU 数量；分母 min(q_i, D_i^G(t)) 是系统此刻真正应该保障的 GPU 数量，也就是 quota 和当前 Guaranteed demand 中较小的一个。直观上就是：<strong>已经兑现多少 / 此刻应该兑现多少</strong>。</p>

<p>如果租户没有 Guaranteed demand，QAD 直接定义为 1，因为“暂时没用 quota”不等于“被系统亏待”。Best-effort 借来的卡不计入分子，所以 QAD 的范围是 0 到 1，不会因为借用资源大于 1。系统还用 EMA 平滑瞬时 QAD，避免短任务完成或突发请求造成频繁抖动。</p>

<h3>4. QAD 统一驱动三个机制</h3>

<p><strong>第一，弹性配额借用 DRA。</strong>租户没有用满 quota 时，闲置 GPU 可以借给其他租户运行 Best-effort 作业；原租户的 Guaranteed demand 回来后，如果资源不足，系统就回收这些可借用资源。这样 quota 从静态分区变成了“可借但必须能还”的保障承诺。</p>

<p><strong>第二，QAD-first 的预测调度。</strong>调度器先按平滑 QAD 升序选择租户，保障不足的租户先调度；只有在 QAD 相同或接近时，才使用预测剩余运行时间让短作业优先。抢占时也会结合可释放的资源、剩余时间和抢占代价选择 victim。因此，预测负责优化效率，QAD 负责守住公平性。</p>

<p><strong>第三，QAD-aware 的干扰感知合用。</strong>系统预测两个作业共享 GPU 后的吞吐保持率，并结合当前资源压力和租户 QAD 动态调整准入阈值。租户越欠保障，系统对它受到的干扰越保守；保障充分时，才更积极地合用 GPU。</p>

<h3>5. 两个预测模块分别怎么做</h3>

<p><strong>运行时间预测模块：</strong>我们观察到租户的提交具有重复性，78% 的用户会反复提交特征和时长相近的作业，因此论文正文采用 per-tenant gradient boosting regressor，利用每个租户自己的历史作业学习其工作负载规律，输出预测剩余运行时间 T̂(j)。历史不足的新租户使用 cluster-wide fallback model。它有两个用途：一是在 QAD 之后作为第二排序键，降低平均排队时间；二是在抢占时帮助判断一个 victim 还剩多久、现在打断是否划算。Venus 23,859 个作业上的 MAPE 是 31.84%，R² = 0.7286。历史提交不少于 50 次的租户 MAPE 小于 25%，冷启动 fallback 的 MAPE 小于 60%。原文没有进一步列出该模型的具体特征向量，所以面试时不要自行补成 DCGM 特征。</p>

<p><strong>干扰预测模块：</strong>这里使用的是 Random Forest。输入不是模型名字，而是 DCGM 采集的硬件遥测，例如 SM activity、显存带宽、L2、PCIe、Tensor Core、DRAM throughput 和功耗等；输出是两个作业合用时的吞吐保持率 ρ̂。采用硬件计数器有两个好处：一是跨框架、跨模型更容易泛化；二是 Random Forest 可以在 scheduler 关键路径上实现亚毫秒级推理。论文中该模型的 R² = 0.902。</p>

<p>预测本身不是安全保证，所以 DeepShare 还做了运行时闭环。DCGM 会持续监控实际保持率；如果连续 3 个采样窗口低于容忍阈值，就把这对合用标为 degraded，并在下一调度周期驱逐 Best-effort 伙伴，优先保护 Guaranteed 作业。</p>

<h3>6. 工程实现和实验结果</h3>

<p>工程上，我们把系统实现成 Kubernetes 的轻量 Controller 加 Scheduler Plugin。Controller 负责 TenantQuota 和作业类别等静态元数据；Plugin 维护实时 QAD 和两级队列，并在 Filter、Score、Reserve、PostFilter、Permit 等扩展点完成合用准入、放置、资源预留和抢占。</p>

<p>在 Venus 23,859 个作业的 trace-driven 实验中，DeepShare 把 GPU 利用率从 39.64% 提高到 70.58%，相对 Lucid 提升 29.5%；平均排队时间相对 Lucid 降低 46%。消融实验中，移除运行时间预测后排队时间增加 18.4%，移除干扰感知后增加 30.1%。在 16-GPU 物理集群上，完整方案相对 Hard+Colocate 将 makespan 降低 32%、JCT 降低 34%、排队时间降低 66%，租户周期的 QoS 合规率达到 93%。</p>

<h3>7. 收尾：这项工作的核心贡献</h3>

<p>所以我认为 DeepShare 最关键的贡献，不是单独提出一个预测器或一个共享策略，而是把<strong>配额保障变成一个可观测、可反馈的 QAD 控制信号</strong>，再让弹性借用、时间调度和空间合用围绕同一个目标闭环。最终实现的是：资源空闲时敢于共享，租户保障不足时能够及时、可解释地收回来。</p>

</div>
</div>

<div class="card card-m">
<h3>面试官打断时，用这四句保住主线</h3>
<ol>
<li><strong>背景：</strong>固定 quota 保公平但浪费，动态共享提利用率但可能还不回来，也可能引入干扰。</li>
<li><strong>核心：</strong>QAD = 已经兑现的 Guaranteed GPU / 此刻应该兑现的 Guaranteed GPU。</li>
<li><strong>设计：</strong>QAD 同时控制资源借用与回收、队列排序与抢占、GPU 合用准入。</li>
<li><strong>预测器：</strong>Gradient Boosting 预测剩余时间、优化先后顺序；Random Forest 预测共享干扰、优化放置位置。</li>
</ol>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不把两个预测任务合并成一个模型？</div>
<div class="qa-a"><p>因为它们的决策对象、数据和错误后果都不同。运行时间预测面向单个作业和租户历史，回答“还要多久”，主要影响队列顺序和抢占收益；干扰预测面向作业对和硬件遥测，回答“放在一起会慢多少”，直接决定共享准入。拆开后可以独立训练、独立回退，也能分别设置安全边界。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 运行时间预测误差有 31.84%，会不会破坏公平性？</div>
<div class="qa-a"><p>不会直接破坏租户公平性，因为调度是词典序：先比较平滑 QAD，再比较 T̂(j)。预测错误只会让同一保障层级内的短作业排序不够理想，不能让一个高 QAD 租户越过一个低 QAD 租户。也就是说，QAD 是安全主键，运行时间只是效率次键。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 干扰预测错了怎么办？</div>
<div class="qa-a"><p>预测只负责准入，运行时监控负责兜底。系统持续用 DCGM 观察实际吞吐保持率，连续 3 个窗口低于动态阈值就降级这对合用，并抢占 Best-effort 伙伴。这个“离线预测 + 在线纠偏”闭环，比只相信模型输出更适合生产调度系统。</p></div>
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
