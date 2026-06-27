## 一句话结论

推理服务部署的核心是把 GPU 算力转化为可预测的 SLO——TTFT 和 TPOT 是两个独立指标，弹性扩缩容要基于 KV 占用率和队列深度而非 GPU-Util，CUDA Graph 在 decode 阶段能省 10-15% 延迟但前提是 shape 稳定。

<div class="card card-m">
<h3>SLO 指标体系：TTFT、TPOT 与延迟分位数</h3>
<p>推理服务不是"吞吐越高越好"，而是要在 SLO 约束下最大化吞吐。面试官常考的 SLO 指标有明确的物理含义和优化方向。</p>
</div>

<div class="card card-s">
<h3>核心延迟指标</h3>
<div class="table-scroll">
<table>
<thead><tr><th>指标</th><th>全称</th><th>物理含义</th><th>主要影响因素</th><th>典型 SLO 目标</th></tr></thead>
<tbody>
<tr><td><strong>TTFT</strong></td><td>Time To First Token</td><td>从请求到达到首 token 输出的时间</td><td>排队等待、Prefill 计算、Prefix Cache 命中</td><td>P50 &lt; 200ms, P99 &lt; 500ms</td></tr>
<tr><td><strong>TPOT</strong></td><td>Time Per Output Token</td><td>每生成一个 token 的平均间隔</td><td>Decode 计算、KV Cache 访存、Batch 大小</td><td>P50 &lt; 30ms, P99 &lt; 80ms</td></tr>
<tr><td><strong>ITL</strong></td><td>Inter-Token Latency</td><td>相邻 token 的时间间隔（同 TPOT）</td><td>同 TPOT</td><td>同 TPOT</td></tr>
<tr><td><strong>E2E Latency</strong></td><td>End-to-End Latency</td><td>请求从到达到完成的总时间</td><td>TTFT + (output_len - 1) × TPOT + 排队</td><td>视输出长度而定</td></tr>
<tr><td><strong>Throughput</strong></td><td>-</td><td>每秒生成 token 数或完成请求数</td><td>Batch size、GPU 利用率、并发数</td><td>tokens/s 或 requests/s</td></tr>
</tbody>
</table>
</div>
</div>

<div class="card card-d">
<h3>延迟分位数为什么重要</h3>
<p>在线推理服务<strong>只看平均延迟是自杀行为</strong>。P50 代表典型体验，P95/P99 代表长尾体验，而用户感知到的恰恰是最差体验。</p>
<ul>
<li><strong>P50</strong>：一半请求比它快，一半比它慢——代表典型用户体验</li>
<li><strong>P95</strong>：5% 的请求超过这个延迟——排查一般性能问题</li>
<li><strong>P99</strong>：1% 的请求超过这个延迟——排查尾延迟、GC、抢占、慢节点</li>
<li><strong>P999</strong>：0.1% 的极端尾部——通常对应故障、超时、重试风暴</li>
</ul>
<p>TTFT 和 TPOT 的分位数要<strong>分别监控</strong>：TTFT P99 高说明排队或 prefill 资源不足；TPOT P99 高说明 decode 阶段有抢占、chunked prefill 干扰、或 batch 过大。</p>
</div>

<div class="card card-w">
<h3>SLO 分解公式</h3>
<p>给定输入长度 S_in、输出长度 S_out、TP=4：</p>
<div class="formula">$$\text{E2E} = T_{\text{queue}} + T_{\text{prefill}}(S_{in}) + (S_{out} - 1) \times T_{\text{decode}}$$</div>
<ul>
<li>T_queue：排队等待调度，由并发度和 batch 饱和度决定</li>
<li>T_prefill：≈ S_in / (prefill_tokens_per_second)，compute-bound，典型 1000-8000 tok/s/GPU</li>
<li>T_decode：每个 token 一次 forward，memory-bound，典型 20-80 tok/s/GPU（batch 大时更高）</li>
</ul>
<p><strong>关键洞察</strong>：输出 512 token 时，TTFT 占比 &lt; 20%，TPOT 是主导；输出 10 token 时，TTFT 占比 &gt; 80%。短文本场景优化 TTFT，长文本场景优化 TPOT。</p>
</div>

<div class="card card-m">
<h3>弹性扩缩容（Autoscaling）</h3>
<p>推理服务的流量有明显的波峰波谷，弹性扩缩容是控制成本的关键。但和 Web 服务不同，LLM 推理不能简单基于 CPU/GPU-Util 扩缩容。</p>
</div>

