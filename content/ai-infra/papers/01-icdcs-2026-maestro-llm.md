<div class="card card-s" style="margin-top:0.8rem">
<p><strong>📄 论文原文：</strong><a href="../../../resources/papers/ICDCS2026_Maestro.pdf" target="_blank">ICDCS 2026 — Maestro PDF</a></p>
</div>

<div class="card card-m">
<h3>问题背景</h3>
<p>传统 LLM 推理面对的是独立的一问一答请求。但现在越来越多的应用把多个 agent 组成协作工作流：比如旅行助手里有"需求分析 agent"、"机票搜索 agent"、"酒店推荐 agent"、"行程整合 agent"，它们之间有 DAG 依赖，一个用户请求触发十几次甚至几十次 LLM 推理调用（称为 stage）。</p>
<p>这带来了三个新挑战：</p>
<ol>
<li><strong>输出长度剧烈波动</strong>：工具调用输出几十 token（JSON），用户交互输出几百上千 token。KV 缓存需求差异巨大，固定分配要么浪费要么 OOM。</li>
<li><strong>多模型共存的内存压力</strong>：不同 agent 使用不同模型，一块 GPU 需要同时驻留多个模型权重加上所有请求的 KV 缓存。</li>
<li><strong>混合延迟要求</strong>：交互式 stage 要低延迟，批处理 stage 要高吞吐。不区分优先级就会造成队头阻塞。</li>
</ol>
</div>

<div class="card card-m">
<h3>系统设计</h3>
<p>核心思路：<span class="hl">不把 LLM 请求当黑盒，利用 agent 上下文做前瞻性预测，指导内存管理和调度。</span></p>

<div class="comp">
<div class="comp-t">组件一：两阶段输出长度预测</div>

<h4>为什么需要预测输出长度？</h4>
<p>LLM 推理的输出长度直接决定两件事：<strong>KV Cache 大小</strong>（每多输出一个 token，KV cache 就多存一组 key/value 向量）和<strong>decode 耗时</strong>（每步 decode 读 KV cache + 矩阵乘，token 越多耗时越长）。而在 LLM-MAS 场景下，不同 agent 的输出长度差异巨大——工具调用几十 token（JSON），用户交互几百上千 token。如果在请求开始前不预测，就无法做资源规划（给多少 KV 显存）和调度排序（谁先谁后），要么浪费要么 OOM。</p>

<h4>预测流水线：两个 GBDT 模型串联，BERT 负责提取语义特征</h4>
<pre><code class="language-flow">                    prompt 文本
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
    MiniLM 编码             结构化特征提取
    (轻量 BERT, 33M)       (role / 工作流位置 /
    384 维向量                 调用索引 / 工具可用性)
            │                       │
            ▼                       │
    PCA 降维 384→32 维              │
    (保留 ~85% 方差)                │
            │                       │
            └───────────┬───────────┘
                        │
                        ▼
            ┌──────────────────────┐
            │  第一阶段：LightGBM    │  二分类：会触发工具调用吗？
            │  分类器               │  AUC = 0.9625
            │  (GBDT)              │  输出连续概率 p̂_tool
            └──────────┬───────────┘
                       │ p̂_tool（经 isotonic regression 校准）
                       ▼
            ┌──────────────────────┐
            │  第二阶段：LightGBM    │  回归：输出多少 token？
            │  回归器               │  MAE = 165, R² = 0.78
            │  (GBDT)              │  对 log(1+L) 建模
            └──────────┬───────────┘
                       │
                       ▼
                  预测 token 数</code></pre>
<p>这里有一个容易被误解的地方：论文图 6 中 BERT/MiniLM 紧邻着 "Classification" 画线，但它<strong>不是分类器本身，而是语义特征提取器</strong>。MiniLM 把 prompt 文本编码为 384 维向量 → PCA 降到 32 维 → 作为特征之一喂入 LightGBM 分类器。真正的分类决策是 LightGBM（GBDT）做的，和第二阶段回归器用的是同一种算法。</p>
<p>第一阶段分类器输出的是<strong>连续概率 p̂_tool</strong>（经 isotonic regression 校准），而非 0/1 离散值。这个概率作为第二阶段回归器的输入特征之一，让回归器知道"当前 stage 有多大概率是工具调用模式"。</p>

