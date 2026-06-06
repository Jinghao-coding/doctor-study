<div class="card card-m">
<h3>K8s 面试学习的总框架：先抓 Pod 主链路</h3>
<p>Kubernetes 面试不要按 API 对象百科式背诵，而要先建立一条主线：<strong>一个 Pod 从提交到运行，中间经过 API Server、etcd、scheduler、controller、kubelet、CRI、CNI、CSI 和容器运行时。</strong>后续所有问题，例如 Pending、Service 不通、PVC Pending、GPU 调度失败、Admission 拒绝，本质上都是这条链路上的某个阶段出了问题。</p>
<table>
<tr><th>学习模块</th><th>解决的核心问题</th><th>面试展开方式</th></tr>
<tr><td>架构与 Pod 主链路</td><td>Pod 如何从 YAML 变成节点上的容器</td><td>按请求链路讲 API Server、etcd、scheduler、kubelet</td></tr>
<tr><td>调度与资源模型</td><td>Pod 为什么能调度或不能调度</td><td>讲 requests/limits、QoS、Filter/Score、抢占、扩展资源</td></tr>
<tr><td>Workload 与 Controller</td><td>声明式系统如何持续逼近期望状态</td><td>讲 Deployment、StatefulSet、Job、Informer、Reconcile</td></tr>
<tr><td>网络与存储</td><td>Pod 如何通信、服务发现、挂载数据</td><td>讲 CNI、Service、DNS、PV/PVC、StorageClass、CSI</td></tr>
<tr><td>安全、准入与多租户</td><td>谁能做什么、请求能否进入集群、资源如何隔离</td><td>讲 AuthN/AuthZ/Admission、RBAC、Quota、Pod Security</td></tr>
<tr><td>故障排查与稳定性</td><td>线上异常如何定位和治理</td><td>按症状反推控制面、节点、网络、存储、资源</td></tr>
<tr><td>AI Infra：GPU / 批调度 / DRA</td><td>GPU、训练任务和异构资源如何接入 K8s</td><td>讲 Device Plugin、Gang、Kueue/Volcano、DRA</td></tr>
<tr><td>面试高频问答</td><td>把知识点转成回答模板</td><td>用“结论 → 原理 → 排查 → 权衡”回答</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Kubernetes 架构图</h3>
<svg viewBox="0 0 920 420" role="img" aria-label="Kubernetes 架构图">
  <rect x="30" y="30" width="860" height="150" rx="18" fill="#eef6ff" stroke="#8bbcf6" />
  <text x="60" y="65" font-size="18" font-weight="700" fill="#1d4ed8">Control Plane</text>
  <rect x="70" y="90" width="150" height="55" rx="12" fill="#ffffff" stroke="#93c5fd" />
  <text x="95" y="123" font-size="14" fill="#1e3a8a">API Server</text>
  <rect x="260" y="90" width="130" height="55" rx="12" fill="#ffffff" stroke="#93c5fd" />
  <text x="294" y="123" font-size="14" fill="#1e3a8a">etcd</text>
  <rect x="430" y="90" width="150" height="55" rx="12" fill="#ffffff" stroke="#93c5fd" />
  <text x="456" y="123" font-size="14" fill="#1e3a8a">Scheduler</text>
  <rect x="620" y="90" width="190" height="55" rx="12" fill="#ffffff" stroke="#93c5fd" />
  <text x="647" y="123" font-size="14" fill="#1e3a8a">Controller Manager</text>

  <rect x="30" y="230" width="395" height="145" rx="18" fill="#f0fdf4" stroke="#86efac" />
  <text x="60" y="265" font-size="18" font-weight="700" fill="#15803d">Worker Node A</text>
  <rect x="70" y="290" width="95" height="45" rx="10" fill="#ffffff" stroke="#86efac" />
  <text x="94" y="318" font-size="13" fill="#166534">kubelet</text>
  <rect x="185" y="290" width="85" height="45" rx="10" fill="#ffffff" stroke="#86efac" />
  <text x="208" y="318" font-size="13" fill="#166534">CRI</text>
  <rect x="290" y="290" width="95" height="45" rx="10" fill="#ffffff" stroke="#86efac" />
  <text x="313" y="318" font-size="13" fill="#166534">Pod</text>

  <rect x="495" y="230" width="395" height="145" rx="18" fill="#f5f3ff" stroke="#c4b5fd" />
  <text x="525" y="265" font-size="18" font-weight="700" fill="#6d28d9">Worker Node B</text>
  <rect x="535" y="290" width="95" height="45" rx="10" fill="#ffffff" stroke="#c4b5fd" />
  <text x="559" y="318" font-size="13" fill="#5b21b6">kubelet</text>
  <rect x="650" y="290" width="85" height="45" rx="10" fill="#ffffff" stroke="#c4b5fd" />
  <text x="673" y="318" font-size="13" fill="#5b21b6">CNI</text>
  <rect x="755" y="290" width="95" height="45" rx="10" fill="#ffffff" stroke="#c4b5fd" />
  <text x="778" y="318" font-size="13" fill="#5b21b6">Pod</text>

  <path d="M220 116 L260 116" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />
  <path d="M390 116 L430 116" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />
  <path d="M505 145 C505 205 120 205 120 290" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#arrow)" />
  <path d="M715 145 C715 205 585 205 585 290" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#arrow)" />
  <defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#64748b" /></marker></defs>
