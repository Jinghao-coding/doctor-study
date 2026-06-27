## 一句话结论

集群调度器架构经历了"集中式（Borg/K8s）→ 两级调度（Mesos/YARN）→ 共享状态（Omega）→ 混合/分布式（Firmament）"的演进，核心矛盾是"全局最优决策 vs 可扩展性 vs 并行调度"。AI 训练集群（万卡规模、Gang 调度、拓扑感知）更适合集中式 + 缓存 + 乐观并发的 Borg 风格架构，而不是纯分布式调度。
<div class="card card-m">
<h3>为什么调度器架构重要？</h3>
<p>调度器的架构决定了三个核心问题：</p>
<ol>
<li><strong>决策质量（Optimality）</strong>：能否做出全局最优的放置决策？还是只能看到局部信息？</li>
<li><strong>可扩展性（Scalability）</strong>：集群规模到 1 万、10 万节点时还能工作吗？每秒能调度多少任务？</li>
<li><strong>并发度（Concurrency）</strong>：多个调度器/多个框架能不能并行做决策？冲突怎么解决？</li>
</ol>
<p>这三个目标是互相矛盾的：全局最优需要看所有信息，但全局信息在大规模下难维护；并行决策提高吞吐，但会产生冲突。不同架构就是在这个三角中做不同的权衡。</p>
</div>

<div class="card card-s">
<h3>架构一：集中式/单体调度器（Centralized/Monolithic）</h3>
<p><strong>代表系统</strong>：Google Borg、Kubernetes 默认调度器、早期 Hadoop MapReduce</p>

<h4>核心设计</h4>
<p>所有调度决策都由<strong>一个中央调度器进程</strong>做出。所有任务提交到全局队列，调度器按顺序处理，一个一个地做"可行性检查（Filter）+ 打分（Score）+ 绑定（Bind）"。</p>

<h4>Borg 的关键设计</h4>
<ul>
<li><strong>Cell 规模</strong>：单个 Borg cell 可以管理上万台机器，同时运行数千个作业、数十万个任务</li>
<li><strong>两阶段调度</strong>：先做 feasibility check（过滤掉不满足资源/约束的节点），再做 scoring（对可行节点按优先级、资源匹配度、抢占代价等打分），选最高分节点</li>
<li><strong>共享状态缓存</strong>：调度器有本地缓存（watch API Server），不需要每次都查全量状态，提高调度吞吐</li>
<li><strong>优先级 + 抢占</strong>：高优先级任务可以抢占低优先级任务，保证线上服务质量</li>
<li><strong>资源回收（Reclamation）</strong>：对低优先级任务使用的"预留但未使用"的资源进行回收，给高优任务用</li>
</ul>

<h4>K8s 默认调度器</h4>
<p>K8s kube-scheduler 是典型的集中式调度器：</p>
<ul>
<li>单进程运行，通过 Informer 缓存集群状态</li>
<li>调度周期：Scheduling Queue → Filter → Score → Reserve → Permit → Bind</li>
<li>默认串行调度一个 Pod，可通过 scheduler framework 扩展</li>
<li>v1.26+ 支持 Scheduler Profile，可配置多个不同配置的调度器，但本质还是"多个集中式调度器"，每个调度器还是单进程串行</li>
</ul>

<h4>优缺点</h4>
<table>
<tr><th>维度</th><th>评价</th></tr>
<tr><td>决策质量</td><td>高——能看到全局状态，做出全局最优（或近似最优）决策</td></tr>
<tr><td>实现复杂度</td><td>低——所有逻辑在一个进程里，没有分布式一致性问题</td></tr>
<tr><td>可扩展性</td><td>有瓶颈——单进程调度吞吐有限，万级节点集群需要性能优化（缓存、增量调度、近似算法）</td></tr>
<tr><td>多框架支持</td><td>差——所有任务类型都要适配同一套调度逻辑，框架定制难</td></tr>
</table>

