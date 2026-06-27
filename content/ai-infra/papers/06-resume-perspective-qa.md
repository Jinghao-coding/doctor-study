## 一句话结论

面试官看不到论文全文，只能看到简历上的 3-5 行描述。本节从面试官视角出发，针对简历中每篇论文的每一条 bullet point，预测最可能被追问的问题并给出精炼回答要点。背熟这一页，简历提问环节就不会被问倒。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 论文工作 |
| 章节类型 | 面试收束类 |
| 解决问题 | 从简历描述出发，覆盖面试官最可能追问的问题，避免"简历上写了但答不上来"的窘境。 |
| 面试抓手 | 每条 bullet point 对应 2-3 个追问题，答案控制在 30 秒-2 分钟。 |

<div class="card card-w">
<h3>简历论文提问的一般规律</h3>
<p>面试官看简历上的论文/项目描述时，通常按以下路径追问：</p>
<ol>
<li><strong>"这个东西解决什么问题？"</strong>——先确认你理解问题本身，不是只记了术语。</li>
<li><strong>"为什么现有方法不行？"</strong>——考察你是否理解 gap 和 motivation。</li>
<li><strong>"你的核心想法是什么？"</strong>——一句话说清楚 insight。</li>
<li><strong>"具体怎么实现的？"</strong>——深入技术细节，考察你是否真做了。</li>
<li><strong>"XX 技术为什么选这个不选那个？"</strong>——设计决策题，考察 trade-off 思维。</li>
<li><strong>"效果怎么样？怎么评估的？"</strong>——数字背后的实验设计和结论可信度。</li>
<li><strong>"有什么局限性？如果重做会怎么改进？"</strong>——考察反思能力。</li>
</ol>
</div>

<div class="card card-m">
<h3>Maestro（ICDCS 2026）简历追问</h3>
<p class="text-muted">简历原文："面向 LLM 多智能体系统的工作负载感知调度系统 Maestro。针对 LLM 多智能体（LLM-MAS）工作流中解码成本不确定、长尾多模型显存竞争与过度预留等系统挑战，设计在严格 GPU 预算下的工作负载感知调度系统。预测层：利用 Agent 角色与工具调用语义构建两阶段输出长度与显存预测器；调度层：工作流感知优先级排序与阶段边界抢占，SLO 达成率较 EDF 提升 23.6pp；节点层：分级权重缓存与弹性显存供给，KV 预留显存降低 67.2%。"</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是"LLM 多智能体工作流"？给一个具体例子。</div>
<div class="qa-a"><p>比如一个旅行助手 Agent：用户说"帮我规划去东京的行程"，系统会依次调用：需求分析 Agent（解析意图）→ 机票搜索 Agent（调工具查航班）→ 酒店推荐 Agent（查酒店）→ 行程整合 Agent（汇总输出）。每个 Agent 背后是一个 LLM 推理调用（称为 stage），一个用户请求可能触发十几次甚至几十次 LLM 调用。这些 Agent 之间有 DAG 依赖关系，不同 Agent 可能用不同模型。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "解码成本不确定"为什么是个问题？固定预留不行吗？</div>
<div class="qa-a"><p>LLM 推理的输出长度变化极大：工具调用输出几十 token（JSON 格式），用户交互输出几百上千 token。输出长度直接决定 KV Cache 大小和 decode 时长。固定按最大长度预留会导致严重的显存浪费（利用率低），按平均长度预留则会 OOM。关键挑战是<strong>在请求开始前就要预测输出长度</strong>来分配资源，但这个预测不准就会出问题。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "两阶段预测器"具体是哪两个阶段？为什么要分两阶段？</div>
<div class="qa-a"><p>第一阶段是<strong>工具调用分类器</strong>（LightGBM），判断当前 stage 是否会触发工具调用（AUC 0.96）。第二阶段是<strong>输出长度回归器</strong>，在分类结果的基础上预测具体 token 数（MAE 165 tokens，R² 0.78）。分两阶段是因为输出长度呈<strong>双峰分布</strong>——工具调用短（几十 token），用户交互长（几百上千 token），单一回归器在双峰上表现差。分类器先识别模式，回归器在各自模式下预测更精准。消融实验去掉分类器后 MAE 从 134 升到 142。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "分级权重缓存"是什么？和普通的 LRU 有什么区别？</div>
<div class="qa-a"><p>多 Agent 场景下一块 GPU 需要同时驻留多个模型权重。设计了五层状态：Running（GPU 上可立即执行）→ Sleeping（权重在 CPU，但 GPU 保留 CUDA Graph/JIT 缓存约 0.5GB，恢复省 5-8 秒）→ CPU-resident → Disk-resident → Remote。Sleeping 状态是关键创新——保留 GPU 侧的 kernel 缓存避免重建开销。层级化 LRU 逐级淘汰，最热模型留 GPU，最冷退到远端。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "弹性显存供给"怎么做的？CUDA VMM 超配 3 倍不怕 OOM 吗？</div>
<div class="qa-a"><p>用 CUDA Virtual Memory Management 实现地址和物理页分离。在 40GB A100 上分配 122GB 虚拟地址池（3 倍超配），物理页按需映射。三层防护防 OOM：(1) 虚拟地址不等于物理内存，多 Agent 的 KV 使用不会同时达峰（统计复用）；(2) 每个 stage 进入前做准入控制，检查剩余物理页是否满足预测需求；(3) cuMemMap 失败时拒绝该 stage 而非崩溃。偏向高估（安全裕度 ρ），低估导致 OOM 的代价远大于高估浪费。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "阶段边界抢占"是什么意思？为什么不做 token 级抢占？</div>
<div class="qa-a"><p>Stage 边界抢占是指只在两个 LLM 推理调用之间切换（一个 stage 完成后、下一个 stage 开始前），不打断正在 decode 的请求。Token 级抢占需要和推理引擎深度集成、做 KV Cache 迁移，工程复杂度极高。Stage 边界抢占只需更新元数据，实测效果已足够——交互排队延迟从 11 秒降到 2 毫秒。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: SLO 达成率提升 23.6pp 的 baseline 是什么？怎么算 SLO 达成？</div>
<div class="qa-a"><p>Baseline 是 EDF（Earliest Deadline First），实时系统经典调度策略。SLO 定义为"交互式 stage 的 TTFT（首 token 时间）< 阈值"。在高负载下 EDF 因为没有预测信息，无法区分长短 stage，导致长 stage 阻塞短交互 stage（队头阻塞）。Maestro 用预测的剩余时间做 SRTF，加上工作流感知的优先级（交互式 > 批处理），SLO 达成率从约 60% 提升到 83.6%。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 46,769 条真实 trace 从哪来的？怎么保证实验可信？</div>
<div class="qa-a"><p>Trace 来自内部部署的多 Agent 应用平台，记录了每个 agent stage 的输入/输出 token 数、模型类型、时间戳。实验分为两部分：16 台 V100 做原型实测（端到端延迟、SLO 达成率），46,769 条 trace 做大规模仿真（64 卡级别）验证调度策略的扩展性。仿真器基于真实 trace 回放，关键参数（KV 内存增长、推理延迟）从原型实测校准。</p></div>
</div>
</div>

