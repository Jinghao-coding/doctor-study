<div class="card card-m">
<h3>故障类型全景</h3>
<p>GPU 集群故障远比 CPU 集群频繁——一块 A100 的 MTBF 约 24 个月，一个 1024 卡集群的平均无故障时间仅约 24 小时。理解每种故障的特征是设计容错体系的前提。</p>
</div>

<div class="card card-s">
<h3>1. GPU ECC 错误</h3>
<table>
<tr><th>维度</th><th>说明</th></tr>
<tr><td><strong>频率</strong></td><td>单卡约每月 1-2 次（可纠正）；不可纠正约每 3-6 个月一次</td></tr>
<tr><td><strong>现象</strong></td><td>可纠正：DCGM 报 <code>ECC_SBE</code> 警告，训练继续但性能微降；不可纠正：CUDA 报 <code>uncorrectable ECC error</code>，进程崩溃</td></tr>
<tr><td><strong>影响</strong></td><td>单卡故障 → 整个训练 Job 挂起（Gang Scheduling 约束）</td></tr>
<tr><td><strong>检测</strong></td><td><code>nvidia-smi -q -d ECC</code>；DCGM <code>dcgmi diag -r 3</code>；Prometheus <code>DCGM_FI_DEV_ECC_SBE_VOLATILE</code> 指标</td></tr>
<tr><td><strong>响应</strong></td><td>可纠正：标记降级，继续运行；不可纠正：驱逐 Pod，触发重调度</td></tr>
</table>
<p class="qa-summary">类比：ECC 就像内存的"自动纠错笔"——单比特翻转它能自己修正（可纠正），但如果一次翻转太多比特，就修不过来了（不可纠正），只能放弃这张卡。</p>
</div>

<div class="card card-s">
<h3>2. NVLink 降级</h3>
<table>
<tr><th>维度</th><th>说明</th></tr>
<tr><td><strong>频率</strong></td><td>较低，约每 2-3 个月一次（通常由温度/物理连接问题引起）</td></tr>
<tr><td><strong>现象</strong></td><td>NVLink 从 600 GB/s 降到 300 GB/s 或完全断开；<code>nvidia-smi nvlink -s</code> 显示链路状态变化</td></tr>
<tr><td><strong>影响</strong></td><td>TP 通信延迟翻倍 → 整体训练吞吐下降 20-40%；Ring AllReduce 性能急剧下降</td></tr>
<tr><td><strong>检测</strong></td><td><code>nvidia-smi nvlink -s</code>；DCGM <code>NVLink</code> 错误计数器；训练中观察到通信时间异常增长</td></tr>
<tr><td><strong>响应</strong></td><td>降低并行度（如 TP=8 降到 TP=4），或将该节点从 TP 组中排除</td></tr>
</table>
<p class="qa-summary">类比：NVLink 降级就像高速公路突然从 8 车道变成 4 车道——车（数据）还能走，但通行时间翻倍。</p>
</div>

<div class="card card-s">
<h3>3. 节点故障</h3>
<table>
<tr><th>维度</th><th>说明</th></tr>
<tr><td><strong>频率</strong></td><td>约 1-2 次/月/节点（包括 kernel panic、内存故障、电源问题等）</td></tr>
<tr><td><strong>现象</strong></td><td>节点 NotReady；所有 GPU Pod 进入 <code>Unknown</code> 或 <code>Terminating</code> 状态</td></tr>
<tr><td><strong>影响</strong></td><td>所有运行在该节点上的训练 Job 中断；如果是 DP 组中的节点，整个 Job 需要重启</td></tr>
<tr><td><strong>检测</strong></td><td>kubelet 心跳超时；Node Problem Detector；DCGM <code>dcgmi diag</code> 节点级诊断</td></tr>
<tr><td><strong>响应</strong></td><td>标记节点 <code>unschedulable</code>；重建 Pod；如果支持弹性训练则缩容继续</td></tr>
</table>
</div>

