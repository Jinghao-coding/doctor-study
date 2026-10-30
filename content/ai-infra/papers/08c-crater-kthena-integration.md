<div class="qa open speech">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: Kthena 怎样集成到 Crater，价值是什么？</div>
<div class="qa-a">
<p>这项集成把模型服务接进 Crater 的用户、模型权限、账户配额和运行管理。用户选择模型、vLLM 或 SGLang、部署拓扑和各角色资源后，Crater 做预检查，并把配置转换为 Kthena 原生的 ModelServing、ModelServer 和 ModelRoute。</p>
<p><strong>ModelServing 描述模型怎样运行。</strong>例如单节点推理只有合并角色；P/D 分离分别配置 Prefill 和 Decode；vLLM 多节点实例用 Entry 与 Worker 表达 Ray 运行结构。Kthena 据此管理服务组、角色与 Pod，通过 PodGroup 和 Volcano 调度到设备上。</p>
<p><strong>ModelServer 和 ModelRoute 把已经部署的实例接到请求入口。</strong>ModelServer 用标签发现属于该部署的入口 Pod，配置引擎、端口和 P/D 分组；ModelRoute 把用户调用的模型路由名指向 ModelServer。用户从 Crater 代理发起 OpenAI 兼容请求，代理先检查部署访问权限，再交给 Kthena Router，Router 选择后端实例，最后由 vLLM 或 SGLang 完成推理。</p>
<p>部署会进入相同的账户和用户队列，并参与平台的资源额度检查。平台进一步提供暂停、恢复、扩缩容、流式调用、会话、日志、诊断和计量。<strong>用户从选择模型到拿到服务入口，再到运行排障和停止释放，都能在同一套平台里完成。</strong></p>
</div>
</div>

