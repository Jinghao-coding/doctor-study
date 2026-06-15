## 一句话结论

K8S 默认把 GPU 当作不可分割的扩展资源，GPU 共享要靠 NVIDIA device-plugin / GPU Operator 把物理 GPU 表达成多个可调度资源。time-slicing、MPS 和 MIG 的本质差异在隔离级别、执行方式和调度语义，不要把逻辑 slot 当成稳定的 1/N 性能。

## 系统链路

```flow
GPU Operator / Device Plugin 读取共享配置
  -> 把物理 GPU 或 MIG 实例上报给 kubelet
  -> kube-scheduler 按扩展资源数量调度 Pod
  -> Pod 内获得 CUDA_VISIBLE_DEVICES / GPU 访问权限
  -> driver / MPS daemon / MIG manager 执行真实共享语义
```

<div class="card card-m">
<h3>K8S 里的 GPU 共享：整体认知</h3>
<p>K8S 默认把 GPU 当作<strong>不可分割的整数资源</strong>：一个容器 request <code>nvidia.com/gpu: 1</code> 就独占一整张卡。要在 K8S 里实现共享（MPS / time-slicing / MIG），靠的都是 <strong>NVIDIA k8s-device-plugin</strong>。它负责把物理 GPU "拆分"成多个可调度的资源单元，上报给 kubelet。</p>
<table>
<tr><th>共享方式</th><th>K8S 落地组件</th><th>隔离强度</th><th>本质</th></tr>
<tr><td>Time-slicing</td><td>device-plugin 配置 replicas</td><td>无隔离（仅时间轮转）</td><td>把 1 张卡复制成 N 个逻辑资源</td></tr>
<tr><td>MPS</td><td>device-plugin sharing.mps</td><td>弱隔离（空分复用）</td><td>多进程共享 CUDA 上下文并行执行</td></tr>
<tr><td>MIG</td><td>device-plugin + MIG Manager</td><td>硬件强隔离</td><td>物理切片，独立 SM/显存</td></tr>
</table>
<p>三者底层都是上层 device-plugin 把同一张 GPU 的 UUID 重复或切片上报，让多个 Pod 调度到同一张物理卡。</p>
</div>

<div class="card card-s">
<h3>方式一：Time-slicing(时间片)</h3>
<p><strong>原理</strong>：device-plugin 把一张物理 GPU 复制成 N 个同名资源（共享同一 UUID），多个 Pod 调度上去后由 GPU 驱动的时间片调度器轮流执行。没有内存隔离、没有故障隔离，一个 Pod 跑飞会影响其他 Pod。</p>
<p><strong>配置步骤</strong>：通过 ConfigMap 定义切分策略，再让 device-plugin 加载。</p>
<pre><code># time-slicing ConfigMap：把每张卡复制成 4 份
apiVersion: v1
kind: ConfigMap
metadata:
  name: time-slicing-config
  namespace: gpu-operator
data:
  any: |-
    version: v1
    flags:
      migStrategy: none
    sharing:
      timeSlicing:
        renameByDefault: false
        failRequestsGreaterThanOne: true
        resources:
        - name: nvidia.com/gpu
          replicas: 4
</code></pre>
<p><strong>关键参数</strong>：</p>
<ul>
<li><code>replicas: 4</code> —— 一张卡上报为 4 个 <code>nvidia.com/gpu</code>，最多 4 个 Pod 共享。</li>
<li><code>failRequestsGreaterThanOne: true</code> —— 共享模式下单个 Pod 只能 request 1，防止误用。</li>
<li><code>renameByDefault: true</code> —— 把资源名改为 <code>nvidia.com/gpu.shared</code>，便于和独占卡区分调度。</li>
</ul>
<p><strong>启用（GPU Operator）</strong>：</p>
<pre><code>kubectl patch clusterpolicy/cluster-policy \
  -n gpu-operator --type merge \
  -p '{"spec":{"devicePlugin":{"config":{"name":"time-slicing-config","default":"any"}}}}'
