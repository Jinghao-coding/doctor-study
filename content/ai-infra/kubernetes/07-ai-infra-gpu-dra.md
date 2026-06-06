<div class="card card-m">
<h3>AI Infra：GPU / 批调度 / DRA 总览</h3>
<p>AI Infra 场景下，Kubernetes 的核心问题从“跑一个无状态服务”扩展为：<strong>如何接入 GPU/NPU 等异构硬件，如何让分布式训练一组 Pod 同时拿到资源，如何表达显存、拓扑、MIG、NVLink、NUMA 等复杂约束。</strong></p>
<table>
<tr><th>方向</th><th>解决的问题</th><th>代表机制</th></tr>
<tr><td>设备接入</td><td>让 kubelet 和 scheduler 看到 GPU/NPU</td><td>Device Plugin、Extended Resource、DRA</td></tr>
<tr><td>设备共享</td><td>提高 GPU 利用率</td><td>MIG、MPS、time-slicing、vGPU</td></tr>
<tr><td>拓扑感知</td><td>减少跨 NUMA、跨 PCIe、跨 NVLink 通信损耗</td><td>Topology Manager、scheduler plugin、DRA attributes</td></tr>
<tr><td>批调度</td><td>训练任务需要一组 Pod 同时运行</td><td>Gang Scheduling、Volcano、Kueue</td></tr>
<tr><td>队列治理</td><td>多团队 GPU 配额、公平性和抢占</td><td>Queue、ClusterQueue、PriorityClass、reclaim/borrowing</td></tr>
</table>
</div>

<div class="card card-s">
<h3>GPU Device Plugin：它把 GPU 接进 K8s 的哪一层</h3>
<p>Device Plugin 是 kubelet 的节点侧插件机制，用于把 GPU、FPGA、RDMA NIC 等非标准硬件暴露给 Kubernetes。以 NVIDIA GPU 为例，插件通常以 DaemonSet 运行在每个 GPU 节点上，向 kubelet 注册 <code>nvidia.com/gpu</code> 这类扩展资源；kubelet 再把资源数量写入 Node 的 <code>capacity</code> / <code>allocatable</code>，供 scheduler 做整数资源调度。</p>
<table>
<tr><th>组件</th><th>职责</th><th>面试关注点</th></tr>
<tr><td>Device Plugin Pod</td><td>发现本机设备，维护设备健康状态，通过 gRPC 向 kubelet 注册资源名</td><td>通常是 DaemonSet，只在有对应硬件的节点运行</td></tr>
<tr><td>kubelet Device Manager</td><td>接收插件注册，维护设备列表，在 Pod 启动前调用 Allocate</td><td>Device Plugin 直接对接 kubelet，不直接对接 scheduler</td></tr>
<tr><td>Node status</td><td>展示扩展资源总量和可分配量，例如 <code>nvidia.com/gpu: 8</code></td><td>scheduler 主要看到的是资源名和整数数量</td></tr>
<tr><td>kube-scheduler</td><td>根据 Pod requests/limits 和 Node allocatable 做过滤与打分</td><td>默认不理解 GPU 型号、显存、NVLink、NUMA 等设备内部属性</td></tr>
<tr><td>Container Runtime</td><td>根据 kubelet 传入的设备信息把 GPU device node、环境变量、mount 注入容器</td><td>常和 NVIDIA Container Toolkit、CDI 等运行时机制配合</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Device Plugin 调度与分配链路</h3>
<ol>
<li>Device Plugin 在节点上发现 GPU，并通过 kubelet 注册资源名，例如 <code>nvidia.com/gpu</code>。</li>
<li>kubelet 更新 Node <code>capacity</code> / <code>allocatable</code>。</li>
<li>用户 Pod 在 <code>resources.limits</code> 中申请 GPU。</li>
<li>scheduler 根据 Node allocatable 和 Pod requests/limits 选择节点。</li>
<li>Pod 绑定到节点后，kubelet 调用 Device Plugin <code>Allocate</code>。</li>
<li>Device Plugin 返回 device id、环境变量、mount、device node 或 CDI 信息。</li>
<li>kubelet 通过 CRI 让容器运行时把设备注入容器。</li>
</ol>
<p>核心边界：<strong>Device Plugin 让 K8s 能看见并交付设备，但默认调度层看到的是资源名和数量，不是完整设备拓扑。</strong></p>
</div>

