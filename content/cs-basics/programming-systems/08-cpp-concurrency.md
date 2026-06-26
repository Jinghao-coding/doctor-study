## 一句话结论

C++ 并发核心是 std::thread + mutex + condition_variable + future/promise + atomic 五件套；mutex 系列配 RAII 锁（lock_guard/unique_lock/scoped_lock）防死锁，condition_variable 必须和 mutex 一起用且 wait 要带 predicate 防虚假唤醒，atomic 靠 memory order（relaxed/acquire/release/seq_cst）建立跨线程 happens-before 关系，C++ 内存模型定义 data race 为 UB，无锁编程用 CAS 循环但要注意 ABA 问题。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 编程与系统工程基础 |
| 章节类型 | 机制类 |
| 解决问题 | C++11 线程库、同步原语、内存模型、无锁编程基础，面试和工程排障高频考点 |
| 面试抓手 | 先讲同步原语选择，再讲 memory order，最后给生产者-消费者和 CAS 代码模板 |

<div class="card card-m">
<h3>std::thread 基础</h3>
<pre><code class="language-cpp">#include &lt;thread&gt;
void func(int x, const string&amp; s) { /* ... */ }

thread t(func, 42, ref(str));  // ref 包装引用参数，否则按值拷贝
t.join();   // 等待线程结束
t.detach(); // 分离，线程在后台继续运行（小心生命周期问题！）

// jthread (C++20) 自动 join，支持 cooperative cancellation
jthread jt(func, 42, ref(str));</code></pre>
<p><strong>传参陷阱</strong>：thread 构造函数默认把参数<strong>按值拷贝</strong>到内部 storage，即使函数签名是引用。要传引用必须用 <code>std::ref</code> / <code>std::cref</code>。</p>
<p>线程函数的参数如果是左值引用，忘记 std::ref 会编译报错；如果是右值引用会隐式 move，但要警惕对象已被 move 后续访问。</p>
</div>

<div class="card card-d">
<h3>Mutex 家族与 RAII 锁</h3>
<table>
<tr><th>Mutex 类型</th><th>特点</th><th>用途</th></tr>
<tr><td>mutex</td><td>最基本的互斥锁，不可递归、不可超时</td><td>大多数场景</td></tr>
<tr><td>timed_mutex</td><td>支持 try_lock_for / try_lock_until</td><td>需要超时避免死等</td></tr>
<tr><td>recursive_mutex</td><td>同一线程可多次 lock，不会死锁</td><td>递归函数中加锁（尽量避免）</td></tr>
</table>
<table>
<tr><th>RAII 锁</th><th>特点</th></tr>
<tr><td>lock_guard</td><td>最简单，构造时 lock、析构时 unlock，不可手动解锁</td></tr>
<tr><td>unique_lock</td><td>灵活：可 defer_lock（延后加锁）、可手动 unlock/lock、可转移所有权，condition_variable wait 必须用它</td></tr>
<tr><td>scoped_lock (C++17)</td><td>同时锁多个 mutex，内部用死锁避免算法（std::lock），推荐多锁场景使用</td></tr>
</table>
<pre><code class="language-cpp">mutex mtx;
// 推荐：用 lock_guard / unique_lock 管理锁
{
    lock_guard&lt;mutex&gt; lock(mtx);  // 构造加锁
    shared_data++;                // 临界区
}                                 // 析构自动解锁，异常安全

// C++17 多锁，防死锁
mutex m1, m2;
{
    scoped_lock lock(m1, m2);  // 内部用 std::lock 避免死锁
}</code></pre>
</div>

<div class="card card-s">
<h3>Condition Variable 与生产者-消费者</h3>
<p>condition_variable 用于"等待某个条件成立"的线程间通信，必须和 mutex + unique_lock 配合使用：</p>
<pre><code class="language-cpp">template &lt;typename T&gt;
class ThreadSafeQueue {
    queue&lt;T&gt; q_;
    mutable mutex mtx_;
    condition_variable cv_;
public:
    void push(T value) {
        {
            lock_guard&lt;mutex&gt; lock(mtx_);
            q_.push(std::move(value));
        }
        cv_.notify_one();  // 通知一个等待的消费者
    }

    T pop() {
        unique_lock&lt;mutex&gt; lock(mtx_);
        // wait：必须用 predicate 形式，防止虚假唤醒
        cv_.wait(lock, [this] { return !q_.empty(); });
        T value = std::move(q_.front());
        q_.pop();
        return value;
    }

    optional&lt;T&gt; try_pop() {
        lock_guard&lt;mutex&gt; lock(mtx_);
        if (q_.empty()) return nullopt;
        T value = std::move(q_.front());
        q_.pop();
        return value;
    }
};</code></pre>
<p><strong>要点</strong>：①wait 必须带 predicate（lambda），循环检查条件，防虚假唤醒；②通知可以在锁外也可以在锁内，锁外通知可减少锁竞争；③push 时 notify_one 唤醒一个消费者，notify_all 唤醒所有（多个条件如队列有多个优先级用 notify_all）。</p>
</div>

