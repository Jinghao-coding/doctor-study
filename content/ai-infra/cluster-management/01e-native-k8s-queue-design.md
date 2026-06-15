## 一句话结论

原生 Kubernetes 的 ResourceQuota 会直接拒绝超额对象，不能表达“用户继续提交任务，但超过 10 张 GPU 的部分进入队列等待”。要实现这个语义，需要在 Pod 调度前增加任务级队列和准入控制。配额账本和任务状态不需要额外数据库，直接存在 CRD 的 `spec` / `status` 里，由 etcd 持久化，控制器靠 reconcile 把账本重新算出来。

<div class="card card-m">
<h3>场景：每个用户限额 10 张 GPU，但允许继续提交</h3>
<p>需求是：用户可以提交任意数量 AIJob，但同一时刻最多运行 10 张 GPU。超过 10 张的任务不能被 API Server 拒绝，而应该进入队列等待，等资源释放后自动准入。</p>
<table>
<tr><th>机制</th><th>能不能满足</th><th>原因</th></tr>
<tr><td>ResourceQuota</td><td>不满足</td><td>超过 quota 时直接拒绝创建 Pod / Job，不会保留等待队列</td></tr>
<tr><td>PriorityClass</td><td>不满足</td><td>只表达优先级，不表达用户运行中 GPU 上限</td></tr>
<tr><td>默认 scheduler</td><td>不满足</td><td>只消费已创建 Pod，不管理任务级准入队列</td></tr>
<tr><td>Kueue / Volcano</td><td>部分满足</td><td>已有 Queue / Workload / PodGroup 能表达准入和排队</td></tr>
<tr><td>自研 AIJob Queue Controller</td><td>满足</td><td>在创建 Pod 前控制任务是否 admitted</td></tr>
</table>
</div>

<div class="card card-d">
<h3>推荐设计：AIJob + Queue + Admission Controller</h3>
<p>不要让用户直接提交 Pod。用户提交 <code>AIJob</code>，Operator 根据队列状态决定是否创建 Pods。</p>
<table>
<tr><th>组件</th><th>职责</th></tr>
<tr><td><code>AIJob</code></td><td>用户提交的任务对象，描述 GPU 数、优先级、队列、checkpoint、minAvailable</td></tr>
<tr><td><code>AIQueue</code></td><td>每个用户 / 团队的队列，记录 maxRunningGPU、已用量、等待任务</td></tr>
<tr><td>Queue Controller</td><td>watch AIJob 和 Pod 状态，计算哪些任务可以 admitted</td></tr>
<tr><td>AIJob Operator</td><td>只有 admitted 的 AIJob 才创建 PodGroup / Pods</td></tr>
<tr><td>Scheduler Plugin</td><td>对 admitted Pods 做实际 Node 选择，可叠加拓扑、干扰和装箱策略</td></tr>
</table>
<pre><code class="language-text">用户提交 AIJob
  ↓
AIJob 进入 PendingQueue
  ↓
Queue Controller 检查 user.runningGpu + job.gpu <= 10
  ↓
满足：标记 admitted=true，Operator 创建 PodGroup/Pods
不满足：AIJob 保持 Queued，不创建 Pods
  ↓
Pod 完成/失败/释放资源后，Queue Controller 重新准入后续任务</code></pre>
</div>

