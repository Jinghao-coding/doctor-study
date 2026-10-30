<div class="qa open speech">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: Crater CLI 有什么特点，为什么适合脚本和 Agent？</div>
<div class="qa-a">
<p>CLI 把平台操作接进用户的终端和自动化流程。用户可以管理登录上下文、查看资源和任务、创建开发或训练作业、传输文件、检查日志与事件、获取 SSH 访问方式，以及创建镜像快照或停止任务。命令通过 Crater API 使用当前身份，权限判断仍由平台执行。</p>
<p><strong>对 Agent 有价值的是稳定的输入输出约定。</strong><code>--json</code> 返回结构化结果，<code>--no-interactive</code> 关闭交互提示，分页字段让调用方继续获取后续记录。错误输出区分参数、平台接口、本地系统和取消操作，并对应分类退出码，调用方可以判断是修改参数、重新登录，还是处理本地环境问题。</p>
<p>例如 Agent 可以先查询任务，取得任务标识，再读取状态、Pod、事件和日志，判断当前是在排队、启动还是执行失败，随后给出定位结果或按用户指令继续操作。随 CLI 提供的 Skills 描述命令用法和操作流程，让 Agent 能复用这些平台能力。</p>
</div>
</div>

下面的查询使用示例任务名，执行时替换成平台实际返回的 <code>jobName</code>：

```bash
crater job ls --json --no-interactive
crater job get example-job --json --no-interactive
crater job pods example-job --json --no-interactive
crater job events example-job --json --no-interactive
crater job logs example-job --all-pods --all-containers --json --no-interactive
```

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 自定义调度具体加了什么？</div>
<div class="qa-a">
<p>普通作业提交时，平台先检查请求是否满足所覆盖的节点容量与约束，并检查单个作业自身是否超过配置的用户限额，然后直接创建 Volcano Job。Volcano 在调度会话中询问 Crater Extender，Crater 依次检查队内用户限额和超时等待保护，再让其他插件继续判断队列和设备是否可用。</p>
<p><strong>队内用户限额解决公共队列被单个用户占满的问题。</strong>例如一个共享队列总上限是八张 GPU，配置每用户最多两张。甲已有两张已准入的作业，再提交一张时，Crater 会暂时拒绝该作业准入；乙仍按自己的用量参与调度。这里的队列总上限和每用户限额是两层规则。</p>
<p><strong>超时等待保护解决资源反复被后续任务取走的问题。</strong>需要多张卡的任务可能长期无法凑齐资源。等待超过设定时间后，系统限制同队列、资源域兼容且显式节点范围有交集的后续候选准入。已经运行的任务可以继续执行，随后释放的资源有机会被等待任务使用。</p>
<p>实现通过可配置的 Extender 回调接入 Volcano。Crater 返回拒绝或弃权；弃权以后，Volcano 的其他插件继续检查。规则启用需要后端配置和 Volcano 回调配置共同生效。</p>
</div>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 等待保护会不会把整个集群挡住？</div>
<div class="qa-a">
<p>阻塞范围限制在同队列且可能竞争相同资源的位置。比如等待任务限定某一组 GPU 节点，另一任务明确只使用不相交的节点，就可以继续进入。资源类型是否兼容也参与判断。</p>
<p>超时任务还要具有可满足性：如果它本来就超过自己的用户限额，或者最小资源需求超过队列及祖先队列的容量上限，就不会获得阻塞后续任务的权利。对于尚未准入的多个超时任务，规则允许同样超时的候选继续参与判断，避免它们互相阻塞。</p>
<p>等待保护付出的代价是可能暂时减少后续小任务的准入，以换取大任务积累资源的机会。具体何时能够运行，仍由任务退出、实际可用设备和 Volcano 的调度决定。</p>
</div>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 并发提交时，怎么避免多个任务重复使用同一份额度？</div>
<div class="qa-a">
<p>Extender 根据缓存中的 Job、PodGroup 和 Queue 构造状态快照，把已准入且未结束作业的请求量计入用户用量。当前进程还维护一份准入预留账本：本轮候选通过 Crater 检查后，先暂记它的申请量，后续候选同时看到已有占用和这份暂记量。</p>
<p>重复检查同一个作业时会排除自身预留；观察到作业已准入、结束或消失后清理对应预留，超时清理作为兜底。这份账本管理用户额度，具体节点和 GPU 仍由 Volcano 分配。</p>
<p>预留账本保存在后端进程内，因此这套精确核算依赖单后端副本的部署条件。配置更新和多副本演进需要同时考虑账本的一致性。</p>
</div>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: 任务状态和资源使用为什么要分开核对？</div>
<div class="qa-a">
<p>提交成功表示集群对象已经创建；PodGroup 准入表示取得调度资格；之后还可能等待节点，容器启动后也可能继续下载模型或初始化服务。用户需要看到自己具体停在哪一步，平台也需要用正确状态计算额度和运行情况。</p>
<p>Crater 的 Reconciler 持续读取 Job 和 PodGroup 状态，更新业务记录并处理终态、通知与结算。监控与清理再结合实际任务和 GPU 指标识别持续低利用率占用，按配置筛选提醒与回收对象。发送停止或删除请求后，还要继续观察实际执行状态，确认资源释放。</p>
</div>
</div>

<div class="qa">
<div class="qa-q" onclick="this.parentElement.classList.toggle('open')">Q: Crater 的特色调度与 DeepShare、ElastiCo 有什么关系？</div>
<div class="qa-a">
<p>Crater 的常规作业路径使用 Volcano，并通过 Extender 实现队内用户限额和等待保护。DeepShare 研究保障兑现程度、预测排序与干扰感知共享，ElastiCo 研究训练和推理任务的配置弹性。平台提供真实的任务、设备和资源管理环境，各项研究围绕其中不同的调度问题展开。</p>
</div>
</div>

源码依据：[CLI 命令](https://github.com/raids-lab/crater/blob/2515bd9666a9dc278c266ebad7ef785e4f1a3d74/cli/cmd/job.go)、[结构化错误和退出码](https://github.com/raids-lab/crater/blob/2515bd9666a9dc278c266ebad7ef785e4f1a3d74/cli/pkg/errorcodes/codes.go)、[Extender 准入判断](https://github.com/raids-lab/crater/blob/2515bd9666a9dc278c266ebad7ef785e4f1a3d74/backend/pkg/extender/decision.go)、[准入预留账本](https://github.com/raids-lab/crater/blob/2515bd9666a9dc278c266ebad7ef785e4f1a3d74/backend/pkg/extender/accumulator.go)。
