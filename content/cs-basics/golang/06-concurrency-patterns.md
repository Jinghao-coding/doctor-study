## 一句话结论

Go 并发常见模式包括 worker pool、pipeline、fan-in/fan-out、超时/限流；面试最高频坑点是 **for-range 循环变量捕获**、goroutine 泄漏、WaitGroup.Add 位置错误，必须能手写出错代码和修正版本，知道用 `go test -race` 检测 data race、pprof 检测 goroutine 泄漏。

<div class="card card-m">
<h3>常见并发模式</h3>
<p>这些模式是 Go 并发编程的「套路」，写服务端代码会反复用到。</p>
<table>
<tr><th>模式</th><th>用途</th><th>核心结构</th></tr>
<tr><td>Worker Pool</td><td>固定数量 goroutine 处理任务，控制并发数</td><td>任务 channel + N 个 worker goroutine + WaitGroup</td></tr>
<tr><td>Pipeline</td><td>多阶段处理，每阶段输出是下一阶段输入</td><td>多个 channel 串联，每个阶段是一组 goroutine</td></tr>
<tr><td>Fan-Out / Fan-In</td><td>并行处理任务再合并结果</td><td>多个 goroutine 读同一个 channel（fan-out），结果写入同一个 channel（fan-in）</td></tr>
<tr><td>Timeout</td><td>防止操作永远阻塞</td><td>select + time.After / context.WithTimeout</td></tr>
<tr><td>Rate Limiting</td><td>控制请求速率</td><td>time.Ticker 或带缓冲 channel 做令牌桶</td></tr>
<tr><td>Done Channel</td><td>通知 goroutine 退出</td><td>close(done) 广播信号，select 监听 <-done</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Worker Pool 示例</h3>
<p>固定 worker 数量，避免无限创建 goroutine 把系统打挂。</p>
<pre><code class="language-go">func worker(id int, jobs <-chan int, results chan<- int, wg *sync.WaitGroup) {
    defer wg.Done()
    for job := range jobs {
        fmt.Printf("worker %d 处理 job %d\n", id, job)
        results <- job * 2
    }
}

func main() {
    const numJobs = 10
    const numWorkers = 3

    jobs := make(chan int, numJobs)
    results := make(chan int, numJobs)

    var wg sync.WaitGroup
    for w := 1; w <= numWorkers; w++ {
        wg.Add(1)
        go worker(w, jobs, results, &wg)
    }

    for j := 1; j <= numJobs; j++ {
        jobs <- j
    }
    close(jobs)

    go func() {
        wg.Wait()
        close(results)
    }()

    for result := range results {
        fmt.Println("结果:", result)
    }
}
</code></pre>
</div>

<div class="card card-d">
<h3>超时与限频示例</h3>
<pre><code class="language-go">// 超时控制：用 select + time.After
func doWithTimeout() error {
    select {
    case res := <-doWork():
        fmt.Println(res)
        return nil
    case <-time.After(2 * time.Second):
        return errors.New("timeout")
    }
}

// 限频：用 time.Ticker 控制 QPS
func rateLimit(requests <-chan Request) {
    ticker := time.NewTicker(100 * time.Millisecond) // 每秒 10 个
    defer ticker.Stop()
    for req := range requests {
        <-ticker.C // 等令牌
        go process(req)
    }
}
</code></pre>
</div>

<div class="card card-r">
<h3>⚠️ 坑点 1：for-range 循环变量捕获（Go 面试第一坑）</h3>
<p>这是最经典的 Go 并发 bug，几乎每个 Go 工程师都踩过。for 循环的循环变量在整个循环中是**同一个变量**，只是每次迭代被重新赋值。</p>
<pre><code class="language-go">// ❌ 错误写法：所有 goroutine 可能打印同一个（最后一个）值
for i := 0; i < 5; i++ {
    go func() {
        fmt.Println(i) // 闭包引用的是循环变量 i 的地址
    }()
}
time.Sleep(time.Second)
// 很可能输出：5 5 5 5 5（或其他混乱结果）

// ✅ 正确写法 1：把 i 作为参数传入（参数是值拷贝）
for i := 0; i < 5; i++ {
    go func(n int) {
        fmt.Println(n)
    }(i)
}

// ✅ 正确写法 2：循环体内用局部变量 shadow（每次循环新建一个变量）
for i := 0; i < 5; i++ {
    i := i // 重要！创建局部 i，遮蔽外部循环变量
    go func() {
        fmt.Println(i)
    }()
}
</code></pre>
<div class="qa-summary">坑点原因：闭包捕获的是变量引用，不是变量值；循环变量是复用的，goroutine 执行时循环可能已经结束了，读到的是最终值。Go 1.22 之后修复了这个问题，循环变量每次迭代都是新的，但面试默认按旧版本行为考。</div>
</div>

