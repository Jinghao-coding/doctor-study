## 并行方式与训练语义

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q1：DP、TP、PP、EP 分别切什么？为什么不能随便增加并行度？</div>
<div class="qa-a"><p>DP 用模型副本处理不同数据；TP 切层内张量运算；PP 切层形成流水线；EP 把 MoE 专家分到不同设备。DP 有梯度同步，TP 常有层内集合通信，PP 传 stage 间激活与梯度，EP 有 token dispatch/combine。并行度越大不代表越快，通信、气泡、小矩阵效率和负载不均可能抵消收益。</p><p><strong>追问：DP×TP×PP×EP 就是卡数吗？</strong>不能无条件相乘。只有互不重叠的 mesh 维度才能相乘；EP 常与已有并行组组合或重用 rank，须先说明具体布局。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q2：DDP 每一步同步参数还是梯度？数据会自动分片吗？</div>
<div class="qa-a"><p>典型 DDP 在初始化时对齐模型状态，反向过程中同步梯度，各 rank 用一致梯度和优化器状态更新本地参数；不是每步从主 rank 下发整份新权重。输入分片由采样器或数据管道负责，DDP 不自动替你切数据。</p><p><strong>追问：为什么同步了梯度还可能结果不同？</strong>检查初始参数、优化器、有效 batch、loss 归一化、随机性和数据重复；模型 buffer 也有自己的同步语义，不能只看参数。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q3：梯度累积怎样等价于大 batch？有效 batch 怎么算？</div>
<div class="qa-a"><p>固定长度、等权样本下，有效 batch = 每个 DP 副本的 micro-batch × 累积步数 × DP。TP/PP 协作处理同一份样本，不再乘进去。多个小步累积后才更新一次；DDP 可用 no_sync 避免非最后一次的同步，且 forward 也应在该上下文内。</p><p><strong>计算例：</strong>DP=4、micro-batch=2、累积=8，有效 batch 为 64。若各小步 loss 都取等规模样本均值，通常再按累积次数缩放。变长 token 或不等 batch 时，应按全局有效 token/样本数归一化；简单除以 8 可能不等价。</p></div>
</div>

DDP 的同步、输入划分与 no_sync 语义参见 [PyTorch DDP 文档](https://docs.pytorch.org/docs/main/generated/torch.nn.parallel.DistributedDataParallel.html)。

## 状态显存与通信估算

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q4：ZeRO 1/2/3 各省什么？开了 ZeRO-3 为什么还会 OOM？</div>
<div class="qa-a"><p>Stage 1 分片优化器状态，Stage 2 再分片梯度，Stage 3 再分片参数。假设每参数权重 2 B、梯度 2 B、FP32 主权重和 Adam 两份状态共 12 B，N 个 DP rank 的状态估算依次为 4+12/N、2+14/N、16/N B/参数。这是给定精度假设下的常驻状态估算。</p><p><strong>追问：哪些没算？</strong>激活、临时 workspace、通信缓冲、正在 all-gather 的完整参数和预取峰值。7B 参数、N=8 的 Stage 3 理想状态约 14 GB（十进制），不是整次训练只需 14 GB/卡。FSDP 的峰值还与分组粒度和 reshard 策略有关。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q5：FSDP 和 TP 都切参数，区别在哪里？</div>
<div class="qa-a"><p>FSDP 在数据并行 rank 间分片状态，计算一个参数组前通常 all-gather 所需完整参数，再执行本地样本计算，之后可重新分片；TP 让各 rank 直接参与同一层的不同张量分片计算。二者通信发生的位置和计算语义不同，也可以组合。</p><p><strong>追问：FSDP 参数组越小越好吗？</strong>小组降低聚合峰值，却增加小消息和调度成本；大组通信更集中，但显存峰值和暴露通信可能增大。预取可重叠通信，也会增加同时驻留的参数。</p></div>
</div>

FSDP 的参数聚合和预取行为参见 [PyTorch FSDP2 教程](https://docs.pytorch.org/tutorials/intermediate/FSDP_tutorial.html)。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q6：Ring AllReduce 的通信量怎么估算？</div>
<div class="qa-a"><p>N 个 rank、每 rank 梯度大小 G 字节，经典 Ring 的 reduce-scatter 加 all-gather 中，每 rank 发送约 2(N−1)G/N 字节，接收同样多。若统计发送加接收总量，应再乘 2；不要混淆统计口径。</p><p><strong>计算例：</strong>N=8、G=1 GiB，每 rank 发送约 1.75 GiB，也接收约 1.75 GiB。以有效单向带宽估计关键路径传输时间时，不应机械用收发总量除带宽；还需考虑启动延迟、双向重叠、拓扑和链路争用。这只是 Ring 模型，不是所有 NCCL 算法的固定代价。</p></div>
</div>

集合通信的结果语义参见 [NCCL Collective Operations](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/collectives.html)；上面的字节数是经典 Ring 的解析估算。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q7：怎样重叠通信和计算？为什么 bucket 不能无限小？</div>
<div class="qa-a"><p>反向时一组梯度就绪即可启动该组通信，与后面层的反向重叠。小 bucket 启动早但小消息开销高；大 bucket 带宽利用可能更好，却更晚就绪，留下不可隐藏的通信尾部。要看梯度就绪时间、通信时间和计算时间线。</p><p><strong>追问：NCCL kernel 很长就一定是网卡慢吗？</strong>也可能在等迟到 rank。先比较各 rank 进入 collective 的时间，再检查实际传输阶段和网卡吞吐。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q8：PP 的流水线气泡怎么降低？</div>
<div class="qa-a"><p>在平衡 stage、忽略通信等简化假设下，常见流水线模型的气泡占比约为 (p−1)/(m+p−1)，p 是 stage 数，m 是 micro-batch 数。例如 p=4、m=8，约 27.3%。增加 m 有利于摊薄填充排空气泡，但会改变 batch 或使单个 micro-batch 太小。</p><p><strong>追问：1F1B 消除气泡了吗？</strong>没有。交错调度能降低部分空闲，1F1B 也有助于控制在途激活；仍需考虑 stage 不均衡、通信与调度约束，不能把简化公式当成实测利用率。</p></div>
</div>

## 排障与恢复

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q9：8 卡扩成 64 卡后加速很差，怎么分析？</div>
<div class="qa-a"><p>先说明固定全局 batch 的强扩展，还是固定每卡 batch 的弱扩展。强扩展时每卡计算减少，通信更难隐藏；弱扩展则改变有效 batch 和优化过程。再分解数据读取、计算、同步、流水线空闲与 checkpoint，定位端到端吞吐损失。</p><p><strong>追问：怎样验证判断？</strong>用合成数据隔离输入，用同节点和跨节点对比检查拓扑，检查最慢 rank 和 bucket 尾部。吞吐提升之外，还要看达到同等质量所需训练时间。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q10：遇到 NCCL timeout，第一步是调大超时吗？</div>
<div class="qa-a"><p>先找所有 rank 中最早的异常：某个 rank OOM、数据迭代提前结束或走入不同 collective，其他 rank 就可能随后超时。核对 collective 顺序、tensor 形状、进程存活，再查网络、驱动和硬件错误；延长 timeout 无法修复顺序不一致。</p><p><strong>追问：作业恢复要保存什么？</strong>模型、优化器、学习率调度器、步数、必要的随机数与数据进度状态。保存应有一致的完成标记，避免读取半份 checkpoint；只恢复权重不能视为无损续训。</p></div>
</div>
