<div class="card card-m">
<h3>分布式训练：调度器为什么必须理解并行策略？</h3>
<p>很多调度器只看到"任务需要 8 GPU"。但 8 GPU 的训练任务可能是：</p>
<ul>
<li><strong>数据并行 DP=8</strong>：8 张卡各自训练完整模型，每步 AllReduce 同步梯度。通信量中等，对拓扑不敏感。</li>
<li><strong>张量并行 TP=8</strong>：8 张卡合作训练一个层的不同部分，每层多次 AllGather。通信量极大，必须 NVLink。</li>
<li><strong>3D 并行 TP=4+PP=2</strong>：4 卡做 TP（需要 NVLink），2 个 stage 做 PP（可以跨节点）。拓扑需求混合。</li>
</ul>
<p>如果调度器不理解这些，把 TP=8 的任务调度到跨节点的 8 张 GPU 上，训练速度可能降低 3 倍以上。<strong>调度器必须理解并行策略，才能做出正确的放置决策。</strong></p>
<p><strong>怎么理解</strong>：调度器如果只看到"8 个人"但不理解"8 个人是在各自独立工作（DP）还是必须坐在一起开会（TP）"，就分配不好工位。</p>
</div>

<div class="card card-s">
<h3>并行策略详解</h3>

<h4>1. 数据并行（Data Parallelism, DP）</h4>
<p><strong>核心思想</strong>：每张卡存一份完整模型，不同的数据分片分配给不同卡。每步训练后 AllReduce 同步梯度。</p>
<p><strong>怎么理解</strong>：8 个厨师各自做一桌菜（同样的菜单、不同的食材），做完后汇总经验（梯度同步），下次做得更好。</p>
<p><strong>显存占用</strong>：每张卡 = 完整模型 + 优化器状态 + 激活值。模型太大单卡放不下时，DP 就不可行了。</p>
<p><strong>通信模式</strong>：每步 1 次 AllReduce，通信量 = 模型参数量 × 2（Ring AllReduce）。GPT-3 175B 参数 FP16 约需 700 GB 通信量/步。</p>
<p><strong>拓扑需求</strong>：低。AllReduce 频率低（每步 1 次），InfiniBand 带宽足够。但大规模 DP（>64 卡）时，AllReduce 的延迟会累积。</p>
<p><strong>适用场景</strong>：模型能放进单卡（< 80GB 参数）。小模型训练的标准方案。</p>

<h4>2. 张量并行（Tensor Parallelism, TP）</h4>
<p><strong>核心思想</strong>：把模型每一层的参数矩阵切分到多张卡上，每张卡只算矩阵的一部分，然后 AllGather 拼出完整结果。</p>
<p><strong>怎么理解</strong>：8 个厨师合作做一道大菜——每人负责切一部分食材，然后拼在一起下锅。如果厨师不在同一个厨房（没有 NVLink），来回传递食材太慢。</p>
<p><strong>具体做法</strong>：以线性层 Y = XA 为例，把 A 按列切成 4 份 A₁, A₂, A₃, A₄，4 张卡各自计算 Yᵢ = XAᵢ，然后 AllGather 得到完整 Y = [Y₁, Y₂, Y₃, Y₄]。</p>
<p><strong>通信模式</strong>：每层前向 AllGather + 反向 AllGather/ReduceScatter。96 层模型一步有 384 次集合通信。</p>
<p><strong>拓扑需求</strong>：极高。必须 NVLink 互联。InfiniBand 的带宽差 10-20 倍，会让通信时间远超计算时间。</p>
<p><strong>适用场景</strong>：单层参数量太大，单卡放不下。大模型训练的标配。</p>

<h4>3. 流水线并行（Pipeline Parallelism, PP）</h4>
<p><strong>核心思想</strong>：把模型按层切分成多个 stage，不同 stage 放在不同卡上。数据像流水线一样从 stage 0 → stage 1 → ... → stage N 依次传递。</p>
<p><strong>怎么理解</strong>：工厂流水线——冲压车间把半成品传给焊接车间，焊接车间传给喷漆车间。每个车间只做一部分工序。</p>
<p><strong>Pipeline Bubble 问题</strong>：最简单的实现（Naive PP）中，stage 0 计算时其他 stage 在等，利用率很低。解决方案：<strong>Micro-batching</strong>——把一个 batch 切成多个 micro-batch，依次送入流水线，让不同 stage 同时工作。1F1B 调度策略下，bubble rate ≈ (p-1)/(m+p-1)（p = stage 数，m = micro-batch 数）。</p>
<p><strong>通信模式</strong>：相邻 stage 之间 P2P Send/Recv，传递激活值（前向）和梯度（反向）。</p>
<p><strong>拓扑需求</strong>：低。P2P 通信量小（只传激活值，不传模型参数），InfiniBand 够用。但相邻 stage 的网络跳数越少越好（减少延迟）。</p>
<p><strong>适用场景</strong>：模型层数多，单卡放不下所有层。通常和 TP 组合使用——TP 处理单层太大的问题，PP 处理层数太多的问题。</p>