</code></pre>
<p><strong>Pod 使用</strong>：和普通 GPU Pod 写法完全一样，调度器自动把它放到被复制的逻辑资源上。</p>
<pre><code>resources:
  limits:
    nvidia.com/gpu: 1   # 实际是 1/4 张卡的时间片
</code></pre>
</div>

<div class="card card-w">
<h3>方式二:MPS(Multi-Process Service)</h3>
<p><strong>原理</strong>：device-plugin 启动 MPS Control Daemon，多个 Pod 的 CUDA 进程通过 MPS Server 共享同一 GPU 上下文，kernel 可以<strong>真正并行</strong>地跑在不同 SM 上（空分复用），而不是 time-slicing 的时间轮转。还能按比例限制每个客户端的显存和算力。</p>
<p><strong>配置步骤</strong>：</p>
<pre><code># MPS ConfigMap：把每张卡按 MPS 方式分成 4 份
apiVersion: v1
kind: ConfigMap
metadata:
  name: mps-config
  namespace: gpu-operator
data:
  any: |-
    version: v1
    sharing:
      mps:
        renameByDefault: false
        resources:
        - name: nvidia.com/gpu
          replicas: 4
</code></pre>
<pre><code>kubectl patch clusterpolicy/cluster-policy \
  -n gpu-operator --type merge \
  -p '{"spec":{"devicePlugin":{"config":{"name":"mps-config","default":"any"}}}}'
</code></pre>
<p><strong>效果</strong>：每个客户端默认分到 <code>1/replicas</code> 的显存上限（4 份即每份约 1/4 显存）和算力配额。device-plugin 会自动拉起 MPS daemon，无需手动 <code>nvidia-cuda-mps-control</code>。</p>
<p><strong>Pod 使用</strong>：同样 request <code>nvidia.com/gpu: 1</code> 即可，对应一个 MPS slice。</p>
</div>

<div class="card card-r">
<h3>Time-slicing vs MPS:怎么选?</h3>
<table>
<tr><th>维度</th><th>Time-slicing</th><th>MPS</th></tr>
<tr><td>执行方式</td><td>时间轮转(串行切换)</td><td>SM 空分(真并行)</td></tr>
<tr><td>显存隔离</td><td>无,容易互相 OOM</td><td>有,可按比例限制</td></tr>
<tr><td>算力 QoS</td><td>无,抢占式</td><td>可设 active thread 百分比</td></tr>
<tr><td>故障隔离</td><td>差,一个崩可能拖累全部</td><td>较差,共享上下文一个进程崩可能影响 MPS server</td></tr>
<tr><td>上下文切换开销</td><td>有(切换上下文)</td><td>低(共享上下文)</td></tr>
<tr><td>适用场景</td><td>开发/测试、推理流量低、Notebook</td><td>多个稳定小推理、I/O 互补的训练任务</td></tr>
</table>
<p><strong>经验法则</strong>：纯粹想"塞更多任务进来、不在乎隔离"用 time-slicing；想要并行吞吐和一定的显存/算力配额用 MPS;要强隔离、多租户生产环境用 MIG。三者不能在同一张卡上叠加(同一时刻一张卡只能选一种共享策略)。</p>
</div>

<div class="card card-s">
<h3>节点级差异化配置</h3>
<p>集群里往往有的节点要共享、有的要独占。device-plugin config 支持多份命名配置,再用节点 label 选择。</p>
<pre><code># ConfigMap 里放多份配置
data:
  shared: |-
    version: v1
    sharing:
      timeSlicing:
        resources:
        - name: nvidia.com/gpu
          replicas: 8
  exclusive: |-
    version: v1
    flags:
      migStrategy: none
</code></pre>
<pre><code># 给节点打 label 选择对应配置
kubectl label node gpu-node-1 \
  nvidia.com/device-plugin.config=shared
kubectl label node gpu-node-2 \
  nvidia.com/device-plugin.config=exclusive