<div class="card card-s">
<h3>4. 网络分区</h3>
<table>
<tr><th>维度</th><th>说明</th></tr>
<tr><td><strong>频率</strong></td><td>约 1 次/1-2 月（交换机故障、光模块损坏、配置错误等）</td></tr>
<tr><td><strong>现象</strong></td><td>部分节点间 RDMA 连接断开；NCCL 超时 <code>ncclTimeout</code>；etcd 选举超时</td></tr>
<tr><td><strong>影响</strong></td><td>集群分裂为多个分区；跨分区的 AllReduce 无法完成；可能导致脑裂</td></tr>
<tr><td><strong>检测</strong></td><td>NCCL 超时日志；InfiniBand <code>ibqueryerrors</code>；etcd 延迟飙升</td></tr>
<tr><td><strong>响应</strong></td><td>缩小训练规模到同一分区内；或者等待网络恢复后重建 Job</td></tr>
</table>
</div>

<div class="card card-w">
<h3>5. OOM（显存溢出）</h3>
<table>
<tr><th>维度</th><th>说明</th></tr>
<tr><td><strong>频率</strong></td><td>训练阶段较高，尤其在模型参数、batch size 变更时</td></tr>
<tr><td><strong>现象</strong></td><td>CUDA <code>out of memory</code>；进程被 OOM Killer 杀掉；容器被驱逐</td></tr>
<tr><td><strong>影响</strong></td><td>单卡 OOM → 整个训练 Job 失败（Gang 约束）</td></tr>
<tr><td><strong>检测</strong></td><td><code>nvidia-smi</code> 显存使用率接近 100%；cgroup OOM 事件；PyTorch <code>CUDA out of memory</code> 异常</td></tr>
<tr><td><strong>响应</strong></td><td>减小 batch size / 启用 gradient checkpointing / 增加 ZeRO 分片级别 / 扩容 GPU 数量</td></tr>
</table>
</div>

<div class="card card-d">
<h3>故障响应体系：检测 → 定位 → 恢复</h3>
<table>
<tr><th>阶段</th><th>方法</th><th>工具</th><th>时延</th></tr>
<tr><td><strong>检测</strong></td><td>指标异常 + 心跳超时 + 诊断测试</td><td>DCGM + Prometheus + NPD</td><td>秒级 ~ 分钟级</td></tr>
<tr><td><strong>定位</strong></td><td>逐层排查：GPU → NVLink → 节点 → 网络</td><td><code>dcgmi diag</code> + <code>ibqueryerrors</code> + <code>kubectl describe</code></td><td>分钟级</td></tr>
<tr><td><strong>恢复</strong></td><td>重启 / 重调度 / 缩容 / 从 Checkpoint 恢复</td><td>Volcano/Kueue + PyTorch Elastic + Checkpoint</td><td>分钟级 ~ 小时级</td></tr>
</table>
</div>

<div class="card card-s">
<h3>检测工具栈</h3>
<pre><code>┌─────────────────────────────────────────────┐
│              Grafana Dashboard               │
│          (可视化告警 &amp; 历史趋势)              │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│              Prometheus                       │
│     (指标采集 + 告警规则 + 数据存储)          │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         DCGM Exporter                        │
│    (GPU 指标: 温度/ECC/显存/利用率/NVLink)    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│            DCGM (Data Center GPU Mgmt)       │
│        (底层 GPU 状态采集 + 诊断)             │
└─────────────────────────────────────────────┘</code></pre>
<table>
<tr><th>指标</th><th>含义</th><th>告警阈值</th></tr>
<tr><td><code>DCGM_FI_DEV_GPU_TEMP</code></td><td>GPU 温度</td><td>&gt; 85°C</td></tr>
<tr><td><code>DCGM_FI_DEV_ECC_DBE_VOLATILE</code></td><td>不可纠正 ECC 错误数</td><td>&gt; 0</td></tr>
<tr><td><code>DCGM_FI_DEV_FB_USED</code> / <code>FB_TOTAL</code></td><td>显存使用率</td><td>&gt; 95%</td></tr>
<tr><td><code>DCGM_FI_DEV_NVLINK_CRC_FLIT_ERROR_COUNT</code></td><td>NVLink CRC 错误</td><td>持续增长</td></tr>
<tr><td><code>DCGM_FI_DEV_GPU_UTIL</code></td><td>GPU 利用率</td><td>&lt; 10%（可能卡死）</td></tr>
<tr><td><code>DCGM_FI_DEV_POWER_USAGE</code></td><td>功耗</td><td>异常低（可能挂起）</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Checkpoint 策略：GPU 训练容错的基石</h3>
<p>没有 Checkpoint，一次故障就可能浪费数天的训练时间。</p>

