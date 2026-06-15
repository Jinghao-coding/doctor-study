## 一句话结论

容器隔离三件套 是 Linux 与容器基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Linux 与容器基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕运行环境、namespace、cgroup、rootfs、Docker/K8S 资源模型建立容器基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m"><h3>容器隔离三件套</h3><p>容器不是轻量 VM，而是 Linux 内核能力的组合：namespace 负责“看见什么”，cgroup 负责“能用多少”，rootfs/镜像负责“文件系统长什么样”。</p></div>
<div class="card card-s"><h3>namespace</h3><table><tr><th>类型</th><th>隔离内容</th></tr><tr><td>pid</td><td>进程号视图</td></tr><tr><td>net</td><td>网卡、路由、端口</td></tr><tr><td>mnt</td><td>挂载点</td></tr><tr><td>uts</td><td>hostname</td></tr><tr><td>ipc</td><td>共享内存、信号量</td></tr><tr><td>user</td><td>用户和权限映射</td></tr></table></div>
<div class="card card-d"><h3>cgroup</h3><p>cgroup 限制和统计 CPU、内存、IO、pids 等资源。K8s 的 requests/limits 最终会落到 cgroup 资源控制上。</p></div>

## 面试回答

**30 秒版：**

02 namespace cgroup rootfs 是 Linux 与容器基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 Linux 与容器基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
