## 一句话结论

scheduler cache、assume、binding cycle 和 preemption 是理解调度一致性和抢占的关键。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Kubernetes 核心 |
| 章节类型 | 系统类 |
| 解决问题 | 围绕控制面、调度资源模型、Workload Controller、网络存储、安全多租户、排障和 AI Infra GPU/DRA 建立平台面试答案。 |
| 面试抓手 | 不要只讲算法，必须讲缓存状态和绑定路径。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m">
<h3>调度问题定位：区分 Pod 属性、调度阶段和调度机制</h3>
<p>在分析 Kubernetes Scheduler 时，需要区分三类概念，<strong>这三类概念不能混在一起</strong>：</p>
<ol>
<li><strong>Pod 属性：</strong>Pod 自身携带的信息，例如优先级、资源请求、节点选择约束等。</li>
<li><strong>调度阶段 / 扩展点：</strong>Scheduler Framework 中处理 Pod 的流程位置，例如 QueueSort、Filter、Score、Reserve、Permit。</li>
<li><strong>调度机制 / 策略：</strong>由多个阶段共同完成的行为，例如抢占、退避重试、Gang 调度、回填调度等。</li>
</ol>
<p>例如，<code>priority</code> 是 Pod 的属性，它会影响队列排序和抢占，但它本身不是调度阶段。<code>Preemption</code> 是调度失败后的抢占机制，通常发生在没有可行节点之后，和 <code>PostFilter</code> 等流程有关，但它也不是普通的节点打分阶段。<code>QueueSort</code>、<code>Filter</code>、<code>Score</code>、<code>Reserve</code>、<code>Permit</code> 才是 Scheduler Framework 中更明确的扩展点。</p>
</div>

<div class="card card-s">
<h3>三类概念对照表</h3>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:140px">类型</th><th>示例</th><th>说明</th></tr>
</thead>
<tbody>
<tr><td class="q-dim">Pod 属性</td><td><code>priority</code>、<code>resource requests</code>、<code>nodeSelector</code>、<code>affinity</code>、<code>tolerations</code>、<code>preemptionPolicy</code></td><td>描述 Pod 自身需求或调度约束，<strong>不是调度阶段</strong></td></tr>
<tr><td class="q-dim">调度阶段 / 扩展点</td><td>QueueSort、PreFilter、Filter、PostFilter、Score、Reserve、Permit、Bind、Unreserve</td><td>Scheduler Framework 中的处理流程，<strong>可以开发插件扩展</strong></td></tr>
<tr><td class="q-dim">调度机制 / 策略</td><td>Preemption、Backoff、UnschedulableQ 重新入队、Gang Scheduling、Backfill、Quota 管理</td><td>通常横跨多个阶段，<strong>不一定对应单一扩展点</strong></td></tr>
</tbody>
</table>
</div>
</div>

<div class="card card-d">
<h3>常见问题应该从哪里定位</h3>
<div class="queue-compare">
<table>
<thead>
<tr><th style="width:160px">问题</th><th style="width:100px">本质</th><th style="width:160px">主要涉及的调度阶段</th><th>相关 Pod 属性 / 机制</th><th>说明</th></tr>
</thead>
<tbody>
<tr><td>高优先级 Pod 长时间没被调度</td><td>Pod 没有及时获得调度机会，或资源被低优任务占住</td><td>QueueSort、PostFilter</td><td><strong>Pod 属性：</strong>priority<br><strong>机制：</strong>Preemption</td><td>priority 影响队列排序和抢占；如果 Pod 未出队，先看 QueueSort；如果出队后无节点可放，再看抢占</td></tr>
<tr><td>Pod 反复扫描大量节点但失败</td><td>失败 Pod 被无效重新入队</td><td>SchedulingQueue、PreFilter、Filter</td><td><strong>机制：</strong>Backoff、UnschedulableQ、事件提示</td><td>应优化重新入队条件，避免无关事件唤醒无关 Pod</td></tr>
<tr><td>短作业被大作业队头阻塞</td><td>出队顺序不合理</td><td>QueueSort</td><td><strong>机制：</strong>Backfill、多队列</td><td>小作业没机会出队时，Score 不会生效</td></tr>
<tr><td>GPU 拓扑放置不合理</td><td>节点或设备组合选择不好</td><td>Filter、Score、Reserve</td><td><strong>Pod 属性：</strong>resource requests、nodeAffinity、GPU topology</td><td>Pod 已进入调度周期，问题是放到哪里和怎么预留设备</td></tr>
<tr><td>Gang 任务部分 Pod 占住资源但整体无法启动</td><td>缺少整组准入与失败回滚</td><td>Reserve、Permit、Unreserve</td><td><strong>机制：</strong>Gang Scheduling、PodGroup</td><td>需要整组 Pod 要么一起放行，要么一起回滚</td></tr>
<tr><td>高优任务无节点可放，但低优任务占着资源</td><td>资源不足，需要让低优任务让路</td><td>PostFilter</td><td><strong>Pod 属性：</strong>priority、preemptionPolicy<br><strong>机制：</strong>Preemption</td><td>没有可行节点时，Score 没意义，需要抢占制造可行节点</td></tr>
</tbody>
</table>
</div>
<div class="qa-summary">面试表达技巧：先区分"这是 Pod 属性问题、调度阶段问题还是调度机制问题"，再定位到具体扩展点或策略。不要把 priority 说成"调度阶段"，也不要把 Preemption 说成"打分的一部分"。</div>
</div>

