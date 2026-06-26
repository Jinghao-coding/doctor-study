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

## 关联模块

- `论文工作 / Maestro`：Maestro 详细设计和问答。
- `论文工作 / DeepShare`：DeepShare 详细设计和问答。
- `论文工作 / ElastiCo`：训推混部机制细节。
- `论文工作 / SagePilot`：GNN 预测技术细节。
