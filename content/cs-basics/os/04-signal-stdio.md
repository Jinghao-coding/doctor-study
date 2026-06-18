## 一句话结论

Signal 是内核投递给进程的异步事件，最该记住的是优雅退出这条线：SIGTERM 是可捕获的"协商退出"，给应用 flush 日志、保存状态、释放锁的机会；SIGKILL 不可捕获、是强制回收。K8s 删 Pod 就是先 SIGTERM、超过 grace period 再 SIGKILL。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 操作系统基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕进程线程、调度、虚拟内存、IO、多路复用、死锁、观测和 AI Infra OS 问题建立系统基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>Signal：进程控制的异步通知机制</h3><p>Signal 是内核投递给进程的异步事件，可用于终止、暂停、恢复、用户中断、非法访问、定时器和子进程状态变化。</p></div>
<div class="card card-d"><h3>常见 Signal</h3><table><tr><th>Signal</th><th>含义</th><th>是否可捕获</th><th>典型场景</th></tr><tr><td>SIGTERM</td><td>请求进程优雅退出</td><td>是</td><td>K8s 删除 Pod、systemctl stop</td></tr><tr><td>SIGKILL</td><td>强制杀死</td><td>否</td><td>grace period 超时</td></tr><tr><td>SIGINT</td><td>用户中断</td><td>是</td><td>Ctrl-C</td></tr><tr><td>SIGSEGV</td><td>非法内存访问</td><td>可捕获但通常不恢复</td><td>C/C++ 指针错误</td></tr><tr><td>SIGCHLD</td><td>子进程退出</td><td>是</td><td>父进程回收子进程</td></tr></table></div>
<div class="card card-s"><h3>stdin/stdout/stderr</h3><table><tr><th>通道</th><th>fd</th><th>用途</th><th>容器/K8s 含义</th></tr><tr><td>stdin</td><td>0</td><td>输入</td><td>交互式 exec 或管道输入</td></tr><tr><td>stdout</td><td>1</td><td>正常输出</td><td>容器日志采集主通道</td></tr><tr><td>stderr</td><td>2</td><td>错误和 warning</td><td>容器日志采集主通道</td></tr></table></div>
<div class="qa" onclick="this.classList.toggle('open')"><div class="qa-q">Q: K8s 删除 Pod 时为什么先 SIGTERM 后 SIGKILL？</div><div class="qa-a"><p>先发 SIGTERM 是为了给应用优雅退出机会：停止接新请求、处理完存量请求、flush 日志、保存状态、释放锁。超过 terminationGracePeriodSeconds 仍未退出时，再发不可捕获的 SIGKILL 强制回收资源。</p><div class="qa-summary">面试口径：SIGTERM 是协商退出，SIGKILL 是强制回收。</div></div></div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
