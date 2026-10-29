## 多副本的 KV 复用有两条数据路径

每个 vLLM 副本有自己的缓存。单实例开启 APC，并不会让其他副本自动看到这些 KV。多副本复用可以把请求送到缓存所在实例，也可以把缓存搬到承担请求的实例。

| 机制 | 移动什么 | 主要状态 | 成本 |
|---|---|---|---|
| 缓存亲和路由 | HTTP 请求 | 前缀到实例的索引、实例负载 | 索引、选址及热点不均衡 |
| 跨实例 KV 共享 | KV 数据 | 内容 key、缓存层级、源/目标块、传输生命周期 | 网络、内存拷贝、兼容性与清理 |
| KV Offload | GPU 与 CPU/SSD 等层之间的 KV | 存储位置、预取和淘汰策略 | 容量收益与额外访问延迟 |
| PD 传输 | 同一请求 P 阶段产出的 KV | P/D 关联、源块保留与读取完成 | 阶段交接和在途状态 |

同一个服务可以组合四种机制，但开启其中一种不会自动拥有其他三种。语义缓存存储相似问题的答案，也不同于精确前缀 KV 复用。

## llm-d 的控制流与数据流

```text
客户端 → Gateway / L7 Proxy ──请求──→ 选定的引擎或 Routing Sidecar
                    │
                    └─ ext-proc → EPP：Filter → Score → Pick
                                      ↑
            Pod 发现、metrics、KV events、在途请求状态

KV 数据：引擎/缓存层 ←──── NIXL 等传输通路 ────→ 引擎/缓存层
```

InferencePool 通过 selector 关联模型服务端点与 EPP；EPP 决定后端，但通常不承担整条响应流的 L7 转发。PD 情况下，Routing Sidecar 负责把一次外部请求变成阶段间的请求序列。

## 近似索引与事件驱动索引

近似实现根据曾经发送的 prompt 前缀维护本地 LRU 索引，成本低，但不知道引擎后续的准确淘汰状态。精确匹配路径先取得模板渲染后的 token ID，再通过 KV 事件跟踪块的位置：

- `BlockStored`：某实例、某存储层出现了相应内容块。
- `BlockRemoved`：移除指定实例/层上的块位置。
- `AllBlocksCleared`：清空该实例对应的记录。

EPP 查询索引，计算候选实例持有的**连续可用前缀**。例如请求块为 `[B0,B1,B2,B3]`，A 有 B0、B1，B 只有 B2、B3，那么在普通前缀复用中 A 命中两块，B 命中零块。后半段内容相同不能替代前面的 attention 状态。

当前实现可通过短期 speculative indexing 在路由后先插入预测条目，弥补请求已路由、真实事件尚未到达的窗口；后续由事件确认或 TTL 过期清理。这是性能预测状态，不是 KV 已计算完成的证明。

多 EPP 副本可各自订阅所有模型 Pod 的事件，分别维护内存索引；也有外部 Redis/Valkey 后端。独立订阅避免每次查询依赖远端存储，但放大订阅数与元数据内存。事件传播、断连、重启和 speculative entries 都意味着索引是近实时视图；即使文档使用“precise”，也不能据此承诺任意时刻强一致或零误判。

## 缓存热点如何与负载均衡协调

强制将所有相同前缀发送到一个 Pod，可能把命中率做高却把队列压满。当前 llm-d 指南组合前缀亲和与 token 负载：优先留在缓存温暖的端点，超过校准的处理能力后扩展可选端点，再按待处理 token 负载选择。

路由关注的是未命中 token 的计算量、已有 decode 占用、KV 容量和目标延迟。可以用成本估计比较“在缓存实例等待”和“在另一个实例重算/拉取”；统一的固定权重只是实现方式之一。不同版本教程可能使用 `prefix-cache-scorer` 与 queue/KV 利用率评分，也可能使用 affinity filter 与 token-load scorer，应记录版本后再解释配置。

## 真正跨副本共享时多了什么

当前 llm-d 的实验性 P2P 指南利用 vLLM OffloadingConnector，从另一副本的 **CPU offload 层**通过 NIXL 拉取 KV。EPP 的精确索引用于找到源，source producer 决定是否值得搬运，sidecar 把远端源信息交给引擎。这条具体路线不能描述成“所有 GPU 直接共享同一块显存”。

成本比较至少包括：源端排队、CPU 内存读取、网络、目标 CPU/GPU 数据搬运和目标剩余 prefill。选择远端源需要同时满足模型及 KV 布局兼容、足够的可复用长度、源存活、缓存未被淘汰。指南要求一致的块大小、hash 相关配置和 TP 布局，并把该路径标为 experimental。

## 版本差异如何读

llm-d 的组件与配置名称持续演化。阅读旧教程时先记录其 llm-d、EPP/router、vLLM、Gateway API Inference Extension 版本，再定位对应配置。旧文章里的 `llm-d-inference-scheduler`、tokenizer sidecar、scorer 名称，不能直接与当前 `llm-d-router` 的目录和参数一一替换。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：vLLM 多副本如何复用 KV Cache？</div>
<div class="qa-a"><p>先在每个实例启用前缀复用，再由外层路由尽量把相同前缀送到已有缓存的副本。llm-d 的 EPP 可以根据历史路由近似判断，也可以用 tokenization 和 KV events 建立块位置索引，并结合负载选择。如果必须把请求放到别的实例，才需要额外的 KV 传输或共享缓存能力；索引本身不会搬运 KV。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：缓存命中率越高，性能一定越好吗？</div>
<div class="qa-a"><p>不一定。集中到一个副本会增加排队，远端命中还可能增加传输。应看端到端 TTFT、ITL 和 SLO goodput，并同时观察实际复用 token、未命中计算量、负载偏斜与传输字节。索引预测命中与引擎实际复用要分开统计。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：llm-d 与 Kthena 应该怎样比较？</div>
<div class="qa-a"><p>二者都覆盖模型服务的请求路由，均需结合缓存与负载。llm-d 在 Gateway/Proxy、EPP、Routing Sidecar 和引擎之间划分职责；Kthena 有 ModelRoute/ModelServer 和独立 Router，并通过插件与 connector 选址、串联 PD。比较应落到依赖、协议、状态源、引擎支持和运维成本，而不是仅比较一个“缓存感知”标签。</p></div>
</div>

来源：[llm-d 前缀路由](https://github.com/llm-d/llm-d/blob/361e1b7678ea228675b99ef7b8b5acfe7e295969/docs/architecture/kv-management/prefix-cache-aware-routing.md)、[KV 索引及事件](https://github.com/llm-d/llm-d/blob/361e1b7678ea228675b99ef7b8b5acfe7e295969/docs/architecture/kv-management/kv-indexer.md)、[当前精确路由部署指南](https://github.com/llm-d/llm-d/blob/361e1b7678ea228675b99ef7b8b5acfe7e295969/guides/precise-prefix-cache-routing/README.md)、[P2P 共享实验指南](https://github.com/llm-d/llm-d/blob/361e1b7678ea228675b99ef7b8b5acfe7e295969/guides/p2p-kv-cache-sharing/README.md)。核对日期：2026-10-29。
