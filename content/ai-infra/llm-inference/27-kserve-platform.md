## 从模型声明到可访问服务

模型上线平台接收模型位置、镜像或 Runtime、资源规格和服务策略，持续把这些期望转化为运行中的实例。KServe 的 `InferenceService` 路径提供这一层声明式管理；vLLM 在实例内部执行推理。以 Standard 模式为例：

```text
InferenceService + ServingRuntime
          ↓ 校验、默认值、调谐
Deployment + Service + 网络路由 + 扩缩容配置
          ↓
Pod → 模型文件准备 → 引擎加载 → Readiness → 接入流量

在线请求：客户端 → Gateway/路由 → Service 后端 → vLLM
```

Controller 负责协调 Kubernetes 对象；每次推理请求不会先经过 Controller。Standard 模式可使用 Gateway API；其他部署模式生成的对象和数据路径会变化。当前 KServe 另有面向高级 LLM 服务的 `LLMInferenceService`，不能把它与普通 `InferenceService` 的控制链混为一谈。[KServe 控制面](https://kserve.github.io/website/docs/concepts/architecture/control-plane)

## Runtime 模板与模型配置

`ServingRuntime` 描述命名空间内的模型服务容器模板，`ClusterServingRuntime` 提供集群级模板。模板包含镜像、启动参数、支持的模型格式等；`InferenceService` 提供具体模型与资源需求。显式指定 Runtime 或按支持格式自动选择，都必须满足兼容条件。运行时模板存在，不代表所用镜像一定支持新模型的架构、量化格式和算子。[ServingRuntime](https://kserve.github.io/website/docs/concepts/resources/servingruntime)

平台设计中，版本应覆盖模型 revision、tokenizer/chat template、镜像 digest、引擎参数和硬件规格。这样扩容出的实例才与旧实例可比较，回滚也能恢复到明确配置。模型文件下载、权重加载、内核预热和可服务状态应分别暴露，避免把 Pod Running 当成模型 Ready。

## 共享 GPU 的控制链

作者的 KServe 0.18 与 HAMi-DRA 0.2.1 示例采用原生 Claim：Predictor 引用 `ResourceClaimTemplate`，每个 Pod 获得自己的 Claim。调度器依据设备信息完成分配，节点侧驱动准备设备，容器运行时应用 CDI 配置，HAMi 的运行时能力落实相应限制。示例还显式选择 GPU 镜像，避免原生 DRA 不填写传统 GPU limit 时选错镜像。[KServe 与 HAMi 实例](https://www.lixueduan.com/posts/ai/24-kserve-p3-hami/)

```text
副本期望数 = 2
  ├─ Pod A → Claim A → 设备上的分配 A
  └─ Pod B → Claim B → 设备上的分配 B
```

两份 Claim 可以分到同一物理 GPU，但共享方式、可分容量和运行时限制由设备驱动及功能配置决定。独立副本不应仅为省事就共用固定 Claim；能否共享一份分配，需要显式确认驱动语义、访问范围和资源核算。HAMi 软件节流也不能直接解释成专属物理 SM。

## 发布失败如何定位

| 现象 | 首先定位的状态 | 下一步 |
|---|---|---|
| 提交即拒绝 | schema、Webhook、Runtime 匹配 | 修正字段、格式或版本 |
| Deployment 存在，Pod Pending | quota、节点条件、GPU/Claim 分配、PVC | 区分额度与物理资源不足 |
| Pod 启动后反复退出 | 模型路径、镜像依赖、显存预算、启动日志 | 复核权重与 KV 预算 |
| Pod Running，服务未 Ready | 模型加载及健康探针 | 等待预热或修复探针与模型加载 |
| Ready 却访问失败 | Gateway、HTTPRoute、Service、EndpointSlice | 检查路由匹配、端口及后端状态 |
| 扩副本后延迟更高 | 新副本缓存、负载分配、共卡争用 | 区分冷启动与资源竞争 |

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：Deployment 已经能跑 vLLM，为什么还需要 KServe？</div>
<div class="qa-a"><p>单个 Deployment 能运行引擎；服务增多以后，模型下载、Runtime 选择、资源配置、路由、健康状态和扩缩容容易出现不同约定。KServe 用声明和控制器统一这些流程。平台收益来自一致的生命周期与运维接口，是否采用它取决于已有平台能力和集成成本。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：用户上传镜像和模型后，平台怎样判断上线完成？</div>
<div class="qa-a"><p>先完成配置和资源校验，再生成工作负载与路由；观测设备分配、文件准备、模型加载和实例 Ready，最后确认入口真实请求成功。状态中记录当前配置版本与失败原因。只看到对象创建成功，或容器进入 Running，都不足以判定模型已经能服务。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：平台 Controller、GPU 调度器和请求 Router 怎样分工？</div>
<div class="qa-a"><p>Controller 管服务期望和子资源生命周期；队列与设备调度决定工作负载何时放行、运行在哪个节点及设备；Router 根据模型、缓存和负载把每条请求送到实例。它们使用的状态和决策频率不同，应通过明确的资源状态、Ready 端点和运行指标衔接。</p></div>
</div>

核对日期：2026-10-29。官方页面当前为 KServe 0.20；所引作者示例使用 0.18，配置字段应按部署版本校验。
