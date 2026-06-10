<div class="card card-w">
<h3>GPU 面试学习地图：AI Infra 视角到底要会什么</h3>
<p>AI Infra 面试里的 GPU 不是只问“CUDA Core 是什么”或“显存多大”。面试官更关心你能不能把一张卡、一个节点、一组节点、一个训练/推理任务串起来理解：计算单元在哪里，数据从哪里来，瓶颈卡在哪里，为什么 GPU 利用率高但训练仍然慢，为什么显存没满却会 OOM，为什么多机训练会 NCCL timeout，以及平台层如何调度、隔离和排障。</p>
<table>
<tr><th>模块</th><th>学习重点</th><th>面试官想确认什么</th><th>答题抓手</th></tr>
<tr><td>GPU 架构</td><td>SM、CUDA Core、Tensor Core、warp、register、shared memory、L2、HBM</td><td>你是否理解 GPU 为什么适合大规模并行计算</td><td>从“线程并行 + 高带宽显存 + 专用矩阵单元”讲起</td></tr>
<tr><td>性能指标</td><td>GPU Util、SM Active、Occupancy、Tensor Core Util、HBM Bandwidth、TFLOPS、MFU</td><td>你是否能判断瓶颈是算力、显存带宽、通信还是调度空洞</td><td>先分层：算子层、单卡层、节点层、集群层</td></tr>
<tr><td>显存与 OOM</td><td>参数、梯度、optimizer state、activation、temporary buffer、通信 buffer、KV cache</td><td>你是否知道显存由哪些部分组成，而不是只会说 batch size 太大</td><td>训练看 activation/optimizer，推理看 KV cache</td></tr>
<tr><td>通信拓扑</td><td>PCIe、NVLink、NVSwitch、InfiniBand、RoCE、GPUDirect RDMA、NCCL</td><td>你是否理解多卡/多机训练为什么会慢</td><td>先区分卡内、机内、机间，再讲 AllReduce 路径</td></tr>
<tr><td>分布式训练</td><td>DP、TP、PP、ZeRO、EP、MoE、rank、world size</td><td>你是否能解释并行策略对显存、通信和吞吐的影响</td><td>用“切数据、切模型、切层、切状态”组织回答</td></tr>
<tr><td>GPU 调度</td><td>Device Plugin、DRA、MIG、MPS、time-slicing、Gang Scheduling、拓扑感知</td><td>你是否能把 Kubernetes 与 GPU 资源管理结合起来</td><td>默认调度器只看资源数量，高级调度要看拓扑、队列和任务整体性</td></tr>
<tr><td>监控排障</td><td>DCGM、nvidia-smi、Xid、ECC、温度、功耗、NVLink error、NCCL timeout</td><td>你是否能定位线上 GPU 任务慢、挂、掉卡的原因</td><td>先判断单卡、节点、网络、框架、调度哪一层异常</td></tr>
<tr><td>推理服务</td><td>Prefill、Decode、KV cache、continuous batching、PagedAttention、量化、TTFT、TPOT</td><td>你是否知道训练和推理的 GPU 瓶颈不同</td><td>Prefill 偏算力，Decode 常受 KV cache 和访存影响</td></tr>
</table>
<div class="qa-summary">一句话：GPU 面试不是背名词，而是要能围绕“算力、显存、通信、调度、可观测性”解释一个 AI 任务为什么快、为什么慢、为什么失败。</div>
</div>

