<div class="card card-m">
<h3>CPU Core、进程与线程</h3>
<p>这组问题的核心是：并行度不是越大越好。真正的吞吐取决于 CPU core、内存带宽、锁竞争、I/O 等共享资源是否还能支撑更多并发。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么可能出现 parallel 越大、线程越多，运行越慢/吞吐越小的状况？</div>
<div class="qa-a">
<p>因为线程数增加只代表“可调度实体”变多，不代表硬件资源变多。当线程数超过 CPU core 数或共享资源瓶颈时，额外线程会带来调度和竞争成本，吞吐反而下降。</p>
<table>
<tr><th>原因</th><th>表现</th><th>例子</th></tr>
<tr><td>上下文切换</td><td>CPU 时间花在保存/恢复寄存器、调度队列切换上</td><td>16 核机器跑 256 个 CPU 密集线程</td></tr>
<tr><td>锁竞争</td><td>线程越多，等待 mutex、队列锁、allocator lock 的时间越长</td><td>多线程同时写同一个队列或日志</td></tr>
<tr><td>缓存失效</td><td>不同 core 修改同一 cache line，导致 cache coherence 流量上升</td><td>多个线程更新相邻计数器，引发 false sharing</td></tr>
<tr><td>内存带宽瓶颈</td><td>CPU core 空转等待内存，线程再多也无法提升吞吐</td><td>数据预处理、memcpy、特征读取</td></tr>
<tr><td>I/O 或下游瓶颈</td><td>并发请求堆积在磁盘、网络、数据库、RPC 下游</td><td>并发下载数据但网卡已打满</td></tr>
<tr><td>NUMA 远端访问</td><td>线程跨 socket 访问远端内存，延迟变高</td><td>进程绑在 NUMA0，却大量访问 NUMA1 内存</td></tr>
</table>
<p>排查时可以看 <code>top/htop</code>、<code>pidstat -w</code>、<code>perf top</code>、<code>vmstat</code>、<code>iostat</code>、<code>numastat</code>。面试回答可以总结为：并行度存在最优点，超过硬件和共享资源承载能力后，边际收益会变成负数。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 进程号是什么？进程名是什么？</div>
<div class="qa-a">
<p><strong>进程号</strong>是 PID（Process ID），是 Linux 内核给每个进程分配的数字标识，用于调度、信号发送、资源统计和父子进程管理。PID 在同一 PID namespace 内唯一，容器里看到的 PID 可能和宿主机不同。</p>
<p><strong>进程名</strong>通常是用户态看到的命令名或可执行文件名，例如 <code>python</code>、<code>runner</code>、<code>java</code>。进程名不要求唯一，多个进程可以有同一个名字。</p>
<table>
<tr><th>字段</th><th>唯一性</th><th>用途</th></tr>
<tr><td>PID</td><td>同一 PID namespace 内唯一</td><td>精准定位和操作进程，例如 <code>kill 1234</code></td></tr>
<tr><td>进程名</td><td>不唯一</td><td>人类识别进程类型，例如搜索所有 <code>runner</code></td></tr>
<tr><td>命令行</td><td>不唯一但信息更完整</td><td>区分同名进程的参数、脚本和工作模式</td></tr>
</table>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 在 Linux 系统中，如何查看某个包含“runner”字符串的进程的进程号？</div>
<div class="qa-a">
<p>常用命令有三类：按完整命令行搜、按进程名搜、用 <code>ps</code> 自己过滤。</p>
<pre><code class="language-bash"># 推荐：按完整命令行匹配，输出 PID 和命令
pgrep -af runner

# 只输出 PID
pgrep -f runner

# 通用写法，注意 [r]unner 避免 grep 自己也被匹配
ps -ef | grep '[r]unner'

