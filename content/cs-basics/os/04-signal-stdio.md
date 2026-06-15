## 一句话结论

Signal：进程控制的异步通知机制 是 操作系统基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

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

<div class="card card-m"><h3>Signal：进程控制的异步通知机制</h3><p>Signal 是内核投递给进程的异步事件，可用于终止、暂停、恢复、用户中断、非法访问、定时器和子进程状态变化。</p></div>
<div class="card card-d"><h3>常见 Signal</h3><table><tr><th>Signal</th><th>含义</th><th>是否可捕获</th><th>典型场景</th></tr><tr><td>SIGTERM</td><td>请求进程优雅退出</td><td>是</td><td>K8s 删除 Pod、systemctl stop</td></tr><tr><td>SIGKILL</td><td>强制杀死</td><td>否</td><td>grace period 超时</td></tr><tr><td>SIGINT</td><td>用户中断</td><td>是</td><td>Ctrl-C</td></tr><tr><td>SIGSEGV</td><td>非法内存访问</td><td>可捕获但通常不恢复</td><td>C/C++ 指针错误</td></tr><tr><td>SIGCHLD</td><td>子进程退出</td><td>是</td><td>父进程回收子进程</td></tr></table></div>
<div class="card card-s"><h3>stdin/stdout/stderr</h3><table><tr><th>通道</th><th>fd</th><th>用途</th><th>容器/K8s 含义</th></tr><tr><td>stdin</td><td>0</td><td>输入</td><td>交互式 exec 或管道输入</td></tr><tr><td>stdout</td><td>1</td><td>正常输出</td><td>容器日志采集主通道</td></tr><tr><td>stderr</td><td>2</td><td>错误和 warning</td><td>容器日志采集主通道</td></tr></table></div>
<div class="qa" onclick="this.classList.toggle('open')"><div class="qa-q">Q: K8s 删除 Pod 时为什么先 SIGTERM 后 SIGKILL？</div><div class="qa-a"><p>先发 SIGTERM 是为了给应用优雅退出机会：停止接新请求、处理完存量请求、flush 日志、保存状态、释放锁。超过 terminationGracePeriodSeconds 仍未退出时，再发不可捕获的 SIGKILL 强制回收资源。</p><div class="qa-summary">面试口径：SIGTERM 是协商退出，SIGKILL 是强制回收。</div></div></div>

## 面试回答

**30 秒版：**

04 signal stdio 是 操作系统基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 操作系统基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
