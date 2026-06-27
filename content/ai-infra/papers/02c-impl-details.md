## 一句话结论

DeepShare 的两级队列中，第一级租户级 Guaranteed/Best-effort 队列在 Controller 里显式维护并做准入，第二级全局队列是逻辑队列——由 Controller 准入后的 Pod 集合加 Scheduler Plugin 的 QAD-aware QueueSort 共同体现，调度执行落在 Framework 各扩展点。
<div class="card card-s">
<h3>两级队列具体在哪里实现</h3>
<p>论文里的队列结构：</p>

<pre><code class="language-text">每个 tenant 有：
  Q_i^G：Guaranteed 队列
  Q_i^B：Best-effort 队列
集群级有：
  Q^G：全局 Guaranteed 候选队列
  Q^B：全局 Best-effort 候选队列</code></pre>

<div class="comp">
<div class="comp-t">第一级（租户队列）：Controller 内显式维护</div>
<p>这是 tenant/job 级语义，必须在 Controller 里：</p>

<pre><code class="language-go">type TenantQueue struct {
    TenantID         string
    GuaranteedQueue  PriorityQueue
    BestEffortQueue  PriorityQueue
}

tenantQueues map[string]*TenantQueue</code></pre>

<p>Controller watch 到新 Job 后，根据 <code>tenant</code> / <code>class</code> / <code>submitTime</code> / <code>estimatedRuntime</code> 放入对应租户队列。</p>
</div>

<div class="comp">
<div class="comp-t">第二级（全局队列）：Controller 生成候选集 + Scheduler Plugin QueueSort</div>
<p>建议回答：<strong>Controller 生成全局候选集，Scheduler Plugin 的 QueueSort 实现最终全局排序。</strong></p>

<pre><code class="language-text">Controller 不显式维护长期存在的 Q^G/Q^B 物理队列；
它周期性从各 tenant 队列里挑出 admitted jobs；
这些 admitted Pods 进入 kube-scheduler；
然后 QueueSort 按 DeepShare 规则排序。</code></pre>

<p>所以 <code>Q^G / Q^B</code> 是<strong>逻辑队列</strong>，由"admitted Pod 集合 + QueueSort 排序规则"共同体现。</p>
</div>

<div class="comp">
<div class="comp-t">为什么不完全放 Controller 排好顺序再逐个放行</div>
<ul>
<li>kube-scheduler 内部仍有自己的 ActiveQ。</li>
<li>Pod 进入 scheduler 后还会经历 backoff / unschedulable。</li>
<li>节点状态变化后，顺序需要重新评估。</li>
<li>QAD 是动态的，会持续变化。</li>
<li>调度还要结合 Filter / Score 的结果。</li>
</ul>
<p>所以更自然：<strong>Controller 控制 admission，Scheduler Plugin 控制 scheduler 内部排序和落点。</strong></p>
</div>
</div>

<div class="card card-m">
<h3>Controller 具体工作流</h3>

<div class="comp">
<div class="comp-t">Step 1 — watch Job / Pod，放入租户队列</div>
<p>用户提交 <code>team-a, Guaranteed, 4 GPU</code>，Controller 将其放入 <code>Q_a^G</code>；Best-effort 任务放入 <code>Q_a^B</code>。</p>
</div>

<div class="comp">
<div class="comp-t">Step 2 — 计算 QAD</div>
<div class="formula">$$\mathrm{QAD} = \frac{\text{Allocated GPU time}}{\text{Guaranteed GPU time}}$$</div>
<p>简化实现：</p>
<div class="formula">$$\mathrm{QAD} = \frac{\text{已满足 Guaranteed GPU}}{\min(\text{quota},\, \text{当前 Guaranteed demand})}$$</div>
<p>例：team-a quota = 32，Guaranteed demand = 40，Guaranteed allocated = 16 → QAD = 16 / min(32, 40) = 0.5。<strong>QAD 越低，租户保障越不足。</strong></p>
</div>

<div class="comp">
<div class="comp-t">Step 3 — Guaranteed admission</div>
<p>对 Guaranteed job 检查：</p>
<div class="formula">$$U_i^G + R_j \le q_i$$</div>
<p>满足则进入调度候选集；否则继续留在 <code>Q_i^G</code> 中等待。</p>
</div>

<div class="comp">
<div class="comp-t">Step 4 — Best-effort admission（更保守）</div>
<p>需同时满足：</p>
<div class="formula">$$\text{没有可放置的 Guaranteed job}\quad\text{且}\quad U_i^B + R_j \le \eta \cdot q_i$$</div>
<p><strong>含义：</strong>Best-effort 可借用空闲资源，但不能无限借，也不能挡住 Guaranteed 作业。</p>
</div>

