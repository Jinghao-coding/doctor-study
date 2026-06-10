<div class="card card-s">
<h3>Kubernetes 架构图</h3>
<svg viewBox="0 0 920 520" role="img" aria-label="Kubernetes 架构图">
  <defs>
    <marker id="k8sArchArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#64748b" />
    </marker>
  </defs>

  <rect x="30" y="30" width="860" height="190" rx="18" fill="#eef6ff" stroke="#8bbcf6" />
  <text x="60" y="65" font-size="18" font-weight="700" fill="#1d4ed8">Control Plane</text>

  <rect x="365" y="82" width="190" height="62" rx="12" fill="#ffffff" stroke="#3b82f6" stroke-width="1.6" />
  <text x="420" y="108" font-size="14" font-weight="700" fill="#1e3a8a">API Server</text>
  <text x="390" y="130" font-size="11" fill="#475569">唯一直接读写 etcd 的入口</text>

  <rect x="80" y="95" width="150" height="55" rx="12" fill="#ffffff" stroke="#93c5fd" />
  <text x="135" y="127" font-size="14" fill="#1e3a8a">etcd</text>

  <rect x="305" y="165" width="150" height="42" rx="10" fill="#ffffff" stroke="#93c5fd" />
  <text x="332" y="191" font-size="13" fill="#1e3a8a">Scheduler</text>

  <rect x="495" y="165" width="190" height="42" rx="10" fill="#ffffff" stroke="#93c5fd" />
  <text x="528" y="191" font-size="13" fill="#1e3a8a">Controller Manager</text>

  <rect x="700" y="95" width="145" height="55" rx="12" fill="#ffffff" stroke="#93c5fd" />
  <text x="725" y="119" font-size="13" fill="#1e3a8a">kubectl /</text>
  <text x="725" y="138" font-size="13" fill="#1e3a8a">clients</text>

  <path d="M230 122 L365 113" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M365 119 L230 130" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M772 122 L555 113" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M390 165 L425 144" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M530 165 L500 144" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#k8sArchArrow)" />

  <rect x="30" y="285" width="395" height="185" rx="18" fill="#f0fdf4" stroke="#86efac" />
  <text x="60" y="320" font-size="18" font-weight="700" fill="#15803d">Worker Node A</text>
  <rect x="70" y="342" width="115" height="45" rx="10" fill="#ffffff" stroke="#86efac" />
  <text x="103" y="370" font-size="13" fill="#166534">kubelet</text>
  <rect x="210" y="342" width="150" height="45" rx="10" fill="#ffffff" stroke="#86efac" />
  <text x="232" y="370" font-size="13" fill="#166534">containerd / CRI</text>
  <rect x="70" y="405" width="90" height="38" rx="10" fill="#ffffff" stroke="#86efac" />
  <text x="101" y="429" font-size="12" fill="#166534">CNI</text>
  <rect x="174" y="405" width="105" height="38" rx="10" fill="#ffffff" stroke="#86efac" />
  <text x="195" y="429" font-size="12" fill="#166534">kube-proxy</text>
  <rect x="295" y="405" width="90" height="38" rx="10" fill="#ffffff" stroke="#86efac" />
  <text x="328" y="429" font-size="12" fill="#166534">Pods</text>

  <rect x="495" y="285" width="395" height="185" rx="18" fill="#f5f3ff" stroke="#c4b5fd" />
  <text x="525" y="320" font-size="18" font-weight="700" fill="#6d28d9">Worker Node B</text>
  <rect x="535" y="342" width="115" height="45" rx="10" fill="#ffffff" stroke="#c4b5fd" />
  <text x="568" y="370" font-size="13" fill="#5b21b6">kubelet</text>
  <rect x="675" y="342" width="150" height="45" rx="10" fill="#ffffff" stroke="#c4b5fd" />
  <text x="697" y="370" font-size="13" fill="#5b21b6">containerd / CRI</text>
  <rect x="535" y="405" width="90" height="38" rx="10" fill="#ffffff" stroke="#c4b5fd" />
  <text x="566" y="429" font-size="12" fill="#5b21b6">CNI</text>
  <rect x="639" y="405" width="105" height="38" rx="10" fill="#ffffff" stroke="#c4b5fd" />
  <text x="660" y="429" font-size="12" fill="#5b21b6">kube-proxy</text>
  <rect x="760" y="405" width="90" height="38" rx="10" fill="#ffffff" stroke="#c4b5fd" />
  <text x="793" y="429" font-size="12" fill="#5b21b6">Pods</text>

  <path d="M420 144 C360 235 130 245 128 342" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M500 144 C560 235 592 245 592 342" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M185 364 L210 364" stroke="#64748b" stroke-width="1.8" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M285 387 L340 405" stroke="#64748b" stroke-width="1.8" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M128 387 L115 405" stroke="#64748b" stroke-width="1.8" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M650 364 L675 364" stroke="#64748b" stroke-width="1.8" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M750 387 L805 405" stroke="#64748b" stroke-width="1.8" fill="none" marker-end="url(#k8sArchArrow)" />
  <path d="M592 387 L580 405" stroke="#64748b" stroke-width="1.8" fill="none" marker-end="url(#k8sArchArrow)" />

  <text x="65" y="500" font-size="12" fill="#64748b">关键点：Scheduler、Controller Manager、kubelet 都通过 API Server 协作；etcd 只保存状态，不直接驱动节点。</text>
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
<p>可以按“四段式”回答，主线是：<strong>所有控制面和节点组件都围绕 API Server 协作，etcd 只负责保存状态，真正执行发生在目标节点的 kubelet 上。</strong></p>
<ol>
<li><strong>入口：</strong>用户通过 <code>kubectl</code> 或 <code>client-go</code> 把 YAML 提交到 API Server。API Server 负责认证、鉴权、准入控制、对象校验和默认值填充；合法对象会<strong>通过 API Server</strong> 持久化到 etcd。这里要强调：通常只有 API Server 直接读写 etcd，其他组件通过 API Server watch 和更新对象。</li>
<li><strong>控制：</strong>如果提交的是 Deployment，Deployment Controller 会 watch API Server 中的对象变化，创建或维护 ReplicaSet；ReplicaSet Controller 再根据期望副本数创建、删除或修复 Pod。这个阶段体现的是 Kubernetes 的声明式 reconcile：用户写期望状态，controller 持续把实际状态逼近期望状态。</li>
<li><strong>调度：</strong>scheduler watch 到未调度、未绑定节点的 Pod 后，经过 Filter、Score、Reserve、Permit、Bind 等流程选择合适 Node。调度器不会直接通知 kubelet，而是把绑定结果写回 API Server，例如设置 Pod 的 <code>spec.nodeName</code> 或创建 Binding。后续 kubelet 是通过 watch API Server 才知道这个 Pod 归自己执行。</li>
<li><strong>执行：</strong>目标节点上的 kubelet watch 到绑定到本节点的 Pod 后，进入 Pod 生命周期执行流程：先准备 volume（CSI）、创建 Pod sandbox，再由网络插件（CNI）配置 Pod 网络，随后通过 CRI 调用 containerd / CRI-O 拉镜像、创建并启动业务容器。容器启动后，kubelet 继续执行探针、重启策略、资源状态采集，并把 Pod phase、container status、Node status 等状态回写到 API Server。</li>
</ol>
<div class="qa-summary">一句话总结：用户提交期望状态到 API Server，controller 负责创建和维护 Pod，scheduler 负责选 Node 并写回绑定结果，kubelet 在目标节点通过 CSI/CNI/CRI 把 Pod 真正跑起来，并持续向 API Server 上报状态。</div>
<p>追问时可以展开：etcd 一致性与 watch、Informer 缓存机制、scheduler 插件链路、绑定与抢占、kubelet Pod Worker、CSI/CNI/CRI 边界、探针和容器运行时。</p>
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