# 只提取 PID
ps -ef | awk '/[r]unner/ {print $2}'</code></pre>
<p>如果在容器里排查，要注意 PID namespace：容器内 PID 与宿主机 PID 可能不同；在 Kubernetes 中还可以先 <code>kubectl exec</code> 进容器，再执行这些命令。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 在 Linux 系统中，如何 kill 掉某个进程？</div>
<div class="qa-a">
<p>本质是给进程发送 signal。默认 <code>kill PID</code> 发送 <code>SIGTERM</code>，请求进程优雅退出；如果进程不响应，再用 <code>SIGKILL</code> 强制杀掉。</p>
<pre><code class="language-bash"># 优雅终止
kill 1234
kill -TERM 1234

# 强制终止，不可被捕获或忽略
kill -9 1234
kill -KILL 1234

# 按名称杀进程，谨慎使用
pkill -f runner

# 先确认再杀
pgrep -af runner
kill &lt;pid&gt;</code></pre>
<p>生产环境建议先发 <code>SIGTERM</code>，给服务保存状态、flush 日志、释放锁和临时文件的机会。<code>SIGKILL</code> 虽然立即生效，但可能留下不一致状态。</p>
</div>
</div>

<div class="card card-s">
<h3>内存、OOM 与 NUMA</h3>
<p>内存问题不能只看“总量是否够”。还要看 cgroup 限制、GPU 显存、NUMA locality、page cache、swap、内存带宽和碎片。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: OOM 是什么意思？CUDA OOM 是什么意思？有什么区别？</div>
<div class="qa-a">
<p><strong>OOM</strong> 是 Out Of Memory，通常指系统内存或 cgroup 内存不足。Linux 可能触发 OOM Killer 杀掉进程，Kubernetes 中常表现为 Pod 状态 <code>OOMKilled</code>。</p>
<p><strong>CUDA OOM</strong> 指 NVIDIA GPU 显存不足，CUDA runtime 或深度学习框架申请 GPU memory 失败，常见报错是 <code>CUDA out of memory</code>。它通常不会由 Linux OOM Killer 直接处理，而是在程序里抛异常或报错退出。</p>
<table>
<tr><th>维度</th><th>系统 OOM</th><th>CUDA OOM</th></tr>
<tr><td>资源</td><td>CPU 内存 / cgroup memory</td><td>GPU 显存 HBM</td></tr>
<tr><td>触发方</td><td>Linux kernel / cgroup</td><td>CUDA runtime / driver / 框架 allocator</td></tr>
<tr><td>现象</td><td>进程被杀，Pod <code>OOMKilled</code></td><td>程序报 <code>CUDA out of memory</code></td></tr>
<tr><td>排查</td><td><code>dmesg</code>、<code>kubectl describe pod</code>、cgroup memory</td><td><code>nvidia-smi</code>、框架显存统计、batch size</td></tr>
<tr><td>解决</td><td>增大 memory limit、减少进程内存、控制 page cache</td><td>减小 batch/seq len、释放 cache、模型并行/量化/checkpoint</td></tr>
</table>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 在你的电脑/开发机上 <code>free -h</code>，输出的结果如何解释？</div>
<div class="qa-a">
<p><code>free -h</code> 展示系统内存概况，重点不要只看 <code>free</code>，更应该看 <code>available</code>。</p>
<pre><code class="language-text">              total        used        free      shared  buff/cache   available
Mem:           125G         40G         10G          1G         75G         82G
Swap:            0B          0B          0B</code></pre>
<table>
<tr><th>字段</th><th>含义</th><th>怎么看</th></tr>
<tr><td>total</td><td>总内存</td><td>机器或容器可见的总量</td></tr>
<tr><td>used</td><td>已使用内存</td><td>包括进程使用和部分内核占用，不等于“不可回收”</td></tr>
<tr><td>free</td><td>完全空闲内存</td><td>通常很小，不代表内存紧张</td></tr>
<tr><td>buff/cache</td><td>buffer 和 page cache</td><td>用于加速文件 I/O，内存紧张时大多可回收</td></tr>
<tr><td>available</td><td>估算还能给新程序使用的内存</td><td>判断是否真的缺内存时优先看这个</td></tr>
<tr><td>swap</td><td>交换分区使用情况</td><td>大量 swap in/out 会显著降速</td></tr>
</table>
<p>在容器中，<code>free -h</code> 有时显示宿主机视角，不一定等于 Pod cgroup limit。Kubernetes 排查时还要看 <code>kubectl describe pod</code>、容器 memory limit 和 cgroup 文件。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 内存只用了 1/10，还有什么其他内存原因可能导致降速吗？</div>
<div class="qa-a">
<p>会。内存“容量”没用完，不代表内存系统没有瓶颈。常见原因包括：</p>
<table>
<tr><th>原因</th><th>为什么会慢</th><th>排查工具</th></tr>
<tr><td>内存带宽打满</td><td>多线程都在读写大数组，CPU 等内存返回</td><td><code>perf</code>、硬件 PMU、<code>pcm-memory</code></td></tr>
<tr><td>NUMA 远端访问</td><td>跨 socket 访问远端内存，延迟和带宽都变差</td><td><code>numastat</code>、<code>numactl -H</code></td></tr>
<tr><td>page fault</td><td>缺页中断频繁，CPU 陷入内核处理页表/磁盘加载</td><td><code>vmstat</code>、<code>perf stat</code></td></tr>
<tr><td>swap 抖动</td><td>热数据被换到磁盘，访问延迟从 ns/us 变成 ms</td><td><code>vmstat si/so</code>、<code>free -h</code></td></tr>
<tr><td>透明大页/碎片</td><td>THP collapse 或内存碎片导致延迟毛刺</td><td><code>/sys/kernel/mm/transparent_hugepage</code></td></tr>
<tr><td>page cache 争抢</td><td>大量文件 I/O 冲掉缓存，训练数据加载变慢</td><td><code>iostat</code>、<code>vmtouch</code></td></tr>
</table>
<p>面试回答：容量、带宽、延迟、局部性和回收机制是不同维度；“只用了 1/10”只能说明容量暂时不紧张，不能排除内存带宽和 NUMA 问题。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: NUMA 的全称是什么，为什么要存在 NUMA 架构？</div>
<div class="qa-a">
<p>NUMA 全称是 Non-Uniform Memory Access，非一致内存访问。它存在的原因是多路 CPU 服务器中，如果所有 CPU 都通过单一总线访问同一内存控制器，会形成严重瓶颈。NUMA 让每个 CPU socket 拥有自己的本地内存控制器和本地内存，同时允许跨 socket 访问远端内存。</p>
<table>
<tr><th>访问类型</th><th>特点</th></tr>
<tr><td>本地内存访问</td><td>CPU 访问自己 NUMA node 下的内存，延迟低、带宽高</td></tr>
<tr><td>远端内存访问</td><td>CPU 通过 UPI/Infinity Fabric 等互联访问其他 socket 的内存，延迟更高、带宽更低</td></tr>
</table>
<p>NUMA 的目标是在大内存、多 CPU 服务器中提升可扩展性，但代价是软件需要关注 CPU 绑核、内存绑定、GPU/NIC locality。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: NUMA 架构下，为什么进程没有用完机器所有内存就 OOM 了？</div>
<div class="qa-a">
<p>因为“机器总内存没用完”和“当前进程可用的本地/受限内存没用完”不是一回事。可能原因包括：</p>
<table>
<tr><th>原因</th><th>解释</th></tr>
<tr><td>NUMA policy 限制</td><td>进程被 <code>numactl --membind</code> 或 cpuset mems 限制只能使用部分 NUMA node</td></tr>
<tr><td>cgroup 限制</td><td>容器/Pod memory limit 小于宿主机总内存</td></tr>
<tr><td>本地 node 内存耗尽</td><td>策略要求本地分配，远端 node 虽有空闲但不能或不愿 fallback</td></tr>
<tr><td>内存碎片</td><td>总空闲足够，但无法满足大块连续页或 hugepage 分配</td></tr>
<tr><td>hugepage 独立池</td><td>普通内存空闲不代表 hugepage 池可用</td></tr>
</table>
<pre><code class="language-bash">numactl -H
numastat -p &lt;pid&gt;
cat /proc/&lt;pid&gt;/status | grep -E 'Mems_allowed|Cpus_allowed'
cat /sys/fs/cgroup/memory.max 2>/dev/null || true</code></pre>
</div>
</div>