<h4>特征工程</h4>
<p><strong>结构化特征</strong>（表格特征，直接可用）：</p>
<ul>
<li><strong>agent 角色</strong>：当前 stage 是搜索/推荐/整合/... agent，one-hot 编码</li>
<li><strong>工作流位置</strong>：节点在图中的入度、出度、深度，反映该 stage 在 DAG 中的位置和依赖关系</li>
<li><strong>调用索引</strong>：当前 stage 在工作流中是第几个被调用的——靠前的 stage 通常输出较短（中间步骤），靠后的 stage 输出较长（汇总结果）</li>
<li><strong>工具可用性</strong>：该 agent 挂了多少工具、工具类型——工具多的 agent 更可能触发工具调用（短输出），纯文本 agent 更可能生成长输出</li>
</ul>
<p><strong>语义特征</strong>（prompt 文本 → 向量 → 降维）：</p>
<ol>
<li><strong>编码</strong>：用 MiniLM（微软的轻量 transformer，约 33M 参数）将 prompt 文本编码为 384 维向量</li>
<li><strong>降维</strong>：PCA 从 384 维 → 32 维，保留约 85% 方差</li>
</ol>
<p>降维有两个目的：384 维对 LightGBM 来说维度过高容易过拟合（训练集 4 万条样本，特征维度太高模型会记样本而非学模式），以及语义编码中部分维度是噪声（MiniLM 在通用文本上预训练，LLM agent prompt 的某些语义差异对输出长度预测无用）。<strong>消融实验</strong>：去掉语义特征，AUC 从 0.9625 降到约 0.93，证明语义信息确实提供了结构化特征无法捕捉的信号——同一个 agent 角色同一个工作流位置，不同的 prompt 内容会导致不同的输出长度。</p>

<h4>训练技巧</h4>
<p><strong>1. Log 变换处理长尾分布</strong>：输出 token 数不是正态分布——绝大部分请求 50-500 token，偶尔有 2000+ 的极端值。直接回归 MSE 会被极端值主导。做法是回归器在 log 空间学习 y' = ln(1+y)，推理时 exp 反变换。</p>
<p><strong>2. Isotonic Regression 校准</strong>：LightGBM 输出的概率 p̂_tool 不一定校准良好（预测 0.7 不代表 70% 概率真的触发工具调用）。Isotonic regression 用保序回归在验证集上拟合一条校准曲线，让概率值对齐真实频率。校准后的概率作为回归器特征更可靠。</p>
<p><strong>3. 非对称 Loss 偏向高估</strong>：回归器 loss 对<strong>低估的惩罚 > 高估的惩罚</strong>。低估 → KV 分配不够 → OOM → 请求被杀（灾难性后果）；高估 → 暂时多占一点显存 → 后续可回收（可接受代价）。配合安全裕度 ρ ∈ [0.1, 0.3]，实际 KV 分配 = 预测值 × (1+ρ)。</p>

<h4>为什么必须两阶段？一阶段直接回归为什么不行？</h4>
<p>输出长度呈<strong>双峰分布</strong>：工具调用集中在几十 token（窄峰），用户交互分散在几百到上千 token（宽峰）。单一回归器面对双峰数据只能取折中——预测值落在两峰之间，对哪个峰都不准。</p>
<p>两阶段的核心思路是<strong>"先识别模式，再在模式内预测"</strong>：分类器先判断"这个请求属于工具调用模式还是用户交互模式"，回归器在给定模式约束下做精确预测。消融实验证明：<strong>去掉分类器头，MAE 从 134 上升到 142</strong>（越高越差），验证了"先分后回归"的价值。</p>

<h4>预测信号如何驱动下游组件</h4>
<table>
<tr><th>组件</th><th>消费方式</th><th>为什么这样用</th></tr>
<tr><td>KV 显存分配</td><td>预测值 × (1+ρ) → 初始物理页映射量</td><td>decode 过程按需追加映射页，不是一次性分配完；预测短则初始少映射，后续不够再追加</td></tr>
<tr><td>SRTF 调度</td><td>预测 token 数 ÷ 解码速度 → 剩余执行时间 → 排队优先级</td><td>短作业先跑减少队头阻塞；交互式 stage 排批处理前面；纯预测（不依赖已执行时间）让新到达的短 stage 可以插队</td></tr>
<tr><td>准入控制</td><td>检查剩余物理显存 ≥ 预测 KV 需求</td><td>不够则拒绝该 stage，避免 OOM 连锁反应；配合安全裕度保证高估侧有缓冲</td></tr>
</table>
<p>三者之间有安全裕度 ρ 做缓冲——预测不可能 100% 准确（R²=0.78），偏高一侧留出余地，配合动态扩容和优雅降级，实际 OOM 率压到 0.1% 以下。</p>
</div>

