## PD 分离中的三项职责

一次请求的 Prefill 和 Decode 可以在不同实例上执行。Prefill 处理输入并产生 KV；Decode 使用这些状态逐 token 生成。端到端流程由请求级编排组件串联，KV 的搬运交给引擎 Connector 和传输后端，各实例的内部 Scheduler 继续负责自己的计算队列。

| 职责 | 典型组件 | 维护的状态 |
|---|---|---|
| 选择 P/D，衔接请求和响应 | Router、Proxy 或 Routing Sidecar | 请求 ID、目标实例、阶段、截止时间、重试状态 |
| 管理 KV 的可读性、读取和释放 | 引擎 KV Connector | 源块/目标块、传输描述、异步完成、引用或租约 |
| 执行本地模型计算 | vLLM Scheduler、KVCacheManager、Worker | token 预算、块表、本地等待和运行请求 |

Kubernetes 调度器负责部署 P/D Pod，并不逐请求发起 Prefill 后再调用 Decode。

## vLLM NIXL 的典型拉取链路

```text
客户端 → 请求编排组件：原始 prompt、生成参数
编排组件 → P：预填充请求，附远端 decode 所需控制信息
P：排队、分配 KV、计算 prompt，保留输出块
P → 编排组件：KV 传输元数据
编排组件 → D：请求 + KV 传输元数据
D Connector：分配目标空间，通过 NIXL 从 P 读取 KV
D：确认所需状态可用后进入生成，流式返回
完成 / 取消 / 超时 → 双端解除引用、回收请求与传输资源
```

常见接口会把发给 P 的请求限制为 `max_tokens=1`，并用 `kv_transfer_params` 衔接 D。具体首 token 的衔接由代理与连接器协议处理，不能直接把 P 的一次输出和 D 的完整输出拼接。HTTP 控制链路上传递的是定位和协调信息，KV 张量通常走引擎间的数据通路。

当前 NixlConnector 的 prefiller 租约会保留块等待 D 读取；D 排队期间可通过心跳延长租约；没有心跳或读取通知且租约到期时释放。这个机制解决的是跨阶段资源生命周期，不能用一个普通 HTTP 超时完全替代。

## llm-d 与 Kthena 怎样实现编排

**llm-d**：Gateway/Proxy 咨询 EPP，EPP 的 PD profile 先选择 D，并由 decider 判断是否需要远端 P；需要时再选择 P。代理将请求交给 D Pod 前的 Routing Sidecar，sidecar 调 P、接收 KV 元数据，再交给本地 D。vLLM 在适当配置下可以走 D-only；不能把这种回退能力套到所有引擎。

**Kthena**：ModelRoute 定位 ModelServer；`pdGroup` 描述 P/D 角色与分组。当前 Router 的 scheduler 普通评分路径先选 D，再从同组候选选 P。Router 中的 NIXL HTTP connector 负责先请求 P，再把响应中的 `kv_transfer_params` 填入 D 请求。它与 vLLM 内部同名技术栈中的 KV Connector 位于不同层。

两者都可能先确定 D 的位置，再执行 P 的计算。**选址顺序与计算依赖顺序可以不同。**先选 D 有利于考虑 decode 的容量、已有前缀和最终输出负载，再为它选择合适的 P。

## 为什么分离，以及何时不划算

Prefill 与 Decode 的资源需求、批处理方式和延迟目标不同。分离后可独立选择并行配置、扩缩容和控制 prefill 对 decode 迭代的干扰。代价包括模型副本、网络传输、跨阶段排队、预留 KV 和故障处理。

可用下面的简化分解判断 TTFT 来源，各项需要使用不重叠的测量边界：

\[
TTFT \approx T_{入口}+W_P+C_P+T_{KV}+W_D+C_{首个输出}
\]

传输可能与部分计算重叠，因此真实端到端耗时应从 trace 观察关键路径，不能直接相加所有 span。假设实际需要搬运 1 GiB KV、有效链路吞吐为 25 GB/s，仅数据传输下界约 43 ms，还没有计算握手、内存拷贝、排队和布局转换。短 prompt、小流量或慢网络中，这个额外成本可能超过收益。

PD 的目标常是改善尾部 ITL 或满足更多请求的 SLO；不能承诺任何负载下总吞吐都会提高。先用聚合实例和 Chunked Prefill 建立基线，再验证分离收益。

## 阶段失败的处理

| 失败点 | 应观察什么 | 处理原则 |
|---|---|---|
| P 未完成 | P 错误、请求截止时间、存活实例 | 在预算内重新选择或走已验证的本地 prefill 回退 |
| P 完成但 D 排队 | 源 KV 持有量、租约、D 队列 | 限制在途预填充，避免源 KV 占满；延续或终止租约 |
| KV 传输失败 | 块缺失、兼容性、网络错误 | 由支持的恢复路径重算/重传，禁止使用未完成 KV |
| 流式输出已经开始 | 已输出 token 数、断连时间 | 不透明重试整条请求；显式失败或使用专门续传协议 |
| 客户端取消 | 两阶段请求和传输是否退出 | 传播取消，清理引用；以租约兜底泄漏 |

跨实例传输需核对模型权重版本、KV dtype、块大小、attention 后端以及 TP/PP 布局。不同并行度能否互通取决于连接器的具体支持，不能仅凭模型名字相同认定可用。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：请求先去 P 再去 D，中间究竟是谁调度？</div>
<div class="qa-a"><p>请求级 Router 或代理负责选 P/D 和串联 RPC；vLLM Connector 负责 KV 数据传输，各实例内部 Scheduler 负责本地执行。以 llm-d 为例，EPP 做选址，D 前的 routing sidecar 先调 P，取得 KV 元数据后调用 D，D 再通过 NIXL 读取 P 的 KV 并开始生成。P 侧在读取完成或租约到期后释放对应资源。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：多轮对话的 KV 在 D 上，下一轮为什么可能还要传回 P？</div>
<div class="qa-a"><p>D 拥有前一轮生成 token 对应的 KV，而 P 可能只保留了旧输入。下一轮完整上下文包含这些生成内容。如果只固定单向 P→D，P 仍可能重算一段已有历史。双向 KV 或跨副本共享可让 P 拉取已有历史，再计算新增后缀。是否值得取决于可复用长度、缓存保留时间和传输成本；需要会话元数据和有效的块生命周期。</p></div>
</div>

来源：[vLLM NIXL 使用与租约](https://github.com/vllm-project/vllm/blob/cf3f6405b849f2b672d93af0c4cf4e5e6dc6bd1b/docs/features/nixl_connector_usage.md)、[llm-d PD 编排](https://github.com/llm-d/llm-d/blob/361e1b7678ea228675b99ef7b8b5acfe7e295969/docs/architecture/disaggregation/pd-disaggregation.md)、[Kthena NIXL 代理实现](https://github.com/volcano-sh/kthena/blob/45d12f13ebb31a88a04723fd82fa7be550633825/pkg/kthena-router/connectors/nixl.go)。核对日期：2026-10-29。
