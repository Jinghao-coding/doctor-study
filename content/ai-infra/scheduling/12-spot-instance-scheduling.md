## 一句话结论

Spot/抢占式实例是云 GPU 成本优化的核心手段（便宜 60-80%），但会被随时回收（30s-2min 警告）。关键模式是"Checkpoint-on-Revocation"：检测回收信号 → 快速保存 checkpoint → 优雅终止 → 自动重新提交。分布式训练需要协调所有 Worker 同时 checkpoint，配合 Spot+On-Demand 混合部署、跨 AZ/实例类型分散来降低回收相关性，最终算清"Spot 便宜价格 - 重算浪费"是否真的划算。
<div class="card card-m">
<h3>云 GPU 经济学：为什么 Spot 便宜？</h3>
<p>云厂商的 IDC 里总有大量空闲计算资源（用户的 On-Demand 实例没跑满、预留实例没卖完、新购机器还没上架等），与其让这些资源空着耗电，不如便宜卖出去——但有个条件：<strong>当 On-Demand 用户需要资源时，Spot 实例可以被随时回收</strong>。这就是 Spot/Preemptible/抢占式实例的本质：<strong>用可被中断换取低价</strong>。</p>

<h4>价格对比（参考，随时间区域变动）</h4>
<table>
<tr><th>实例类型</th><th>A100 80GB 大概价格（小时）</th><th>相对 On-Demand</th><th>回收警告时间</th><th>是否会被回收</th></tr>
<tr><td>On-Demand（按需）</td><td>~$3.0-4.0</td><td>100%</td><td>N/A</td><td>不会（除非你欠费/违规）</td></tr>
<tr><td>Reserved/Commitment（预留）</td><td>~$1.8-2.4</td><td>60-70%（1-3年合约）</td><td>N/A</td><td>不会</td></tr>
<tr><td>Spot/Preemptible（抢占式）</td><td>~$0.8-1.5</td><td>20-40%</td><td>30s-2min</td><td>会，价格或容量变化时</td></tr>
</table>
<p><strong>关键数字</strong>：Spot 比 On-Demand 便宜 60-80%。如果能把重算浪费控制在 20% 以内，总成本只有 On-Demand 的 50% 甚至更低——这对大规模训练（几千卡跑几周）来说是百万级别的成本节省。</p>
</div>

<div class="card card-s">
<h3>Spot 回收机制：什么时候会被 kick 掉？</h3>

<h4>回收原因</h4>
<ol>
<li><strong>容量回收（Capacity Reclamation）</strong>：On-Demand 用户需要资源，Spot 实例被赶走。这是最常见原因，热门 GPU 类型（A100/H100）在白天业务高峰时容量紧张。</li>
<li><strong>价格超过出价</strong>：Spot 价格是浮动的（随供需变化），如果你的出价低于当前市场价格，实例会被回收。设置"出价 = On-Demand 价格"可以规避这个原因，只承担容量回收风险。</li>
<li><strong>硬件维护/退役</strong>：云厂商需要维护物理机时，Spot 实例优先被迁移/回收（On-Demand 通常会被热迁移）。</li>
</ol>

<h4>中断率参考</h4>
<p>不同实例类型、不同可用区（AZ）的中断率差异很大：</p>
<ul>
<li>热门 GPU（A100/H100）：5-20% 周中断率（一周内被回收的概率）</li>
<li>不那么热门的 GPU（如 T4、A10G、旧型号 V100）：1-5% 周中断率</li>
<li>CPU 实例：通常更低，1-10%</li>
<li>多个 AZ/多种实例类型混合：可以降低"同时被回收"的概率（协方差低）</li>
</ul>

<h4>回收信号检测</h4>
<table>
<tr><th>云厂商</th><th>回收警告机制</th><th>警告时间</th></tr>
<tr><td>AWS EC2 Spot</td><td>轮询 Instance Metadata Service (IMDS) <code>http://169.254.169.254/latest/meta-data/spot/instance-action</code>；也可以通过 EventBridge 事件通知</td><td>2 分钟</td></tr>
<tr><td>GCP Preemptible/Spot VM</td><td>发送 <code>SIGTERM</code> 信号给所有进程；也可以轮询 Metadata Server</td><td>30 秒（Preemptible）/ 即时后30秒（Spot 可变）</td></tr>
<tr><td>Azure Spot VM</td><td>轮询 Metadata Service <code>http://169.254.169.254/metadata/scheduledevents</code>；Scheduled Events 提前通知</td><td>30 秒</td></tr>
<tr><td>阿里云抢占式实例</td><td>实例元数据 + 云监控事件通知</td><td>1-5 分钟（可配置）</td></tr>
</table>
</div>

