## Workload 与发布

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Deployment、StatefulSet、DaemonSet、Job 怎么选？</div>
<div class="qa-a">
<div class="qa-summary">Deployment 管可替换的无状态副本；StatefulSet 管有稳定身份和独立存储的副本；DaemonSet 管每个符合条件的节点一个 Pod；Job 管运行到完成的任务。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>在线无状态服务通常用 Deployment；数据库、协调组件等需要固定 ordinal、稳定 DNS 或 PVC 模板时用 StatefulSet；CNI、日志 Agent、Device Plugin 用 DaemonSet；数据预处理和模型转换用 Job。CronJob 只负责按时间创建 Job。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>StatefulSet 不自动解决数据一致性，DaemonSet 也只覆盖满足 selector、affinity 和 toleration 的节点。</p></div>
<div class="qa-section"><div class="qa-section-title">关联章节</div><p><code>Workload 与 Controller</code>。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Deployment 滚动更新是怎么完成的？</div>
<div class="qa-a">
<div class="qa-summary">Deployment 创建新 ReplicaSet，并在 <code>maxSurge</code>、<code>maxUnavailable</code> 约束下逐步扩新缩旧；Readiness 决定新 Pod 何时能接流量。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Pod Template 改变后 Deployment Controller 创建新 ReplicaSet，同时按策略调整新旧副本数。只有新 Pod Ready 后 EndpointSlice 才接入它；发布异常时通过 progress deadline、事件和 ReplicaSet 状态定位，并可回滚到历史 revision。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Pod 进入 Running 不代表已经 Ready；PDB 主要约束主动驱逐，不直接控制 Deployment 的滚动更新数量。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Liveness、Readiness、Startup Probe 有什么区别？</div>
<div class="qa-a">
<div class="qa-summary">Liveness 决定是否重启容器，Readiness 决定是否接收流量，Startup Probe 在慢启动阶段保护前两种探针。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Readiness 失败会把 Pod 从 EndpointSlice 摘除但不会重启；Liveness 连续失败由 kubelet 重启容器；配置 Startup Probe 后，在它成功前不会执行 Liveness 和 Readiness。阈值应根据真实启动时间和故障恢复时间设置。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>不要用 Liveness 检查慢依赖，否则依赖抖动会制造重启风暴；Readiness 也不应该只检查进程是否存在。</p></div>
</div></div>

## 网络与服务发现

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 访问一个 Service 时，流量经过哪些组件？</div>
<div class="qa-a">
<div class="qa-summary">客户端先通过 DNS 得到 Service 地址，Service Controller 维护 EndpointSlice，节点上的 kube-proxy 或 eBPF 数据面把流量转发到 Ready Pod。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Service 是 API 对象，不是一个代理进程。CoreDNS 负责名称解析，EndpointSlice 由 selector 和 Pod Ready 状态生成，iptables/IPVS/eBPF 规则完成负载均衡。排障要分别验证 DNS、ClusterIP、EndpointSlice、端口和跨节点数据面。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p><code>targetPort</code> 指向 Pod 监听端口；Pod Running 但不 Ready 时通常不会出现在可服务端点中。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Headless Service 有什么用？</div>
<div class="qa-a">
<div class="qa-summary">Headless Service 设置 <code>clusterIP: None</code>，不提供统一虚拟 IP，而是让 DNS 直接返回后端 Pod 地址。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>它适合客户端需要自己做服务发现、选主、分片或直连固定副本的场景，常与 StatefulSet 配合形成稳定 DNS，例如 <code>pod-0.service.namespace.svc</code>。它和 StatefulSet 常一起使用，但并非强绑定。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Headless 不代表没有 Service，也不代表自动获得负载均衡。</p></div>
</div></div>

## 存储、安全与弹性

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: PV、PVC、StorageClass 和 CSI 是什么关系？</div>
<div class="qa-a">
<div class="qa-summary">PVC 表达应用的存储需求，PV 表达可绑定的存储资源，StorageClass 描述动态供给策略，CSI Driver 完成创建、Attach 和 Mount。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>用户创建 PVC 后，外部 provisioner 可根据 StorageClass 创建 PV；调度器还要考虑 volume topology 和 binding mode。Pod 落到节点后，Attach/Detach Controller 与 kubelet Volume Manager 调用 CSI Controller/Node 插件完成挂载。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>PVC Bound 只说明逻辑绑定成功，不代表节点侧 Attach、格式化、权限和 Mount 一定成功。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ConfigMap 和 Secret 更新后，容器会自动拿到新值吗？</div>
<div class="qa-a">
<div class="qa-summary">通过环境变量注入的值不会自动更新；通过 Volume 投射的文件会最终更新但存在传播延迟，应用还必须主动重载。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>环境变量在容器创建时固定，需要重建 Pod。Volume 方式由 kubelet 周期同步，但使用 <code>subPath</code> 的挂载通常不会随源对象更新。Secret 的 base64 只是编码，生产还需 etcd 静态加密、RBAC 最小权限和外部密钥管理。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>常用做法是配置版本哈希触发 Deployment 滚动更新，或使用支持热加载的 sidecar/reloader。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: RBAC、Admission 和 Pod Security 分别解决什么问题？</div>
<div class="qa-a">
<div class="qa-summary">RBAC 决定谁能对什么资源执行什么动作；Admission 在写入前变更或校验对象；Pod Security Admission 专门约束 Pod 的安全上下文。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>请求先经过认证，再由 RBAC 等授权器鉴权，之后进入 Mutating/Validating Admission，最终完成 schema 校验并写入存储。多租户还需要 Namespace、NetworkPolicy、Quota、Secret 管理和审计共同构成边界。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>ServiceAccount 是工作负载身份，不等于授权策略；Secret 默认也不是不可读取的密文。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: HPA、VPA、Cluster Autoscaler 和 Karpenter 的边界是什么？</div>
<div class="qa-a">
<div class="qa-summary">HPA 调 Pod 副本，VPA 调单 Pod 资源建议或请求，Cluster Autoscaler/Karpenter 调节点容量；扩 Pod 和扩节点是两个控制回路。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>HPA 根据指标修改 replicas；VPA 根据历史用量调整 requests，可能需要重建 Pod；CA 从不可调度 Pod 推导节点组扩容；Karpenter 直接根据 Pod 约束选择节点规格并持续整合。GPU 节点还要等待 Driver、Device Plugin 和镜像预热完成。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>只提高 HPA 副本不保证有节点可运行；只看 GPU-Util 也不足以决定在线推理扩缩容。</p></div>
</div></div>