<div class="card card-r">
<h3>⚠️ 坑点 2：Goroutine 泄漏</h3>
<p>goroutine 很轻量，但不是免费的。如果 goroutine 因为 channel 永远阻塞无法退出，它就泄漏了——内存不释放，GC 也回收不了，服务跑久了内存涨、goroutine 数越来越多，最后 OOM。</p>
<pre><code class="language-go">// ❌ 泄漏：如果 ch 永远没数据，这个 goroutine 永远阻塞
func leak() {
    ch := make(chan int)
    go func() {
        val := <-ch // 永远等，没人发，goroutine 泄漏
        fmt.Println(val)
    }()
}

// ✅ 正确：用 context 或 done channel 通知退出
func noLeak(ctx context.Context) {
    ch := make(chan int)
    go func() {
        select {
        case val := <-ch:
            fmt.Println(val)
        case <-ctx.Done(): // 收到取消信号就退出
            return
        }
    }()
}
</code></pre>
<div class="card-d">
<h4>常见 goroutine 泄漏原因</h4>
<ul>
<li>channel 没人发送/接收，goroutine 永远等</li>
<li>没有设置超时的 HTTP/RPC 请求</li>
<li>WaitGroup.Add 数量不匹配，Wait() 永远等</li>
<li>死锁（互相等锁，但全程序死锁 Go 会 panic，单个 goroutine 等不会）</li>
</ul>
</div>
</div>

<div class="card card-r">
<h3>⚠️ 坑点 3：nil channel 永远阻塞（妙用）</h3>
<p>从 nil channel 接收、向 nil channel 发送都会永远阻塞。这看起来是坑，但在 select 里是有用的技巧：把已经处理完的 case 的 channel 设为 nil，相当于禁用这个 case，不用退出 select 循环。</p>
<pre><code class="language-go">// nil channel 的妙用：合并两个 channel
func merge(a, b <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for a != nil || b != nil {
            select {
            case v, ok := <-a:
                if !ok {
                    a = nil // a 关闭了，设为 nil，下次 select 这个 case 永远阻塞
                    continue
                }
                out <- v
            case v, ok := <-b:
                if !ok {
                    b = nil // 同理
                    continue
                }
                out <- v
            }
        }
    }()
    return out
}
</code></pre>
</div>

<div class="card card-r">
<h3>⚠️ 坑点 4：WaitGroup.Add 在 goroutine 里面调用（竞态）</h3>
<pre><code class="language-go">// ❌ 错误：wg.Add 在 goroutine 里，可能 wg.Wait() 时 Add 还没执行
var wg sync.WaitGroup
for i := 0; i < 5; i++ {
    go func() {
        wg.Add(1) // ❌ 这里 Add，可能 Wait 已经跑了，根本没等
        defer wg.Done()
        fmt.Println("hello")
    }()
}
wg.Wait() // 可能直接通过，没等任何 goroutine

// ✅ 正确：Add 必须在 go func() 之前
for i := 0; i < 5; i++ {
    wg.Add(1) // ✅ 在启动 goroutine 之前 Add
    go func() {
        defer wg.Done()
        fmt.Println("hello")
    }()
}
wg.Wait()
</code></pre>
</div>

