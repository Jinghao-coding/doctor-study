<div class="card card-m">
<h3>调度面试题精讲：直接回答问题，不讲路线图</h3>
<p>AI Infra / GPU 集群调度问题按“核心概念 → 标准回答 → 设计落点 → 常见追问”组织。</p>
<div class="qa-summary">总口径：GPU 集群调度不是“找一台有空 GPU 的机器”，而是在 workload 语义、多资源公平、拓扑质量、GPU 碎片、抢占代价和系统可观测之间做权衡。</div>
</div>

<div class="card card-s">
<h3>先建立统一模型：调度器到底在做什么</h3>
<p>调度器的输入是任务和资源，输出是调度决策。一个完整调度器至少要回答五个问题：谁先调度、能不能运行、放到哪里、是否要抢占、运行后如何回收/重试。</p>
<table>
<tr><th>决策点</th><th>要回答的问题</th><th>常用机制</th><th>AI Infra 特殊点</th></tr>
<tr><td>排序 QueueSort</td><td>谁先被考虑</td><td>FIFO、优先级、SJF、DRF/QAD、aging</td><td>长短任务混部，不能简单 FIFO</td></tr>
<tr><td>准入 Admit</td><td>这个任务现在能不能启动</td><td>quota、gang、minAvailable、reservation</td><td>训练任务需要 all-or-nothing</td></tr>
<tr><td>放置 Placement</td><td>放到哪些节点/哪些 GPU</td><td>Filter/Score、bin packing、拓扑打分</td><td>同样 8 卡，NVLink/跨节点性能差异巨大</td></tr>
<tr><td>抢占 Preemption</td><td>高优任务来了谁让位</td><td>Priority、checkpoint-aware cost、reclaim</td><td>训练抢占会丢进度、重建通信组</td></tr>
<tr><td>运行时控制</td><td>失败、扩缩容、资源回收怎么处理</td><td>checkpoint、retry、elastic training、health check</td><td>NCCL hang、GPU Xid、节点失联都要处理</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Q1：如果有一个 GPU 集群，如何设计一个任务调度器？</h3>
<p><strong>标准回答：</strong>我会把它设计成“队列层 + 准入层 + 放置层 + 运行时控制层 + 观测层”的调度系统，而不是只做一个节点打分器。</p>
<ol>
<li><strong>任务抽象：</strong>区分训练、推理、评测、数据处理。训练任务需要 gang、checkpoint 和拓扑；推理任务关注 SLA 和弹性扩缩；评测/数据任务更像批处理。</li>
<li><strong>资源抽象：</strong>GPU 不只看数量，还要看型号、显存、CPU、内存、RDMA/NIC、NVLink、机架、存储、本地 NVMe 和故障域。</li>
<li><strong>队列层：</strong>按团队/项目建层级队列，配置 min/max quota、优先级、可借用资源和回收策略。</li>
<li><strong>准入层：</strong>检查 quota、gang minAvailable、GPU flavor、拓扑硬约束。资源不够时可以 reservation，而不是让部分 worker 先跑。</li>
<li><strong>放置层：</strong>Filter 过滤不可行节点，Score 综合 bin packing、拓扑质量、碎片影响、故障域、数据 locality。</li>
<li><strong>抢占与回收：</strong>高优任务或保障队列资源不足时，按 checkpoint 新鲜度、重启成本和释放资源价值选择牺牲者。</li>
<li><strong>运行时控制：</strong>支持重试、checkpoint 恢复、elastic training 扩缩容、节点/GPU 健康检查。</li>
<li><strong>观测层：</strong>暴露 pending 原因、等待时间、JCT、利用率、公平性、抢占损失、失败率和拓扑命中率。</li>
</ol>
<div class="qa-summary">核心回答：先做多租户队列和 gang 准入，再做拓扑感知 placement，最后用 backfill、抢占和 elastic training 提高利用率。</div>
</div>