<div class="card card-w">
<h3>Future / Promise / async</h3>
<pre><code class="language-cpp">#include &lt;future&gt;

// std::async：异步执行函数，返回 future
future&lt;int&gt; f = async(launch::async, [] { return 42; });
int result = f.get();  // 阻塞等待结果

// launch::async 立即在新线程执行；launch::deferred 延迟到 get() 时在当前线程执行
// 默认策略（不指定）是 deferred|async，由实现选择

// promise + future：手动传递结果
promise&lt;int&gt; p;
future&lt;int&gt; fut = p.get_future();
thread t([p = std::move(p)]() mutable {
    this_thread::sleep_for(1s);
    p.set_value(42);  // 生产结果
});
int val = fut.get();  // 等待 set_value
t.join();

// packaged_task：把函数包装成 future 提供者
packaged_task&lt;int()&gt; task([] { return 42; });
future&lt;int&gt; f2 = task.get_future();
thread t2(std::move(task));
int v = f2.get();</code></pre>
<p>共享 future：<code>shared_future&lt;T&gt;</code> 可以被多个线程等待（future 只能 get 一次），通过 <code>fut.share()</code> 获取。</p>
</div>

<div class="card card-m">
<h3>Atomic 与 Memory Order</h3>
<p><code>std::atomic&lt;T&gt;</code> 提供原子操作，底层靠 CPU 指令（lock 前缀、LL/SC、CAS）保证单个操作的原子性，但原子性不等于跨线程顺序。<strong>memory order</strong> 控制编译器和 CPU 的重排：</p>
<table>
<tr><th>memory_order</th><th>语义</th><th>用途</th></tr>
<tr><td>memory_order_relaxed</td><td>仅保证原子性，无顺序约束</td><td>计数器（不依赖顺序）</td></tr>
<tr><td>memory_order_acquire</td><td>读操作，之后的读写不能重排到它前面</td><td>加载同步点</td></tr>
<tr><td>memory_order_release</td><td>写操作，之前的读写不能重排到它后面</td><td>发布同步点</td></tr>
<tr><td>memory_order_acq_rel</td><td>同时是 acquire 和 release（RMW 操作）</td><td>fetch_add 等读改写</td></tr>
<tr><td>memory_order_seq_cst</td><td>顺序一致性，全局统一顺序（最强也是默认）</td><td>默认选择，最不容易错</td></tr>
</table>
<pre><code class="language-cpp">// 无锁计数器：CAS 循环（compare-exchange loop）
atomic&lt;int&gt; counter{0};

void increment() {
    int expected = counter.load(memory_order_relaxed);
    while (!counter.compare_exchange_weak(
            expected, expected + 1,
            memory_order_acq_rel, memory_order_relaxed)) {
        // expected 被更新为当前值，重试
    }
}
// 简单场景直接用：counter.fetch_add(1, memory_order_relaxed);</code></pre>
<p><strong>compare_exchange_weak vs strong</strong>：weak 可能伪失败（即使值相等也返回 false），适合循环中使用；strong 保证不伪失败，但性能略差，适合不循环的场景。</p>
</div>

<div class="card card-r">
<h3>Acquire-Release 模式详解</h3>
<p>这是最常用的非 seq_cst 模式，用于"生产者发布数据，消费者获取数据"：</p>
<pre><code class="language-cpp">atomic&lt;bool&gt; ready{false};
int data = 0;

// 线程 A（生产者）
void producer() {
    data = 42;                          // (1) 写数据
    ready.store(true, memory_order_release);  // (2) 发布：(1) 不会重排到 (2) 之后
}

// 线程 B（消费者）
void consumer() {
    while (!ready.load(memory_order_acquire));  // (3) 获取
    assert(data == 42);                         // (4) 一定读到 42！
    // acquire 保证 (4) 不会重排到 (3) 之前，且看到 release 之前的所有写
}</code></pre>
<p><strong>synchronizes-with 关系</strong>：如果一个 release store 被一个 acquire load 读到，那么 release 之前的所有写操作都对 acquire 之后的读可见，这就是 happens-before 的基础。</p>
<div class="qa-summary">面试口径：relaxed 最轻量但只能保证原子性；acquire/release 建立单向同步；seq_cst 最强，所有线程看到一致的全局修改顺序，默认用 seq_cst 不出错。</div>
</div>

