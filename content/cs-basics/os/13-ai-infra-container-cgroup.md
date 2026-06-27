## 一句话结论

namespace 管"看见什么"（PID、网络栈、挂载点、IPC），cgroup 管"能用多少"（CPU、内存、I/O、设备），容器隔离就是 namespace + cgroup + rootfs + capability/seccomp 组合出来的。AI Infra 几乎都跑在容器和 K8s 上，所以要能把 OS 知识映射到容器 OOM（exit 137）、CFS throttling、cgroup memory limit 和 /dev/shm 不足这些实际故障。
## AI Infra 面试模块：容器、cgroup 与 Linux 隔离机制

AI Infra 基本运行在容器和 Kubernetes 之上，因此操作系统知识必须能映射到 namespace、cgroup、device plugin、资源限制和容器内外观测差异。

### 需要掌握

- namespace：pid、net、mnt、uts、ipc、user，负责隔离“看到什么”。
- cgroup：CPU、memory、blkio/io、device、pids，负责限制和统计“能用多少”。
- 容器与虚拟机：容器共享宿主机内核，虚拟机有独立 guest kernel。
- Docker 镜像层与 overlayfs：镜像是只读层叠加，可写层记录容器修改。
- 容器内看到的资源与宿主机资源关系：工具显示可能来自宿主机视角，但实际受 cgroup 限制。
- OOM、CPU throttling、文件描述符限制在容器中的表现。

### AI Infra 相关关注点

- Kubernetes 训练任务的 CPU、内存、GPU 资源隔离由 request/limit、cgroup、device plugin 和调度器共同实现。
- 容器 OOM 与宿主机 OOM 不同：容器达到 memory limit 会在 cgroup 内 kill。
- cgroup memory limit 会影响匿名内存、page cache、shared memory，可能出现 page cache 把容器 limit 顶满。
- 多卡训练容器通过 NVIDIA device plugin 暴露 GPU device、驱动库和 `CUDA_VISIBLE_DEVICES`。
- `/dev/shm` 太小会导致 PyTorch DataLoader、共享内存队列或分布式训练异常。

<div class="card card-s">
<h3>namespace 和 cgroup 的区别</h3>
<p>namespace 解决“看见什么”：PID、网络栈、挂载点、主机名、IPC 对象。cgroup 解决“能用多少”：CPU、内存、I/O、进程数和设备。容器隔离通常是 namespace + cgroup + rootfs + capability/seccomp 组合出来的。</p>
</div>

### 高频问题

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Docker 容器是如何实现隔离的？</div>
<div class="qa-a"><p>Docker 主要利用 Linux namespace 隔离进程视图、网络、挂载、IPC、用户等；利用 cgroup 限制和统计 CPU、内存、I/O、设备等资源；利用 overlayfs 提供镜像层和可写层；再配合 capability、seccomp、AppArmor/SELinux 限制权限和系统调用。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 容器内进程被 OOM kill，如何排查？</div>
<div class="qa-a"><p>先看 Pod 状态、exit code 137、events；再看 cgroup memory.current/memory.max、容器日志和 dmesg；区分主进程 RSS、DataLoader worker、/dev/shm、page cache、shared memory、内存泄漏和 batch size 是否异常。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: /dev/shm 不足会导致什么问题？</div>
<div class="qa-a"><p>/dev/shm 是 tmpfs 共享内存。PyTorch DataLoader 多进程、共享内存队列、Ray、某些分布式通信都可能依赖它。空间不足会出现 bus error、worker 异常退出、进程 hang 或吞吐下降。</p></div>
</div>