<div class="card card-m">
<h3>核心模式：Checkpoint-on-Revocation</h3>
<p>用 Spot 跑训练的标准工作流程：</p>
<pre><code>          ┌─────────────────────────────────────────┐
          │                                         │
          ▼                                         │
    提交训练 Job ──► 申请 Spot 实例 ──► 启动训练    │
          │                              │         │
          │                              ├─ 周期性 Checkpoint（每 N 分钟/step）
          │                              │         │
          │                              ▼         │
          │                     收到回收信号？──No──┘
          │                              │ Yes
          │                              ▼
          │                     触发紧急 Checkpoint
          │                              │
          │                              ▼
          │                     优雅终止（Cleanup）
          │                              │
          └──────────────────────────────┘
                                 自动重新提交</code></pre>

<h4>关键步骤详解</h4>

<h5>1. 信号检测与处理</h5>
<p>训练进程需要注册 SIGTERM 信号处理器（GCP）或启动一个后台线程轮询 Metadata（AWS/Azure）。一旦检测到回收信号：</p>
<ul>
<li>立即停止接受新的 batch</li>
<li>完成当前正在处理的 batch（不要在 step 中间保存，容易损坏 checkpoint）</li>
<li>触发 checkpoint 保存</li>
<li>Checkpoint 保存完成后，发送释放信号，让 Job 标记为失败/需要重启</li>
</ul>
<p><strong>重要</strong>：警告时间只有 30s-2min！Checkpoint 保存必须在这个时间内完成。HDFS/S3/对象存储上传大 checkpoint（几十 GB 到几百 GB）可能需要几分钟，因此：</p>
<ul>
<li>平时周期性 checkpoint 到本地 SSD/内存盘，紧急时只需要把最新 checkpoint 上传到共享存储</li>
<li>或者持续异步上传 checkpoint，紧急时只需要等当前上传完成</li>
<li>模型+优化器状态 checkpoint 做分片，多 Worker 并行写，加快保存速度</li>
</ul>

<h5>2. 周期性 Checkpoint 策略</h5>
<p>不能等回收信号来了才做第一次 checkpoint——需要平时就定期保存。Checkpoint 频率是一个 trade-off：</p>
<table>
<tr><th>Checkpoint 频率</th><th>丢失工作量</th><th>Checkpoint 开销</th><th>适用场景</th></tr>
<tr><td>每 1 小时</td><td>平均 30 分钟重算</td><td>低</td><td>中断率低、checkpoint 很大（如大模型训练）</td></tr>
<tr><td>每 15 分钟</td><td>平均 7.5 分钟重算</td><td>中</td><td>大多数场景</td></tr>
<tr><td>每 5 分钟</td><td>平均 2.5 分钟重算</td><td>高</td><td>中断率高、checkpoint 小、单步计算代价高</td></tr>
</table>
<p><strong>经验公式</strong>：选择 checkpoint 间隔，使得"checkpoint 保存开销"约等于"预期丢失重算开销"——<code>保存时间 ≈ (1/中断率) 内的平均丢失时间</code>。但实际上，大多数团队直接配置为每 10-30 分钟，或按 step 数（如每 1000 step）。</p>

<h5>3. 自动重试机制</h5>
<p>Checkpoint 保存后，Job 应该由调度器/工作流管理器（如 Argo Workflows、KubeFlow、Volcano Job、Airflow）自动重新提交，从最新 checkpoint 恢复。重启时可能需要：</p>
<ul>
<li>申请新的 Spot 实例（可能换 AZ、换实例类型）</li>
<li>加载 checkpoint 到新实例</li>
<li>重建数据加载器、NCCL 通信组</li>
<li>继续训练</li>
</ul>
<p>不要让人工介入——Spot 回收是常态，必须完全自动化。</p>
</div>