<div class="card card-d">
<p><strong>Borg 怎么解决单进程瓶颈？</strong></p>
<ul>
<li><strong>乐观并发</strong>：调度时基于缓存做决策，Bind 时如果资源已被占用就重试，不需要全局锁</li>
<li><strong>分 Cell</strong>：不是一个大集群管所有机器，而是分成多个独立的 cell（每个 cell 几万台机器），每个 cell 有自己的调度器</li>
<li><strong>批量调度</strong>：对同类型的小任务做批量调度，减少重复计算</li>
<li><strong>得分近似</strong>：不需要绝对最优，对 top-K 节点做精确打分，其余快速过滤</li>
</ul>
</div>
</div>

<div class="card card-s">
<h3>架构二：两级调度（Two-Level / Two-Tier）</h3>
<p><strong>代表系统</strong>：Apache Mesos、Hadoop YARN</p>

<h4>核心设计思想</h4>
<p>把调度分成两层：</p>
<ol>
<li><strong>第一层（中央 Resource Master）</strong>：决定"给哪个框架多少资源"，负责资源分配和公平性</li>
<li><strong>第二层（框架调度器 Application Master）</strong>：决定"把这些资源给我的哪个任务、启动在哪里"，框架自己做任务调度</li>
</ol>
<p>关键机制是<strong>资源 Offer（资源邀约）</strong>：Master 主动给框架发 Offer（"我这儿有这些空闲资源，你要不要？"），框架接受或拒绝。</p>

<h4>Mesos 具体工作流程</h4>
<pre><code>1. Slave 节点上报空闲资源给 Mesos Master
2. Master 按 DRF（Dominant Resource Fairness）算法决定给哪个 Framework 发 Offer
3. Master 向 Framework Scheduler 发送 Resource Offer
4. Framework 检查 Offer：符合自己需求就 Accept，否则 Decline
5. Accept 的话，Framework 告诉 Master 在哪些节点上启动哪些 Task
6. Master 把 Task 发给对应 Slave 的 Executor 启动</code></pre>

<h4>DRF 公平性</h4>
<p>Mesos 用 DRF 做多资源公平分配：每个框架有一个"主导资源（Dominant Share）"——对 CPU 密集型框架是 CPU 份额，对内存密集型是内存份额，对 GPU 训练是 GPU 份额。DRF 让所有框架的主导资源份额相等，这是多资源下的 max-min 公平。</p>

<h4>优缺点</h4>
<table>
<tr><th>维度</th><th>评价</th></tr>
<tr><td>多框架支持</td><td>非常好——Hadoop/Spark/MPI/在线服务都可以接入，每个框架有自己的调度逻辑</td></tr>
<tr><td>可扩展性</td><td>好——框架并行调度，Master 只做资源分配不做任务调度，压力小</td></tr>
<tr><td>决策质量</td><td>低——框架只能看到 Master 给自己的 Offer，看不到全局资源；"Pessimistic Offer"策略下给了一个框架的资源其他框架暂时不能用，资源利用率低</td></tr>
<tr><td>优先级反转风险</strong>：高——低优框架拿了 Offer 但不释放，高优框架等不到资源；或者框架拒绝了 Offer 但资源在 Offer 期间被锁</td></tr>
<tr><td>实现复杂度</td><td>中——两层之间需要协议，框架需要自己实现调度逻辑</td></tr>
</table>

<div class="card card-w">
<p><strong>Mesos Offer 机制的问题</strong>：</p>
<ul>
<li><strong>悲观并发（Pessimistic Concurrency）</strong>：资源 Offer 发给一个框架后，这些资源在被接受/拒绝/超时前，其他框架看不到——相当于被锁住了，利用率低</li>
<li><strong>框架信息不全</strong>：框架不知道"下一个 Offer 什么时候来"、"还有多少资源"，可能做出次优决策（比如接受一个不够大的 Offer，因为怕等不到更好的）</li>
<li><strong>不适合 Gang Scheduling</strong>：大的分布式训练需要同时拿到 N 张 GPU，但 Offer 是分批给的，框架很难凑齐 Gang</li>
</ul>
<p>这也是为什么 Mesos 在 AI 训练场景用得不多——Gang 调度和拓扑感知需要全局视图。</p>
</div>
</div>

