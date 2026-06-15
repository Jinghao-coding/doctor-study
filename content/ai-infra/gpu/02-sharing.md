## 一句话结论

GPU 共享不是一种机制，而是一组取舍：MIG 追求硬件隔离，MPS 追求多进程并发，time-slicing 追求低成本复用，CUDA VMM 解决虚拟地址和物理显存映射弹性。面试里要先说清隔离边界，再谈利用率提升。

## 核心概念

| 方式 | 隔离级别 | 原理 | 适用场景 |
|---|---|---|---|
| MIG | 硬件切片 | 物理切分 GPU 为独立实例，各有独立显存和 SM | 推理、多租户强隔离、稳定 SLA |
| MPS | 进程级复用 | 多进程共享 GPU 上下文，并发执行 kernel | 可信团队、小 kernel、小模型推理 |
| Time Slicing | 时间级复用 | 多个进程按时间片轮换使用同一 GPU | Notebook、开发测试、低优实验 |
| CUDA VMM | 虚拟内存 | 虚拟地址空间预留，物理页按需映射 | KV cache、显存池、弹性内存管理 |
| vGPU | 虚拟化 | Hypervisor 层虚拟化 GPU | 云桌面、传统虚拟化多租户 |

## 系统链路

Kubernetes 里常见链路是：GPU Operator 或 NVIDIA Device Plugin 读取共享配置，把一张物理 GPU 暴露成多个逻辑扩展资源；kube-scheduler 只按资源数量调度 Pod；真正的共享语义由 driver、MPS daemon、CUDA runtime 或 MIG manager 执行。

在 Kubernetes 里，MPS 和 Time Slicing 通常不是通过改 kube-scheduler 实现，而是通过 **NVIDIA Device Plugin / NVIDIA GPU Operator** 把一张物理 GPU 暴露成多个可被 Pod 申请的逻辑 GPU slot。

<table>
<tr><th>机制</th><th>K8s 资源表达</th><th>底层含义</th><th>适合场景</th></tr>
<tr><td>Time Slicing</td><td><code>sharing.timeSlicing.resources[].replicas</code></td><td>多个 Pod 按时间片轮流使用同一张 GPU</td><td>Notebook、开发测试、低优实验、小推理</td></tr>
<tr><td>MPS</td><td><code>sharing.mps.resources[].replicas</code></td><td>多个 CUDA 进程通过 MPS daemon 并发共享 GPU</td><td>可信团队内的小 kernel、多进程推理</td></tr>
</table>

例如把 `nvidia.com/gpu` 配成 `replicas: 4` 后，一张物理 GPU 会向 Kubernetes 上报为 4 个逻辑可申请资源；如果开启 `renameByDefault: true`，Pod 侧通常申请 `nvidia.com/gpu.shared: 1`，从语义上区分共享 GPU 和独占 GPU。

关键边界：**scheduler 只看到逻辑资源数量，不理解每个 slot 的真实性能隔离。**Time Slicing 和 MPS 都不是 MIG 那种硬件切分，生产使用时要特别关注显存 OOM、P99 延迟抖动、监控归因和 workload 之间的干扰。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MIG 和 MPS 的本质区别？</div>
<div class="qa-a"><p><strong>MIG</strong> 是硬件级切分——GPU 被物理切成若干独立实例，每个实例有自己的 SM、显存控制器和缓存，互相完全隔离，类似物理分区。<strong>MPS</strong> 是软件级复用——多个进程共享同一个 GPU 上下文，kernel 可以并行执行在不同 SM 上，但共享显存和缓存，有干扰风险。MIG 安全但粒度粗（A100 最多 7 个实例），MPS 灵活但需要干扰控制。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: K8s 里 Time Slicing 和 MPS 是否需要改 kube-scheduler？</div>
<div class="qa-a"><p>通常不需要。常见做法是让 NVIDIA Device Plugin 或 GPU Operator 读取 sharing ConfigMap，把每张物理 GPU 按 <code>replicas</code> 上报成多个逻辑扩展资源。scheduler 仍然按扩展资源数量做普通调度；真正的时间片复用或 MPS 并发共享发生在 NVIDIA device plugin、driver 和 MPS daemon 层。面试时要强调：K8s 调度的是逻辑 GPU slot，不代表底层有稳定硬隔离。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CUDA VMM 的虚拟内存超配原理？</div>
<div class="qa-a"><p>类似操作系统的虚拟内存：用 cuMemAddressReserve 分配大块虚拟地址（如 122GB），再用 cuMemMap 按需映射物理页。物理显存只有 40GB，但虚拟地址空间 122GB。应用看到连续大内存，实际物理页按需分配和回收。</p></div>
</div>

