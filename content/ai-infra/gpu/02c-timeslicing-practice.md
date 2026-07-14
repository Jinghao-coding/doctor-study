## 一句话结论

Time-Slicing 的作用是让多个 Pod 获得同一张物理 GPU 的共享访问权。它最容易部署，但也最容易被误解：**`replicas: 4` 只把每张 GPU 注册为 4 个逻辑访问名额，不保证每个 Pod 固定获得 25% 算力、25% 显存或独立故障域。**

## 系统链路

```flow
Device Plugin 读取 timeSlicing 配置
  -> 为每张物理 GPU 创建 N 个逻辑引用
  -> Kubelet 把逻辑数量写入 Node Capacity / Allocatable
  -> kube-scheduler 按普通扩展资源分配 Pod
  -> 多个 Pod 获得同一 GPU UUID 的访问权
  -> CUDA driver 在进程之间交错执行
```

kube-scheduler 不知道这些 slot 来自同一张物理卡，也不会为每个 slot 保留固定 SM 或显存。Time-Slicing 解决的是“能不能共享访问”，不是“怎么保证共享性能”。

## Kubernetes 怎么配置

### 1. 创建 ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nvidia-device-plugin-config
  namespace: gpu-operator
data:
  time-slicing-4: |-
    version: v1
    flags:
      migStrategy: none
    sharing:
      timeSlicing:
        renameByDefault: true
        failRequestsGreaterThanOne: true
        resources:
          - name: nvidia.com/gpu
            replicas: 4
```

关键参数：

<table>
<thead><tr><th>参数</th><th>含义</th><th>为什么重要</th></tr></thead>
<tbody>
<tr><td><code>replicas: 4</code></td><td>每张物理 GPU 创建 4 个共享访问名额</td><td>控制最大共享密度，不是算力比例</td></tr>
<tr><td><code>renameByDefault: true</code></td><td>资源名改为 <code>nvidia.com/gpu.shared</code></td><td>防止用户把共享 slot 当独占 GPU</td></tr>
<tr><td><code>failRequestsGreaterThanOne: true</code></td><td>拒绝单容器一次申请多个共享 slot</td><td>强调申请的是访问权，不是成比例算力</td></tr>
</tbody>
</table>

### 2. 让 Device Plugin 加载配置

GPU Operator 环境示例：

```bash
kubectl apply -f nvidia-device-plugin-config.yaml

kubectl patch clusterpolicy/cluster-policy \
  --type merge \
  -p '{"spec":{"devicePlugin":{"config":{"name":"nvidia-device-plugin-config","default":"time-slicing-4"}}}}'

kubectl label node gpu-node-1 \
  nvidia.com/device-plugin.config=time-slicing-4 --overwrite
```

官方 Device Plugin 的共享方式按节点配置：同一节点上的 GPU 使用相同 sharing method，不能让 GPU0 用 Time-Slicing、GPU1 用 MPS。需要不同策略时，应拆成不同节点池或至少使用不同节点配置。

### 3. 确认资源已经上报

假设节点有 8 张 GPU、每张设置 4 个 replicas，Node 应显示 32 个共享资源：

```bash
kubectl describe node gpu-node-1 \
  | grep -E 'nvidia.com/(gpu.shared|gpu.replicas|gpu.sharing-strategy)'

kubectl get node gpu-node-1 \
  -o jsonpath='{.status.capacity.nvidia\.com/gpu\.shared}{"\n"}'
```

如果仍然只看到 8 张独占 GPU，检查 ConfigMap namespace、ClusterPolicy 引用、节点 label 和 Device Plugin Pod 日志。

## Pod 怎么申请

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: timeslice-demo
spec:
  restartPolicy: Never
  containers:
    - name: cuda
      image: nvcr.io/nvidia/cuda:12.8.0-base-ubuntu22.04
      command: ["bash", "-lc", "nvidia-smi -L && sleep 3600"]
      resources:
        limits:
          nvidia.com/gpu.shared: 1
```

```bash
kubectl apply -f timeslice-demo.yaml
kubectl get pod timeslice-demo -o wide
kubectl exec timeslice-demo -- nvidia-smi -L
kubectl exec timeslice-demo -- nvidia-smi
```

Pod 通常会看到整张物理 GPU 的 UUID 和显存容量。多个 Pod 可能看到同一 UUID，这正是它们共享同一张卡的证据。不能因为 `nvidia-smi` 显示整卡显存，就让每个进程都按整卡容量分配。

## 如何验证真实边界

不要只创建 4 个 sleep Pod。至少进行下面四组实验：

1. **单任务基线**：记录单独运行的吞吐、P50/P99 和显存峰值。
2. **并发压力**：同时运行 2/4 个计算密集 workload，观察性能是否近似均分以及上下文切换开销。
3. **显存冲突**：让两个 workload 的显存总需求超过物理显存，确认其中一个可能 OOM，证明 replicas 不隔离显存。
4. **异常影响**：记录 Xid、Pod 重启和其他同卡 workload 的影响，验证共享故障域风险。

```bash
kubectl get pods -o wide
kubectl logs -n gpu-operator -l app=nvidia-device-plugin-daemonset --tail=200
nvidia-smi pmon -s um -c 10
```

## 适用与不适用

<table>
<thead><tr><th>适合</th><th>不适合</th></tr></thead>
<tbody>
<tr><td>Notebook、交互式开发、低负载实验</td><td>延迟敏感在线推理</td></tr>
<tr><td>低优离线推理和评测</td><td>互不信任租户</td></tr>
<tr><td>可以接受性能抖动的教学/研发集群</td><td>显存峰值大、容易 OOM 的训练</td></tr>
<tr><td>希望低成本提高 Pod 密度</td><td>要求固定 GPU 百分比计费或 SLA</td></tr>
</tbody>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: replicas=4 时，一个 Pod 实际拿到多少 GPU？</div>
<div class="qa-a"><p>它拿到的是“访问一张共享 GPU”的权利，而不是静态 1/4 卡。如果只有一个 CUDA 进程，它可能使用大部分 GPU；多个满负载进程同时运行时，驱动会在它们之间交错执行，但不提供固定算力、显存或 P99 保证。</p></div>
</div>

## 常见误区

| 误区 | 正确理解 |
|---|---|
| 每个 Pod 会只看到 1/4 显存 | 通常仍看到整卡，多个 Pod 的显存申请可能互相挤压。 |
| 申请 2 个 shared GPU 就有两倍算力 | 多申请共享 slot 不代表获得成比例算力，建议开启 `failRequestsGreaterThanOne`。 |
| Time-Slicing 能让训练和推理安全混部 | 它缺少强隔离，在线 SLO 容易被训练 kernel 和显存争用影响。 |
| GPU-Util 变高就说明收益更好 | 还要检查吞吐、JCT、P99、OOM 和上下文切换代价。 |

## 资料来源

- [NVIDIA Kubernetes Device Plugin：CUDA Time-Slicing](https://github.com/NVIDIA/k8s-device-plugin#with-cuda-time-slicing)

## 关联模块

- `MPS 实战`：需要并发执行和等份显存/执行资源限制时的官方方案。
- `HAMi 开源方案`：需要任意显存/算力配比和设备感知调度时的开源方案。
- `利用率诊断链路`：确认提高的是有效吞吐，而不是无效竞争。
