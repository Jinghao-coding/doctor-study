## 副本、模型并行与拓扑

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q1：分布式推理和分布式训练最大的区别是什么？</div>
<div class="qa-a"><p>训练要反向传播、同步梯度并更新状态，通常关注吞吐、收敛时间和恢复；推理通常没有梯度同步，但要管理动态请求、KV 和尾延迟。推理的模型副本可独立处理请求，TP/PP 内部仍需协同通信，不能说推理不需要分布式同步。</p><p><strong>追问：同样的并行配置能通用吗？</strong>未必。小 batch decode 更容易暴露每层通信延迟，训练中能被大计算量隐藏的通信，在推理中可能成为主导。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q2：模型单卡放得下，选 8 个副本还是 TP=8？</div>
<div class="qa-a"><p>先核算权重加目标并发 KV 是否放得下。独立副本适合扩大请求吞吐并隔离故障，但每个副本重复放权重；TP 分摊权重和部分 KV，可扩大容量、降低部分计算耗时，却引入通信。选择取决于输入输出长度、并发与 TTFT/ITL 目标，不能只看模型权重。</p><p><strong>追问：怎么选？</strong>在同一卡数、相同请求分布与到达速率下对比多个副本/TP 组合，统计满足延迟目标的完成吞吐，而不只测单个请求或离线 tokens/s。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q3：跨两台 8 卡机器，为什么常考虑 TP=8、PP=2？</div>
<div class="qa-a"><p>TP 的层内通信频繁，优先利用节点内高速互联；PP 在 stage 边界跨节点传激活，可以减少频繁跨节点 collective。但这是拓扑导向的候选方案，不是固定最优。层数不均、低并发流水线空闲和跨节点激活传输都可能影响效果。</p><p><strong>追问：跨节点 TP 一定不可用吗？</strong>不是。高速网络和合适模型下可行，应比较实际通信代价与 PP 气泡，并检查每个 rank 的 KV 分布和容量。</p></div>
</div>

并行部署方式参见 [vLLM Parallelism and Scaling](https://docs.vllm.ai/en/latest/serving/parallelism_scaling/)。

## Prefill / Decode 分离与 KV 传输

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q4：为什么做 PD 分离？什么情况反而变慢？</div>
<div class="qa-a"><p>把长 prefill 和逐步 decode 放到不同资源池，可以分别调并行度和容量，减少 prefill 对 decode 尾延迟的干扰。代价是传输 KV、多一段排队和路由，以及两边负载不均。短 prompt、网络慢或负载低时，额外成本可能超过收益。</p><p><strong>追问：为什么不只用 chunked prefill？</strong>分块能在共置实例内控制 prefill 对 decode 的干扰，部署更简单；PD 分离多了资源独立伸缩能力，也多了网络成本。应在同一 SLO 下比较，不能直接断言分离一定提升吞吐。</p></div>
</div>

PD 分离的目的与限制参见 [vLLM Disaggregated Prefilling](https://docs.vllm.ai/en/latest/features/disagg_prefill/)。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q5：怎样估算一次 KV 传输是否值得？</div>
<div class="qa-a"><p>先算实际传输的 KV 字节数，再除以有效带宽，加上连接、布局转换、排队和同步开销。假设传 1 GiB、有效带宽 25 GiB/s，纯传输就约 40 ms；若排队和重排再花 15 ms，总成本约 55 ms。只有节省的计算或干扰成本足以抵消这些开销，才可能改善目标指标。</p><p><strong>追问：TP=8 就除以 8 吗？</strong>只有分片能真正并行传输且不竞争同一瓶颈链路时才可能接近。TP 配置不同还要重新分片；共享 NIC 的总流量不能靠 rank 数消失。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q6：KV 传完就能直接开始 Decode 吗？</div>
<div class="qa-a"><p>接收端需先确认容量，校验模型/LoRA 版本、token 和位置、dtype、布局及分片方式，等数据和元信息都就绪后安装映射。不能把部分完成的 KV 标为可读，也不能传输尚未完成就让源端复用该块。</p><p><strong>追问：迁移失败怎么办？</strong>以请求和迁移版本标记状态，保证重复消息幂等；只有接收端确认后才转移所有权。失败时回退原实例或重算，释放暂存块。进行中的请求还需处理已返回 token、采样状态和输出顺序，KV 本身不是完整请求状态。</p></div>
</div>

## 路由、扩缩容与训推协同

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q7：最短队列路由和 KV cache-aware 路由怎样取舍？</div>
<div class="qa-a"><p>队列请求数不等于工作量：一个长 prompt 可能比多个短请求更贵。估计完成成本时要结合排队 token、剩余 prefill/decode、缓存命中节省和 KV 可用容量。命中节点如果已经拥堵，去空闲节点重算可能更快。</p><p><strong>追问：如何避免所有请求追着同一个热点跑？</strong>设置容量和负载约束、并发准入及适度分流；观测缓存命中带来的真实时间节省和各副本尾延迟，避免仅追求命中率。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q8：推理扩容为什么不能等同于增加几个 Pod？</div>
<div class="qa-a"><p>新实例还要准备权重、初始化并行组、分配 KV 和完成必要预热，才能接流量；缓存冷启动也可能增加 prefill。缩容则应先停止新请求，再排空或迁移在途状态，避免直接中断流式回答。</p><p><strong>追问：按什么扩容？</strong>结合队列等待、token 负载、KV 压力和 TTFT/ITL 是否逼近目标，再纳入启动时间；单看 GPU 利用率会漏掉通信等待或缓存容量不足。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q9：分布式训练和在线推理能混在同一批 GPU 上吗？</div>
<div class="qa-a"><p>可以设计混部，但要同时满足显存硬约束和性能要求。训练会占用算力、HBM 带宽和网络，集合通信还可能放大慢 rank 的影响；推理则可能因 prefill 突发或 KV 增长破坏已有预算。应测双向干扰，并对每种配置分别验证训练吞吐和推理尾延迟。</p><p><strong>追问：推理突发时直接暂停一张训练卡行不行？</strong>同步训练的其他 rank 可能一起阻塞。回收应由作业级控制协调，在安全边界降低占用、暂停整个并行组或恢复 checkpoint，并计入保存恢复代价。MPS 配额也不能单独保证尾延迟。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q10：RL 训推协同里，权重更新和 KV Cache 有什么关系？</div>
<div class="qa-a"><p>Rollout 用某一策略版本生成轨迹，训练更新后将新权重同步给推理实例。系统需记录轨迹对应的策略版本，并控制更新与生成的并发边界。旧 KV 由旧权重产生，通常不能直接接到新权重上继续生成。</p><p><strong>追问：怎样切换版本？</strong>可以让在途请求继续使用旧版本，新请求路由到新版本；或排空后整体切换并使缓存失效。异步 rollout 还要记录策略滞后并按训练算法处理，不能只靠缓存管理解决。权重分片与推理并行布局不同，也要付出重排和传输成本。</p></div>
</div>

路由、迁移、混部和版本切换题按系统约束推导具体设计；上述耗时数字是示例估算，不是框架性能承诺。