<div class="card card-m">

<h3>架构与 Pod 主链路高频问答</h3>

<p>本模块的问答按“概念 → 作用 → 链路/排查 → 面试口径”组织，避免只背一段结论。</p>

</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么说 Kubernetes 是声明式系统？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 概念</div><p>声明式系统的核心是用户提交“期望状态”，例如 Deployment 期望 3 个副本，而不是一步步命令系统创建哪几个容器。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 作用</div><p>声明式 API 让系统可以容错和自愈：Pod 被删、节点故障、实际副本数不匹配时，controller 会重新 reconcile。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 实现方式</div><p>API Server 保存 spec，controller 通过 Informer watch 对象变化，比较期望状态和实际状态，再创建、更新或删除相关对象。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 面试边界</div><p>etcd 保存状态，API Server 提供读写入口，controller 负责逼近期望状态；不要把 Kubernetes 理解成一次性脚本执行器。</p></div>
<div class="qa-summary">面试口径：Kubernetes 的声明式体现在“用户写 spec，controller 持续 reconcile，最终让实际状态逼近期望状态”。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: API Server、Controller、Scheduler、kubelet 都在 watch 什么？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. API Server 的位置</div><p>API Server 不只是被 watch 的对象入口，也是认证、鉴权、准入、版本转换和 watch 分发中心，其他组件基本都围绕它协作。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Controller watch 什么</div><p>Controller watch 自己关心的资源，例如 Deployment、ReplicaSet、Pod、Node，并根据 spec/status 差异执行 reconcile。</p></div>
<div class="qa-section"><div class="qa-section-title">3. Scheduler watch 什么</div><p>Scheduler 主要 watch 未绑定节点的 Pod，以及 Node、PVC、ResourceClaim 等会影响调度结果的对象。</p></div>
<div class="qa-section"><div class="qa-section-title">4. kubelet watch 什么</div><p>kubelet watch 绑定到本节点的 Pod，然后在节点侧准备 volume、网络和容器，并持续回写 Pod/Node 状态。</p></div>
<div class="qa-summary">面试口径：watch 机制让组件通过 API Server 解耦协作，Controller 管期望状态，Scheduler 管放置决策，kubelet 管节点执行。</div>
</div>
</div>
