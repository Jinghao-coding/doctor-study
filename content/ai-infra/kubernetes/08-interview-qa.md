<div class="card card-m">
<h3>K8s 面试回答总模板</h3>
<p>复杂题建议用固定结构回答：<strong>先给结论，再讲链路，再讲异常排查，最后讲取舍和生产经验。</strong>不要只背概念名词，要能把对象、组件、控制循环和故障现象串起来。</p>
<table>
<tr><th>题型</th><th>回答结构</th><th>示例</th></tr>
<tr><td>原理题</td><td>定义 → 组件 → 流程 → 边界</td><td>Pod 如何启动、Service 如何转发</td></tr>
<tr><td>排障题</td><td>症状 → 链路拆解 → 命令观察 → 根因分类</td><td>Pending、CrashLoop、Service 不通</td></tr>
<tr><td>设计题</td><td>目标 → 约束 → 架构 → 风险 → 演进</td><td>多租户 GPU 集群、训练平台</td></tr>
<tr><td>对比题</td><td>共同点 → 差异 → 适用场景 → 误区</td><td>Deployment vs StatefulSet、DP vs DRA</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一个 Pod 从提交到运行经历哪些步骤？</div>
<div class="qa-a"><p>kubectl 把对象提交给 API Server，经过认证、鉴权、准入后写入 etcd。如果是 Deployment，controller 创建 ReplicaSet 和 Pod。scheduler watch 到未绑定 Pod 后执行过滤、打分、绑定。目标节点 kubelet watch 到 Pod 后调用 CSI 准备存储、CNI 准备网络、CRI 创建容器，并持续把状态回写 API Server。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod Pending 你会怎么排查？</div>
<div class="qa-a"><p>先看 <code>kubectl describe pod</code> Events。如果是 FailedScheduling，检查资源不足、污点容忍、nodeSelector/affinity、拓扑分布、优先级抢占。若提示 PVC，检查 PVC/StorageClass/CSI。若是 GPU，检查扩展资源、Device Plugin、DRA ResourceClaim/ResourceSlice。若是配额，检查 ResourceQuota、LimitRange 或队列准入。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: requests 和 limits 有什么区别？</div>
<div class="qa-a"><p>requests 主要影响调度和资源预留，scheduler 用它判断节点是否放得下；limits 是运行时上限，CPU 超限通常 throttling，内存超限通常 OOMKilled。QoS 也由 CPU/Memory 的 requests/limits 组合决定，影响节点压力下的驱逐顺序。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Deployment 和 StatefulSet 有什么区别？</div>
<div class="qa-a"><p>Deployment 管无状态副本，Pod 名称和存储不稳定，适合通过 Service 负载均衡。StatefulSet 管有状态副本，提供稳定序号、稳定网络身份和稳定 PVC，通常配合 Headless Service，用于数据库、消息队列或需要固定身份的训练组件。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Informer 为什么重要？</div>
<div class="qa-a"><p>Informer 通过 List/Watch 维护本地缓存，并把事件转成回调和 WorkQueue key。它减少控制器直接访问 API Server 的压力，支持事件驱动、缓存读取、失败重试和多 controller 共享 watch，是 Controller Pattern 的核心基础设施。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Service 不通怎么排查？</div>
<div class="qa-a"><p>先确认访问入口是 DNS、ClusterIP、NodePort 还是 LB。然后看 Service selector 是否匹配 Pod label、EndpointSlice 是否有 ready endpoints、Pod readiness 是否通过。再直接访问 Pod IP 区分应用问题和 Service 问题，最后检查 NetworkPolicy、CoreDNS、kube-proxy/eBPF、CNI 和节点网络。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Headless Service 和 ClusterIP Service 的区别？</div>
<div class="qa-a"><p>ClusterIP Service 有虚拟 IP，客户端访问 VIP 后由 kube-proxy 或 eBPF 转发到后端 Pod。Headless Service 没有 ClusterIP，DNS 直接返回后端 Pod 地址，常用于 StatefulSet 稳定域名、服务发现或客户端自行负载均衡。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: PVC Pending 怎么排查？</div>
<div class="qa-a"><p>看 PVC Events、StorageClass 是否存在、provisioner 是否运行、访问模式和容量是否满足。如果是 <code>WaitForFirstConsumer</code>，还要看使用该 PVC 的 Pod 是否能调度，以及卷拓扑和节点拓扑是否匹配。云盘或本地盘还要看可用区、配额和底层存储状态。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: RBAC、Admission、Pod Security 分别解决什么问题？</div>
<div class="qa-a"><p>RBAC 判断某个主体能否对某类资源执行某个动作；Admission 在对象写入前做变更或校验；Pod Security 限制 Pod 是否能使用特权、宿主机 namespace、危险 capabilities 等。它们处在 API Server 请求链路不同阶段，需要配合使用。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CrashLoopBackOff 怎么排查？</div>
<div class="qa-a"><p>先看当前日志和 <code>--previous</code> 日志，再看退出码、环境变量、配置、依赖服务和启动命令。若是 OOMKilled，看内存 limit 和应用内存曲线；若是探针导致重启，检查 liveness 是否过激、慢启动是否需要 startupProbe。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU Device Plugin 和普通调度有什么关系？</div>
<div class="qa-a"><p>Device Plugin 在节点上发现 GPU 并向 kubelet 注册扩展资源，kubelet 把数量写到 Node allocatable。scheduler 根据 Pod 中的 GPU limits 和节点可分配数量做调度。Pod 绑定到节点后，kubelet 调用 Device Plugin Allocate，把具体设备、环境变量、mount 或 CDI 信息交给容器运行时。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: <code>nvidia.com/a100</code>、<code>nvidia.com/v100</code> 不也是 Device Plugin 实现的吗？那 DRA 价值在哪里？</div>
<div class="qa-a"><p>是的，它们可以通过 Device Plugin 暴露，本质是把卡型编码进资源名。这能解决简单型号区分，但当要表达显存、MIG profile、NUMA、NVLink、健康状态、共享关系时，资源名和 label 会组合爆炸。DRA 的价值是用 ResourceSlice 发布结构化属性，用 ResourceClaim 和 CEL 表达需求，让 scheduler 做设备级匹配。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ResourceSlice 是谁创建的？大集群会不会很多？</div>
<div class="qa-a"><p>ResourceSlice 通常由 DRA driver 自动创建和维护，用户一般不手写。大集群会有很多 ResourceSlice，这是设计预期，因为它把设备库存从 Node status 中拆出来，避免 Node 对象膨胀和资源名爆炸。需要治理的是分片粒度、更新频率和 watch 压力。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CEL 表达式在 DRA 中怎么理解？</div>
<div class="qa-a"><p>CEL 是安全表达式语言，在 DRA 中可用于基于设备属性过滤候选设备。例如选择 model 为 A100、显存不少于 80Gi、同 NUMA 或特定 NVLink fabric 的设备。它的核心价值是从“申请某个资源名”变成“查询结构化设备属性”。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: DRA 和 Device Plugin 能不能同时使用？</div>
<div class="qa-a"><p>集群层面可以共存，但同一块物理设备不应同时由 DP 和 DRA 暴露，否则可能双重分配。更稳妥的方式是按 node pool、设备类型或灰度资源池隔离：一批节点继续用 Device Plugin，另一批节点用 DRA driver。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: DRA driver 是什么？如何获取？</div>
<div class="qa-a"><p>DRA driver 是 Kubernetes 侧设备资源驱动，不是 Linux 内核驱动。它负责发现设备、发布 ResourceSlice、协助 ResourceClaim 分配，并在 Pod 落到节点后 prepare/unprepare 设备。获取方式通常是厂商或社区提供的 Kubernetes 组件，例如 controller、node plugin、Helm chart 或 Operator。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 国产 GPU/NPU 厂商有没有 DRA driver，面试怎么回答？</div>
<div class="qa-a"><p>要谨慎回答公开成熟度。很多国产 GPU/NPU 生态更常见的是 Device Plugin、Operator、vGPU 或 HAMi 等方案，是否是真正 DRA driver 要看它是否使用 <code>resource.k8s.io</code> API、是否发布 ResourceSlice、DeviceClass、ResourceClaim，并支持 kubelet 的 prepare/unprepare 设备交付链路。</p></div>
</div>