<h4>4. 专家并行（Expert Parallelism, EP）</h4>
<p><strong>核心思想</strong>：MoE（Mixture of Experts）模型中，不同的专家放在不同的 GPU 上。输入 token 被路由到对应专家所在的 GPU。</p>
<p><strong>通信模式</strong>：All-to-All。每个 token 都可能被路由到任何专家，所以每个 GPU 都需要和所有其他 GPU 通信。</p>
<p><strong>拓扑需求</strong>：极高。All-to-All 需要全网等带宽（bisection bandwidth），比 AllReduce 要求更高。在非全互联拓扑中（如 fat-tree），All-to-All 性能受限于交换机带宽。</p>
<p><strong>适用场景</strong>：MoE 模型（Mixtral、DeepSeek-MoE）。这是 MoE 训练的专属并行策略。</p>

<h4>5. ZeRO 优化</h4>
<p><strong>核心思想</strong>：数据并行的显存优化。训练需要存三类数据：优化器状态（Adam: momentum + variance，每参数 12 字节）、梯度（4 字节/参数）、模型参数（FP16: 2 字节/参数）。ZeRO 把这些数据切分到 N 张卡上。</p>
<p><strong>三个阶段</strong>：</p>
<ul>
<li><strong>ZeRO-1</strong>：只切分优化器状态。每卡只存 1/N 的优化器状态。通信量 = 原始 DP（AllReduce）。节省最多内存的单一优化。</li>
<li><strong>ZeRO-2</strong>：切分优化器状态 + 梯度。ReduceScatter 后每卡只保留自己负责的梯度分片。通信量 = 原始 DP（ReduceScatter + AllGather = AllReduce）。</li>
<li><strong>ZeRO-3</strong>：切分优化器状态 + 梯度 + 参数。前向/反向时按需 AllGather 参数，用完释放。通信量 ≈ 原始 DP × 1.5（额外的前向 AllGather）。</li>
</ul>
<p><strong>怎么理解</strong>：ZeRO-1 像"合租但不共享冰箱"——优化器状态各管各的，其他共享。ZeRO-3 像"全部共享"——连自己的房间都是按需使用，用完就让出来。</p>
<p><strong>显存节省计算</strong>：以 7B 参数模型 + 4 卡为例：</p>
<ul>
<li>无 ZeRO：每卡 = 7B × (12+4+2) = 126 GB → 放不下（A100 只有 80GB）</li>
<li>ZeRO-1：每卡 = 7B × (12/4+4+2) = 7B × 9 = 63 GB → 放得下</li>
<li>ZeRO-3：每卡 = 7B × (12/4+4/4+2/4) = 7B × 4.5 = 31.5 GB → 很充裕</li>
</ul>
</div>

<div class="card card-d">
<h3>并行策略对比与组合</h3>
<table>
<tr><th>策略</th><th>切分维度</th><th>通信模式</th><th>通信频率</th><th>拓扑需求</th><th>显存节省</th><th>适用场景</th></tr>
<tr><td>DP</td><td>数据 batch</td><td>AllReduce</td><td>每步 1 次</td><td>低</td><td>无</td><td>模型放得进单卡</td></tr>
<tr><td>TP</td><td>模型层内矩阵</td><td>AllGather + ReduceScatter</td><td>每层 4 次</td><td>极高（NVLink）</td><td>每层参数量/TP</td><td>单层太大</td></tr>
<tr><td>PP</td><td>模型层间</td><td>P2P Send/Recv</td><td>每 micro-batch 1 次</td><td>低</td><td>层数/PP</td><td>层数太多</td></tr>
<tr><td>EP</td><td>MoE 专家</td><td>All-to-All</td><td>每层 1 次</td><td>极高</td><td>专家数/EP</td><td>MoE 模型</td></tr>
<tr><td>ZeRO-1</td><td>优化器状态</td><td>AllReduce</td><td>每步 1 次</td><td>低</td><td>优化器/N</td><td>DP 的低成本优化</td></tr>
<tr><td>ZeRO-3</td><td>全部状态</td><td>AllGather + ReduceScatter</td><td>每层 2 次</td><td>中</td><td>全部/N</td><td>超大模型</td></tr>
</table>

