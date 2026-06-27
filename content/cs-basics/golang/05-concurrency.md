## 一句话结论

Go 并发哲学是 **CSP（Communicating Sequential Processes）**：「Don't communicate by sharing memory; share memory by communicating」；核心工具是 goroutine + channel + select + sync 包 + context，面试必考点是 channel 语义（unbuffered vs buffered、close 后行为）、select 随机选择、Mutex vs channel 选型、context 取消传播。

<div class="card card-m">
<h3>CSP 并发模型</h3>
<p>传统并发编程是「共享内存 + 锁」：多个线程访问共享变量，用互斥锁保证原子性，容易出 data race、死锁。Go 推崇 CSP 模型：goroutine 之间通过 channel 通信，不共享内存，数据的所有权通过 channel 传递。</p>
<table>
<tr><th>并发模型</th><th>通信方式</th><th>特点</th><th>Go 实现</th></tr>
<tr><td>共享内存</td><td>共享变量 + Mutex/RWMutex</td><td>性能好，但容易出 data race、死锁，需要仔细设计锁粒度</td><td>sync.Mutex、sync.RWMutex</td></tr>
<tr><td>CSP</td><td>channel 传递数据</td><td>代码清晰，数据所有权明确，goroutine 之间解耦</td><td>chan T、select</td></tr>
</table>
<div class="qa-summary">一句话：Go 不是不让用锁，而是推荐优先用 channel 做 goroutine 间协作；保护共享状态临界区小的时候用 Mutex 更简单，传递数据所有权的时候用 channel 更清晰。</div>
</div>

<div class="card card-s">
<h3>Channel 语义详解</h3>
<p>channel 是 goroutine 之间通信的管道，是类型安全的队列。</p>
<pre><code class="language-go">ch := make(chan int)        // 无缓冲 channel（同步）
ch := make(chan int, 10)    // 缓冲 channel，容量 10（异步）
ch <- v                     // 发送 v 到 ch
v := <-ch                   // 从 ch 接收
v, ok := <-ch               // 接收，ok=false 表示 channel 已关闭且读完
close(ch)                   // 关闭 channel（只能由发送方关闭）
</code></pre>
<table>
<tr><th>操作</th><th>nil channel</th><th>已关闭 channel</th><th>正常 channel</th></tr>
<tr><td>发送 ch <- v</td><td>永远阻塞</td><td>panic: send on closed channel</td><td>阻塞直到有接收者（unbuffered）或缓冲区满（buffered）</td></tr>
<tr><td>接收 v := <-ch</td><td>永远阻塞</td><td>立刻返回，读完缓冲后返回零值+ok=false</td><td>阻塞直到有发送者</td></tr>
<tr><td>close(ch)</td><td>panic</td><td>panic: close of closed channel</td><td>关闭 channel</td></tr>
</table>
<div class="card-d">
<h4>Unbuffered vs Buffered Channel</h4>
<table>
<tr><th></th><th>Unbuffered（make(chan T)）</th><th>Buffered（make(chan T, n)）</th></tr>
<tr><td>容量</td><td>0</td><td>n</td></tr>
<tr><td>发送行为</td><td>发送阻塞直到有 goroutine 接收（同步握手 rendezvous）</td><td>缓冲区未满时发送不阻塞，满了阻塞</td></tr>
<tr><td>接收行为</td><td>接收阻塞直到有 goroutine 发送</td><td>缓冲区非空时接收不阻塞，空了阻塞</td></tr>
<tr><td>语义</td><td>强同步：发送和接收必须同时就绪</td><td>异步：解耦发送和接收的速度</td></tr>
<tr><td>适用场景</td><td>信号通知、两个 goroutine 同步、一对一交接</td><td>任务队列、限流（容量=并发数）、生产者消费者</td></tr>
</table>
</div>
<div class="card-w">
<h4>⚠️ Channel 方向约束</h4>
<p>函数参数中可以指定 channel 方向，让编译器帮你检查，防止误操作：</p>
<pre><code class="language-go">func producer(ch chan<- int)  { ch <- 1 }  // 只能发送
func consumer(ch <-chan int)  { <-ch }     // 只能接收
func bidirectional(ch chan int) { ... }    // 可发可收
</code></pre>
</div>
</div>