<div class="card card-w">
<h3>GPU 架构：不要只背 SM，要理解一条数据怎么被算完</h3>
<p>学习 GPU 架构时，可以先把 GPU 想成一个为大规模并行计算设计的处理器。CPU 擅长复杂控制流、低延迟和少量强核；GPU 擅长把大量相似计算拆成海量线程并行执行。深度学习中的矩阵乘、卷积、attention 都有大量重复计算，因此很适合 GPU。</p>
<table>
<tr><th>概念</th><th>它是什么</th><th>学习者怎么理解</th><th>面试答题要点</th></tr>
<tr><td>SM</td><td>Streaming Multiprocessor，GPU 的核心执行单元</td><td>可以把 SM 理解成 GPU 里的一个“计算工厂”，里面有执行线程、调度 warp、访问寄存器和 shared memory 的能力</td><td>GPU 并行能力主要来自很多 SM 同时工作</td></tr>
<tr><td>CUDA Core</td><td>执行 FP32/INT 等通用计算的计算单元</td><td>类似工厂里的普通工位，适合做标量/向量计算</td><td>不要只用 CUDA Core 数量衡量深度学习性能，还要看 Tensor Core、显存带宽和软件栈</td></tr>
<tr><td>Tensor Core</td><td>面向矩阵乘加的专用计算单元</td><td>深度学习训练/推理里大量 GEMM 可以用 Tensor Core 加速</td><td>FP16/BF16/TF32/FP8 等低精度训练与推理性能很依赖 Tensor Core</td></tr>
<tr><td>Warp</td><td>GPU 调度执行的线程组，NVIDIA 常见为 32 个线程</td><td>GPU 不是一个线程一个线程随意执行，而是一组线程一起执行</td><td>分支发散会让同一个 warp 内不同路径串行化，降低效率</td></tr>
<tr><td>Register</td><td>每个线程私有的高速存储</td><td>最快，但数量有限；单个线程用太多 register 会影响并发度</td><td>kernel 性能常受 register pressure 影响</td></tr>
<tr><td>Shared Memory</td><td>同一个 thread block 内线程共享的片上存储</td><td>比 HBM 快，适合做数据复用和 tile</td><td>高性能 GEMM/attention kernel 通常会精心设计 shared memory 访问</td></tr>
<tr><td>L2 Cache</td><td>GPU 片上缓存</td><td>位于 SM 和 HBM 之间，缓解重复访存</td><td>cache 命中率会影响有效带宽和算子性能</td></tr>
<tr><td>HBM</td><td>High Bandwidth Memory，高带宽显存</td><td>模型参数、activation、KV cache 等主要放在这里</td><td>很多算子不是算力不够，而是 HBM 读写跟不上</td></tr>
<tr><td>NVLink / NVSwitch</td><td>GPU 间高速互联</td><td>让多 GPU 之间传输数据比走普通 PCIe 更快</td><td>多卡训练性能很依赖机内 GPU 拓扑</td></tr>
</table>
<p>NVIDIA Hopper 架构文档中提到，H100 这类 GPU 通过 Tensor Core、HBM、高速互联等能力服务大规模 AI 和 HPC 负载；学习时不要孤立看某一个部件，而要看它们如何共同决定训练和推理性能[[NVIDIA Hopper Architecture In-Depth](https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth)]。</p>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：GPU 为什么比 CPU 更适合深度学习？</strong></p><p>答题时不要只说“GPU 核多”。更好的回答是：深度学习的核心计算主要是矩阵乘、卷积、attention 等高度并行、计算模式规则的任务。GPU 有大量 SM 和线程并行能力，配合高带宽 HBM 与 Tensor Core，可以把大量相同计算批量执行。CPU 更适合复杂控制流、系统调度和低延迟任务；GPU 更适合吞吐优先的大规模数据并行计算。</p></div>
<div class="qa-section"><div class="qa-section-title">答题要点</div><ul><li>先比较 CPU 与 GPU 的设计目标：低延迟 vs 高吞吐。</li><li>再说明深度学习计算模式：大量矩阵运算，可并行，可向量化。</li><li>最后补充限制：GPU 快不代表所有任务都快，数据搬运、访存、通信和 kernel launch 都可能成为瓶颈。</li></ul></div>
</div>

