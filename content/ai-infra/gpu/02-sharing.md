<table>
<tr><th>方式</th><th>隔离级别</th><th>原理</th><th>适用场景</th></tr>
<tr><td>MIG</td><td>硬件切片</td><td>物理切分 GPU 为独立实例，各有独立显存和 SM</td><td>推理、多租户强隔离</td></tr>
<tr><td>MPS</td><td>进程级复用</td><td>多进程共享 GPU 上下文，并行执行 kernel</td><td>训练合用、I/O 互补</td></tr>
<tr><td>时间片</td><td>时间级复用</td><td>CUDA 调度器轮换上下文</td><td>轻量共享、交互式</td></tr>
<tr><td>CUDA VMM</td><td>虚拟内存</td><td>虚拟地址空间超配，物理页按需映射</td><td>KV 缓存弹性管理</td></tr>
<tr><td>vGPU</td><td>虚拟化</td><td>Hypervisor 层虚拟化 GPU</td><td>云服务多租户</td></tr>
</table>

<div class="card card-m">
<h3>K8s 中 MPS / Time Slicing 怎么落地</h3>
<p>在 Kubernetes 里，MPS 和 Time Slicing 通常不是通过改 kube-scheduler 实现，而是通过 <strong>NVIDIA Device Plugin / NVIDIA GPU Operator</strong> 把一张物理 GPU 暴露成多个可被 Pod 申请的逻辑 GPU slot。</p>
<table>
<tr><th>机制</th><th>K8s 资源表达</th><th>底层含义</th><th>适合场景</th></tr>
<tr><td>Time Slicing</td><td><code>sharing.timeSlicing.resources[].replicas</code></td><td>多个 Pod 按时间片轮流使用同一张 GPU</td><td>Notebook、开发测试、低优实验、小推理</td></tr>
<tr><td>MPS</td><td><code>sharing.mps.resources[].replicas</code></td><td>多个 CUDA 进程通过 MPS daemon 并发共享 GPU</td><td>可信团队内的小 kernel、多进程推理</td></tr>
</table>
<p>例如把 <code>nvidia.com/gpu</code> 配成 <code>replicas: 4</code> 后，一张物理 GPU 会向 Kubernetes 上报为 4 个逻辑可申请资源；如果开启 <code>renameByDefault: true</code>，Pod 侧通常申请 <code>nvidia.com/gpu.shared: 1</code>，从语义上区分共享 GPU 和独占 GPU。</p>
<p>关键边界：<strong>scheduler 只看到逻辑资源数量，不理解每个 slot 的真实性能隔离。</strong>Time Slicing 和 MPS 都不是 MIG 那种硬件切分，生产使用时要特别关注显存 OOM、P99 延迟抖动、监控归因和 workload 之间的干扰。</p>
</div>

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

<div class="card card-w">
<h3>显存碎片是如何产生的？</h3>
<p>GPU 显存碎片可以分为两类：<strong>外部碎片</strong> 和 <strong>内部碎片</strong>。外部碎片是总空闲显存足够，但没有足够大的连续块；内部碎片是为了对齐或预留最大长度而分配了比实际需求更大的块。</p>
<table>
<tr><th>来源</th><th>怎么产生</th><th>典型场景</th></tr>
<tr><td>动态 tensor shape</td><td>不同 batch、seq_len、activation 大小频繁变化，allocator 反复 malloc/free</td><td>训练中动态 batch、变长输入</td></tr>
<tr><td>KV Cache 长短不一</td><td>每个请求输出长度不同，传统连续 KV 分配难复用</td><td>LLM serving 高并发长尾请求</td></tr>
<tr><td>多进程共享 GPU</td><td>不同进程各自持有 CUDA context 和 allocator pool，彼此不可见</td><td>MPS/time-slicing 多租户共享</td></tr>
<tr><td>大块临时 workspace</td><td>cuBLAS/cuDNN/NCCL/attention kernel 需要临时 buffer，峰值时挤占连续空间</td><td>大 batch prefill、长上下文 attention</td></tr>
<tr><td>框架缓存策略</td><td>PyTorch caching allocator 为减少 cudaMalloc 开销会缓存块，可能形成不可用空洞</td><td>训练/推理长期运行服务</td></tr>
</table>
<p>面试要点：OOM 不一定表示总显存不够，也可能是可用连续块不够、allocator pool 不可回收、或某个进程持有了大量碎片化缓存。</p>
</div>

<div class="card card-d">
<h3>调度层和 Runtime 层如何缓解显存碎片？</h3>
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
<p>如果面试官追问“调度层能不能解决显存碎片”，可以回答：调度层只能减少碎片产生概率，比如保留大块资源、限制共享密度、做显存画像；真正的细粒度碎片复用要靠 runtime allocator、PagedAttention、CUDA VMM 这类机制。</p>
</div>

<div class="card card-m">
<h3>MPS、MIG、Time Slicing 的多租户取舍</h3>
<table>
<tr><th>机制</th><th>优点</th><th>缺点</th><th>调度建议</th></tr>
<tr><td>MIG</td><td>硬件隔离强，显存/L2/SM 分区清晰，QoS 稳定</td><td>profile 固定，切分不灵活，容易产生 profile 碎片</td><td>生产多租户、强 SLA 推理优先使用</td></tr>
<tr><td>MPS</td><td>多个 CUDA 进程可并发执行，小 kernel 利用率更高，可限制一定 SM 占比</td><td>共享显存/缓存/故障域，内存争用时性能可能明显下降</td><td>可信团队、同类 workload、小模型推理或实验共享</td></tr>
<tr><td>Time Slicing</td><td>配置简单，兼容老卡，适合把低利用率任务超卖到同一张卡</td><td>无硬隔离，不保证 1/N 算力或显存，P99 抖动明显</td><td>Notebook、开发测试、低优任务，生产谨慎</td></tr>
</table>
<p>一句话：<strong>MIG 是隔离优先，MPS 是并发效率优先，Time Slicing 是部署简单和提高密度优先。</strong>强隔离多租户不要把 MPS/Time Slicing 当 MIG 用。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 显存碎片在调度系统里怎么观测？</div>
<div class="qa-a"><p>至少要同时看三类指标：GPU 总显存使用率、进程级显存占用、allocator 层 reserved/allocated 差值。对 PyTorch 服务，可以看 <code>memory_reserved - memory_allocated</code> 判断缓存池空洞；对推理引擎，还要看 KV block 使用率、空闲 block 数、prefix cache 命中率和 OOM 前的最大可分配块。调度层可把这些画像沉淀成任务 profile，用于后续显存 bin packing 和共享密度控制。</p></div>
</div>

<div class="card card-s">
<h3>参考资料</h3>
<ul>
<li>NVIDIA GPU Operator Time-Slicing 文档：说明 GPU replicas、共享 GPU 与 MIG 的隔离差异。</li>
<li>NVIDIA GPU Operator MIG 文档：说明 Ampere 及后续架构可把 GPU 分区为安全独立实例，并由 MIG Manager 管理节点配置。</li>
<li>NVIDIA GPU workload consolidation 文章和 MPS/MIG 评测论文：强调 MPS 的灵活性与 MIG 的隔离性之间存在取舍。</li>
</ul>
</div>