<div class="card card-w">
<h3>MIG / MPS / time-slicing 的区别</h3>
<table>
<tr><th>机制</th><th>隔离粒度</th><th>优点</th><th>风险</th></tr>
<tr><td>MIG</td><td>硬件级 GPU 分区</td><td>隔离强，profile 清晰</td><td>切分形态固定，资源碎片</td></tr>
<tr><td>MPS</td><td>进程级共享</td><td>提升小任务并发利用率</td><td>隔离弱，干扰和故障影响更复杂</td></tr>
<tr><td>time-slicing</td><td>时间片共享</td><td>部署简单，适合轻量任务</td><td>不是硬隔离，显存仍可能竞争</td></tr>
<tr><td>vGPU</td><td>虚拟化切分</td><td>适合云化售卖和多租户</td><td>依赖厂商方案和授权</td></tr>
</table>
</div>

<div class="card card-m">
<h3>批调度：Gang、Kueue、Volcano</h3>
<p>分布式训练通常需要 worker、parameter server、launcher 等一组 Pod 同时运行。如果只按单 Pod 调度，可能出现部分 worker 占住 GPU，剩余 worker 长期 Pending，导致资源浪费。Gang Scheduling 要求一组 Pod 要么一起拿到资源，要么一起等待。</p>
<table>
<tr><th>机制</th><th>定位</th><th>面试回答</th></tr>
<tr><td>Gang Scheduling</td><td>调度语义</td><td>一组 Pod 满足最小可运行数量后再整体放行</td></tr>
<tr><td>Volcano</td><td>批调度系统</td><td>提供 Queue、PodGroup、Gang、DRF、公平调度等能力</td></tr>
<tr><td>Kueue</td><td>K8s 原生批任务准入</td><td>更偏资源准入和队列治理，与 Job、RayJob、训练 Operator 集成</td></tr>
<tr><td>Permit 插件</td><td>Scheduling Framework 扩展点</td><td>可让 Pod 在绑定前等待同组 Pod 凑齐</td></tr>
</table>
</div>

<div class="card card-s">
<h3>DRA 是什么</h3>
<p>DRA 是 Dynamic Resource Allocation，面向 GPU、DPU、FPGA、NIC 等设备的新一代动态资源分配 API。它的目标不是替代所有 Device Plugin 场景，而是解决传统扩展资源在复杂异构设备上的表达能力不足。</p>
<table>
<tr><th>DRA 对象</th><th>类比</th><th>作用</th></tr>
<tr><td>DeviceClass</td><td>StorageClass</td><td>管理员定义一类可申请设备及选择规则</td></tr>
<tr><td>ResourceClaim</td><td>PVC</td><td>用户声明自己需要什么设备</td></tr>
<tr><td>ResourceClaimTemplate</td><td>volumeClaimTemplates</td><td>为每个 Pod 自动生成相似但独立的 claim</td></tr>
<tr><td>ResourceSlice</td><td>设备库存分片</td><td>DRA driver 发布设备列表、属性、容量、拓扑和可访问节点</td></tr>
<tr><td>Pod resourceClaims</td><td>Pod 引用 PVC</td><td>Pod 声明要使用哪些 ResourceClaim</td></tr>
</table>
</div>

