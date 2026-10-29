## 从模型名到具体实例

Kthena 为模型服务提供部署管理和请求路由。一次推理请求进入 Router 后，先根据模型名和请求规则匹配 ModelRoute，再选择目标 ModelServer，最后在其后端 Pod 中进行过滤和评分。模型内部计算由 vLLM、SGLang 等引擎执行。

```text
HTTP 请求
  → 认证 / 限流与请求解析
  → ModelRoute：模型名、header 规则、目标及权重
  → ModelServer：实际模型、引擎类型、Pod selector、流量策略
  → 候选 Pod 过滤 → 调度插件评分 → 选择实例
  → 聚合式转发，或 PD connector 编排 P/D
  → 流式响应与在途计数更新

旁路控制信息：
  Kubernetes Watch → Controller → Pod / 路由对象快照
  引擎 metrics → Backend 适配 / Metrics Fetcher → 调度数据
```

ModelRoute 的目标权重适合版本或模型流量分配；Pod 评分处理同一目标内部的负载与缓存局部性。两层权重不是同一组参数。调度器需要先满足模型、角色、健康、LoRA 等硬条件，再比较性能分数，不能让高缓存分数覆盖不兼容条件。

## `prefix-cache` 的实际做法

当前源码中，`prefix-cache` 是轻量级历史路由索引。它将提取出的 prompt 字符串按固定**字节数**分块，初始 hash 包含模型名，每个后续 hash 包含上一个 hash 与本块内容，使用 xxHash 形成前缀链。

索引结构为 `model → prefix hash → pods`，并用 LRU 限制元数据量。Score 查找历史匹配的候选 Pod，按匹配块数占当前参与匹配块数的比例评分；PostSchedule 把本次前缀与选定 Pod 关联。源码默认分块为 64 字节、最多处理前 128 块、保留 top-K 匹配候选，但这些是配置默认值，不能视为 vLLM 的 token block 大小。

这个索引记录的是“此前把相似输入送到了哪里”。它没有证明 GPU 上的 KV 仍然存在：请求可能失败，缓存可能被淘汰，Pod 可能重启，聊天模板与 tokenizer 也可能产生不同的实际 token。若输入超过匹配上限，得分还只覆盖被检查的前缀，不能解释为完整 prompt 的缓存命中比例。

## `kvcache-aware` 的状态来源

当前主线还包含独立的 `kvcache-aware` 插件：token 级分块匹配，支持从 Redis 查询 runtime sidecar 写入的块映射，也支持从 KV 事件维护的内存索引评分。请求 tokenization、块 key 与引擎侧上报必须兼容。

| 维度 | `prefix-cache` | `kvcache-aware` 当前实现 |
|---|---|---|
| 匹配输入 | prompt 字节块 | token 块 |
| 状态来源 | 之前的路由决定 | runtime 映射或 KV 事件 |
| 索引存储 | Router 本地缓存 | Redis 或事件驱动内存索引 |
| 优点 | 部署简单，额外依赖少 | 更接近引擎实际缓存状态 |
| 代价 | 缓存淘汰后可能误判 | 分词、事件传递、索引更新与故障处理 |

因此不能笼统说“Kthena 的 prefix 插件一定实时查询 vLLM 的每一块 KV”，也不能因设计文档位于 proposal 目录就断言其功能尚未实现。判断依据是所部署版本的代码和实际启用配置。

## 负载和缓存怎样共同影响选址

前缀复用减少未命中的 prefill，排队则可能抵消节省。可以用一个设计层面的成本模型解释选择，注意这不是 Kthena 所有插件的统一源码公式：

\[
\widehat{T}_i = \widehat{W}_i + \widehat{C}_{prefill}(T-H_i) + \widehat{T}_{transfer,i}
\]

T 为输入 token 数，H_i 为实例 i 可用的连续前缀长度，W_i 为预计排队时间。比如 A 命中 90% 但排队 800 ms、剩余计算 50 ms；B 完全未命中但只需 300 ms prefill 且不用排队，B 的预计 TTFT 更低。所有数字是说明取舍的假设值。

真实系统可将 least-request、延迟、缓存等插件组合，并对分数归一化、设置权重。还要及时记录在途请求，否则连续多次选择会把流量集中到同一个看似空闲的 Pod。请求数相同也不代表负载相同，长 prompt 与长输出对资源占用不同。

## PD 分组和失败边界

ModelServer 的 `pdGroup.groupKey` 用标签值定义兼容分组，`prefillLabels`、`decodeLabels` 区分角色。普通调度路径先选 D，再在同组中选 P。分组有助于防止不兼容的 P/D 配对，但不能替代对模型版本、并行布局与连接器网络的校验。

生产排障应同时查看候选集为什么被过滤、各插件得分、最终选定实例、P/D 阶段耗时、引擎实际命中与错误。索引命中率高而引擎命中率低，首先检查索引陈旧、模板/tokenizer 不一致、块大小与配置、Pod 重建及模型版本。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：Kthena 收到请求后如何分发？</div>
<div class="qa-a"><p>先用 ModelRoute 做模型和流量规则匹配，再定位 ModelServer 及其候选 Pod。Router 从 watch 与引擎 metrics 维护状态，先过滤不可用或不兼容实例，再结合在途请求、延迟和缓存亲和评分。聚合部署直接转发；PD 部署还要选择兼容的 P/D 对并由 connector 串联两个阶段。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：前缀缓存匹配为什么不等于命中了真实 KV？</div>
<div class="qa-a"><p>轻量 prefix-cache 根据历史路由推测缓存位置，真实 KV 则由引擎分配和淘汰，两者不在同一状态机里。事件驱动索引能缩小偏差，但仍有传播时延。路由选择只影响性能，最终能否复用必须由引擎根据实际块和兼容性判断，不能因为路由分数高就跳过必要计算。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：Kthena、KTransformers 和 Volcano 是一类东西吗？</div>
<div class="qa-a"><p>Kthena 主要处理模型服务编排和请求路由；KTransformers 是推理执行与异构计算方向的框架；Volcano 主要做 Kubernetes 作业和资源调度。它们可以位于一条服务链路的不同层，不能仅因为名字相近就互换解释。</p></div>
</div>

来源：[Router 架构](https://kthena.volcano.sh/docs/architecture/kthena-router)、[prefix-cache 源码](https://github.com/volcano-sh/kthena/blob/45d12f13ebb31a88a04723fd82fa7be550633825/pkg/kthena-router/scheduler/plugins/prefix_cache.go)、[kvcache-aware 源码](https://github.com/volcano-sh/kthena/blob/45d12f13ebb31a88a04723fd82fa7be550633825/pkg/kthena-router/scheduler/plugins/kvcache_aware.go)、[PD 选址实现](https://github.com/volcano-sh/kthena/blob/45d12f13ebb31a88a04723fd82fa7be550633825/pkg/kthena-router/scheduler/scheduler_impl.go)。核对日期：2026-10-29；当前主线能力需与部署版本对应。