<div class="card card-d">
<h3>DeepShare（IEEE Cluster 2026）简历追问</h3>
<p class="text-muted">简历原文："以连续的「配额保障度（QAD）」为统一运行时控制信号、协调弹性配额借用、预测调度和干扰感知共置四类决策的 Kubernetes 原生调度框架。QAD = 分配量/min(配额, 保障需求)，经 EMA 平滑。空闲配额以 best-effort 借出（DRA），按 QAD+运行时预测做字典序排序，代价感知抢占。干扰感知共置用 RF 预测吞吐损失，MPS 共置无需改代码。23,859 条 Venus trace 仿真 GPU 利用率 70.6%（vs Lucid +29.5%），排队延迟降 46%；16 节点 64 卡 K8S 实测 JCT 降 34%，QoS 达成 93%。"</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是"配额保障度 QAD"？为什么不直接用"用了多少 GPU / 配额"？</div>
<div class="qa-a"><p>QAD = 已分配的 Guaranteed GPU / min(配额, 当前 Guaranteed 需求)。分母用 min(quota, demand) 很关键：如果租户 quota 32 但只需要 8 张，保障 8 张就是满足（QAD=1），不需要给满 32 张；如果租户提交 100 张需求但 quota 只有 32，保障 32 张就够（QAD=1），不会因为超额提交就认为系统欠它的。而"使用率"（usage/quota）不区分 Guaranteed 和 Best-effort，也无法区分"需求少"和"被欠服务"。EMA 平滑（λ=0.3）避免瞬时波动频繁触发抢占。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "四类决策"是哪四类？QAD 怎么统一协调它们？</div>
<div class="qa-a"><p>四类决策：(1) 弹性配额借用/回收（DRA）——QAD < 1 时回收 Best-effort 资源恢复保障；(2) 调度排序——Guaranteed 优先，QAD 低的租户优先，QAD 接近时短作业优先；(3) 抢占 victim 选择——抢占效率 Ej = (释放资源 × 剩余时间) / (1 + α × 抢占代价)，选代价最小的 Best-effort 作业；(4) GPU 共置准入——QAD 高时允许更激进的 colocation（利用率优先），QAD 低时收紧（保障优先）。QAD 作为统一信号，让四个模块的决策方向一致——保障不足时偏向 QoS，保障充分时偏向利用率。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "MPS 共置"具体怎么实现？K8s 不是以整卡为单位调度吗？</div>
<div class="qa-a"><p>K8s 的 nvidia.com/gpu 是 Extended Resource，分配后不可修改。GPU 共享通过<strong>节点侧 MPS DaemonSet</strong>实现——每块 GPU 运行 MPS control daemon，允多个 CUDA context 共享 GPU，通过 per-client SM 限制（CUDA_MPS_ACTIVE_THREAD_PERCENTAGE）做算力隔离。Scheduler Plugin 在 Filter 阶段检查节点是否有足够空闲 SM 和显存来接纳新 Pod（基于干扰预测），允许后 Pod 调度到该节点，Node Agent 配置 MPS 限制。不需要扩展 K8s 资源模型，也不需要改用户代码。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 干扰模型用什么特征？为什么选 Random Forest 不用深度学习？</div>
<div class="qa-a"><p>特征来自 DCGM 硬件计数器：SM activity、memory bandwidth utilization、L2 cache hit rate、PCIe throughput 等——这些是<strong>框架无关</strong>的，不管你跑 PyTorch 还是 TensorFlow 都能采集。选 RF 三个原因：(1) 推理延迟 < 1ms，满足实时调度（DL 模型要 50-200ms）；(2) R² = 0.902，精度足够；(3) 硬件计数器特征跨模型泛化，不需要每种架构重训。运行时持续监控实际 slowdown，超过动态阈值时驱逐低优任务。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Venus trace 是什么？为什么不直接在大集群上跑？</div>
<div class="qa-a"><p>Venus 是公司内部集群的作业 trace，包含 23,859 个深度学习作业的提交时间、GPU 需求、运行时长等信息。Trace-driven simulation 可以在可控环境下对比多种策略（对比 Lucid、Gandiva 等 baseline），控制变量。同时我们在 16 节点 64 卡的 K8s 原型上做了实测验证，证明仿真结论在真实环境中成立。大规模集群实测成本高且影响生产，仿真是学术研究的标准做法。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 JCT 只降 34% 而 GPU 利用率提升到 70.6%？</div>
<div class="qa-a"><p>JCT = 排队时间 + 执行时间。调度优化主要影响排队时间，执行时间由计算量决定。当集群负载高时排队时间占比大，JCT 改善明显；负载低时改善小。34% 是平均 JCT 降低，排队延迟降了 46%，执行时间基本不变。GPU 利用率从 39.64% 提升到 70.6%（+29.5% vs Lucid），说明资源确实被更充分利用了——主要来自 DRA 借用空闲配额和干扰感知共置两块收益。</p></div>
</div>
</div>

