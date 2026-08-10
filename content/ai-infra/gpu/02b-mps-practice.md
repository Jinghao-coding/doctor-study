## MPS 执行链路

```flow
MPS control daemon | 接收管理命令并创建 MPS server
MPS server | 持有 GPU 调度资源，接收多个 client 的 CUDA work
CUDA clients | 通过 pipe 连接 server，提交 kernel 和内存申请
GPU | 允许来自不同 client 的 kernel 并发执行
监控 | nvidia-smi / DCGM / MPS ps 观察 client、显存和吞吐
```

MPS 的目标是降低多 CUDA context 独立运行的切换成本，并增加小 kernel 的并发机会。它不是 MIG：不同 client 仍然共享物理 GPU、部分缓存、带宽和故障域。

## 裸机怎么用

### 1. 启动 MPS daemon

下面是单用户、单 GPU 的最小实验流程。生产环境需要独立服务账号、目录权限和进程生命周期管理。

```bash
export CUDA_VISIBLE_DEVICES=0
export CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps
export CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-log

mkdir -p "$CUDA_MPS_PIPE_DIRECTORY" "$CUDA_MPS_LOG_DIRECTORY"
nvidia-cuda-mps-control -d

# 查看 server 和 client
echo ps | nvidia-cuda-mps-control
```

随后在同一组 MPS pipe 配置下启动两个 CUDA 进程，它们会连接到 MPS server。应用必须在创建 CUDA context 之前设置资源限制。

### 2. 限制执行资源

```bash
# 该 client 新建 CUDA context 时最多使用约 30% 的可用执行资源
export CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=30
python inference_worker.py
```

`CUDA_MPS_ACTIVE_THREAD_PERCENTAGE` 限制的是 client 可用的执行线程比例，最终值会按硬件支持粒度取整。它不是“把每个时刻的 GPU-Util 精确锁死在 30%”，也不直接保证业务吞吐等于整卡的 30%。

MPS 还支持通过控制命令设置未来 client 的默认执行比例：

```bash
echo 'set_default_active_thread_percentage 30' \
  | nvidia-cuda-mps-control
```

### 3. 限制显存

```bash
# 限制未来 MPS client 在 GPU 0 上可分配的 device memory
echo 'set_default_device_pinned_mem_limit 0 8G' \
  | nvidia-cuda-mps-control

# client 侧还可以进一步收紧，不能突破 server 的更低限制
export CUDA_MPS_PINNED_DEVICE_MEM_LIMIT='0=6G'
python inference_worker.py
```

超出限制时，CUDA 内存分配会返回 OOM。显存限制要预留 CUDA context、库 workspace 和通信 buffer，不要只按模型权重大小计算。

### 4. 停止 MPS

```bash
echo ps | nvidia-cuda-mps-control
echo quit | nvidia-cuda-mps-control
```

退出前先停止 client workload。异常退出后还要检查残留 server、pipe 目录和 GPU 上下文。

## Kubernetes 怎么用

NVIDIA Device Plugin 的 MPS sharing 用 `replicas` 定义等份共享资源。官方文档仍将该能力标为实验性；MPS 与 Time-Slicing 互斥，并且当前不能用于已启用 MIG 的设备。

### 1. 创建共享配置

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nvidia-device-plugin-config
  namespace: gpu-operator
data:
  mps-4: |-
    version: v1
    flags:
      migStrategy: none
    sharing:
      mps:
        renameByDefault: true
        resources:
          - name: nvidia.com/gpu
            replicas: 4
```

这表示每张 GPU 暴露 4 个 `nvidia.com/gpu.shared`，MPS control daemon 为每个共享资源限制为大约总显存和执行资源的四分之一。它与裸机手工设置任意百分比不同：这里是按 replicas 等份管理。

### 2. 让 Device Plugin 加载配置

GPU Operator 环境可以让 ClusterPolicy 引用 ConfigMap，并通过节点 label 选择配置：

```bash
kubectl apply -f nvidia-device-plugin-config.yaml

kubectl patch clusterpolicy/cluster-policy \
  --type merge \
  -p '{"spec":{"devicePlugin":{"config":{"name":"nvidia-device-plugin-config","default":"mps-4"}}}}'

kubectl label node gpu-node-1 \
  nvidia.com/device-plugin.config=mps-4 --overwrite
```

不同 GPU Operator / Device Plugin 版本的 chart 字段可能变化，上线前要以所锁定版本的配置 schema 为准。

### 3. Pod 申请与验证

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mps-demo
spec:
  restartPolicy: Never
  containers:
    - name: cuda
      image: nvcr.io/nvidia/cuda:12.8.0-base-ubuntu22.04
      command: ["bash", "-lc", "nvidia-smi && sleep 3600"]
      resources:
        limits:
          nvidia.com/gpu.shared: 1
```

```bash
kubectl describe node gpu-node-1 \
  | grep -E 'nvidia.com/(gpu.shared|gpu.sharing-strategy|mps.capable)'

kubectl apply -f mps-demo.yaml
kubectl exec mps-demo -- nvidia-smi
```

验证不能只看 Pod Running，还要同时运行多份实际 workload，比较：

- 单独运行与共置运行的吞吐、P50/P99 延迟。
- 每个 client 的显存峰值和 OOM 行为。
- SM Active、DRAM throughput、L2、PCIe 等 DCGM 指标。
- 任一 client 异常时，其他 client 是否受到影响。

## 什么时候适合 MPS

<table>
<thead><tr><th>适合</th><th>不适合</th></tr></thead>
<tbody>
<tr><td>同一团队的多个小模型推理</td><td>互不信任租户、需要强故障隔离</td></tr>
<tr><td>单任务 kernel 很小，整卡利用率低</td><td>单任务已经接近打满 SM 或 HBM</td></tr>
<tr><td>计算型与 I/O 型 workload 互补</td><td>严格 P99 SLO 且无法容忍共享抖动</td></tr>
<tr><td>能持续采集干扰指标并自动降级</td><td>只有“多放几个 Pod”而没有运行时保护</td></tr>
</tbody>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MPS 设置 30%，是不是这个进程永远只能获得 30% GPU 性能？</div>
<div class="qa-a"><p>不是。active thread percentage 约束 client 能使用的执行资源上限，不直接等价于业务性能比例。实际吞吐还受 kernel 并行度、显存带宽、cache、CPU/IO、其他 client 负载和硬件取整影响，必须用真实 workload 基准测试。</p></div>
</div>

## 常见误区

| 误区 | 正确理解 |
|---|---|
| 启用 MPS 后多个进程就完全隔离 | MPS 改善并发和可施加资源限制，但仍共享物理 GPU 与故障域。 |
| Active thread 30% 等于 GPU-Util 30% | 它限制执行资源，不是业务层的恒定利用率。 |
| 只限制 SM 就不会互相影响 | 显存容量、HBM 带宽、L2、PCIe、CPU/IO 仍可能成为共享瓶颈。 |
| MPS 可以直接和 MIG sharing 同时打开 | 官方 Device Plugin 当前不支持在 MIG-enabled device 上启用 MPS sharing。 |

## 资料来源

- [NVIDIA MPS：When to Use MPS](https://docs.nvidia.com/deploy/mps/when-to-use-mps.html)
- [NVIDIA MPS Tools and Interface](https://docs.nvidia.com/deploy/mps/610/appendix-tools-and-interface-reference.html)
- [NVIDIA Kubernetes Device Plugin](https://github.com/NVIDIA/k8s-device-plugin)
