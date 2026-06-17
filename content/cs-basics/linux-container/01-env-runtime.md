## 一句话结论

环境变量是进程启动时继承的一份 key-value 快照，每个进程一份、不是全局状态。AI Infra 里大量「在我机器上能跑、容器里跑不了」的问题，本质是 PATH、LD_LIBRARY_PATH、CUDA_VISIBLE_DEVICES、代理这几个变量在容器和宿主机之间不一致。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Linux 与容器基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕运行环境、namespace、cgroup、rootfs、Docker/K8S 资源模型建立容器基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>环境变量与运行环境</h3><p>环境变量是进程启动时继承的一组 key-value，用于传递配置、路径、鉴权和运行模式。它不是全局状态，而是每个进程自己的环境快照。</p></div>
<div class="card card-d"><h3>常见变量</h3><table><tr><th>变量</th><th>作用</th><th>问题</th></tr><tr><td>PATH</td><td>查找可执行文件</td><td>命令找不到或执行了错误版本</td></tr><tr><td>LD_LIBRARY_PATH</td><td>动态库查找路径</td><td>缺库、ABI 不兼容</td></tr><tr><td>CUDA_VISIBLE_DEVICES</td><td>控制 GPU 可见性</td><td>容器内卡号和宿主机卡号映射混淆</td></tr><tr><td>HTTP_PROXY</td><td>网络代理</td><td>下载失败或访问内网异常</td></tr></table></div>

## 面试回答

**30 秒版：**

环境变量是进程启动时继承的 key-value，用来传配置、路径、鉴权和运行模式，它是进程级快照不是全局状态。最容易出问题的是 PATH（命令版本不对）、LD_LIBRARY_PATH（缺库/ABI 不兼容）、CUDA_VISIBLE_DEVICES（卡号映射混淆）和代理变量（下载失败）。

**2 分钟版：**

我会先讲本质：环境变量在 exec 时由父进程传给子进程，每个进程持有自己的副本，改一个进程的环境不会影响别人，这也是为什么「在 shell 里 export 了但服务读不到」——服务不是这个 shell 的子进程。然后讲几类高频变量和坑：PATH 决定命令查找顺序，多版本共存时容易执行错版本；LD_LIBRARY_PATH 影响动态库加载，CUDA、cuDNN 版本不匹配常报符号缺失；CUDA_VISIBLE_DEVICES 控制进程能看到哪些 GPU，容器里看到的卡号和宿主机物理卡号是映射关系，调试时要分清；HTTP_PROXY 在内网构建镜像时不设会拉不到包、设错会访问不到内网。最后收束：排查容器运行问题，我会先 env 比对容器内外的关键变量，再确认 GPU 可见性和库路径，这通常比直接怀疑代码更快定位。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。