<div class="card card-w">
<h3>Q2：多租户场景下，如何保证不同用户/团队之间的公平性？</h3>
<p><strong>核心概念：</strong>公平不是平均分 GPU，而是“有保障、有上限、可借用、可回收”。在多资源场景里，公平通常要看 dominant resource，即一个租户最紧张的资源份额。</p>
<table>
<tr><th>机制</th><th>作用</th><th>怎么回答</th></tr>
<tr><td>层级队列</td><td>把公司/部门/团队/项目组织成资源治理树</td><td>每层都有 quota 和优先级，避免全局 FIFO 被大团队占满</td></tr>
<tr><td>min quota</td><td>保障资源</td><td>团队至少能拿到承诺份额，适合关键业务</td></tr>
<tr><td>max quota</td><td>限制上限</td><td>防止某个团队无限扩张</td></tr>
<tr><td>borrowing</td><td>提升利用率</td><td>别人不用时可以借，但要记录 debt</td></tr>
<tr><td>reclaim</td><td>保证公平回收</td><td>owner 需要资源时，从 borrower 低优任务回收</td></tr>
<tr><td>DRF / QAD</td><td>度量多资源公平</td><td>按主导资源份额或 quota 满足度排序</td></tr>
<tr><td>aging</td><td>防止饥饿</td><td>等待越久动态优先级越高</td></tr>
</table>
<p><strong>标准回答：</strong>我会使用层级队列 + min/max quota + DRF/QAD 排序。空闲资源允许借用，但借用资源要可回收；当保障队列资源不足时，优先抢占借用资源上的低优任务。为避免低优任务长期饥饿，需要 aging 和最大等待时间兜底。</p>
</div>

<div class="card card-r">
<h3>Q3：如何处理高优任务抢占低优任务？抢占有什么代价？</h3>
<p><strong>标准回答：</strong>抢占不能简单“优先级高就杀低优任务”。AI 训练里抢占代价很高，需要做 checkpoint-aware preemption。</p>
<table>
<tr><th>抢占代价</th><th>具体含义</th><th>设计对策</th></tr>
<tr><td>训练进度损失</td><td>回滚到上一次 checkpoint，checkpoint 之后的 step 白跑</td><td>优先抢 checkpoint 新鲜、沉没成本低的任务</td></tr>
<tr><td>重启成本</td><td>重新排队、拉镜像、加载模型、加载数据</td><td>镜像预热、模型缓存、本地缓存</td></tr>
<tr><td>通信重建</td><td>NCCL world、rank、通信组需要重建</td><td>gang 级别重启，避免只杀一部分 worker</td></tr>
<tr><td>系统抖动</td><td>大量 Pod 删除/重建冲击 API Server 和调度器</td><td>分批抢占、抢占限速、冷却时间</td></tr>
<tr><td>用户体验</td><td>低优用户训练频繁被打断</td><td>抢占次数上限、aging、可抢占队列说明</td></tr>
</table>
<div class="formula">$$\text{victim\_score} = \text{release\_value} / (\text{checkpoint\_age} + \text{restart\_cost} + \text{disruption\_penalty})$$</div>
<p><strong>面试展开：</strong>先判断高优任务需要释放哪些资源，再找能释放目标资源且代价最低的 victim；抢占前尽量发优雅退出信号让任务保存 checkpoint，超时后再强制终止。</p>
</div>

<div class="card card-d">
<h3>Q4：如何避免 GPU 碎片？8 卡任务为什么可能跑不起来？</h3>
<p><strong>核心概念：</strong>GPU 碎片不是“总 GPU 不够”，而是“满足任务约束的连续/同拓扑资源不够”。例如集群剩 8 张 GPU，但分散在 8 台机器上，每台 1 张；一个需要单机 8 卡 NVLink 的任务仍然无法运行。</p>
<table>
<tr><th>方法</th><th>解决什么</th><th>代价</th></tr>
<tr><td>Bin Packing</td><td>小任务尽量塞满已有节点，保留完整空节点</td><td>热点和故障爆炸半径增加</td></tr>
<tr><td>Topology-aware placement</td><td>保留完整 NVLink / 机架 / RDMA 域</td><td>等待时间可能增加</td></tr>
<tr><td>Reservation</td><td>为大 gang 任务预留未来资源窗口</td><td>短期利用率下降</td></tr>
<tr><td>Backfill</td><td>大任务等资源时，用短任务填碎片</td><td>依赖运行时间预测</td></tr>
<tr><td>Defragmentation</td><td>迁移/抢占低优任务合并资源</td><td>有重启和进度损失</td></tr>
<tr><td>资源池分层</td><td>按 GPU 型号、拓扑域、队列隔离</td><td>池子太细会降低整体利用率</td></tr>
</table>
<p><strong>标准回答：</strong>我会在 Score 阶段引入碎片惩罚：小任务优先填已有节点，大任务优先拿完整拓扑；队列层用 reservation 保护大任务，用 backfill 填补等待窗口。必要时做 checkpoint-aware defragmentation。</p>
</div>

