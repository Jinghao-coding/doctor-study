<div class="k8s-arch">
<svg viewBox="0 0 720 480" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;border-radius:16px;background:var(--card-solid);border:1px solid var(--border)">
<defs>
<linearGradient id="cpGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="var(--pri-l)"/><stop offset="100%" stop-color="rgba(37,99,235,.08)"/></linearGradient>
<linearGradient id="dpGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="var(--sec-l)"/><stop offset="100%" stop-color="rgba(5,150,105,.08)"/></linearGradient>
<filter id="shadow"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-opacity=".12"/></filter>
</defs>

<marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="var(--border)"/></marker>

<rect x="20" y="20" width="680" height="210" rx="18" fill="url(#cpGrad)" stroke="var(--pri)" stroke-opacity=".35" class="k8s-box"/>
<text x="40" y="50" class="k8s-subtitle">Control Plane（控制面）</text>

<rect x="45" y="70" width="145" height="75" rx="10" fill="var(--card-solid)" stroke="var(--pri)" stroke-opacity=".5" filter="url(#shadow)" class="k8s-comp"/>
<text x="117" y="98" text-anchor="middle" class="k8s-label">kube-apiserver</text>
<text x="117" y="116" text-anchor="middle" class="k8s-desc">API 网关 · 所有操作入口</text>
<text x="117" y="132" text-anchor="middle" class="k8s-desc">无状态，可水平扩展</text>

<rect x="205" y="70" width="130" height="75" rx="10" fill="var(--card-solid)" stroke="var(--pri)" stroke-opacity=".5" filter="url(#shadow)" class="k8s-comp"/>
<text x="270" y="98" text-anchor="middle" class="k8s-label">etcd</text>
<text x="270" y="116" text-anchor="middle" class="k8s-desc">分布式 KV 存储</text>
<text x="270" y="132" text-anchor="middle" class="k8s-desc">Raft 共识 · 唯一持久化</text>

<rect x="350" y="70" width="145" height="75" rx="10" fill="var(--card-solid)" stroke="var(--pri)" stroke-opacity=".5" filter="url(#shadow)" class="k8s-comp"/>
<text x="422" y="98" text-anchor="middle" class="k8s-label">kube-scheduler</text>
<text x="422" y="116" text-anchor="middle" class="k8s-desc">Pod → 节点绑定</text>
<text x="422" y="132" text-anchor="middle" class="k8s-desc">Scheduling Framework</text>

<rect x="510" y="70" width="170" height="75" rx="10" fill="var(--card-solid)" stroke="var(--pri)" stroke-opacity=".5" filter="url(#shadow)" class="k8s-comp"/>
<text x="595" y="98" text-anchor="middle" class="k8s-label">controller-manager</text>
<text x="595" y="116" text-anchor="middle" class="k8s-desc">控制循环执行者</text>
<text x="595" y="132" text-anchor="middle" class="k8s-desc">Deployment / ReplicaSet / Node</text>

<path d="M190 107 L200 107" class="k8s-arrow"/><path d="M335 107 L345 107" class="k8s-arrow"/><path d="M495 107 L505 107" class="k8s-arrow"/>

<rect x="205" y="160" width="310" height="52" rx="10" fill="var(--soft)" stroke="var(--border)" stroke-dasharray="4,3" opacity=".7" class="k8s-comp"/>
<text x="360" y="182" text-anchor="middle" class="k8s-desc">所有组件通过 API Server 通信（Watch / List）</text>
<text x="360" y="198" text-anchor="middle" class="k8s-desc">Informer 本地缓存 + 增量事件驱动</text>

<rect x="20" y="250" width="680" height="210" rx="18" fill="url(#dpGrad)" stroke="var(--sec)" stroke-opacity=".35" class="k8s-box"/>
<text x="40" y="280" class="k8s-subtitle">Data Plane / Worker Node（数据面）</text>

<rect x="45" y="300" width="195" height="90" rx="10" fill="var(--card-solid)" stroke="var(--sec)" stroke-opacity=".5" filter="url(#shadow)" class="k8s-comp"/>
<text x="142" y="328" text-anchor="middle" class="k8s-label">kubelet</text>
<text x="142" y="346" text-anchor="middle" class="k8s-desc">节点代理 · 管理 Pod 生命周期</text>
<text x="142" y="362" text-anchor="middle" class="k8s-desc">CRI 调用容器运行时</text>
<text x="142" y="378" text-anchor="middle" class="k8s-desc">上报节点状态到 API Server</text>

