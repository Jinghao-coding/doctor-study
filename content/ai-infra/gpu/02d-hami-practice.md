## 一句话结论

HAMi 是面向 Kubernetes 的开源异构加速器虚拟化中间件。它不是简单把 `nvidia.com/gpu` 数量乘大，而是通过 **Mutating Webhook + Scheduler Extender + Device Plugin + HAMi-Core**，同时完成细粒度资源声明、物理设备选择、容器注入以及显存/算力限制。

## HAMi 解决什么问题

官方 NVIDIA Device Plugin 的 Time-Slicing/MPS 主要按 `replicas` 做等份共享。平台如果希望用户声明“我要一张物理 GPU 上的 3GiB 显存和 30% 算力”，默认 kube-scheduler 无法理解这种二维设备容量。

HAMi 为 Pod 增加细粒度资源：

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
    nvidia.com/gpumem: 3000
    nvidia.com/gpucores: 30
```

- `nvidia.com/gpu`：需要分配的 GPU 设备数量。
- `nvidia.com/gpumem`：每个设备的显存需求，常用单位为 MiB。
- `nvidia.com/gpucores`：设备计算资源百分比，1 表示 1%。

HAMi 还支持多种 GPU/NPU/MLU/DCU 等后端，但每种设备的共享和隔离能力不同，不能只看“支持列表”就假设所有硬件都有相同能力。

## 核心架构

```flow
Pod 提交细粒度 GPU request
  -> Mutating Webhook 识别 HAMi resource，并设置 hami-scheduler
  -> Scheduler Extender 维护全局设备视图，执行 Filter / Score / Bind
  -> 选定物理 GPU UUID，把分配结果写入 Pod annotation
  -> HAMi Device Plugin 在 Allocate 阶段挂载设备和运行时配置
  -> HAMi-Core 注入容器，执行显存检查与算力节流
  -> Monitor / Metrics 持续观测分配和使用情况
```

<table>
<thead><tr><th>组件</th><th>职责</th><th>关键状态</th></tr></thead>
<tbody>
<tr><td>Mutating Webhook</td><td>识别 HAMi 资源并选择调度入口</td><td><code>spec.schedulerName</code></td></tr>
<tr><td>Scheduler Extender</td><td>维护剩余显存/算力，选择节点和物理设备</td><td>Node/Pod annotation、设备全局视图</td></tr>
<tr><td>HAMi Device Plugin</td><td>注册设备、读取调度结果、向容器注入设备与环境</td><td>GPU UUID、Allocate 结果</td></tr>
<tr><td>HAMi-Core</td><td>在容器内拦截 CUDA/NVML 调用，执行显存上限和算力节流</td><td>显存上限、SM limit、运行时计数器</td></tr>
</tbody>
</table>

这条链路解释了为什么 HAMi 不能只靠 Device Plugin：标准 scheduler 在调度阶段看不到每张 GPU 剩余多少显存和算力，而 Device Plugin 的 Allocate 又发生在节点已经选定之后。HAMi 需要 Scheduler Extender 先做设备级放置，再通过 annotation 把结果交给节点侧执行。

## Helm 部署

### 1. 前置检查

GPU 节点应先满足：

- NVIDIA driver 和 NVIDIA Container Toolkit 可用。
- 容器运行时已正确配置 NVIDIA runtime。
- Kubernetes、Helm、CUDA/driver 版本符合当前 HAMi release 的兼容矩阵。
- 同一批节点没有另一个 Device Plugin 同时注册和管理相同 GPU 资源。

HAMi、Volcano vGPU Device Plugin 和 NVIDIA 官方 Device Plugin 不应同时管理同一节点上的同一类 GPU。生产上应通过节点池和 label 划分职责。

### 2. 安装

```bash
# 标记由 HAMi 管理的 GPU 节点
kubectl label node gpu-node-1 gpu=on --overwrite

helm repo add hami-charts https://project-hami.github.io/HAMi/
helm repo update

helm install hami hami-charts/hami \
  -n kube-system
```

部分 HAMi 版本要求 scheduler 镜像 tag 与 Kubernetes 版本对应。安装前应阅读所锁定 chart 版本的 values 和兼容说明，不要直接复制其他集群的版本参数。

### 3. 验证控制面与节点组件

```bash
kubectl get pods -n kube-system \
  | grep -E 'hami-(scheduler|device-plugin)'

kubectl logs -n kube-system deploy/hami-scheduler --tail=200
kubectl get daemonset -n kube-system | grep hami-device-plugin
```

至少确认：

- `hami-scheduler` 正常运行并可访问 API Server。
- 每个目标 GPU 节点都有 `hami-device-plugin` Pod。
- Node 上已经注册 HAMi 管理的 GPU 数量与设备信息。
- 原 NVIDIA Device Plugin 没有同时争抢相同资源名。

## Pod 怎么申请细粒度 GPU

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: hami-vgpu-demo
  annotations:
    hami.io/node-scheduler-policy: "binpack"
spec:
  restartPolicy: Never
  containers:
    - name: cuda
      image: nvcr.io/nvidia/cuda:12.8.0-base-ubuntu22.04
      command: ["bash", "-lc", "nvidia-smi && sleep 3600"]
      resources:
        limits:
          nvidia.com/gpu: 1
          nvidia.com/gpumem: 3000
          nvidia.com/gpucores: 30
```

```bash
kubectl apply -f hami-vgpu-demo.yaml
kubectl get pod hami-vgpu-demo -o wide
kubectl get pod hami-vgpu-demo \
  -o jsonpath='{.spec.schedulerName}{"\n"}'
kubectl describe pod hami-vgpu-demo
kubectl exec hami-vgpu-demo -- nvidia-smi
```

