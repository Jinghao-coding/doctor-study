## 设计动机与核心方法

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q1：你的预测器到底解决什么问题？</div>
<div class="qa-a"><p>我做的是面向 Agent 工作流的执行成本预测。一次工作流会多次调用模型，有的阶段只生成工具调用参数，有的阶段要长篇推理或汇总，单看模型大小和输入长度，很难判断这次请求到底会占用多久、需要多少显存。我利用 Agent 的输入语义和阶段上下文，先预测工具调用意图，再预测输出长度，把这个长度转成执行时间和 KV 预算，让调度器能够提前安排，而不是等请求执行起来才发现资源紧张。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q2：为什么分两阶段，不直接预测输出长度？</div>
<div class="qa-a"><p>因为工具调用和自由文本生成往往对应两种不同的输出模式。比如同一个研究 Agent，有时只是生成检索参数，有时要写一段分析，输出长度差别很大。我先用分类器估计工具调用概率，再把这个概率作为回归器的输入，让长度模型获得一个更明确的行为信号。</p><p>这里传递的是连续概率，不是先判成 0 或 1 再硬切换模型。一阶段回归也是合理基线；两阶段的价值在于显式利用行为模式，尤其是工具调用与文本输出长度差别较大的场景。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q3：为什么用了 MiniLM，还要用 LightGBM？</div>
<div class="qa-a"><p>它们承担不同任务。MiniLM 提取输入的语义，比如当前是在搜索、分析还是总结；LightGBM 把语义向量和输入长度、工具数量、阶段位置等表格特征结合起来，预测工具调用概率与输出长度。这种组合能利用文本信息，也便于按 Agent 单独训练和更新，部署时还可以预加载模型、控制 CPU 线程和复用编码结果。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q4：具体用了哪些特征？举一个实际例子。</div>
<div class="qa-a"><p>结构化特征包括输入 token 数、工具数量、是否开启思考模式、当前阶段序号、同一个 Agent 已经调用过几次，以及上一阶段输出长度。语义特征来自系统提示、对话内容和工具描述，用 MiniLM 编码后经 PCA 降到 32 维。</p><p>比如同一个 Agent 第一次拿到问题，可能需要先调用搜索工具；第二次已经拿到上游信息，就可能进入长文本分析。角色没变，但调用次数、前序输出和当前语义变了，这些信息能帮助模型区分两次调用的成本。</p></div>
</div>

## 模型训练与工程实现

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q5：为什么每个 Agent 配一个回归器？</div>
<div class="qa-a"><p>不同 Agent 的职责和输出风格相对稳定。检索 Agent、翻译 Agent、总结 Agent 的长度分布不同，使用专属回归器可以减少跨角色混杂。全局分类器共享“是否调用工具”的规律，各 Agent 回归器学习自己的长度模式，因此既有共享信息，也有角色适配。</p><p>实现上按完整 Agent 名称保存模型包，包里包含回归器、特征顺序和 PCA 参数。当前服务在 Agent 数据达到 50 条后才训练专属回归器；缺模型时先使用默认长度，待有足够数据后建立专属模型。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q6：为什么分类器和回归器各有一套 PCA？</div>
<div class="qa-a"><p>分类器要识别所有 Agent 中共同的工具调用模式，回归器要解释某个 Agent 内部的输出长度变化，因此两者关注的语义方向不同。全局 PCA 用全局数据训练，Agent PCA 用该 Agent 的数据训练；线上 MiniLM 只生成一份 384 维向量，再分别投影到两个 32 维空间，既共享编码成本，也保留任务差异。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q7：长 prompt 怎么处理？直接截断吗？</div>
<div class="qa-a"><p>默认使用重叠滑动窗口。每个窗口最多取 510 个内容 token，步长 255，加上特殊 token 后送入 ONNX 编码器批量处理。先对窗口内 token 做 mean pooling，再聚合各窗口向量。这样能覆盖长对话中的多个部分，避免只看开头或结尾；相应代价是 prompt 越长，需要处理的窗口越多，所以编码成本也要单独监控。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q8：输出长度是长尾分布，怎么训练？</div>
<div class="qa-a"><p>当前实现先对真实输出长度做 log1p 变换，再训练 LightGBM 分位数回归器，目标分位数是 0.5。log 变换压缩长短输出之间的尺度差异，中位数目标提供一个典型长度估计。线上再用 expm1 还原成 token 数。训练还对较新的样本赋予更高权重，使模型更关注近期运行模式。</p><p>预测长度和资源余量是两层决策：模型给出典型需求，调度器结合低估误差和剩余显存决定预留多少。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q9：怎么把训练、预测和运行反馈接起来？</div>
<div class="qa-a"><p>执行前调用预测服务，执行后通过 callback 回传真实输出长度和运行数据。节点数据先进入 Redis，工作流结束后交给 Celery 汇总入库；后台根据新增数据量决定是否训练，训练完成后让服务热重载模型。这样请求路径只负责预测，数据整理和训练异步进行，避免训练拖慢用户请求。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q10：预测本身会不会成为瓶颈？你做了哪些工程处理？</div>
<div class="qa-a"><p>会，尤其是长 prompt 和突发并发，不能只看一次树模型推理。我把成本拆成请求排队、文本编码、特征准备、Redis 访问、分类和回归。实现上使用 ONNX Runtime 编码、启动预加载模型、限制原生线程数量，并把同步计算放到受限工作线程中，让 HTTP 事件循环继续处理其他请求。优化时先看哪一段占主导，再决定是复用向量、调整并发，还是减少重复数据访问。</p></div>
</div>

