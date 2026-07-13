## 一句话结论

讲 DeepShare 时不要从 Kubernetes 扩展点开始。先讲“静态 quota 浪费、完全共享又破坏保障”的矛盾，再用 QAD 的“已兑现 / 该兑现”解释统一控制信号，最后展开 DRA、预测调度、colocation 和 Kubernetes 落地。

<div class="card card-w">
<h3>口述记忆骨架</h3>

```flow
矛盾 | 静态 quota 浪费，过度共享破坏 QoS
指标 | QAD = 已兑现 Guaranteed GPU / 当前应兑现 Guaranteed GPU
借还 | DRA 让 Best-effort 借空闲资源，Guaranteed 需要时可回收
排序 | 先 Q̃ 低的租户，再预测运行时间短的作业
共享 | 低 Q̃ 租户提高 retention 门槛，必要时停止新 colocation
落地 | Controller 管配置态，Scheduler Plugin 管实时控制环，DaemonSet 管 MPS/DCGM
结果 | 利用率、排队时间和 QoS 同时改善
```
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 请介绍一下 DeepShare。</div>
<div class="qa-a">
<p>DeepShare 解决的是多租户 GPU 集群里 quota 保障和资源效率之间的矛盾。严格静态 quota 会让暂时无人使用的 GPU 空闲；完全共享虽然利用率高，但原租户需求回来时可能拿不回承诺资源。</p>
<p>我们的核心设计是 QAD，也就是 Quota Assurance Degree。它衡量租户当前 Guaranteed 权益的兑现率：分子 <code>A_i^G(t)</code> 是已经分配的 Guaranteed GPU，分母 <code>min(q_i,D_i^G(t))</code> 是 quota 和当前 Guaranteed demand 取小，也就是平台此刻真正应该保障的 GPU 数。没有 Guaranteed demand 时 QAD 定义为 1；Best-effort 借用不计入分子，所以 QAD 位于 0 到 1。</p>
<p>我们再对瞬时 QAD 做 EMA 平滑，用同一个信号协调三个模块。第一，DRA 把空闲 capacity 给 Best-effort 作业使用，但资源保持可回收；第二，调度采用词典序，先让平滑 QAD 低的租户恢复，再用预测运行时间优化局部顺序；第三，GPU colocation 同时看 RF 预测的 throughput retention 和双方 QAD，任一租户欠保障时就提高共享门槛。</p>
<p>工程上，轻量 Controller 只 reconcile TenantQuota 和作业类别元数据，Scheduler Plugin 在内存里维护 QAD、队列、放置和抢占控制环，节点 DaemonSet 用 MPS 执行共享、用 DCGM 做运行时干扰保护。实验中系统把 GPU 利用率提升到 70.58%，租户 QoS 合规率达到 93%；在 16-GPU 部署中，结合 DRA 与 colocation 后 JCT 和排队时间也明显下降。</p>
<p>所以 DeepShare 的创新不只是一个排序算法，而是用 QAD 把弹性借用、预测调度和干扰感知共享闭环起来。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: QAD 这一段最短怎么说？</div>
<div class="qa-a"><p>QAD 就是租户 Guaranteed 权益的兑现率：分子是已经给到的 Guaranteed GPU，分母是 quota 和当前 Guaranteed demand 取小，也就是此刻应该给到的 GPU。需求为零时 QAD 记为 1；Best-effort 不计入分子。瞬时 QAD 再做 EMA 平滑，低 QAD 租户优先恢复，共享门槛也更严格。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 QAD 的分母不是 quota？</div>
<div class="qa-a"><p>因为 quota 是承诺上限，不是每时每刻都必须占满。quota 为 8、当前只需求 4、实际已给 4 时，租户已经完全被保障，QAD 应该是 1；如果直接除以 quota 会得到 0.5，错误地把主动空闲当成系统亏欠。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你在这篇工作里最核心的设计判断是什么？</div>
<div class="qa-a"><p>我认为最关键的不是单独引入短作业优先或 GPU 共享，而是让“租户保障是否兑现”成为所有优化之前的第一约束。预测运行时间只能在保障程度相近时优化局部顺序；低干扰 pair 也不能在租户欠保障时盲目共享。QAD 把公平和效率的优先级关系固定下来。</p></div>
</div>

## 容易说错的四句话

<table>
<thead><tr><th>不要这样说</th><th>应该这样说</th></tr></thead>
<tbody>
<tr><td>QAD 大于 1 表示借了额外资源</td><td>Best-effort 单独记账，不进入 QAD 分子</td></tr>
<tr><td>Controller 计算 QAD 写到 CRD</td><td>Scheduler Plugin 在内存中维护 QAD，故障后可从 Pod 重建</td></tr>
<tr><td>QAD 低就立刻杀 Best-effort</td><td>QAD 决定恢复优先级；placement failure 才触发抢占搜索</td></tr>
<tr><td>DeepShare 就是 SJF + GPU 共享</td><td>QAD 是第一控制信号，预测和共享都不能越过租户保障</td></tr>
</tbody>
</table>

## 关联模块

- `DeepShare / QAD 记忆模型`：数字例子和边界条件。
- `DeepShare / 总体架构`：论文实现的真实组件边界。
- `DeepShare / 高频问答`：DRF、MPS、过载与抢占追问。