<div class="card card-d">
<h3>stdin/stdout/stderr 与日志</h3>
<p>标准流用于把程序输入、正常输出和错误输出分离，便于 shell 重定向、日志采集和故障排查。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Shell 的屏幕上输出的是 stdout 还是 stderr？</div>
<div class="qa-a">
<p>默认情况下，stdout 和 stderr 都连接到当前终端，所以屏幕上看到的可能两者都有。区别在于文件描述符：stdout 是 fd 1，stderr 是 fd 2。</p>
<pre><code class="language-bash"># 只把 stdout 写入 out.txt，stderr 仍显示在屏幕
cmd > out.txt

# 只把 stderr 写入 err.txt，stdout 仍显示在屏幕
cmd 2> err.txt

# stdout 和 stderr 都写入 all.log
cmd > all.log 2>&1

# 丢弃 stderr
cmd 2>/dev/null</code></pre>
<p>很多命令会把正常结果写 stdout，把进度、warning、error 写 stderr。这样 stdout 可以安全地被管道消费，例如 <code>cmd | jq</code>，不会被错误日志污染。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: glog 默认的输出打到哪里？为什么？</div>
<div class="qa-a">
<p>Google glog 的默认行为通常是把日志写到日志文件，同时较高严重级别日志会输出到 stderr；具体行为受启动参数影响，例如 <code>--logtostderr</code>、<code>--alsologtostderr</code>、<code>--stderrthreshold</code>、<code>--log_dir</code>。</p>
<table>
<tr><th>参数</th><th>作用</th></tr>
<tr><td><code>--logtostderr=1</code></td><td>所有日志只打到 stderr，不写文件</td></tr>
<tr><td><code>--alsologtostderr=1</code></td><td>写文件的同时也打到 stderr</td></tr>
<tr><td><code>--stderrthreshold=ERROR</code></td><td>达到 ERROR 及以上的日志额外打到 stderr</td></tr>
<tr><td><code>--log_dir=/path</code></td><td>指定日志文件目录</td></tr>
</table>
<p>为什么要这样设计：文件日志适合长期保存和按级别切分，stderr 适合容器、systemd、Kubernetes 等运行环境统一采集进标准日志系统。</p>
</div>
</div>

