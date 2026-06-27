## 一句话结论

分布式训练有三条不同的数据通路：控制面走 RPC 传任务和状态、训练数据面走 NCCL/RDMA 传梯度和参数、存储数据面走对象存储/分布式 FS 传样本和 checkpoint。三者的瓶颈和优化手段完全不同，排查性能问题时要先判断卡在哪条面上，别用一套思路套全部。
<div class="card card-m"><h3>控制面、训练数据面、存储数据面</h3><table><tr><th>链路</th><th>技术</th><th>传输内容</th><th>核心指标</th><th>瓶颈</th></tr><tr><td>控制面</td><td>HTTP/gRPC/Thrift</td><td>任务提交、状态、心跳</td><td>延迟、可用性</td><td>超时、重试、限流</td></tr><tr><td>训练数据面</td><td>NCCL、RDMA、NVLink</td><td>梯度、参数、激活值</td><td>带宽、同步耗时</td><td>拓扑差、拥塞、慢 rank</td></tr><tr><td>存储数据面</td><td>对象存储、分布式 FS、NVMe</td><td>样本、checkpoint、权重</td><td>吞吐、IOPS、元数据性能</td><td>小文件、启动风暴、并发写</td></tr></table></div>