<div class="comp">
<div class="comp-t">组件二：节点级弹性内存管理</div>
<p><strong>模型状态管理</strong>：五种状态按层级流转——</p>
<ul>
<li><strong>Running</strong>：权重在 GPU，可立即执行推理</li>
<li><strong>Sleeping</strong>：权重移到 CPU，但 GPU 上保留 CUDA Graph 和 JIT 内核缓存（约 0.5GB），重新激活省 5-8 秒</li>
<li><strong>CPU-resident</strong>：权重完全在 CPU 内存</li>
<li><strong>Disk-resident</strong>：权重在本地 NVMe</li>
<li><strong>Remote</strong>：权重在远程存储</li>
</ul>
<p>层级化 LRU 逐级淘汰，最热的模型留 GPU，最冷的逐步退到远端。</p>
<p><strong>KV 缓存管理</strong>：CUDA VMM 虚拟内存超配——40GB 物理 GPU 上分配 122GB 虚拟地址池（3 倍超配）。关键在于虚拟地址和物理页分离，按需映射物理页。三层防护：(1) 虚拟 vs 物理分离，不会同时达峰；(2) 准入控制——每个 stage 检查剩余物理页是否够；(3) 映射失败时拒绝 stage 而非崩溃。五级降级策略保证极端情况也不会 OOM。</p>
<p><strong>内存核算</strong>：M_kv + M_res ≤ M_total，安全裕度 ρ ∈ [0.1, 0.3]，偏向高估以避免低估导致 OOM。</p>
</div>

<div class="comp">
<div class="comp-t">组件三：工作流感知 SRTF 调度</div>
<p>基于预测的剩余执行时间排队（SRTF），优先执行快要完成的工作流。交互式和批处理 stage 分开排队。Stage 边界抢占——只在两次 LLM 调用之间切换，不打断正在解码的请求。</p>
<p><strong>节点选择</strong>：适应度评分 S(N,T) = A(N,T) − λ·T_ready − μ·C_deg，综合模型就绪延迟和降级代价。</p>
</div>

<h3>核心结果</h3>
<div class="grid">
<div class="gi"><div class="gv">+23.6pp</div><div class="gl">SLO 达成率 (vs EDF)</div></div>
<div class="gi"><div class="gv">−67.2%</div><div class="gl">KV 预留内存</div></div>
<div class="gi"><div class="gv">−84.8%</div><div class="gl">交互排队延迟</div></div>
<div class="gi"><div class="gv">64×A100</div><div class="gl">14.4 万 stage</div></div>
</div>
</div>