<div class="card card-s">
<h3>Q5：如何设计队列、优先级和配额系统？</h3>
<p><strong>标准回答：</strong>队列系统要同时表达组织结构、资源保障、业务优先级和弹性借用。</p>
<table>
<tr><th>设计项</th><th>建议方案</th><th>原因</th></tr>
<tr><td>队列结构</td><td>层级队列：部门 / 团队 / 项目</td><td>方便组织级资源治理和审计</td></tr>
<tr><td>配额</td><td>min quota + max quota + flavor quota</td><td>既保障基本资源，又限制无限扩张；H100/A100 要分开</td></tr>
<tr><td>优先级</td><td>业务优先级 + 队列优先级 + aging</td><td>同时支持紧急任务和长期公平</td></tr>
<tr><td>借用</td><td>空闲资源可跨队列借用</td><td>提高利用率</td></tr>
<tr><td>回收</td><td>owner 资源不足时从 borrower 回收</td><td>保证配额承诺兑现</td></tr>
<tr><td>审计</td><td>记录 quota usage、borrow debt、preemption history</td><td>让用户知道为什么排队或被抢占</td></tr>
</table>
<p><strong>追问回答：</strong>如果面试官问“为什么不用 ResourceQuota”，回答：ResourceQuota 只能限制 namespace 资源用量，不解决队列排序、DRF 公平、借用回收、gang 准入和 GPU 拓扑放置。</p>
</div>

<div class="card card-m">
<h3>Q6：如何支持 Elastic Training / 弹性训练？</h3>
<p><strong>核心概念：</strong>弹性训练允许任务在 min/max worker 范围内运行。例如 min=16、target=64、max=128；达到 min 就能启动，资源充足后扩容，资源紧张时缩容。</p>
<table>
<tr><th>组件</th><th>要做什么</th><th>难点</th></tr>
<tr><td>任务 API</td><td>声明 min/target/max、弹性策略、扩缩容冷却时间</td><td>用户要能表达效率和资源的 trade-off</td></tr>
<tr><td>调度器</td><td>min 满足即准入，空闲资源可增量分配</td><td>扩容不能破坏高优 reservation</td></tr>
<tr><td>训练框架</td><td>支持 world size / rank membership 变化</td><td>NCCL 通信组、优化器状态、数据分片一致性</td></tr>
<tr><td>Checkpoint</td><td>扩缩容前后保持状态一致</td><td>I/O 压力和恢复时间</td></tr>
<tr><td>监控</td><td>观察扩缩容后吞吐是否真的提升</td><td>不是卡越多越快，通信可能成为瓶颈</td></tr>
</table>
<p><strong>标准回答：</strong>弹性训练用更复杂的训练框架能力换更短等待时间和更高集群利用率。它不是调度器单独能完成的，必须训练框架、checkpoint、数据加载和调度器一起支持。</p>
</div>

<div class="card card-w">
<h3>Q7：如何处理长任务和短任务混部？</h3>
<p><strong>标准回答：</strong>不能只用 FIFO，也不能只用 SJF。FIFO 会让短任务被队头长任务阻塞；SJF 会让长任务饥饿。实际系统要结合多队列、aging、backfill、quota 和抢占成本。</p>
<table>
<tr><th>策略</th><th>解决的问题</th><th>注意点</th></tr>
<tr><td>多队列</td><td>交互式短任务、长期训练、best-effort 分开治理</td><td>队列之间要有公平共享</td></tr>
<tr><td>SJF / 预测排序</td><td>降低平均等待时间</td><td>长任务要 aging 兜底</td></tr>
<tr><td>Backfill</td><td>短任务利用大任务等待窗口</td><td>不能破坏大任务 reservation</td></tr>
<tr><td>Quota</td><td>保证长任务也有资源份额</td><td>过硬会降低利用率</td></tr>
<tr><td>Preemption</td><td>高优短任务快速启动</td><td>要考虑 checkpoint 和重启成本</td></tr>
</table>
<div class="qa-summary">短任务要低等待，长任务要不饥饿；用 backfill 提高利用率，用 aging/quota 保证长期公平。</div>
</div>

