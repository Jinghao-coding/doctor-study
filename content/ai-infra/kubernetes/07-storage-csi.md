<div class="card card-m">
<h3>Kubernetes 存储体系总览</h3>
<p>Kubernetes 把“应用如何声明存储需求”和“底层如何创建/挂载具体存储”拆开。面试时要围绕 PV、PVC、StorageClass、CSI 之间的关系来讲。</p>
<table>
<tr><th>对象</th><th>角色</th><th>谁创建</th><th>面试重点</th></tr>
<tr><td>Volume</td><td>Pod spec 中声明的挂载来源</td><td>用户或控制器</td><td>生命周期通常跟 Pod 绑定，类型很多</td></tr>
<tr><td>PersistentVolumeClaim (PVC)</td><td>用户对存储的申请</td><td>用户或 StatefulSet volumeClaimTemplates</td><td>声明容量、访问模式、StorageClass</td></tr>
<tr><td>PersistentVolume (PV)</td><td>集群中的真实存储资源抽象</td><td>管理员静态创建或 provisioner 动态创建</td><td>PV 与 PVC 绑定后供 Pod 挂载</td></tr>
<tr><td>StorageClass</td><td>动态供给模板</td><td>管理员</td><td>定义 provisioner、参数、reclaimPolicy、volumeBindingMode</td></tr>
<tr><td>CSI Driver</td><td>存储厂商插件</td><td>平台管理员部署</td><td>负责创建、挂载、扩容、快照等存储操作</td></tr>
</table>
</div>

<div class="card card-s">
<h3>PV/PVC 绑定流程</h3>
<ol>
<li>用户创建 PVC，声明所需容量、访问模式和 StorageClass。</li>
<li>如果存在匹配 PV，控制器将 PVC 与 PV 绑定。</li>
<li>如果没有现成 PV，且 StorageClass 支持动态供给，external-provisioner 调用 CSI 创建真实存储并生成 PV。</li>
<li>Pod 引用 PVC 后，调度器需要考虑 volume 约束，例如 zone、node affinity。</li>
<li>Pod 调度到节点后，kubelet 通过 CSI node plugin 挂载 volume 到容器。</li>
</ol>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: PVC Pending 常见原因有哪些？</div>
<div class="qa-a">
<div class="qa-grid"><div class="qa-mini"><strong>没有匹配 PV</strong>静态 PV 容量、accessMode、storageClassName 不匹配。</div><div class="qa-mini"><strong>动态供给失败</strong>CSI provisioner 异常、权限不足、云盘配额不足。</div><div class="qa-mini"><strong>WaitForFirstConsumer</strong>StorageClass 等待 Pod 调度后再创建 PV，PVC 可能暂时 Pending。</div><div class="qa-mini"><strong>拓扑限制</strong>存储所在 zone 与 Pod 可调度节点不一致。</div></div>
</div>
</div>
</div>

<div class="card card-w">
<h3>访问模式与回收策略</h3>
<table>
<tr><th>字段</th><th>常见取值</th><th>解释</th><th>注意事项</th></tr>
<tr><td>accessModes</td><td>ReadWriteOnce</td><td>单个节点读写挂载</td><td>云盘最常见；不是单个 Pod，而是单个节点</td></tr>
<tr><td>accessModes</td><td>ReadOnlyMany</td><td>多个节点只读挂载</td><td>适合共享只读数据</td></tr>
<tr><td>accessModes</td><td>ReadWriteMany</td><td>多个节点读写挂载</td><td>需要 NFS、CephFS、NAS 等支持</td></tr>
<tr><td>reclaimPolicy</td><td>Delete</td><td>PVC 删除后底层存储也删除</td><td>动态供给常用，危险点是误删数据</td></tr>
<tr><td>reclaimPolicy</td><td>Retain</td><td>PVC 删除后保留 PV 和底层数据</td><td>适合重要数据，但需要人工回收</td></tr>
</table>
</div>

<div class="card card-m">
<h3>StorageClass 关键字段</h3>
<table>
<tr><th>字段</th><th>作用</th><th>面试解释</th></tr>
<tr><td>provisioner</td><td>指定由哪个 CSI 或内置 provisioner 创建存储</td><td>例如云厂商块存储、Ceph、NFS 等</td></tr>
<tr><td>parameters</td><td>传给 provisioner 的参数</td><td>磁盘类型、IOPS、文件系统类型、加密等</td></tr>
<tr><td>reclaimPolicy</td><td>PV 回收策略</td><td>Delete 自动删除底层资源，Retain 保留数据</td></tr>
<tr><td>allowVolumeExpansion</td><td>是否允许 PVC 扩容</td><td>扩容还需要底层 CSI 支持</td></tr>
<tr><td>volumeBindingMode</td><td>Immediate 或 WaitForFirstConsumer</td><td>后者能结合 Pod 调度选择合适 zone，避免存储和计算不在同一可用区</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: WaitForFirstConsumer 为什么重要？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">Immediate 的问题</div><p>Immediate 会在 PVC 创建时立刻创建 PV。如果云盘先被创建在 zone-a，而 Pod 后续只能调到 zone-b，就会出现存储和计算拓扑冲突。</p></div>
<div class="qa-section"><div class="qa-section-title">WaitForFirstConsumer 的价值</div><p>等到 Pod 参与调度时，调度器结合节点拓扑和存储拓扑决定 PV 创建在哪个 zone，减少调度失败。</p></div>
<div class="qa-summary">一句话：延迟绑定让存储创建跟 Pod 调度一起考虑，避免跨可用区挂载失败。</div>
</div>
</div>
</div>