<div class="card card-m">
<h3>Maestro 高频问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 低估输出长度和高估，哪个危害更大？</div>
<div class="qa-a"><p><strong>低估远比高估危害大</strong>：(1) KV 缓存方面，低估导致预分配不够，解码到一半 OOM，请求被杀；高估只是暂时多占。(2) SRTF 调度方面，低估剩余时间导致长作业排到队首，造成队头阻塞；高估则长作业排后面，影响较小。所以设计安全裕度 ρ 偏向高估。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CUDA VMM 超配 3 倍不怕 OOM 吗？</div>
<div class="qa-a"><p>三层防护：(1) 122GB 是虚拟地址空间，物理页按需映射，不会同时分配满；(2) 每个 stage 进来先做准入控制，检查剩余物理页是否够预测需求；(3) cuMemMap 返回失败时拒绝该 stage 而非崩溃。多 agent 的 KV 使用弹性大，统计上不会同时达峰，类似内存超卖的思路。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 五种模型状态 vs 四层存储的关系？</div>
<div class="qa-a"><p>四层存储：GPU → CPU → Disk → Remote。五种状态多出一个 <strong>Sleeping</strong>——权重在 CPU，但 GPU 上保留 CUDA Graph 和 JIT 内核缓存（约 0.5GB），重新激活省 5-8 秒。Sleeping 横跨 GPU 和 CPU 两层。设计原因：模型切换频繁时，CUDA Graph 的重建开销可观。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Stage 边界抢占够用吗？为什么不做 token 级？</div>
<div class="qa-a"><p>Token 级抢占需要和解码引擎深度集成，还要做 KV 缓存迁移，工程复杂度极高。Stage 边界抢占只需更新元数据，实测效果已足够：交互排队从 11 秒降到 2 毫秒。超长解码阶段可作为 future work。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 新 agent 角色上线没有历史数据怎么办？</div>
<div class="qa-a"><p>三级回退：(1) per-role 数据不足时回退到全局模型；(2) 结构化特征（工作流位置、工具可用性）本身就有信号；(3) post-execution profiling 增量更新，几轮执行后适应新角色。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 适应度评分 S(N,T) 的权重怎么设？</div>
<div class="qa-a"><p>S(N,T) = A(N,T) − λ·T_ready − μ·C_deg。默认 λ = μ = 1（毫秒量级）。交互式 stage 增大网络延迟权重。用 robust min-max 归一化（5/95 分位数裁剪），防止异常值主导。验证集上选定后跨负载固定。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是"LLM 多智能体工作流"？给一个具体例子。</div>
<div class="qa-a"><p>比如一个旅行助手 Agent：用户说"帮我规划去东京的行程"，系统会依次调用：需求分析 Agent（解析意图）→ 机票搜索 Agent（调工具查航班）→ 酒店推荐 Agent（查酒店）→ 行程整合 Agent（汇总输出）。每个 Agent 背后是一次 LLM 推理调用（称为 stage），一个用户请求可能触发十几次甚至几十次 LLM 调用。这些 stage 之间有 DAG 依赖关系，不同 Agent 可能使用不同模型，输出长度差异巨大——工具调用返回几十 token 的 JSON，用户交互输出几百上千 token。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "解码成本不确定"为什么是个问题？固定按最大长度预留不行吗？</div>
<div class="qa-a"><p>LLM 推理的输出长度变化极大：工具调用输出几十 token（JSON 格式），用户交互输出几百上千 token。输出长度直接决定 KV Cache 大小和 decode 时长。固定按最大长度预留→显存严重浪费（利用率极低）；按平均长度预留→一旦超了就 OOM。核心难点是<strong>必须在请求开始前就预测输出长度来分配资源</strong>，但这个预测天然不准。Maestro 的做法是：预测 + 安全裕度（偏向高估）+ 动态扩容（decode 过程中按需追加物理页）+ 优雅降级（真不够时抢占低优先级 stage），而不是依赖完美的预测。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么分类器和回归器都用 LightGBM（GBDT），而不是用深度学习模型做分类/回归？</div>
<div class="qa-a"><p>注意区分两个角色：<strong>语义特征提取</strong>用的是 MiniLM（本身就是 BERT 系的 DL 模型），但<strong>分类和回归的决策模型</strong>用的是 LightGBM。这样设计的原因：(1) <strong>推理延迟</strong>：语义编码只需要做一次 MiniLM 前向（离线也可预计算），但分类/回归在每次调度决策时都要跑。LightGBM 单次推理 < 1ms，DL 分类器（如 MLP/Transformer）需要 10-100ms，在调度关键路径上不可接受；(2) <strong>数据形态</strong>：LightGBM 的输入是结构化特征 + 已降维的 32 维语义特征，属于典型的表格数据。GBDT 在这种异构特征上通常优于或持平 DL，且不需要大量调参；(3) <strong>可解释性</strong>：LightGBM 直接输出特征重要性，方便分析"agent 角色 vs 工作流位置 vs 语义特征"各自对预测的贡献。论文实验中对比了 MLP（单阶段）、dual-tower Transformer 融合模型等 DL baseline，LightGBM 在 AUC 和延迟上综合最优。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 预测特征具体有哪些？语义特征怎么提取的？</div>
<div class="qa-a"><p>分为两大类：<strong>结构化特征</strong>包括——agent 角色（one-hot 编码，如"搜索 agent"/"推荐 agent"/"整合 agent"）、工作流图中的位置（入度/出度/深度）、当前 stage 在所属工作流中的调用索引（第几个被调用的）、工具可用性（该 agent 可调用的工具数量和类型）。<strong>语义特征</strong>：用 MiniLM（一个小型 transformer 模型，参数量约 33M）对 prompt 文本做编码，得到 384 维向量，再通过 PCA 降到 32 维（保留约 85% 方差）。PCA 降维有两个目的——减少特征维度避免过拟合，以及去掉语义编码中的噪声分量。消融实验显示：去掉语义特征 AUC 从 0.9625 降到约 0.93，证明语义信息确实提供了结构化特征无法捕捉的信号。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 预测器出错了怎么办？如果预测输出 100 token 实际输出了 1000 token 呢？</div>
<div class="qa-a"><p>这是所有预测驱动系统都要面对的核心问题，Maestro 做了三层防护：(1) <strong>偏向高估</strong>——训练时对低估加更大惩罚（非对称 loss），让预测值倾向偏高。低估导致 OOM（请求直接被杀）的代价远大于高估（暂时浪费显存），设计安全裕度 ρ ∈ [0.1, 0.3]；(2) <strong>动态扩容</strong>——KV 内存在 decode 过程中按页增长（类似 PagedAttention 的思路），不是一次性分配完。如果实际输出超过预测，运行时可以追加映射物理页（只要物理显存池还有剩余）；(3) <strong>优雅降级</strong>——如果物理内存真的耗尽（极端情况），选择抢占/暂停优先级最低的 stage 释放空间，而不是让整个服务崩溃。配合这三层防护，预测准确率 R²=0.78 看起来不高，但实际 OOM 率 < 0.1%。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: KV 预留显存降低 67.2%，但这不就是靠 CUDA VMM 超配"骗"出来的吗？实际物理显存并没有减少啊？</div>
<div class="qa-a"><p>这个问题需要分清两个层面：(1) <strong>预留（reservation）≠ 实际使用</strong>。传统方案为每个请求预分配最大 KV 物理空间，即使实际输出很短也占着不放——这是真正的物理显存浪费。CUDA VMM 让虚拟地址远大于物理显存，但物理页按需映射，<strong>真正减少的是物理 HBM 占用</strong>；(2) 67.2% 降低的是<strong>预留的 HBM 物理显存</strong>，不是虚拟地址空间。通过输出长度预测来决定实际映射多少物理页——短请求只映射少量物理页，长请求映射更多，而不是所有人都按最坏情况分配。统计复用的前提是多 Agent 的 KV 峰值不重叠（某个 agent 在输出长文本时，其他 agent 可能正在工具调用或空闲），如果所有请求同时输出长文本确实还会 OOM，但实际 trace 中这种概率极低，且有准入控制兜底。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: EDF 作为 baseline 是不是太弱了？为什么不和更先进的调度方法比？</div>
<div class="qa-a"><p>不只对比了 EDF。Maestro 的实验对比了 EDF、SRTF（无预测版本，纯按已执行时间排序）、FCFS（先到先服务）、Karma（LLM 推理服务最近的调度工作）。关键在于 Maestro 的核心贡献<strong>不是调度算法本身</strong>（SRTF 是经典算法），而是<strong>把预测信号引入 LLM-MAS 场景</strong>并设计了弹性显存机制来利用这些预测。实验设计的目的：EDF → 证明传统实时调度在 LLM-MAS 场景下失效（无法区分长短 stage）；SRTF（无预测）→ 证明纯 SRTF 因为不知道剩余时间只能按已执行时间估计，在双峰分布下偏差大；Maestro → 证明预测信号能显著提升 SRTF 的效果。对比不是为了证明"我的排序算法更好"，而是证明"预测信号有价值"。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不直接用 vLLM/TGI 这些现成的推理框架？它们已经有 PagedAttention、continuous batching 了。</div>
<div class="qa-a"><p>这是不同层面的优化，两者是互补而非替代关系：vLLM/TGI 优化的是<strong>单节点内</strong>推理引擎的 batching 和 KV 管理（PagedAttention 解决内部碎片、continuous batching 提高单模型 GPU 利用率）。Maestro 解决的是<strong>多节点、多模型、多 Agent 工作流</strong>层面的调度问题——一个用户请求涉及十几个 Agent stage、用多个不同模型、分布在多块 GPU 上，需要全局视角决定"哪个 stage 放哪块 GPU、哪个模型该常驻、KV 显存怎么跨请求复用"。Maestro 可以和 vLLM 配合使用：节点内用 vLLM 做推理引擎优化（PagedAttention、continuous batching），节点间用 Maestro 做全局调度和显存管理。事实上我们的原型实现就是基于 vLLM 做的，分级权重缓存和 CUDA VMM 超配是在 vLLM 之上的额外优化。</p></div>
</div>

</div>

<hr class="div">