<div class="card card-s">
<h3>架构三：共享状态调度（Shared-State）</h3>
<p><strong>代表系统</strong>：Google Omega、Microsoft Apollo</p>

<h4>核心设计思想</h4>
<p>针对两级调度"框架看不到全局状态"和集中式"单进程瓶颈"的问题，Omega 提出了<strong>共享状态 + 乐观并发控制</strong>：</p>
<ol>
<li><strong>全集群状态复制</strong>：每个调度器（可以有多个，每个可以负责不同类型任务）都有一份完整的、一致的集群状态副本（通过 Paxos/Raft 类共识协议复制）</li>
<li><strong>并行独立决策</strong>：每个调度器基于自己看到的全局状态，<strong>独立、并行地</strong>做调度决策，不需要等 Master 分配 Offer</li>
<li><strong>事务提交冲突解决</strong>：调度器做出决策后，以<strong>事务（Transaction）</strong>的形式提交到共享状态存储。如果两个调度器的决策冲突（比如同时把同一个任务/资源分配给了不同地方），其中一个事务会 abort，重试即可</li>
</ol>
<p><strong>和 Mesos 的本质区别</strong>：Mesos 是"悲观锁"——Offer 期间资源被锁；Omega 是"乐观并发"——大家都能看、都能改，冲突了再重试。</p>
<p><strong>和集中式的本质区别</strong>：集中式只有一个调度器做决策；Omega 可以有多个调度器并行做决策，每个都看全局状态。</p>

<h4>工作流程</h4>
<pre><code>1. 所有 Cell State 通过 Paxos 复制到每个 Scheduler 副本
2. Scheduler A 和 Scheduler B 同时看到全局空闲资源
3. Scheduler A 决策：任务 X 放节点 1，生成事务 T1
4. Scheduler B 决策：任务 Y 放节点 1，生成事务 T2
5. T1 先提交成功，节点 1 资源被标记为已用
6. T2 提交时发现节点 1 资源不足，abort，Scheduler B 基于新状态重新决策
7. Scheduler B 重试：任务 Y 放节点 2，提交成功</code></pre>

<h4>优缺点</h4>
<table>
<tr><th>维度</th><th>评价</th></tr>
<tr><td>决策质量</td><td>高——每个调度器都能看到全局状态，和集中式一样</td></tr>
<tr><td>并发度</td><td>高——多个调度器并行决策，没有中央瓶颈</td></tr>
<tr><td>多框架支持</td><td>好——不同框架可以有自己的调度器，共享全局视图</td></tr>
<tr><td>冲突问题</td><td>高负载下冲突率高，大量事务 abort 重试，反而降低吞吐（thrashing）</td></tr>
<tr><td>实现复杂度</td><td>高——需要分布式共识、事务冲突检测、重试机制</td></tr>
</table>

<div class="card card-w">
<p><strong>Omega 的冲突问题（Conflict Thrashing）</strong>：</p>
<p>当集群负载很高、空闲资源很少时，多个调度器都盯着同一块空闲资源，大家都做决策、提交冲突、abort、重试——调度器都在忙着重试，有效吞吐反而下降。这和数据库高并发写时的锁冲突类似。Omega 的解法是：</p>
<ul>
<li>不同调度器负责不同类型的任务，减少资源竞争</li>
<li>高优先级任务的事务优先提交，减少低优任务的无效重试</li>
<li>冲突退避：abort 后等一会再重试，不要立即重试</li>
</ul>
</div>
</div>

<div class="card card-s">
<h3>架构四：混合/分布式/优化调度（Hybrid/Distributed）</h3>
<p><strong>代表系统</strong>：Firmament、K8s 多调度器、Volcano/Kueue（队列层）</p>