<div class="card card-m">
<h3>ElastiCo（Performance Evaluation 2026）简历追问</h3>
<p class="text-muted">简历原文："训推弹性混部（ElastiCo）：面向训练与离线 LLM 推理在同一 GPU 上的安全共置，提出资源形态变换、弹性影子定价与干扰感知共置三项机制，以原生 Kubernetes 中间件形式实现、无需改动用户代码。64 卡实测与最高 512 卡仿真下，平均完成时间最高降低 2.94×、集群吞吐提升 2.02×、GPU 利用率由约 25% 提升至 46%。"</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么要把训练和推理放同一块 GPU？分别放不行吗？</div>
<div class="qa-a"><p>训练集群平均 GPU 利用率只有 25% 左右——训练任务在数据加载、梯度同步通信、checkpoint 保存时 GPU 是空闲的，这些空窗期加起来占了大部分时间。同时离线推理（如批量 embedding、离线评估）有明确 SLO 但不需要独占 GPU。把它们共置可以填补这些空窗，把利用率从 25% 提到 46%。为什么不分开跑？分开跑需要额外 GPU，而 GPU 是最贵的资源——共置用同样的硬件跑更多任务，直接降成本。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "资源形态变换"是什么意思？训练和推理的资源使用有什么互补性？</div>
<div class="qa-a"><p>"形态"指 SM 算力和显存的分配比例随负载动态变化。互补性体现在：(1) 训练在 forward/backward 阶段 SM 利用率高（80-90%），在 dataloader/communication 阶段 SM 空闲；(2) 推理在 prefill 阶段突发 SM 需求，decode 阶段 SM 利用率低但占显存（KV Cache）。通过 MPS 动态调整 SM 比例+ VMM 弹性显存，可以在训练空闲时把 SM 让给推理 prefill，训练繁忙时收回 SM。这和 MIG 静态切分（固定 50/50）的区别是：MIG 切完就不变，ElastiCo 毫秒级动态调整。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "弹性影子定价"是什么？怎么定的价？</div>
<div class="qa-a"><p>给 GPU 上的 SM 和显存定一个动态价格，反映当前稀缺程度。价格由训练任务的实时 GPU 利用率和显存占用决定——训练越忙价格越高，训练空闲价格越低。推理任务有一个"价值"（SLO 优先级 × 剩余工作量），价值大于当前价格才允许共置。本质上是一个<strong>基于市场机制的准入控制</strong>：价格自动调节供需，比固定阈值灵活——高优推理在资源紧张时仍可进入（付高价），低优推理只在空闲时进入（付低价）。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 和 DeepShare 的区别是什么？你们为什么做了两个系统？</div>
<div class="qa-a"><p>DeepShare 解决的是<strong>多租户之间</strong>的配额管理（A 团队和 B 团队之间怎么借 GPU），合用对象是训练+训练；ElastiCo 解决的是<strong>同一 GPU 上训推</strong>的共置问题，两者在不同层级。而且训推共置有特殊挑战：训练是长作业、不能被杀（重启代价大），离线推理是短作业、可以被暂停/驱逐——这种主客不对称性是 DeepShare 没有的。两者可以组合：DeepShare 做集群级租户治理，ElastiCo 做节点级训推填充。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "无需改动用户代码"具体怎么做到的？</div>
<div class="qa-a"><p>三层透明注入：(1) Admission Webhook 自动给 Pod 注入 MPS 环境变量和 VMM 配置；(2) Node Agent（DaemonSet）通过 CUDA Driver API 动态管理显存映射和 SM 限制，不经过用户代码；(3) Scheduler Plugin 在调度时做放置决策，用户只需给 Pod 打上 `elastico.sh/class: training` 或 `inference` 标签。底层用 LD_PRELOAD hook 部分 CUDA 内存分配 API 实现显存记账，对训练/推理框架完全透明。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 利用率 46% 也不算高啊？为什么不是更高？</div>
<div class="qa-a"><p>25% → 46% 已经是将近翻倍的提升。为什么不是 70%+？(1) 我们有严格的 SLO 约束——训练 slowdown 不能超过阈值（约 10%），推理 SLO 必须达标；(2) 训练的空窗期不是完全可预测的，有时推理刚加载进来训练就开始计算了，需要保护训练；(3) 显存容量是硬约束——训练占了大部分显存（权重+梯度+优化器状态），推理的 KV Cache 和权重可用空间有限；(4) 46% 是<strong>安全共置</strong>下的利用率，牺牲部分利用率换 SLO 保证是合理的 trade-off。</p></div>
</div>
</div>