<div class="card card-d">
<h3>分布式训练的 Spot 容错策略</h3>
<p>单卡训练的 Checkpoint-on-Revocation 很简单，但分布式训练（多机多卡）要复杂得多：<strong>一个 Worker 被回收，整个 Job 都要停</strong>（因为 NCCL 通信环断了，所有 Worker 都会 hang 或 crash）。</p>

<h4>策略一：协调 Checkpoint（Elastic Training 弹性训练）</h4>
<p>标准做法：</p>
<ol>
<li>任意一个 Worker 检测到回收信号，立即通知所有其他 Worker（通过 NCCL 带外通信、共享存储标记、或 rendezvous 服务）</li>
<li>所有 Worker 同步停止训练，在当前 step 边界共同保存 checkpoint</li>
<li>所有 Worker 优雅退出</li>
<li>Job 控制器自动重新提交，申请新的 Worker（数量可能相同也可能不同，弹性训练支持 world size 变化）</li>
<li>新的 Worker 组加载 checkpoint，重新初始化，继续训练</li>
</ol>
<p><strong>框架支持</strong>：</p>
<ul>
<li><strong>PyTorch</strong>：TorchElastic（<code>torchrun</code>）原生支持弹性训练，Worker 变化时自动 rendezvous 重启</li>
<li><strong>DeepSpeed</strong>：支持 checkpoint 分片保存和恢复，配合弹性训练可以处理 Worker 增减</li>
<li><strong>Megatron-LM</strong>：有自己的 checkpoint 和容错机制</li>
<li><strong>JAX/Flax</strong>：通过 Orbax 等库做 checkpoint</li>
</ul>

<h4>策略二：Spot + On-Demand 混合部署</h4>
<p>把<strong>关键节点放在 On-Demand</strong>，<strong>Worker 用 Spot</strong>：</p>
<ul>
<li>Parameter Server / Coordinator / Scheduler：On-Demand，永远不回收——这些节点挂了整个集群状态丢失，代价最大</li>
<li>训练 Worker：Spot，可以被回收，回收后只需要 Worker 组重建</li>
<li>混合 Gang Scheduling：允许部分 Gang 用 Spot，容忍一定的 Worker 流失</li>
</ul>
<p>更极端一点：关键 Rank（如 Rank 0，负责 checkpoint 保存、日志、coordination）放 On-Demand，其余 Worker 放 Spot。Rank 0 不丢，checkpoint 机制就更可靠。</p>

<h4>策略三：Spot Fleet / 多实例类型分散</h4>
<p>"不要把鸡蛋放在一个篮子里"：</p>
<ol>
<li><strong>跨可用区（AZ）</strong>：在多个 AZ 申请实例，不同 AZ 的容量回收是不相关的——所有 AZ 同时回收的概率极低</li>
<li><strong>跨实例类型</strong>：不要只申请 A100，同时申请 A100-80G、A100-40G（如果模型放得下）、甚至 A10G 做混合部署，不同实例类型的回收不相关</li>
<li><strong>Spot Fleet / Auto Scaling Group</strong>：配置云厂商的 Spot Fleet，自动在多个实例类型/AZ 中选最便宜最可用的组合</li>
</ol>
<p><strong>弹性训练的好处</strong>：如果支持弹性 world size，那么不需要等所有 Worker 都回来——只要拿到足够多的新 Spot 实例，就可以恢复训练（world size 变小，吞吐降低，但至少训练继续，不会空等）。</p>

<h4>策略四：出价策略</h4>
<p>简单但有效：<strong>把 Spot 出价设为 On-Demand 价格</strong>。这样不会因为价格上涨被回收，只会因为容量不足被回收。容量回收是真的资源不够，价格问题只是你出价不够高——用 On-Demand 价格出价可以消除价格因素导致的回收，剩下的只有容量回收，中断率会明显降低。</p>
<p>毕竟 Spot 价格到 On-Demand 的时候，不如直接用 On-Demand 了。</p>
</div>

<div class="card card-s">
<h3>推理服务能跑在 Spot 上吗？</h3>
<p><strong>结论：在线推理不建议直接用 Spot，但离线批处理推理/异步推理可以</strong>。</p>