<div class="card card-m">
<h3>ResourceSlice 深入理解</h3>
<p><strong>ResourceSlice 是 DRA 的设备库存分片。</strong>它通常由 DRA driver 自动创建和维护，用户和平台管理员一般不手写。它把设备的结构化信息发布给 API Server，让 scheduler 能基于设备属性、容量和拓扑做匹配。</p>
<table>
<tr><th>字段/概念</th><th>含义</th><th>为什么重要</th></tr>
<tr><td>driver</td><td>哪个 DRA driver 管理这批设备</td><td>避免不同厂商/驱动资源混淆</td></tr>
<tr><td>pool</td><td>资源池名称、generation、slice 数量</td><td>帮助 scheduler 判断同一资源池的库存版本</td></tr>
<tr><td>nodeName / nodeSelector</td><td>这些设备在哪些节点可用</td><td>设备必须和 Pod 调度节点匹配</td></tr>
<tr><td>devices</td><td>设备列表</td><td>可以表达每个 GPU/NPU/NIC 的名称、属性、容量</td></tr>
<tr><td>attributes</td><td>结构化属性</td><td>型号、厂商、NUMA、PCIe、NVLink、MIG profile 等</td></tr>
<tr><td>capacity</td><td>设备容量</td><td>显存、队列数、带宽等可被选择或分配</td></tr>
</table>
<p>大集群中会有很多 ResourceSlice，这是预期设计。它避免把大量设备细节全部塞进 Node status，也避免用 <code>nvidia.com/a100</code>、<code>nvidia.com/a100-80g-sxm-numa0</code> 这类资源名无限膨胀。</p>
</div>

<div class="card card-w">
<h3>CEL 表达式在 DRA 中的作用</h3>
<p>CEL 是 Common Expression Language，一种安全、可嵌入的表达式语言。DRA 可以用 CEL 对 ResourceSlice 中的设备属性做过滤，例如选择 A100、显存至少 80Gi、同 NUMA 或带特定 NVLink fabric 的设备。</p>
<pre><code class="language-yaml">selectors:
- cel:
    expression: "device.attributes['model'].string == 'A100' && device.capacity['memory'].quantity >= quantity('80Gi')"
</code></pre>
<p>面试回答要点：<strong>CEL 的价值是把“申请某个资源名”升级为“基于结构化设备属性做查询”。</strong></p>
</div>

<div class="card card-s">
<h3>DRA driver 是什么</h3>
<p>DRA driver 是 Kubernetes 侧的设备资源驱动，不是 Linux kernel driver，也不是 CUDA/NPU runtime 本身。它负责把真实硬件接入 DRA API：一边向 API Server 发布设备库存，一边在 Pod 落到节点后配合 kubelet 准备并交付设备。</p>
<table>
<tr><th>职责</th><th>具体动作</th><th>对应对象/接口</th></tr>
<tr><td>设备发现</td><td>发现 GPU、NPU、DPU、FPGA、NIC 等设备，读取型号、显存、拓扑、健康状态</td><td>厂商 runtime、节点 agent</td></tr>
<tr><td>库存发布</td><td>把设备列表、属性、容量、资源池信息写入 API Server</td><td><code>ResourceSlice</code></td></tr>
<tr><td>分配协作</td><td>让 scheduler 能基于 ResourceClaim 选择具体设备，并把分配结果写入 claim 状态</td><td>scheduler + <code>ResourceClaim.status</code></td></tr>
<tr><td>设备准备</td><td>Pod 绑定后在目标节点上准备设备，例如 CDI、device node、环境变量、mount、MIG/VF 配置</td><td>kubelet 调用 driver 的 prepare/unprepare</td></tr>
<tr><td>回收与健康</td><td>Pod 结束后清理设备状态，设备故障时更新可用性</td><td>driver controller / node plugin</td></tr>
</table>
<p>一句话：<strong>Kubernetes 提供 DRA 框架和 API，DRA driver 负责把某类真实硬件翻译成 Kubernetes 能理解和交付的资源。</strong></p>
</div>

