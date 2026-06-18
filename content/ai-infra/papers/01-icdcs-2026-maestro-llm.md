## 一句话结论

Maestro 针对 LLM 多智能体工作流推理，利用 agent 上下文做前瞻性输出长度预测，再驱动弹性内存管理（CUDA VMM 超配）和工作流感知 SRTF 调度，在 64×A100 上把 SLO 达成率提升 23.6pp、KV 预留内存降 67.2%。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 论文工作 |
| 章节类型 | 论文项目类 |
| 解决问题 | 围绕 Maestro 与 DeepShare 的问题背景、系统设计、实现细节、实验结果和高频追问建立项目叙事。 |
| 面试抓手 | 按背景、方案、实现、结果、局限回答。 |

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
<p><strong>第一阶段——工具调用分类器</strong>：LightGBM 判断当前 stage 是否会触发工具调用，AUC = 0.9625。特征包括结构化特征（agent 角色、工作流位置、调用索引、工具可用性）和语义特征（MiniLM 编码 prompt，PCA 从 384 维降到 32 维）。</p>
<p><strong>第二阶段——输出长度回归器</strong>：拿到分类器的预测概率 p̂_tool 作为额外特征，预测输出 token 数。MAE = 165 tokens，R² = 0.78。对 token 数做 log 变换处理长尾分布，用 isotonic regression 校准分类器概率。</p>
<p><strong>为什么分两阶段？</strong>输出长度呈双峰分布——工具调用短、用户交互长。单一回归器在双峰上表现差。分类器先识别模式，回归器在给定模式下预测。消融实验：去掉分类器 MAE 从 134 升到 142。</p>
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
</div>

<hr class="div">

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