<div class="card card-s">
<h3>为什么不能用 GPU-Util 做 HPA</h3>
<p>GPU-Util 反映的是时间维度的利用率，而非负载压力：</p>
<ol>
<li><strong>Decode 阶段 GPU-Util 天然低</strong>：memory-bound 阶段 SM 利用率可能只有 30-50%，但服务已经接近满载</li>
<li><strong>GPU-Util 100% ≠ 服务饱和</strong>：可能是在做低效的小 batch decode，加机器反降 GPU-Util</li>
<li><strong>KV Cache 才是硬约束</strong>：显存中 KV block 耗尽时，新请求必须排队或抢占，此时 GPU-Util 可能只有 60%</li>
</ol>
</div>

<div class="card card-d">
<h3>正确的扩缩容指标</h3>
<div class="table-scroll">
<table>
<thead><tr><th>指标</th><th>含义</th><th>扩容阈值</th><th>缩容阈值</th></tr></thead>
<tbody>
<tr><td><strong>KV Cache 使用率</strong></td><td>已分配 KV block / 总 block</td><td>&gt; 80% 扩容</td><td>&lt; 30% 缩容</td></tr>
<tr><td><strong>Waiting Queue 长度</strong></td><td>等待调度的请求数</td><td>&gt; 0 持续 30s 扩容</td><td>= 0 持续 5min 缩容</td></tr>
<tr><td><strong>TTFT P99</strong></td><td>首 token 延迟分位数</td><td>&gt; SLO 阈值扩容</td><td>&lt; SLO 50% 缩容</td></tr>
<tr><td><strong>Running 序列数</strong></td><td>当前正在 decode 的并发数</td><td>接近 max_num_seqs 扩容</td><td>&lt; 50% 缩容</td></tr>
<tr><td><strong>Preemption 速率</strong></td><td>每秒抢占次数</td><td>&gt; 0 持续扩容</td><td>= 0 考虑缩容</td></tr>
</tbody>
</table>
</div>
</div>

<div class="card card-w">
<h3>扩缩容工程挑战</h3>
<ul>
<li><strong>冷启动延迟</strong>：加载 70B 模型权重需要 30-120 秒（HBM 带宽 ~2TB/s，但权重 140GB），突发流量来不及</li>
<li><strong>权重预热</strong>：实例启动后先跑几个 warmup 请求，让 CUDA kernel JIT 编译、CUDA Graph capture、权重预取完成</li>
<li><strong>缩容优雅退出</strong>：不能直接 kill，要等 running 请求完成或设最长等待时间（如 60s）；新请求不再路由到该实例</li>
<li><strong>PD 分离场景</strong>：Prefill 和 Decode 独立扩缩容。Prefill 集群按 QPS × avg_input_len 扩；Decode 集群按并发数 × avg_output_len 扩</li>
<li><strong>最小实例数</strong>：必须保留 baseline 实例数应对突发，不能缩到 0</li>
</ul>
</div>

<div class="card card-m">
<h3>CUDA Graph：生产部署视角</h3>
<p>CUDA Graph 把一系列 kernel launch 录制成一张图，replay 时一次性提交，省去逐个 launch 的 CPU 开销和驱动层延迟。</p>
</div>

<div class="card card-s">
<h3>为什么 Decode 阶段最受益</h3>
<ul>
<li><strong>Shape 固定</strong>：Decode 阶段 batch_size 不变时，input shape（1 token × batch × hidden_dim）每步都一样</li>
<li><strong>Kernel launch 开销占比高</strong>：Decode step 计算量小（单 token），kernel launch 延迟（每次 ~5-10μs，上百个 kernel 累计 0.5-1ms）占 TPOT 比例大</li>
<li><strong>Prefill 不适合</strong>：Prefill 的 input 长度多变（不同 prompt 长度差异大），shape 不固定，无法 capture 一张通用 graph</li>
</ul>
<p><strong>收益</strong>：Llama-3-8B BF16 在 A100 上 decode TPOT 降低 10-15%；小模型（7B 以下）收益更大（计算量小，launch 开销占比高）。</p>
</div>

<div class="card card-d">
<h3>vLLM 中的 CUDA Graph 实践</h3>
<ul>
<li><strong>多 graph capture</strong>：为不同 batch_size（1, 2, 4, 8, ..., max_num_seqs）各 capture 一张 graph；运行时按实际 batch 匹配最近的 graph，padding 到对应 batch 大小</li>
<li><strong>Padding 开销</strong>：实际 batch=6 时用 batch=8 的 graph，多算 2 个位置，但省去了 launch 开销，整体仍赚</li>
<li><strong>内存开销</strong>：每张 graph 占用一定显存存中间状态，batch 档位越多越占显存；vLLM 默认 capture 约 8-10 个档位</li>
<li><strong>开关</strong>：<code>--enforce-eager</code> 关闭 CUDA Graph（调试用）；默认开启</li>
<li><strong>与 Chunked Prefill 兼容</strong>：Prefill 不走 graph，decode 走 graph；混合 batch 时 decode 部分 padding 到最近档位</li>
</ul>
</div>