<div class="card card-d">
<h3>DRA 与 Device Plugin 是否冲突</h3>
<table>
<tr><th>模式</th><th>是否可行</th><th>说明</th></tr>
<tr><td>纯 Device Plugin</td><td>可行</td><td>成熟稳定，适合同质整卡资源</td></tr>
<tr><td>纯 DRA</td><td>可行</td><td>适合新集群或强异构设备，但依赖 driver 生态</td></tr>
<tr><td>按 node pool 共存</td><td>推荐</td><td>一部分节点继续 DP，一部分节点灰度 DRA</td></tr>
<tr><td>按设备类型共存</td><td>可行</td><td>GPU 用 DP，DPU/特殊 NIC 用 DRA，或反过来</td></tr>
<tr><td>同一物理设备同时暴露</td><td>不推荐</td><td>可能导致双重分配和资源状态不一致</td></tr>
</table>
</div>

<div class="card card-w">
<h3>DRA 排障路径</h3>
<pre><code class="language-bash"># 1. 看 DRA API 是否存在
kubectl api-resources | grep resource.k8s.io

# 2. 看是否有设备库存
kubectl get resourceslices -A

# 3. 看平台暴露了哪些设备类别
kubectl get deviceclasses

# 4. 看具体 claim 的分配状态
kubectl describe resourceclaim &lt;claim-name&gt;

# 5. 看 driver 组件是否运行
kubectl get pods -A | grep -i dra
</code></pre>
<p>如果 ResourceClaim 长期未分配，重点检查 DeviceClass 是否存在、ResourceSlice 是否发布、CEL selector 是否过严、节点可访问性是否满足、driver controller 和 node plugin 是否正常。</p>
</div>

<div class="card card-m">
<h3>面试高频追问：默认展示版</h3>
<table>
<tr><th>问题</th><th>回答要点</th><th>可继续展开</th></tr>
<tr><td>ResourceSlice 是谁创建的？</td><td>通常由 DRA driver 自动创建和维护，用户一般不手写</td><td>driver 根据节点、资源池、设备类型和更新粒度做分片</td></tr>
<tr><td>大集群会不会有很多 ResourceSlice？</td><td>会，而且这是预期设计；目的是避免 Node 对象膨胀和资源名爆炸</td><td>代价是 API Server / scheduler watch 对象更多，需要控制分片和更新频率</td></tr>
<tr><td>DRA 和 Device Plugin 冲突吗？</td><td>集群层面可以共存，同一物理设备不能双重暴露</td><td>推荐按 node pool、设备类型或灰度资源池隔离</td></tr>
<tr><td><code>nvidia.com/a100</code> 已能表达卡型，DRA 价值在哪里？</td><td>资源名编码只能解决简单分类，DRA 可表达结构化属性、容量、拓扑和共享关系</td><td>显存、NVLink、NUMA、MIG profile、健康状态都适合放进 ResourceSlice</td></tr>
<tr><td>DRA driver 和 Linux driver 是一回事吗？</td><td>不是。Linux driver / CUDA / NPU runtime 管底层硬件，DRA driver 管 Kubernetes 资源发现、库存发布和设备交付</td><td>面试中要说清楚 controller、node plugin、prepare/unprepare 的边界</td></tr>
<tr><td>国产 GPU/NPU 是否有 DRA driver？</td><td>公开成熟度要谨慎判断；多数生态更常见的是 Device Plugin、Operator、vGPU 或 HAMi 等方案</td><td>判断真 DRA 看是否使用 <code>resource.k8s.io</code>、ResourceSlice、DeviceClass、ResourceClaim</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何从 Device Plugin 平滑迁移到 DRA？</div>
<div class="qa-a"><p>不要在同一批物理设备上同时开放 DP 和 DRA。推荐先建设独立 node pool，部署 DRA driver，发布 DeviceClass 和 ResourceSlice；再让少量训练任务通过 ResourceClaim 灰度接入，验证调度、prepare、监控和回收；最后按设备类型或业务队列逐步迁移。</p></div>
</div>
