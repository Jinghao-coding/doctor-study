## 前缀复用与请求隔离

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q1：相同文本就能共享 KV 吗？命中后 Decode 也会变快吗？</div>
<div class="qa-a"><p>需要是相同的有效前缀，并匹配模型版本、LoRA、token、位置与相关输入。相同文本放在不同前文后面，其隐藏状态可能不同；多模态占位 token 一样也不意味着图片相同。命中主要省掉已缓存前缀的 prefill，后续 decode 仍需关注这些历史位置。</p><p><strong>追问：多 Agent 用同一个模型就能共享上下文吗？</strong>不能。模型权重可以共享，只有满足上述条件的前缀 KV 才可复用；各 Agent 的私有历史和生成分支应保持独立。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q2：前缀缓存的 key 怎么设计？为什么不能只 hash 当前 block？</div>
<div class="qa-a"><p>当前 block 的 K/V 依赖此前上下文。可以将父 block 的 hash、本 block token 和附加输入标识共同构成 key，并用模型版本命名空间隔离；否则相同局部文本可能错误命中不同前文。vLLM 的相关设计还考虑 LoRA、多模态输入和 cache salt。</p><p><strong>追问：多租户怎么隔离？</strong>可信服务端按租户或共享域划分缓存命名空间或 salt，兼顾授权和命中时延侧信道；不能把仅由客户端随意声明的标识当成完整权限机制。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q3：共享 block 为什么需要引用计数和写时复制？</div>
<div class="qa-a"><p>引用计数表示有多少活跃序列在使用物理 block。只读前缀可以共享；若多个生成分支共用一个可写尾块，一个分支追加时要获得独占块或写时复制，避免覆盖另一个分支的数据。采用只共享完整只读块的实现，可以避开部分尾块复制场景。</p><p><strong>追问：引用数归零就立刻清空显存吗？</strong>不一定，可以保留为可驱逐的前缀缓存。活跃引用、缓存索引和可回收队列是不同状态，需要一致维护。</p></div>
</div>

前缀 key、完整块复用和回收状态参见 [vLLM Prefix Caching 设计](https://docs.vllm.ai/en/latest/design/prefix_caching/)。

## 预算、抢占与层级存储

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q4：输出长度未知，怎样准入才能避免 OOM？</div>
<div class="qa-a"><p>把预测用于排序和预留估计，把实际可用 block 数作为执行约束。每轮根据新增 token、未命中 prefill 和临时需求核算下一步需要的块；不足时暂停接纳或抢占，并保留非 KV 显存余量。按最大输出预留较保守，按需分配利用率高但必须有运行时回退。</p><p><strong>追问：预测 p90 能保证不 OOM 吗？</strong>不能，它只表达分布中的一个分位数，还可能漂移。容量检查和超预算处理必须独立存在；多请求各自 p90 也不直接等于整体 p90。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q5：KV 不够了，重算、CPU offload、直接淘汰怎么选？</div>
<div class="qa-a"><p>先区分未被活跃请求引用的缓存和仍在使用的状态。前者可驱逐，代价是将来的 miss；后者只能协调暂停后转存，或丢弃 KV 并保留 token 历史以便重算。比较预计重算耗时和传出、传回、排队成本，同时考虑恢复后的 SLO。</p><p><strong>追问：CPU 内存足够就能无限扩展吗？</strong>不能。PCIe 或网络带宽、拷贝缓冲和重复换入换出会限制吞吐。还需要冷却时间、并发传输上限和进度保障，防止同一请求反复被抢占。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q6：PagedAttention、CUDA VMM、KV offload 是一回事吗？</div>
<div class="qa-a"><p>PagedAttention 通过软件 block table 组织和读取 KV；CUDA VMM 负责虚拟地址的物理显存映射；offload 负责把数据搬到其他存储层。分页 block pool 可能提前占住一大块 GPU 显存，释放逻辑 block 通常只是池内可复用，不代表显存已归还给其他进程。</p><p><strong>追问：论文里说弹性显存，应证明什么？</strong>应分别报告逻辑 KV 用量、已分配物理显存、回收后其他任务实际得到的容量，以及回收/恢复耗时。保留虚拟地址不等于保留物理显存，也不保证旧 KV 数据仍在。</p></div>
</div>

## 性能诊断与验证

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q7：前缀命中率很高，为什么服务还是慢？</div>
<div class="qa-a"><p>先看统计口径：请求命中率高，不代表命中的 token 多；命中的短前缀价值也可能很小。随后分解排队、未命中 prefill、KV 获取和 decode；偏向缓存节点的路由可能造成热点，长输出也会淹没 prefill 节省的时间。</p><p><strong>追问：记录什么指标？</strong>请求命中率、token 命中率、节省的 prefill 时间、KV 占用/驱逐/重算量，以及按输入输出长度分桶的 TTFT、ITL 和完成率。缓存收益最终要体现在业务延迟或吞吐上。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q8：如何证明自己的 KV 管理方案正确且有效？</div>
<div class="qa-a"><p>固定模型、请求 trace、到达速率和输出限制，对比连续分配或现有分页基线，分别测峰值物理显存、有效并发、TTFT/ITL 分位数、完成请求量和失败率。把前缀复用、分页、量化、offload 分开做消融，避免把多个优化收益全归给一个模块。</p><p><strong>正确性追问：</strong>覆盖分支生成、取消、块重复释放、模型版本切换和传输中断；检查引用数与容量不变量。无损管理方案比较同一数值条件下的 logits 或允许误差，量化方案另做质量评测。随机采样时不能只凭最终文字不同判断缓存出错。</p></div>
</div>
