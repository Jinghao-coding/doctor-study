<div class="card card-m">
<h3>分布式计算：Role 与 Replica</h3>
<p>分布式系统里，Role 描述“这个进程承担什么职责”，Replica 描述“这个职责有多少个副本”。它们经常一起出现在训练任务、推理服务、微服务和 Kubernetes workload 中。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Role 和 Replica 在分布式计算中一般指什么？</div>
<div class="qa-a">
<p><strong>Role</strong> 是角色，表示一个进程或一组进程在系统中的职责；<strong>Replica</strong> 是副本，表示同一角色启动了多少个实例。</p>
<table>
<tr><th>概念</th><th>含义</th><th>例子</th></tr>
<tr><td>Role</td><td>职责类型</td><td>worker、parameter server、chief、scheduler、trainer、evaluator</td></tr>
<tr><td>Replica</td><td>同一 role 的实例数</td><td>8 个 worker、2 个 PS、3 个 serving replica</td></tr>
<tr><td>Rank</td><td>分布式通信中的全局或局部编号</td><td>PyTorch DDP 的 global rank/local rank</td></tr>
<tr><td>World size</td><td>参与通信的总进程数</td><td>8 卡训练通常 world size = 8</td></tr>
</table>
<p>例如一个 PyTorchJob 可以有 1 个 master role 和 8 个 worker role；worker role 的 replicas 是 8。每个 worker 进程会拿到不同的 rank，参与 NCCL all-reduce。</p>
<p>面试中可以这样回答：Role 解决“做什么”，Replica 解决“做几个”，Rank 解决“我是第几个”。</p>
</div>
</div>

<div class="card card-s">
<h3>通信与存储补充</h3>
<p>原文的“通信（NCCL，Thrift/RPC）”和“存储”没有列出具体思考题，这里补充最常见的理解边界。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: NCCL 通信和 Thrift/RPC 通信有什么区别？</div>
<div class="qa-a">
<table>
<tr><th>维度</th><th>NCCL</th><th>Thrift/RPC</th></tr>
<tr><td>定位</td><td>GPU 集合通信库</td><td>服务间请求/响应通信框架</td></tr>
<tr><td>典型场景</td><td>all-reduce、broadcast、reduce-scatter</td><td>控制面 API、任务提交、元数据查询</td></tr>
<tr><td>数据规模</td><td>大 tensor、高吞吐</td><td>结构化消息，通常较小</td></tr>
<tr><td>网络</td><td>NVLink、PCIe、IB/RDMA、RoCE</td><td>TCP/HTTP/自定义传输</td></tr>
<tr><td>关注点</td><td>带宽、拓扑、rank 映射、同步语义</td><td>延迟、超时、重试、负载均衡、兼容性</td></tr>
</table>
<p>一句话：NCCL 更像“训练数据平面的高速集体搬运”，RPC 更像“控制面的服务调用”。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 分布式训练为什么特别关注存储？</div>
<div class="qa-a">
<p>因为训练链路不只消耗 GPU，还持续读取样本、写 checkpoint、加载模型权重。如果存储吞吐或元数据性能不足，GPU 会等待数据，表现为 GPU 利用率低但任务并没有真正计算。</p>
<table>
<tr><th>场景</th><th>存储瓶颈</th><th>优化方向</th></tr>
<tr><td>数据集读取</td><td>小文件多、随机读、元数据压力大</td><td>打包样本、缓存、预取、顺序读</td></tr>
<tr><td>Checkpoint</td><td>多 worker 同时写大文件，带宽尖峰</td><td>分片 checkpoint、异步写、错峰保存</td></tr>
<tr><td>模型加载</td><td>启动时大量节点同时拉权重</td><td>镜像预热、本地缓存、分层存储</td></tr>
<tr><td>日志/指标</td><td>高频小写导致后端压力</td><td>批量写、采样、异步聚合</td></tr>
</table>
</div>
</div>

<div class="card card-d">
<h3>NVIDIA GPU 查看命令</h3>
<p>GPU 排查第一步通常是确认：机器有几张卡、是什么型号、显存使用多少、哪些进程占用了 GPU。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 对于 NVIDIA GPU 上的机器/容器，怎么查看有几块 GPU、分别是什么型号、有哪些进程在使用 GPU？</div>
<div class="qa-a">
<p>最常用工具是 <code>nvidia-smi</code>。</p>
<pre><code class="language-bash"># 总览：卡数量、型号、显存、温度、功耗、进程
nvidia-smi