<h4>为什么在线推理难用 Spot？</h4>
<ul>
<li><strong>延迟 SLO</strong>：在线推理有严格的延迟 SLO（P99 < 几百 ms），Spot 被回收时 2 分钟内实例就没了——正在处理的请求会失败，新请求无法路由</li>
<li><strong>冷启动开销</strong>：加载大模型（LLM 几十 GB）需要几十秒到几分钟，新实例启动后不能立刻接流量</li>
<li><strong>KV Cache 丢失</strong>：推理实例的 KV Cache 都在本地 GPU 内存里，实例回收后 Cache 全丢，新实例需要重建</li>
</ul>

<h4>什么推理场景可以用 Spot？</h4>
<ol>
<li><strong>离线批处理推理 / Batch Inference</strong>：比如"晚上把昨天的日志全部过一遍模型"、"给 1 亿张图片打标签"。这种任务没有严格延迟要求，可以拆分、可以重试、可以 checkpoint 进度，和训练一样——非常适合 Spot。</li>
<li><strong>异步推理 / 消息队列驱动</strong>：请求进队列，Worker 从队列取处理，Worker 挂了请求不丢，重新入队给其他 Worker 处理。只要队列保留足够长的时间，Spot 挂了不丢请求。</li>
<li><strong>Warm Pool Standby 热备</strong>：主要容量用 On-Demand，额外用 Spot 实例做"额外算力"处理突发流量。Spot 被回收时，On-Demand 容量还在，只是降容不宕机。Spot 加进来提升吞吐，被回收时 graceful drain，把正在处理的请求处理完再退出。</li>
</ol>

<h4>Spot + On-Demand 混合推理策略</h4>
<pre><code>                    ┌─────────────────────┐
                    │  Load Balancer      │
                    └─────────┬───────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     ┌─────────────────┐             ┌─────────────────┐
     │ On-Demand 池    │             │ Spot 池         │
     │ （基础容量）    │◄────────────┤ （弹性突发容量）│
     │ 永远在线        │   回收时    │ 处理多余流量    │
     │ 保证 SLO        │   drain     │ 挂了不影响服务  │
     └─────────────────┘             └─────────────────┘</code></pre>
<p>On-Demand 承载保底流量（如按历史 P50 流量预留），Spot 承载流量尖峰。Spot 实例收到回收信号时，停止接新请求，处理完正在处理的请求后退出——这需要服务支持 graceful shutdown 和连接 draining（K8s 有 preStop hook + readinessProbe 可以做）。</p>
</div>

<div class="card card-s">
<h3>Kubernetes 集成：Kueue/Karpenter/Descheduler</h3>
<p>在 K8s 上用 Spot GPU 需要几个组件配合：</p>

<h4>1. 节点标签与污点（Taint/Toleration）</h4>
<p>Spot 节点应该被标记 capacity-type=spot 并加上污点，避免不支持容错的工作负载误调度上来：</p>
<pre><code>nodeSelector:
  node.kubernetes.io/instance-type: p4d.24xlarge  # A100
  karpenter.sh/capacity-type: spot                 # Spot 实例
tolerations:
- key: "karpenter.sh/capacity-type"
  operator: "Equal"
  value: "spot"
  effect: "NoSchedule"</code></pre>

<h4>2. Karpenter：自动扩缩容 Spot 节点</h4>
<p>Karpenter 是 AWS 开源的 K8s 节点自动扩缩容工具（替代 Cluster Autoscaler），可以：</p>
<ul>
<li>根据待调度 Pod 的需求，自动申请最合适的 Spot 实例类型（在用户配置的多实例类型中选最可用最便宜的）</li>
<li>自动处理 Spot 节点回收——收到中断通知后自动 cordon + drain，把 Pod 驱逐到其他节点</li>
<li>支持 Spot diversification（跨实例类型/AZ 分散）</li>
</ul>
<p>Karpenter 配置示例：</p>
<pre><code>requirements:
- key: karpenter.sh/capacity-type
  operator: In
  values: ["spot", "on-demand"]  # 优先 Spot，不行 fallback On-Demand
- key: node.kubernetes.io/instance-type
  operator: In
  values: ["p4d.24xlarge", "p4de.24xlarge", "p3dn.24xlarge"]  # 多实例类型</code></pre>