## 显存碎片

GPU 显存碎片可以分为两类：**外部碎片**和**内部碎片**。外部碎片是总空闲显存足够，但没有足够大的连续块；内部碎片是为了对齐或预留最大长度而分配了比实际需求更大的块。

<table>
<tr><th>来源</th><th>怎么产生</th><th>典型场景</th></tr>
<tr><td>动态 tensor shape</td><td>不同 batch、seq_len、activation 大小频繁变化，allocator 反复 malloc/free</td><td>训练中动态 batch、变长输入</td></tr>
<tr><td>KV Cache 长短不一</td><td>每个请求输出长度不同，传统连续 KV 分配难复用</td><td>LLM serving 高并发长尾请求</td></tr>
<tr><td>多进程共享 GPU</td><td>不同进程各自持有 CUDA context 和 allocator pool，彼此不可见</td><td>MPS/time-slicing 多租户共享</td></tr>
<tr><td>大块临时 workspace</td><td>cuBLAS/cuDNN/NCCL/attention kernel 需要临时 buffer，峰值时挤占连续空间</td><td>大 batch prefill、长上下文 attention</td></tr>
<tr><td>框架缓存策略</td><td>PyTorch caching allocator 为减少 cudaMalloc 开销会缓存块，可能形成不可用空洞</td><td>训练/推理长期运行服务</td></tr>
</table>

面试要点：OOM 不一定表示总显存不够，也可能是可用连续块不够、allocator pool 不可回收，或某个进程持有了大量碎片化缓存。

## 关键机制

显存碎片治理要分层看：

<table>
<tr><th>层次</th><th>手段</th><th>作用</th><th>代价</th></tr>
<tr><td>调度层</td><td>按显存需求做 bin packing</td><td>把大显存任务放到空闲完整 GPU，避免被小任务切碎</td><td>可能牺牲负载均衡</td></tr>
<tr><td>调度层</td><td>保留整卡/整 MIG profile</td><td>给大模型或长上下文推理保留连续容量</td><td>利用率可能下降</td></tr>
<tr><td>调度层</td><td>限制共享密度</td><td>MPS/time-slicing 不盲目提高 replicas，避免多进程显存互相挤压</td><td>可调度 slot 变少</td></tr>
<tr><td>Runtime 层</td><td>预分配 memory pool</td><td>减少运行期频繁 cudaMalloc/free</td><td>启动时占用显存更多</td></tr>
<tr><td>Runtime 层</td><td>固定 block/page 管理</td><td>把 KV Cache 切成固定块，非连续物理块也能组合</td><td>需要 block table 和引用计数</td></tr>
<tr><td>Runtime 层</td><td>CUDA VMM / expandable segment</td><td>用虚拟地址隐藏物理页不连续，支持按需映射</td><td>依赖 CUDA/驱动能力和框架支持</td></tr>
<tr><td>模型层</td><td>GQA/MQA、KV 量化、Prefix Cache</td><td>减少 KV Cache 体积或复用已有缓存</td><td>可能影响精度或增加缓存治理复杂度</td></tr>
</table>

如果面试官追问“调度层能不能解决显存碎片”，可以回答：调度层只能减少碎片产生概率，比如保留大块资源、限制共享密度、做显存画像；真正的细粒度碎片复用要靠 runtime allocator、PagedAttention、CUDA VMM 这类机制。

## 对比表

