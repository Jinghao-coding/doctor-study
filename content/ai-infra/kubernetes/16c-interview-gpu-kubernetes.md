## 一句话结论

Kubernetes 不直接执行 CUDA，也不天然理解 GPU 拓扑和共享隔离。GPU 面试题要沿 `Driver → Container Toolkit/CDI → Device Plugin/DRA → kubelet → scheduler → Runtime → DCGM` 分层回答。

## GPU 资源注册与分配

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一个新 GPU 节点来了，怎样让 Kubernetes 使用它？</div>
<div class="qa-a">
<div class="qa-summary">先隔离节点并验证普通 Worker 基线，再从 PCIe、Driver、Container Toolkit/CDI、Device Plugin 到 CUDA Canary 逐层验收，最后接入 DCGM 监控后才开放业务。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>检查 <code>lspci</code>、<code>nvidia-smi</code> 和拓扑；配置 containerd 与 NVIDIA Toolkit；由 GPU Operator 或手工 DaemonSet 部署 Device Plugin；确认 Node Allocatable 出现 GPU；运行真实申请 GPU 的 Pod，验证 Allocate、容器内 CUDA kernel、Xid/ECC 和指标采集。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p><code>nvidia-smi</code> 正常只证明宿主机 Driver 正常，不代表 Kubernetes 和容器链路已经打通。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Driver、Container Toolkit、Device Plugin 和 GPU Operator 分别负责什么？</div>
<div class="qa-a">
<div class="qa-summary">Driver 驱动硬件；Toolkit/CDI 把设备和驱动库注入容器；Device Plugin 注册、上报健康并参与 Allocate；GPU Operator 负责部署和收敛整套节点软件栈。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Driver 属于宿主机内核和用户态兼容层；Toolkit 修改 OCI/CDI 创建路径；Device Plugin 通过 kubelet gRPC 接口暴露扩展资源；Operator 还可管理 GFD/NFD、MIG Manager、DCGM 和 Validator，但它不替代 Scheduler 或 CUDA Runtime。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>RuntimeClass 是选择 CRI runtime handler 的 Kubernetes 对象，不是另一个容器引擎。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Device Plugin 是怎样向 kubelet 注册 GPU 的？</div>
<div class="qa-a">
<div class="qa-summary">插件在 kubelet 设备目录创建 gRPC Socket，调用 Registration API 注册资源名，再通过 ListAndWatch 持续上报设备 ID 和健康状态。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>kubelet Device Manager 根据 ListAndWatch 更新本地设备账本和 Node Capacity/Allocatable。Pod 被调度到节点后，kubelet 为容器选择设备 ID 并调用 Allocate，插件返回 device、mount、env、annotation 或 CDI device。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>kubelet 重启会删除旧 Socket，插件需要监测并重新注册。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ListAndWatch 和 Allocate 的职责有什么区别？</div>
<div class="qa-a">
<div class="qa-summary">ListAndWatch 回答“节点现在有哪些健康设备”；Allocate 回答“给这个已选定容器暴露哪些设备和配置”。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>ListAndWatch 是持续流，设备变成 Unhealthy 后 kubelet 会减少可分配资源；Allocate 发生在 Pod 已经落到节点、容器创建之前。传统路径中 Scheduler 通常只根据资源数量选节点，不直接调用 Allocate，也不直接决定 GPU UUID。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Allocate 不负责集群级排队和节点选择。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么装了 Device Plugin，容器里仍可能看不到 GPU？</div>
<div class="qa-a">
<div class="qa-summary">Device Plugin 只解决 Kubernetes 资源注册与 Allocate；容器仍依赖 Driver、Toolkit/CDI、CRI 配置和镜像兼容性。</div>
<div class="qa-section"><div class="qa-section-title">排查</div><p>先确认 Pod 确实请求 GPU且 Node Allocatable 正常，再看插件 Allocate 日志；检查 CDI spec、Runtime handler、<code>/dev/nvidia*</code>、驱动库挂载和 Driver-CUDA 兼容。宿主机和容器各跑一次 <code>nvidia-smi</code>，定位断在哪一层。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>不要看到 Node 有 <code>nvidia.com/gpu</code> 就跳过容器运行时检查。</p></div>
</div></div>

