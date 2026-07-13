## 一句话结论

DeepShare 的关键实现链路是：Scheduler Plugin 从 informer cache 计算租户保障状态，在内部做两级队列排序，再按“独占放置 → 安全合用 → CPU/Memory 回收 → GPU 抢占”的干扰递增顺序尝试落点。

## 一次调度周期怎么走

```flow
读取租户 quota、作业 class 与运行 Pod | Controller 提供配置元数据，informer 提供实时状态
计算瞬时 QAD | A_i^G / min(q_i, D_i^G)，无 Guaranteed demand 时为 1
EMA 平滑 | 得到调度控制信号 Q̃_i
两级队列排序 | Guaranteed 先于 Best-effort，Q̃ 低优先，预测剩余时间短次优先
尝试独占 GPU | 无干扰，优先级最高
尝试安全 colocation | RF retention 预测与 QAD 动态门槛同时通过
回收 CPU / Memory | 对 Best-effort Pod 发起 in-place resize
选择 GPU victims | PostFilter 按抢占效率贪心回收足够的完整 GPU
```

## 两级队列不要记成两个 Controller

<div class="card card-s">
<h3>队列符号和职责</h3>
<table>
<thead><tr><th>队列</th><th>含义</th><th>做什么</th></tr></thead>
<tbody>
<tr><td><code>Q_i^G</code> / <code>Q_i^B</code></td><td>租户 <code>i</code> 的 Guaranteed / Best-effort 队列</td><td>按 quota 与 cap 做租户级 admission</td></tr>
<tr><td><code>Q^G</code> / <code>Q^B</code></td><td>集群级 Guaranteed / Best-effort 队列</td><td>按平滑 QAD 和预测剩余时间决定放置顺序</td></tr>
</tbody>
</table>

<p>Guaranteed 作业只有在 <code>U_i^G + R_j ≤ q_i</code> 时进入集群 Guaranteed 队列。Best-effort 作业只有在没有剩余 Guaranteed 作业能通过独占或安全合用落点，并且 <code>U_i^B + R_j ≤ ηq_i</code> 时才进入候选集。</p>
<p>集群级排序采用词典序：先区分 Guaranteed / Best-effort，再按 <code>(Q̃_i ↑, T̂(j) ↑)</code> 排序。QAD 是第一键，所以运行时间预测误差不会让保障充分的租户跨过保障不足的租户。</p>
</div>

## QAD 在调度路径中的输入输出

<div class="card card-m">
<h3>输入：已兑现与应兑现</h3>
<div class="formula">$$
Q_i(t)=
\begin{cases}
1, & D_i^G(t)=0,\\
\dfrac{A_i^G(t)}{\min\!\left(q_i,D_i^G(t)\right)}, & D_i^G(t)>0.
\end{cases}
$$</div>
<ul>
<li><code>A_i^G(t)</code>：当前已经分配的 Guaranteed GPU，Best-effort 不计入。</li>
<li><code>min(q_i,D_i^G(t))</code>：当前应兑现的 Guaranteed GPU。</li>
<li><code>Q_i(t)</code>：瞬时兑现率；<code>Q̃_i(t)</code>：EMA 平滑后的控制信号。</li>
</ul>
</div>

<div class="card card-d">
<h3>输出：同一个 Q̃ 驱动三类决策</h3>
<ol>
<li><strong>恢复排序：</strong><code>Q̃</code> 越低，租户越欠保障，越先调度。</li>
<li><strong>共享收紧：</strong>任一租户 <code>Q̃</code> 低时，提高所需 throughput retention 门槛；极端时停止创建新 colocation。</li>
<li><strong>QoS 报告：</strong>用连续的保障度观察长期 deficit，而不是只看“是否超 quota”的二值状态。</li>
</ol>
<p>注意：QAD 不直接无条件触发删除 Pod。GPU 抢占由 Guaranteed 作业 placement failure 触发，PostFilter 再用代价模型选 Best-effort victims。</p>
</div>

## 五个扩展点怎么串起来

<table>
<thead><tr><th>顺序</th><th>扩展点</th><th>关键动作</th></tr></thead>
<tbody>
<tr><td>1</td><td>Filter</td><td>检查空闲/单 resident GPU、CPU/内存/显存 headroom 和 Best-effort cap</td></tr>
<tr><td>2</td><td>Score</td><td>比较 RF 预测 retention，优先低干扰候选</td></tr>
<tr><td>3</td><td>Reserve</td><td>在下一周期视图中预占 GPU，防止并发调度 double booking</td></tr>
<tr><td>4</td><td>PostFilter</td><td>无可行节点时执行 cost-aware victim selection</td></tr>
<tr><td>5</td><td>Permit</td><td>仅在 CPU/Memory resize 已发起时等待 Pod.Status.Resources 更新</td></tr>
</tbody>
</table>

## 故障恢复与热路径

<div class="card card-s">
<ul>
<li>Plugin 以多副本 Deployment 运行，通过 Lease 选主。</li>
<li>QAD 可从 informer cache 的运行 Pod 推导；新 leader 用首轮瞬时 QAD warm-start EMA。</li>
<li>抢占表达为 Pod deletion，由 API Server 幂等 reconcile，不需要自定义补偿事务。</li>
<li>调度端到端延迟低于 50ms，其中特征提取、队列记账和受限候选打分合计低于 25ms。</li>
</ul>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官问“两级队列和 QAD 到底怎么连起来”，怎么回答？</div>
<div class="qa-a"><p>每个租户先在自己的 Guaranteed / Best-effort 队列做 quota admission；通过后进入对应的集群级队列。集群级排序先保证 Guaranteed 优先，再用平滑 QAD 让欠保障租户先恢复，只有在保障程度相近时才用预测剩余时间做短作业优化。QAD 因此负责跨租户公平，runtime prediction 只负责局部效率。</p></div>
</div>

## 关联模块

- `DeepShare / QAD 记忆模型`：分子、分母、特殊分支和 EMA。
- `DeepShare / 总体架构`：Controller、Scheduler Plugin、DaemonSet 的边界。
- `DeepShare / 论文延伸问答`：抢占效率、动态 retention 门槛和过载降级。
