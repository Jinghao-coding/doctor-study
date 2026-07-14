## 一句话结论

GPU 虚拟化不是单一技术，而是从“整卡直通”到“硬件切片、进程并发、时间片复用、软件配额”的一组方案。面试回答必须先说清楚：**切分发生在哪一层、隔离了什么、调度器看见什么、运行时如何执行、出错时会不会互相影响。**

## 一条完整主线

```flow
业务需求 | 独占、强 SLA、开发测试、细粒度显存或算力
隔离目标 | 故障、显存、SM、带宽、时延分别要隔离到什么程度
选择机制 | 整卡 / MIG / MPS / Time-Slicing / HAMi
暴露资源 | Device Plugin、GPU Operator 或 HAMi 向 Kubelet 注册资源
调度放置 | kube-scheduler 或 HAMi Scheduler 选择节点和物理 GPU
运行时执行 | MIG 硬件实例、MPS server、CUDA 时间片或 HAMi-Core 执行限制
监控兜底 | DCGM、进程显存、P99、Xid、OOM 与共享密度
```

<div class="card card-m">
<h3>先分清五个层次</h3>
<table>
<thead><tr><th>层次</th><th>机制</th><th>真正被切分的对象</th><th>隔离强度</th></tr></thead>
<tbody>
<tr><td>设备直通</td><td>整卡 / PCIe Passthrough</td><td>整张物理 GPU</td><td>最强，但粒度最粗</td></tr>
<tr><td>硬件分区</td><td>MIG</td><td>GPU Instance / Compute Instance，对应 SM、显存切片和缓存等硬件资源</td><td>强</td></tr>
<tr><td>驱动级并发</td><td>MPS</td><td>多个 CUDA client 通过 MPS server 共享执行资源</td><td>中等，仍共享故障域和部分硬件</td></tr>
<tr><td>时间复用</td><td>Time-Slicing</td><td>多个进程交错获得 GPU 执行时间</td><td>弱，不提供显存和性能硬隔离</td></tr>
<tr><td>K8S 软件虚拟化</td><td>HAMi</td><td>用调度账本分配显存/算力，再在容器内执行软限制</td><td>取决于设备后端，NVIDIA 常见路径是软件隔离</td></tr>
</tbody>
</table>
</div>

## 核心机制对比

<table>
<thead><tr><th>机制</th><th>K8S 如何表达</th><th>能保证什么</th><th>不能保证什么</th><th>典型场景</th></tr></thead>
<tbody>
<tr><td><strong>MIG</strong></td><td>每个 MIG profile 作为独立扩展资源，例如 <code>nvidia.com/mig-1g.10gb</code></td><td>固定规格的硬件资源与故障隔离，性能更稳定</td><td>不能动态借用相邻实例的空闲资源；profile 组合会产生碎片</td><td>强 SLA 推理、多租户生产、稳定小训练</td></tr>
<tr><td><strong>MPS</strong></td><td>官方 Device Plugin 按 <code>replicas</code> 暴露共享访问，MPS daemon 管理 client</td><td>多进程 kernel 并发；可限制 client 的执行资源和显存</td><td>不等于 MIG 级隔离；共享故障域，干扰仍需监控</td><td>可信 workload、小 kernel、多路推理</td></tr>
<tr><td><strong>Time-Slicing</strong></td><td>Device Plugin 为每张卡创建多个逻辑引用</td><td>让多个 Pod 获得同一张 GPU 的共享访问权</td><td><code>replicas=N</code> 不代表固定 <code>1/N</code> 算力，也不隔离显存</td><td>Notebook、开发测试、低优离线任务</td></tr>
<tr><td><strong>HAMi</strong></td><td><code>nvidia.com/gpu</code> + <code>nvidia.com/gpumem</code> + <code>nvidia.com/gpucores</code></td><td>细粒度显存/算力请求、设备感知调度、异构加速器统一管理</td><td>软件限制不自动获得 MIG 的硬件故障隔离；能力依赖设备后端</td><td>私有云、多团队研发、细粒度 vGPU、国产异构设备</td></tr>
<tr><td><strong>CUDA VMM</strong></td><td>不是 K8S 资源类型，由应用或运行时调用 CUDA Driver API</td><td>虚拟地址与物理显存页分离，支持按需映射和弹性显存池</td><td>不负责多租户算力隔离，也不是 GPU 调度器</td><td>KV Cache、模型权重缓存、弹性显存</td></tr>
</tbody>
</table>