<h4>3. Kueue：队列级 Spot 管理与 Preemption</h4>
<p>Kueue 通过 ClusterQueue 和 ResourceQuota 管理 Spot/On-Demand 配额：</p>
<ul>
<li>把 Spot 资源作为一个独立的 resource flavor，有自己的配额</li>
<li>支持 Preemption：当集群资源紧张、或 On-Demand 有更高优先级任务需要资源时，可以抢占 Spot 任务</li>
<li>Reclaimable Spot：Spot 任务被抢占时自动 checkpoint 并重新排队</li>
</ul>

<h4>4. Pod 优雅终止：preStop Hook</h4>
<p>Pod 被驱逐时（无论是 Spot 回收还是抢占），K8s 会发 SIGTERM，然后等 <code>terminationGracePeriodSeconds</code> 后强杀（SIGKILL）。给训练 Pod 配置足够的优雅终止时间：</p>
<pre><code>terminationGracePeriodSeconds: 300  # 给 5 分钟做 checkpoint 和 cleanup
containers:
- name: trainer
  lifecycle:
    preStop:
      exec:
        command: ["/bin/sh", "-c", "python /scripts/trigger_checkpoint_and_wait.py"]</code></pre>
<p>preStop 脚本执行 checkpoint 并等待保存完成，然后退出；退出后 K8s 才会删除 Pod。</p>

<h4>5. Descheduler：主动 Spot 驱逐</h4>
<p>Descheduler 可以根据策略主动驱逐 Pod，比如：</p>
<ul>
<li>Spot 价格上涨时主动驱逐，换更便宜的实例</li>
<li>低优先级 Spot 任务占着资源，高优任务来了需要让位置</li>
<li>节点利用率过低时，迁移 Pod 到其他节点缩容</li>
</ul>
</div>

<div class="card card-d">
<h3>成本模型：Spot 真的划算吗？Break-Even 分析</h3>
<p>Spot 不是稳赚不赔——被回收后要重算，重算浪费时间和钱。算一下 break-even：</p>

<pre><code>总成本(Spot) = Spot 单价 × 运行时间 × (1 + 浪费率 Waste Ratio)
总成本(On-Demand) = On-Demand 单价 × 运行时间

当 总成本(Spot) &lt; 总成本(On-Demand) 时划算：
  Spot 单价 × (1 + Waste Ratio) &lt; On-Demand 单价
  1 + Waste Ratio &lt; On-Demand / Spot 单价
  Waste Ratio &lt; (On-Demand / Spot 单价) - 1</code></pre>

<p><strong>数值例子</strong>：On-Demand = $3/h，Spot = $1/h（3折）：</p>
<table>
<tr><th>Waste Ratio（重算浪费比例）</th><th>实际每小时成本</th><th>vs On-Demand</th></tr>
<tr><td>0%（完全不浪费）</td><td>$1.00</td><td>省 67%</td></tr>
<tr><td>20%</td><td>$1.20</td><td>省 60%</td></tr>
<tr><td>50%</td><td>$1.50</td><td>省 50%</td></tr>
<tr><td>100%</td><td>$2.00</td><td>省 33%</td></tr>
<tr><td>200%</td><td>$3.00</td><td>持平</td></tr>
<tr><td>&gt;200%</td><td>&gt;$3.00</td><td>亏了</td></tr>
</table>
<p><strong>结论</strong>：当 Spot 是 On-Demand 的 1/3 价格时，只要浪费率不超过 200%（平均每次回收导致重算 2 倍已运行时间），就比 On-Demand 划算。实践中，如果 checkpoint 频率合理（15-30 分钟）、重启自动化，waste ratio 通常在 5-30%，Spot 非常划算。</p>

<h4>浪费率估算</h4>
<p>Waste Ratio 取决于：</p>
<ul>
<li><strong>Checkpoint 间隔</strong>：最坏情况丢失 checkpoint 间隔内的全部计算，平均丢失间隔/2</li>
<li><strong>Checkpoint 保存开销</strong>：保存 checkpoint 本身花的时间（读写共享存储）</li>
<li><strong>重启开销</strong>：重新申请实例、加载模型、重建 NCCL 通信组、数据加载器 warm-up 的时间（通常 1-10 分钟）</li>
<li><strong>中断频率</strong>：越频繁被回收，重启和 checkpoint 开销占比越高</li>
</ul>
<p><strong>公式近似</strong>：<code>Waste Ratio ≈ (MTTR / MTTF) + (Checkpoint时间 / Checkpoint间隔)</code>，其中 MTTR 是平均修复/重启时间，MTTF 是平均无故障时间（平均多久被回收一次）。</p>
</div>