<h3>3D 并行组合策略</h3>
<p>大模型训练通常组合 DP + TP + PP。核心原则：</p>
<ol>
<li><strong>TP 在节点内</strong>：TP 通信频率最高，必须 NVLink。TP 度 = 节点内 GPU 数（通常 4 或 8）。</li>
<li><strong>PP 跨节点</strong>：PP 通信量小，P2P 可走 InfiniBand。PP 度 = 模型层数 / 单 stage 层数。</li>
<li><strong>DP 在最外层</strong>：DP 通信频率最低，每步一次 AllReduce。DP 度 = 总 GPU / (TP × PP)。</li>
</ol>
<p><strong>配置示例</strong>：</p>
<table>
<tr><th>模型</th><th>GPU 数</th><th>TP</th><th>PP</th><th>DP</th><th>节点数</th></tr>
<tr><td>GPT-3 175B</td><td>64</td><td>8</td><td>4</td><td>2</td><td>8</td></tr>
<tr><td>GPT-4 1.8T</td><td>512</td><td>8</td><td>8</td><td>8</td><td>64</td></tr>
<tr><td>Llama-2 70B</td><td>32</td><td>8</td><td>2</td><td>2</td><td>4</td></tr>
</table>
</div>

<div class="card card-w">
<h3>梯度同步优化</h3>
<p>数据并行（包括 ZeRO）的核心性能瓶颈是梯度同步。几种关键优化：</p>

<h4>1. 通信-计算重叠</h4>
<p><strong>核心思想</strong>：反向传播是逐层计算的。当某一层的梯度算完时，立即启动该层的 AllReduce，不等所有层都算完。</p>
<p><strong>怎么理解</strong>：做饭的同时洗碗——不等所有菜做完再统一洗碗，而是做完一道洗一道。锅的利用率更高。</p>
<p><strong>效果</strong>：在带宽够的情况下，通信时间可以几乎完全隐藏在计算时间内，等效通信开销接近 0。</p>

<h4>2. 梯度累积</h4>
<p><strong>核心思想</strong>：多个 micro-batch 的梯度在本地累积，累积到 N 个后再做一次 AllReduce。通信频率降低 1/N。</p>
<p><strong>怎么理解</strong>：快递攒够一车再发，不一个个寄。</p>
<p><strong>Trade-off</strong>：增大有效 batch size，可能影响模型收敛。</p>

<h4>3. 梯度压缩</h4>
<p><strong>核心思想</strong>：只传 top-k 梯度或量化为低精度（FP8/INT8），减少通信量。</p>
<p><strong>Trade-off</strong>：压缩引入误差，可能影响模型精度。需要仔细调参。</p>

<h4>4. Ring AllReduce</h4>
<p><strong>核心思想</strong>：GPU 排成逻辑环，数据分步传递。每步每个 GPU 只和左右邻居通信，带宽利用均匀。</p>
<p><strong>通信量</strong>：2(N-1)/N × data_size ≈ 2 × data_size（当 N 较大时）。比朴素的 centralized reduce（通信量 = (N-1) × data_size）节省很多。</p>
</div>

