<div class="card card-m">
<h3>安全、准入与多租户：请求能不能进入，资源能不能隔离</h3>
<p>Kubernetes 安全链路可以概括为：<strong>Authentication 识别你是谁，Authorization 判断你能做什么，Admission 决定这个请求是否符合集群策略，Persistence 才会写入 etcd。</strong>多租户治理则在此基础上叠加 namespace、RBAC、Quota、LimitRange、Pod Security、PriorityClass 和队列配额。</p>
</div>

<div class="card card-s">
<h3>API Server 请求链路</h3>
<table>
<tr><th>阶段</th><th>作用</th><th>常见机制</th><th>面试重点</th></tr>
<tr><td>Authentication</td><td>确认调用者身份</td><td>证书、Token、OIDC、ServiceAccount</td><td>未认证通常是 anonymous 或直接拒绝</td></tr>
<tr><td>Authorization</td><td>判断是否有权限</td><td>RBAC、Node、Webhook</td><td>RBAC 是 allow-only，没有显式 deny</td></tr>
<tr><td>Mutating Admission</td><td>修改请求对象</td><td>默认值注入、sidecar 注入</td><td>先变更再校验</td></tr>
<tr><td>Validating Admission</td><td>校验请求对象</td><td>Webhook、ValidatingAdmissionPolicy</td><td>策略不通过则拒绝写入</td></tr>
<tr><td>Persistence</td><td>写入 etcd</td><td>storage layer</td><td>写入后其他组件通过 watch 感知</td></tr>
</table>
</div>

<div class="card card-d">
<h3>RBAC 与 ServiceAccount</h3>
<table>
<tr><th>对象</th><th>作用</th><th>注意点</th></tr>
<tr><td>Role</td><td>namespace 级权限集合</td><td>只能授予本 namespace 内资源权限</td></tr>
<tr><td>ClusterRole</td><td>集群级权限集合</td><td>可用于集群资源，也可被 RoleBinding 绑定到 namespace</td></tr>
<tr><td>RoleBinding</td><td>把 Role/ClusterRole 授给主体</td><td>作用域是 namespace</td></tr>
<tr><td>ClusterRoleBinding</td><td>集群范围授权</td><td>权限很大，生产要谨慎</td></tr>
<tr><td>ServiceAccount</td><td>Pod 内访问 API Server 的身份</td><td>配合最小权限原则</td></tr>
</table>
<p>回答 RBAC 时要强调“主体 subject、动作 verb、资源 resource、作用域 namespace/cluster”四个维度。</p>
</div>

<div class="card card-w">
<h3>Admission、Webhook 与策略治理</h3>
<table>
<tr><th>机制</th><th>适合做什么</th><th>风险/注意点</th></tr>
<tr><td>MutatingAdmissionWebhook</td><td>注入 sidecar、默认资源、镜像仓库前缀</td><td>要避免循环变更和高延迟</td></tr>
<tr><td>ValidatingAdmissionWebhook</td><td>拒绝不合规镜像、特权容器、非法标签</td><td>Webhook 故障可能影响 API 写入</td></tr>
<tr><td>ValidatingAdmissionPolicy</td><td>用 CEL 写内置校验策略</td><td>适合轻量规则，减少外部 webhook 依赖</td></tr>
<tr><td>Pod Security</td><td>限制特权、宿主机 namespace、危险能力</td><td>按 namespace enforce/audit/warn 逐步推进</td></tr>
<tr><td>OPA/Gatekeeper/Kyverno</td><td>更完整的策略即代码</td><td>需要治理策略复杂度和误伤</td></tr>
</table>
</div>

<div class="card card-m">
<h3>多租户资源治理</h3>
<table>
<tr><th>机制</th><th>解决的问题</th><th>AI Infra 场景</th></tr>
<tr><td>Namespace</td><td>基础隔离边界</td><td>按团队、项目、环境隔离</td></tr>
<tr><td>ResourceQuota</td><td>限制 namespace 资源总量</td><td>限制 CPU、内存、Pod 数、PVC、GPU 扩展资源</td></tr>
<tr><td>LimitRange</td><td>设置单 Pod/容器默认值和上下限</td><td>防止用户不写 requests 或申请过大</td></tr>
<tr><td>PriorityClass</td><td>定义任务优先级</td><td>线上推理优先于离线训练，关键任务可抢占</td></tr>
<tr><td>Queue</td><td>批任务排队和准入</td><td>Kueue/Volcano 按队列管理训练任务</td></tr>
<tr><td>Quota borrowing</td><td>空闲配额可临时借用</td><td>提升 GPU 利用率</td></tr>
<tr><td>Reclaim</td><td>高优任务需要资源时回收借用资源</td><td>保证关键队列 SLA</td></tr>
</table>
</div>

<div class="card card-r">
<h3>安全题常见误区</h3>
<ul>
<li>不要把 RBAC 和 NetworkPolicy 混为一谈：RBAC 管 API 权限，NetworkPolicy 管网络流量。</li>
<li>不要认为 namespace 是强安全隔离：它是逻辑隔离，还需要 RBAC、Quota、NetworkPolicy、Pod Security 配合。</li>
<li>不要让 Webhook 无超时、无降级策略：它可能成为 API Server 写路径上的稳定性风险。</li>
<li>不要给默认 ServiceAccount 过大权限：Pod 被攻陷后会扩大影响面。</li>
<li>不要只限制 CPU/内存而忘记扩展资源：GPU 集群要把 <code>nvidia.com/gpu</code>、NPU 等纳入 Quota。</li>
</ul>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一个用户说自己没有权限创建 Pod，怎么排查？</div>
<div class="qa-a"><p>先确认用户身份和 namespace，再用 <code>kubectl auth can-i create pods -n xxx --as user</code> 验证 RBAC。然后检查 Role/ClusterRole、RoleBinding/ClusterRoleBinding 是否绑定正确。如果 RBAC 允许但仍失败，再看 Admission Webhook、Quota、Pod Security 等是否拒绝。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 多租户 GPU 集群如何做公平性和利用率平衡？</div>
<div class="qa-a"><p>基础层用 namespace、RBAC、ResourceQuota 做隔离；调度层用队列、PriorityClass、Gang Scheduling 做准入；资源层支持 borrowing 提升利用率，关键任务到来时 reclaim；运行层配合监控、审计和准入策略限制特权容器、非法镜像和越权访问。</p></div>
</div>
