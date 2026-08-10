## 面试回答方法

遇到系统问题时先分四层，不要一上来只报命令：

```flow
业务现象 | 吞吐、延迟、失败率、GPU 空转
进程与容器 | 状态、线程、cgroup、OOM、FD、共享内存
主机资源 | CPU、内存、NUMA、磁盘、网络
加速器与分布式 | H2D、SM、HBM、NCCL、GPU 拓扑
```

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 容器 OOM 和宿主机 OOM 怎么区分？</div>
<div class="qa-a"><p>先看 Pod termination reason、exit code 137 和事件，再看对应 cgroup 的 <code>memory.current</code>、<code>memory.max</code> 与 <code>memory.events</code>。如果进程触及容器 memory limit，通常是 cgroup 内 OOM；如果节点整体内存耗尽，则还要结合宿主机 <code>dmesg</code>、系统可用内存和其他进程判断。详细隔离机制放在“Linux 与容器”。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 利用率低为什么也可能是操作系统问题？</div>
<div class="qa-a"><p>GPU 可能在等 CPU 解码、DataLoader、page fault、磁盘或网络 I/O，也可能因为 NUMA 放置不当导致 H2D 路径变长。OS 负责解释供给链为什么阻塞；SM Active、Warp Stall 和 NCCL 等 GPU 专项判断放在 GPU 与分布式训练页面。</p></div>
</div>

## 常见误区

- cgroup 能限制 CPU、内存和设备访问，不等于它能直接切分 GPU 的 SM 与 HBM。
- 显存占用高只说明资源常驻，不说明 GPU 正在高效计算。
- `top` 中 CPU 不满不能排除单核热点、锁竞争、系统调用等待和 NUMA 问题。
- `mmap` 不等于数据已经进入物理内存；首次访问仍可能触发缺页。