<div class="card card-w">
<h3>GPU 性能指标：先判断瓶颈在哪一层</h3>
<p>GPU 性能指标最容易被问，也最容易答得空。很多同学只会说 GPU Utilization 高低，但 AI Infra 面试中，面试官更想知道你能不能用一组指标判断任务到底卡在算力、显存带宽、通信、输入 pipeline，还是调度等待。</p>
<table>
<tr><th>指标</th><th>含义</th><th>常见误区</th><th>排查思路</th></tr>
<tr><td>GPU Utilization</td><td>一段时间内 GPU 是否有 kernel 在运行</td><td>Util 高不代表算力打满；Util 低也不一定是 GPU 问题</td><td>结合 SM Active、Tensor Core、memory bandwidth 看</td></tr>
<tr><td>SM Active</td><td>SM 处于活跃执行状态的比例</td><td>只看 GPU Util 会掩盖 SM 实际忙不忙</td><td>SM Active 低通常说明 kernel 不够、调度空洞、输入不足或通信等待</td></tr>
<tr><td>Occupancy</td><td>SM 上活跃 warp 数相对理论最大值的比例</td><td>Occupancy 高不一定性能高</td><td>低 occupancy 可能来自 register/shared memory 使用过多或 block 配置不合理</td></tr>
<tr><td>Tensor Core Util</td><td>Tensor Core 使用程度</td><td>模型跑在 GPU 上不代表用了 Tensor Core</td><td>检查精度、算子实现、shape 是否适合 Tensor Core</td></tr>
<tr><td>HBM Bandwidth</td><td>显存读写带宽使用程度</td><td>算子慢不一定是算力不够，也可能是访存受限</td><td>带宽接近上限但算力不高，通常是 memory-bound</td></tr>
<tr><td>TFLOPS</td><td>每秒浮点运算次数</td><td>理论峰值不等于实际可达</td><td>实际 TFLOPS 要结合精度、算子、batch、并行策略</td></tr>
<tr><td>MFU</td><td>Model FLOPs Utilization，模型实际利用理论算力的比例</td><td>只适合在明确模型 FLOPs 估算方式时比较</td><td>大模型训练常用 MFU 评价整体训练效率</td></tr>
<tr><td>通信耗时</td><td>AllReduce、AllGather、ReduceScatter、P2P 等通信占比</td><td>单卡指标正常，多卡仍可能慢</td><td>看 NCCL 日志、拓扑、网络、bucket、并行策略</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">排查顺序</div><ol><li><strong>先看任务有没有持续喂饱 GPU</strong>：GPU Util、SM Active 是否周期性掉到很低。</li><li><strong>再看算子是否真正用上高性能路径</strong>：Tensor Core、精度、shape、kernel 类型。</li><li><strong>再看是 compute-bound 还是 memory-bound</strong>：算力利用率和 HBM 带宽谁先接近瓶颈。</li><li><strong>多卡任务继续看通信</strong>：NCCL collective 是否占比过高，是否跨 NUMA、跨 PCIe switch、跨节点。</li><li><strong>最后看平台层</strong>：是否 gang scheduling 等待、数据加载慢、共享 GPU 抢占、节点健康异常。</li></ol></div>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：GPU Utilization 90%，是不是说明 GPU 已经跑满了？</strong></p><p>不能这么判断。GPU Utilization 通常表示采样周期内 GPU 是否在执行任务，不代表 SM、Tensor Core、HBM 都被充分利用。一个小 kernel 高频运行也可能让 GPU Util 看起来很高，但 SM Active、Tensor Core Util 或实际 TFLOPS 并不高。更好的判断方式是结合 SM Active、Tensor Core Util、HBM bandwidth、kernel trace、端到端 step time 和通信占比。</p></div>
<div class="qa-summary">答题口诀：Util 看“有没有活”，SM Active 看“计算单元忙不忙”，Tensor Core 看“矩阵单元用没用上”，HBM bandwidth 看“是不是访存卡住”，MFU 看“模型整体效率”。</div>
</div>

<div class="card card-w">
<h3>Roofline：用一张图理解算力瓶颈和带宽瓶颈</h3>
<p>Roofline 模型是 GPU 性能分析里很有用的思维工具。它不要求你一开始就记复杂公式，只要先理解一个核心问题：一个算子慢，到底是因为计算次数太多、算力不够，还是因为每做一点计算都要频繁读写显存，导致显存带宽不够。</p>
<table>
<tr><th>概念</th><th>含义</th><th>如何理解</th></tr>
<tr><td>算术强度</td><td>Arithmetic Intensity，FLOPs / Bytes</td><td>每读写 1 byte 数据能做多少计算</td></tr>
<tr><td>Compute-bound</td><td>受算力上限限制</td><td>算术强度高，数据复用好，瓶颈在计算单元</td></tr>
<tr><td>Memory-bound</td><td>受显存带宽限制</td><td>算术强度低，读写多、计算少，瓶颈在 HBM</td></tr>
<tr><td>优化方向</td><td>针对瓶颈选手段</td><td>compute-bound 优化计算路径；memory-bound 优化访存、融合、缓存复用</td></tr>
</table>
<p>比如大矩阵乘通常算术强度较高，更容易接近 Tensor Core 算力上限；而 elementwise、embedding lookup、某些归约或小 batch decode 则可能更受访存和调度开销影响。</p>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：一个 GPU 算子性能不好，你会怎么分析？</strong></p><p>可以回答：我会先看这个算子是 compute-bound 还是 memory-bound。具体会看实际 TFLOPS、Tensor Core 使用率、HBM 带宽、kernel 执行时间和输入 shape。如果 HBM 带宽很高但算力利用不高，可能是访存瓶颈，要考虑算子融合、减少中间 tensor、改善 memory coalescing、提高数据复用；如果 Tensor Core 没用上，要检查数据类型、layout、shape 和 kernel 实现。</p></div>
</div>