<div class="card card-s">
<h3>SagePilot（撰写中）简历追问</h3>
<p class="text-muted">简历原文："结构感知的深度学习负载资源预测与 Agentic 工作流编排（SagePilot）。计算图表征：ONNX 计算图→图样本，融合算子类型、张量形状与拓扑结构。GNN 多目标预测：一次前向预测时延、显存峰值、GPU 利用率，免反复试跑。Benchmark：运行时程序分析自动采集，10W+ 条，覆盖 CNN/Transformer/推荐。工作流编排：冷启动预部署、OOM 风险选卡、显存复用与驱逐。"</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么需要"不运行就预测"？直接 profile 不行吗？</div>
<div class="qa-a"><p>Profiling 成本非常高：一个 7B 模型在 A100 上跑一次推理 profiling 需要几分钟到十几分钟，如果要测多个 batch size、序列长度、GPU 型号组合，可能需要几小时、占用多张 GPU。对于大模型（70B），profiling 本身就需要多卡，成本更高。而且在 Agentic 场景下，模型组合是动态的（用户请求决定用哪个模型），无法提前 profile 所有组合。SagePilot 通过 ONNX 图 + GNN 一次前向推理（毫秒级）就能给出多指标预测，零试跑成本。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么用 GNN？计算图和 GNN 的图是什么关系？</div>
<div class="qa-a"><p>ONNX 计算图天然就是 DAG——节点是算子（matmul、conv、layernorm），边是张量（带 shape 和 dtype）。GNN 的消息传递机制恰好模拟了张量在算子间的流动：每个算子节点聚合其输入张量的信息，类似实际执行时算子读入输入计算输出的过程。MLP/CNN 无法处理变长拓扑（不同模型节点数从几百到几万不等），GNN 天然支持。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 多目标预测具体怎么做的？显存预测 OOM 怎么办？</div>
<div class="qa-a"><p>共享 GIN backbone，三个独立 MLP 输出头分别预测时延、显存、利用率。训练时用 uncertainty weighting 自动平衡三个 loss。显存预测使用<strong>非对称 loss</strong>——低估的惩罚是高估的 3 倍，因为低估导致 OOM（请求直接失败），高估只是浪费显存（可接受）。预测结果加安全裕度 ρ ∈ [0.1, 0.3]。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ONNX 图丢了 kernel fusion 等运行时信息，预测准吗？</div>
<div class="qa-a"><p>这是个好问题。ONNX 静态图确实看不到推理引擎的 kernel fusion 策略，但我们做了补偿：(1) 训练标签来自真实执行的 profiling 数据，fusion 带来的加速已经隐含在标签里，GNN 会学习到哪些算子模式容易被融合；(2) 加入常见 fusion pattern 的特征（如 matmul+bias+gelu 的组合模式）；(3) 对于特定引擎（TensorRT）可以加一个校准步骤，用少量 profiling 数据 fine-tune。当前 R² 在 0.8 左右，对资源调度场景足够。</p></div>
</div>
</div>

<div class="card card-r">
<h3>跨论文追问（面试官可能串联提问）</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你做了这么多调度系统，核心方法论是什么？</div>
<div class="qa-a"><p>贯穿几篇工作的核心理念是<strong>用轻量预测为调度器提供前瞻性信号，再设计弹性资源管理和代价感知抢占来利用这些信号</strong>。DeepShare 预测作业运行时间来做排序和抢占，Maestro 预测输出长度来做显存分配和 SRTF 调度，ElastiCo 用影子定价（本质也是基于利用率的预测）做共置准入，SagePilot 直接预测模型资源画像。共同模式是：(1) 识别可预测的信号；(2) 选择轻量、低延迟、可泛化的预测模型（LightGBM/RF/GNN，不用大模型）；(3) 设计弹性机制利用预测信号获益，同时有安全兜底应对预测错误。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 这些系统都是在 Kubernetes 上做的，为什么不自己做一个调度器？</div>
<div class="qa-a"><p>Kubernetes 已经是 GPU 集群管理的事实标准，生态成熟（device plugin、CSI、CNI、Prometheus 监控）。基于 K8s Scheduler Framework 做插件可以复用大部分基础设施（节点管理、Pod 生命周期、资源账本），只需要扩展调度逻辑，用户迁移成本低。DeepShare 和 ElastiCo 都是 Scheduler Plugin + Controller + DaemonSet 的架构，不侵入 kube-scheduler 核心代码，升级 K8s 版本时维护成本低。Crater 开源平台也是基于 K8s + Volcano，验证了这个路线的可行性。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你在这些论文中具体负责什么？哪些是你做的？</div>
<div class="qa-a"><p>四篇一作论文中我都是第一作者，负责问题定义、系统设计、核心算法实现、实验验证和论文写作。具体来说：DeepShare 中我设计了 QAD 指标和三个子系统的协同机制，实现了 K8s Scheduler Plugin 和 Controller 的核心代码，跑了 64 卡实测和 trace 仿真；Maestro 中我设计了两阶段预测器和 CUDA VMM 弹性显存管理，实现了节点级运行时和全局调度器；ElastiCo 中我提出了资源形态变换和影子定价机制，实现了训推共置的 K8s 中间件；SagePilot 中我设计了计算图表征方案和 GNN 多任务架构，搭建了自动化数据采集 pipeline。导师给方向指导，合作者协助部分实验对比。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你的工作有什么局限性？如果再做一遍会改进什么？</div>
<div class="qa-a"><p>几个明确的局限：(1) 预测模型都需要训练数据，新场景/新硬件冷启动需要少量 profiling 数据做校准，未来方向是用 transfer learning 减少冷启动成本；(2) ElastiCo 目前只支持离线推理和训练共置，在线推理有严格 TTFT 要求，共置风险更大；(3) DeepShare 的 colocation 用 MPS 做 SM 隔离，但 MPS 不支持显存硬隔离（只是建议值），极端情况下一个任务可能撑爆显存影响另一个；(4) SagePilot 的 GNN 在超大规模计算图（>10万节点）上推理延迟可能成为瓶颈，需要子图采样或层次化预测。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你在字节实习做的跨团队二级调度框架，和你论文中的调度思想有什么联系？</div>
<div class="qa-a"><p>核心思想一脉相承：都是<strong>在固定配额基础上做弹性资源借用和抢占回收</strong>。实习项目解决的是工业界真实问题——GPU 按团队固定分配导致 400 张卡闲置但其他团队排队，我设计的跨团队 Spot 资源动态分配和多维约束抢占回收算法，本质上和 DeepShare 的 DRA + 代价感知抢占是同一类问题。区别是工业界有更复杂的业务约束（ABC 多级优先级、MySQL + Redis 存储、Thrift RPC 对接 Merlin），而论文可以更干净地做形式化和算法设计。实习反过来也验证了论文中的弹性配额和抢占思路在生产环境是有实际需求的。</p></div>
</div>
</div>