<h4 style="margin-top:14px;">1. 周期性 Checkpoint（Periodic）</h4>
<p><strong>原理</strong>：每隔 N 步或 N 分钟保存一次完整的模型状态。</p>
<pre><code># PyTorch 示例
for step, batch in enumerate(dataloader):
    loss = model(batch)
    loss.backward()
    optimizer.step()

    if step % checkpoint_interval == 0:
        torch.save({
            'step': step,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
        }, f"checkpoint_{step}.pt")</code></pre>
<p><strong>优点</strong>：实现简单，所有框架原生支持<br/><strong>缺点</strong>：保存期间训练暂停（大模型 Checkpoint 可能耗时 10-30 分钟）；存储开销大</p>
<p class="qa-summary">手动推演：175B 参数模型 FP16 存储 = 参数 350GB + Adam 状态 1.75TB ≈ 2.1TB/次，每 1000 步保存利用率降低约 2-5%。</p>

<h4 style="margin-top:14px;">2. 异步 Checkpoint（Async）</h4>
<pre><code>训练进程 ──copy──→ 共享内存 ──background──→ 持久存储
   │                                         │
   └── 立即恢复训练 ←──────────不等待──────────┘</code></pre>
<p><strong>优点</strong>：训练暂停时间极短（通常 &lt; 1 秒）<br/><strong>缺点</strong>：需要额外内存（2 倍模型状态）；极端情况可能丢失最后几个 step</p>

<h4 style="margin-top:14px;">3. 增量 Checkpoint（Incremental）</h4>
<p><strong>原理</strong>：只保存与上次 Checkpoint 相比发生变化的部分（通常是优化器状态的增量）。<br/>
<strong>优点</strong>：存储和 I/O 开销大幅降低（增量通常只有全量的 5-20%）<br/>
<strong>缺点</strong>：恢复时需要回放所有增量，恢复链越长越慢</p>

<h4 style="margin-top:14px;">4. 分布式 Checkpoint（Distributed）</h4>
<p><strong>原理</strong>：每个 Rank 只保存自己负责的分片，恢复时各 Rank 读取自己的分片即可。适用于 ZeRO 或 TP 分片场景。<br/>
<strong>优点</strong>：每个节点只写一小部分数据，I/O 并行化，保存速度快<br/>
<strong>缺点</strong>：恢复时必须保证 Rank 映射不变（或支持重映射）</p>
<p class="qa-summary">为什么大模型必须用分布式 Checkpoint？以 175B + ZeRO-3 为例，每张 GPU 只存 1/N 的参数。N=1024 时每卡仅 ~350 MB，保存时间从分钟级降到秒级。</p>
</div>

<div class="card card-d">
<h3>Checkpoint 策略选择</h3>
<table>
<tr><th>维度</th><th>周期性</th><th>异步</th><th>增量</th><th>分布式</th></tr>
<tr><td><strong>实现复杂度</strong></td><td>★☆☆</td><td>★★☆</td><td>★★★</td><td>★★☆</td></tr>
<tr><td><strong>训练暂停</strong></td><td>10-30 min</td><td>&lt; 1s</td><td>&lt; 5 min</td><td>&lt; 1 min</td></tr>
<tr><td><strong>存储开销</strong></td><td>全量</td><td>全量×2</td><td>增量</td><td>全量/N</td></tr>
<tr><td><strong>恢复速度</strong></td><td>快（单文件）</td><td>快</td><td>慢（回放增量）</td><td>中等（需协调）</td></tr>
<tr><td><strong>适用规模</strong></td><td>小模型</td><td>中大模型</td><td>大模型</td><td>超大模型</td></tr>
<tr><td><strong>生产推荐</strong></td><td>小型实验</td><td>通用</td><td>配合分布式</td><td>配合 ZeRO</td></tr>
</table>
<p class="qa-summary">生产实践：异步 + 分布式 + 定期全量（作为增量基线）组合使用。</p>
</div>