<div class="card card-w">
<h3>显存与 OOM：训练和推理要分开讲</h3>
<p>显存问题是 GPU 面试高频题。学习时要先建立一个完整账本：显存不是只有模型参数，还包括梯度、优化器状态、activation、临时 workspace、通信 buffer、CUDA context、框架缓存，以及推理阶段非常关键的 KV cache。</p>
<table>
<tr><th>显存组成</th><th>训练阶段</th><th>推理阶段</th><th>优化手段</th></tr>
<tr><td>参数</td><td>模型权重，所有训练都需要</td><td>模型权重，常驻显存</td><td>量化、tensor parallel、offload</td></tr>
<tr><td>梯度</td><td>反向传播需要保存</td><td>通常不需要</td><td>ZeRO、gradient accumulation、释放无用梯度</td></tr>
<tr><td>Optimizer State</td><td>Adam 常见有 m/v 等状态，可能比参数更占显存</td><td>不需要</td><td>ZeRO、8-bit optimizer、offload</td></tr>
<tr><td>Activation</td><td>前向中间结果，反向需要</td><td>prefill/decode 中也有中间 tensor</td><td>activation checkpointing、sequence parallel、减小 batch/seq</td></tr>
<tr><td>Temporary Buffer</td><td>cuDNN/cuBLAS/NCCL/框架 workspace</td><td>attention、采样、图优化也会产生临时 buffer</td><td>选择算法、限制 workspace、算子融合</td></tr>
<tr><td>Communication Buffer</td><td>AllReduce/AllGather/ReduceScatter 需要</td><td>多卡推理也需要</td><td>调 bucket、overlap、并行策略优化</td></tr>
<tr><td>KV Cache</td><td>训练一般不是核心瓶颈</td><td>LLM 推理的核心显存大户</td><td>PagedAttention、continuous batching、限制 max tokens、量化 KV cache</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">PyTorch 缓存分配器</div><p>很多人看到 <code>nvidia-smi</code> 里显存占用很高，就以为都是真实 tensor。实际上 PyTorch 等框架常使用 caching allocator：释放 tensor 后，显存可能先留在框架缓存中，方便后续复用，不一定立刻还给 GPU driver。因此排查 OOM 要区分 allocated、reserved/cache、fragmentation 和真正不可释放的 tensor。</p></div>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：训练 OOM 你会怎么处理？</strong></p><p>我会先判断 OOM 发生在初始化、前向、反向、optimizer step 还是通信阶段。然后拆显存账本：参数、梯度、optimizer state、activation、临时 buffer 和通信 buffer。常见手段包括减小 micro batch、使用 gradient accumulation 保持 global batch、开启 activation checkpointing、混合精度、ZeRO/FSDP 切分参数/梯度/优化器状态、offload 到 CPU/NVMe、减少 sequence length，或者检查是否有 tensor 被 Python 引用导致无法释放。</p></div>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：推理 OOM 和训练 OOM 最大区别是什么？</strong></p><p>推理通常没有梯度和 optimizer state，但 LLM 推理会有 KV cache。KV cache 随 batch size、sequence length、layer 数、hidden size、并发请求数增长，decode 阶段会持续追加。训练 OOM 更常从 activation、optimizer state、并行切分角度分析；推理 OOM 更常从 KV cache 管理、max context、并发度、continuous batching、PagedAttention 和量化角度分析。vLLM 文档明确将 PagedAttention、continuous batching、量化和 tensor parallelism 作为其高吞吐服务能力的重要组成部分[[Welcome to vLLM! — vLLM](https://docs.vllm.ai/en/v0.4.2/)]。</p></div>
</div>