</code></pre>
<p>这样一个集群里既能有 8 路共享的推理节点,也能保留整卡独占的训练节点。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: time-slicing 的 replicas=4，是不是每个 Pod 拿到 1/4 算力？</div>
<div class="qa-a"><p>不是。time-slicing 只是<strong>时间轮转</strong>，没有任何资源配额。replicas=4 意味着最多 4 个 Pod 能调度到这张卡,它们轮流占用整张卡跑一个时间片。如果只有 1 个 Pod 在跑,它能用满整卡;如果 4 个都满负载,它们大致平分时间但会有上下文切换开销。它解决的是"调度上能不能放进来",不解决"性能隔离"。要按比例限制算力/显存,得用 MPS 或 MIG。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: K8S 里 MPS 比裸机 MPS 多做了什么？</div>
<div class="qa-a"><p>裸机用 MPS 需要手动启动 <code>nvidia-cuda-mps-control -d</code>、设置 <code>CUDA_MPS_*</code> 环境变量、管理 pipe 目录。K8S 里 device-plugin(GPU Operator)把这些全自动化:自动拉起 MPS Control Daemon、为每个 slice 注入正确的环境变量和显存/算力配额、把 N 个 MPS slice 作为可调度资源上报给 kubelet。开发者只要正常 request <code>nvidia.com/gpu: 1</code>,底层就落在一个受配额限制的 MPS 客户端上。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 共享 GPU 后，Pod 里 nvidia-smi 看到的是什么？</div>
<div class="qa-a"><p>time-slicing 和 MPS 下,Pod 里 <code>nvidia-smi</code> 看到的是<strong>整张物理卡</strong>(同一个 UUID),显示的显存总量也是整卡的——因为它们本质是共享同一设备。这容易误导:程序如果按 nvidia-smi 的总显存来分配,在 MPS 配额或多 Pod 共存时会 OOM。相比之下 MIG 下看到的是切分后的实例(独立显存)。所以共享场景要靠应用自己控制显存用量,或依赖 MPS 的显存上限配额。</p></div>
</div>

## 常见误区

| 误区 | 正确理解 |
|---|---|
| `replicas=4` 就是每个 Pod 固定 1/4 算力 | time-slicing 只是逻辑 slot 和时间轮转，不保证固定算力。 |
| kube-scheduler 理解 GPU 干扰 | 默认 scheduler 只看扩展资源数量，不知道 SM、HBM、P99 抖动。 |
| MPS 和 MIG 都是硬隔离 | MIG 是硬件切片，MPS 是共享上下文，隔离弱很多。 |
| Pod 里看到整卡显存就可以全用 | time-slicing/MPS 下多个 Pod 共享同一卡，应用需要限制显存使用。 |

## 面试回答

**30 秒版：**

K8S 默认把 GPU 当整数扩展资源，`nvidia.com/gpu: 1` 表示一整张卡。共享 GPU 通常靠 NVIDIA device-plugin 或 GPU Operator 配置 time-slicing、MPS 或 MIG，把物理 GPU 上报成多个逻辑资源。scheduler 只按资源数量调度，真正的共享和隔离由 driver、MPS daemon 或 MIG 硬件分区实现。time-slicing 简单但无隔离，MPS 可以并发但共享故障域，MIG 隔离强但切分粒度固定。

**2 分钟版：**

我会先说明 K8S 的资源模型：GPU 是 extended resource，默认不可分割。device-plugin 把 GPU 资源发现并上报给 kubelet，scheduler 只看到 `nvidia.com/gpu` 这类资源名和数量。共享时，time-slicing 通过 replicas 把一张卡复制成多个逻辑 slot；MPS 启动 MPS control daemon，让多个 CUDA 进程共享上下文并可设置一定显存/算力比例；MIG 则把支持的 GPU 做硬件切片，上报成独立实例。生产选择要看 SLA 和隔离：开发测试可以 time-slicing，可信小任务可以 MPS，强隔离多租户优先 MIG。

## 关联模块

- `共享方式`：理解 MIG/MPS/time-slicing 的底层取舍。
- `Kubernetes 核心`：device plugin、extended resource、node label 和调度语义。
- `调度与集群`：共享密度、显存碎片、干扰建模和租户配额。
