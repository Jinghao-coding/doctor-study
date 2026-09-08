## 字节 Lumen：跨团队训练资源调度

<div class="card card-m">
<h3>01 · 问题与职责</h3>
<div class="qa-summary">把闲置 GPU 借给排队团队</div>
<ul>
<li><strong>问题：</strong>团队固定分卡，排队与闲置并存。</li>
<li><strong>我负责：</strong>Merlin 上层的跨团队资源协调。</li>
<li><strong>执行链：</strong>看配额与占用 → 决定借用、回收 → Thrift 对接 Merlin。</li>
</ul>
<div class="qa speech">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">展开口述 · 问题与职责</div>
<div class="qa-a">
<p>我在字节国际电商 Lumen 实习时，参与的是训练统一资源池的调度系统建设。当时 GPU 主要按团队<strong>固定分配</strong>，问题是不同团队的<strong>需求并不同步</strong>：一边有训练任务持续排队，另一边却还有数百张 GPU 空闲。</p>
<p>这不只是资源总量不够，也有固定分配带来的资源隔离问题。</p>
<p>我这段工作的重点，是在已有的 Merlin 训练平台之上设计<strong>跨团队调度层</strong>。上层统一看团队配额、实际占用和待运行任务，决定资源怎样借用、任务怎样安排、什么时候需要回收，再通过 <strong>Thrift</strong> 把调度结果交给 Merlin 执行。</p>
<p>我的工作围绕资源协调和任务状态管理展开。</p>
</div>
</div>
</div>

<div class="card card-m">
<h3>02 · 配额与优先级</h3>
<div class="qa-summary">额度、执行顺序、回收权是三个维度</div>
<ul>
<li><strong>配额：</strong>团队有多少资源额度。</li>
<li><strong>优先级：</strong>A/B/C 参与任务执行安排。</li>
<li><strong>Spot：</strong>闲置时借出，原团队需要时收回。</li>
</ul>
<div class="qa speech">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">展开口述 · 配额与优先级</div>
<div class="qa-a">
<p>第一个策略点是配额借用。固定配额代表团队的资源额度，但不意味着它暂时不用的资源必须一直空着。我们把空闲配额作为<strong>可回收的 Spot 资源</strong>借给其他团队，原团队需求恢复时再收回。</p>
<p>这样借用方获得了额外的运行机会，原团队也保留了恢复使用的能力。这里的关键是把<strong>正常配额使用和借用资源区分开</strong>，否则后面回收时就说不清哪些任务可以被影响。</p>
<p>第二个策略点是优先级。我们把 <strong>A/B/C</strong> 任务优先级纳入调度，但它不是唯一的决策依据。配额回答的是团队可以获得怎样的资源额度，优先级回答的是任务竞争时的安排，而 Spot 回答的是资源能不能被收回。</p>
<p>这<strong>三个维度</strong>需要一起考虑。比如一个借用任务优先级比较高，也不能仅凭这个标签推导出它永远不需要归还资源；具体还要看配额保障与借用规则。A/B/C 的具体分类和当时的排序细节我现在记不全，但这些约束不能混成一个优先级数字。</p>
</div>
</div>
</div>

<div class="card card-m">
<h3>03 · 抢占策略</h3>
<div class="qa-summary">先判断能否回收，再选择低代价组合</div>
<ul>
<li><strong>候选：</strong>允许回收的任务。</li>
<li><strong>代价：</strong>任务类型 + SM Active + 已运行时长。</li>
<li><strong>目标：</strong>释放足够 GPU，减少计算损失和不必要的中断。</li>
</ul>
<div class="qa speech">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">展开口述 · 抢占策略</div>
<div class="qa-a">
<p>第三个策略点是低代价抢占。原团队需要收回资源时，要决定中断哪些任务。</p>
<p>我们结合<strong>任务类型</strong>、<strong>SM Active</strong>，也就是计算单元活跃度，以及<strong>已经运行的时长</strong>来估计中断代价，再选择能够释放足够 GPU、代价相对较低的任务组合。目标是减少已经投入的计算损失，以及一次回收影响的任务数量。</p>
<p>这里不能只选活跃度最低的任务。<strong>低活跃</strong>可能与通信、读数据或者执行阶段有关，不一定代表任务没价值；<strong>已运行时长也不等于剩余时长</strong>，不能据此断言任务马上就完成了。</p>
<p>所以这些信号需要结合起来看。具体评分权重和组合算法我已经记不清了，但可以把策略分成两个问题：候选是否允许回收，以及回收这些候选的代价和资源效果如何。</p>
</div>
</div>
</div>

