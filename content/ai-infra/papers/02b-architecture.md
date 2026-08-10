<div class="card card-s">
<h3>总体架构</h3>

```flow
TenantQuota CRD + Job class annotation | 描述 quota、Best-effort 上限和作业类别
Lightweight Quota Controller | reconcile 配置，生成 per-tenant quota metadata
Scheduler Plugin | 维护 Q / Q̃、两级队列、colocation 准入和抢占
Informer Cache | 从运行 Pod 重建 Guaranteed allocation 与 demand
MPS + DCGM DaemonSet | 执行 GPU 共享、采样干扰并上报 degraded pair
Kubernetes API Server | Bind、Pod resize、Pod deletion 与故障幂等恢复
```

<div class="qa-summary">面试记忆：Controller 管“配置态”，Plugin 管“决策态”，DaemonSet 管“节点运行态”。</div>
</div>

## 三类组件分别管什么

<table>
<thead><tr><th>组件</th><th>核心状态</th><th>关键职责</th><th>不负责什么</th></tr></thead>
<tbody>
<tr><td>Quota Controller</td><td>TenantQuota、作业 class annotation</td><td>reconcile 租户 quota 与 Best-effort cap 元数据</td><td>不做节点放置，不维护实时 QAD</td></tr>
<tr><td>Scheduler Plugin</td><td>队列、瞬时/平滑 QAD、节点视图、预测结果</td><td>排序、Filter、Score、Reserve、PostFilter、Permit</td><td>不负责 MPS 进程和 DCGM 采样</td></tr>
<tr><td>Node-local DaemonSet</td><td>MPS client、DCGM counters、degraded pair</td><td>GPU 共享、干扰监控、异常上下文清理</td><td>不决定租户优先级</td></tr>
</tbody>
</table>

## QAD 在哪里维护

<div class="card card-m">
<h3>QAD 是 Scheduler Plugin 的内存状态</h3>
<p>Scheduler Plugin 从 informer cache 里的运行 Pod 推导 <code>A_i^G(t)</code>、<code>D_i^G(t)</code> 和 quota 元数据，计算瞬时 <code>Q_i(t)</code>，再维护 EMA 平滑值 <code>Q̃_i(t)</code>。这样排序、colocation 和抢占看到的是同一份实时状态。</p>
<p>论文没有把每一轮 QAD 写进 <code>TenantQuota.status</code>。发生 leader failover 后，新 leader 可以从运行 Pod 重建瞬时 QAD，并用首轮值 warm-start EMA，避免额外持久化和热路径写放大。</p>
</div>

## Kubernetes 对象如何表达

<div class="card card-s">
<h3>TenantQuota CRD：保存权益配置，不保存实时控制环</h3>

<pre><code class="language-yaml">apiVersion: deepshare.io/v1
kind: TenantQuota
metadata:
  name: team-a
spec:
  gpuQuota: 8
  bestEffortMultiplier: 2</code></pre>

<ul>
<li><code>gpuQuota</code> 对应 <code>q_i</code>，即 Guaranteed GPU quota。</li>
<li><code>bestEffortMultiplier</code> 对应 <code>η</code>，限制机会型作业的借用上限。</li>
<li>作业通过 <code>deepshare.io/class: guaranteed|best-effort</code> annotation 声明服务类别。</li>
</ul>

<pre><code class="language-yaml">metadata:
  annotations:
    deepshare.io/class: guaranteed
spec:
  schedulerName: deepshare-scheduler
  containers:
  - name: train
    resources:
      limits:
        nvidia.com/gpu: 4</code></pre>
</div>

## Scheduler Framework 五个扩展点

<table>
<thead><tr><th>扩展点</th><th>DeepShare 中的作用</th></tr></thead>
<tbody>
<tr><td>Filter</td><td>筛出有空闲 GPU，或满足 CPU、内存、显存、Best-effort cap 和共享条件的节点</td></tr>
<tr><td>Score</td><td>用 RF 干扰预测和双边 retention 门槛排序候选位置</td></tr>
<tr><td>Reserve</td><td>把 GPU claim 写入下一调度周期的集群视图，避免 double booking</td></tr>
<tr><td>PostFilter</td><td>没有可行 GPU 时运行代价感知的 Best-effort victim 选择</td></tr>
<tr><td>Permit</td><td>只有触发 CPU/Memory in-place resize 时等待 Pod 状态反映新资源量；不是用来做 Gang Scheduling</td></tr>
</tbody>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 QAD 不放在 Controller 里周期性写 CRD？</div>
<div class="qa-a"><p>QAD 是 50ms 调度周期内持续变化的热状态，排序、共享和抢占都要同步消费。若 Controller 计算后再写 CRD，既增加 API Server 写压力，也引入控制环延迟和一致性窗口。放在 Scheduler Plugin 内存里能直接复用 informer cache，并在 leader 切换后重建。</p></div>
</div>