</svg>
</div>

<div class="card card-m">
<h3>一个 Pod 从提交到运行的完整链路</h3>
<table>
<tr><th>阶段</th><th>核心组件</th><th>发生什么</th><th>面试关键词</th></tr>
<tr><td>提交请求</td><td>kubectl / client-go → API Server</td><td>用户提交 Pod、Deployment、Job 等资源对象</td><td>REST API、OpenAPI、版本转换</td></tr>
<tr><td>认证鉴权</td><td>API Server</td><td>检查调用者是谁、有没有权限、是否满足准入策略</td><td>Authentication、Authorization、Admission</td></tr>
<tr><td>持久化</td><td>API Server → etcd</td><td>合法对象被写入 etcd，成为集群期望状态</td><td>声明式 API、resourceVersion、watch</td></tr>
<tr><td>控制器处理</td><td>Controller Manager</td><td>Deployment 创建 ReplicaSet，ReplicaSet 创建 Pod</td><td>Reconcile、OwnerReference、Finalizer</td></tr>
<tr><td>调度决策</td><td>kube-scheduler</td><td>监听未绑定 Pod，经过 Filter / Score / Reserve / Bind 选择节点</td><td>Scheduling Framework、requests、亲和性、污点容忍</td></tr>
<tr><td>节点执行</td><td>kubelet</td><td>目标节点 kubelet watch 到 Pod，准备 volume、网络、容器</td><td>Pod Worker、PLEG、CNI、CSI、CRI</td></tr>
<tr><td>运行容器</td><td>containerd / CRI-O</td><td>拉镜像、创建 sandbox、启动容器并持续上报状态</td><td>Pause 容器、Pod IP、探针、状态回写</td></tr>
</table>
</div>

<div class="card card-w">
<h3>面试回答模板：Pod 是怎么跑起来的？</h3>
<p>可以按“四段式”回答：</p>
<ol>
<li><strong>入口：</strong>用户把 YAML 提交到 API Server，经过认证、鉴权、准入后写入 etcd。</li>
<li><strong>控制：</strong>如果是 Deployment，controller 会创建 ReplicaSet，再由 ReplicaSet 创建 Pod。</li>
<li><strong>调度：</strong>scheduler 监听没有 <code>nodeName</code> 的 Pod，经过过滤、打分、抢占等流程绑定到某个 Node。</li>
<li><strong>执行：</strong>节点 kubelet 看到绑定到本节点的 Pod 后，调用 CSI 准备存储、CNI 准备网络、CRI 创建容器，并把状态回写到 API Server。</li>
</ol>
<p>追问时再展开 etcd 一致性、Informer watch、scheduler 插件、kubelet Pod Worker、探针和容器运行时。</p>
</div>

<div class="card card-d">
<h3>控制面与数据面组件速记</h3>
<table>
<tr><th>组件</th><th>职责</th><th>常见追问</th></tr>
<tr><td>API Server</td><td>所有资源操作入口，负责认证、鉴权、准入、聚合 API、watch</td><td>为什么它是唯一直接访问 etcd 的组件？</td></tr>
<tr><td>etcd</td><td>保存集群期望状态和关键元数据</td><td>备份恢复、watch、resourceVersion、压缩与碎片整理</td></tr>
<tr><td>Scheduler</td><td>为未绑定 Pod 选择节点</td><td>Filter / Score / Reserve / Permit / Bind 的区别</td></tr>
<tr><td>Controller Manager</td><td>运行 Deployment、ReplicaSet、Node、Job 等控制循环</td><td>什么是 reconcile？如何处理最终一致性？</td></tr>
<tr><td>kubelet</td><td>节点代理，负责 Pod 生命周期和状态上报</td><td>kubelet 如何调用 CRI / CNI / CSI？</td></tr>
<tr><td>kube-proxy / eBPF datapath</td><td>实现 Service 转发或服务负载均衡</td><td>iptables、IPVS、eBPF 的差异</td></tr>
<tr><td>Container Runtime</td><td>真正创建和管理容器</td><td>CRI、containerd、pause 容器、镜像拉取</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么说 Kubernetes 是声明式系统？</div>
<div class="qa-a"><p>用户提交的是期望状态，例如“我要 3 个副本”，控制器持续 watch 实际状态并通过 reconcile 把实际状态逼近期望状态。它不是一次性命令式脚本，而是由 API 对象、控制循环和最终一致性共同组成的系统。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: API Server、Controller、Scheduler、kubelet 都在 watch 什么？</div>
<div class="qa-a"><p>Controller watch 自己关心的资源并维护派生对象，scheduler watch 未调度 Pod 和节点/资源变化，kubelet watch 绑定到本节点的 Pod。watch 机制减少轮询压力，也让各组件围绕 API Server 解耦。</p></div>
</div>