<div class="card card-s">
<h3>CSI 工作机制</h3>
<p>CSI 把 Kubernetes 与存储厂商解耦。它通常由 Controller 插件和 Node 插件组成，配合 external-provisioner、external-attacher、external-resizer、external-snapshotter 等 sidecar 工作。</p>
<table>
<tr><th>组件</th><th>位置</th><th>职责</th><th>典型操作</th></tr>
<tr><td>CSI Controller Plugin</td><td>控制面部署，通常是 Deployment</td><td>管理存储卷生命周期</td><td>CreateVolume、DeleteVolume、ControllerPublishVolume</td></tr>
<tr><td>CSI Node Plugin</td><td>每个节点部署，通常是 DaemonSet</td><td>负责节点本地挂载和卸载</td><td>NodeStageVolume、NodePublishVolume、NodeUnpublishVolume</td></tr>
<tr><td>external-provisioner</td><td>sidecar</td><td>监听 PVC 并创建 PV</td><td>动态供给</td></tr>
<tr><td>external-attacher</td><td>sidecar</td><td>处理云盘 attach/detach</td><td>把云盘挂到节点</td></tr>
<tr><td>external-resizer</td><td>sidecar</td><td>处理 PVC 扩容</td><td>扩容底层卷和文件系统</td></tr>
</table>
</div>

<div class="card card-w">
<h3>常见 Volume 类型</h3>
<table>
<tr><th>类型</th><th>生命周期</th><th>用途</th><th>风险</th></tr>
<tr><td>emptyDir</td><td>随 Pod 创建和删除</td><td>临时缓存、容器间共享临时文件</td><td>Pod 删除后数据消失</td></tr>
<tr><td>hostPath</td><td>绑定节点本地路径</td><td>系统组件访问宿主机文件，如日志、device plugin</td><td>强节点耦合，有安全风险，不适合普通业务随意使用</td></tr>
<tr><td>configMap volume</td><td>来自 ConfigMap</td><td>挂载配置文件</td><td>配置更新到容器内有延迟；subPath 挂载不会自动更新</td></tr>
<tr><td>secret volume</td><td>来自 Secret</td><td>挂载证书、token、密码</td><td>要注意权限、最小化暴露和审计</td></tr>
<tr><td>PVC volume</td><td>跟 PVC/PV 生命周期相关</td><td>持久化数据</td><td>需要考虑绑定、拓扑、扩容、回收策略</td></tr>
</table>
</div>

<div class="card card-d">
<h3>StatefulSet 存储模式</h3>
<p>StatefulSet 的 <code>volumeClaimTemplates</code> 会为每个 Pod 创建独立 PVC。例如 <code>mysql-0</code> 对应自己的 PVC，Pod 重建后仍然挂回自己的存储。</p>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: StatefulSet 删除后 PVC 会不会自动删除？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">传统行为</div><p>StatefulSet 删除时，PVC 通常不会自动删除，以避免误删有状态数据。</p></div>
<div class="qa-section"><div class="qa-section-title">新能力</div><p>较新版本 Kubernetes 支持 persistentVolumeClaimRetentionPolicy，可以控制 StatefulSet 删除或缩容时 PVC 的保留策略。</p></div>
<div class="qa-summary">面试记忆：Pod 可重建，PVC 要谨慎保留；有状态数据默认不应因为控制器删除而丢失。</div>
</div>
</div>
</div>

<div class="card card-d">
<h3>官方参考</h3>
<div class="resource-grid">
<a class="resource-card" href="https://kubernetes.io/docs/concepts/storage/persistent-volumes/"><div class="resource-type">official</div><div class="resource-title">Persistent Volumes</div><div class="resource-desc">PV、PVC、StorageClass、访问模式、回收策略。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/storage/storage-classes/"><div class="resource-type">official</div><div class="resource-title">Storage Classes</div><div class="resource-desc">动态供给、volumeBindingMode、reclaimPolicy。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/storage/volumes/"><div class="resource-type">official</div><div class="resource-title">Volumes</div><div class="resource-desc">emptyDir、hostPath、configMap、secret、PVC 等 volume 类型。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/storage/volumes/#csi"><div class="resource-type">official</div><div class="resource-title">CSI Volumes</div><div class="resource-desc">CSI volume 机制和 Kubernetes 存储插件模型。</div></a>
</div>
</div>