<div class="card card-w">
<h3>风险矩阵：什么任务适合跑 Spot？</h3>
<table>
<tr><th>任务类型</th><th>Spot 适用性</th><th>原因</th><th>建议</th></tr>
<tr><td>开发/实验 Job（&lt;1小时）</td><td>✅ 非常适合</td><td>运行时间短，被回收概率低（MTTF 通常几小时到几天），就算被回收重跑代价也小</td><td>直接用 Spot，甚至可以不用 checkpoint</td></tr>
<tr><td>中小规模训练（几小时到1天）</td><td>✅ 适合</td><td>Checkpoint 做好，重启几次也能跑完，成本节省明显</td><td>周期性 checkpoint + 自动重试</td></tr>
<tr><td>分布式训练（多机多卡）</td><td>⚠️ 需要改造</td><td>一个 Worker 挂全 Job 重启，协调 checkpoint 复杂，但成本节省巨大</td><td>弹性训练 + 关键节点 On-Demand + 多 AZ/实例类型分散</td></tr>
<tr><td>大规模生产训练（几天到几周，千卡）</td><td>⚠️ Spot+On-Demand 混合</td><td>全 Spot 风险太高（每天都可能被回收几次，重启开销大），全 On-Demand 太贵</td><td>关键 Rank/PS 用 On-Demand，Worker 用 Spot 混搭；或者按比例 30% On-Demand + 70% Spot</td></tr>
<tr><td>在线推理服务（有严格 SLO）</td><td>❌ 不适合直接用</td><td>回收导致请求失败、冷启动慢、SLO 无法保证</td><td>用 On-Demand 做基础容量，Spot 做弹性突发</td></tr>
<tr><td>离线批处理推理</td><td>✅ 非常适合</td><td>没有严格延迟，可以拆任务、重试、checkpoint 进度</td><td>直接用 Spot，配合任务队列</td></tr>
<tr><td>异步/队列驱动推理</td><td>✅ 适合</td><td>请求不丢，Worker 挂了重入队</td><td>MQ 保证消息不丢，Spot 作为 Worker 池</td></tr>
</table>

<div class="card-r">
<h4>Spot 反模式（不要这么做）</h4>
<ul>
<li><strong>没有 checkpoint 就跑长训练</strong>：一被回收几天进度没了，浪费的算力比 Spot 省的钱多得多</li>
<li><strong>所有 Worker 只在一个 AZ/一个实例类型</strong>：这个 AZ/实例类型容量紧张时，所有 Worker 同时被回收，Job 完全中断</li>
<li><strong>Checkpoint 只写本地盘</strong>：实例被回收本地盘也没了，checkpoint 白做了；checkpoint 必须写共享持久存储（S3/HDFS/NFS/EFS）</li>
<li><strong>Checkpoint 保存时间比警告时间长</strong>：30 秒警告但 checkpoint 要存 5 分钟，最后 SIGKILL 来了 checkpoint 没存完，文件损坏</li>
<li><strong>单 Worker 挂了不处理，等所有 Worker 都超时</strong>：一个 Spot 被回收，其他 Worker 空等 NCCL 超时（可能 30 分钟），浪费算力；应该有快速失败机制</li>
</ul>
</div>
</div>