<div class="card card-w">
<h3>通信与拓扑：多卡训练慢，很多时候不是单卡问题</h3>
<p>单卡训练只要关注一张 GPU 内部的算力和显存；多卡训练还要关注 GPU 之间、节点之间怎么通信。AI Infra 面试中，如果能把 PCIe、NVLink、NVSwitch、InfiniBand/RoCE、GPUDirect RDMA 和 NCCL 放到同一张链路图里讲清楚，会明显加分。</p>
<table>
<tr><th>层级</th><th>常见技术</th><th>它解决什么问题</th><th>面试要点</th></tr>
<tr><td>GPU 内部</td><td>SM、L2、HBM</td><td>单卡计算和显存访问</td><td>判断 compute-bound / memory-bound</td></tr>
<tr><td>同机 GPU 间</td><td>PCIe、NVLink、NVSwitch</td><td>机内多卡参数、梯度、activation 交换</td><td>NVLink/NVSwitch 通常比 PCIe 更适合高频大流量通信</td></tr>
<tr><td>跨机通信</td><td>InfiniBand、RoCE、以太网</td><td>多节点之间交换梯度或模型分片</td><td>网络带宽、延迟、拥塞和 RDMA 配置会影响训练效率</td></tr>
<tr><td>GPU 与网卡</td><td>GPUDirect RDMA</td><td>让网卡直接访问 GPU memory，减少 CPU 中转</td><td>跨节点训练性能常依赖 GPUDirect RDMA 是否生效</td></tr>
<tr><td>通信库</td><td>NCCL</td><td>实现 AllReduce、AllGather、ReduceScatter、Broadcast 等 collective</td><td>NCCL 会根据拓扑选择 ring/tree 等算法</td></tr>
</table>
<p>GPUDirect 的核心价值是让网络适配器或存储设备直接读写 GPU memory，从而减少不必要的数据拷贝、CPU 开销和延迟[[GPUDirect | NVIDIA Developer](https://developer.nvidia.com/gpudirect)]。</p>
<div class="qa-section"><div class="qa-section-title">AllReduce 怎么讲</div><p>Data Parallel 中，每张卡各自计算一份梯度，然后需要把所有卡的梯度聚合并同步回每张卡。AllReduce 做的就是“先 reduce 再 broadcast”的 collective 操作。Ring AllReduce 会把数据切块，在环上分阶段传递，带宽利用较好；Tree AllReduce 更关注降低延迟。真实系统中 NCCL 会结合拓扑和数据规模选择合适路径。</p></div>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：多机多卡训练 NCCL timeout，你怎么排查？</strong></p><p>我会分层排查：第一，看是否某个 rank 先 OOM、进程退出或卡在 dataloader，导致其他 rank 等 collective；第二，看 NCCL 日志，确认卡在哪个 collective、哪些 rank；第三，看网络和拓扑，检查 IB/RoCE、GPUDirect RDMA、网卡状态、路由、MTU、丢包、拥塞；第四，看节点 GPU 健康，是否有 Xid、ECC、掉卡、NVLink error；第五，看调度层，是否跨了不合适的 NUMA、PCIe switch 或网络拓扑，或者混用了性能差异很大的节点。</p></div>
</div>

<div class="card card-w">
<h3>分布式训练：用“切什么”理解并行策略</h3>
<p>分布式训练的并行策略很多，但学习时不要先陷入名词。最简单的分类方式是：Data Parallel 切数据，Tensor Parallel 切张量/算子，Pipeline Parallel 切层，ZeRO/FSDP 切训练状态，Expert Parallel 切专家。</p>
<table>
<tr><th>并行方式</th><th>切什么</th><th>优点</th><th>代价/瓶颈</th><th>面试回答关键词</th></tr>
<tr><td>Data Parallel</td><td>不同 GPU 处理不同 batch</td><td>简单，扩展常见</td><td>梯度 AllReduce 通信</td><td>global batch、gradient sync、overlap</td></tr>
<tr><td>Tensor Parallel</td><td>把矩阵或 attention head 切到多卡</td><td>单层大算子可跨卡</td><td>层内 AllReduce/AllGather 高频</td><td>适合单层参数太大或单卡放不下</td></tr>
<tr><td>Pipeline Parallel</td><td>按 layer/stage 切模型</td><td>降低单卡模型显存</td><td>pipeline bubble、调度复杂</td><td>micro batch、bubble、1F1B</td></tr>
<tr><td>ZeRO / FSDP</td><td>切参数、梯度、optimizer state</td><td>显著降低冗余显存</td><td>AllGather/ReduceScatter 增多</td><td>stage 1/2/3、reshard、offload</td></tr>
<tr><td>Expert Parallel</td><td>MoE 中不同 expert 放不同设备</td><td>扩大模型容量</td><td>token dispatch、负载不均</td><td>router、all-to-all、capacity factor</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：为什么大模型训练要混合并行？</strong></p><p>因为单一并行方式通常只能解决一类瓶颈。Data Parallel 简单，但每张卡仍要放完整模型和 optimizer state；Tensor Parallel 能拆大算子，但层内通信频繁；Pipeline Parallel 能拆层，但有 bubble；ZeRO/FSDP 能降低训练状态冗余，但会增加参数聚合通信。大模型训练通常同时受显存容量、算力、机内通信和跨机网络限制，因此需要把 DP、TP、PP、ZeRO/FSDP 组合起来，在显存、通信和吞吐之间折中。</p></div>
</div>

<div class="card card-w">
<h3>GPU 调度与资源管理：Kubernetes 默认能力为什么不够</h3>
<p>在 Kubernetes 里申请 GPU，最基础的方式是通过 NVIDIA device plugin 把 GPU 暴露成 extended resource，例如 <code>nvidia.com/gpu: 1</code>。但 AI Infra 平台不能只满足“分到一张卡”，还要考虑队列公平性、gang scheduling、拓扑、MIG、共享、抢占、quota、节点健康和多租户隔离。</p>
<table>
<tr><th>能力</th><th>解决的问题</th><th>为什么默认 K8s 不够</th><th>平台侧常见方案</th></tr>
<tr><td>Device Plugin</td><td>把 GPU 注册给 kubelet，并在容器启动时注入设备</td><td>主要解决“有几张卡、分哪张卡”</td><td>NVIDIA device plugin、GPU Operator</td></tr>
<tr><td>DRA</td><td>Dynamic Resource Allocation，支持更灵活的资源声明、选择和分配</td><td>extended resource 表达能力有限</td><td>ResourceClaim、ResourceClass、结构化参数</td></tr>
<tr><td>Gang Scheduling</td><td>分布式训练要么所有 worker 一起启动，要么都不启动</td><td>默认调度可能先启动部分 Pod，剩余 Pod 等待，造成资源浪费</td><td>Volcano、scheduler plugin、PodGroup</td></tr>
<tr><td>拓扑感知</td><td>选择同节点、同 NVSwitch、同 NUMA、同机架或同网络域资源</td><td>默认资源计数不知道 GPU 互联质量</td><td>topology label、scheduler extender/plugin、资源画像</td></tr>
<tr><td>MIG</td><td>把一张支持 MIG 的 GPU 切成多个隔离实例</td><td>适合小模型推理或开发任务，但切分规格需要管理</td><td>MIG profile、节点池隔离、配额</td></tr>
<tr><td>MPS/time-slicing</td><td>多个进程共享一张 GPU</td><td>隔离性、性能抖动和故障影响更复杂</td><td>按场景开启，配合监控和限额</td></tr>
<tr><td>抢占与配额</td><td>保障高优任务与团队公平</td><td>GPU 贵，长任务多，排队不可避免</td><td>priority、quota、preemption、queue</td></tr>
</table>
<p>Kubernetes DRA 的目标是让资源分配比传统 extended resource 更灵活，可通过 ResourceClaim 等对象表达动态资源需求[[Dynamic Resource Allocation | Kubernetes](https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/)]。NVIDIA MIG 则允许把支持的 GPU 分区为多个 GPU instance，每个实例拥有专用的计算和内存资源[[MIG User Guide — NVIDIA Multi-Instance GPU User Guide](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/index.html)]。</p>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：为什么 GPU 训练任务需要 Gang Scheduling？</strong></p><p>分布式训练通常要求多个 worker/rank 同时参与。如果只启动了一部分 Pod，它们可能会一直等待其他 rank，既不能推进训练，又占着 GPU。Gang Scheduling 通过 PodGroup 或类似机制确保资源满足最小集合后再整体启动，避免部分启动造成资源浪费。回答时可以补充：Gang Scheduling 解决“整体性”，队列调度解决“公平性”，拓扑调度解决“性能”，Device Plugin/DRA 解决“资源表达与分配”。</p></div>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：MIG、MPS、time-slicing 有什么区别？</strong></p><p>MIG 是硬件级分区，把一张 GPU 切成多个相对隔离的实例，每个实例有独立的部分计算和显存资源，隔离性更好；MPS 是让多个 CUDA 进程更高效共享 GPU 执行资源，适合提升小 kernel 并发，但隔离不是硬切；time-slicing 是时间片共享，多个任务轮流用 GPU，简单但性能抖动更明显。平台设计时要根据训练、推理、开发测试等场景选择，不应混为一谈。</p></div>
</div>

<div class="card card-w">
<h3>GPU 监控与故障排查：先分层，再定位</h3>
<p>GPU 线上问题通常表现为任务慢、任务挂、OOM、NCCL timeout、GPU 掉卡、节点不可用、推理延迟抖动。排障时不要一上来就重启机器，应该先分层：任务代码层、框架层、GPU 硬件层、节点系统层、网络通信层、调度平台层。</p>
<table>
<tr><th>现象</th><th>可能原因</th><th>关键指标/日志</th><th>处理思路</th></tr>
<tr><td>GPU 利用率低</td><td>dataloader 慢、batch 太小、CPU 预处理慢、通信等待、调度空洞</td><td>GPU Util、SM Active、CPU、IO、step trace</td><td>定位空洞来自输入、计算还是通信</td></tr>
<tr><td>显存 OOM</td><td>batch/seq 太大、activation 多、KV cache 爆、内存碎片、泄漏</td><td>allocated/reserved、nvidia-smi、框架日志</td><td>拆显存账本，定位发生阶段</td></tr>
<tr><td>NCCL timeout</td><td>rank 失败、网络问题、拓扑差、某节点慢、collective 不一致</td><td>NCCL_DEBUG、网络计数器、Xid、rank 日志</td><td>先找第一个异常 rank，再看网络和 GPU 健康</td></tr>
<tr><td>GPU 掉卡</td><td>硬件故障、driver 问题、PCIe/NVLink 错误、功耗/温度异常</td><td>Xid、dmesg、DCGM、nvidia-smi</td><td>隔离节点、重置 GPU、升级驱动、硬件维修</td></tr>
<tr><td>推理延迟抖动</td><td>请求长度差异、batching 策略、KV cache eviction、共享 GPU 干扰</td><td>TTFT、TPOT、queue time、batch size、cache usage</td><td>拆 prefill/decode/排队/调度时间</td></tr>
<tr><td>训练吞吐下降</td><td>降频、温度、功耗限制、慢节点、网络拥塞</td><td>power、temperature、clocks、step time 分布</td><td>比较节点间指标，找 straggler</td></tr>
</table>
<p>DCGM 提供 GPU 监控、诊断和管理能力，常用于数据中心 GPU 健康检查、指标采集与故障诊断[[Feature Overview — NVIDIA DCGM Documentation](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/feature-overview.html)]。</p>
<div class="qa-section"><div class="qa-section-title">常用命令</div><pre><code class="language-bash"># 查看 GPU 基础状态
nvidia-smi

# 查看某些实时指标
nvidia-smi dmon

# 查看拓扑关系
nvidia-smi topo -m

# 查看系统内核日志中的 NVIDIA/Xid 错误
dmesg | grep -i -E "nvrm|xid|nvidia"

# NCCL 排障常用环境变量
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=INIT,GRAPH,COLL,NET</code></pre></div>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：一个训练任务突然变慢，你怎么定位？</strong></p><p>我会先确认是所有 step 都慢，还是周期性抖动；是所有 rank 慢，还是某个 rank/节点拖慢。然后看 GPU 指标：SM Active、Tensor Core、HBM、功耗、温度、时钟；再看通信占比和 NCCL 日志；再看数据输入是否阻塞；最后看调度和节点层是否发生共享、抢占、降频或网络拥塞。核心是用时间线把 step 拆成 data、forward、backward、optimizer、communication，而不是只看一个 GPU Util。</p></div>
</div>

<div class="card card-w">
<h3>LLM 推理中的 GPU 问题：Prefill、Decode、KV Cache</h3>
<p>训练和推理的 GPU 关注点不同。训练更看吞吐、显存切分、反向传播和通信；LLM 推理更看请求排队、首 token 延迟、decode 吞吐、KV cache 管理和动态 batch。</p>
<table>
<tr><th>阶段/指标</th><th>含义</th><th>GPU 瓶颈</th><th>优化方向</th></tr>
<tr><td>Prefill</td><td>处理 prompt，生成第一步所需 KV cache</td><td>prompt 长时计算量大，attention/GEMM 重</td><td>batching、Tensor Core、prefix cache、chunked prefill</td></tr>
<tr><td>Decode</td><td>逐 token 生成输出</td><td>每步计算较小但要频繁读 KV cache，容易 memory-bound</td><td>continuous batching、PagedAttention、KV cache 优化</td></tr>
<tr><td>TTFT</td><td>Time To First Token</td><td>受排队、prefill 和调度影响</td><td>控制队列、prefill 分块、优先级</td></tr>
<tr><td>TPOT</td><td>Time Per Output Token</td><td>受 decode kernel、KV cache、batch 策略影响</td><td>提高 decode batch、减少访存、量化</td></tr>
<tr><td>QPS/吞吐</td><td>单位时间完成请求或 token 数</td><td>受并发、batch、显存和延迟 SLA 共同约束</td><td>动态 batching、并行、量化、缓存复用</td></tr>
<tr><td>KV Cache</td><td>保存历史 token 的 key/value</td><td>随并发和上下文长度增长，容易吃满显存</td><td>PagedAttention、cache block 管理、限制 max tokens</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">面试官常问</div><p><strong>Q：为什么 LLM 推理 decode 阶段 GPU 利用率可能不高？</strong></p><p>Decode 是逐 token 生成，每一步要读取历史 KV cache，但单步计算量相对 prefill 小，容易受到访存、batch 组织和 kernel launch 开销影响。如果并发不足或 batch 中序列长度差异大，GPU 可能无法形成足够大的高效矩阵计算。优化方向包括 continuous batching、PagedAttention、合适的并发控制、KV cache 管理、量化和张量并行。</p></div>
</div>

<div class="card card-w">
<h3>高频面试问答：推荐答题结构</h3>
<p>下面这些问题适合放在复习页最后。回答时建议使用固定结构：先给结论，再分层解释，最后补充权衡和排查方法。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: AI Infra 面试里，怎么系统介绍你对 GPU 的理解？</div>
<div class="qa-a">
<p>我会从五层讲：第一是硬件架构层，GPU 通过 SM、warp、Tensor Core、HBM 实现高吞吐并行计算；第二是算子性能层，用 GPU Util、SM Active、Tensor Core Util、HBM bandwidth、Roofline 判断瓶颈；第三是任务层，训练要关注参数、梯度、optimizer state、activation 和通信，推理要关注 KV cache、prefill/decode 和 batching；第四是多卡多机层，关注 NVLink/NVSwitch、PCIe、InfiniBand/RoCE、GPUDirect RDMA 和 NCCL；第五是平台层，关注 Kubernetes device plugin、DRA、gang scheduling、MIG/MPS、拓扑感知、监控和故障恢复。</p>
<div class="qa-summary">答题要点：不要从零散名词开始，要从“单卡计算 → 多卡通信 → 集群调度 → 线上排障”组织。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 利用率低，你会怎么排查？</div>
<div class="qa-a">
<p>我会先确认低利用率是持续低还是周期性低。如果周期性低，可能是 dataloader、CPU 预处理、通信同步或 checkpoint 导致的空洞；如果持续低，可能是 batch 太小、kernel 太碎、shape 不适合 Tensor Core、模型本身计算量不足或被共享任务干扰。然后结合 SM Active、Tensor Core Util、HBM bandwidth、CPU/IO、NCCL trace 和 step timeline 判断。单卡任务重点看输入 pipeline 和算子效率，多卡任务还要看 collective 通信和 straggler。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 显存没满，为什么任务还是可能很慢？</div>
<div class="qa-a">
<p>显存容量只是能不能放下任务，不代表任务跑得快。任务可能受算力、显存带宽、cache miss、通信、CPU dataloader、kernel launch、同步点或调度等待影响。比如 decode 阶段可能 KV cache 占用可控，但每步读取历史 KV 导致访存瓶颈；多卡训练可能每张卡显存都没满，但 AllReduce 或 AllGather 占用大量时间。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果让你设计一个 GPU 集群调度系统，你会考虑哪些点？</div>
<div class="qa-a">
<p>我会分资源表达、调度策略、隔离共享、队列公平、拓扑感知、可观测性和故障处理几部分。资源表达上要支持整卡、MIG、共享 GPU、RDMA、local SSD 等组合资源；调度策略上要支持 gang scheduling、priority、quota、preemption 和 backfill；性能上要考虑 NVLink/NVSwitch、NUMA、机架和网络拓扑；隔离上要区分训练、推理、开发任务，合理使用 MIG/MPS/time-slicing；可观测性上要采集 DCGM、NCCL、作业级吞吐和节点健康；故障处理上要支持自动隔离坏卡、重试、迁移、checkpoint 恢复和容量回收。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你如何解释 MFU？它和 GPU Utilization 有什么区别？</div>
<div class="qa-a">
<p>GPU Utilization 更偏设备是否忙，MFU 更偏模型实际计算效率。MFU 通常用模型实际完成的 FLOPs 除以硬件理论峰值 FLOPs，用来衡量大模型训练是否充分利用了 GPU 理论算力。GPU Util 高可能只是一直有 kernel 在跑，但这些 kernel 可能不是高效 Tensor Core kernel，也可能受访存或通信限制，实际 MFU 不高。因此训练优化不能只看 GPU Util，还要看 step time、实际 token/s、TFLOPS、通信占比和 MFU。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么拓扑感知调度对 GPU 集群很重要？</div>
<div class="qa-a">
<p>因为同样是 8 张 GPU，它们之间的互联质量可能完全不同。在同一个 NVSwitch 域内通信，和跨 PCIe switch、跨 NUMA、跨节点通信，带宽和延迟差异很大。分布式训练中大量 AllReduce、AllGather、ReduceScatter 或 all-to-all 通信会放大这种差异。拓扑感知调度可以尽量把同一个任务放到通信更近、带宽更高、网络更稳定的资源集合上，减少通信瓶颈和 straggler。</p>
</div>
</div>