<div class="card card-w">
<h3>Signal</h3>
<p>Signal 是 Linux 进程间和内核到进程的异步通知机制，用于终止、暂停、恢复、用户中断、非法访问、计时器等场景。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Linux 系统中有哪些最常用的 Signal？Signal 的存在意义是什么？</div>
<div class="qa-a">
<table>
<tr><th>Signal</th><th>常见来源</th><th>含义</th></tr>
<tr><td><code>SIGTERM</code></td><td><code>kill PID</code>、K8s 删除 Pod</td><td>请求进程优雅终止，可捕获</td></tr>
<tr><td><code>SIGKILL</code></td><td><code>kill -9 PID</code></td><td>强制杀死，不可捕获</td></tr>
<tr><td><code>SIGINT</code></td><td>终端 <code>Ctrl+C</code></td><td>用户中断</td></tr>
<tr><td><code>SIGHUP</code></td><td>终端断开、reload 约定</td><td>挂起或重载配置</td></tr>
<tr><td><code>SIGSTOP</code></td><td><code>kill -STOP</code></td><td>暂停进程，不可捕获</td></tr>
<tr><td><code>SIGCONT</code></td><td><code>kill -CONT</code></td><td>继续运行暂停进程</td></tr>
<tr><td><code>SIGSEGV</code></td><td>非法内存访问</td><td>段错误，通常生成 core dump</td></tr>
<tr><td><code>SIGABRT</code></td><td><code>abort()</code></td><td>进程主动异常退出</td></tr>
<tr><td><code>SIGPIPE</code></td><td>管道读端关闭后继续写</td><td>写 broken pipe</td></tr>
</table>
<p>Signal 的意义是提供轻量异步控制通道，不需要进程主动轮询，就能被外部或内核通知发生了重要事件。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 哪些 Signal 是从进程外部触发的，哪些 Signal 是进程内部触发的？</div>
<div class="qa-a">
<table>
<tr><th>类型</th><th>例子</th><th>说明</th></tr>
<tr><td>外部触发</td><td><code>SIGTERM</code>、<code>SIGKILL</code>、<code>SIGINT</code>、<code>SIGHUP</code>、<code>SIGSTOP</code>、<code>SIGCONT</code></td><td>来自用户、shell、其他进程、Kubernetes、systemd 等</td></tr>
<tr><td>内部/异常触发</td><td><code>SIGSEGV</code>、<code>SIGFPE</code>、<code>SIGILL</code>、<code>SIGABRT</code>、<code>SIGBUS</code></td><td>来自当前进程执行错误、主动 abort 或硬件异常</td></tr>
<tr><td>内核事件触发</td><td><code>SIGPIPE</code>、<code>SIGALRM</code>、<code>SIGCHLD</code></td><td>由内核根据管道、定时器、子进程状态变化发送</td></tr>
</table>
<p>严格来说，signal 都由内核投递；这里的“外部/内部”是按根因划分。</p>
</div>
</div>