<div class="card card-m">
<h3>Checkpoint 最优频率的数学推导</h3>
<p><strong>建模</strong>：C = 单次 Checkpoint 开销（保存时间），F = 平均故障间隔（MTBF），T = 两次 Checkpoint 之间的训练时间。</p>
<ol>
<li>每次 Checkpoint 浪费 C 的时间</li>
<li>故障发生时，平均丢失 T/2 的训练进度</li>
<li>单位时间总浪费 = (C/T) + (T/(2F))
  <ul>
  <li>C/T：Checkpoint 的稳态开销</li>
  <li>T/(2F)：故障导致的平均进度丢失</li>
  </ul>
</li>
<li>对 T 求导令其为零：<code>T* = √(2 × F × C)</code></li>
</ol>
<p><strong>手动验证</strong>：F = 24 小时，C = 15 分钟 → T* = √(2 × 24 × 15) = √720 ≈ 26.8 分钟，即约每 27 分钟保存一次最优。</p>
<div class="qa-summary">面试金句：Checkpoint 频率的最优解是 T* = √(2FC)，本质上是在 Checkpoint 固定开销和故障导致的进度丢失之间找平衡点。</div>
</div>

<div class="card card-s">
<h3>弹性训练（PyTorch Elastic / torchrun）</h3>
<p><strong>核心思想</strong>：允许训练过程中动态改变 world_size（GPU 数量），故障时自动缩容继续训练，新节点加入时自动扩容。</p>
<table>
<tr><th>组件</th><th>作用</th><th>说明</th></tr>
<tr><td><strong>Rendezvous</strong></td><td>分布式协调</td><td>保证所有 Worker 就同一 epoch 的 world_size 达成一致</td></tr>
<tr><td><strong>StateDict</strong></td><td>状态同步</td><td>每个 Rank 保存自己的状态，Rendezvous 后按新 world_size 重新分配</td></tr>
<tr><td><strong>Watchdog</strong></td><td>故障检测</td><td>监控心跳，发现 Worker 失败后触发 Rendezvous 重新协商</td></tr>
</table>

<h4 style="margin-top:12px;">Rendezvous 流程</h4>
<pre><code>初始: 8 GPU (world_size=8), Rank 0-7

Step 1: Rank 3 故障
  └── Watchdog 检测到 Rank 3 心跳超时

Step 2: 触发 Rendezvous
  ├── 存活 Rank [0,1,2,4,5,6,7] 进入 Rendezvous
  ├── 等待 min_nodes=6（最少需要 6 个节点才能继续）
  └── 新 world_size = 7

Step 3: 状态重分配
  ├── 从最近 Checkpoint 恢复模型状态
  ├── 数据集按 7 份重新分片
  └── 优化器状态重新分配（ZeRO 场景）

Step 4: 继续训练
  └── 从 Checkpoint 对应的 step 继续训练</code></pre>

<h4 style="margin-top:12px;">torchrun 启动示例</h4>
<pre><code class="language-bash">torchrun \
  --nnodes=4:8 \
  --nproc_per_node=8 \
  --rdzv_id=job-001 \
  --rdzv_backend=c10d \
  --rdzv_endpoint=master:29500 \
  train.py</code></pre>
</div>

<div class="card card-d">
<h3>弹性 vs 非弹性对比</h3>
<table>
<tr><th>维度</th><th>非弹性训练</th><th>弹性训练</th></tr>
<tr><td><strong>故障响应</strong></td><td>整个 Job 失败，从最近 Checkpoint 重启</td><td>自动缩容，继续训练</td></tr>
<tr><td><strong>恢复时间</strong></td><td>分钟级（重调度 + 重启 + 恢复）</td><td>秒级（Rendezvous + 恢复）</td></tr>
<tr><td><strong>GPU 利用率</strong></td><td>故障期间 GPU 空闲</td><td>故障节点排除，其余继续</td></tr>
<tr><td><strong>实现复杂度</strong></td><td>低</td><td>高（需要处理 Rank 重映射、数据重分片）</td></tr>
<tr><td><strong>训练一致性</strong></td><td>确定性（相同 world_size）</td><td>弱确定性（world_size 变化影响 BatchNorm 等）</td></tr>
<tr><td><strong>框架支持</strong></td><td>所有框架</td><td>PyTorch Elastic、DeepSpeed 等</td></tr>
<tr><td><strong>调度器要求</strong></td><td>普通 Gang Scheduling 即可</td><td>需要支持弹性配额和动态扩缩</td></tr>
</table>