<div class="card card-m">
<h3>04 · 策略设计展开</h3>
<div class="qa-summary">能凑够卡，还要能真正放下任务</div>
<ul>
<li><strong>过滤：</strong>排除不可回收、资源不匹配的候选。</li>
<li><strong>选择：</strong>可参考代价与释放量排序，逐步构造候选集合。</li>
<li><strong>检查：</strong>同节点多卡、卡型、整任务回收等约束。</li>
</ul>
<p><small>设计展开：不是已核对的历史算法。</small></p>
<div class="qa speech">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">展开口述 · 策略设计展开</div>
<div class="qa-a">
<p>如果进一步展开实现设计，我会<strong>先过滤不能抢的任务</strong>，再评估候选组合。一个可实现的近似方案是参考中断代价与可释放资源量做排序，逐步选出候选，再检查<strong>资源放置是否可行</strong>。</p>
<p>比如目标任务需要同节点四张卡，分别从四个节点腾出一张卡未必有用；多卡任务如果需要整体停止，也不能假设可以只抽走其中一张卡。这是我根据机制<strong>重建的实现思路</strong>，不是对原代码算法的逐行还原。</p>
</div>
</div>
</div>

<div class="card card-m">
<h3>05 · 工程可靠性</h3>
<div class="qa-summary">不重复分配，也不提前释放</div>
<ul>
<li><strong>状态链：</strong>提交 → 排队 → 调度 → 运行 → 终止。</li>
<li><strong>存储与对接：</strong>MySQL 持久化；Redis 缓存；Thrift → Merlin。</li>
<li><strong>正确性：</strong>原子校验与预留；回收确认后才可再分配；超时先核查。</li>
</ul>
<p><small>状态管理与对接来自简历；原子预留和超时恢复为重建方案。</small></p>
<div class="qa speech">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">展开口述 · 工程可靠性</div>
<div class="qa-a">
<p>工程方面，我设计了覆盖提交、排队、调度、运行和终止的<strong>任务状态机</strong>。<strong>MySQL</strong> 持久化任务和配额状态，<strong>Redis</strong> 缓存调度需要的高频数据，<strong>Thrift</strong> 对接 Merlin 的执行层。</p>
<p>任务状态变化时更新记录，同时持续核对团队配额、调度记录中的分配和实际占用，检测状态不一致或执行异常。</p>
<p>这部分有两个非常重要的正确性问题。一个是<strong>并发预留</strong>：如果两个调度请求同时看到还有四张卡，不能各自都分配四张。</p>
<p>另一个是<strong>异步回收</strong>：发出终止请求不等于 GPU 已经空闲，必须确认执行层释放后，才能把资源交给新任务。</p>
<p>如果让我现在实现，我会把<strong>配额检查和预留</strong>放在同一个并发控制范围里，先持久化预留与待执行操作，再调用 Merlin。回收请求发出后仍保留占用，收到明确释放结果后再更新账本。</p>
<p><strong>RPC 超时</strong>不能直接当失败，更不能立即把资源重新分配出去，因为对方可能已经执行，只是响应没有回来；需要查执行状态，并用可追踪、可重试的操作配合状态核对来收敛。具体事务、字段和重试代码是设计层面的解释，不能说我还记得当时用了哪一种实现。</p>
</div>
</div>
</div>

<div class="card card-m">
<h3>06 · 成果与取舍</h3>
<div class="qa-summary">共享效率、团队保障和中断成本一起考虑</div>
<ul>
<li><strong>完成工作：</strong>资源借用、低代价回收、状态管理、执行对接。</li>
<li><strong>关键取舍：</strong>更多任务能用上资源，同时保留原团队的回收能力。</li>
<li><strong>结果口径：</strong>只讲可核实结果，不补利用率或成本收益数字。</li>
</ul>
<div class="qa speech">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">展开口述 · 成果与取舍</div>
<div class="qa-a">
<p>这段实习让我积累的是把资源共享策略接到实际任务执行上的经验。策略上要同时考虑<strong>资源利用、团队保障和中断成本</strong>；工程上要保证调度记录与实际占用能够对应起来。</p>
<p>结果方面，现有材料能支持的是借用、回收、状态管理及平台对接这些工作，<strong>量化收益</strong>我没有足够依据，所以不会报一个利用率提升或节省成本的数字。</p>
</div>
</div>
</div>

## 项目职责追问

### 已经有 Merlin，为什么还需要这一层？

**我做的是跨团队资源协调。**

- **上层**：统一资源视图、配额借用、任务优先级和回收决策。
- **Merlin**：承接调度结果，执行训练任务。
- **衔接**：通过 Thrift 下发操作，并同步、核对任务状态。

### 个人贡献和收益怎么讲？

我参与训练资源池建设，重点是**跨团队调度、借用回收、任务状态管理和平台对接**。收益是让原来隔离的闲置资源可以跨团队使用，并有明确的回收与状态跟踪机制。

**事实口径**：来源为最新中文简历与经历库，未核对内部代码。个人独立完成的模块和团队成果需分别说明；A/B/C 定义、评分权重、checkpoint、恢复策略和量化收益未确认。重建方案应以“如果现在实现”表述。
