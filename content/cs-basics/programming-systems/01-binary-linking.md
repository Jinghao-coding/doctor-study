## 一句话结论

一份源码要变成能跑的进程，要走预处理、编译、汇编、链接、加载五个阶段，每个阶段产物和典型报错都不同；AI Infra 里最常踩的坑是链接和加载阶段的「符号找不到」「缺动态库」，定位口诀是 `ldd` 看依赖、`nm`/`readelf` 看符号、`strace` 看加载。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 编程与系统工程基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕编译链接、C++、内存、智能指针、调试和工程排障建立系统编程答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>从源码到进程</h3><table><tr><th>阶段</th><th>输入</th><th>输出</th><th>常见问题</th><th>工具</th></tr><tr><td>预处理</td><td>源码、头文件、宏</td><td>.i</td><td>宏/头文件错误</td><td><code>gcc -E</code></td></tr><tr><td>编译</td><td>预处理结果</td><td>汇编</td><td>优化导致行为变化</td><td><code>gcc -S</code></td></tr><tr><td>汇编</td><td>汇编</td><td>.o</td><td>指令集不兼容</td><td><code>objdump</code></td></tr><tr><td>链接</td><td>.o 和库</td><td>ELF/.so</td><td>符号找不到</td><td><code>ldd</code>、<code>nm</code>、<code>readelf</code></td></tr><tr><td>加载</td><td>ELF</td><td>进程</td><td>缺动态库、权限错误</td><td><code>strace</code></td></tr></table></div>
<div class="qa" onclick="this.classList.toggle('open')"><div class="qa-q">Q: 程序在本机能跑，容器里报缺库，怎么排查？</div><div class="qa-a"><p>先用 <code>ldd binary</code> 看动态库依赖，再检查容器内是否存在对应 <code>.so</code> 和版本；检查 <code>LD_LIBRARY_PATH</code>、基础镜像、glibc/libstdc++ 版本和 CUDA/cuDNN/NCCL 版本。</p></div></div>

## 面试回答

**30 秒版：**

源码到进程要经过预处理、编译、汇编、链接、加载五步：前三步把 `.cpp` 变成 `.o` 目标文件，链接把多个 `.o` 和库做符号解析、重定位生成 ELF，加载阶段动态链接器再把 `.so` 映射进地址空间。生产里最高频的问题集中在后两步：链接报「undefined symbol」往往是库没链上或 ABI 不符，运行时「缺库」则用 `ldd` 查依赖。

**2 分钟版：**

源码到可执行进程分五个阶段：预处理做宏展开和头文件包含，编译生成汇编，汇编生成 `.o` 目标文件，链接做符号解析和重定位生成 ELF 或 `.so`，最后加载阶段由动态链接器把依赖的动态库映射进进程地址空间。每个阶段都有对应工具：`gcc -E/-S`、`objdump`、`nm`、`readelf`、`ldd`、`strace`。工程上的关键权衡是静态链接还是动态链接——静态库体积大但无运行时依赖，动态库省体积、可共享但要求运行环境有匹配版本的 `.so`。落到 AI Infra，CUDA、cuDNN、NCCL 基本都以动态库分发，最典型的故障是「本机能跑、容器里报缺库」，排查路径就是 `ldd` 看缺哪个 `.so`，再核对 `LD_LIBRARY_PATH`、基础镜像里的 glibc/libstdc++ 以及 CUDA 各组件版本是否对得上。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