<div class="card card-w">
<h3>面试官"挑刺"与陷阱题</h3>
<p class="text-muted">面试官可能用挑战性问题试探你对自己工作的理解深度——不是真的否定你，而是看你是否思考过弱点。这些问题如果没准备过很容易卡壳。</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Maestro 说 KV 预留显存降低 67.2%，但这不是靠 CUDA VMM 超配"骗"出来的吗？实际物理显存并没有减少啊？</div>
<div class="qa-a"><p>这个问题很尖锐。需要分清两个层面：(1) <strong>预留（reservation）≠ 实际使用</strong>。传统方案为每个请求预分配最大 KV 空间（物理显存），即使实际输出很短也占着不放——这是真正的浪费。CUDA VMM 让虚拟地址远大于物理显存，但物理页按需映射，真正减少的是物理显存占用。(2) 67.2% 降低的是<strong>预留的 HBM 物理显存</strong>，不是虚拟地址。我们通过输出长度预测来决定实际映射多少物理页，短请求只映射少量物理页，其余虚拟地址不占物理内存。统计复用的前提是多 Agent 的 KV 峰值不重叠。如果所有请求同时输出长文本还是会 OOM，但实际 trace 中这种概率极低，且有准入控制兜底。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 预测器出错了怎么办？如果预测输出 100 token 实际输出了 1000 token 呢？</div>
<div class="qa-a"><p>这是所有预测驱动系统都要面对的问题。我们做了三层防护：(1) <strong>偏向高估</strong>——训练 loss 对低估加惩罚（类似 SagePilot 的非对称 loss），预测值偏高而不是偏低，宁可浪费不能 OOM；(2) <strong>动态扩容</strong>——KV 内存在 decode 过程中按页增长（paged attention 类似 vLLM 的思路），不是一次分配完，如果实际输出超过预测，运行时可以追加映射物理页；(3) <strong>优雅降级</strong>——如果物理内存真的耗尽，选择抢占/暂停优先级最低的 stage 释放空间，而不是让整个服务崩溃。预测准确率 R²=0.78 看起来不高，但配合安全裕度和动态扩容，实际 OOM 率 < 0.1%。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: DeepShare 的干扰预测 R²=0.902 就敢用来做共置决策？万一预测错了把高优任务拖慢了怎么办？</div>
<div class="qa-a"><p>R²=0.902 是在<strong>离线测试集</strong>上的指标，真正运行时我们不依赖单点预测做决策，而是：(1) <strong>保守准入</strong>——预测 slowdown < 5% 才允许共置，留出足够安全边界；(2) <strong>运行时闭环</strong>——共置后持续监控实际 slowdown（通过 DCGM 实时采集 SM 利用率），一旦实测 slowdown 超过阈值（如 10%）立即驱逐 Best-effort 任务，反应时间在秒级；(3) <strong>只对 Best-effort 任务冒险</strong>——Guaranteed 任务的资源绝不用于共置，只有空闲配额借出的 Best-effort 任务才参与共置，预测错误最坏情况是杀掉 Best-effort 任务，不影响 Guaranteed QoS。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你们所有论文都用 trace 仿真+小集群实测，怎么证明在大规模生产环境有效？</div>
<div class="qa-a"><p>这是学术研究的通用方法论局限。我们做了几件事增强可信度：(1) Trace 来自真实生产集群（Venus 23,859 条作业、Maestro 46,769 条 stage），不是合成数据；(2) 仿真器参数从 16 节点原型实测校准，保证仿真结果和真实环境趋势一致；(3) 64 卡 K8s 实测验证了关键结论（端到端 JCT、SLO 达成率），仿真主要用于验证大规模扩展性；(4) ElastiCo 做了 512 卡仿真看 scaling 趋势；(5) 字节实习中验证了核心算法思想在生产环境的可行性——弹性配额借用和代价感知抢占在工业界确实能落地。当然，真正部署到几千卡集群还需要更多工程鲁棒性工作，这也是未来方向。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不直接用 vLLM/TGI 这些现成的推理框架？它们已经有 PagedAttention、continuous batching 了。</div>
<div class="qa-a"><p>这是不同层面的优化：vLLM/TGI 优化的是<strong>单节点内</strong>推理引擎的 batching 和 KV 管理（PagedAttention 解决内部碎片、continuous batching 提高 GPU 利用率），Maestro 解决的是<strong>多节点、多模型、多 Agent 工作流</strong>的调度问题——一个用户请求涉及十几个 Agent stage、用多个不同模型、分布在多块 GPU 上。Maestro 可以和 vLLM 配合使用：节点内用 vLLM 做推理引擎优化，节点间用 Maestro 做工作流感知调度和显存管理。事实上我们的原型就是基于 vLLM 做的，分级权重缓存和 CUDA VMM 超配是在 vLLM 之上的额外优化。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: EDF 作为 baseline 是不是太弱了？为什么不和更先进的方法比？</div>
<div class="qa-a"><p>EDF 是实时调度的经典 baseline，但我们的对比不只是 EDF。Maestro 对比了 EDF、SRTF（无预测）、FCFS、Karma（LLM 服务最近的调度工作）；DeepShare 对比了 Lucid（GPU 共享最强无侵入基线）、Gandiva（协同调度）、Tiresias（GPU 调度经典工作）、K8s 默认调度器。关键是 Maestro 的核心贡献不是调度算法本身（SRTF 是经典算法），而是<strong>把预测信号引入 LLM-MAS 场景</strong>并设计弹性显存机制来利用这些预测。和纯算法 baseline 比是为了证明预测信号的价值，而不是发明新的排序算法。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MPS 有已知的问题啊——一个 CUDA context 段错误会影响 MPS server 下所有进程，你们怎么处理的？</div>
<div class="qa-a"><p>确实，MPS 的一个已知风险是故障隔离差。我们的应对：(1) 只在<strong>受控环境</strong>下使用 MPS 共置——Best-effort 任务和 Guaranteed 任务共置时，Best-effort 任务是经过准入检查的（短作业、已知模型类型），减少未知风险；(2) 每个 GPU 节点上跑 MPS health monitor，检测到 MPS server 异常立即重启并隔离该节点上的新任务调度；(3) ElastiCo 场景下训练任务直接跑在 GPU 上（不经 MPS），推理任务通过 MPS 共享 SM，训练故障不依赖 MPS；(4) 对于生产环境，长期方案是用 MIG 或时间片（MPS 属于进程级共享，MIG 是硬件级隔离），但 MIG 不支持动态 SM 划分，ElastiCo 的动态资源形态变换目前只能通过 MPS 实现。</p></div>
</div>
</div>

