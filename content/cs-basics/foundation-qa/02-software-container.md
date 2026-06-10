<div class="card card-m">
<h3>环境变量</h3>
<p>环境变量是进程启动时从父进程继承的一组 key-value 配置。它常用于传递路径、运行模式、认证配置、代理、动态库搜索路径等。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 在 Linux 系统中，哪条 shell 命令可以查看所有的环境变量？</div>
<div class="qa-a">
<p>最常用的是 <code>env</code> 或 <code>printenv</code>。</p>
<pre><code class="language-bash"># 查看当前 shell 进程环境变量
env
printenv

# 查看某个变量
echo "$PATH"
printenv PATH

# 查看某个进程的环境变量，注意 NUL 分隔
tr '\0' '\n' &lt; /proc/&lt;pid&gt;/environ</code></pre>
<p><code>set</code> 会显示 shell 变量、函数和环境变量，范围更大；<code>env</code>/<code>printenv</code> 更适合回答“环境变量”。</p>
<table>
<tr><th>命令</th><th>范围</th><th>场景</th></tr>
<tr><td><code>env</code></td><td>环境变量</td><td>查看当前进程启动子进程时会继承的变量</td></tr>
<tr><td><code>printenv</code></td><td>环境变量</td><td>查看全部或某个指定变量</td></tr>
<tr><td><code>set</code></td><td>shell 变量 + 函数 + 环境变量</td><td>调试 shell 脚本</td></tr>
<tr><td><code>export KEY=VALUE</code></td><td>设置并导出</td><td>让子进程继承变量</td></tr>
</table>
</div>
</div>

<div class="card card-s">
<h3>Binary、编译与工具链</h3>
<p>原文这两节只列了“思考题”标题，没有给出具体问题。这里补一组面试中常被追问的基础答案，帮助建立上下文。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Binary 通常指什么？运行一个 binary 时系统做了什么？</div>
<div class="qa-a">
<p>Binary 通常指编译后的可执行文件或库文件，例如 Linux 下的 ELF executable、<code>.so</code> 动态库。运行 binary 时，shell 会调用 <code>execve</code>，内核读取 ELF header，建立虚拟地址空间，加载代码段/数据段，设置栈和环境变量，再跳转到入口点。</p>
<table>
<tr><th>阶段</th><th>说明</th></tr>
<tr><td>解析格式</td><td>内核识别 ELF、解释器路径、程序头</td></tr>
<tr><td>加载映射</td><td>把代码段、数据段、动态链接器 mmap 到进程地址空间</td></tr>
<tr><td>动态链接</td><td>加载依赖的 <code>.so</code>，解析符号和重定位</td></tr>
<tr><td>启动运行</td><td>执行运行时初始化，再进入 <code>main</code></td></tr>
</table>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 编译和工具链通常包含哪些环节？</div>
<div class="qa-a">
<p>C/C++ 常见工具链链路是：预处理、编译、汇编、链接。</p>
<pre><code class="language-bash"># 预处理：展开 include、宏
gcc -E main.c -o main.i

# 编译：C/C++ 到汇编
gcc -S main.i -o main.s

# 汇编：汇编到目标文件
gcc -c main.s -o main.o

# 链接：目标文件和库合成可执行文件
gcc main.o -o main</code></pre>
<p>排查 binary 问题常用 <code>ldd</code> 看动态库依赖，<code>nm</code> 看符号，<code>readelf</code>/<code>objdump</code> 看 ELF 结构，<code>file</code> 看文件类型。</p>
</div>
</div>

<div class="card card-d">
<h3>Docker 与 Kubernetes</h3>
<p>Docker 解决“应用和依赖如何打包并隔离运行”，Kubernetes 解决“大量容器如何在集群中调度、编排、扩缩容、发现和自愈”。理解容器时不要只记“轻量级虚拟化”，更要能说清楚：<strong>namespace 负责视图隔离，cgroup 负责资源限制，rootfs/镜像负责文件系统环境，容器运行时负责把这些能力组合起来。</strong></p>
</div>

