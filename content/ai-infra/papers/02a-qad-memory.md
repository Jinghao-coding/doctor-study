## 一句话结论

QAD 不是“这个租户用了多少资源”，而是“这个租户当前**应被保障的 Guaranteed GPU 中，已经兑现了多少**”。最稳的记忆方式只有一句：**分子是已兑现，分母是该兑现，QAD 是兑现率。**

<div class="card card-m">
<h3>先把完整公式记对</h3>
<div class="formula">$$
Q_i(t)=
\begin{cases}
1, & D_i^G(t)=0,\\
\dfrac{A_i^G(t)}{\min\!\left(q_i, D_i^G(t)\right)}, & D_i^G(t)>0.
\end{cases}
$$</div>

<table>
<thead><tr><th>符号</th><th>含义</th><th>记忆问题</th></tr></thead>
<tbody>
<tr><td><code>i</code></td><td>第 <code>i</code> 个租户</td><td>在看谁？</td></tr>
<tr><td><code>q_i</code></td><td>平台承诺给租户的 Guaranteed GPU quota</td><td>最多承诺多少？</td></tr>
<tr><td><code>D_i^G(t)</code></td><td>时刻 <code>t</code> 租户当前提出的 Guaranteed GPU 需求</td><td>现在想要多少？</td></tr>
<tr><td><code>A_i^G(t)</code></td><td>时刻 <code>t</code> 已经分配并运行的 Guaranteed GPU</td><td>现在实际兑现多少？</td></tr>
<tr><td><code>min(q_i, D_i^G(t))</code></td><td>平台此刻真正应该保障的 GPU 数</td><td>现在该兑现多少？</td></tr>
</tbody>
</table>

<div class="qa-summary">分子 <code>A_i^G(t)</code>：已经给到的 Guaranteed GPU；分母 <code>min(q_i,D_i^G(t))</code>：当前应该给到的 Guaranteed GPU；两者相除就是保障兑现率。</div>
</div>

## 为什么分母一定是 `min(quota, demand)`

<div class="card card-s">
<h3>分母不是 quota，也不是 demand，而是“当前应保障量”</h3>
<ul>
<li>当 <code>demand &lt; quota</code>：租户只申请了 4 张，即使 quota 是 8，平台此刻也只欠它 4 张；分母取 demand。</li>
<li>当 <code>demand &gt; quota</code>：租户申请了 12 张，但平台只承诺 8 张；分母取 quota。</li>
<li>因此租户既不会因为暂时没用满 quota 被判定为“受损”，也不能靠提交超大需求压低 QAD、抬高恢复优先级。</li>
</ul>
<p><strong>记忆口令：</strong><code>想要多少 D</code>、<code>承诺多少 q</code>，二者取小才是系统此刻“该给多少”。</p>
</div>

## 用一个数字例子把边界钉死

假设租户 A 的 quota 为 `q_A = 8` 张 GPU：

<table>
<thead><tr><th>场景</th><th><code>D_A^G</code></th><th><code>A_A^G</code></th><th>分母</th><th>QAD</th><th>含义</th></tr></thead>
<tbody>
<tr><td>暂时没有 Guaranteed 作业</td><td>0</td><td>0</td><td>特殊分支</td><td>1</td><td>没有未兑现的保障，不算欠它</td></tr>
<tr><td>只需要 4 张，目前给了 2 张</td><td>4</td><td>2</td><td><code>min(8,4)=4</code></td><td>0.5</td><td>当前保障只兑现了一半</td></tr>
<tr><td>只需要 4 张，目前给满 4 张</td><td>4</td><td>4</td><td><code>min(8,4)=4</code></td><td>1</td><td>当前需求已完全保障</td></tr>
<tr><td>需要 12 张，目前给了 4 张</td><td>12</td><td>4</td><td><code>min(8,12)=8</code></td><td>0.5</td><td>承诺的 8 张只兑现了一半</td></tr>
<tr><td>Guaranteed 给满 8 张，另有 4 张 Best-effort</td><td>12</td><td>8</td><td><code>min(8,12)=8</code></td><td>1</td><td>借来的 4 张不进入分子，QAD 不是 1.5</td></tr>
</tbody>
</table>