<div class="card card-s">
<h3>Crater 开源平台追问</h3>
<p class="text-muted">简历原文："主导基于 Kubernetes 的 GPU 集群管理平台 Crater...已在实验室稳定运行 1.5 年，纳管 250+ 张 GPU、日均调度 200+ 任务，Apache-2.0 开源。"这是工程能力的重要证明。</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Crater 和 Volcano/Kubeflow 有什么区别？为什么不直接用现成的？</div>
<div class="qa-a"><p>Volcano 提供了队列、优先级、gang scheduling 等基础能力，但它是<strong>通用的</strong>批调度器，缺少科研场景需要的功能：(1) 配额管理是硬划分，没有 DeepShare/ElastiCo 那种弹性借用；(2) 没有用户管理、审批流程、账户计费——科研集群需要导师审批学生的 GPU 使用；(3) 没有一键 LLM 训练/推理的作业模板，用户要写完整 YAML；(4) 没有集成 Jupyter/WebIDE/终端开发环境，科研用户需要交互式开发。Kubeflow 更偏 ML pipeline，不是集群管理平台。Crater 在 Volcano 基础上做了面向科研场景的封装和增强，整合了 DeepShare 和 ElastiCo 的调度能力，提供 Web 控制台降低使用门槛。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 250 张 GPU 的集群，你作为项目负责人最头疼的技术问题是什么？</div>
<div class="qa-a"><p>最头疼的是<strong>多用户场景下的 GPU 资源争用和占卡不释放问题</strong>。实验室场景下学生经常启动 Jupyter 后忘记关，GPU 被占着但利用率为 0。我们做了：(1) 占卡检测——Agent 监控 GPU 利用率，连续 N 分钟低于阈值就通知用户，超时自动回收；(2) 交互式任务有最长运行时间限制（默认 12 小时，可以续期）；(3) 训练任务必须在容器内跑，容器退出自动释放资源；(4) 空闲 GPU 标记和自动推荐。另外一个挑战是多型号 GPU（A100/A800/3090/4090/V100 混合），不同作业对 GPU 型号有不同要求，调度器需要感知拓扑和型号约束。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Crater 的技术栈是 Go/React/Helm，你在其中写了多少代码？哪部分最复杂？</div>
<div class="qa-a"><p>我是项目负责人，核心后端（Go）大约 70% 是我写的，包括自定义 Controller、Scheduler Plugin、API Server、配额管理逻辑；前端（React/TypeScript）主要是两个师弟做的，我做了架构设计和 Code Review；Helm Chart 和部署脚本是我写的。最复杂的部分是<strong>调度器和 K8s controller 的设计</strong>——队列状态机、配额超分/回收逻辑、和 Volcano 的协同、多维度抢占顺序的正确性保证。调试调度器问题非常痛苦，因为状态分布在 etcd、scheduler cache、node agent 多处，需要全链路 tracing。</p></div>
</div>
</div>