## 资源模型与共享

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Scheduler 知道 Pod 最终使用哪张物理 GPU 吗？</div>
<div class="qa-a">
<div class="qa-summary">传统 Device Plugin 路径中，Scheduler 主要按节点扩展资源数量选 Node，具体设备 ID 通常由 kubelet Device Manager 在节点侧选择。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>这意味着默认 Scheduler 不理解两份逻辑资源是否属于同一物理卡、NVLink 关系和剩余显存。可通过 Node 标签、Topology Manager、自定义 Plugin、供应商调度器或 DRA 增强设备级决策。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>DRA 会把设备分配显式写入 ResourceClaim，使 Scheduler 能结合设备属性与节点可达性决策。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Extended Resource 为什么不能直接表达显存和拓扑？</div>
<div class="qa-a">
<div class="qa-summary">它本质是 Node 上的命名整数计数，适合“几份资源”，不适合“什么属性、多少容量、设备之间什么关系”。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p><code>nvidia.com/gpu: 2</code> 不能说明型号、显存、NVLink island、NUMA/NIC 距离和动态配置，也不能原生超卖。平台通常通过不同资源名、Label、Webhook 和 Scheduler Plugin 补充，但会产生资源名爆炸和多处状态。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Node Allocatable 是容量上限，不会因为 Pod 使用后在 Status 中动态减一；已分配量要看 Pod requests 或 describe node。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MIG、MPS、Time-Slicing、HAMi 有什么本质区别？</div>
<div class="qa-a">
<div class="qa-summary">MIG 是硬件实例切分；MPS 是驱动级多进程并发；Time-Slicing 是共享访问名额；HAMi 是 Kubernetes 调度与容器运行时层的细粒度软件虚拟化。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>强 SLA 优先整卡/MIG；可信小 Kernel 并发可考虑 MPS；开发测试可用 Time-Slicing；需要任意显存/算力配比和设备感知调度时考虑 HAMi。选择时同时比较显存、算力、故障域、性能隔离和重配成本。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p><code>replicas: 4</code> 只表示四个共享访问名额，不保证每个 Pod 固定获得 25% 算力或显存。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: DRA 相比 Device Plugin 解决了什么问题？</div>
<div class="qa-a">
<div class="qa-summary">DRA 把设备从节点整数扩展资源提升为可声明、可匹配、可配置、可追踪的设备对象模型。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>DRA Driver 发布 ResourceSlice，管理员定义 DeviceClass，工作负载通过 ResourceClaim 声明属性和配置，Scheduler 联合决定 Claim 与 Node，kubelet 再调用 Prepare/Unprepare。它更适合 GPU/NIC/FPGA 的富属性和动态配置。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>核心 API GA 不等于所有供应商 Driver、监控和运维链路已经完全一致，生产仍需验证兼容矩阵。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 出现 Xid/ECC 错误后，平台应该怎样处理？</div>
<div class="qa-a">
<div class="qa-summary">先区分可恢复错误和设备失效，快速停止新增调度并隔离设备或节点，再结合 DCGM、内核日志和业务状态决定重置、重启或下线维修。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Device Plugin 可通过 ListAndWatch 把设备标记 Unhealthy；平台还应给节点加 taint/cordon，触发训练 Checkpoint 或任务重试，保存 Xid、ECC、温度和 PCIe/NVLink 证据。恢复后必须跑 CUDA/NCCL Canary，不能仅以 <code>nvidia-smi</code> 恢复为准。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>直接删除 Pod 可能把任务再次调度回故障节点；先隔离资源，再恢复工作负载。</p></div>
</div></div>

## 关联模块

- `GPU / 新 GPU 节点接入`：完整部署命令、验收清单和故障定位表。
- `GPU / MIG、MPS、Time-Slicing、HAMi`：各共享方案实战。
- `Kubernetes / Device Plugin 与 DRA`：接口、资源模型和调度边界。
- `GPU 平台系统设计`：多租户、拓扑、监控和故障治理。