<div class="card card-w">
<h3>生产部署 Checklist</h3>
<pre><code>1. 模型加载
   ├── 权重格式（safetensors / GGUF / TensorRT engine）
   ├── 多卡 TP/PP 初始化（NCCL 通信域建立）
   └── Warmup：跑 5-10 次 dummy forward，触发 JIT + Graph capture
2. 服务配置
   ├── max_num_seqs：最大并发序列数（按显存/KV 估算）
   ├── max_num_batched_tokens：单 step 最大 token 预算
   ├── --enable-chunked-prefill：开启分块 prefill
   ├── --enable-prefix-caching：开启前缀缓存
   └── 量化配置（AWQ/GPTQ/FP8/FP8-KV）
3. 监控告警
   ├── TTFT P50/P95/P99
   ├── TPOT P50/P95/P99
   ├── KV Cache 使用率 & Prefix Cache 命中率
   ├── Running/Waiting/Swapped 队列长度
   ├── GPU-Util、显存、功耗、温度
   └── Preemption 次数、OOM 次数
4. 扩缩容策略
   ├── KV 使用率 &gt; 80% → 扩容
   ├── TTFT P99 &gt; SLO → 扩容
   ├── KV 使用率 &lt; 30% 且 waiting=0 → 缩容
   └── 冷启动 60-120s，保留 baseline 实例
5. 容灾
   ├── 多 AZ 部署
   ├── 健康检查：/health 端点 + 实际推理 probe
   ├── 慢节点驱逐：TPOT P99 持续异常 → 摘除
   └── 滚动升级：权重本地缓存 + 连接 drain</code></pre>
</div>

<div class="card card-r">
<h3>常见面试陷阱</h3>
<ul>
<li>❌ "GPU-Util 低说明服务没压力" → decode 阶段 GPU-Util 天生低，要看 KV 和队列</li>
<li>❌ "CUDA Graph 对所有阶段都有用" → 只对 shape 固定的 decode 有用，prefill 不适合</li>
<li>❌ "TTFT 高就是 prefill 慢" → 可能是排队等待，先看 queue_time 指标</li>
<li>❌ "弹性扩缩容可以缩到 0" → 模型加载几十秒，必须保留最小实例</li>
<li>❌ "平均延迟达标就行" → 在线服务 P99 才是用户感知的体验</li>
</ul>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q1: 怎么估算一个 LLM 推理服务的显存需求？</div>
<div class="qa-a">
<p><strong>显存 = 模型权重 + KV Cache + 激活/Workspace + CUDA Graph 开销</strong></p>

<img src="../../../resources/images/llm-inference/pagedattention-fig1-memory-layout.png" alt="A100 GPU 上 LLM 推理显存布局（PagedAttention 论文 Figure 1）" style="width:100%;max-width:640px;margin:8px 0 8px 0;border-radius:8px;border:1px solid var(--border);" loading="lazy"/>
<p style="font-size:0.85em;color:var(--text-secondary);margin:0 0 12px 0;">来源：PagedAttention 论文（SOSP'23）Figure 1：13B 模型在 A100-40GB 上权重占 65%、KV Cache 约 30%</p>