## 调度价值与 KV Cache 追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q11：vLLM 已经按需分配 KV，为什么还需要预测？</div>
<div class="qa-a"><p>按需分配解决的是“已经需要这些 KV，怎样高效存下来”，预测解决的是“这个请求后面还会占多少资源、持续多久”。在多 Agent、多模型场景下，这个未来需求会影响请求排序、模型驻留和节点选择。例如两个请求当前都只占少量 KV，但一个很快结束，另一个会继续生成很长文本，调度策略就不应完全一样。预测提供前瞻信号，分页管理负责高效执行，两者配合才能把资源安排得更好。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q12：预测 100 token，实际生成 1000 token，怎么办？</div>
<div class="qa-a"><p>把预测作为初始预算，运行时继续按真实需求增长。每次追加前检查可用容量，不够时暂停新请求准入，或者选择低代价的回收与重算策略。与此同时，把这次低估反馈给后续预算校准。这里最关键的是把“提高利用率的预测”和“约束实际分配的容量检查”配合起来，这样预测不准时仍然有明确的处理路径。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q13：Cache 命中会改变耗时，你的预测怎样适应？</div>
<div class="qa-a"><p>我会把输出长度预测和运行成本估计分开。输出长度主要由任务语义和生成行为决定；相同输出长度在不同缓存、batch 和资源状态下，耗时可能不同。前缀命中后，时间估计要扣除已复用部分的 prefill 成本，再结合当前排队、decode 速度，以及可能的 KV 传输或重算成本。长度预测器提供需求信号，缓存与负载观测负责把需求换算成当前系统上的成本。</p><p>现有长度模型没有把前缀命中率作为显式特征，因此这类在线状态更适合先接到成本估计层。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q14：当前阶段长度和整个工作流剩余时间有什么关系？</div>
<div class="qa-a"><p>预测器先给当前调用的长度，再用模型的 prefill 和 decode profile 转成当前阶段时间。工作流调度还要考虑后续阶段：根据当前进度和相似历史状态估计后续成本，再与当前阶段合起来。工具调用时间也要单独处理，因为预测工具调用参数的 token 数，并不等于预测外部工具要执行多久。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q15：怎么证明两阶段预测带来了实际价值？</div>
<div class="qa-a"><p>我分两层看：预测层比较长度误差，并分别分析工具调用、非工具调用和思考模式；系统层看这些预测是否改善排序、显存预算和最终完成时间。论文中输出长度预测 MAE 为 165.43 token、R² 为 0.7774，相比 Magnus 的 MAE 降低 19.2%。消融比较直接回归、加入工具调用概率，以及加入语义特征后的变化。然后固定工作负载和运行资源，比较排队、SLO 达成与显存预留，建立从预测到调度收益的联系。</p><p>验证时按时间划分训练和测试，并把同一会话的数据关联起来检查，避免未来信息进入当前请求特征。平均误差之外，还要看长输出和低估尾部。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q16：你这项工作的技术贡献怎么概括？</div>
<div class="qa-a"><p>我把 Agent 工作流中的行为差异转化成了系统可用的资源信号：通过工具调用意图与输出长度的两阶段预测，提前估计阶段成本，再把这些估计接到工作流调度和多模型显存管理中。工程上补齐了预测服务、上下文获取、异步反馈和模型更新，使预测能够进入真实请求链路。这项工作的价值在于把模型行为、资源需求和调度决策连起来。</p></div>
</div>

来源：Maestro 论文 §III–IV，以及 `concerto-runtime@8ee8969` 中 `python-predictor` 的训练、预测与回调实现。实现细节对应后续服务快照；实验数字取自论文。