<div class="card card-w">
<h3>Scheduler Cache 与 Assume 机制</h3>
<p>scheduler 不会每调度一个 Pod 都从 API Server 重新拉全量 Node 和 Pod。它维护本地 cache，并在调度周期开始时生成 snapshot。选中节点后，scheduler 会先在本地 cache 中 assume 该 Pod 已经占用资源，然后异步绑定。</p>
<table>
<tr><th>机制</th><th>解决什么问题</th><th>风险</th></tr>
<tr><td>NodeInfo</td><td>缓存节点资源、Pod、镜像、本地状态</td><td>cache 与 API Server 存在短暂不一致</td></tr>
<tr><td>Snapshot</td><td>给一个调度周期提供稳定视图</td><td>不是强一致，只是调度器本地视角</td></tr>
<tr><td>Assumed Pod</td><td>绑定完成前先占住资源，避免过度分配</td><td>Bind 失败后必须过期或回滚</td></tr>
<tr><td>Nominated Pod</td><td>抢占时记录候选节点</td><td>被抢占 Pod 退出前，高优先级 Pod 仍可能等待</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Plugin 扩展点与调度研究问题的映射</h3>
<table>
<tr><th>研究问题</th><th>适合扩展点</th><th>说明</th></tr>
<tr><td>短作业优先 / SLA 排序</td><td>QueueSort</td><td>改变 Pod 出队顺序，影响全局等待时间</td></tr>
<tr><td>Gang Scheduling</td><td>PreFilter + Permit + Reserve</td><td>先识别 PodGroup，再在 Permit 阶段等待同组 Pod 凑齐</td></tr>
<tr><td>拓扑感知放置</td><td>PreFilter + Filter + Score</td><td>基于 NUMA、NVLink、机架、RDMA 等约束过滤和打分</td></tr>
<tr><td>多资源公平</td><td>QueueSort + Score + PostFilter</td><td>排序决定谁先获得机会，抢占决定如何回收资源</td></tr>
<tr><td>代价基抢占</td><td>PostFilter</td><td>调度失败后选择 victim，考虑 checkpoint、运行时长和释放资源量</td></tr>
<tr><td>DRA 设备匹配</td><td>PreFilter + Filter + Reserve</td><td>基于 ResourceClaim 和 ResourceSlice 做设备级匹配与预留</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Preemption 深入</h3>
<p>抢占不是简单地“杀掉低优先级 Pod 后马上运行高优先级 Pod”。scheduler 会先寻找通过移除低优先级 Pod 后可满足高优先级 Pod 的节点，选择 victim 后设置 <code>nominatedNodeName</code>，等待被抢占 Pod 优雅退出。期间如果集群状态变化，调度结果仍可能改变。</p>
<ul>
<li><strong>PDB：</strong>PodDisruptionBudget 会影响 victim 选择，减少对高可用服务的破坏。</li>
<li><strong>Graceful termination：</strong>被抢占 Pod 有终止宽限期，高优先级 Pod 不能立刻拿到资源。</li>
<li><strong>不可抢占约束：</strong>nodeSelector 不匹配、PVC 约束不满足、硬亲和性不满足，抢占也解决不了。</li>
<li><strong>训练任务代价：</strong>AI 训练抢占要考虑 checkpoint 新鲜度、已运行时间、重启成本和 gang 语义。</li>
</ul>
</div>

<div class="card card-w">
<h3>Gang Scheduling → 见"任务调度理论"页面</h3>
<p>Gang Scheduling 的理论基础（partial allocation、PodGroup/minAvailable、Backfill、弹性训练）和 K8s 实现细节（Coscheduling Plugin / Volcano / Kueue、Framework 扩展点落点、边界情况）已统一归并到 <strong>"任务调度理论" → "批调度、Gang 与 Backfill"</strong> 标签页。</p>
<p>快速索引：Gang 概念与 partial allocation → 任务调度理论 / 批调度、Gang 与 Backfill；Framework 扩展点落点 → 同上；Coscheduling / Volcano / Kueue 对比 → 同上；边界情况与坑 → 同上。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么说调度算法不能脱离 scheduler cache 和 binding cycle 讨论？</div>
<div class="qa-a"><p>因为算法给出的只是“应该放哪里”，而 Kubernetes 还要解决并发绑定、缓存一致性、资源临时预留、失败回滚和 API Server 写入延迟。一个理论上最优的策略，如果不能处理 assume、reserve、unreserve、permit timeout 和抢占等待，在真实 kube-scheduler 中就不可落地。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Scheduler Extender、Scheduler Plugin、多个 scheduler 怎么选？</div>
<div class="qa-a"><p>新能力优先用 Scheduling Framework Plugin，因为它能接入完整生命周期和 scheduler cache；Extender 更像外部 HTTP 过滤/打分，延迟和一致性控制较弱；多个 scheduler 适合业务强隔离，但要避免不同 scheduler 同时竞争同一批资源造成策略冲突。</p></div>
</div>

## 面试回答

**30 秒版：**

scheduler cache、assume、binding cycle 和 preemption 是理解调度一致性和抢占的关键。 不要只讲算法，必须讲缓存状态和绑定路径。

**2 分钟版：**

我会先说明这个问题在 Kubernetes 核心 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。