<div class="qa-section"><div class="qa-section-title">模型权重</div><p>参数量 × bytes_per_param。BF16/FP16 是 2 bytes/param；INT8/W8A8 是 1 byte/param；W4A16/AWQ 是约 0.5 bytes/param + 少量元数据。例：70B BF16 ≈ 140GB，70B W4A16 ≈ 35GB + overhead。</p></div>
<div class="qa-section"><div class="qa-section-title">KV Cache</div><p>2 × layers × kv_heads × head_dim × seq_len × bytes × batch。Llama-3-70B：80层, 8 KV heads(GQA), head_dim=128，BF16 KV = 2×80×8×128×2 bytes/token = 327,680 bytes/token ≈ 320KB/token。batch=64, seq=4096 → 320KB × 64 × 4096 ≈ 80GB。FP8 KV 减半到 ~40GB。</p></div>
<div class="qa-section"><div class="qa-section-title">激活/Workspace</div><p>Prefill 阶段临时激活，约 1-5GB 取决于 batch 和 seq；Decode 阶段很小。FlashAttention 的 workspace 通常几百 MB。</p></div>
<div class="qa-section"><div class="qa-section-title">CUDA Graph</div><p>每 capture 一个 batch 档位占用几十到几百 MB，8-10 个档位共 1-3GB。</p></div>
<div class="qa-summary">快速估算：权重占大头（70B BF16 ≈ 140GB），KV Cache 按并发×上下文长度算。生产环境一般留 20% 余量。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q2: A100 和 H100 在 LLM 推理中的实际性能差异有多大？为什么？</div>
<div class="qa-a">
<p><strong>典型差距：H100 推理吞吐是 A100 的 2-3 倍，decode TPOT 降低 40-60%。</strong></p>
<div class="qa-section"><div class="qa-section-title">硬件差异</div>
<p>A100: 40/80GB HBM2e, 1.6/2.0 TB/s 带宽, 312 TFLOPS BF16, 无 FP8 支持。H100 SXM: 80GB HBM3, 3.35 TB/s 带宽, 989 TFLOPS BF16 (Tensor Core), 1979 TFLOPS FP8。</p></div>
<div class="qa-section"><div class="qa-section-title">Prefill（compute-bound）</div>
<p>H100 BF16 Tensor Core 算力是 A100 的 ~3.2x，加上 TMA + warp specialization 等 Hopper 特性，prefill 吞吐约 2.5-3x A100。FP8 再提升 1.5-2x（需模型支持）。</p></div>
<div class="qa-section"><div class="qa-section-title">Decode（memory-bound）</div>
<p>Decode 瓶颈在 HBM 带宽。H100 HBM3 带宽 3.35 TB/s vs A100 HBM2e 2.0 TB/s，理论上限 1.67x；加上 FlashAttention v3、FP8 KV 等优化，实际 decode 吞吐约 1.8-2.4x。</p></div>
<div class="qa-section"><div class="qa-section-title">互联</div>
<p>H100 NVLink 900 GB/s vs A100 600 GB/s，多卡 TP 通信更快；H100 支持 NVLink Switch 全互联。</p></div>
<div class="qa-summary">A100→H100 不是简单频率升级，是算力（3x）+带宽（1.7x）+FP8+TMA 的代际跨越，推理端到端约 2-3x 提升。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q3: TP=4 和 PP=4 在同样的模型上，通信量差多少？</div>
<div class="qa-a">
<p><strong>TP=4 每层通信量远大于 PP=4，但频率也更高；PP 的问题是 pipeline bubble。</strong></p>
<div class="qa-section"><div class="qa-section-title">TP=4 通信量</div><p>Tensor Parallel 在每层 attention 和 FFN 末尾各做一次 All-Reduce。单次 All-Reduce 通信量 ≈ 2 × (hidden_dim / TP) × (TP-1)/TP × dtype_size。简化：每层每个 token 通信量 ≈ 2 × hidden_dim × dtype_size（All-Reduce 的 ring 实现总传输量约 2×(P-1)/P × message_size ≈ 2 × message_size for P≥4）。Llama-70B hidden=8192, BF16: 每层每 token ≈ 2 × 8192 × 2 = 32KB。80 层 × 2（attn+ffn）= 每 token 全模型 ~5MB 通信。TP 走 NVLink，延迟低。</p></div>
<div class="qa-section"><div class="qa-section-title">PP=4 通信量</div><p>Pipeline Parallel 在 stage 边界传输激活值。每 micro-batch 传输一次激活：batch × seq_len × hidden_dim × dtype_size。PP=4 切 4 段，只有 3 个边界点，每个 micro-batch 在边界处通信 2 次（前向+反向，但推理只需前向）。单次通信量 = batch × seq × hidden_dim × 2B，batch=1, seq=1(decode) 时只有 ~16KB，但 PP 的问题是<strong>气泡</strong>而非通信量：4 stage 流水线，第一个输出需要 4 个 step（等所有 stage 充满），之后每 step 出一个结果，但首次延迟高。</p></div>
<div class="qa-section"><div class="qa-section-title">推理选型</div><p>推理 decode 阶段 batch=1 时 PP 的通信量小但 bubble 大（首 token 延迟高），TP 通信量大但延迟低（NVLink 900GB/s 传 32KB ≈ 0.04μs）。所以推理<strong>优先 TP，慎用 PP</strong>；只有模型大到单节点放不下（如 400B+）才跨机 TP+PP 混合。</p></div>
<div class="qa-summary">推理优先 TP（低延迟、通信可被 NVLink 掩盖），PP 只用于模型跨节点时；TP 通信量大但频率高、单次小；PP 通信量小但有 pipeline bubble。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q4: 推理服务 TTFT P99 突然升高怎么排查？</div>
<div class="qa-a">
<p><strong>按数据流路径从外到内逐层排查：</strong></p>
<div class="qa-section"><div class="qa-section-title">1. 接入层</div><p>检查网关 LB 延迟、鉴权耗时、限流排队。看 Nginx/Envoy 的 upstream_response_time。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 队列等待</div><p>看 <code>vllm:request_queue_time_seconds</code>：如果 queue_time 涨了，说明服务端调度不过来。可能原因：max_num_seqs 打满、KV Cache 满了导致 waiting 队列堆积、某实例卡住。</p></div>
<div class="qa-section"><div class="qa-section-title">3. Prefill 阶段</div><p>看 <code>vllm:time_to_first_token_seconds</code> 减去 queue_time。Prefill 慢可能是：chunked prefill 的 token budget 太小、有长 prompt 抢占了 prefill 资源、Prefix Cache 命中率下降。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 抢占/重算</div><p>看 <code>vllm:num_preemptions_total</code>：抢占激增说明 KV 不足，新请求触发 recompute/swap，TTFT 暴涨。</p></div>
<div class="qa-section"><div class="qa-section-title">5. 慢节点/坏卡</div><p>检查是否有单个实例的 TTFT 远高于其他实例（负载不均或硬件故障）。DCGM 看 ECC 错误、NVLink 降速、温度异常。</p></div>
<div class="qa-section"><div class="qa-section-title">6. GC/内存压力</div><p>Python GC 停顿、CPU 内存不足导致 swap、宿主机其他进程抢占 CPU。</p></div>
<div class="qa-summary">排查顺序：接入层 → 队列等待 → Prefill → 抢占 → 慢节点 → 系统层。先看 queue_time 拆分 TTFT。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q5: vLLM 和 TensorRT-LLM 在生产部署上的核心差异？</div>
<div class="qa-a">
<p><strong>差异在于：vLLM 是"Python 生态优先"，TRT-LLM 是"性能优先但工程成本高"。</strong></p>
<div class="qa-section"><div class="qa-section-title">易用性</div><p>vLLM：<code>pip install vllm</code> + 一行命令启动，自动从 HF 下载模型，支持绝大多数开源模型。TRT-LLM：需要把模型 build 成 TensorRT engine（离线编译 30-60min），版本绑定严格（TRT 版本 × CUDA 版本 × 模型版本），新模型支持滞后 2-4 周。</p></div>
<div class="qa-section"><div class="qa-section-title">性能</div><p>TRT-LLM 在 NVIDIA 自家 GPU 上通常比 vLLM 快 10-30%（极致 kernel fusion、in-flight batching、FP8 全栈优化），但差距在缩小（vLLM 0.6+ 引入 FlashInfer、FP8、CUDA Graph 默认开启后差距约 5-15%）。</p></div>
<div class="qa-section"><div class="qa-section-title">灵活性</div><p>vLLM：Python 代码可直接 hack 调度器、加自定义 logits processor、做研究原型。TRT-LLM：核心是 C++ runtime + 预编译 engine，改 kernel 需要重新 build，灵活性差。</p></div>
<div class="qa-section"><div class="qa-section-title">生态</div><p>vLLM：社区活跃、模型支持最快、与 LangChain/vLLM Production Stack/K8s 集成好。TRT-LLM：NVIDIA 官方支持、与 Triton Inference Server 深度集成、企业级 SLA。</p></div>
<div class="qa-summary">快速上线/研究/多样模型选 vLLM；NVIDIA 全栈、极致性能、大厂核心业务选 TRT-LLM + Triton。</div>
</div>
</div>

<div class="card card-s">
<h3>🔗 关联模块</h3>
<ul>
<li><strong>端到端链路</strong>：6 阶段 pipeline 中本页对应"调度→输出"的服务化部分。</li>
<li><strong>Prefill/Decode</strong>：解释了两阶段为何瓶颈不同，直接影响 SLO 指标分解。</li>
<li><strong>推理引擎对比</strong>：vLLM/TRT-LLM/SGLang 引擎内核对比，本页补充部署运维视角。</li>
<li><strong>性能瓶颈</strong>：本页 SLO 指标是瓶颈分析的观测入口。</li>
<li><strong>集群管理</strong>：GPU 监控（DCGM）、弹性扩缩容在 K8s 上的落地。</li>
</ul>
</div>
