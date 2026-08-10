<div class="card card-m">
<h3>NCCL：GPU 集合通信的事实标准</h3>
<p>NCCL 负责 GPU 间高效集合通信，常见于 DDP 梯度同步、TP 层内通信、MoE expert routing 等场景。分布式训练排障里，NCCL 往往是最关键也最难定位的一层。</p>
</div>

<div class="card card-s">
<h3>常见集合通信语义</h3>
<table>
<tr><th>操作</th><th>语义</th><th>训练场景</th></tr>
<tr><td>AllReduce</td><td>所有 rank 的数据归约后广播给所有 rank</td><td>DDP 梯度同步</td></tr>
<tr><td>ReduceScatter</td><td>归约后按 rank 分片</td><td>ZeRO/FSDP 梯度分片</td></tr>
<tr><td>AllGather</td><td>收集所有 rank 的分片到每个 rank</td><td>ZeRO-3/FSDP 参数按需 gather</td></tr>
<tr><td>Broadcast</td><td>一个 rank 发送给所有 rank</td><td>初始化参数、同步状态</td></tr>
<tr><td>All-to-All</td><td>每个 rank 给每个 rank 发送不同分片</td><td>MoE expert parallel</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Ring vs Tree</h3>
<table>
<tr><th>算法</th><th>优势</th><th>劣势</th><th>适合场景</th></tr>
<tr><td>Ring</td><td>带宽利用高，链路均匀</td><td>延迟随 rank 数增加</td><td>大 tensor AllReduce</td></tr>
<tr><td>Tree</td><td>延迟更低</td><td>带宽利用可能不如 ring</td><td>小 tensor、rank 数多</td></tr>
<tr><td>Hierarchical</td><td>节点内/节点间分层优化</td><td>实现复杂，依赖拓扑识别</td><td>多节点多 GPU 训练</td></tr>
</table>
</div>

<div class="card card-w">
<h3>通信时间粗估</h3>
<p>通信瓶颈可以用“数据量 / 有效带宽”粗估：</p>
<div class="formula">$$\text{Communication Time} \approx \frac{\text{Traffic}}{\text{Effective Bandwidth}}$$</div>
<p>例如每卡 AllReduce 流量 49GB，有效带宽 100GB/s，则裸通信时间约：</p>
<div class="formula">$$49 \text{GB} / 100 \text{GB}/s = 0.49 s$$</div>
<p>实际还要加上启动延迟、拓扑、协议栈、拥塞、NCCL 算法选择和通信计算重叠效果。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: NCCL 训练 hang 了，应该怎么排查？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先区分是某个 rank 先失败还是所有 rank 卡在通信，再从日志、网络、拓扑、环境变量逐层排查。</p>
<div class="qa-section"><div class="qa-section-title">1. 看 rank 是否一致进入 collective</div><p>集合通信要求所有 rank 按相同顺序调用。如果某个 rank OOM、数据读取失败或提前退出，其他 rank 会卡在 NCCL 调用里。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 打开 NCCL 日志</div><p>常用环境变量：</p><pre><code class="language-bash">export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=INIT,NET,COLL
export TORCH_DISTRIBUTED_DEBUG=DETAIL</code></pre></div>
<div class="qa-section"><div class="qa-section-title">3. 检查网络与设备</div><p>确认 IB/RDMA 设备可见、网卡选择正确、端口互通、容器权限和 device plugin 注入正常。</p></div>
<div class="qa-summary">面试口径：NCCL hang 常常不是 NCCL 本身错，而是 rank 顺序不一致、某 rank 先失败、网络或设备不可用。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 MoE 的 All-to-All 比 DDP AllReduce 更难优化？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>对比通信模式、流量分布和负载均衡。</p>
<div class="qa-section"><div class="qa-section-title">1. AllReduce 数据模式规则</div><p>AllReduce 通常每个 rank 发送相同大小梯度，通信模式规则，容易用 ring/tree 做优化。</p></div>
<div class="qa-section"><div class="qa-section-title">2. All-to-All 更依赖路由分布</div><p>MoE 中 token 被路由到不同专家，某些专家可能热门，导致不同 rank 发送/接收数据不均衡。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 对全网带宽要求高</div><p>All-to-All 需要更高 bisection bandwidth；拓扑不均衡、交换机拥塞、跨机房部署都会放大性能问题。</p></div>
<div class="qa-summary">面试口径：All-to-All 难在不规则、全互联、负载不均衡；它比规则 AllReduce 更吃拓扑和路由质量。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: NCCL 常见环境变量有哪些？面试中怎么说？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>不要背一堆变量名，要按用途分类。</p>
<div class="qa-section"><div class="qa-section-title">1. 日志诊断</div><p><code>NCCL_DEBUG=INFO</code>、<code>NCCL_DEBUG_SUBSYS=INIT,NET,COLL</code> 用于看初始化、网络选择和 collective 信息。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 网卡选择</div><p><code>NCCL_SOCKET_IFNAME</code>、<code>NCCL_IB_HCA</code> 用于限制 NCCL 选择哪些网卡，避免走错 docker0、lo 或低速网卡。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 功能开关</div><p><code>NCCL_IB_DISABLE</code>、<code>NCCL_P2P_DISABLE</code> 可用于隔离 RDMA/P2P 问题，但生产不应长期关闭高性能路径。</p></div>
<div class="qa-summary">面试口径：NCCL 环境变量按日志、网卡选择、功能开关三类记，核心是帮助判断走了哪条通信路径。</div>
</div>
</div>