<div class="card card-m">
<h3>Spot 实例调度面试问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Spot 实例被回收了训练怎么办？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">标准流程：Checkpoint-on-Revocation</div><ol>
<li><strong>检测回收信号</strong>：GCP 收 SIGTERM，AWS/Azure 轮询 Metadata Service 或事件通知，警告时间 30s-2min。</li>
<li><strong>优雅停止</strong>：停止接新 batch，完成当前 step（不要在 step 中间保存，避免 checkpoint 损坏）。</li>
<li><strong>紧急保存 Checkpoint</strong>：把模型权重、优化器状态、训练进度（epoch/step、数据加载器位置、随机种子等）保存到持久共享存储（S3/HDFS/EFS），不能写本地盘。</li>
<li><strong>Cleanup 退出</strong>：释放资源，通知调度器/Job 控制器这个 Job 中断了。</li>
<li><strong>自动重新提交</strong>：工作流系统（Argo/KubeFlow/Volcano）检测到 Job 失败，自动重新提交，申请新实例。</li>
<li><strong>恢复训练</strong>：新实例加载最新 checkpoint，重建数据加载器、NCCL 通信组，从 checkpoint 的 step 继续训练。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">关键细节</div><p>(1) 平时必须做周期性 checkpoint（每 10-30 分钟），不能等回收信号才第一次存——回收了进度全丢。(2) Checkpoint 保存必须在警告窗口内完成，大 checkpoint 做分片多进程并行写、本地 SSD 缓存、异步上传。(3) 整个流程必须完全自动化，不需要人工介入。</p></div>
<div class="qa-summary">面试要点：按"信号检测 → 优雅停 → Checkpoint → 重试 → 恢复"流程讲，提周期性 checkpoint、持久存储、自动化这几个关键点。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 分布式训练怎么应对 spot 回收？一个 Worker 挂了怎么办？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">问题本质</div><p>分布式训练（数据并行/张量并行）NCCL 通信是 all-reduce/all-gather 等集合通信，一个 Worker 挂了通信环断了，其他所有 Worker 会 hang 或 crash——单卡的"自己 checkpoint 自己重启"不够，需要协调所有 Worker。</p></div>
<div class="qa-section"><div class="qa-section-title">核心策略</div><ol>
<li><strong>协同 Checkpoint + 弹性训练</strong>：任何一个 Worker 检测到回收信号，立即通知所有 Rank（通过带外通信、共享存储标记、或 rendezvous）；所有 Worker 同步在 step 边界共同保存分片 checkpoint，然后一起退出；Job 控制器自动重新提交，新的 Worker 组 rendezvous、加载 checkpoint、恢复训练。框架用 TorchElastic、DeepSpeed、Megatron 的弹性训练能力支持 world size 变化。</li>
<li><strong>关键节点 On-Demand，Worker Spot 混合</strong>：Coordinator/Rank 0/Parameter Server 放 On-Demand 不回收（这些节点状态最关键），计算 Worker 用 Spot；Rank 0 负责 checkpoint 协调，它不丢整个 checkpoint 流程更可靠。</li>
<li><strong>多 AZ/多实例类型分散</strong>：Spot Fleet 在多个可用区、多个兼容实例类型（如 A100-40G/80G、甚至跨代）分散申请，降低同时被回收的概率——不同 AZ 的容量是独立的。</li>
<li><strong>出价 = On-Demand 价格</strong>：消除因价格上涨导致的回收，只承担真正的容量回收风险，中断率降低。</li>
<li><strong>快速失败机制</strong>：不要等 NCCL 默认超时（通常 30 分钟），检测到一个 Worker 失联后快速触发全 Job 停止和 checkpoint，减少空等浪费。</li>
</ol></div>
<div class="qa-summary">面试要点：先说分布式的特殊性（一个挂全挂），然后按"协同checkpoint + 混合部署 + 分散风险 + 快速失败"四个策略讲，提 TorchElastic 等框架支持。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Spot 和 on-demand 比例怎么定？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心 trade-off</div><p>Spot 便宜但会被回收（需要重算），On-Demand 贵但稳定。比例取决于：(1) 任务对中断的容忍度（checkpoint 做得好不好、重启开销大不大）；(2) 训练时长；(3) 业务对完成时间确定性的要求。</p></div>
<div class="qa-section"><div class="qa-section-title">经验比例</div><table>
<tr><th>场景</th><th>On-Demand 比例</th><th>Spot 比例</th><th>原因</th></tr>
<tr><td>开发实验（短，可重跑）</td><td>0%</td><td>100%</td><td>跑的时间短，被回收概率低；就算回收了重跑代价小，不需要保留 On-Demand</td></tr>
<tr><td>中小规模训练（几小时-1天）</td><td>0-20%</td><td>80-100%</td><td>Checkpoint 做好，重启几次也能跑完，全 Spot 最省成本</td></tr>
<tr><td>大规模分布式训练（几天-几周，千卡）</td><td>20-40%</td><td>60-80%</td><td>关键节点（Rank 0/PS/Coordinator）必须 On-Demand；计算 Worker 混合；全 Spot 风险太高，重启开销太大影响总完工时间</td></tr>
<tr><td>有截止日期的生产训练</td><td>40-60%</td><td>40-60%</td><td>不能无限等重启，需要足够的 On-Demand 容量保证进度稳定，Spot 作为加速补充</td></tr>
<tr><td>在线推理</td><td>100%（基础）+ 0-50% Spot（弹性）</td><td>只用 On-Demand 保底，Spot 做突发</td><td>SLO 不能破，Spot 挂了 On-Demand 还能服务</td></tr>
</table></div>
<div class="qa-section"><div class="qa-section-title">成本 break-even 计算</div><p>实际选择时算一下账：假设 Spot 3折，重算浪费 20%，那么 Spot 实际成本是 On-Demand 的 0.3 × 1.2 = 36%——省 64%。如果 On-Demand 占 30%、Spot 占 70%，平均成本是 0.3×100% + 0.7×36% ≈ 55%——相当于全 On-Demand 打 5.5 折，同时风险可控。</p><p>如果训练很重要怕 Spot 中断影响交付时间，可以预留 100% On-Demand 作为"保底资源池"——On-Demand 跑基础进度，有额外 Spot 就加进去加速，Spot 回收了不影响 On-Demand 继续跑（弹性训练缩容）。</p></div>
<div class="qa-summary">面试要点：分场景给比例，讲清 trade-off，用成本 break-even 数字说话，不要给固定答案。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 推理服务可以用 spot 吗？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">结论：分场景</div><p><strong>有严格延迟 SLO 的在线推理不建议直接跑 Spot</strong>，但<strong>离线批推理、异步推理可以</strong>，<strong>在线推理可以用 Spot 做弹性补充但不能做主力</strong>。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么在线推理直接用 Spot 不行？</div><p>(1) <strong>SLO 无法保证</strong>：Spot 被回收时 2 分钟内就没了，正在处理的请求直接失败，新请求无法路由；(2) <strong>冷启动慢</strong>：LLM 几十 GB 模型加载到 GPU 需要几十秒到几分钟，新实例不能立刻接流量；(3) <strong>KV Cache 丢失</strong>：本地 KV Cache 全丢，即使流量切走，新实例没有 Cache 性能下降。</p></div>
<div class="qa-section"><div class="qa-section-title">哪些推理场景可以用 Spot？</div><ol>
<li><strong>离线 Batch Inference</strong>：如"夜间批量跑昨日数据推理"、"给数据集打标签"——没有延迟要求，可以拆分、重试、checkpoint 进度，和训练一样，完全适合 Spot。</li>
<li><strong>异步/消息队列推理</strong>：请求先进 MQ（Kafka/RabbitMQ），Worker 从队列消费处理，结果异步返回。Worker 挂了请求不丢，重新入队给其他 Worker；Spot 作为 Worker 池非常合适。</li>
<li><strong>在线推理 Spot 弹性池（Warm Pool）</strong>：主力容量用 On-Demand 保证 SLO（按 P50-P70 流量预留），额外用 Spot 实例处理流量尖峰。Spot 收到回收信号时，先从 LB 摘流量（readiness fail），处理完正在处理的请求（graceful connection draining），再退出。Spot 加进来提升吞吐，被回收时只是降容不宕机。</li>
</ol></div>
<div class="qa-summary">面试要点：不要直接说"可以"或"不可以"，要分三种场景（在线SLO/离线batch/弹性补充）分别回答，讲清楚每种场景的原因和做法。</div>
</div>
</div>
</div>

## 关联模块

- `批处理与 Gang 调度`：Gang Scheduling、Backfill，分布式作业调度
- `Kubernetes 调度器扩展`：Preemption、PriorityClass、调度框架，K8s 抢占与驱逐
- `分布式训练容错`：Checkpoint、弹性训练、故障恢复
- `集群管理：容错`：更广泛的容错机制设计
