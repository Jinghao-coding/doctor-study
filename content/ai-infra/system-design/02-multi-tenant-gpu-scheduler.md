<div class="card card-d">
<h3>题目</h3>
<p>设计一个多团队共享的 GPU 训练集群调度系统，要求公平且高效。</p>

<h3>设计要点</h3>
<ol>
<li><strong>配额管理</strong>
  <ul>
  <li>QAD 连续信号替代二元配额（有/没有）</li>
  <li>DRA 弹性借用：闲置资源可借，需要时按 QAD 优先级回收</li>
  </ul>
</li>
<li><strong>调度排序</strong>
  <ul>
  <li>词典序 (QAD↑, T̂↑)：先满足最欠缺的租户，同等 QAD 下短作业优先</li>
  <li>代价基抢占：综合释放资源量和沉没成本</li>
  </ul>
</li>
<li><strong>资源共享</strong>
  <ul>
  <li>干扰感知合用：RF 预测性能保持率 → 高于阈值才合用</li>
  <li>运行时监控 + 驱逐机制保护主任务</li>
  </ul>
</li>
<li><strong>K8s 原生</strong>
  <ul>
  <li>Scheduler Plugin 覆盖 5 个扩展点</li>
  <li>DaemonSet 部署 MPS daemon + DCGM 监控</li>
  <li>Lease-based 选主保证高可用</li>
  </ul>
</li>
</ol>


<div class="card card-m">
<h3>开放题：设计面向大模型训练任务的 GPU 集群调度系统</h3>
<p>这类题不要直接跳到某个算法。推荐按“任务抽象 → 资源抽象 → 调度目标 → 调度策略 → 拓扑感知 → 故障处理 → 观测系统 → 性能优化”的顺序回答。这样既覆盖系统边界，也能体现你知道 AI Infra 和普通 K8s 调度的差异。</p>
</div>

<div class="card card-s">
<h3>1. 任务抽象：不同任务的调度语义不同</h3>
<table>
<tr><th>任务类型</th><th>调度特点</th><th>关键字段</th><th>控制器/对象</th></tr>
<tr><td>大模型训练任务</td><td>多 worker、强同步、需要 gang、运行时间长</td><td>world_size、min/target/max、并行策略、checkpoint</td><td>TrainingJob / VolcanoJob / PyTorchJob</td></tr>
<tr><td>在线推理任务</td><td>长期服务、SLA、流量波动、可水平扩缩容</td><td>模型、QPS、SLO、显存、batch 策略</td><td>Deployment / InferenceService</td></tr>
<tr><td>评测任务</td><td>批处理、可排队、通常可重试</td><td>数据集、模型版本、并发度、deadline</td><td>Job / Workflow</td></tr>
<tr><td>数据处理任务</td><td>I/O 密集、存储和网络敏感</td><td>输入路径、输出路径、CPU/内存/IOPS</td><td>Job / SparkApplication</td></tr>
</table>
</div>

<div class="card card-d">
<h3>2. 资源抽象：不能只抽象成 GPU 数量</h3>
<table>
<tr><th>资源</th><th>为什么重要</th><th>调度表达</th></tr>
<tr><td>GPU 型号</td><td>H100/A100/V100 性能和能力不同</td><td>ResourceFlavor、node label、extended resource</td></tr>
<tr><td>显存</td><td>模型能否放下、batch size 上限</td><td>GPU memory profile、MIG slice、DRA attributes</td></tr>
<tr><td>CPU / 内存</td><td>数据加载、预处理、通信线程</td><td>requests/limits、NUMA 亲和</td></tr>
<tr><td>网络</td><td>NCCL、RDMA、跨节点 AllReduce</td><td>NIC 亲和、机架/交换机拓扑</td></tr>
<tr><td>存储</td><td>数据集读取、checkpoint 写入</td><td>存储类型、本地 NVMe、带宽/IOPS</td></tr>
<tr><td>拓扑</td><td>同机、同交换机、跨机通信代价不同</td><td>Topology score、DRA ResourceSlice、scheduler plugin</td></tr>
</table>
</div>

