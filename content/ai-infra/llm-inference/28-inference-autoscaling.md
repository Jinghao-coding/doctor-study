## 指标驱动的扩缩容闭环

推理实例的显存包含常驻权重、运行空间和 KV Cache。即使请求很少，显存也可能接近预分配上限；GPU 利用率达到高值后，也未必能区分一个请求与大量积压。扩缩容应观察待处理工作量，并用 TTFT、ITL 和吞吐验证效果。

KServe 的 KEDA 示例采用以下路径；官方示例使用 Standard 部署配置，文档也将这一路径称为 Raw 模式：[KServe KEDA 集成](https://kserve.github.io/website/docs/model-serving/predictive-inference/autoscaling/keda-autoscaler)

```text
vLLM /metrics → Prometheus → KEDA metrics-apiserver
                                     ↓ external metrics
InferenceService → ScaledObject → HPA → Deployment 副本数
                                         ↓
                 资源分配 → 加载模型 → Ready → 实际吞吐
                                         ↓
                              队列、TTFT、ITL 反馈
```

HPA 本身支持自定义指标和外部指标。KEDA 提供事件源适配、指标服务和 HPA 生命周期管理；在其典型 Deployment 路径中，0↔1 由 KEDA Operator 处理，1↔N 由 HPA 处理。只有 CPU/内存指标时，缩到零后没有运行实例可供观测，无法据此触发唤醒。[KEDA 架构](https://keda.sh/docs/2.21/concepts/)

## 请求数指标怎样解释

| 指标 | 对象、单位与窗口 | 适用判断 | 容易误判的情况 |
|---|---|---|---|
| running requests | 每引擎当前执行请求数，条，瞬时 gauge | 当前并发 | 长短请求成本差异大 |
| waiting requests | 每引擎等待请求数，条，瞬时 gauge | 引擎内部积压 | 看不到入口尚未转发的请求 |
| 待处理 token | 请求估算的剩余工作量，token | 比请求数更细的负载估计 | 输出长度未知、缓存命中会改变工作量 |
| TTFT | 发起请求到首 token，ms，窗口内分位数 | 首响应 SLO | 包含排队、网络、预处理与计算，需分解 |
| ITL | 相邻输出 token 的间隔，ms，窗口内分位数 | 流式输出是否稳定 | 按请求平均可能隐藏局部长停顿 |
| SLO goodput | 窗口内满足约束的完成请求数/时间，请求/s | 扩容是否带来有效收益 | SLO 与负载分布变化会改变可比性 |

作者的功能 Demo 聚合所有 Predictor Pod 的 `running + waiting`，以每副本目标请求数驱动 1→2→1。它通过 ServiceMonitor 发现各 Pod 端点，避免反复随机采集 Service 后面的某一个实例。[作者扩缩容实战](https://www.lixueduan.com/posts/ai/26-kserve-p4-keda/)

若配置对应的目标语义是每副本平均承载 q 条，聚合值为 Q，忽略容差和稳定窗口时，可用 `ceil(Q / q)` 理解期望副本数。例如 Q=12、q=4，对应 3 个副本。这里的数值是解释性例子。必须核对 HPA 中实际生成的指标类型，不能把总量与单 Pod 平均量混用后再乘一次副本数。[HPA 算法](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)

## 如何校准扩容规则

以下是设计与验证方案，阈值应由实际模型和硬件测得：

1. 固定模型、精度、输入输出长度分布和 SLO，测每个热副本的可承载区间。
2. 同时观察入口队列和引擎队列，区分 Router 限流与引擎处理不足。
3. 把 Pending、Loading、Ready 副本分别计数。已申请的新实例还未 Ready 时，不应把其全部处理能力计入已供给容量。
4. 配置最大副本数、扩容速率及缩容稳定窗口；指标采集失败时保留故障信号，不把缺失值当成零流量。
5. 缩容先减少新流量，再排空在途请求，最后释放实例。流式连接、会话状态和 KV 生命周期需要明确处理。

冷启动应拆成：等待可调度资源、模型下载或挂载、权重加载、引擎编译/预热和健康检测。缓存感知路由也会影响扩容：新副本没有热前缀，若 Router 永远偏向老副本，新容量可能一直空闲。可以通过负载上限、有限的冷副本流量和后台预热逐步建立缓存。

## PD 分离后的容量判断

P 和 D 的需求应分别估计。P 池关注未命中输入 token、排队与 prefill 时间；D 池关注活跃序列、输出速率、ITL 和 KV 容量。单独扩 P 可能把 D 压满，扩 D 也不会消除 P 的长队列。还应计入 KV 传输带宽与在途占用，再用端到端 SLO 校验。

缩到零还需要独立于推理 Pod 的唤醒信号，例如持久队列或入口侧指标。Kubernetes 的原生缩零能力在不同版本与 feature gate 下有变化；即使控制器支持零副本，也仍需解决请求暂存、唤醒和模型加载延迟。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：为什么不直接按显存使用率扩容？</div>
<div class="qa-a"><p>权重和 KV 池可能常驻或预分配，显存占用不能直接代表请求积压。我会先用请求或 token 工作量表达需求，再结合排队时间、TTFT 和 ITL 判断容量是否不足。显存仍用于约束 KV 容量和识别 OOM 风险。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：KEDA 替代了 HPA 吗？</div>
<div class="qa-a"><p>KEDA 与 HPA 协作。它适配事件源、提供外部指标并管理 HPA；典型模式下自己处理 0↔1，HPA 处理 1↔N。HPA 原本就支持外部指标，选择 KEDA 的理由是复用成熟的事件源和扩缩容集成。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：副本加倍后吞吐为什么没加倍？</div>
<div class="qa-a"><p>先确认新增实例真的 Ready 且收到流量，再检查是否共用同一张 GPU、同一网络或存储瓶颈。之后分解冷启动和冷缓存代价，检查 Router 是否仍把流量集中到旧副本。扩副本只有增加有效容量，才可能提高满足 SLO 的吞吐。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：模型服务缩容怎样尽量保持健康？</div>
<div class="qa-a"><p>先确认剩余热容量能承载流量，再让目标实例停止接新请求并排空在途连接。若涉及迁移，先在目标准备资源、加载模型并验证健康，再切流和释放来源。没有冗余容量且来源必须立即退出时，无法承诺零中断，需要排队、限流或明确降级。</p></div>
</div>

核对日期：2026-10-29。公式与容量规划是解释性分析；本文未报告 GPU 实测结果。
