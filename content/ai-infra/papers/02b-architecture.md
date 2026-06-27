## 一句话结论

DeepShare 在 Kubernetes 上拆成 Controller 加 Scheduler Plugin 两层：Controller 管租户级的 quota、QAD、队列与准入，通过 TenantQuota CRD 和 Pod annotation 把租户语义传给调度路径；Scheduler Plugin 复用 Scheduler Framework 五个扩展点做 Pod 级排序、过滤、打分、预留和抢占。
<div class="card card-d">
<h3>总体架构</h3>

<pre><code class="language-text">用户提交 GPU Job / Pod
        |
        v
DeepShare Controller
        |-- 维护 TenantQuota
        |-- 计算 QAD
        |-- 维护租户级 Guaranteed / Best-effort 队列
        |-- 做 quota admission
        |-- 给 Pod 打 annotation / 移除 schedulingGate
        |-- 必要时触发 Best-effort 抢占
        v
kube-scheduler + DeepShare Scheduler Plugins
        |-- QueueSort：QAD-aware 排序
        |-- PreFilter：解析 tenant / class / GPU request
        |-- Filter：quota、节点 GPU、共享可行性
        |-- Score：bin packing、干扰感知、碎片控制
        |-- Reserve / Unreserve：更新资源账本
        |-- PostFilter：资源不足时触发抢占候选选择
        v
Bind Pod 到 Node</code></pre>

</div>

<div class="card card-s">
<h3>为什么要拆成 Controller + Scheduler Plugin</h3>
<p>DeepShare 的核心机制（QAD、弹性配额借用、预测性调度、干扰感知合用、Best-effort 借用与回收、Guaranteed QoS）属于<strong>租户级 / 作业级</strong>逻辑；而 kube-scheduler 默认的调度对象是 <strong>Pod</strong>，原生并不知道：</p>

<ul>
<li>这个 Pod 属于哪个 tenant</li>
<li>这个 Pod 是 Guaranteed 还是 Best-effort</li>
<li>这个 tenant quota 是多少</li>
<li>这个 tenant 当前 QAD 是多少</li>
<li>这个 Pod 是否借用了别人的空闲资源</li>
<li>这个 Pod 是否应该被抢占</li>
<li>这个 Pod 与已有 GPU workload 是否会互相干扰</li>
</ul>

<table>
<thead><tr><th>模块</th><th>适合处理的问题</th></tr></thead>
<tbody>
<tr><td>Controller</td><td>租户状态、quota、QAD、队列、准入、抢占策略</td></tr>
<tr><td>Scheduler Plugin</td><td>Pod 级排序、节点过滤、节点打分、资源预留、绑定前决策</td></tr>
</tbody>
</table>
</div>

<div class="card card-m">
<h3>系统里需要的 K8S 对象</h3>

<div class="comp">
<div class="comp-t">TenantQuota CRD</div>
<p>表示每个租户的 GPU quota 与当前状态：</p>

<pre><code class="language-yaml">apiVersion: deepshare.io/v1
kind: TenantQuota
metadata:
  name: team-a
spec:
  gpuQuota: 32
  bestEffortMultiplier: 2
status:
  guaranteedDemand: 40
  guaranteedAllocated: 20
  bestEffortUsed: 8
  qad: 0.625</code></pre>

<ul>
<li><code>gpuQuota</code>：租户 Guaranteed 配额。</li>
<li><code>bestEffortMultiplier</code>：Best-effort 借用上限 η（如 η=2）。</li>
<li><code>guaranteedDemand</code>：当前 Guaranteed 需求。</li>
<li><code>guaranteedAllocated</code>：当前已满足的 Guaranteed 资源。</li>
<li><code>bestEffortUsed</code>：当前 Best-effort 使用量。</li>
<li><code>qad</code>：当前租户保障程度。</li>
</ul>
</div>

<div class="comp">
<div class="comp-t">GPU Job / Pod 的两种表达方式</div>
<p><strong>方式 A：DeepShareJob CRD</strong>（推荐，更工程化，便于做租户级排队和准入）</p>

<pre><code class="language-yaml">apiVersion: deepshare.io/v1
kind: DeepShareJob
metadata:
  name: train-a
spec:
  tenant: team-a
  class: Guaranteed
  gpu: 4
  estimatedRuntime: 3600
  preemptible: false</code></pre>

<p><strong>方式 B：原生 Pod / Job + label</strong>（轻量化）</p>

<pre><code class="language-yaml">apiVersion: v1
kind: Pod
metadata:
  name: train-a
  labels:
    deepshare.io/tenant: team-a
    deepshare.io/class: guaranteed
  annotations:
    deepshare.io/estimated-runtime: "3600"
spec:
  schedulerName: deepshare-scheduler
  containers:
  - name: train
    image: train:latest
    resources:
      limits:
        nvidia.com/gpu: 4</code></pre>

</div>

<div class="comp">
<div class="comp-t">Pod Annotation / Label（Controller 写入，调度路径读取）</div>

<pre><code class="language-yaml">metadata:
  labels:
    deepshare.io/tenant: team-a
    deepshare.io/class: guaranteed
  annotations:
    deepshare.io/qad: "0.625"
    deepshare.io/estimated-runtime: "3600"
    deepshare.io/admitted: "true"
    deepshare.io/preemptible: "false"</code></pre>

<p>Scheduler Plugin 通过这些字段做 QueueSort、Filter、Score。</p>
</div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