<div class="card card-m">
<h3>论文间深层关系与体系化思考</h3>
<p class="text-muted">面试官喜欢问"你的几篇论文之间是什么关系"——这考察你是否有体系化的研究视角，而不是零散地做了几个项目。</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你的几篇工作（DeepShare/Maestro/ElastiCo/SagePilot）是一开始就规划好的 research line，还是逐步演进的？</div>
<div class="qa-a"><p>是<strong>从实践中逐步演进</strong>出来的，不是一开始就规划好的。最早做 Crater 平台（2023）时发现真实 GPU 集群利用率只有 25-40%，于是做了 DeepShare 解决多租户配额借用问题（集群级）；在 DeepShare 实测中发现训推混部是更大的利用率提升空间，而且有独特的主客不对称挑战，于是做了 ElastiCo（节点级训推）；同时在 LLM Agent 场景下发现输出长度不确定是全新的调度挑战，做了 Maestro（请求级 LLM 推理）；在所有这些工作中反复遇到一个痛点——资源画像预测不准，需要 profiling，于是做 SagePilot（预测底座）。回头看形成了从<strong>集群→节点→请求→预测</strong>的逐层深入，但当时是跟着实际问题走的。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果让你把这四个系统合并成一个超级系统，架构会是什么样？</div>
<div class="qa-a"><p>这是个好问题。分层架构：(1) <strong>预测层（SagePilot）</strong>——所有上层决策的基础，提供作业/模型/请求级别的资源画像预测，不需要运行就能给出时延、显存、利用率估计；(2) <strong>集群调度层（DeepShare）</strong>——基于 QAD 做多租户配额管理、弹性借用、全局排序和抢占决策，决定作业放到哪个节点；(3) <strong>节点运行时层（ElastiCo + Maestro）</strong>——在节点内做精细资源管理：训推共置用 ElastiCo 的资源形态变换和影子定价，LLM 推理用 Maestro 的分级权重缓存和 CUDA VMM 弹性显存，stage 边界抢占。Crater 是产品形态，把这些能力封装成用户友好的平台。共同的设计原则：预测驱动、弹性资源、代价感知、安全兜底。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你的工作和业界主流方案（K8s + Volcano/YARN/Kubernetes Scheduler）比，最大的 gap 在哪里？为什么工业界没有这样做？</div>
<div class="qa-a"><p>几个原因：(1) <strong>工业界优先稳定性</strong>——预测驱动调度如果预测出错会产生线上事故，工业界倾向用简单确定性策略（优先级队列+固定配额），学术界更愿意用预测换效率；(2) <strong>工作负载差异</strong>——我们的场景是科研集群+LLM Agent，负载波动大、任务类型多样，弹性收益明显；而大厂在线服务集群负载规律，弹性空间小；(3) <strong>工程复杂度</strong>——MPS 共置、CUDA VMM 超配、干扰预测都需要精细的工程实现和监控，大厂有更成熟的隔离方案（如 MIG、物理分区）；(4) 但趋势是工业界也在往这个方向走——字节内部的跨团队 Spot 调度、云厂商的 GPU 共享（如阿里云 cGPU、腾讯 qGPU）本质上都是弹性配额和精细隔离。我们的工作提供了算法和机制上的验证。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ESCAPE（IEEE JCC Best Paper）和你后面的工作有什么关系？</div>
<div class="qa-a"><p>ESCAPE 是我硕士阶段做的微服务资源估算工作，用 GNN + Profiling Engine 预测微服务的资源需求。这是我第一次接触<strong>"用 ML 做资源预测"</strong>这个方向，GNN 的使用经验直接启发了 SagePilot 的计算图表征思路——微服务调用图和 DNN 计算图在结构上都是 DAG，都可以用 GNN 建模；Profile Engine 的经验让我意识到 profiling 成本问题，才有了 SagePilot "零试跑预测"的动机。可以说 ESCAPE 是 research line 的起点，后面的 DeepShare/Maestro/ElastiCo 都需要预测信号，SagePilot 是回到预测这个基础问题上做深度工作。</p></div>
</div>
</div>