<div class="card card-m">
<h3>状态存哪里：不用数据库，存在 CRD 的 spec / status</h3>
<p>这是面试最关键的落点。很多人第一反应是“再起一个 MySQL / Redis 存队列和配额”，但在 K8s 里更标准的做法是<strong>不引入外部数据库</strong>，把状态拆成两类，全部交给 etcd：</p>
<table>
<tr><th>状态类型</th><th>存在哪</th><th>谁写</th><th>例子</th></tr>
<tr><td>用户期望（desired）</td><td>CRD 的 <code>spec</code></td><td>用户 / 提交端</td><td>这个 AIJob 要几张卡、属于哪个队列、优先级</td></tr>
<tr><td>系统观测（observed）</td><td>CRD 的 <code>status</code></td><td>控制器</td><td>AIJob 当前 phase、AIQueue 已用了多少 GPU、等待列表</td></tr>
</table>
<p>etcd 本身就是 K8s 的强一致 KV 存储，CRD 对象的读写都走 API Server，自带 watch、乐观锁（resourceVersion）、RBAC 和审计。<strong>再单独搭一个数据库反而要自己解决一致性、备份、和 etcd 状态对不齐的问题</strong>，所以默认不这么做。</p>
<pre><code class="language-yaml"># AIQueue：配额账本就是它的 status
apiVersion: scheduling.example.com/v1
kind: AIQueue
metadata:
  name: team-a
spec:
  maxRunningGPU: 10          # 配额上限（desired）
status:
  runningGPU: 8             # 当前在跑的 GPU 总数（observed）
  admitted:                 # 已准入、在跑的任务
    - jobName: train-001
      gpu: 4
    - jobName: train-002
      gpu: 4
  pending:                  # 排队中的任务，按入队/优先级排序
    - jobName: train-003
      gpu: 4
    - jobName: train-004
      gpu: 2</code></pre>
<pre><code class="language-yaml"># AIJob：任务本身的状态机也写在 status.phase
apiVersion: scheduling.example.com/v1
kind: AIJob
metadata:
  name: train-003
spec:
  queue: team-a
  gpu: 4
  minAvailable: 4           # Gang：4 个 Pod 要么一起跑
status:
  phase: Queued             # Pending -> Queued -> Admitted -> Running -> Succeeded/Failed
  admitted: false</code></pre>
</div>

<div class="card card-s">
<h3>配额账本怎么算出来：reconcile 而不是手工加减</h3>
<p>关键认知：<code>status.runningGPU</code> 这个数字<strong>不要靠“准入时 +4、结束时 -4”这种手工累加来维护</strong>，因为控制器可能重启、可能漏事件，累加值会和真实情况飘移。正确做法是每次 reconcile 都<strong>重新从真相源（source of truth）全量算一遍</strong>：</p>
<pre><code class="language-text">Queue Controller reconcile(queue):
  1. List 属于该 queue 且 phase=Admitted/Running 的所有 AIJob
  2. runningGPU = Σ(这些 job 的 gpu)        # 重新算，不依赖旧值
  3. for job in pending(按优先级/FIFO 排序):
       if runningGPU + job.gpu <= maxRunningGPU:
           job.status.phase = Admitted       # 标记准入
           runningGPU += job.gpu
       else:
           break                              # 队头算不动就停，保证顺序
  4. 把 runningGPU / admitted / pending 写回 queue.status</code></pre>
<p>这样即使控制器重启、丢了内存里的队列，下次 reconcile 也能从 etcd 里的 AIJob 列表把账本完整重建，<strong>状态是“可重算的”而不是“攒出来的”</strong>。这就是 K8s 控制器的 level-triggered（看最终状态）而非 edge-triggered（依赖每个事件）思想。</p>
</div>

<div class="card card-w">
<h3>并发与一致性：多副本控制器怎么不互相打架</h3>
<table>
<tr><th>问题</th><th>处理方式</th></tr>
<tr><td>两个任务同时被准入导致超额</td><td>控制器对同一个 queue 串行 reconcile（workqueue 按 key 去重，同一 key 不并发），不会两个 goroutine 同时改一个账本</td></tr>
<tr><td>写 status 时对象已被别人改过</td><td>API Server 用 <code>resourceVersion</code> 做乐观锁，update 冲突返回 409 Conflict，控制器 requeue 重新算一遍再写</td></tr>
<tr><td>控制器跑多副本</td><td>用 Lease 做 leader election，同一时刻只有一个 leader 真正 reconcile，避免多写</td></tr>
<tr><td>准入后 Pod 一直起不来</td><td>设 Admitted 超时，超时退回 Queued 并释放占用，避免名额被占死</td></tr>
</table>
<div class="qa-summary">一致性靠 etcd 乐观锁 + 单 key 串行 reconcile + 全量重算，而不是分布式锁或事务数据库。</div>
</div>

