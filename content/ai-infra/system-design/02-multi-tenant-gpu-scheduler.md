<div class="card card-d">
<h3>题目</h3>
<p>设计一个多团队共享的 GPU 训练集群调度系统，要求公平且高效。</p>

<h3>设计要点</h3>
<ol>
<li><strong>配额管理</strong>
  <ul>
  <li>QAD 连续信号替代二元配额（有/没有）</li>
  <li>DRA 弹性借用：闲置资源可借，需要时按 QAD 优先级回收</li>
  </ul>
</li>
<li><strong>调度排序</strong>
  <ul>
  <li>词典序 (QAD↑, T̂↑)：先满足最欠缺的租户，同等 QAD 下短作业优先</li>
  <li>代价基抢占：综合释放资源量和沉没成本</li>
  </ul>
</li>
<li><strong>资源共享</strong>
  <ul>
  <li>干扰感知合用：RF 预测性能保持率 → 高于阈值才合用</li>
  <li>运行时监控 + 驱逐机制保护主任务</li>
  </ul>
</li>
<li><strong>K8s 原生</strong>
  <ul>
  <li>Scheduler Plugin 覆盖 5 个扩展点</li>
  <li>DaemonSet 部署 MPS daemon + DCGM 监控</li>
  <li>Lease-based 选主保证高可用</li>
  </ul>
</li>
</ol>

<h3>追问方向</h3>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">追问：怎么处理大任务和小任务的矛盾？</div>
<div class="qa-a"><p>大任务（需要 64 GPU）和小任务（需要 1 GPU）的调度矛盾：(1) Gang scheduling 保证大任务原子性。(2) Backfill 让小任务见缝插针。(3) 大任务可以拆分为弹性训练（先用 32 GPU 开始，有空闲再扩到 64）。(4) 预留机制：为大任务预留资源窗口，避免永远等不到足够资源。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">追问：如何处理异构 GPU？</div>
<div class="qa-a"><p>(1) ResourceFlavor 区分不同 GPU 型号（A100/H100/V100）。(2) 运行时间预测模型需要区分 GPU 类型——同样的作业在 A100 和 H100 上时间不同。(3) 价格/性能比引导调度：不紧急的任务用便宜 GPU，紧急任务用高端 GPU。(4) 混合精度兼容性：H100 支持 FP8，A100 只支持到 FP16/BF16。</p></div>
</div>
</div>

<hr class="div">
