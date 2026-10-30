<div class="qa open speech">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 请完整介绍一下 Crater，有哪些平台特点？</div>
<div class="qa-a">
<p>Crater 是一个面向多团队共享异构算力的云原生 AI 训练与推理平台。场景是实验室或科研机构里，不同团队共用多种 GPU 和加速卡，用户既要开发调试、跑训练，也要部署模型服务。<strong>平台把设备、运行环境、模型和数据、团队配额，以及任务执行和监控连在一起，让用户能完成一整条研发流程。</strong></p>
<p>比如一个用户要微调模型，可以先通过 Web 或 CLI 选择镜像和 GPU，挂载模型与数据，启动 Jupyter 或 WebIDE，也可以通过 SSH 接入开发环境。代码和环境准备好后，再提交单机或分布式训练。训练产出的文件保存在挂载的存储里，后续作业可以继续使用，也可以把合适的模型目录登记成平台模型，再部署推理服务。镜像、模型和数据能够按权限复用，用户可以沿用已经准备好的环境和资产。</p>
<p><strong>一个特点是把不同设备和不同任务放进同一套资源管理流程。</strong>平台按设备类型和节点条件表达资源需求，配套选择镜像、启动参数和挂载；开发任务、训练作业和模型服务都关联到用户、账户、队列与配额。管理员既能控制团队可以用多少资源，也能查看资源分给了哪些任务、实际运行情况怎样。</p>
<p><strong>第二个特点是同时面向人、脚本和 Agent 提供操作入口。</strong>Web 适合查看资源和交互配置，CLI 可以创建任务、管理文件、查看状态和日志、获取 SSH 访问方式，以及停止任务。CLI 提供结构化 JSON 输出、非交互模式和分类错误码，脚本或 Agent 可以据此判断提交是否成功、任务是否开始运行，再决定下一步操作。这样，本地开发、远程实验和运行排障能够使用同一套平台能力。</p>
<p><strong>调度方面，我们在 Volcano 上接入了共享集群需要的定制规则。</strong>一类是同队列内的用户限额，避免某个用户把公共队列全部占满；另一类是等待保护。比如一个需要四张卡的任务一直在等，后来的单卡任务却不断进入，空出来的资源始终凑不齐。等待超过设定时间后，平台会限制同队列里竞争相同资源的新任务准入，让已有任务结束后释放的资源有机会积累。这个规则还会比较资源类型和节点范围，其他资源上的任务可以继续推进。</p>
<p><strong>模型服务方面，我们集成 Kthena，把模型部署和请求访问接起来。</strong>用户选择授权模型、vLLM 或 SGLang，配置单节点或 Prefill/Decode 分离拓扑；vLLM 还可以通过 Ray 组织多节点实例。Crater 检查权限与资源需求，生成 Kthena 的原生部署和路由对象；服务 Pod 通过 Volcano 进入对应账户队列，运行后由 Kthena Router 把推理请求送到后端实例。平台提供调用入口、流式响应、按角色查看的日志与诊断，以及暂停、恢复和扩缩容管理。</p>
<p>运行管理还会关联任务状态、GPU 指标和用户信息，按配置识别持续低利用率占用，进行提醒和回收。对模型服务，还需要区分资源已经分配、容器已经启动和服务真正就绪。<strong>Crater 的价值，是把资源申请、环境准备、调度执行、模型服务访问，以及监控和释放做成用户能够直接使用的完整平台。</strong></p>
<p>平台采用 Apache-2.0 开源，已在之江实验室、启元实验室等科研机构部署应用。在北航实验室的部署统计中，纳管 GPU 超过 250 张，日均调度任务超过 200 个。</p>
</div>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 平台架构如何分工？</div>
<div class="qa-a">
<p>从用户入口往下看，Web 和 CLI 调用 Crater API，后端处理身份、账户、配额、镜像与数据权限，把用户配置转换成具体的集群对象。普通训练和开发作业提交为 Volcano Job；模型服务用 ModelServing 表达角色和副本拓扑，用 ModelServer 与 ModelRoute 接上请求路由。</p>
<p>Volcano 负责队列、成组准入和节点资源分配，Kubernetes 控制器、kubelet 与容器运行时负责对象生命周期和容器执行。Crater 的状态协调与监控组件持续读取实际状态，更新平台展示、诊断、计量与清理结果。Kthena Router 处理已经运行起来的推理实例之间的请求分发，vLLM/SGLang 在实例内部执行模型推理。</p>
<div class="table-scroll">
<table>
<thead><tr><th>层次</th><th>主要对象</th><th>具体职责</th></tr></thead>
<tbody>
<tr><td>用户入口</td><td>Web、CLI、HTTP API</td><td>提交配置、查询状态、访问环境与服务、接入脚本和 Agent。</td></tr>
<tr><td>Crater 控制层</td><td>用户、账户、队列、模型、镜像、任务记录</td><td>权限与配额、部署转换、定制准入、状态协调与运行治理。</td></tr>
<tr><td>工作负载与资源调度</td><td>Volcano Job、PodGroup、ModelServing、Pod</td><td>生命周期、角色拓扑、成组调度和节点放置。</td></tr>
<tr><td>推理请求与模型执行</td><td>ModelRoute、ModelServer、Router、vLLM/SGLang</td><td>模型名路由、后端发现、请求分发、实例内批处理和生成。</td></tr>
</tbody>
</table>
</div>
</div>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 开发、训练和推理怎样复用环境与数据？</div>
<div class="qa-a">
<p>用户在开发环境中调试代码，把代码、数据和训练产物保存在挂载存储中；需要保留环境时，可以创建镜像快照。后续训练作业使用对应镜像和挂载路径，模型服务也可以只读挂载已授权的模型目录。它们是分别提交和管理的工作负载，通过镜像、文件与模型资产衔接。</p>
<p>例如训练任务结束后，模型文件仍保存在共享存储中；登记模型目录后，部署服务时可以选择它并挂载。平台维护文件与模型权限，任务结束时释放计算资源，数据是否保留由存储与资产操作决定。</p>
</div>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 你在 Crater 中具体承担什么工作？</div>
<div class="qa-a">
<p>我是 Crater 的创建者、项目负责人和维护者，主导平台架构与核心功能研发。我的主要工作围绕共享算力的使用和治理展开，包括异构设备与运行环境管理、任务与队列配额、启动前检查和等待保护、运行状态与实际占用核对，以及面向用户和 Agent 的平台入口。</p>
<p>工程难点集中在跨组件的状态与决策。例如定制准入需要同时处理队列总量、用户限额、同一轮多个候选的临时记账和超时任务的阻塞范围；模型部署则要把权限、拓扑、配额、运行就绪和调用路由串起来。这些都是平台能否正确交付资源和服务的关键。</p>
</div>
</div>

源码依据：[Crater main（2515bd96）](https://github.com/raids-lab/crater/tree/2515bd9666a9dc278c266ebad7ef785e4f1a3d74)、[Kthena 集成代码](https://github.com/raids-lab/crater/pull/495)。部署规模采用 2026-10-21 项目材料中的统计。
