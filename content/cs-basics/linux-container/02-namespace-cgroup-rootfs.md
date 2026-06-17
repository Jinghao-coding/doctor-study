## 一句话结论

容器不是轻量虚拟机，而是 Linux 内核三种能力的组合：namespace 决定进程「能看见什么」、cgroup 决定「能用多少资源」、rootfs/镜像决定「文件系统长什么样」。理解这三件套，才能解释容器为什么共享宿主机内核、为什么资源限制最终落到 cgroup。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Linux 与容器基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕运行环境、namespace、cgroup、rootfs、Docker/K8S 资源模型建立容器基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>容器隔离三件套</h3><p>容器不是轻量 VM，而是 Linux 内核能力的组合：namespace 负责“看见什么”，cgroup 负责“能用多少”，rootfs/镜像负责“文件系统长什么样”。</p></div>
<div class="card card-s"><h3>namespace</h3><table><tr><th>类型</th><th>隔离内容</th></tr><tr><td>pid</td><td>进程号视图</td></tr><tr><td>net</td><td>网卡、路由、端口</td></tr><tr><td>mnt</td><td>挂载点</td></tr><tr><td>uts</td><td>hostname</td></tr><tr><td>ipc</td><td>共享内存、信号量</td></tr><tr><td>user</td><td>用户和权限映射</td></tr></table></div>
<div class="card card-d"><h3>cgroup</h3><p>cgroup 限制和统计 CPU、内存、IO、pids 等资源。K8s 的 requests/limits 最终会落到 cgroup 资源控制上。</p></div>

## 面试回答

**30 秒版：**

容器是 namespace + cgroup + rootfs 的组合：namespace 隔离视图（pid/net/mnt/uts/ipc/user），cgroup 限制和统计资源（CPU/内存/IO/pids），rootfs 提供独立文件系统。它们共享宿主机内核，所以容器比 VM 轻，但隔离强度也弱于 VM。

**2 分钟版：**

我会按三件套展开：namespace 决定进程能看到什么，pid namespace 让容器内进程号从 1 开始，net namespace 给独立网卡和端口，mnt namespace 隔离挂载点；cgroup 决定能用多少，限制 CPU、内存、IO、pids 并做统计，K8s 的 requests/limits 最终就是写到 cgroup；rootfs 由镜像分层叠加而来，决定容器里的文件系统视图。然后讲关键认知：容器共享宿主机内核，没有独立内核，所以内核漏洞、内核参数、GPU 驱动都是和宿主机共用的，这也是容器逃逸和 GPU 容器化要特别注意的地方。最后收束到 AI Infra：GPU 容器要靠 device plugin 把设备挂进 mnt/device，CUDA_VISIBLE_DEVICES 配合 cgroup 做卡级隔离；排查容器 OOM 时要看 cgroup 内存统计而不是宿主机整体内存。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