<div class="card card-s">
<h3>容器隔离三件套：namespace、cgroup、rootfs</h3>
<p>容器不是一台真正的虚拟机，它本质上还是宿主机上的进程。这个进程之所以“看起来像在一台独立机器里”，是因为 Linux 内核给它换了一套资源视图，并限制了它能使用的资源。</p>
<table>
<tr><th>机制</th><th>解决的问题</th><th>容器里的直观表现</th><th>面试口径</th></tr>
<tr><td>namespace</td><td>隔离“能看到什么”</td><td>容器内看到自己的 PID、网卡、hostname、挂载点</td><td>让进程拥有隔离视图</td></tr>
<tr><td>cgroup</td><td>限制“能用多少”</td><td>CPU、内存、PID、IO、设备访问被限制和统计</td><td>让进程不能无限消耗宿主机资源</td></tr>
<tr><td>rootfs / image</td><td>提供“运行时文件系统”</td><td>容器内有自己的 <code>/bin</code>、<code>/lib</code>、Python 包、CUDA 库</td><td>让应用依赖可复制、可分发</td></tr>
<tr><td>container runtime</td><td>把上述能力组装成容器</td><td>拉镜像、创建容器、配置网络和挂载、启动进程</td><td>Docker/containerd/CRI-O 等负责落地执行</td></tr>
</table>
<div class="qa-summary">一句话：namespace 让容器“看起来隔离”，cgroup 让容器“资源受控”，rootfs 让容器“环境可复现”。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Linux namespace 是什么？Docker/K8s 常用哪些 namespace？</div>
<div class="qa-a">
<p>namespace 是 Linux 内核提供的资源视图隔离机制。不同 namespace 中的进程看到的系统资源不同，因此容器进程会觉得自己有独立的进程树、网络栈、hostname、挂载点等。</p>
<table>
<tr><th>namespace</th><th>隔离对象</th><th>容器中的表现</th><th>常见排查点</th></tr>
<tr><td>PID namespace</td><td>进程号空间</td><td>容器内主进程通常是 PID 1</td><td>容器内 PID 与宿主机 PID 不同</td></tr>
<tr><td>NET namespace</td><td>网络设备、IP、路由、端口</td><td>Pod 有自己的网卡、IP、路由表</td><td><code>ip addr</code>、端口监听、CNI 问题</td></tr>
<tr><td>MNT namespace</td><td>挂载点视图</td><td>容器内看到独立的根文件系统和 volume</td><td>volume 是否挂载、路径是否一致</td></tr>
<tr><td>UTS namespace</td><td>hostname、domain name</td><td>容器可拥有自己的 hostname</td><td>服务发现和日志标识</td></tr>
<tr><td>IPC namespace</td><td>System V IPC、POSIX message queue</td><td>隔离共享内存、信号量等 IPC 资源</td><td>多进程通信、共享内存</td></tr>
<tr><td>USER namespace</td><td>用户和用户组 ID 映射</td><td>容器内 root 可映射为宿主机非 root</td><td>权限隔离、安全加固</td></tr>
<tr><td>TIME namespace</td><td>部分时间视图</td><td>可隔离 monotonic/boottime offset</td><td>较少见，和时间相关测试有关</td></tr>
</table>
<p>在 Kubernetes 中，同一个 Pod 内的容器通常共享 network namespace，所以它们可以通过 <code>localhost</code> 互相访问；但它们一般有各自的 mount namespace 和进程视图，具体还受 <code>shareProcessNamespace</code> 等配置影响。</p>
<div class="qa-summary">面试口径：namespace 解决隔离视图问题；Pod 不是一组完全无关的容器，而是一组共享部分 namespace 和资源上下文的容器集合。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: cgroup 到底限制了什么？cgroup v1 和 v2 有什么直观区别？</div>
<div class="qa-a">
<p>cgroup 是 Linux Control Groups，用于对一组进程做资源限制、优先级控制和用量统计。容器平台会把容器进程放入特定 cgroup，再通过 cgroup 文件系统配置 CPU、内存、IO、PID、设备等控制规则。</p>
<table>
<tr><th>控制器</th><th>解决的问题</th><th>K8s/Docker 中的体现</th></tr>
<tr><td>cpu</td><td>限制 CPU 时间片或设置相对权重</td><td>CPU limit、CPU request 对应的调度权重</td></tr>
<tr><td>cpuset</td><td>限制可运行的 CPU core 和可用 NUMA node</td><td>绑核、NUMA locality、独占 CPU</td></tr>
<tr><td>memory</td><td>限制内存、统计 usage、触发 OOM</td><td>memory limit、Pod OOMKilled</td></tr>
<tr><td>io / blkio</td><td>限制块设备 IO 或设置权重</td><td>磁盘读写隔离，防止单任务打爆磁盘</td></tr>
<tr><td>pids</td><td>限制进程/线程数量</td><td>防止 fork bomb 或线程数失控</td></tr>
<tr><td>devices</td><td>控制设备文件访问</td><td>容器是否能访问 GPU、RDMA、磁盘设备</td></tr>
</table>
<p><strong>cgroup v1</strong> 是多 hierarchy 模型，不同 controller 可以挂在不同层级；<strong>cgroup v2</strong> 是统一 hierarchy 模型，资源控制更一致，文件名也不同。例如 v1 常见 <code>memory.usage_in_bytes</code>，v2 常见 <code>memory.current</code>、<code>memory.max</code>。</p>
<pre><code class="language-bash"># 查看当前进程所在 cgroup
cat /proc/self/cgroup

