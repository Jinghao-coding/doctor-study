<div class="card card-m">
<h3>API Server 请求链路：认证、鉴权、准入</h3>
<p>Kubernetes 安全治理的核心入口是 API Server。所有写操作都要经过认证、鉴权、准入控制，再持久化到 etcd。面试中要能把这条链路讲清楚。</p>
<table>
<tr><th>阶段</th><th>问题</th><th>典型机制</th><th>面试要点</th></tr>
<tr><td>Authentication</td><td>你是谁？</td><td>证书、Bearer token、ServiceAccount token、OIDC</td><td>认证只确认身份，不决定能做什么</td></tr>
<tr><td>Authorization</td><td>你能做什么？</td><td>RBAC、Node、Webhook、ABAC</td><td>最常见是 RBAC，按 verb/resource/namespace 授权</td></tr>
<tr><td>Admission</td><td>这个请求是否允许或需要修改？</td><td>内置 admission、MutatingWebhook、ValidatingWebhook、ValidatingAdmissionPolicy</td><td>准入发生在鉴权之后、写入 etcd 之前</td></tr>
<tr><td>Persistence</td><td>状态如何保存？</td><td>etcd</td><td>最终状态写入 etcd 后，控制器通过 watch 感知变化</td></tr>
</table>
</div>

<div class="card card-s">
<h3>RBAC：Role、ClusterRole、Binding</h3>
<p>RBAC 是 Kubernetes 权限面试最高频部分。关键是区分“权限集合”和“把权限绑定给谁”。</p>
<table>
<tr><th>对象</th><th>作用域</th><th>作用</th><th>示例</th></tr>
<tr><td>Role</td><td>namespace 内</td><td>定义一组权限规则</td><td>允许读取 default namespace 下的 pods</td></tr>
<tr><td>ClusterRole</td><td>集群级</td><td>定义集群级或可复用权限规则</td><td>允许读取 nodes，或作为多个 namespace 的通用权限模板</td></tr>
<tr><td>RoleBinding</td><td>namespace 内</td><td>把 Role 或 ClusterRole 绑定给用户、组、ServiceAccount</td><td>把 read-pods 权限给某个 SA</td></tr>
<tr><td>ClusterRoleBinding</td><td>集群级</td><td>把 ClusterRole 绑定到集群范围</td><td>给集群管理员权限</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Role 和 ClusterRole 的区别是什么？</div>
<div class="qa-a">
<div class="qa-grid"><div class="qa-mini"><strong>Role</strong>只能定义 namespace 作用域内的资源权限。</div><div class="qa-mini"><strong>ClusterRole</strong>可以定义集群级资源权限，也可以作为跨 namespace 复用模板。</div><div class="qa-mini"><strong>RoleBinding</strong>可以绑定 Role，也可以绑定 ClusterRole，但权限只在该 namespace 生效。</div><div class="qa-mini"><strong>ClusterRoleBinding</strong>绑定后在集群范围生效，要谨慎使用。</div></div>
</div>
</div>
</div>

<div class="card card-w">
<h3>ServiceAccount 与 Pod 身份</h3>
<p>Pod 访问 API Server 时通常使用 ServiceAccount 身份。ServiceAccount token 会以投射卷形式挂载到 Pod 中，应用可以用它调用 Kubernetes API。</p>
<table>
<tr><th>概念</th><th>说明</th><th>高频点</th></tr>
<tr><td>ServiceAccount</td><td>面向 workload 的身份</td><td>不同于用户账号，常用于 Pod 内访问 API Server</td></tr>
<tr><td>automountServiceAccountToken</td><td>是否自动挂载 token</td><td>不需要访问 API 的 Pod 可关闭，降低凭证泄漏风险</td></tr>
<tr><td>TokenRequest</td><td>按需颁发短期 token</td><td>新版本推荐短期、可轮转 token，而非长期 secret token</td></tr>
<tr><td>RBAC Binding</td><td>给 ServiceAccount 授权</td><td>最小权限原则，只授予必要 verb/resource</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Admission Controller</h3>
<p>Admission Controller 可以在对象写入 etcd 前对请求进行默认值注入、校验、拒绝或变更。它是平台治理的重要抓手。</p>
<table>
<tr><th>类型</th><th>作用</th><th>典型场景</th></tr>
<tr><td>Mutating Admission</td><td>修改请求对象</td><td>自动注入 sidecar、默认资源 requests/limits、补充 labels/annotations</td></tr>
<tr><td>Validating Admission</td><td>校验请求对象</td><td>禁止 privileged、限制镜像仓库、要求必须设置 requests</td></tr>
<tr><td>ValidatingAdmissionPolicy</td><td>基于 CEL 的内置校验策略</td><td>不用部署 webhook 即可做部分策略校验</td></tr>
<tr><td>Webhook</td><td>调用外部服务做变更或校验</td><td>灵活强，但要注意可用性、超时和失败策略</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Admission Webhook 有什么生产风险？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">可用性风险</div><p>Webhook 服务不可用时，API 写请求可能被阻塞或失败，取决于 failurePolicy。</p></div>
<div class="qa-section"><div class="qa-section-title">性能风险</div><p>Webhook 增加 API Server 请求延迟，高并发集群下要控制超时和处理耗时。</p></div>
<div class="qa-section"><div class="qa-section-title">治理建议</div><p>设置合理 timeoutSeconds、namespaceSelector/objectSelector、failurePolicy，并监控 webhook 错误率和延迟。</p></div>
</div>
</div>
</div>