<h4>Firmament：基于最小费用最大流的全局优化</h4>
<p>Firmament 把调度问题形式化为<strong>min-cost max-flow（最小费用最大流）</strong>问题：</p>
<ul>
<li>构造一个流网络：源点 → 任务节点 → 机器节点 → 汇点</li>
<li>边的容量：任务到机器的边容量为 1（一个任务放一台机器），机器到汇点的容量是机器的资源量</li>
<li>边的费用：任务放某台机器的代价（不满足亲和性代价高、满足局部性代价低、抢占代价等）</li>
<li>求 min-cost max-flow，就能得到全局最优的放置方案</li>
</ul>
<p>Firmament 可以做到<strong>接近全局最优</strong>的决策质量，同时流算法的增量更新让它有不错的扩展性。Google 的一部分 Borg 调度逻辑已经使用了类似的优化方法。</p>
<p><strong>局限</strong>：流算法有计算开销，万级任务规模需要近似和增量优化；Gang 调度等复杂约束需要特殊建模。</p>

<h4>K8s 多调度器（Multiple Schedulers）</h4>
<p>K8s 从 v1.x 就支持运行多个调度器：</p>
<ul>
<li>Pod 通过 <code>spec.schedulerName</code> 指定用哪个调度器</li>
<li>不同调度器可以有完全不同的 Filter/Score 插件和策略</li>
<li>例如：默认调度器处理普通 Pod，GPU 调度器处理 GPU 任务，批处理调度器处理 AI 训练任务</li>
</ul>
<p>这其实是一种"共享状态"的轻量实现——所有调度器都 watch 同一个 API Server，看到相同的集群状态，调度决策通过 Bind 时的资源检查来解决冲突（相当于乐观并发）。但 K8s 本身不做事务冲突的自动重试，需要调度器自己处理。</p>
</div>

<div class="card card-d">
<h3>Volcano/Kueue 是什么？不是全功能调度器</h3>
<p>面试中经常被问：Volcano、Kueue、YuniKorn 这些是调度器吗？答案是：<strong>它们主要是队列/批处理层，运行在 K8s 默认调度器之上</strong>，不是替代 kube-scheduler。</p>
<table>
<tr><th>组件</th><th>定位</th><th>核心能力</th></tr>
<tr><td>K8s kube-scheduler</td><td>核心调度器</td><td>Pod→Node 放置、Filter/Score/Bind、资源分配</td></tr>
<tr><td>Volcano</td><td>批调度增强</td><td>Gang Scheduling、Queue、公平性、DRF、Job/TaskGroup 管理</td></tr>
<tr><td>Kueue</td><td>队列层（Job 排队）</td><td>多租户队列、配额/公平、Preemption、Job 准入控制，不做 Pod 放置</td></tr>
<tr><td>YuniKorn</td><td>资源调度器</td><td>可以替代 kube-scheduler，也可以作为 K8s 调度器插件，侧重分层队列和公平</td></tr>
</table>
<p><strong>关键区分</strong>：</p>
<ul>
<li>Kueue 不做 Pod 放到哪个 Node 的决策——它只决定"哪个 Job 先放行、放行多少资源"，放行后的 Pod 还是交给 kube-scheduler 去放节点</li>
<li>Volcano 有自己的调度器（volcano-scheduler）可以替代 kube-scheduler，但大多数场景是配合使用</li>
</ul>
</div>

<div class="card card-m">
<h3>四种架构对比表</h3>
<table>
<tr><th>架构类型</th><th>并发决策</th><th>决策全局最优性</th><th>可扩展性</th><th>实现复杂度</th><th>多框架支持</th><th>典型系统</th></tr>
<tr><td>集中式/单体</td><td>低（串行）</td><td>高（全局视图）</td><td>中（单进程瓶颈，但可通过缓存/分 Cell 扩展）</td><td>低</td><td>差（单一调度逻辑）</td><td>Borg, K8s 默认调度器</td></tr>
<tr><td>两级/双层</td><td>高（框架并行）</td><td>低（框架只看 Offer）</td><td>高（Master 轻量）</td><td>中</td><td>好（框架自定义逻辑）</td><td>Mesos, YARN</td></tr>
<tr><td>共享状态</td><td>高（多调度器并行）</td><td>高（全视图复制）</td><td>中高（高负载冲突 thrashing）</td><td>高（需要共识/事务）</td><td>好（多调度器）</td><td>Omega, Apollo</td></tr>
<tr><td>混合/分布式</td><td>中高（取决于具体设计）</td><td>非常高（优化算法）</td><td>中（流算法开销）</td><td>高</td><td>中</td><td>Firmament, K8s 多调度器</td></tr>
</table>
</div>