# 只列 GPU 编号、名称、显存
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free --format=csv

# 查看正在使用 GPU 的计算进程
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv

# 持续刷新
watch -n 1 nvidia-smi

# 拓扑关系：GPU-GPU、GPU-NIC、CPU affinity
nvidia-smi topo -m

# 更详细的设备列表
nvidia-smi -L</code></pre>
<p>容器内如果看不到 GPU，可能是没有使用 NVIDIA Container Toolkit、没有分配 GPU device、<code>NVIDIA_VISIBLE_DEVICES</code> 限制、K8s device plugin 没有注入设备，或者权限/驱动不匹配。</p>
<table>
<tr><th>问题</th><th>排查方向</th></tr>
<tr><td>看不到 <code>nvidia-smi</code></td><td>镜像里没有工具或 PATH 不对</td></tr>
<tr><td><code>nvidia-smi</code> 报 driver 错</td><td>宿主机驱动、容器 runtime、CUDA 兼容性</td></tr>
<tr><td>宿主机有卡，容器内无卡</td><td>K8s GPU request、device plugin、runtimeClass、设备挂载</td></tr>
<tr><td>有进程占卡但不知道是谁</td><td>用 PID 结合 <code>ps -fp &lt;pid&gt;</code> 或 <code>cat /proc/&lt;pid&gt;/cmdline</code></td></tr>
</table>
</div>
</div>

<div class="card card-w">
<h3>MLU 与 SM Active</h3>
<p>原文 MLU 和 SM Active 小节没有具体问题，但这两个概念常用于国产加速器和 GPU 利用率分析。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MLU 通常指什么？和 GPU/NPU 是什么关系？</div>
<div class="qa-a">
<p>MLU 常指 Machine Learning Unit，是寒武纪等厂商对 AI 加速器的命名。它和 GPU/NPU 一样，都属于面向深度学习计算的加速器，但具体编程栈、驱动、算子库和监控工具不同。</p>
<table>
<tr><th>维度</th><th>NVIDIA GPU</th><th>MLU/NPU 等 AI 加速器</th></tr>
<tr><td>编程栈</td><td>CUDA、cuDNN、NCCL</td><td>厂商 SDK、算子库、通信库</td></tr>
<tr><td>K8s 接入</td><td>NVIDIA device plugin / DRA driver</td><td>厂商 device plugin / operator</td></tr>
<tr><td>监控</td><td><code>nvidia-smi</code>、DCGM</td><td>厂商 CLI 和 exporter</td></tr>
<tr><td>排查关注</td><td>显存、SM、Tensor Core、NVLink</td><td>片上内存、计算核心、算子支持、驱动兼容</td></tr>
</table>
<p>面试时不要把 MLU 简单说成 GPU。更准确的说法是：MLU 是某类 AI 加速器产品名，系统层面要关注设备发现、运行时、算子库、通信库、容器注入和调度资源表达。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: SMA = SM Active 是什么？如何理解这个指标？</div>
<div class="qa-a">
<p>SM Active 表示 GPU Streaming Multiprocessor 处于 active 状态的比例，可以理解为 GPU 计算单元有多少时间在执行工作。它是判断 GPU 是否“忙于计算”的重要指标，但不能单独代表整体效率。</p>
<table>
<tr><th>现象</th><th>可能原因</th><th>进一步看什么</th></tr>
<tr><td>SM Active 高，显存带宽高</td><td>计算和访存都很忙，可能接近满载</td><td>MFU、Tensor Core 利用率、功耗</td></tr>
<tr><td>SM Active 低，显存带宽高</td><td>内存带宽瓶颈，典型如 LLM decode/KV cache 读取</td><td>HBM bandwidth、cache hit、batch size</td></tr>
<tr><td>SM Active 低，显存带宽也低</td><td>CPU/data loading/I/O/调度等待瓶颈</td><td>DataLoader、磁盘、网络、CPU 利用率</td></tr>
<tr><td>SM Active 高，但训练慢</td><td>可能 kernel 效率低、通信等待、算子碎片化</td><td>NCCL timeline、kernel profile、MFU</td></tr>
</table>
<p>SM Active 适合做诊断入口，但面试中要补充：它不等于模型 FLOPS 利用率，也不等于吞吐。分析 GPU 性能要同时看 SM、Tensor Core、HBM、PCIe/NVLink、CPU 数据供给和通信等待。</p>
</div>
</div>