<div class="card card-w">
<h3>3. 调度目标：先定硬约束，再定优化目标</h3>
<table>
<tr><th>目标</th><th>含义</th><th>对应策略</th><th>牺牲项</th></tr>
<tr><td>高利用率</td><td>减少 GPU 空闲和碎片</td><td>bin packing、backfill、GPU sharing</td><td>故障隔离、热点、SLA</td></tr>
<tr><td>低等待时间</td><td>任务提交后尽快开始</td><td>SJF、优先级、预留、弹性训练</td><td>拓扑质量、全局最优</td></tr>
<tr><td>公平性</td><td>团队之间按份额获得资源</td><td>DRF、quota、QAD、aging</td><td>短期吞吐</td></tr>
<tr><td>SLA</td><td>在线推理和关键任务不能违约</td><td>优先级、预留、抢占、隔离池</td><td>离线利用率</td></tr>
<tr><td>成本</td><td>用更少 GPU 完成更多任务</td><td>性能预测、混部、低优任务填充</td><td>系统复杂度</td></tr>
</table>
</div>

<div class="card card-s">
<h3>4. 调度策略：队列、配额、抢占、回填组合使用</h3>
<ol>
<li><strong>队列准入：</strong>任务进入团队队列，检查 quota、优先级、GPU flavor 和 gang 需求。</li>
<li><strong>排序：</strong>先按保障度/QAD 和优先级排序，同等级内可以用 SJF 或 aging。</li>
<li><strong>Gang 准入：</strong>训练任务必须满足 minAvailable，否则不启动任何 worker。</li>
<li><strong>放置：</strong>Filter 检查资源和硬约束，Score 综合 bin packing、拓扑、碎片、故障域。</li>
<li><strong>回填：</strong>队头大任务等资源时，允许短任务利用碎片窗口。</li>
<li><strong>抢占：</strong>高优任务或保障租户不足时，按 checkpoint-aware cost 回收低优任务。</li>
<li><strong>运行时调整：</strong>支持 elastic training 扩缩容，或根据干扰/故障触发迁移和重试。</li>
</ol>
</div>

<div class="card card-d">
<h3>5. 拓扑感知：同样 8 卡，性能可能完全不同</h3>
<table>
<tr><th>并行方式</th><th>通信模式</th><th>放置偏好</th></tr>
<tr><td>张量并行 TP</td><td>每层 AllReduce/AllGather</td><td>同节点 NVLink/NVSwitch</td></tr>
<tr><td>流水线并行 PP</td><td>相邻 stage P2P</td><td>相邻 stage 尽量同机柜/低延迟网络</td></tr>
<tr><td>数据并行 DP</td><td>每步梯度 AllReduce</td><td>可跨节点，但要 RDMA 网络质量好</td></tr>
<tr><td>专家并行 EP</td><td>All-to-All</td><td>尽量避免跨拥塞域</td></tr>
</table>
</div>

<div class="card card-w">
<h3>6. 故障处理：训练任务的失败成本更高</h3>
<table>
<tr><th>故障</th><th>检测</th><th>处理</th></tr>
<tr><td>节点失联</td><td>Node heartbeat、Pod event</td><td>标记节点不可调度，任务从 checkpoint 重启</td></tr>
<tr><td>GPU 故障</td><td>DCGM、ECC/Xid、健康检查</td><td>隔离 GPU，驱逐相关任务，触发重调度</td></tr>
<tr><td>NCCL hang</td><td>训练心跳、step time 超时</td><td>dump 日志，重建通信组或整组重启</td></tr>
<tr><td>存储故障</td><td>I/O error、checkpoint timeout</td><td>重试、切换副本、降低 checkpoint 频率</td></tr>
<tr><td>抢占</td><td>队列回收或高优任务到达</td><td>优雅 checkpoint 后退出，超时强制终止</td></tr>
</table>
</div>

