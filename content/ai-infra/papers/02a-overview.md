<div class="card card-s" style="margin-top:0.8rem">
<p><strong>📄 论文原文：</strong><a href="../../../resources/papers/cluster_2026_Deepshare.pdf" target="_blank">IEEE Cluster 2026 — DeepShare PDF</a></p>
</div>

<div class="card card-d">
<h3>问题背景</h3>
<p>多团队共享 GPU 集群的核心矛盾：</p>
<ul>
<li><strong>配额闲置</strong>：某个团队暂时没有训练任务时 GPU 空转浪费，实测集群平均利用率只有 40%。</li>
<li><strong>配额不够</strong>：另一个团队赶 deadline 想多用几块卡，却因超配额被拒。</li>
</ul>
<p>固定配额简单但浪费严重，完全共享利用率高但无法保障 SLA。问题本质：<strong>在保障每个租户配额的前提下，把闲置资源借给需要的人，原主需要时及时收回。</strong></p>
<p>额外问题：即使 GPU 被分配出去了，很多训练任务在 I/O 或 CPU 预处理阶段 GPU 是空闲的。两个任务合用同一块 GPU 可以提升利用率，但会互相干扰——抢占 SM 和显存带宽，搞不好两个任务都变慢。</p>
</div>

<div class="card card-d">
<h3>系统设计</h3>
<p>统一控制信号——<span class="hl">配额保障度 QAD</span>，同时驱动三个子系统：</p>
<div class="formula">$$Q_i(t)=\frac{A_i^G(t)}{\min\!\left(q_i,\,D_i^G(t)\right)}\quad\left(D_i^G(t)>0\right)$$</div>
<table>
<thead><tr><th>部分</th><th>含义</th><th>记忆</th></tr></thead>
<tbody>
<tr><td>分子 <code>A_i^G(t)</code></td><td>已经分配给租户的 Guaranteed GPU</td><td>已经兑现多少</td></tr>
<tr><td>分母 <code>min(q_i,D_i^G(t))</code></td><td>quota 与当前 Guaranteed demand 取小</td><td>此刻应该兑现多少</td></tr>
<tr><td>比值 <code>Q_i(t)</code></td><td>当前保障兑现率</td><td>已给 / 该给</td></tr>
</tbody>
</table>
<p><strong>边界：</strong>没有 Guaranteed demand 时 <code>Q_i(t)=1</code>；Best-effort 借用不计入分子，所以 QAD 位于 <code>[0,1]</code>，不会因为借卡大于 1。</p>

<div class="comp">
<div class="comp-t">子系统一：弹性配额借用（DRA）</div>
<p>空闲 GPU 可被其他租户借走跑低优先级任务。保障需求恢复时，先按 QAD 排序尝试放置；仍无法放置才回收机会型任务。资源交付还取决于可行设备和任务退出时间。</p>
</div>

<div class="comp">
<div class="comp-t">子系统二：预测性调度</div>
<p>Per-tenant gradient boosting regressor 预测作业剩余运行时间（MAPE 31.84%，R² = 0.7286）。调度排序采用词典序：</p>
<div class="formula">$$\big(\tilde{Q}_i(t)\uparrow,\; \hat{T}(j)\uparrow\big)$$</div>
<p>先按 QAD 升序（优先欠缺的租户），再按预测运行时间升序（短作业优先）。</p>
<p>抢占对象选择：对候选 GPU 上全部 Best-effort 任务计算集合代价，选择最小者。</p>
<div class="formula">$$\Phi(J)=\sum_{j\in J}\frac{1+\alpha C_p(j)}{\hat T(j)}+\frac{\beta(|J|-1)}{\bar T(J)}$$</div>
<p>剩余时间越短、累计抢占开销越高，代价越高；第二项额外惩罚同时中断多个任务。候选设备必须在清退全部驻留任务后满足新任务的资源约束。</p>
</div>

<div class="comp">
<div class="comp-t">子系统三：干扰感知 GPU 合用</div>
<p>Random Forest 预测两个任务共享同一块 GPU 时的性能保持率（R² = 0.902）。特征来自硬件计数器（SM activity、memory bandwidth），用于估计共置后的吞吐变化。只有双方预测保持率都达到动态门槛时才允许合用。运行时根据硬件指标估计保持率，连续三个窗口低于门槛，下一周期回收机会型伙伴。</p>
</div>

<p>整个系统实现为 <strong>Kubernetes scheduler plugin</strong>，覆盖 Filter、Score、Reserve、PostFilter、Permit 五个扩展点（无可行节点时才进入 PostFilter 抢占分支），端到端调度延迟 &lt; 50ms。</p>

<h3>核心结果</h3>
<div class="grid">
<div class="gi"><div class="gv g">70.58%</div><div class="gl">GPU 利用率 (基线 39.64%)</div></div>
<div class="gi"><div class="gv g">−46%</div><div class="gl">排队延迟</div></div>
<div class="gi"><div class="gv g">−34%</div><div class="gl">作业完成时间</div></div>
<div class="gi"><div class="gv g">93%</div><div class="gl">租户周期合规 (平滑 QAD≥0.95)</div></div>
</div>
<p>70.58% 利用率及约 46% 排队降幅来自轨迹模拟，排队降幅相对 Lucid；34% 作业完成时间降幅和 93% 合规率来自 16 卡实测，完成时间比较对象为 Hard+Colocate。</p>
</div>

<div class="card card-d">
<h3>核心定位</h3>
<p>DeepShare 的 Kubernetes 实现拆成轻量 Controller 与实时 Scheduler Plugin 两层：</p>
<ul>
<li><strong>Controller</strong>：把 <code>TenantQuota</code> CRD 和作业 class annotation 整理为租户 quota 元数据。</li>
<li><strong>Scheduler Plugin</strong>：维护瞬时/平滑 QAD 和队列，执行排序、放置、colocation 准入与抢占。</li>
</ul>
<p>面试<span class="hl">Controller 管静态权益元数据，Scheduler Plugin 管实时 QAD 控制环。</span></p>
<p>论文不覆盖 Gang Scheduling，因此不引入 PodGroup / minAvailable；但 <strong>Permit 仍用于等待 CPU/Memory in-place resize 生效</strong>，不要把两种用途混在一起。</p>
</div>