<div class="card card-r">
<h3>压力面与行为题（结合论文经历）</h3>
<p class="text-muted">面试官可能在技术讨论中穿插行为面试问题，用你的论文经历来考察软素质。这些问题需要用 STAR 法则回答。</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 做论文过程中遇到最大的困难是什么？怎么解决的？</div>
<div class="qa-a"><p>（STAR 示例）S: DeepShare 做 64 卡实测时，干扰预测模型在实验环境精度很高（R²=0.9），但部署到真实集群后预测完全不准，共置任务频繁 slowdown 超阈值。T: 需要在不重写系统的前提下找出原因并修复。A: 我花了两周时间排查：(1) 先加详细日志记录每次共置的特征和实际 slowdown；(2) 发现实验环境用的是同一类型 GPU（A100），但真实集群有多种型号 GPU 混用，DCGM 指标在不同型号上的分布差异很大；(3) 训练数据只覆盖了 A100，没有做跨 GPU 泛化。解决方案是为每个 GPU 型号训练独立的 RF 模型，并加入 GPU 型号作为特征，同时引入 online fine-tuning——新的共置数据持续更新模型。R: 修复后跨型号预测 R² 恢复到 0.85 以上，共置 QoS 达标率从 60% 回升到 93%。这个教训让我在后续 ElastiCo 和 SagePilot 中都提前考虑了跨硬件泛化问题。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果导师给你的方向你觉得不对，你会怎么办？（结合 ElastiCo/DeepShare 的选题经历）</div>
<div class="qa-a"><p>我会<strong>先做小实验验证</strong>而不是直接反驳。例如最初导师建议在 DeepShare 中用强化学习做调度决策，我做了 literature review 后发现 RL 在调度场景的 sample efficiency 很低，真实集群无法承受在线探索的代价。但我没有直接否定，而是用一周时间做了个小 prototype：用 DQN 在仿真环境训练，对比 RF + 启发式规则的方案，结果 RL 收敛慢、调参困难、泛化差。带着数据和导师讨论，最终改用 RF 干扰预测 + 启发式排序的方案。我觉得导师给方向是大方向指引，具体技术选型需要自己用实验验证，用数据说话比争论更有效。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你同时推进 DeepShare、Maestro、ElastiCo、SagePilot 四个项目，怎么管理时间和优先级？</div>
<div class="qa-a"><p>这确实是博士期间的挑战。我的方法：(1) <strong>串行深入、并行维持</strong>——一个时间段主攻一个项目（做核心实验和写作），其他项目只做基础推进（每周开一次会、review 合作者进度）；(2) <strong>复用基础设施</strong>——四个项目共享 Crater 平台、trace 采集 pipeline、K8s 部署脚本，避免重复造轮子；(3) <strong>借助合作者</strong>——ElastiCo 有师弟帮忙做部分实验对比，SagePilot 的 ONNX 解析和图特征工程有一个本科生协助，我专注核心算法设计和论文写作；(4) <strong>按截止日期排列优先级</strong>——会议截稿日期前 2 个月集中全部精力在那篇论文上。关键是识别项目之间的依赖关系（比如 SagePilot 的预测能力反过来可以增强 Maestro），让它们互相促进而不是互相竞争。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你的一作论文有四篇，最满意哪一篇？为什么？</div>
<div class="qa-a"><p>最满意 DeepShare。原因：(1) <strong>从问题到落地完整闭环</strong>——它是从 Crater 平台真实问题出发，经过 QAD 指标设计、系统实现、64 卡实测、开源验证完整走通的，不只是算法创新，而是真正在 250 卡集群上跑了一年多的系统；(2) <strong>工程和研究的平衡最好</strong>——QAD 指标虽然简单，但统一协调四个子系统的设计很优雅，工程实现也足够扎实（Scheduler Plugin + Controller + DaemonSet 架构）；(3) <strong>反馈最好</strong>——在实验室落地后确实解决了 GPU 争抢问题，同学们的作业等待时间明显缩短，这种"真的有人在用"的感觉比论文中稿更有成就感。Maestro 的 LLM 场景更新颖，但 DeepShare 是我从系统思维到工程能力成长最多的一篇。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你在寒武纪实习做 TF 算子适配，这段经历对你后面做 GPU 调度有什么帮助？</div>
<div class="qa-a"><p>帮助很大，让我从<strong>底层理解了 AI 芯片的执行模型</strong>：(1) 做算子适配时需要理解 chip 的内存层次（SRAM/DRAM/片上缓存）、并行方式（多核/向量/张量核）、算子切分和 fusion 策略，这让我后来在做 GPU 调度时能从硬件特性出发思考问题——比如为什么 SM 和显存是两种不同资源、为什么 kernel fusion 会影响 SM 利用率、为什么 MPS 的 SM 比例调整不能太频繁；(2) C++ 底层调试经验让我在做 CUDA VMM、MPS 配置、LD_PRELOAD hook 时不怕碰底层；(3) 国产芯片的适配经历让我对硬件异构性有直观感受，后来 SagePilot 做跨 GPU 泛化时我就知道不同硬件的 performance counter 含义和分布差异很大。</p></div>
</div>
</div>

<div class="card card-d">
<h3>场景题：如果面试官问"你来我们团队会怎么做"</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果加入我们团队做 AI Infra，你觉得你的研究经验能怎么转化为业务价值？</div>
<div class="qa-a"><p>几个直接相关点：(1) <strong>GPU 利用率优化</strong>——我在 DeepShare/ElastiCo 中做的弹性配额、干扰感知共置、训推混部可以直接应用于提高集群利用率，字节实习中已经验证了类似思路在生产环境可行（400 张空闲卡问题）；(2) <strong>LLM 推理系统</strong>——Maestro 的输出长度预测、分级权重缓存、CUDA VMM 弹性显存思路可以优化 LLM 推理服务的显存利用率和 TTFT；(3) <strong>K8s 调度器开发经验</strong>——我有从零写 Scheduler Plugin、Controller、DaemonSet 的实战经验，不需要 Ramp-up 就能上手 K8s 相关开发；(4) <strong>性能预测能力</strong>——SagePilot 的 GNN 预测思路可以用于作业调度前的资源预估、容量规划、自动扩缩容决策；(5) <strong>工程能力</strong>——Crater 250 卡开源平台的经验证明我能把研究原型推进到生产级可用系统。</p></div>
</div>
</div>

## 关联模块

- `论文工作 / Maestro`：Maestro 详细设计和问答。
- `论文工作 / DeepShare`：DeepShare 详细设计和问答。
- `论文工作 / ElastiCo`：训推混部机制细节。
- `论文工作 / SagePilot`：GNN 预测技术细节。