<rect x="260" y="300" width="175" height="90" rx="10" fill="var(--card-solid)" stroke="var(--sec)" stroke-opacity=".5" filter="url(#shadow)" class="k8s-comp"/>
<text x="347" y="328" text-anchor="middle" class="k8s-label">kube-proxy</text>
<text x="347" y="346" text-anchor="middle" class="k8s-desc">维护网络规则</text>
<text x="347" y="362" text-anchor="middle" class="k8s-desc">iptables / IPVS 转发</text>
<text x="347" y="378" text-anchor="middle" class="k8s-desc">Service 负载均衡实现</text>

<rect x="450" y="300" width="230" height="90" rx="10" fill="var(--card-solid)" stroke="var(--sec)" stroke-opacity=".5" filter="url(#shadow)" class="k8s-comp"/>
<text x="565" y="328" text-anchor="middle" class="k8s-label">容器运行时 (Container Runtime)</text>
<text x="565" y="346" text-anchor="middle" class="k8s-desc">containerd / CRI-O</text>
<text x="565" y="362" text-anchor="middle" class="k8s-desc">拉取镜像 · 创建/销毁容器</text>
<text x="565" y="378" text-anchor="middle" class="k8s-desc">CNI 配置网络 · CSI 挂载存储</text>

<path d="M117 230 L117 245 L360 245 L360 255" class="k8s-arrow" stroke-dasharray="4,3"/>
<text x="240" y="238" text-anchor="middle" font-size="9" fill="var(--muted)">watch Pod spec 变化</text>

<rect x="260" y="410" width="195" height="38" rx="10" fill="var(--warn-l)" stroke="var(--warn)" stroke-opacity=".4" opacity=".8" class="k8s-comp"/>
<text x="357" y="433" text-anchor="middle" class="k8s-desc">用户 kubectl ↔ API Server ↔ 各组件</text>
</svg>
</div>

<h3>控制面组件</h3>
<div class="comp-grid">
<div class="comp-item">
<div class="comp-name">kube-apiserver</div>
<div class="comp-role">集群 API 入口，所有操作的网关。所有组件通过它通信。</div>
<div class="comp-detail">无状态服务，支持水平扩展。性能瓶颈往往在 etcd 的读写上。</div>
</div>
<div class="comp-item">
<div class="comp-name">etcd</div>
<div class="comp-role">分布式键值存储，集群唯一的持久化状态源。</div>
<div class="comp-detail">Raft 共识协议，建议 3 或 5 节点部署。存储所有对象状态。</div>
</div>
<div class="comp-item">
<div class="comp-name">kube-scheduler</div>
<div class="comp-role">为未绑定的 Pod 选择最合适的运行节点。</div>
<div class="comp-detail">可插件化扩展（Scheduling Framework），支持自定义 Filter / Score 插件。</div>
</div>
<div class="comp-item">
<div class="comp-name">kube-controller-manager</div>
<div class="comp-role">运行各类控制循环：Deployment、ReplicaSet、Node、Service 等。</div>
<div class="comp-detail">声明式 API 执行者——将实际状态不断收敛到期望状态。</div>
</div>
</div>

<h3>数据面组件</h3>
<div class="comp-grid">
<div class="comp-item">
<div class="comp-name">kubelet</div>
<div class="comp-role">节点代理，管理 Pod 生命周期。</div>
<div class="comp-detail">通过 CRI（Container Runtime Interface）调用容器运行时创建和管理容器。</div>
</div>
<div class="comp-item">
<div class="comp-name">kube-proxy</div>
<div class="comp-role">维护网络规则，实现 Service 的负载均衡。</div>
<div class="comp-detail">底层使用 iptables 或 IPVS 模式转发流量到后端 Pod。</div>
</div>
<div class="comp-item">
<div class="comp-name">容器运行时</div>
<div class="comp-role">containerd / CRI-O，负责镜像管理和容器运行。</div>
<div class="comp-detail">同时调用 CNI（网络）和 CSI（存储）插件完成网络和挂载配置。</div>
</div>
</div>