<div class="card card-d">
<h3>Q8：如何判断任务应该立即运行，还是等待更好的资源组合？</h3>
<p><strong>核心概念：</strong>立即运行降低等待时间，但可能拿到差拓扑、导致训练变慢或制造碎片；等待更好资源提高运行效率，但增加排队时间。</p>
<table>
<tr><th>维度</th><th>倾向立即运行</th><th>倾向等待</th></tr>
<tr><td>任务时长</td><td>短任务，等待成本占比高</td><td>长训练，拓扑差会长期放大损失</td></tr>
<tr><td>通信强度</td><td>单卡、小 DP、低通信</td><td>TP/MoE/NCCL-heavy</td></tr>
<tr><td>拓扑影响</td><td>差拓扑只损失少量吞吐</td><td>差拓扑可能导致 step time 翻倍</td></tr>
<tr><td>碎片影响</td><td>不会打散完整节点</td><td>会破坏未来大任务资源窗口</td></tr>
<tr><td>优先级</td><td>高优/交互式任务</td><td>低优/best-effort 任务</td></tr>
<tr><td>预测置信度</td><td>不知道何时有更好资源</td><td>能预测某批资源很快释放</td></tr>
</table>
<div class="formula">$$\text{schedule now if } \text{waiting\_cost} > \text{performance\_loss} + \text{fragmentation\_cost}$$</div>
<p><strong>标准回答：</strong>我会给每个候选 placement 计算拓扑质量和碎片代价；如果当前 placement 的性能损失和碎片代价小于继续等待的成本，就立即运行；否则做 reservation，并允许短任务 backfill。</p>
</div>

<div class="card card-s">
<h3>Q9：K8s 默认调度器为什么不够？</h3>
<p><strong>标准回答：</strong>K8s 默认调度器适合通用 Pod 放置，但 AI 训练需要队列公平、gang 语义、拓扑感知、GPU 设备属性和训练运行时控制。</p>
<table>
<tr><th>不足</th><th>具体问题</th><th>需要的扩展</th></tr>
<tr><td>缺少 gang 语义</td><td>Pod 独立调度，部分 worker 先启动会造成 GPU 空转</td><td>PodGroup、Permit、Volcano/Kueue</td></tr>
<tr><td>队列公平不足</td><td>PriorityClass 不等于多租户公平</td><td>DRF、Elastic Quota、QAD、层级队列</td></tr>
<tr><td>GPU 拓扑弱</td><td>只看 GPU 数量，不理解 NVLink/NIC/NUMA</td><td>DRA、拓扑打分、自定义 plugin</td></tr>
<tr><td>抢占代价粗糙</td><td>默认抢占不了解 checkpoint 和训练进度</td><td>checkpoint-aware preemption</td></tr>
<tr><td>弹性训练弱</td><td>固定副本数，不表达 min/target/max</td><td>TrainingJob CRD、elastic controller</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官让你概括 GPU 调度难点，怎么说？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">推荐回答</div><p>GPU 调度难在它同时是多资源、多租户、强拓扑、强同步、抢占代价高的问题。CPU 调度主要分配时间片，而 GPU 训练调度要分配一组满足拓扑和 gang 语义的设备，并且要在公平性、利用率、等待时间和训练效率之间权衡。</p></div>
<div class="qa-section"><div class="qa-section-title">展开顺序</div><p>先说 gang：多 worker 必须一起启动；再说拓扑：不同 placement 训练性能差异大；再说碎片：总卡数够不代表可调度；再说公平：多团队共享要有 quota；最后说抢占：训练任务被打断有 checkpoint 和重启代价。</p></div>
<div class="qa-summary">不要只说“资源昂贵”，要说清楚昂贵资源为什么难调度。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果让你现场画架构图，应该画哪些模块？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">模块清单</div><p>画用户提交入口、TrainingJob/InferenceJob API、队列管理器、Quota/Fairness 控制器、Scheduler、Topology/Resource Cache、Preemption/Reclaim 控制器、Job Controller、Checkpoint/Retry 控制器、Metrics/Events/Tracing。</p></div>
<div class="qa-section"><div class="qa-section-title">数据流</div><p>任务提交后进入队列；队列管理器计算公平排序；scheduler 做 gang 准入和 placement；资源不足时 reservation/backfill；高优任务触发 reclaim/preemption；运行中由 controller 监控状态并处理失败恢复。</p></div>
<div class="qa-summary">架构图要体现“队列公平 + gang 准入 + 拓扑放置 + 运行时恢复”，不要只画一个 scheduler 方框。</div>
</div>
</div>