# cgroup v2 常见内存文件
cat /sys/fs/cgroup/memory.current 2>/dev/null
cat /sys/fs/cgroup/memory.max 2>/dev/null

# cgroup v1 常见内存文件
cat /sys/fs/cgroup/memory/memory.usage_in_bytes 2>/dev/null
cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null</code></pre>
<div class="qa-summary">面试口径：namespace 管“看见什么”，cgroup 管“能用多少”；v2 相比 v1 更强调统一层级和一致语义。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Kubernetes 的 request / limit 和 cgroup 是什么关系？为什么 Pod 会 OOMKilled？</div>
<div class="qa-a">
<p>Kubernetes 中，<code>requests</code> 主要用于调度和资源预留，<code>limits</code> 主要用于运行时限制。Pod 被调度到某个节点后，kubelet 会通过容器运行时创建容器，并把 CPU、memory 等限制写入对应 cgroup。</p>
<table>
<tr><th>K8s 字段</th><th>主要作用</th><th>落到运行时后大致体现</th></tr>
<tr><td><code>resources.requests.cpu</code></td><td>调度时计算节点是否放得下；运行时设置相对权重</td><td>CPU shares / weight</td></tr>
<tr><td><code>resources.limits.cpu</code></td><td>限制容器最多能用多少 CPU 时间</td><td>CPU quota / period</td></tr>
<tr><td><code>resources.requests.memory</code></td><td>调度时计算内存预留；影响 QoS</td><td>不等于硬限制</td></tr>
<tr><td><code>resources.limits.memory</code></td><td>限制容器最多能用多少内存</td><td>memory.max / memory.limit_in_bytes</td></tr>
</table>
<p>当容器内进程申请内存导致 cgroup memory 使用超过 limit 时，内核会在该 cgroup 内选择进程杀掉，Kubernetes 观察到容器退出原因后显示为 <code>OOMKilled</code>。注意：这和整机 OOM 不完全一样，哪怕宿主机还有空闲内存，容器也可能因为自己的 cgroup limit 被杀。</p>
<p>CPU limit 通常表现为 throttling，即被限速而不是被杀；memory limit 则可能触发 OOMKilled，这是二者最重要的差别之一。</p>
<div class="qa-summary">面试口径：request 决定“能不能调度、调度时算多少”，limit 决定“运行时最多能用多少”；memory 超 limit 会 OOMKilled，CPU 超 limit 多数是 throttling。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 大规模计算资源系统中，为什么要使用 Docker 和 K8s？用形象语言比喻一下，它们分别解决了什么问题？</div>
<div class="qa-a">
<p>可以用“集装箱”和“港口调度系统”来类比。</p>
<table>
<tr><th>系统</th><th>比喻</th><th>解决的问题</th></tr>
<tr><td>Docker</td><td>标准化集装箱</td><td>把应用、依赖、运行环境打成统一镜像，减少“我机器上能跑”的问题</td></tr>
<tr><td>Kubernetes</td><td>港口/物流调度系统</td><td>决定集装箱放哪台机器、如何重启、扩缩容、服务发现、滚动发布</td></tr>
</table>
<p>在大规模计算资源系统中，如果没有 Docker，每个任务都要手工配置 Python/CUDA/动态库/系统依赖，环境不可复现；如果没有 K8s，就需要人工决定任务跑在哪台机器、失败后谁拉起、资源如何隔离、服务如何发现。</p>
<p>更具体地说：</p>
<ul>
<li>Docker 提供镜像、容器隔离、依赖封装和可复现运行环境。</li>
<li>K8s 提供调度、资源声明、健康检查、控制器、自愈、Service、Secret/ConfigMap、滚动升级。</li>
<li>AI Infra 里，K8s 还负责 GPU 扩展资源、队列、Gang Scheduling、训练/推理工作负载管理等上层能力。</li>
</ul>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: K8s/Docker 的内存监控中，rss 和 usage 分别是什么？GPU 机器上，它们分别可能包括通过什么途径分配的内存？</div>
<div class="qa-a">
<p><strong>RSS</strong> 是 Resident Set Size，表示进程当前驻留在物理内存中的匿名页和文件映射页的一部分。它更接近“进程实际占用的物理内存”。</p>
<p><strong>Usage</strong> 在容器/cgroup 语境下通常指 cgroup 统计的内存使用量，范围比单进程 RSS 更大，可能包括多个进程、page cache、slab、tmpfs 等。</p>
<table>
<tr><th>指标</th><th>常见来源</th><th>可能包含</th></tr>
<tr><td>RSS</td><td><code>ps</code>、<code>top</code>、<code>/proc/&lt;pid&gt;/status</code></td><td>heap、stack、匿名 mmap、部分文件 mmap、部分共享库驻留页</td></tr>
<tr><td>cgroup usage</td><td><code>memory.current</code>、cAdvisor、container runtime</td><td>容器内所有进程 RSS、page cache、tmpfs、部分 kernel memory</td></tr>
<tr><td>working set</td><td>K8s/cAdvisor 常见展示</td><td>usage 减去一部分可回收 inactive file，更接近活跃内存</td></tr>
</table>
<p>GPU 机器上需要区分 CPU 内存和 GPU 显存：</p>
<ul>
<li>CPU 内存：Python 对象、DataLoader worker、预处理 buffer、mmap 数据集、page cache、pinned memory、NCCL/通信库 host buffer。</li>
<li>GPU 显存：模型权重、optimizer state、activation、KV cache、CUDA context、cuBLAS/cuDNN workspace、framework caching allocator 保留的显存。</li>
<li>Pinned memory 属于 CPU 内存，但用于加速 CPU-GPU DMA 拷贝，可能推高 RSS 或 cgroup usage。</li>
<li>GPU 显存通常看 <code>nvidia-smi</code>、DCGM 或框架 API，不应简单等同于容器 memory usage。</li>
</ul>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 从 Kubernetes 创建 Pod 到容器进程启动，中间大致发生了什么？</div>
<div class="qa-a">
<p>这条链路能把 K8s、容器运行时、namespace、cgroup 串起来。用户提交 Pod 后，Scheduler 只负责把 Pod 绑定到某个 Node；真正创建容器的是该 Node 上的 kubelet。</p>
<table>
<tr><th>阶段</th><th>主要组件</th><th>做什么</th></tr>
<tr><td>1. 调度</td><td>kube-scheduler</td><td>根据 request、亲和性、污点容忍、资源插件等选择节点</td></tr>
<tr><td>2. 下发</td><td>kubelet</td><td>watch 到分配给本节点的 Pod，准备启动容器</td></tr>
<tr><td>3. 创建 sandbox</td><td>CRI runtime</td><td>创建 Pod sandbox，通常先准备 pause 容器和 Pod 网络 namespace</td></tr>
<tr><td>4. 配置网络</td><td>CNI plugin</td><td>给 Pod 分配 IP、创建 veth、写路由和 iptables/eBPF 规则</td></tr>
<tr><td>5. 拉镜像</td><td>containerd / CRI-O</td><td>拉取镜像，解压层，准备 rootfs</td></tr>
<tr><td>6. 创建容器</td><td>OCI runtime，例如 runc</td><td>设置 namespace、cgroup、mount、capability、seccomp，最后 exec 用户进程</td></tr>
<tr><td>7. 持续管理</td><td>kubelet</td><td>执行 probe、上报状态、重启失败容器、采集日志和资源指标</td></tr>
</table>
<p>Pod 内多个容器通常共享同一个 network namespace，因此共享 IP 和端口空间；这也是为什么同一个 Pod 内两个容器不能监听同一个端口。</p>
<div class="qa-summary">面试口径：Scheduler 只决定 Pod 去哪台机器；kubelet 通过 CRI 调 runtime；runtime 再通过 OCI/runc 等机制配置 namespace、cgroup、rootfs 并启动容器进程。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Kubernetes QoS 是什么？它和 request / limit / OOM 优先级有什么关系？</div>
<div class="qa-a">
<p>Kubernetes 会根据容器是否设置 CPU/Memory request 和 limit，把 Pod 分成 Guaranteed、Burstable、BestEffort 三类 QoS。QoS 会影响节点资源紧张时的驱逐顺序和 OOM 选择倾向。</p>
<table>
<tr><th>QoS 类型</th><th>条件</th><th>资源紧张时的风险</th><th>适合场景</th></tr>
<tr><td>Guaranteed</td><td>每个容器都设置 CPU/Memory request 和 limit，且 request=limit</td><td>相对最不容易被驱逐</td><td>核心服务、关键训练控制面</td></tr>
<tr><td>Burstable</td><td>至少一个容器设置了 request，但不满足 Guaranteed</td><td>中等风险，超过 request 越多越危险</td><td>大多数在线服务和训练任务</td></tr>
<tr><td>BestEffort</td><td>没有设置 request 和 limit</td><td>最容易被驱逐或在资源竞争中受影响</td><td>临时调试、低优先级任务</td></tr>
</table>
<p>注意 QoS 不是简单等于 cgroup limit。limit 决定容器自己的硬上限；QoS 更多影响节点整体资源压力下，谁更可能先被驱逐或被 OOM 选中。</p>
<div class="qa-summary">面试口径：request/limit 既影响调度和 cgroup，也影响 QoS；Guaranteed 最稳定，BestEffort 最脆弱，Burstable 最常见。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Docker 镜像、容器、进程之间是什么关系？容器为什么比虚拟机轻？</div>
<div class="qa-a">
<p>镜像是静态模板，容器是镜像运行起来后的实例，容器里的主程序本质上是宿主机上的一个进程。容器比虚拟机轻，是因为它不需要为每个应用启动一个完整 guest kernel，而是复用宿主机内核，通过 namespace、cgroup、rootfs 等机制提供隔离和限制。</p>
<table>
<tr><th>对象</th><th>本质</th><th>类比</th></tr>
<tr><td>Image</td><td>分层只读文件系统 + 元数据</td><td>应用安装包 / 集装箱模板</td></tr>
<tr><td>Container</td><td>镜像 + 可写层 + namespace + cgroup + 启动进程</td><td>正在运行的集装箱</td></tr>
<tr><td>Process</td><td>内核调度的运行实体</td><td>容器里真正执行的程序</td></tr>
<tr><td>VM</td><td>虚拟硬件 + guest OS + guest kernel</td><td>完整虚拟机器</td></tr>
</table>
<p>所以容器启动快、资源开销低，但隔离边界主要依赖共享内核的安全机制；虚拟机更重，但内核级隔离更强。</p>
</div>
</div>

<div class="card card-w">
<h3>C++ 基础提示</h3>
<p>原文 C++ 小节没有列出具体问题。AI Infra 面试里，如果追问 C++，常见落点是内存生命周期、RAII、智能指针、线程同步、移动语义、动态库链接和性能 profiling。后续可以单独拆一个 C++ 专题页。</p>
</div>
