<div class="card card-m"><h3>容器隔离三件套</h3><p>容器不是轻量 VM，而是 Linux 内核能力的组合：namespace 负责“看见什么”，cgroup 负责“能用多少”，rootfs/镜像负责“文件系统长什么样”。</p></div>
<div class="card card-s"><h3>namespace</h3><table><tr><th>类型</th><th>隔离内容</th></tr><tr><td>pid</td><td>进程号视图</td></tr><tr><td>net</td><td>网卡、路由、端口</td></tr><tr><td>mnt</td><td>挂载点</td></tr><tr><td>uts</td><td>hostname</td></tr><tr><td>ipc</td><td>共享内存、信号量</td></tr><tr><td>user</td><td>用户和权限映射</td></tr></table></div>
<div class="card card-d"><h3>cgroup</h3><p>cgroup 限制和统计 CPU、内存、IO、pids 等资源。K8s 的 requests/limits 最终会落到 cgroup 资源控制上。</p></div>