<div class="card card-d">
<h3>死锁预防</h3>
<p>死锁四个必要条件：互斥、持有并等待、不可剥夺、循环等待。常用预防手段：</p>
<ul>
<li><strong>固定加锁顺序</strong>：多个线程都按相同顺序获取锁，打破循环等待。</li>
<li><strong>std::scoped_lock / std::lock</strong>：C++17 的 scoped_lock 内部使用死锁避免算法（类似 try-and-backoff），一次性获取多个锁不会死锁。</li>
<li><strong>try_lock 回退</strong>：获取不到所有锁时释放已获取的，等一会重试。</li>
<li><strong>减少锁粒度</strong>：锁持有时间尽量短，锁的范围尽量小。</li>
</ul>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: condition_variable 为什么必须和 mutex 一起用？为什么不能直接用一个 atomic bool？</div>
<div class="qa-a"><p>有两个核心原因：<strong>①丢失唤醒（lost wakeup）问题</strong>。如果线程 A 检查条件发现不满足、正准备 wait 时，线程 B 修改条件并 notify，这个 notify 会丢失（A 还没进入 wait 状态），A 永远等不到。mutex 保证"检查条件"和"进入 wait"是原子的——wait 在内部把锁释放并进入等待是一个不可分割的操作，notify 在持锁时发，wait 在持锁时等，就不会丢信号。<strong>②条件本身的保护</strong>。条件（如队列是否为空）是多个线程共享的变量，必须用 mutex 保护，否则检查条件本身就是 data race（UB）。atomic bool 可以解决原子性，但无法原子地"检查并睡眠"，仍有 lost wakeup 风险。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: memory_order_relaxed 到底会怎样？为什么不总是用最强的 seq_cst？</div>
<div class="qa-a"><p><code>memory_order_relaxed</code> 只保证单个原子变量的修改是原子的（不会读到撕裂值），但<strong>完全不保证顺序</strong>：不同线程对多个变量的 relaxed 访问可能看到完全不同的顺序，编译器和 CPU 可以自由重排。它适合纯计数器场景（如引用计数、统计计数），这些场景只关心最终值，不依赖操作顺序。为什么不用 seq_cst 到处用？因为<strong>性能开销</strong>：seq_cst 通常会插入内存屏障指令（如 x86 的 MFENCE 或 lock 前缀），阻止编译器和 CPU 重排，在高并发场景（如无锁数据结构）会显著影响性能。但在一般业务代码中，优先用 seq_cst（或 mutex）保证正确性，只有在性能热点且对内存模型理解透彻时才用 acquire/release/relaxed。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是虚假唤醒（spurious wakeup）？为什么 wait 必须带 predicate？</div>
<div class="qa-a"><p>虚假唤醒是指 condition_variable 的 wait 没有被任何线程 notify 却返回了的现象。这不是 bug，而是<strong>POSIX 线程等底层实现允许的行为</strong>（为了实现更简单/性能更好），在 Linux 上偶发、Windows 上几乎不会发生。应对方式就是 <strong>wait 的 predicate 形式</strong>：<code>cv.wait(lock, predicate)</code> 等价于 <code>while (!predicate()) cv.wait(lock);</code>，醒来后再检查一次条件，不满足就继续等。永远不要写不带 predicate 的 wait：<code>cv.wait(lock);</code> 是错的！因为即使不是虚假唤醒，也可能有多个消费者被 notify，一个消费者取走数据后队列又空了，其他消费者醒来发现条件不满足也得继续等。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: detach 后的线程怎么安全退出？</div>
<div class="qa-a"><p>强烈建议<strong>避免 detach</strong>，优先用 join + 协作式退出标志（如 atomic&lt;bool&gt; stop_flag 或 C++20 jthread 的 stop_token）。如果必须 detach（如某些框架要求），安全退出要点：①线程函数不能持有栈上/已析构对象的引用或指针（detach 后线程还在跑，主线程对象可能已销毁）——这是 detach 最大的坑，常导致 use-after-free。②用静态对象、shared_ptr 或全局/堆上数据来传递状态。③用 <code>std::atomic&lt;bool&gt;</code> 做退出标志，线程循环检查它。④程序退出时无法 join detached 线程，main 返回后 detached 线程会被强制终止（可能导致数据损坏），尽量设计成 daemon 线程或用 <code>std::atexit</code> 协调。工程上更推荐：让线程对象作为类成员，析构时设置 stop flag + join 等待退出，即 RAII 管理线程生命周期。</p></div>
</div>

## 关联模块

- `04-cpp-memory.md`：多线程内存模型和 cache coherence 是理解 memory order 的硬件基础
- `05-cpp-compile-smartptr.md`：多线程下 shared_ptr 的引用计数本身是原子的，但对象访问需要额外同步
- `07-cpp-stl-containers.md`：STL 容器本身不是线程安全的，需要外部同步（容器适配器的并发版本如 TBB concurrent_queue）