<div class="card card-d">
<h3>宕机恢复：为什么不用持久化内存队列</h3>
<p>控制器是<strong>无状态</strong>的，内存里的队列只是缓存。崩溃 / 升级 / 重新调度后：</p>
<ol>
<li>新实例启动，通过 informer 从 API Server <strong>List + Watch</strong> 拉全量 AIJob 和 AIQueue。</li>
<li>对每个 queue 触发一次 reconcile，按上面的算法<strong>重新算出 runningGPU 和准入结果</strong>。</li>
<li>已经在跑的 Pod 不受影响（它们的真相在 etcd 和节点上），队列顺序也能从 AIJob 的创建时间 / 优先级字段恢复。</li>
</ol>
<p>所以“状态怎么保存”的答案是：<strong>任务和配额状态保存在 etcd 里的 CRD 对象上，控制器自己不持久化任何东西，靠 reconcile 随时重建</strong>。需要外部数据库的，只有 etcd 装不下或不该放的东西——比如要做<strong>跨集群的全局配额、长期计费/用量审计、历史任务归档</strong>，这时才会把汇总数据写进 Postgres/ClickHouse 之类，但准入决策的实时账本仍留在 etcd。</p>
</div>

<div class="card card-s">
<h3>为什么不要让超额 Pod 先创建出来</h3>
<table>
<tr><th>问题</th><th>原因</th></tr>
<tr><td>污染 scheduler queue</td><td>大量明知超额的 Pod 会反复 Pending，浪费调度周期</td></tr>
<tr><td>事件噪声</td><td>用户会看到大量 FailedScheduling，但根因其实是队列准入</td></tr>
<tr><td>难做 Gang</td><td>部分 Pod 被创建后容易 partial allocation</td></tr>
<tr><td>难做公平</td><td>scheduler 只看 Pod，不知道整个 AIJob 的队列位置和用户额度</td></tr>
</table>
<div class="qa-summary">关键设计：排队应该发生在 Pod 创建前，而不是让 Pod 全部进入 kube-scheduler 再 Pending。</div>
</div>

<div class="card card-w">
<h3>面试回答模板</h3>
<p>如果面试官问“原生 K8s 不支持超额排队，你怎么改”，可以这样答：</p>
<p>我会引入任务级 CRD，而不是让用户直接创建 Pod。用户提交 AIJob，AIJob 进入队列对象 AIQueue。Queue Controller 维护每个用户正在运行的 GPU 用量和等待队列，只有当 <code>runningGpu + jobGpu <= quota</code> 时才把 AIJob 标记为 admitted，并让 AIJob Operator 创建 PodGroup / Pods。超过额度的任务保留为 Queued 状态，不创建 Pod，因此不会污染 scheduler。资源释放后，Queue Controller 重新扫描队列并准入下一个任务。真正的 Pod 到 Node 绑定仍交给 scheduler plugin，可以继续做拓扑、Gang、干扰和装箱。</p>
<p>如果追问“状态存在哪、要不要数据库”，我会说：<strong>不用额外数据库</strong>。期望状态放 CRD 的 spec，运行状态和配额账本放 CRD 的 status，全部由 etcd 持久化。配额用量不是手工加减出来的，而是每次 reconcile 从所有 Admitted/Running 的 AIJob <strong>全量重算</strong>，所以控制器重启后能从 etcd 重建账本。并发靠 etcd 的 resourceVersion 乐观锁加同一队列串行 reconcile 保证不超发，多副本用 leader election。只有跨集群全局配额或长期计费审计才会引入外部数据库。</p>
</div>
