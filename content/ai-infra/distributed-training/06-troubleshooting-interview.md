## 一句话结论

分布式训练排障先分层：数据、单卡算子、通信、并行策略、存储、调度和故障恢复。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 分布式训练 |
| 章节类型 | 排障诊断类 |
| 解决问题 | 围绕数据并行、张量并行、流水线并行、ZeRO/FSDP、NCCL 和训练排障建立大模型训练系统答案。 |
| 面试抓手 | 把 GPU-Util、MFU、NCCL、OOM、hang 分开定位。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m">
<h3>分布式训练排障：先定位瓶颈属于哪一层</h3>
<p>分布式训练慢或失败，不能只盯 GPU 利用率。应按链路拆分：数据加载 → CPU 预处理 → GPU 计算 → 显存/激活 → NCCL 通信 → checkpoint/存储 → 调度和拓扑。</p>
</div>

<div class="card card-s">
<h3>高频故障速查</h3>
<table>
<tr><th>现象</th><th>优先排查</th><th>常见原因</th></tr>
<tr><td>GPU 利用率低</td><td>DataLoader、CPU、I/O、通信等待</td><td>数据供给慢、batch 太小、NCCL 等待</td></tr>
<tr><td>GPU 利用率高但训练慢</td><td>MFU、kernel timeline、NCCL timeline</td><td>低效 kernel、通信占比高、显存带宽瓶颈</td></tr>
<tr><td>NCCL hang</td><td>rank 日志、首个失败 rank、网络设备</td><td>rank 调用顺序不一致、某 rank OOM、IB 不通</td></tr>
<tr><td>CUDA OOM</td><td>模型状态、activation、fragmentation</td><td>batch/seq 太大、ZeRO 配置不当、checkpoint 缺失</td></tr>
<tr><td>checkpoint 很慢</td><td>存储带宽、元数据、并发写</td><td>多 rank 同时写、共享文件系统拥塞</td></tr>
</table>
</div>

<div class="card card-d">
<h3>面试计算题套路</h3>
<table>
<tr><th>题型</th><th>核心公式</th><th>容易错的点</th></tr>
<tr><td>DP 通信量</td><td><div class="formula">$$2 \times (N - 1) / N \times P \times \text{bytes}$$</div></td><td>区分梯度大小和每卡收发量</td></tr>
<tr><td>ZeRO 显存</td><td><div class="formula">$$P \times (optimizer/N + grad/N + param/N)$$</div></td><td>不同 ZeRO 阶段分片对象不同</td></tr>
<tr><td>PP bubble</td><td><div class="formula">$$(p - 1) / (m + p - 1)$$</div></td><td>m 是 micro-batch 数，不是 batch size</td></tr>
<tr><td>3D 并行度</td><td><div class="formula">$$\text{Total GPUs} = DP \times TP \times PP$$</div></td><td>TP 通常不能跨节点随便放</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 利用率低，如何判断是数据加载慢还是通信慢？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先观察时间线，再做隔离实验。</p>
<div class="qa-section"><div class="qa-section-title">1. 看 timeline</div><p>用 profiler 看 GPU kernel 之间是否有大空洞。如果空洞出现在 forward 前，多半是数据加载；如果出现在 backward 中或 optimizer 前，多半是通信同步。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 做隔离实验</div><p>用 synthetic data 替代真实 DataLoader。如果吞吐显著提升，说明数据链路慢；如果仍慢，再看 NCCL/计算。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 看系统指标</div><p>数据慢常伴随 CPU 高、磁盘/网络读高、DataLoader worker 忙；通信慢常伴随 NCCL kernel 时间长、网卡带宽高或 rank 等待。</p></div>
<div class="qa-summary">面试口径：先看 timeline 空洞位置，再用 synthetic data 隔离数据链路，最后结合 CPU/I/O/NCCL 指标判断。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 nvidia-smi 显示 GPU-Util 100%，训练仍然可能不高效？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>区分 GPU-Util、SM Active、MFU 和端到端吞吐。</p>
<div class="qa-section"><div class="qa-section-title">1. GPU-Util 不是算力利用率</div><p><code>nvidia-smi</code> 的 GPU-Util 更接近采样窗口内是否有 kernel 在跑，不代表 Tensor Core 被充分利用。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 更应看 MFU</div><p>MFU 衡量模型实际吞吐对应的 FLOPs 占硬件峰值的比例：</p><div class="formula">$$\mathrm{MFU} = \text{Actual Model FLOPs} / \text{Hardware Peak FLOPs}$$</div></div>
<div class="qa-section"><div class="qa-section-title">3. 高 util 低效率原因</div><p>可能是小 kernel 碎片、访存瓶颈、通信等待、精度未用 Tensor Core、batch 太小或算子 fallback。</p></div>
<div class="qa-summary">面试口径：GPU-Util 100% 只能说明 GPU 忙，不说明忙得有效；训练效率要看 MFU、吞吐和 timeline。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 64 卡训练，TP=8、PP=4，DP 是多少？如果每节点 8 卡，需要几台机器？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>用 3D 并行乘积公式，再结合每节点 GPU 数计算机器数。</p>
<div class="qa-section"><div class="qa-section-title">1. 计算 DP</div><div class="formula">$$DP = 64 / (8 \times 4) = 2$$</div></div>
<div class="qa-section"><div class="qa-section-title">2. 计算节点数</div><p>每节点 8 卡，总共 64 卡：</p><div class="formula">$$\text{Nodes} = 64 / 8 = 8$$</div></div>
<div class="qa-section"><div class="qa-section-title">3. 放置解释</div><p>每个 TP group 占一台机器，4 个 PP stage 占 4 台机器，一条 pipeline 用 4 台机器；DP=2 表示两条 pipeline 副本，共 8 台机器。</p></div>
<div class="qa-summary">面试口径：DP=2，总共 8 台 8 卡机器；TP 节点内，PP 跨节点，DP 是 pipeline 副本数。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 训练任务 OOM，应该先调 batch size、ZeRO，还是 activation checkpointing？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>按 OOM 来源分类，不要机械回答。</p>
<div class="qa-section"><div class="qa-section-title">1. 参数/优化器状态 OOM</div><p>如果模型状态占主导，优先 ZeRO/FSDP、optimizer offload、参数分片。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Activation OOM</div><p>如果 seq_len/batch 增大后 OOM，通常是 activation 占主导，优先 activation checkpointing、减小 micro-batch 或 sequence parallel。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 碎片和峰值</div><p>如果偶发 OOM，要看 allocator fragmentation、临时 workspace、checkpoint 保存/加载时的峰值。</p></div>
<div class="qa-summary">面试口径：状态 OOM 用 ZeRO/FSDP，activation OOM 用 checkpointing/减 batch，偶发 OOM 要看碎片和临时峰值。</div>
</div>
</div>

## 面试回答

**30 秒版：**

分布式训练排障先分层：数据、单卡算子、通信、并行策略、存储、调度和故障恢复。 把 GPU-Util、MFU、NCCL、OOM、hang 分开定位。

**2 分钟版：**

我会先说明这个问题在 分布式训练 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