<div class="card card-d">
<h3>演进趋势与 AI Infra 的选择</h3>

<h4>架构演进脉络</h4>
<pre><code>集中式 → 两级调度 → 共享状态 → 混合/多调度器
(Borg)    (Mesos)     (Omega)    (Firmament/K8s)</code></pre>
<p>演进方向不是"后者替代前者"，而是"针对不同场景选择合适架构"：</p>
<ul>
<li>小规模集群/统一工作负载：集中式最简单最可靠</li>
<li>多种异构框架（Hadoop/Spark/MPI/Web Service）：两级调度或共享状态</li>
<li>需要极致调度质量：全局优化（Firmament 风格）</li>
</ul>

<h4>AI 训练集群为什么适合集中式（Borg 风格）？</h4>
<p>大规模 AI 训练（万卡级别）有几个特殊需求：</p>
<ol>
<li><strong>Gang Scheduling</strong>：分布式训练需要同时拿到所有 GPU（all-or-nothing），要么一个 Job 的 N 张卡全到位，要么一个都不启动——否则拿到部分卡的任务只能空等，浪费资源。两级调度的 Offer 机制很难凑齐 Gang。</li>
<li><strong>拓扑感知</strong>：多机训练需要考虑 NVLink/NVSwitch/机架/网络拓扑（同机 > 同机架 > 同 Spine），这需要全局视图才能做最优放置——局部视图下做不了拓扑优化。</li>
<li><strong>碎片化问题</strong>：GPU 是稀缺资源，碎片化（每个节点剩 1-2 张卡，但需要 8 卡的任务放不进去）代价极高，全局 Bin Packing 比局部决策减少碎片。</li>
<li><strong>故障域感知</strong>：大训练 Job 的 Worker 要分散到不同故障域，避免一个机架断电整个 Job 挂掉，这也需要全局视图。</li>
<li><strong>任务类型相对统一</strong>：AI 集群主要是训练 Job（和少量推理/开发），不像 Borg/Mesos 时代有 MapReduce/Spark/Web Service/Cron 等五花八门的框架，不需要强"多框架自定义调度"能力。</li>
</ol>
<p><strong>结论</strong>：万卡级 AI 训练集群，通常采用 Borg 风格的<strong>集中式调度 + 本地缓存 + 乐观并发 + 分 Cell/分区</strong>架构：</p>
<ul>
<li>调度器有全局视图，做 Gang/拓扑/碎片优化</li>
<li>通过缓存、批量调度、近似算法解决单进程性能瓶颈</li>
<li>规模太大时分多个 Cell/分区，每个分区独立调度</li>
<li>上层用 Kueue/Volcano 做队列管理、多租户公平、配额，底层还是集中式放置</li>
</ul>
</div>