## 为什么默认 Kubernetes 不够

默认 NVIDIA Device Plugin 把 GPU 注册为整数扩展资源，例如 `nvidia.com/gpu: 8`。kube-scheduler 主要知道“还有几份资源”，不知道：

- 两个逻辑资源是否来自同一张物理 GPU。
- 当前还剩多少真实显存、SM 和 HBM 带宽。
- 两个 workload 放在一起会产生多大干扰。
- 一个共享进程崩溃是否会影响同卡其他进程。

因此，GPU 虚拟化至少需要两部分：

1. **资源表达和放置**：Device Plugin、GPU Operator、HAMi Scheduler 等告诉 Kubernetes 能分配什么。
2. **执行和隔离**：MIG、MPS、CUDA driver、HAMi-Core 等真正执行硬件或软件限制。

只改 scheduler 的资源数量，不会自动得到显存、算力和故障隔离。

## 选型决策树

```flow
是否要求强故障隔离和稳定 SLA | 是 -> 整卡或 MIG
是否需要细粒度显存/算力任意配比 | 是 -> HAMi，或厂商 vGPU 方案
是否是可信 workload 且希望 kernel 并发 | 是 -> MPS
是否只想让低利用率任务共享访问 | 是 -> Time-Slicing
是否主要解决 KV Cache / 权重显存弹性 | 是 -> CUDA VMM，不要把它当 GPU 算力虚拟化
```

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MIG、MPS、Time-Slicing 和 HAMi 最本质的区别是什么？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">一句话</div><p>MIG 在硬件层切设备，MPS 在驱动层并发执行，Time-Slicing 在时间上共享访问，HAMi 在 Kubernetes 调度和容器运行时层做细粒度软件配额。</p></div>
<div class="qa-section"><div class="qa-section-title">判断标准</div><p>不要只背“隔离强弱”，还要追问隔离对象：MIG 能提供固定硬件实例；MPS 可以限制 client 的执行资源和显存但仍共享故障域；Time-Slicing 只提供共享访问；HAMi 的显存/算力限制依赖软件拦截或设备后端能力。</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 虚拟化是不是就是把一张卡显示成很多张卡？</div>
<div class="qa-a"><p>不是。“显示成多份”只是资源表达。真正要看底层有没有硬件实例、执行资源限制、显存限制和故障隔离。Time-Slicing 可以把一张卡上报成多个逻辑 slot，但这些 slot 仍然共享整张卡；MIG 的每一份则对应真实硬件实例。</p></div>
</div>

## 常见误区

| 误区 | 正确理解 |
|---|---|
| `replicas: 4` 就是每个 Pod 固定获得 25% GPU | 它只表示 4 个共享访问名额；Time-Slicing 不保证固定算力和显存份额。 |
| MPS 和 MIG 都是“切卡” | MIG 创建硬件实例；MPS 让多个 client 通过 server 并发使用同一 GPU。 |
| HAMi 等于开源 MIG | HAMi 是 Kubernetes 虚拟化中间层，NVIDIA 常见实现是软件调度与容器内限制，不等于硬件 MIG。 |
| CUDA VMM 能隔离多个租户的 SM | VMM 管虚拟地址和物理显存映射，不负责 SM 公平或故障隔离。 |
| kube-scheduler 会自动避免共享干扰 | 默认 scheduler 不理解真实 SM/HBM 干扰，需要扩展调度、画像或在线监控。 |

## 资料来源

- [NVIDIA MIG User Guide](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/)
- [NVIDIA Kubernetes Device Plugin](https://github.com/NVIDIA/k8s-device-plugin)
- [NVIDIA CUDA MPS Documentation](https://docs.nvidia.com/deploy/mps/latest/)
- [HAMi 官方文档](https://project-hami.io/docs/)

## 关联模块

- `MIG 实战`：从裸机启用到 GPU Operator 管理和 Pod 申请。
- `MPS 实战`：从 MPS daemon 到 Kubernetes 共享配置和资源限制。
- `Time-Slicing 实战`：配置 replicas、申请共享资源并验证真实边界。
- `HAMi 开源方案`：细粒度显存/算力调度与容器内隔离。
- `生产选型与论文映射`：把机制映射到真实工作负载和个人论文项目。