<div class="card card-s">
<h3>ResourceQuota 与 LimitRange</h3>
<p>多租户集群必须做资源治理，否则单个团队或任务可能耗尽整个集群资源。ResourceQuota 管 namespace 总量，LimitRange 管单个对象的默认值和上下限。</p>
<table>
<tr><th>对象</th><th>控制粒度</th><th>能限制什么</th><th>常见用途</th></tr>
<tr><td>ResourceQuota</td><td>namespace 总量</td><td>CPU/Memory requests 和 limits、PVC 数量、Service 数量、Pod 数量、GPU 扩展资源</td><td>限制租户总资源消耗</td></tr>
<tr><td>LimitRange</td><td>单个 Pod/Container/PVC</td><td>默认 requests/limits、最小/最大资源、limit/request ratio</td><td>防止用户不设置 requests 或设置过大/过小</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ResourceQuota 和 LimitRange 怎么配合？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">LimitRange</div><p>给单个容器设置默认 requests/limits 和上下限，避免用户漏填或填得不合理。</p></div>
<div class="qa-section"><div class="qa-section-title">ResourceQuota</div><p>限制 namespace 总资源使用量，确保一个租户不能无限创建 Pod 或 PVC。</p></div>
<div class="qa-summary">一句话：LimitRange 管单个对象，ResourceQuota 管整个 namespace。</div>
</div>
</div>
</div>

<div class="card card-w">
<h3>Pod Security 与运行时安全</h3>
<p>安全面试常问 privileged、hostPath、hostNetwork、capabilities、runAsNonRoot 等字段。重点是能解释风险，而不是只背字段名。</p>
<table>
<tr><th>字段/能力</th><th>风险</th><th>治理建议</th></tr>
<tr><td>privileged</td><td>容器获得接近宿主机 root 的能力</td><td>普通业务禁止，系统组件严格审批</td></tr>
<tr><td>hostPath</td><td>访问宿主机文件，可能读写敏感路径</td><td>限制路径白名单，尽量用 PVC 替代</td></tr>
<tr><td>hostNetwork</td><td>共享宿主机网络命名空间</td><td>端口冲突、网络隔离减弱，谨慎使用</td></tr>
<tr><td>capabilities</td><td>额外 Linux capabilities 扩大权限</td><td>默认 drop ALL，只按需添加</td></tr>
<tr><td>runAsNonRoot</td><td>root 运行增加逃逸风险</td><td>要求非 root 用户运行</td></tr>
<tr><td>readOnlyRootFilesystem</td><td>根文件系统可写增加篡改风险</td><td>尽可能只读，临时写入使用 emptyDir</td></tr>
</table>
</div>

<div class="card card-d">
<h3>CRD 与 Operator</h3>
<p>CRD 和 Operator 是 Kubernetes 扩展能力的核心。CRD 只是扩展 API 类型；Operator 是围绕 CRD 实现自动化运维逻辑的控制器。</p>
<table>
<tr><th>概念</th><th>作用</th><th>面试解释</th></tr>
<tr><td>CRD</td><td>注册自定义资源类型</td><td>让 API Server 能存储和校验新的对象，例如 TrainingJob、ModelService</td></tr>
<tr><td>Custom Resource</td><td>CRD 的实例</td><td>用户声明期望状态，例如副本数、模型路径、资源需求</td></tr>
<tr><td>Controller</td><td>监听资源变化并执行 reconcile</td><td>把实际状态收敛到期望状态</td></tr>
<tr><td>Operator</td><td>领域化控制器</td><td>把复杂系统的部署、升级、扩缩容、故障恢复自动化</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 Operator 适合复杂有状态服务？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">复杂流程</div><p>数据库、训练平台、模型服务往往有备份、扩容、主从切换、版本升级等领域流程，单靠 Deployment 难以表达。</p></div>
<div class="qa-section"><div class="qa-section-title">Reconcile</div><p>Operator 通过 Informer watch 资源变化，持续执行 reconcile，把实际状态修正到用户声明的期望状态。</p></div>
<div class="qa-summary">CRD 定义 API，Operator 实现自动化运维。</div>
</div>
</div>
</div>

<div class="card card-d">
<h3>官方参考</h3>
<div class="resource-grid">
<a class="resource-card" href="https://kubernetes.io/docs/reference/access-authn-authz/rbac/"><div class="resource-type">official</div><div class="resource-title">RBAC Authorization</div><div class="resource-desc">Role、ClusterRole、RoleBinding、ClusterRoleBinding。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/security/service-accounts/"><div class="resource-type">official</div><div class="resource-title">Service Accounts</div><div class="resource-desc">Pod 身份、ServiceAccount token 和访问 API Server。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/"><div class="resource-type">official</div><div class="resource-title">Admission Controllers</div><div class="resource-desc">准入控制器与请求处理链路。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/policy/resource-quotas/"><div class="resource-type">official</div><div class="resource-title">Resource Quotas</div><div class="resource-desc">namespace 级资源配额治理。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/"><div class="resource-type">official</div><div class="resource-title">Custom Resources</div><div class="resource-desc">CRD、自定义资源和 Kubernetes API 扩展。</div></a>
</div>
</div>