<div class="card card-s">
<h3>Select：多路复用 channel</h3>
<p>select 同时等待多个 channel 操作，哪个 case 就绪就执行哪个。</p>
<pre><code class="language-go">select {
case v := <-ch1:
    fmt.Println("ch1 收到:", v)
case ch2 <- 42:
    fmt.Println("ch2 发送了 42")
case <-time.After(3 * time.Second):
    fmt.Println("超时了")
default:
    fmt.Println("没有 case 就绪，不阻塞（非阻塞模式）")
}
</code></pre>
<div class="qa-summary">select 关键特性：① 多个 case 同时就绪时随机选一个执行（公平性，不总是选第一个）；② default 让 select 不阻塞，用于轮询；③ for-range 可以循环从 channel 接收，channel 关闭时自动退出循环。</div>
<pre><code class="language-go">// for-range 接收 channel：close(ch) 后循环自动退出
for v := range ch {
    fmt.Println(v)
}
</code></pre>
</div>

<div class="card card-m">
<h3>sync 包：传统并发原语</h3>
<p>不是所有并发场景都适合 channel，保护共享状态临界区时，sync 包往往更简单直接。</p>
<table>
<tr><th>类型</th><th>作用</th><th>用法</th><th>注意事项</th></tr>
<tr><td><code>Mutex</code></td><td>互斥锁</td><td><code>mu.Lock(); defer mu.Unlock()</code></td><td>不可重入（Go 故意不设计可重入锁）；不要复制 Mutex（用指针传递）</td></tr>
<tr><td><code>RWMutex</code></td><td>读写锁</td><td><code>mu.RLock()/RUnlock()</code> 读，<code>mu.Lock()/Unlock()</code> 写</td><td>读多写少场景性能好；写锁等待时会阻塞后续读，防止写饥饿</td></tr>
<tr><td><code>WaitGroup</code></td><td>等待一组 goroutine 完成</td><td><code>wg.Add(n); defer wg.Done(); wg.Wait()</code></td><td>Add 必须在 goroutine 启动前调用，不要在 goroutine 里面 Add；不要复制 WaitGroup</td></tr>
<tr><td><code>Once</code></td><td>保证函数只执行一次</td><td><code>var once sync.Once; once.Do(f)</code></td><td>常用于单例初始化、配置加载；f panic 了也算执行过</td></tr>
<tr><td><code>Cond</code></td><td>条件变量</td><td>等待/唤醒多个 goroutine</td><td>复杂场景用 channel 更简单，少用 Cond</td></tr>
<tr><td><code>Pool</code></td><td>对象池</td><td><code>pool.Get()/Put(x)</code></td><td>用于复用临时对象减少 GC 压力（如 bytes.Buffer），对象随时可能被 GC 回收，不能存连接池这种</td></tr>
</table>
<pre><code class="language-go">// WaitGroup 正确用法
var wg sync.WaitGroup
for i := 0; i < 10; i++ {
    wg.Add(1) // ✅ 在 goroutine 外面 Add
    go func(i int) {
        defer wg.Done()
        fmt.Println(i)
    }(i)
}
wg.Wait()
</code></pre>
</div>

<div class="card card-m">
<h3>Context：取消、超时、传值</h3>
<p>context 是 Go 并发编程的标准实践，用于在 goroutine 调用链中传播取消信号、超时、截止时间和请求级值。</p>
<pre><code class="language-go">// 派生 context（从父 context 派生，形成树结构）
ctx, cancel := context.WithCancel(parentCtx)   // 手动取消
ctx, cancel := context.WithTimeout(parentCtx, 5*time.Second) // 超时自动取消
ctx, cancel := context.WithDeadline(parentCtx, time.Now().Add(5*time.Second)) // 截止时间
ctx := context.WithValue(parentCtx, key, val)  // 传请求级值