<div class="card card-m">
<h3>网络：TCP RPC 与 RDMA</h3>
<p>AI Infra 中网络不仅影响 RPC 延迟，也影响参数同步、数据加载和分布式训练通信效率。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 使用 TCP 的 RPC 请求可能在什么地方消耗 CPU？使用 RDMA 可能会有什么改进？</div>
<div class="qa-a">
<p>TCP RPC 的 CPU 开销来自协议栈、拷贝、序列化、系统调用和中断处理等多个环节。</p>
<table>
<tr><th>环节</th><th>CPU 开销来源</th></tr>
<tr><td>用户态序列化</td><td>Protobuf/Thrift 编解码、压缩、校验</td></tr>
<tr><td>系统调用</td><td><code>send/recv</code> 进入内核，用户态/内核态切换</td></tr>
<tr><td>内核协议栈</td><td>TCP 分片重组、拥塞控制、ACK、重传、checksum</td></tr>
<tr><td>内存拷贝</td><td>用户 buffer 到 kernel buffer，再到 NIC DMA buffer</td></tr>
<tr><td>中断和软中断</td><td>网卡收包、NAPI poll、softirq 处理</td></tr>
</table>
<p>RDMA 的改进是让网卡直接读写远端内存，绕过大部分内核协议栈和多次拷贝，降低 CPU 占用和延迟，提高吞吐。代价是编程模型更复杂，需要注册内存、管理 queue pair、处理可靠性和网络配置。</p>
<p>一句话：TCP RPC 更通用，CPU 参与更多；RDMA 更接近“网卡直接搬内存”，适合高吞吐低延迟通信。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 给出一个 shell，用什么命令查看该 Pod 上是否有 RDMA（硬件 & 软件）支持？</div>
<div class="qa-a">
<p>可以同时检查设备文件、PCI 设备、内核模块、RDMA link 和用户态工具。</p>
<pre><code class="language-bash">#!/usr/bin/env bash
set -e

echo "== RDMA device files =="
ls -l /dev/infiniband 2>/dev/null || echo "no /dev/infiniband"

echo "== RDMA links =="
if command -v rdma >/dev/null 2>&1; then
  rdma link show || true
else
  echo "rdma command not found"
fi

echo "== InfiniBand devices =="
if command -v ibv_devinfo >/dev/null 2>&1; then
  ibv_devinfo || true
else
  echo "ibv_devinfo not found"
fi

echo "== PCI devices =="
lspci 2>/dev/null | grep -Ei 'mellanox|infiniband|ethernet controller' || true

echo "== Kernel modules =="
lsmod 2>/dev/null | grep -E 'mlx5|ib_uverbs|rdma_ucm' || true</code></pre>
<p>在 Kubernetes Pod 中，如果没有挂载 <code>/dev/infiniband</code> 或没有相应 device plugin / CNI / capability，即使宿主机有 RDMA，容器内也可能不可见。</p>
</div>
</div>