<div class="card card-r">
<h3>⚠️ 坑点 5：向已关闭 channel 发送 panic / 多次 close panic</h3>
<p>这个在 channel 章节讲过，这里重申原则：<strong>谁创建 channel，谁关闭；谁发送，谁关闭</strong>。多个生产者时用 sync.Once 保证只关一次，或者用一个额外的 done channel 通知所有生产者退出，不要直接 close 任务 channel。</p>
<pre><code class="language-go">// 多生产者安全关闭示例
func main() {
    jobs := make(chan int)
    done := make(chan struct{})
    var once sync.Once

    // 消费者
    go func() {
        for v := range jobs {
            fmt.Println(v)
        }
        close(done)
    }()

    // 多个生产者
    var wg sync.WaitGroup
    for i := 0; i < 3; i++ {
        wg.Add(1)
        go func(n int) {
            defer wg.Done()
            for j := 0; j < 5; j++ {
                jobs <- n*10 + j
            }
        }(i)
    }

    go func() {
        wg.Wait()
        once.Do(func() { close(jobs) }) // 所有生产者完成后关一次
    }()

    <-done
}
</code></pre>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 怎么检测和排查 goroutine 泄漏？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从监控、工具、代码习惯三个层面说。</p>
<div class="qa-section">
<div class="qa-section-title">监控指标</div>
<p>用 <code>runtime.NumGoroutine()</code> 暴露 goroutine 数量到监控（Prometheus），正常服务 goroutine 数应该稳定，不应该持续增长。如果持续上涨基本就是泄漏了。pprof 的 goroutine profile 是核心排查手段。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">pprof 排查</div>
<p>导入 <code>_ "net/http/pprof"</code>，启动后访问：<br>
- <code>go tool pprof http://addr/debug/pprof/goroutine</code> 看所有 goroutine 栈<br>
- <code>curl http://addr/debug/pprof/goroutine?debug=2</code> 直接看所有 goroutine 调用栈<br>
重点看：哪些 goroutine 很多（成百上千相同栈）？卡在哪个 channel 接收/锁等待？栈会告诉你具体是哪行代码阻塞的。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">预防手段</div>
<p>1. 所有阻塞操作（HTTP、DB、RPC）都设超时，用 context 控制；<br>
2. 启动 goroutine 就要考虑它怎么退出，每个 go func() 都要有退出机制（ctx.Done() 或 done channel）；<br>
3. 不要在生产环境写裸的 <code>go func() { ... }</code> 不处理退出；<br>
4. 用 <code>go test -race</code> 测试并发代码（虽然它不直接查泄漏，但能发现 data race）；<br>
5. 有现成库：<code>github.com/uber-go/goleak</code> 可以在单元测试里检测 goroutine 泄漏，非常推荐。</p>
</div>
<div class="qa-summary">面试口径：监控 goroutine 数，涨了就是泄漏；pprof goroutine 看阻塞栈定位原因；预防上每个 goroutine 必须有退出路径，阻塞操作要有超时，测试用 goleak 验证。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Go 并发如何避免 data race？-race 检测原理是什么？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>data race 是多个 goroutine 并发访问同一个变量，至少一个是写。预防手段 + 检测工具。</p>
<div class="qa-section">
<div class="qa-section-title">什么是 data race</div>
<p>两个或更多 goroutine 并发访问同一个内存位置，且至少有一个是写操作，而且没有用任何同步机制（锁、channel、atomic），这就是 data race。data race 是未定义行为，可能出现各种诡异bug（读到撕裂值、panic、随机结果），不是每次都复现。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">怎么避免 data race</div>
<p>1. 不要在多个 goroutine 共享变量做写操作，优先通过 channel 传递数据所有权；<br>
2. 必须共享的话，用 sync.Mutex/RWMutex 保护读写临界区；<br>
3. 基本类型的原子操作用 sync/atomic（AddInt64、CompareAndSwap 等）；<br>
4. 不要在 goroutine 里直接改外部变量，要么传参要么加锁。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">go test -race 原理</div>
<p>开启 race detector 后，编译器会插桩，在每个内存读写前后记录访问时间、goroutine ID；运行时用 ThreadSanitizer 算法（矢量时钟）检测两个不同 goroutine 对同一地址的访问是否没有 happens-before 关系。性能开销：内存 5-10 倍，速度 2-20 倍慢，所以只在测试/预发布环境用，不要开在生产环境。<code>go run -race main.go</code> 也可以跑。</p>
</div>
<div class="qa-summary">面试口径：data race 是未定义行为，必须避免；预防是 channel 传所有权/Mutex 保护临界区/atomic 原子操作；检测用 go test -race（ThreadSanitizer 插桩），测试一定要开 -race。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Fan-in 和 Fan-out 模式是什么？适合什么场景？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>这是 pipeline 模式下两个常用的并行化手段。</p>
<div class="qa-section">
<div class="qa-section-title">Fan-Out（扇出）</div>
<p>一个 channel 的数据被多个 goroutine 并行读取处理，就是 fan-out。用于把 CPU/IO 密集型任务并行化，充分利用多核。比如一个阶段处理很慢，启动多个 worker 并行读同一个任务 channel。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">Fan-In（扇入）</div>
<p>把多个 channel 的结果合并到一个 channel，就是 fan-in。启动一个 goroutine 监听多个输入 channel，哪个有数据就收哪个，全部输入关闭了再关闭输出 channel。之前 merge 函数就是 fan-in 的实现。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">典型场景</div>
<p>比如下载图片：fan-out 启动 N 个 worker 并发下载（下载是 I/O 密集，适合多开）；下载后的结果 fan-in 到一个 channel，统一做后续处理（解码、保存）。这比一个 goroutine 串行下载快很多，同时也不会因为启动太多 goroutine 把资源打满。</p>
</div>
<div class="qa-summary">面试口径：Fan-out 是多个 worker 并行处理同一个输入 channel（并行计算），Fan-in 是合并多个输入 channel 的结果（结果汇聚），二者经常和 Pipeline 模式组合用，处理并行任务。</div>
</div>
</div>

## 关联模块

- `Channel 与并发同步`：channel 基础语义、select、context 是并发模式的基础
- `GMP 调度模型`：goroutine 泄漏和调度关系
- `Go 工程实践`：pprof 性能分析、race detector、单元测试
