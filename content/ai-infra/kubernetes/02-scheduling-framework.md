<div class="card card-m">
<h3>核心流程</h3>
<p>K8s 1.19+ 引入 Scheduling Framework，把调度流程拆成 <strong>11 个扩展点</strong>（extension points），每个扩展点可以挂载多个插件。调度一个 Pod 经过两个阶段：</p>

<h4>调度周期（Scheduling Cycle）——串行，对一个 Pod</h4>
<ol>
<li><strong>QueueSort</strong>：决定待调度队列中 Pod 的排序。默认按优先级降序 + 时间戳升序</li>
<li><strong>PreFilter</strong>：预处理和检查，计算 Pod 需要的资源汇总。如果检查失败直接拒绝，不进入后续流程</li>
<li><strong>Filter（预选）</strong>：遍历所有节点，排除不满足硬约束的。常见过滤条件：资源不足、NodeSelector 不匹配、Taint/Toleration 不满足、亲和性冲突。并行执行，默认取 min(numNodes, 100) 个可行节点后停止（percentageOfNodesToScore）</li>
<li><strong>PostFilter</strong>：当 Filter 没有找到任何可行节点时触发。默认行为是尝试抢占——找到优先级更低的 Pod 驱逐后能释放出足够资源的节点</li>
<li><strong>PreScore</strong>：Score 的预处理，可以共享计算结果给多个 Score 插件</li>
<li><strong>Score（优选）</strong>：对 Filter 通过的候选节点打分（0-100）。常见策略：LeastRequestedPriority（资源剩余最多）、BalancedResourceAllocation（CPU/内存比例均衡）、NodeAffinityPriority</li>
<li><strong>NormalizeScore</strong>：将各 Score 插件的分数归一化到 [0, 100]，然后加权求和</li>
<li><strong>Reserve</strong>：预占资源——在调度器缓存中扣减节点资源，防止后续 Pod 重复分配同一资源。这是乐观并发控制：先占再绑定</li>
</ol>

<h4>绑定周期（Binding Cycle）——可并行，多个 Pod 同时绑定</h4>
<ol start="9">
<li><strong>Permit</strong>：最终准入控制。三种决定：Approve（放行）、Deny（拒绝，回退 Reserve）、Wait（挂起，等条件满足后放行）</li>
<li><strong>PreBind</strong>：绑定前的准备工作，如挂载 PV</li>
<li><strong>Bind</strong>：写入 API Server，告诉 kubelet 在该节点启动 Pod</li>
<li><strong>PostBind</strong>：清理和通知，如更新指标、发事件</li>
</ol>
</div>

<div class="card card-m">
<h3>三个队列</h3>
<table>
<tr><th>队列</th><th>用途</th><th>流转条件</th></tr>
<tr><td>ActiveQ（活跃队列）</td><td>待调度的 Pod，按 QueueSort 排序</td><td>新 Pod 加入 / BackoffQ 到期 / 集群事件触发重试</td></tr>
<tr><td>BackoffQ（退避队列）</td><td>调度失败但可以重试的 Pod</td><td>等待指数退避时间（1s, 2s, 4s...最大 10s）后移入 ActiveQ</td></tr>
<tr><td>UnschedulableQ（不可调度队列）</td><td>当前集群状态下无法调度的 Pod</td><td>等待集群事件（节点加入、Pod 删除等）后移入 BackoffQ 或 ActiveQ</td></tr>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod 调度失败后的完整流转过程？</div>
<div class="qa-a">
<p>1. Pod 在 ActiveQ 中被取出调度</p>
<p>2. Filter 阶段找不到可行节点</p>
<p>3. PostFilter 尝试抢占，如果成功→标记 nominatedNode，Pod 回 ActiveQ 等待被抢占 Pod 终止</p>
<p>4. 如果抢占也失败→Pod 进入 UnschedulableQ</p>
<p>5. 集群发生变化（节点资源释放、新节点加入）→触发 Pod 移到 BackoffQ</p>
<p>6. 退避时间到期→Pod 移回 ActiveQ 重新调度</p>
</div>
</div>
</div>

<div class="card card-m">
<h3>抢占机制详解</h3>
<p>当一个高优先级 Pod 无法调度时，调度器尝试找到一个节点，驱逐上面优先级更低的 Pod 以释放资源：</p>
<ol>
<li><strong>候选筛选</strong>：遍历节点，模拟驱逐低优先级 Pod 后是否满足需求</li>
<li><strong>牺牲者选择</strong>：选择需要驱逐最少 Pod 的节点；同等条件下选择驱逐优先级最低 Pod 的方案</li>
<li><strong>优雅终止</strong>：被驱逐 Pod 收到 SIGTERM，等待 terminationGracePeriodSeconds 后强制终止</li>
<li><strong>PDB 保护</strong>：PodDisruptionBudget 可以限制同时被驱逐的 Pod 数量，保证服务可用性</li>
</ol>
</div>
