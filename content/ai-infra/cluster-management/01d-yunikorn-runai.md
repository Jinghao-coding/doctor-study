<div class="card card-s">
<h3>YuniKorn：层级队列和 Application 级调度</h3>
<p>YuniKorn 源自 YARN 的资源管理思想，核心优势是层级队列。它适合公司 / 部门 / 团队 / 项目多层资源治理场景。</p>
<table>
<tr><th>能力</th><th>说明</th><th>适用场景</th></tr>
<tr><td>层级队列</td><td>root → department → team → project</td><td>大型组织资源治理</td></tr>
<tr><td>Application 级调度</td><td>一组 Pod 作为一个应用管理</td><td>Spark、Flink、训练任务</td></tr>
<tr><td>替换调度器</td><td>可以作为完整 scheduler 运行</td><td>需要强资源管理能力的集群</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Run:ai：商业 GPU 共享和配额平台</h3>
<p>Run:ai 提供 GPU 分时共享、配额、项目级资源治理、可视化和成本归因。它的优势是开箱即用，适合想快速落地 GPU 平台能力的团队。</p>
<table>
<tr><th>能力</th><th>价值</th><th>局限</th></tr>
<tr><td>GPU sharing</td><td>提高 Notebook、小实验、推理任务利用率</td><td>闭源实现，深度定制受限</td></tr>
<tr><td>Quota / borrowing</td><td>项目级配额和空闲借用</td><td>策略能力取决于产品版本</td></tr>
<tr><td>可视化</td><td>降低平台运维门槛</td><td>大规模特殊需求可能仍需自研</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: YuniKorn 的层级队列有什么优势？</div>
<div class="qa-a"><p>层级队列把组织结构映射到资源治理：公司给部门配额，部门给团队配额，团队之间可以按规则借用和回收。扁平队列在团队少时够用，但组织层级多后很难维护公平和预算边界。</p></div>
</div>