<div class="card card-m">
<h3>调度器架构面试问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Borg 和 K8s Scheduler 有什么区别？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心定位</div><p>Borg 是 Google 内部使用了十多年的生产级集群管理系统，经过了万台规模、百万任务的验证；K8s 是 Borg 的开源"精神续作"，设计思想来自 Borg，但更通用、更可扩展。</p></div>
<div class="qa-section"><div class="qa-section-title">具体差异</div><table>
<tr><th>维度</th><th>Borg</th><th>K8s Default Scheduler</th></tr>
<tr><td>规模</td><td>单 Cell 万台机器，数十万个任务</td><td>官方支持 5k 节点规模，更大规模需要调优</td></tr>
<tr><td>资源模型</td><td>细粒度，有资源回收（reclamation）——可以用低优任务的预留资源</td><td>requests/limits 模型，没有原生 reclamation，需要靠 PriorityClass/Preemption</td></tr>
<tr><td>调度算法</td><td>多年优化的成熟逻辑，有全局优化、批量调度、碎片整理等</td><td>可扩展的 Framework 插件，默认插件相对简单，高级能力靠 Volcano 等扩展</td></tr>
<tr><td>Gang 调度</td><td>原生支持</td><td>不原生支持，需要 Volcano/Kueue</td></tr>
<tr><td>高可用性</td><td>调度器有热备，故障快速切换</td><td>多副本选主，但单副本调度</td></tr>
<tr><td>扩展性</td><td>内部系统，扩展靠 Google 工程师</td><td>高度可扩展——Scheduler Framework、Webhook、自定义调度器</td></tr>
</table></div>
<div class="qa-section"><div class="qa-section-title">面试要点</div><p>不要说"K8s 是 Borg 的开源版"，要说"K8s 借鉴了 Borg 的设计思想（Pod/Service/Node、优先级抢占、两阶段调度），但为了通用性和扩展性，在默认实现上简化了很多大规模场景下的高级能力（如 Gang、资源回收、全局优化），这些能力需要通过 Volcano/Kueue 等扩展组件补充。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 两级调度（Mesos/YARN）的优缺点？适合什么场景？不适合什么场景？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">优点</div><p>(1) 多框架支持好——不同计算框架（Hadoop MapReduce、Spark、MPI、Web 服务）可以有自己的调度逻辑，不需要改中央调度器。(2) 可扩展性好——中央 Master 只做资源 Offer 和公平分配，任务级调度由框架自己做，Master 压力小。(3) 框架隔离——一个框架调度器出问题不影响其他框架。</p></div>
<div class="qa-section"><div class="qa-section-title">缺点</div><p>(1) 框架看不到全局资源——只能看到 Master 发给自己的 Offer，做不了全局最优决策，特别是拓扑感知和 Gang 调度。(2) 悲观 Offer 锁资源——Offer 发给框架后、被接受/拒绝前，资源被临时锁定，利用率低。(3) 优先级反转——低优框架拿着 Offer 不释放，高优框架等不到资源。(4) 响应延迟——框架要等 Offer，Offer 是周期性发的，任务启动延迟高。</p></div>
<div class="qa-section"><div class="qa-section-title">适合场景</div><p>多种异构计算框架并存的大数据集群——例如同时跑 Hadoop、Spark、Storm，每个框架有自己的调度需求，统一调度器难以适配所有框架。</p></div>
<div class="qa-section"><div class="qa-section-title">不适合场景</div><p>AI 训练集群——因为需要 Gang Scheduling（同时拿 N 张卡）、拓扑感知（NVLink/机架）、全局碎片优化，这些都需要全局视图，Mesos 的 Offer 机制很难做好。</p></div>
<div class="qa-summary">面试要点：说清两级调度的核心是"Master 管资源分配，框架管任务调度"，优点是多框架和扩展性，缺点是局部视图和 Offer 锁资源。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Omega 的 shared-state 怎么解决冲突？和乐观锁/悲观锁是什么关系？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心机制：乐观并发控制（Optimistic Concurrency Control, OCC）</div><p>(1) 每个调度器都有一份全集群状态副本，基于这份状态"乐观地"做决策，不加锁。(2) 决策结果以事务形式提交给共享状态存储。(3) 提交时检查：事务涉及的资源是否被其他事务修改过？如果没有，提交成功；如果冲突（资源已被占用），事务 abort，调度器基于最新状态重新做决策。</p></div>
<div class="qa-section"><div class="qa-section-title">和悲观锁的对比</div><table>
<tr><th></th><th>悲观并发（Mesos Offer）</th><th>乐观并发（Omega）</th></tr>
<tr><td>思想</td><td>先锁资源，再做决策，别人用不了</td><td>先做决策，提交时检查冲突</td></tr>
<tr><td>冲突少（低负载）时</td><td>性能差——锁等待开销大</td><td>性能好——无锁并行</td></tr>
<tr><td>冲突多（高负载）时</td><td>性能还行——锁保证不冲突</td><td>性能差——大量 abort/retry（thrashing）</td></tr>
<tr><td>决策质量</td><td>低——可能锁了不用</td><td>高——基于全视图决策</td></tr>
</table></div>
<div class="qa-section"><div class="qa-section-title">类比</div><p>悲观锁像"会议室预约"——先预约锁时间，别人在这个时间不能用；乐观锁像"谁先到谁用"——大家都去会议室，发现已经有人了就等会再来。预约保证你能用但可能浪费（预约了没人来），无锁效率高但人多的时候大家都在抢。</p></div>
<div class="qa-summary">面试要点：Omega 用乐观并发，核心是"全状态复制 + 并行决策 + 事务提交 + 冲突重试"，对比 Mesos 悲观 Offer 的优劣势。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 AI 训练集群适合 centralized scheduler？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">AI 训练的特殊需求</div><p>大规模分布式训练（特别是万卡级 LLM 训练）有几个核心需求，这些需求天然适合集中式调度：</p>
<ol>
<li><strong>Gang Scheduling（all-or-nothing）</strong>：分布式训练要求所有 Worker 同时启动、同时通信。一个 1024 卡的 Job，要么 1024 张卡同时到位，要么一张都不要启动——否则拿到部分卡的 Worker 只能空等其他 Worker，浪费资源还容易超时。全局视图才能检查"是否有 1024 张卡能凑成符合拓扑的 Gang"，两级调度的局部 Offer 做不到。</li>
<li><strong>拓扑感知放置</strong>：多机多卡训练的通信性能高度依赖拓扑——同机 NVLink > 同机架 RDMA > 跨机架网络。最优放置需要全局计算拓扑匹配度，局部决策（如 Mesos 框架只看 Offer）做不了全局拓扑优化。</li>
<li><strong>碎片化控制</strong>：GPU 极其昂贵，碎片化（每个节点剩 1-2 张卡，凑不出 8 卡任务）是最大浪费之一。集中式全局 Bin Packing 可以最大程度减少碎片，局部决策容易导致"每个节点都剩一点，但谁都用不了"。</li>
<li><strong>故障域分散</strong>：大训练 Job 的 Worker 要分散到不同机架/电源域/交换机，避免单点故障导致整个 Job 失败。这也需要全局视图。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">那可扩展性怎么办？</div><p>Borg 已经证明：集中式调度配合(1)本地状态缓存减少 API Server 压力、(2)乐观并发 Bind 而不是全局锁、(3)批量调度和近似算法减少计算、(4)分 Cell（每个 Cell 几千到几万台），完全可以支撑超大规模集群。AI 集群任务类型相对统一（主要是训练 Job，不像 Borg 混跑 Web/MapReduce/ cron），单调度器压力更小。</p></div>
<div class="qa-section"><div class="qa-section-title">实际架构</div><p>实际的万卡 AI 集群通常是：上层用 Kueue/Volcano 做队列管理、多租户公平、配额（Job 排队和准入），底层用集中式调度器（优化过的 kube-scheduler 或自研）做 Pod→Node 的放置和 Gang/拓扑优化——本质还是"Borg 风格集中式 + 上层队列层"。</p></div>
<div class="qa-summary">面试要点：从 Gang/拓扑/碎片/故障域四个需求出发，说明为什么全局视图必要；再回答可扩展性问题，提缓存/乐观/分 Cell 等优化手段；最后说实际架构是"上层队列 + 下层集中式放置"。</div>
</div>
</div>
</div>

## 关联模块

- `Kubernetes 调度器扩展`：Scheduler Framework、插件机制、队列设计，K8s 调度器实现细节
- `批处理与 Gang 调度`：Gang Scheduling 机制、Backfill 算法、资源回收
- `拓扑感知调度`：NVLink/NVSwitch/机架拓扑、网络拓扑感知
- `多租户 GPU 调度`：DRF 公平性、多队列、配额管理