<table>
<tr><th>机制</th><th>优点</th><th>缺点</th><th>调度建议</th></tr>
<tr><td>MIG</td><td>硬件隔离强，显存/L2/SM 分区清晰，QoS 稳定</td><td>profile 固定，切分不灵活，容易产生 profile 碎片</td><td>生产多租户、强 SLA 推理优先使用</td></tr>
<tr><td>MPS</td><td>多个 CUDA 进程可并发执行，小 kernel 利用率更高，可限制一定 SM 占比</td><td>共享显存/缓存/故障域，内存争用时性能可能明显下降</td><td>可信团队、同类 workload、小模型推理或实验共享</td></tr>
<tr><td>Time Slicing</td><td>配置简单，兼容老卡，适合把低利用率任务超卖到同一张卡</td><td>无硬隔离，不保证 1/N 算力或显存，P99 抖动明显</td><td>Notebook、开发测试、低优任务，生产谨慎</td></tr>
</table>

一句话：**MIG 是隔离优先，MPS 是并发效率优先，Time Slicing 是部署简单和提高密度优先。**强隔离多租户不要把 MPS/Time Slicing 当 MIG 用。

## 常见误区

| 误区 | 正确理解 |
|---|---|
| time-slicing 的 `replicas: 4` 等于每个 Pod 固定 1/4 GPU | 它只是暴露 4 个逻辑 slot，不保证算力、显存或 P99 延迟隔离。 |
| MPS 可以提供 MIG 级别隔离 | MPS 共享显存、cache 和故障域，适合可信 workload，不适合强隔离多租户。 |
| scheduler 理解 GPU 共享真实性能 | 默认 scheduler 只看扩展资源数量，不理解每个 slot 的干扰和带宽争用。 |
| 显存碎片只靠调度解决 | 调度只能减少碎片产生，细粒度复用要靠 runtime allocator、PagedAttention、CUDA VMM。 |

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 显存碎片在调度系统里怎么观测？</div>
<div class="qa-a"><p>至少要同时看三类指标：GPU 总显存使用率、进程级显存占用、allocator 层 reserved/allocated 差值。对 PyTorch 服务，可以看 <code>memory_reserved - memory_allocated</code> 判断缓存池空洞；对推理引擎，还要看 KV block 使用率、空闲 block 数、prefix cache 命中率和 OOM 前的最大可分配块。调度层可把这些画像沉淀成任务 profile，用于后续显存 bin packing 和共享密度控制。</p></div>
</div>

## 面试回答

**30 秒版：**

GPU 共享要先区分隔离语义。MIG 是硬件切片，SM、显存和 cache 边界清晰，适合生产多租户和稳定 SLA；MPS 是软件级多进程共享，可以提升小 kernel 或小模型并发效率，但共享显存和 cache，有干扰风险；time-slicing 是按时间复用，部署简单但不保证固定算力。K8S 里通常通过 NVIDIA Device Plugin 把物理 GPU 暴露成多个逻辑资源，scheduler 只看到 slot，不理解真实性能隔离。

**2 分钟版：**

我会从调度层和 runtime 层两层讲。调度层通过 device plugin、GPU Operator、MIG profile、共享 replicas 和节点标签来表达可分配资源，但它只能决定 Pod 放在哪里。runtime 层才真正决定 GPU 怎么共享：MIG 由硬件分区，MPS 由 MPS daemon 合并多个 CUDA context，time-slicing 由 driver 轮换上下文，CUDA VMM 则用虚拟地址和物理页映射解决弹性显存。生产里选择方案要看 SLA、租户信任边界、显存压力和 P99 抖动，而不是只看平均利用率。

## 关联模块

- `K8S GPU 共享`：继续看 device plugin、replicas 和节点级配置。
- `CUDA 内存模型与 Occupancy`：理解显存、shared memory、register 对共享密度的影响。
- `LLM 推理系统`：KV cache、PagedAttention 和 CUDA VMM 是显存共享的重要场景。
- `调度与集群`：共享 GPU 会引入干扰建模、碎片治理和拓扑感知调度问题。