defer cancel() // 一定要调用 cancel，释放资源

select {
case <-ctx.Done():
    // ctx 被取消：ctx.Err() 是 context.Canceled 或 context.DeadlineExceeded
    fmt.Println("取消了:", ctx.Err())
case v := <-ch:
    fmt.Println("结果:", v)
}
</code></pre>
<div class="card-w">
<h4>⚠️ Context 使用原则</h4>
<ul>
<li>✅ Context 作为函数第一个参数，命名为 ctx：<code>func DoSomething(ctx context.Context, ...)</code></li>
<li>✅ 不要把 Context 存在 struct 里（除了底层库内部）</li>
<li>✅ 派生 context 一定要 defer cancel()，否则 goroutine 泄漏</li>
<li>✅ context.Value 只传请求范围的元数据（traceID、requestID），不要传业务参数</li>
<li>❌ 不要传 nil context，用 context.TODO() 或 context.Background() 占位</li>
</ul>
</div>
<div class="qa-summary">取消传播：父 context 取消，所有派生子 context 都会同时取消；调用链上所有监听 ctx.Done() 的 goroutine 都会收到信号并退出，这是优雅关停的标准做法。</div>
</div>

<div class="card card-d">
<h3>生产者-消费者示例（buffered channel）</h3>
<pre><code class="language-go">func producer(ctx context.Context, ch chan<- int) {
    i := 0
    for {
        select {
        case <-ctx.Done():
            close(ch) // 退出时关闭 channel，通知消费者
            return
        case ch <- i:
            i++
        }
    }
}

func consumer(ctx context.Context, ch <-chan int) {
    for v := range ch { // channel 关闭后 range 自动退出
        fmt.Println("消费:", v)
    }
}