<div class="table-scroll">
<table>
<thead><tr><th>对象或组件</th><th>回答的问题</th><th>Crater 接入的具体内容</th></tr></thead>
<tbody>
<tr><td>ModelServing</td><td>启动哪些角色、实例和节点？</td><td>角色拓扑、镜像与命令、模型挂载或下载、CPU/GPU/RDMA、队列和副本数。</td></tr>
<tr><td>ModelServer</td><td>哪些 Pod 是这个后端的服务入口？</td><td>部署标识与入口标签、引擎端口、P/D 角色和服务组匹配、KV connector。</td></tr>
<tr><td>ModelRoute</td><td>请求中的模型路由名对应哪个后端？</td><td>路由名和指向 ModelServer 的规则。</td></tr>
<tr><td>Volcano</td><td>这些服务 Pod 何时、在哪些节点运行？</td><td>账户/用户队列、PodGroup、成组资源需求和节点约束。</td></tr>
<tr><td>Kthena Router</td><td>这一条推理请求交给哪些实例？</td><td>读取模型路由和后端发现结果，处理普通或 P/D 请求转发。</td></tr>
<tr><td>vLLM / SGLang</td><td>实例内部怎样执行生成？</td><td>模型加载、实例内请求调度、批处理、KV 管理与计算。</td></tr>
</tbody>
</table>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 从点“创建部署”到收到回答，完整经过哪些步骤？</div>
<div class="qa-a">
<p>先检查当前用户、账户、模型目录或下载凭据的使用权限，再校验引擎与拓扑组合、镜像、模型版本、角色资源和队列状态。平台模型通过授权 PVC 目录只读挂载，外部模型通过初始化容器下载。分布式模型使用固定 revision，保证不同角色拿到同一版本。</p>
<p>随后按全部服务组、角色实例和 Entry/Worker 汇总资源，检查配额与等待条件。满足条件时创建 ModelServing，再以它的实际 UID 创建关联的 ModelServer 和 ModelRoute；后续删除和路由修复也按同一归属关系处理。</p>
<p>Kthena 根据 ModelServing 创建角色 Pod 和 PodGroup，沿 Volcano 队列进行资源调度。Pod 就位后准备模型、启动推理引擎；平台按期望的服务组、角色、实例和 Entry/Worker 检查完整就绪状态，提供分角色日志和诊断。</p>
<p>调用时，客户端把路由名放进请求的 <code>model</code> 字段。Crater 代理校验访问权限并补齐或校验路由名，再通过 Kubernetes Service proxy 转给 Kthena Router。Router 根据 ModelRoute 找到 ModelServer 及后端实例，返回结果后，代理把流式内容逐段传回客户端。</p>
</div>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 配额不足时，模型服务怎样等待？</div>
<div class="qa-a">
<p>集成代码按整套拓扑汇总资源：服务组数乘以各角色实例的 Entry 与 Worker 请求之和。部署自身超过用户队列限额时拒绝创建；只是当前累计用量不足以容纳它时，创建零服务组的 ModelServing，并在注解中保存期望服务组数。</p>
<p>Kthena Reconciler 周期性检查这些等待部署，在重新校验权限、配置、队列和配额后，恢复期望服务组数，随后由 Kthena 和 Volcano 推进执行。准入操作还通过用户与账户维度的锁协调，避免同一份额度同时被多个提交使用。</p>
<p>这里模型服务的等待通过零服务组和部署协调器表达。普通训练作业的 Extender 则在 Volcano 的准入回调中检查其 Job/PodGroup。它们都需要使用账户和用户队列，但对象和推进方式各有对应的实现。</p>
</div>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: P/D 分离里，请求和 KV 数据分别怎样走？</div>
<div class="qa-a">
<p>ModelServing 把 Prefill 和 Decode 表达为不同角色。ModelServer 的 <code>pdGroup</code> 使用服务组标签和角色标签，将同一组中的两个角色关联起来，Router 据此选择配套实例并推进请求。</p>
<p>Prefill 先处理输入并生成 KV 状态，Decode 在取得相应状态后继续逐 token 生成。Router 协调请求与所需的连接信息；KV 数据由引擎配套的 connector 和传输机制在实例间交换。集成对 vLLM P/D 配置 NixlConnector，并在 ModelServer 中设置 <code>kvConnector.type=nixl</code>；SGLang P/D 使用对应的 Mooncake 运行配置。</p>
<p>因此需要一起校验模型 revision、镜像、tokenizer/KV 类型和 connector 契约。跨节点角色还要配好网络与 RDMA 等资源；只创建两组不同名称的 Pod，无法完成这条执行流程。</p>
</div>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 暂停、缩容和删除时，资源怎样正确释放？</div>
<div class="qa-a">
<p>暂停会保存期望服务组数并把实际组数降为零，恢复时重新检查配置和配额。缩容或删除后，Pod 可能仍在终止；资源核算继续保留这些 Pod 的占用，直到实际退出。这样，平台不会在旧进程还占着 GPU 时，就把同一份额度再次发出去。</p>
<p>ModelServer 和 ModelRoute 由真实 ModelServing UID 关联，删除根对象后通过所有者关系清理。创建过程中若关联资源失败，回滚只删除本次新建对象。Reconciler 还会修复与该部署对应的路由资源。</p>
<p>计费以 Pod 资源请求和占用时长为基础；Router 与引擎分别提供请求、错误、延迟和 token 指标。P/D 的总体生成 token 吞吐取 Decode，避免把两个阶段重复相加。</p>
</div>
</div>

集成实现依据：[PR #495](https://github.com/raids-lab/crater/pull/495)、[原生对象构造（041677c6）](https://github.com/Jinghao-coding/crater/blob/041677c678cc753eb44559f37a6ec80a8066d002/backend/internal/handler/inference_native_builder.go)、[准入与等待](https://github.com/Jinghao-coding/crater/blob/041677c678cc753eb44559f37a6ec80a8066d002/backend/internal/handler/inference_admission.go)、[代理调用](https://github.com/Jinghao-coding/crater/blob/041677c678cc753eb44559f37a6ec80a8066d002/backend/internal/handler/inference_proxy.go)。Router 的对象与 P/D 路由机制参见 [Kthena 官方路由文档](https://kthena.volcano.sh/docs/user-guide/router-routing)。