预期现象：

- Webhook 将任务路由到 HAMi scheduler。
- Pod annotation 中记录选中的 GPU UUID、显存和算力分配结果。
- 容器内 `nvidia-smi` 看到的显存信息受到 HAMi-Core 的 NVML 拦截影响。
- 超出显存配额的 CUDA 分配返回 OOM，而不是无限挤占同卡其他 Pod。
- 算力限制依靠运行时节流，`nvidia-smi` 的瞬时 GPU-Util 仍可能波动。

注意：Node Capacity/Allocatable 可能主要显示 `nvidia.com/gpu`，而 `gpumem`/`gpucores` 的剩余容量由 HAMi scheduler 的设备视图和 annotation 管理，不一定像普通 Extended Resource 一样直接出现在 Capacity 中。

## 调度策略

<table>
<thead><tr><th>策略</th><th>含义</th><th>适合场景</th></tr></thead>
<tbody>
<tr><td><code>binpack</code></td><td>优先把任务放到已经使用的节点/GPU，保留完整设备</td><td>提高整卡可用性、便于缩容、减少碎片</td></tr>
<tr><td><code>spread</code></td><td>把任务分散到不同节点/GPU</td><td>降低热点和共享干扰，提高故障分散</td></tr>
</tbody>
</table>

选择不能只看利用率：小模型推理可以 binpack，延迟敏感或带宽密集 workload 更适合 spread。多 GPU 训练还要考虑 NVLink/PCIe 拓扑，不能只按显存余量拼卡。

## HAMi 与其他方案怎么选

<table>
<thead><tr><th>维度</th><th>NVIDIA Time-Slicing</th><th>NVIDIA MPS Sharing</th><th>HAMi</th><th>MIG</th></tr></thead>
<tbody>
<tr><td>分配粒度</td><td>共享访问名额</td><td>按 replicas 等份</td><td>显存 MiB + 算力百分比 + 设备数</td><td>固定硬件 profile</td></tr>
<tr><td>调度感知</td><td>主要看逻辑数量</td><td>主要看逻辑数量</td><td>感知单卡剩余显存/算力和设备策略</td><td>profile 作为独立资源</td></tr>
<tr><td>隔离方式</td><td>时间复用，弱</td><td>MPS server 限制</td><td>软件/设备后端限制</td><td>硬件隔离</td></tr>
<tr><td>异构设备</td><td>NVIDIA</td><td>NVIDIA</td><td>面向多厂商扩展</td><td>支持 MIG 的 NVIDIA GPU</td></tr>
<tr><td>系统复杂度</td><td>低</td><td>中</td><td>较高，增加 Webhook/Scheduler/Core</td><td>中，需要 profile 生命周期管理</td></tr>
</tbody>
</table>

HAMi 还提供 dynamic MIG 等扩展能力，但它们依赖支持的 GPU、驱动和 HAMi 版本。面试时应把“HAMi 软件 vGPU”和“HAMi 调用硬件 MIG 动态创建实例”区分开。

## 排障路径

```flow
Pod 未被调度 | 看 schedulerName、Webhook、HAMi scheduler 日志
资源不足 | 看 Pod annotation、设备注册信息、显存/算力剩余视图
Pod 卡在 ContainerCreating | 看 Device Plugin Allocate、runtime、libvgpu 注入
显存限制没生效 | 看 HAMi-Core、LD_PRELOAD、CUDA/NVML 兼容性
性能抖动 | 看 gpucores、binpack 密度、HBM/SM 指标和同卡 workload
设备重复或数量异常 | 排查是否与 NVIDIA/Volcano Device Plugin 冲突
```

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: HAMi 是怎么做到“申请 3GiB GPU 显存”的？</div>
<div class="qa-a"><p>调度阶段，HAMi Scheduler 先从全局设备视图中选择剩余显存足够的物理 GPU，并把 UUID 和 3GiB 配额写入 Pod annotation；Allocate 阶段，Device Plugin 注入设备、环境变量和 HAMi-Core；容器内 HAMi-Core 拦截 CUDA/NVML 的显存查询和分配调用，超过配额时返回 OOM。它是调度账本和容器内执行限制的组合。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: HAMi 和 MIG 最大的区别是什么？</div>
<div class="qa-a"><p>MIG 的边界来自硬件实例，规格固定、故障和性能隔离更强；HAMi 的优势是显存/算力比例更灵活、能做设备感知调度和异构统一管理，但 NVIDIA 常见 vGPU 路径主要依赖软件拦截与节流，不能直接宣称获得 MIG 同等级硬件隔离。</p></div>
</div>

## 资料来源

- [HAMi GitHub](https://github.com/Project-HAMi/HAMi)
- [HAMi Architecture](https://project-hami.io/docs/v2.7.0/core-concepts/architecture)
- [HAMi GPU Virtualization Principles](https://project-hami.io/docs/core-concepts/gpu-virtualization)
- [HAMi Helm Deployment](https://project-hami.io/docs/v2.8.0/get-started/deploy-with-helm)

## 关联模块

- `Time-Slicing 实战`：最轻量的共享访问方案。
- `MPS 实战`：NVIDIA 官方并发共享和等份限制方案。
- `Kubernetes / DRA`：HAMi 当前 Device Plugin/Extender 路径与未来 DRA 设备模型的区别。
- `生产选型与论文映射`：决定何时值得引入 HAMi 的额外控制面复杂度。