func main() {
    ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
    defer cancel()

    ch := make(chan int, 10)
    go producer(ctx, ch)
    go consumer(ctx, ch)

    <-ctx.Done()
    time.Sleep(100 * time.Millisecond) // 等消费者处理完
}
</code></pre>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: channel 关闭后还能 recv 吗？往 closed channel send 会怎么样？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>分发送、接收、重复 close 三种情况说清楚，记住「谁创建谁关闭，发送方关闭」。</p>
<div class="qa-section">
<div class="qa-section-title">向已关闭的 channel 发送</div>
<p>会立刻 panic：<code>panic: send on closed channel</code>。这是程序错误，发送方必须保证 channel 关闭后不再发送，通常是发送方（生产者）负责关闭 channel，消费者不关闭。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">从已关闭的 channel 接收</div>
<p>可以正常接收，不会 panic：<br>
1. 如果 channel 缓冲区还有数据，继续读缓冲区数据，ok = true<br>
2. 缓冲区读完了，立刻返回该类型的零值，ok = false<br>
这就是为什么 <code>v, ok := <-ch</code> 中 ok 很重要：ok=true 说明是有效数据，ok=false 说明 channel 已关闭且没有数据了。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">重复关闭 channel</div>
<p>close 一个已经关闭的 channel 会 panic：<code>panic: close of closed channel</code>。关闭 nil channel 也会 panic。</p>
</div>
<div class="qa-summary">面试口径：close(channel) 原则——永远在生产者侧关闭，不要在消费者侧关闭；从 closed channel recv 安全（零值+ok=false），send/close 已关闭的 channel 都会 panic。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: select 如果多个 case 同时 ready 会选哪个？为什么这样设计？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>是伪随机选择，目的是公平性，避免饥饿。</p>
<div class="qa-section">
<div class="qa-section-title">行为</div>
<p>如果 select 的多个 case 同时就绪（比如多个 channel 同时有数据），Go 会<strong>随机均匀选择一个 case 执行</strong>，不是按代码顺序选第一个。如果只有 default 就绪，直接走 default；如果都没就绪且没有 default，select 阻塞直到有一个 case 就绪。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">为什么要随机？</div>
<p>如果总是按顺序选第一个就绪的 case，会导致前面的 case 总是被优先处理，后面的 case 一直得不到执行（饥饿问题）。随机选择保证了多个就绪 channel 有公平的执行机会。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">空 select 会怎么样？</div>
<p><code>select {}</code> 没有任何 case，会永远阻塞当前 goroutine。有时候 main goroutine 不想退出就写 select{}，但更推荐用信号等待或者 channel 阻塞。</p>
</div>
<div class="qa-summary">面试口径：select 多个 case ready 时随机选一个，这是为了公平性避免饥饿；不要依赖 case 顺序，不要写 select{} 泄漏 goroutine。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Mutex 和 channel 怎么选？什么时候用哪个？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>不是非此即彼，Go 社区有明确的经验法则。</p>
<div class="qa-section">
<div class="qa-section-title">用 channel 的场景</div>
<p>① 传递数据所有权（把数据从一个 goroutine 交给另一个）；② 异步分发任务（worker pool 用 channel 传任务）；③ 多路复用等待多个事件（select 监听多个信号）；④ 协调 goroutine 生命周期（done channel 通知退出）。一句话：「通过通信来共享内存」的时候用 channel。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">用 Mutex 的场景</div>
<p>① 保护共享状态的临界区（比如一个 map、一个计数器，多 goroutine 读写）；② 临界区很小、很简单（increment 一个计数器、读写一个字段）；③ 性能关键路径，channel 有额外的调度开销。一句话：「共享内存来通信」的时候，也就是单纯保护共享数据，用 Mutex 更简单直接。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">社区经验（Go Wiki）</div>
<p>Channel 是「拥有」数据的 goroutine 之间转移所有权；Mutex 是保护共享结构内部状态。新手容易犯的错是不管什么都套 channel，导致代码绕来绕去；反过来也不要无脑用 Mutex 做 goroutine 协调。一个典型判断：如果你的互斥锁只是保护一个结构体字段，用 Mutex；如果涉及 goroutine 等待/通知/分发，考虑 channel。</p>
</div>
<div class="qa-summary">面试口径：Channel 擅长 goroutine 间通信、协调、所有权转移；Mutex 擅长保护共享临界区；根据场景选，不要教条地「只用 channel」。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: context 取消是怎么传播的？为什么说不要用 context.Value 传业务参数？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>context 是树结构，取消自上而下传播；Value 设计目的是请求元数据，不是参数传递。</p>
<div class="qa-section">
<div class="qa-section-title">取消传播机制</div>
<p>context 形成一棵树：Background()/TODO() 是根节点，WithCancel/WithTimeout/WithDeadline 派生子节点。当父节点被取消，所有子节点（包括子节点的子节点...）都会级联取消，所有监听 ctx.Done() 的 goroutine 都会收到信号。底层是每个 context 维护一个 done channel 和 children 集合，取消时 close(done channel)，所有 <-ctx.Done() 都会立刻返回。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">context.Value 为什么不推荐传业务参数</div>
<p>context.Value 设计目标是传「请求范围的元数据」，比如 traceID、requestID、认证 token、logger 这种跨 API 边界、和业务逻辑无关的东西。为什么不能传业务参数：① 没有类型检查，值是 interface{}，取出来要类型断言；② 依赖隐式传递，函数签名看不出来依赖了什么参数，可读性差，重构难；③ 值是线性查找（沿父链向上找），性能随深度下降；④ 容易被中间层覆盖，出现难以调试的问题。业务参数就明明白白写在函数参数里。</p>
</div>
<div class="qa-summary">面试口径：取消是级联传播的树结构；context.Value 只传跨切面的请求元数据（traceID 这类），业务参数显式放函数参数里，不要图省事塞 context。</div>
</div>
</div>