<div class="card card-m">
<h3>分布式训练面试问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ZeRO 三个阶段分别做了什么？通信开销怎么变化？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>训练需要存三类数据：优化器状态（12 字节/参数，Adam 的 momentum + variance）、梯度（4 字节/参数）、参数（2 字节/参数，FP16）。</p>
<ul>
<li><strong>ZeRO-1</strong>：切分优化器状态。每卡只存 1/N 的优化器状态。通信量 = DP（不变，AllReduce 梯度）。</li>
<li><strong>ZeRO-2</strong>：切分优化器状态 + 梯度。ReduceScatter 后只保留自己分片的梯度。通信量 = DP（ReduceScatter + AllGather ≈ AllReduce）。</li>
<li><strong>ZeRO-3</strong>：切分全部。前向时 AllGather 参数，反向时 AllGather + ReduceScatter。通信量 ≈ DP × 1.5（额外的前向 AllGather）。</li>
</ul></div>
<div class="qa-section"><div class="qa-section-title">关键洞察</div><p>ZeRO-1 和 ZeRO-2 几乎不增加通信量，但显著节省显存。ZeRO-3 增加约 50% 通信量，但节省最多显存。所以实践中 ZeRO-2 是最常用的"甜点"——显存节省大，通信开销不增。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"ZeRO-2 是性价比最高的选择——和纯 DP 几乎相同的通信量，但显存节省接近 ZeRO-3 的 2/3。除非模型大到 ZeRO-2 还放不下，否则优先选 ZeRO-2。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 3D 并行（DP+TP+PP）的配置怎么选？有什么经验规则？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>三条经验规则：</p>
<ol>
<li><strong>TP = 节点内 GPU 数</strong>（通常 4 或 8）。TP 必须同节点 NVLink，所以 TP 度不能超过单节点 GPU 数。一般直接用满节点内所有 GPU。</li>
<li><strong>PP = 模型层数 / 单 stage 层数</strong>。单 stage 层数取决于单卡能放多少层（考虑显存）。PP 度 = 总层数 / 单卡层数。PP 越大 bubble 越大，尽量少。</li>
<li><strong>DP = 总 GPU / (TP × PP)</strong>。DP 度由剩余 GPU 决定。DP 越大吞吐越高（更多数据并行），但 AllReduce 通信量也随 N 增加。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">调优原则</div><p>(1) <strong>TP 优先用满</strong>：节点内 GPU 闲置就是浪费。(2) <strong>PP 尽量小</strong>：PP 引入 bubble，每个 stage 增加流水线延迟。(3) <strong>DP 做吞吐</strong>：DP 是最便宜的并行——增加 DP 度可以线性增加吞吐（前提是通信-计算重叠好）。(4) <strong>特殊情况</strong>：如果模型小到单卡放得下，用 DP+ZeRO 而不是 3D 并行，简单且高效。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"3D 并行的配置是 TP 决定拓扑约束、PP 决定显存约束、DP 决定吞吐。先满足约束（TP 同节点、PP 不超显存），再优化目标（DP 最大化吞吐）。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pipeline Bubble 怎么优化？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>Pipeline Bubble 的本质是 stage 之间的串行依赖——stage 1 必须等 stage 0 算完才能开始。优化思路：</p>
<ol>
<li><strong>Micro-batching</strong>：把一个 batch 切成 m 个 micro-batch，依次送入流水线。不同 micro-batch 可以在不同 stage 同时执行。Bubble rate 从 1（naive PP）降到 (p-1)/(m+p-1)（1F1B 调度）。</li>
<li><strong>1F1B 调度</strong>：一个前向 + 一个反向交替执行，而不是所有前向做完再所有反向。减少显存占用（不需要存所有 micro-batch 的激活值），同时保持低 bubble。</li>
<li><strong>Interleaved 1F1B</strong>：每个 device 负责多个不连续的 stage（如 device 0 负责 stage 0 和 stage 4），让流水线更"紧凑"。Bubble rate 从 (p-1)/m 降到 (p-1)/(m × v)（v = 每 device 的 stage 数）。</li>
<li><strong>增大 micro-batch 数</strong>：m 越大 bubble rate 越小。但 m 受总 batch size 限制——m × micro_batch_size = global_batch_size。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"Pipeline Bubble 的优化核心是'让更多 stage 同时工作'。Micro-batching 让不同 micro-batch 占据不同 stage，1F1B 减少显存占用，Interleaved 让流水线更紧凑。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 调度器怎么感知并行策略？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>调度器需要知道任务的并行策略才能做正确的放置。三种方式：</p>
<ol>
<li><strong>用户声明</strong>：在 Pod/Job 的 annotation 或 CRD 字段中声明并行策略。例如 Volcano Job 的 <code>task.spec</code> 可以区分 master 和 worker，annotation <code>scheduling.volcano.sh/tp-size: "8"</code> 声明 TP 度。调度器据此做拓扑感知放置。</li>
<li><strong>框架推理</strong>：从训练框架的配置（如 PyTorchJob 的 <code>torchrun</code> 参数 <code>--nproc_per_node=8 --nnodes=4</code>）推断 TP=8, PP=4。需要训练框架和调度器的集成。</li>
<li><strong>自动发现</strong>：调度器观察 Pod 的通信模式（哪些 Pod 之间有大量 NCCL 流量），推断并行策略。这是研究前沿，尚无成熟方案。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">实践建议</div><p>短期用用户声明（最简单），中期做框架集成（更可靠），长期探索自动发现（最智能）。关键是不让调度器猜——显式声明比隐式推断可靠。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"调度器感知并行策略的关键是'不让调度器猜'——用户声明最可靠，框架集成更自动化，自动发现是远景。显式优于隐式。"</p></div>
</div>
</div>
</div>
