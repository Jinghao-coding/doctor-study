## 一句话结论

进程地址空间从高到低是栈、mmap 区、堆、.bss、.data、.text，栈向下、堆向上、中间是动态映射区；理解这套布局能解释三件高频考点——为什么 mmap 能高效加载几十 GB 大模型权重（按需分页+减少拷贝）、为什么数组越界有时立即 core 有时「带病运行」（取决于越界地址是否触发页错误）、以及怎么用 ASan/Valgrind 配合 RAII 防住内存泄漏。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 编程与系统工程基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕编译链接、C++、内存、智能指针、调试和工程排障建立系统编程答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m">
<h3>程序内存分布（从高地址到低地址）</h3>
<table>
<tr><th>区域</th><th>内容</th><th>特点</th></tr>
<tr><td>命令行参数 / 环境变量</td><td>argv、environ</td><td>最高地址</td></tr>
<tr><td>栈 stack</td><td>函数局部变量、调用帧、返回地址</td><td>向下增长，自动分配/释放，容量有限</td></tr>
<tr><td>↓ ... ↑（中间空洞）</td><td>mmap 区域常落在这里</td><td>栈向下、堆向上，中间是动态映射区</td></tr>
<tr><td>堆 heap</td><td>malloc / new 动态分配</td><td>向上增长，手动管理，易泄漏</td></tr>
<tr><td>.bss</td><td>未初始化的全局/静态变量</td><td>运行时清零，不占文件体积</td></tr>
<tr><td>.data</td><td>已初始化的全局/静态变量</td><td>程序运行自动加载</td></tr>
<tr><td>.text（常量区 + 代码区）</td><td>只读数据、机器指令</td><td>最低地址，只读，写入会段错误</td></tr>
</table>
</div>

<div class="card card-s">
<h3>mmap 内存映射：加载大模型权重的关键</h3>
<p>mmap 把一个文件映射到进程地址空间，使文件内容直接成为进程内存的一部分，可以用指针操作而不需要显式 read/write。加载大模型权重（动辄几十 GB）时优势明显：</p>
<ul>
<li><strong>按字节随机访问</strong>：对权重等二进制数据的随机访问更直观，用指针偏移代替复杂的文件偏移量管理。</li>
<li><strong>按需分页加载</strong>：mmap 不是一次性把整个文件读入内存，而是根据访问位置分块（逐页）加载，因此能在有限内存里处理远大于内存的模型文件。</li>
<li><strong>减少数据拷贝</strong>：传统 read 要把数据从内核缓冲区拷到用户缓冲区；mmap 直接把文件页映射进地址空间，省掉这一次拷贝，提升访问速度。</li>
</ul>
<div class="qa-summary">面试口径：mmap = 文件直接映射进地址空间 + 按需分页 + 减少拷贝，是 llama.cpp 等推理框架快速加载大权重的常用手段。</div>
</div>

<div class="card card-r">
<h3>数组越界：为什么有时立即 core dump、有时过一会才崩</h3>
<p>段错误（Segmentation Fault）是虚拟内存管理系统在检测到非法内存访问时触发的。是否立即崩溃，取决于越界落到的地址是否是"非法地址"：</p>
<ul>
<li>访问<strong>不存在的内存空间</strong>（进程地址空间以外的未映射页）→ 立即触发段错误。</li>
<li>访问<strong>没有权限的内存空间</strong>（如内核地址）→ 立即段错误。</li>
<li>写入<strong>只读内存段</strong>（如 .text 代码段）→ 立即段错误。</li>
<li>但如果越界后访问的地址<strong>仍落在已映射的合法页内</strong>（例如同一页里相邻的堆数据、缓冲区溢出但没跨页），硬件不会报错，程序会"带病运行"，直到后续某次访问真正踩到非法页或破坏的数据导致逻辑崩溃，才"过一会儿"core dump。</li>
</ul>
<p>所以越界是否立即崩溃，本质是"越界地址是否触发了内存页错误/段错误"，而不是"是否越界"。这也是越界 bug 难定位的原因——崩溃点往往不是真正出错的地方。</p>
</div>

<div class="card card-w">
<h3>内存泄漏检测：工具与原理</h3>
<table>
<tr><th>工具</th><th>平台</th><th>原理</th><th>开销</th></tr>
<tr><td>Valgrind</td><td>Linux / macOS</td><td>动态二进制插桩：在虚拟 CPU 上运行程序，把每条指令翻译并插入检查逻辑，跟踪每次分配/释放/访问，检测越界、未初始化读、重复释放、泄漏</td><td>慢 10–20×</td></tr>
<tr><td>AddressSanitizer (ASan)</td><td>GCC / Clang</td><td>编译期插桩 + 影子内存（shadow memory）：编译时在内存访问前插入检查，用影子内存标记每个字节是否可访问</td><td>慢 2–3×（远低于 Valgrind）</td></tr>
<tr><td>VS CRT 调试</td><td>Windows</td><td><code>_CrtDumpMemoryLeaks</code> 在程序结束时报告泄漏</td><td>低</td></tr>
</table>
<pre><code class="language-bash"># Valgrind
valgrind --leak-check=yes ./your_program

# AddressSanitizer：编译时加 flag
g++ -fsanitize=address -g main.cpp -o main</code></pre>
<p><strong>如何避免内存泄漏</strong>：①用智能指针（unique_ptr / shared_ptr）让内存随作用域自动释放；②异常安全，用 RAII 把资源生命周期绑定到对象生命周期，异常时析构自动释放，避免 try-catch 里手动 free 遗漏。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Valgrind 和 AddressSanitizer 的核心区别是什么？</div>
<div class="qa-a"><p>Valgrind 是运行时动态二进制插桩，不需要重新编译，把程序跑在自带虚拟 CPU 上逐指令检查，覆盖全但慢 10–20×。ASan 是编译期插桩，需要加 <code>-fsanitize=address</code> 重新编译，靠影子内存在访问前快速判定，开销只有 2–3×，更适合在 CI 和日常开发中常态化开启。</p></div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