<div class="card card-w">
<h3>最容易答错的边界</h3>
<p>论文中的 <code>A_i^G(t)</code> 只统计 Guaranteed allocation；Best-effort allocation 不进入分子，因此不会把 QAD “冲高”。在 DeepShare 的定义和准入约束下，<code>Q_i(t) ∈ [0,1]</code>：<code>1</code> 表示应兑现的保障已经满足，低于 <code>1</code> 才表示存在 deficit。</p>
</div>

## 瞬时 QAD 和调度用 QAD 不要混

<div class="card card-s">
<h3>一个看快照，一个做控制</h3>
<div class="formula">$$\tilde{Q}_i(t)=\lambda Q_i(t)+(1-\lambda)\tilde{Q}_i(t-1),\qquad \lambda=0.3$$</div>
<table>
<thead><tr><th>量</th><th>回答的问题</th><th>用途</th></tr></thead>
<tbody>
<tr><td><code>Q_i(t)</code></td><td>这一时刻保障兑现了多少？</td><td>瞬时观测值</td></tr>
<tr><td><code>Q̃_i(t)</code></td><td>这个租户是否持续处于保障不足？</td><td>队列排序、回收优先级、colocation 收紧</td></tr>
</tbody>
</table>
<p>EMA 是为了过滤短作业完成和突发到达造成的亚秒级抖动。论文设置 50ms 调度周期和 <code>λ=0.3</code>，持续 deficit 大约 350ms 就能体现 90% 的稳态影响。</p>
</div>

## QAD 怎么驱动 DeepShare

```flow
统计 Guaranteed demand 与 allocation | 得到瞬时 Q_i(t)
EMA 平滑 | 得到控制信号 Q̃_i(t)
租户恢复排序 | Q̃ 低的租户先恢复，预测运行时间只做第二排序键
资源回收 | Guaranteed 放置失败时，先回收可让渡资源，再做低代价 Best-effort 抢占
共享准入 | 任一租户 Q̃ 低时提高 retention 门槛，必要时停止新 colocation
```

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官问“QAD 是什么”，怎么一口气讲清楚？</div>
<div class="qa-a">
<p>QAD 是租户级的配额保障兑现率。分子 <code>A_i^G(t)</code> 是当前已经分配的 Guaranteed GPU，分母 <code>min(q_i,D_i^G(t))</code> 是平台此刻真正应该保障的 GPU 数：需求小于 quota 时只保障实际需求，需求超过 quota 时最多保障 quota。如果当前没有 Guaranteed demand，就把 QAD 定义为 1，因为没有未兑现的权益。Best-effort 借用不计入分子，所以 QAD 落在 0 到 1。系统再对瞬时 QAD 做 EMA 平滑，用平滑值优先恢复欠保障租户，并收紧它们的 GPU 共享。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不能直接用 allocation / quota？</div>
<div class="qa-a"><p>因为租户当前可能只需要 quota 的一小部分。若 quota 是 8、需求只有 4、实际已给 4，用 allocation/quota 会得到 0.5，错误地认为租户受损；DeepShare 用 <code>min(quota, demand)</code> 后得到 1，表示当前需求已完全兑现。</p></div>
</div>

## 常见误区

<table>
<thead><tr><th>错误记法</th><th>正确理解</th></tr></thead>
<tbody>
<tr><td>QAD = 总 GPU 使用量 / quota</td><td>分子只算 Guaranteed allocation，不算 Best-effort</td></tr>
<tr><td>分母永远是 quota</td><td>分母是 <code>min(quota, 当前 Guaranteed demand)</code></td></tr>
<tr><td>没有需求时 QAD = 0</td><td>没有未兑现保障，论文显式定义为 1</td></tr>
<tr><td>借到额外资源后 QAD &gt; 1</td><td>借用量不进入分子，QAD 保持在 0 到 1</td></tr>
<tr><td>运行时间短的作业永远优先</td><td>先按平滑 QAD 恢复欠保障租户，再用预测时间优化局部顺序</td></tr>
</tbody>
</table>

## 关联模块

- `DeepShare / 概述与设计`：QAD 为什么能统一 DRA、预测调度与干扰感知合用。
- `DeepShare / K8S 实现细节`：QAD 在 Scheduler Plugin 的实时控制环中如何维护和消费。
- `DeepShare / 论文延伸问答`：EMA、过载恢复和动态 colocation 门槛的论文级追问。
