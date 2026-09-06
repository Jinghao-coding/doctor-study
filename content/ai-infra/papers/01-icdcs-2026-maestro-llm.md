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
<p>Agent 工作流中的调用成本差异很大：生成工具参数通常较短，分析和总结可能较长。提前估计输出长度，可以同时为请求排序、模型驻留和 KV 预算提供依据。按需分配负责执行时的空间管理，预测则帮助系统提前安排未来需求。</p>

<h4>两阶段流水线</h4>
<pre><code class="language-text">消息、工具描述 → MiniLM → 384 维语义向量
                              ├→ 全局 PCA 32 维
                              │       + 结构化特征
                              │       → 全局 LightGBM 分类器
                              │       → 工具调用概率
                              │                │
                              └→ Agent PCA 32 维
                                      + 结构化特征 + 工具调用概率
                                      → Agent 专属 LightGBM 回归器
                                      → log(1 + 输出长度)
                                      → expm1 → token 数</code></pre>
<p>MiniLM 负责提取语义，LightGBM 负责分类和回归。分类器传递连续概率，让回归器利用工具调用的可能性，而不是先把请求硬切成两个类别。全局分类器共享跨 Agent 的行为规律，专属回归器适配各 Agent 的输出分布。</p>

<h4>服务中的输入特征</h4>
<p>当前服务配置使用输入 token 数、工具数量、思考模式、是否为首个阶段、阶段序号、同一 Agent 的调用次数、上一阶段输出长度，以及 PCA 语义特征。Agent 名称用于选择模型包；会话 ID 用于获取上下文。语义编码处理系统提示、对话和工具名称与描述，长文本通过重叠滑动窗口聚合。</p>
<p>分类器使用全局 PCA，回归器使用 Agent 专属 PCA；线上共用同一份原始语义向量，再分别投影。这让分类和回归保留各自关注的语义方向，同时减少重复编码。</p>

<h4>训练目标与冷启动</h4>
<p>当前服务的分类器学习工具调用标签，回归器对真实输出 token 数做 log1p 变换，采用 alpha=0.5 的分位数回归，预测中位数长度；近期样本获得更高权重。模型包保存模型、PCA 参数和特征顺序，推理按同样的顺序组装输入。</p>
<p>论文方法包含 isotonic 概率校准和冷启动时的共享全局模型。后续服务快照直接使用 predict_proba，缺少 Agent 模型或全局分类器时返回默认 150 token。资源安全余量由预算策略处理，不应把当前中位数回归器称为偏向高估的损失函数。</p>

<h4>两阶段带来的价值</h4>
<p>工具调用概率为长度回归提供显式的行为模式信号，一阶段直接回归则是自然的对照方法。论文报告输出长度 MAE 为 165.43 token、R² 为 0.7774，相比 Magnus 的 MAE 降低 19.2%。消融显示工具意图特征在非 CoT 场景更有帮助；开启 CoT 后，两种模式都可能包含推理文本，因此收益会随工作负载变化。</p>

<h4>预测信号如何驱动下游组件</h4>
<div class="table-scroll">
<table>
<tr><th>组件</th><th>消费方式</th><th>作用</th></tr>
<tr><td>KV 预算</td><td>每 token KV 字节数 ×（输入长度 + 预测输出长度），再加余量</td><td>估计未来需求；执行时结合真实容量按需增长</td></tr>
<tr><td>阶段成本</td><td>prefill profile + 每 token decode profile × 预测输出长度</td><td>估计当前阶段执行时间</td></tr>
<tr><td>工作流排序</td><td>当前阶段成本 + 后续工作流时间估计</td><td>决定任务优先级，减少依赖链上的等待</td></tr>
<tr><td>准入与放置</td><td>结合预测需求、模型状态和可用容量</td><td>选择可承载任务的节点，安排模型驻留与回收</td></tr>
</table>
</div>
<p>论文根据近期低估误差调整资源安全余量；预测服务本身输出概率与长度，实际容量检查由资源管理层完成。节点运行结束后回传真实用量，异步整理数据和更新模型。</p>
<p>实现依据：concerto-runtime@8ee8969 中的 python-predictor；方法与实验结果依据：Maestro 论文 §III-B、§III-D、§IV。</p>
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
<div class="qa-a"><p>固定按最大长度预留简单但保守，实际输出较短时会浪费空间。只按需分配能减少浪费，却不能提前判断哪些请求会长时间占用资源。我用 Agent 输入与上下文预测输出长度，帮助排序、模型驻留和 KV 预算；运行时再按真实用量增长，并在空间紧张时执行准入或回收策略。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么分类器和回归器都用 LightGBM（GBDT），而不是用深度学习模型做分类/回归？</div>
<div class="qa-a"><p>MiniLM 负责提取文本语义，LightGBM 将语义特征与输入长度、工具数量、阶段上下文结合起来做分类与回归。这样的分工适合结构化特征与文本信息混合的场景，也便于给不同 Agent 训练专属模型。工程上可以预加载树模型、复用编码结果并控制线程数量。性能评估要把文本编码与接口排队一起计入，不能只拿树模型的一次调用时间代表整个预测服务。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 预测特征具体有哪些？语义特征怎么提取的？</div>
<div class="qa-a"><p>落到当前服务实现，结构化特征是输入 token 数、工具数量、思考模式、首阶段标记、阶段序号、同一 Agent 的调用次数和上一阶段输出长度。Agent 名称用于选择专属模型。语义特征由 MiniLM 对系统提示、对话和工具描述编码，长文本采用重叠滑动窗口，聚合为 384 维向量，再分别通过全局 PCA 和 Agent PCA 降到 32 维。分类器与回归器各用对应投影，回归器还接收工具调用概率。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 预测器出错了怎么办？如果预测输出 100 token 实际输出了 1000 token 呢？</div>
<div class="qa-a"><p>预测给出初始需求，实际分配持续接受容量约束。KV 随生成按需增长，每次追加前检查空间；不足时暂停准入，或选择合适的回收与恢复策略，再将低估反馈到后续预算校准。当前回归器输出中位数，保守余量属于资源预算策略。这样预测负责改善利用率，运行时负责处理超出预算的情况。</p></div>
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