<div class="comp">
<div class="comp-t">Step 5 — 释放 admitted Pod 到调度器</div>
<p><strong>方法 A（推荐）：移除 schedulingGate</strong></p>

<pre><code class="language-yaml">spec:
  schedulingGates:
  - name: deepshare.io/admission</code></pre>

<p>Controller 判断可以调度后移除 gate，Pod 才进入 kube-scheduler。</p>
<p><strong>方法 B：annotation 兜底</strong> — Pod 已存在但 plugin 仅放行 <code>deepshare.io/admitted: "true"</code> 的 Pod；不推荐完全依赖，因为 Pod 已进入 scheduler 后可能造成无效调度循环。</p>
</div>
</div>

<div class="card card-m">
<h3>Scheduler Plugin 的扩展点实现</h3>
<p>运行自定义调度器：<code>schedulerName: deepshare-scheduler</code>，复用 Kubernetes Scheduler Framework 加载 DeepShare 插件。</p>

<div class="comp">
<div class="comp-t">QueueSort — DeepShare 全局排序</div>
<p>排序 key（按优先级从高到低）：</p>
<ol>
<li><strong>class</strong>：Guaranteed 优先于 Best-effort。</li>
<li><strong>tenant QAD</strong>：QAD 低优先。</li>
<li><strong>predicted runtime</strong>：短任务优先。</li>
<li><strong>submit time</strong>：早提交优先（tie-breaker）。</li>
</ol>

<table>
<thead><tr><th>Pod</th><th>class</th><th>tenant</th><th>QAD</th><th>runtime</th></tr></thead>
<tbody>
<tr><td>pod-a</td><td>Guaranteed</td><td>team-a</td><td>0.4</td><td>2h</td></tr>
<tr><td>pod-b</td><td>Guaranteed</td><td>team-b</td><td>0.9</td><td>10min</td></tr>
<tr><td>pod-c</td><td>Best-effort</td><td>team-c</td><td>1.0</td><td>5min</td></tr>
</tbody>
</table>

<p>排序：<code>pod-a → pod-b → pod-c</code>。即使 pod-b 更短，team-a QAD 更低也优先。<span class="hl">先恢复保障不足的租户，再用预测运行时间优化局部顺序。</span></p>
</div>

<div class="comp">
<div class="comp-t">PreFilter — 解析调度上下文</div>

<pre><code class="language-text">读取 tenant / class / GPU request
读取 estimated runtime / QAD / preemptible
写入 cycle state，供后续插件复用</code></pre>

</div>

<div class="comp">
<div class="comp-t">Filter — 节点可放置性</div>
<ul>
<li>节点是否有足够 GPU；GPU 型号是否满足。</li>
<li>node affinity / taint toleration 是否满足。</li>
<li>共享 GPU 是否超过共享上限。</li>
<li>colocation 干扰是否在阈值内（对应论文 interference-aware colocation）。</li>
<li>Best-effort 是否会影响 Guaranteed 的资源恢复能力。</li>
</ul>
</div>

<div class="comp">
<div class="comp-t">Score — 节点打分</div>
<ul>
<li><strong>bin packing</strong>：减少碎片，2-GPU 任务优先放到刚好剩 2 张 GPU 的节点；不要打散完整 8-GPU 节点。</li>
<li><strong>GPU utilization</strong>：优先利用空闲碎片。</li>
<li><strong>interference score</strong>：选择干扰更小的 colocated 节点。</li>
<li><strong>reserved capacity</strong>：避免破坏 Guaranteed 恢复能力。</li>
<li>Best-effort 优先放到可回收、低干扰位置；Guaranteed 优先放到稳定、低干扰位置。</li>
</ul>
</div>

<div class="comp">
<div class="comp-t">Reserve / Unreserve — 维护资源账本</div>
<p>选定节点但未 Bind 时更新 DeepShare 账本：</p>

<pre><code class="language-text">tenant guaranteedUsed += gpuRequest
node   allocatedGpu  += gpuRequest
if Best-effort:
    tenant bestEffortUsed += gpuRequest</code></pre>

<p>Bind 失败时 Unreserve 回滚。<strong>很重要：</strong>避免 DeepShare 账本与 kube-scheduler assumed state 不一致。</p>
</div>

<div class="comp">
<div class="comp-t">PostFilter — 抢占</div>
<p>Guaranteed Pod 调度失败且 tenant QAD 很低时触发。Victim 选择优先级：</p>

<pre><code class="language-text">Best-effort Pod
低优先级 Pod
可抢占 Pod
抢占代价低的 Pod</code></pre>

<p>对应论文 predictive scheduling 与 preemption cost：综合 progress loss、checkpoint 状况、restart overhead，确认抢占后能真正释放足够 GPU 并提升低 QAD 租户保障。</p>
</div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
