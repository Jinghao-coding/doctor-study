## 一句话结论

内存问题不是只看容量 是 操作系统基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 操作系统基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕进程线程、调度、虚拟内存、IO、多路复用、死锁、观测和 AI Infra OS 问题建立系统基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m"><h3>内存问题不是只看容量</h3><p>内存排查要同时看系统内存、cgroup limit、GPU 显存、NUMA locality、page cache、swap、带宽和碎片。容量够不代表没有瓶颈。</p></div>
<div class="card card-d"><h3>内存问题基础模型</h3><table><tr><th>维度</th><th>看什么</th><th>典型问题</th><th>排查入口</th></tr><tr><td>容量</td><td>系统内存、cgroup、GPU 显存</td><td>OOMKilled、CUDA OOM</td><td><code>free -h</code>、<code>memory.current</code>、<code>nvidia-smi</code></td></tr><tr><td>带宽</td><td>内存/HBM 吞吐</td><td>容量够但吞吐低</td><td><code>perf</code>、DCGM、Nsight</td></tr><tr><td>延迟</td><td>page fault、swap、远端 NUMA</td><td>P99 抖动</td><td><code>vmstat</code>、<code>numastat</code></td></tr><tr><td>局部性</td><td>CPU/GPU/NIC 是否同 NUMA 域</td><td>跨 socket 访问慢</td><td><code>numactl -H</code>、<code>nvidia-smi topo -m</code></td></tr></table></div>
<div class="card card-s"><h3>OOM、CUDA OOM 和 cgroup OOM</h3><table><tr><th>类型</th><th>资源池</th><th>触发者</th><th>现象</th></tr><tr><td>系统 OOM</td><td>宿主机内存</td><td>Linux OOM killer</td><td>进程被 kill，dmesg 有记录</td></tr><tr><td>cgroup OOM</td><td>容器 memory limit</td><td>cgroup memory controller</td><td>Pod OOMKilled</td></tr><tr><td>CUDA OOM</td><td>GPU 显存</td><td>CUDA runtime / 框架 allocator</td><td>程序抛 CUDA out of memory</td></tr></table></div>
<div class="qa" onclick="this.classList.toggle('open')"><div class="qa-q">Q: NUMA 是什么？为什么机器内存没用完也可能 OOM 或变慢？</div><div class="qa-a"><p>NUMA 是 Non-Uniform Memory Access。多 socket 机器上，每个 CPU socket 有本地内存控制器，访问本地内存快，访问远端内存慢。进程可能被 cpuset、membind、cgroup 或 hugepage 池限制，只能使用部分内存；即使宿主机总内存没用完，也可能因为本地 NUMA node 不足或碎片导致分配失败。</p><div class="qa-summary">面试口径：机器总内存、当前 cgroup 可用内存、本地 NUMA 内存、GPU 显存是不同资源池。</div></div></div>

## 面试回答

**30 秒版：**

03 memory oom numa 是 操作系统基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 操作系统基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
