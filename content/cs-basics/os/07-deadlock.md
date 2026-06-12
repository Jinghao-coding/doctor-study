<div class="card card-m">
<h3>死锁：四个必要条件</h3>
<p>死锁是指一组进程/线程互相持有对方需要的资源，谁都无法继续。下面四个条件<strong>同时满足</strong>才会发生，破坏任意一个即可预防。</p>
<table>
<tr><th>条件</th><th>含义</th><th>破坏方式</th></tr>
<tr><td>互斥</td><td>资源同一时刻只能被一个持有</td><td>资源可共享化（多数难破坏）</td></tr>
<tr><td>持有并等待</td><td>持有资源的同时等待新资源</td><td>一次性申请全部资源</td></tr>
<tr><td>不可剥夺</td><td>资源不能被强行抢走</td><td>允许超时释放、可抢占</td></tr>
<tr><td>循环等待</td><td>存在环形等待链</td><td>按全局固定顺序加锁</td></tr>
</table>
<div class="qa-summary">工程上最常用、最实用的手段是破坏“循环等待”——所有线程按统一顺序加锁。</div>
</div>

<div class="card card-d">
<h3>处理策略：预防 / 避免 / 检测 / 恢复</h3>
<table>
<tr><th>策略</th><th>做法</th><th>代价</th></tr>
<tr><td>预防</td><td>破坏四条件之一（如固定加锁顺序）</td><td>降低并发或资源利用率</td></tr>
<tr><td>避免</td><td>运行时判断是否进入不安全状态（银行家算法）</td><td>需预知最大需求，实际少用</td></tr>
<tr><td>检测</td><td>构建资源分配图找环</td><td>检测有开销</td></tr>
<tr><td>恢复</td><td>杀进程、回滚、抢占资源</td><td>有副作用，需可重试</td></tr>
</table>
<p>大多数业务系统采用<strong>预防 + 超时</strong>：统一加锁顺序避免大部分死锁，再用锁超时（<code>try_lock</code> + 超时回退）兜底，而不是上线复杂的银行家算法。</p>
</div>

<div class="card card-r">
<h3>经典死锁代码（加锁顺序不一致）</h3>

<pre><code class="language-cpp">
// 线程 A: lock(mutex1) -> lock(mutex2)
// 线程 B: lock(mutex2) -> lock(mutex1)   <-- 顺序相反，可能死锁

// 修复：所有线程统一按地址/ID 顺序加锁
std::lock(mutex1, mutex2);            // C++ 一次性获取，避免顺序问题
std::lock_guard<std::mutex> g1(mutex1, std::adopt_lock);
std::lock_guard<std::mutex> g2(mutex2, std::adopt_lock);
</code></pre>

</div>

<div class="card card-w">
<h3>死锁排查与活锁/饥饿区分</h3>
<table>
<tr><th>现象</th><th>特征</th><th>排查/区分</th></tr>
<tr><td>死锁</td><td>线程互相等待，CPU 不忙但卡死</td><td><code>gdb</code> / <code>pstack</code> 看线程栈都停在 lock；<code>jstack</code>（Java）能直接报 deadlock</td></tr>
<tr><td>活锁</td><td>线程不停重试却都没进展，CPU 很忙</td><td>加随机退避打破对称</td></tr>
<tr><td>饥饿</td><td>某线程长期抢不到资源</td><td>用公平锁、优先级 aging</td></tr>
</table>
</div>

<div class="card card-s">
<h3>和 AI Infra / 分布式的联系</h3>
<p>死锁不只在单机锁里出现：<strong>① 分布式训练</strong>中，集合通信（如 NCCL all-reduce）要求所有 rank 都参与，如果某个 rank 因异常没进入通信原语，其他 rank 会一直等待，表现为整作业 hang（本质是分布式死锁/挂起）；<strong>② 资源调度</strong>中，多个大作业各占一部分 GPU 又都等不到完整资源，形成资源死锁，需靠 gang scheduling（要么全给要么不给）破解；<strong>③ 数据库/分布式锁</strong>跨服务加锁顺序不一致同样会死锁。排查训练 hang 常用 <code>py-spy dump</code> / 看各 rank 卡在哪一步。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何预防死锁？工程上最实用的办法是什么？</div>
<div class="qa-a"><p>理论上破坏四个必要条件之一即可，但互斥和不可剥夺往往难破坏。工程上最实用的是<strong>破坏循环等待</strong>：给所有锁定义全局顺序，任何线程都按同一顺序加锁，环就不可能形成。再辅以<strong>锁超时 + 可重试</strong>兜底，以及减小锁粒度、缩短临界区、能用无锁结构就用无锁。</p><div class="qa-summary">面试口径：先说四条件，再落到“统一加锁顺序 + 超时回退”这种可落地的方案，比背银行家算法更有说服力。</div></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 分布式训练任务 hang 住了，可能和死锁有什么关系？</div>
<div class="qa-a"><p>集合通信是同步屏障，要求所有 rank 一起到达。如果某个 rank 提前报错退出、走了不同的代码分支、或数据加载卡住没进入 all-reduce，其余 rank 会在通信原语上无限等待，整个作业 hang——这是一种分布式层面的“互相等待”。排查时用 <code>py-spy</code>/栈抓取看各 rank 卡在哪，常见根因是 rank 间逻辑分支不一致或某卡 OOM/异常。</p></div>
</div>