<div class="card card-s">
<h3>7. 观测系统：没有指标就无法调度优化</h3>
<table>
<tr><th>观测对象</th><th>关键指标</th><th>用途</th></tr>
<tr><td>任务状态</td><td>Pending/Running/Failed、等待原因、重试次数</td><td>解释任务为什么没跑</td></tr>
<tr><td>资源利用率</td><td>GPU util、SM Active、显存、CPU、网络、存储</td><td>判断瓶颈和资源浪费</td></tr>
<tr><td>调度指标</td><td>waiting time、JCT、队列长度、backfill 命中率</td><td>评估调度策略效果</td></tr>
<tr><td>公平性</td><td>QAD、dominant share、quota debt</td><td>判断租户是否被保障</td></tr>
<tr><td>失败率</td><td>节点故障、GPU Xid、NCCL error、OOM</td><td>做故障治理和容量规划</td></tr>
</table>
</div>

<div class="card card-m">
<h3>8. 性能优化：碎片、局部性和预测</h3>
<table>
<tr><th>优化方向</th><th>方法</th><th>收益</th></tr>
<tr><td>减少碎片</td><td>bin packing、reservation、defragmentation</td><td>大任务更容易启动</td></tr>
<tr><td>提升 locality</td><td>拓扑打分、GPU-NIC 亲和、同机/同机柜优先</td><td>降低通信开销</td></tr>
<tr><td>结合性能预测</td><td>预测不同 placement 的 step time 或 JCT</td><td>更准确地判断是否等待更好资源</td></tr>
<tr><td>提升启动速度</td><td>镜像预热、模型缓存、本地数据缓存</td><td>降低 cold start 和 JCT</td></tr>
<tr><td>混部优化</td><td>干扰预测、MIG/MPS、低优任务填空</td><td>提升利用率但保护主任务</td></tr>
</table>
</div>

<div class="card card-d">
<h3>面试回答模板</h3>
<ol>
<li><strong>先明确 workload：</strong>训练、推理、评测、数据处理，不同任务调度语义不同。</li>
<li><strong>再定义资源：</strong>GPU 不只是数量，还包括型号、显存、拓扑、网络、存储和故障域。</li>
<li><strong>然后讲队列系统：</strong>多租户用层级队列、min/max quota、DRF/QAD、公平借用和回收。</li>
<li><strong>接着讲调度流水线：</strong>排序、gang 准入、Filter/Score、拓扑放置、backfill、抢占。</li>
<li><strong>补充 AI 特有点：</strong>GPU 碎片、NCCL、checkpoint、elastic training、拓扑感知和性能预测。</li>
<li><strong>最后讲可观测和容错：</strong>等待原因、资源利用率、失败率、checkpoint 恢复和健康检查。</li>
</ol>
<div class="qa-summary">面试金句：GPU 集群调度不是“找有空 GPU 的节点”，而是在多租户公平、gang 语义、拓扑质量、碎片治理和抢占代价之间做持续权衡。</div>
</div>

<h3>追问方向</h3>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">追问：怎么处理大任务和小任务的矛盾？</div>
<div class="qa-a"><p>大任务（需要 64 GPU）和小任务（需要 1 GPU）的调度矛盾：(1) Gang scheduling 保证大任务原子性。(2) Backfill 让小任务见缝插针。(3) 大任务可以拆分为弹性训练（先用 32 GPU 开始，有空闲再扩到 64）。(4) 预留机制：为大任务预留资源窗口，避免永远等不到足够资源。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">追问：如何处理异构 GPU？</div>
<div class="qa-a"><p>(1) ResourceFlavor 区分不同 GPU 型号（A100/H100/V100）。(2) 运行时间预测模型需要区分 GPU 类型——同样的作业在 A100 和 H100 上时间不同。(3) 价格/性能比引导调度：不紧急的任务用便宜 GPU，紧急任务用高端 GPU。(4) 混合精度兼容性：H100 支持 FP8，A100 只支持到 FP16/BF16。</p></div>
</div>
</div>

<hr class="div">
