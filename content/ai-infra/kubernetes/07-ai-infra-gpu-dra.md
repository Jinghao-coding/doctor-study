## 一句话结论

Kubernetes 不直接执行 CUDA，也不负责切分 GPU。它通过 Device Plugin 或 DRA 获取设备资源模型，由 scheduler 完成“设备与节点”的联合放置，再由 kubelet、设备驱动和容器运行时把已分配设备注入容器。MIG、MPS、Time-Slicing、HAMi 的硬件或共享机制统一放在 GPU 专题。

## Device Plugin 主链路

```flow
Device Plugin 启动 gRPC 服务 | 监听 /var/lib/kubelet/device-plugins/ 下的 Unix Socket
向 kubelet 注册 | 上报 API 版本、Socket、ResourceName
ListAndWatch | 持续上报设备 ID 和 Healthy/Unhealthy
kubelet 更新 Node Status | Capacity/Allocatable 出现 nvidia.com/gpu
scheduler 选择节点 | Extended Resource 按整数、不可超卖
kubelet 调用 Allocate | 获得 device、mount、env、annotation 或 CDI device
容器运行时创建容器 | 注入设备节点和匹配的驱动用户态库
```

核心接口：

| 接口 | 职责 | 面试重点 |
|---|---|---|
| `Register` | 插件向 kubelet 注册资源名和 Socket | 插件要先启动服务再注册 |
| `ListAndWatch` | 上报设备列表及健康状态 | 决定 Node 可见设备数量 |
| `Allocate` | 为已分配设备返回容器配置 | 不负责选择节点，发生在容器创建前 |
| `GetPreferredAllocation` | 可选的设备选择偏好 | 可表达部分拓扑偏好，但不是完整集群调度 |
| `PreStartContainer` | 可选的启动前设备操作 | 适合需要重置或初始化的设备 |

Extended Resource 的重要限制：通常按整数请求、不能原生超卖，也不能直接表达“需要 20GB 显存、支持某精度、与某 NIC 同 NUMA”等富属性。

## Device Plugin、Runtime 与 Scheduler 的边界

| 组件 | 负责 | 不负责 |
|---|---|---|
| NVIDIA Driver | 宿主机识别和驱动 GPU | Kubernetes 资源注册 |
| Container Toolkit / CDI | 将设备与驱动库注入容器 | 选择节点和排队 |
| Device Plugin | 发现、健康上报、Allocate | GPU Kernel 调度和业务性能隔离 |
| kubelet Device Manager | 节点侧设备账本与分配 | 集群全局放置 |
| kube-scheduler | 根据请求与 Node 状态选择节点 | 在容器内挂载设备 |
| GPU Operator | 部署和维护节点侧 GPU 软件栈 | 替代业务调度器或 CUDA Runtime |

## DRA 解决什么

DRA 把设备从“一个整数扩展资源”提升为可声明、可匹配、可配置的设备对象模型。当前主链路是：

```flow
DRA Driver 发布 ResourceSlice | 描述设备、属性、容量和可访问节点
管理员定义 DeviceClass | 给出设备类别和选择规则
工作负载创建 ResourceClaim/Template | 声明需要什么设备
scheduler 过滤并分配 | 同时确定 Claim 与可访问节点
kubelet + DRA Driver Prepare | 在节点上配置并向容器暴露设备
Pod 结束后 Unprepare | 回收设备状态
```

| 维度 | Device Plugin | DRA |
|---|---|---|
| 请求方式 | `limits.vendor/resource: N` | `ResourceClaim` / `ResourceClaimTemplate` |
| 描述能力 | 资源名 + 整数数量 | 属性、容量、类别、配置和约束 |
| 调度状态 | 主要在 Node Capacity/Allocatable | ResourceSlice + Claim allocation |
| 典型场景 | 简单整卡、成熟兼容路径 | GPU/NIC/FPGA 等富属性、动态配置设备 |

DRA 核心能力已在 Kubernetes v1.34 进入 GA，但具体 GPU DRA Driver、运维流程与兼容矩阵仍应按集群版本和供应商实现验证，不要把“核心 API 稳定”误解为所有驱动能力完全一致。

## GPU 共享机制如何接入 Kubernetes

Kubernetes 页面只记资源呈现方式：

| 机制 | Kubernetes 可能看到的资源 | 机制细节归属 |
|---|---|---|
| 整卡 | `nvidia.com/gpu` | GPU / 新节点接入 |
| MIG | `nvidia.com/mig-*` 或按策略暴露 | GPU / MIG 实战 |
| Time-Slicing | 扩大的共享资源副本数 | GPU / Time-Slicing 实战 |
| MPS | 由 NVIDIA Device Plugin 共享策略暴露 | GPU / MPS 实战 |
| HAMi | 方案定义的显存/算力资源与调度扩展 | GPU / HAMi 实战 |

Kubernetes 中的资源数量只是调度抽象，不能单独证明硬件隔离强度、显存边界或性能份额。

## 常见故障定位

| 现象 | 优先检查 |
|---|---|
| Node 没有 `nvidia.com/gpu` | Device Plugin Pod、注册 Socket、ListAndWatch、Driver 可见性 |
| Pod Pending / Insufficient GPU | Node Allocatable、已分配量、taint/affinity、配额、队列准入 |
| Pod 已调度但启动失败 | Allocate 日志、CDI/runtime、device node、驱动库兼容 |
| GPU 变 Unhealthy | Xid/ECC/掉卡、插件健康上报、节点隔离策略 |
| kubelet 重启后资源消失 | 插件是否监测 Socket 删除并重新注册 |

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: scheduler 怎么知道某个 Pod 要用哪一张物理 GPU？</div>
<div class="qa-a"><p>传统 Device Plugin 路径中，scheduler 主要根据 Node 的扩展资源数量选择节点，不直接决定具体设备 ID；节点确定后由 kubelet Device Manager 和 Device Plugin 的 Allocate 流程完成设备选择和注入。DRA 则把设备分配状态显式放进 ResourceClaim，使 scheduler 能在更丰富的设备属性和节点可达性上联合决策。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么装了 Device Plugin，容器里仍可能看不到 GPU？</div>
<div class="qa-a"><p>Device Plugin 解决资源注册和 Allocate，但容器还需要 Container Toolkit/CDI 与运行时正确注入设备节点和驱动库。还应检查 Pod 是否真正请求了资源、Allocate 是否成功，以及宿主机 Driver 与容器 CUDA 兼容性。</p></div>
</div>

## 关联模块与官方资料

- `GPU / 新 GPU 节点接入`：Driver、Runtime、Toolkit、Device Plugin、GPU Operator 的部署和验收。
- `GPU / MIG、MPS、Time-Slicing、HAMi`：共享机制、配置与隔离边界。
- `任务调度理论`：Gang、拓扑、公平性和抢占算法。
- [Kubernetes Device Plugins](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/)
- [Kubernetes Dynamic Resource Allocation](https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/)
- [Kubernetes v1.34: DRA Core Features Graduate to GA](https://kubernetes.io/blog/2025/09/01/kubernetes-v1-34-dra-updates/)
- [NVIDIA Kubernetes Device Plugin](https://github.com/NVIDIA/k8s-device-plugin)