<div class="card card-w" style="margin-top:12px;">
<h3>弹性训练的局限</h3>
<ol>
<li><strong>BatchNorm 兼容性</strong>：world_size 变化导致 global batch size 变化，BN 统计量不一致 → 需使用 SyncBN 或改用 LayerNorm</li>
<li><strong>学习率调整</strong>：线性缩放规则 <code>lr = base_lr × batch_size / 256</code>，batch size 变化时需要相应调整学习率</li>
<li><strong>数据分片</strong>：需要可重新分片的数据加载器（如 <code>DistributedSampler</code> 的 <code>drop_last=False</code>）</li>
<li><strong>ZeRO 重分片</strong>：优化器状态需要按新的 world_size 重新分片，实现复杂</li>
<li><strong>调度器配合</strong>：需要调度器支持弹性配额（如 ElasticQuota），否则缩容后的资源可能被抢占</li>
</ol>
</div>
<div class="qa-summary">面试金句：弹性训练的核心挑战不是技术实现，而是 world_size 变化带来的语义一致性——BatchNorm、学习率、梯度累积步数都需要适配。</div>
</div>

<h3>面试问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一个 1024 卡的 GPU 集群，故障率大约是什么量级？你会怎么设计高可用？</div>
<div class="qa-a">
<p>单卡 MTBF 约 24 个月，1024 卡集群的 MTBF ≈ 24/1024 月 ≈ 42 分钟。这意味着训练过程中几乎必然会遇到故障。</p>
<p><strong>高可用设计层次</strong>：</p>
<ol>
<li><strong>检测层</strong>：DCGM + Prometheus + NPD，秒级发现异常</li>
<li><strong>容错层</strong>：异步分布式 Checkpoint，频率按 T* = √(2FC) 计算</li>
<li><strong>恢复层</strong>：弹性训练（PyTorch Elastic），自动缩容继续</li>
<li><strong>隔离层</strong>：故障节点自动标记 unschedulable，防止新 Pod 调度上去</li>
<li><strong>预防层</strong>：定期 <code>dcgmi diag</code> 体检，提前发现 ECC 错误趋势和温度异常</li>
</ol>
<p>高可用的核心不是"不故障"（不可能），而是"故障后快速恢复"。关键指标是 <strong>MTTR（平均恢复时间）</strong>，而非 MTBF。</p>
<p class="qa-summary">1024 卡集群的 MTBF 约 42 分钟，所以高可用的核心不是防故障，而是降 MTTR——检测快、Checkpoint 密、弹性恢复。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Checkpoint 的最优保存频率怎么算？实际中你怎么定？</div>
<div class="qa-a">
<p>理论最优频率 T* = √(2 × F × C)，其中 F 是 MTBF，C 是单次 Checkpoint 耗时。</p>
<p><strong>手动推演</strong>：F = 24h（256 卡集群），C = 10min（异步分布式 Checkpoint）→ T* = √(2 × 1440 × 10) = √28800 ≈ 170 min ≈ 2.8 小时。</p>
<p><strong>实际调整</strong>：</p>
<ol>
<li><strong>不能比理论值更频繁</strong>：否则 Checkpoint 开销占比过高</li>
<li><strong>可以比理论值稍稀疏</strong>：如果训练对断点丢失容忍度低（如预训练），宁可多保存</li>
<li><strong>关键节点必保存</strong>：epoch 边界、学习率衰减点、验证指标最佳点</li>
<li><strong>生产实践</strong>：通常按步数（如每 1000 步）保存，按时间（如每 2 小时）做全量 Checkpoint</li>
</ol>
<p class="qa-summary">T* 是数学最优解，但实际还需考虑存储成本、I/O 瓶颈、业务容忍度。Checkpoint 频率本质是 Checkpoint 开销和故障损失的帕累托最优。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 弹性训练和 Checkpoint 恢复各自的适用场景？</div>
<div class="qa-a">
<table>
<tr><th>维度</th><th>弹性训练</th><th>Checkpoint 恢复</th></tr>
<tr><td><strong>故障规模</strong></td><td>少量节点故障（1-2 节点）</td><td>大规模故障（半数以上节点）</td></tr>
<tr><td><strong>恢复速度</strong></td><td>秒级 ~ 分钟级</td><td>分钟级 ~ 十分钟级</td></tr>
<tr><td><strong>GPU 利用率</strong></td><td>高（剩余 GPU 继续训练）</td><td>低（所有 GPU 等待重启）</td></tr>
<tr><td><strong>实现复杂度</strong></td><td>高</td><td>低</td></tr>
<tr><td><strong>训练一致性</strong></td><td>弱确定性</td><td>强确定性</td></tr>
</table>
<p><strong>选择原则</strong>：</p>
<ul>
<li>少量节点故障 → 弹性训练（缩容继续，不浪费剩余 GPU）</li>
<li>大规模故障 / 网络分区 → Checkpoint 恢复（等环境恢复后统一重启）</li>
<li>预训练（容忍弱一致性）→ 优先弹性训练</li>
<li>精调 / 对齐（需要强一致性）→ 优先 Checkpoint 恢复</li>
</ul>
<p class="qa-summary">弹性训练和 Checkpoint 恢复不是互斥的，而是互补的——小故障弹性恢复，大故障 Checkpoint 兜底。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 设计一个 GPU 集群的故障自动恢复系统</div>
<div class="qa-a">
<pre><code>┌─────────────────────────────────────────────────────┐
│                   故障自动恢复系统                      │
├────────────┬────────────┬────────────┬──────────────┤
│  检测层     │  决策层     │  执行层     │  验证层      │
│            │            │            │             │
│ DCGM指标   │ 故障分类器  │ 节点隔离    │ 恢复验证     │
│ 心跳监控   │ 恢复策略    │ Pod 驱逐    │ 训练一致性   │
│ NCCL超时   │ 优先级排序  │ 弹性缩容    │ 指标回归     │
│ NPD事件    │ 并发控制    │ Checkpoint  │ 健康检查     │
│            │            │   恢复      │             │
└────────────┴────────────┴────────────┴──────────────┘</code></pre>
<p><strong>决策逻辑</strong>：</p>
<ol>
<li><strong>单卡故障</strong> → 弹性缩容（排除故障卡，继续训练）</li>
<li><strong>节点级故障</strong> → 弹性缩容 + 新节点调度（如果有空闲节点）</li>
<li><strong>网络分区</strong> → 缩小训练规模到同一分区内</li>
<li><strong>大规模故障（&gt; 50% 节点）</strong> → 暂停训练，等待恢复后 Checkpoint 重启</li>
</ol>
<p><strong>关键设计决策</strong>：故障分级（ECC 可纠正只记录，不可纠正才驱逐）；恢复优先级（小任务优先）；防抖动（连续 N 次检测失败才确认）；人工兜底。</p>
<p class="qa-summary">故障恢复系统的核心不是技术复杂度，而是决策逻辑——什么故障用什么策略，什么规模走什么流程，需要有清晰的分级响应机制。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何监控一个 GPU 集群？你会关注哪些指标？</div>
<div class="qa-a">
<p><strong>三层监控体系</strong>：</p>
<table>
<tr><th>层次</th><th>关注指标</th><th>工具</th></tr>
<tr><td><strong>基础设施层</strong></td><td>GPU 温度/ECC/功耗、NVLink 状态、InfiniBand 误码率、节点 CPU/内存/磁盘</td><td>DCGM Exporter + Node Exporter + IB Exporter</td></tr>
<tr><td><strong>训练层</strong></td><td>GPU 利用率、显存使用率、训练吞吐（samples/s）、损失曲线、通信占比</td><td>PyTorch Profiler + WandB + 自定义 Metric</td></tr>
<tr><td><strong>调度层</strong></td><td>队列等待时间、资源利用率、Pending Pod 数、抢占次数</td><td>Volcano/Kueue Metrics + Kubernetes Metrics</td></tr>
</table>
<p><strong>关键告警规则</strong>：GPU 温度 &gt; 85°C、ECC 不可纠正 &gt; 0、GPU 利用率 &lt; 10% 持续 5 分钟、NVLink CRC 持续增长、Pending Pod 超阈值、Loss NaN。</p>
<p class="qa-summary">GPU 监控的核心不是指标多，而是三层联动——硬件异常要能追溯到训练影响，训练瓶颈要能定位到硬件根因。</p>
</div>
</div>
