<h3>四阶段流程</h3>
<ol>
<li><strong>模型加载</strong>：权重从存储（磁盘/网络）加载到 GPU 显存。大模型可能需要几十秒到几分钟</li>
<li><strong>Prefill（预填充，计算密集）</strong>：一次性处理整个 prompt，并行计算所有 token 的 attention，生成初始 KV 缓存。延迟主要取决于 prompt 长度和模型大小</li>
<li><strong>Decode（解码，内存密集）</strong>：自回归逐 token 生成。每步只计算一个新 token 的 attention，但需要读取全量 KV 缓存。带宽瓶颈，GPU 计算单元大量空闲</li>
<li><strong>返回结果</strong>：流式输出或一次性返回</li>
</ol>

<h3>关键性能指标</h3>
<table>
<tr><th>指标</th><th>含义</th><th>影响因素</th></tr>
<tr><td>TTFT（Time to First Token）</td><td>首 token 延迟</td><td>模型加载 + prefill 时间</td></tr>
<tr><td>TPOT（Time Per Output Token）</td><td>每 token 延迟</td><td>decode 单步时间，受显存带宽限制</td></tr>
<tr><td>Throughput</td><td>吞吐（tokens/s）</td><td>batch size × 单步速度</td></tr>
<tr><td>SLO 达成率</td><td>满足延迟目标的请求比例</td><td>排队 + 计算 + 内存管理</td></tr>
</table>

<h3>Prefill vs Decode 的计算特性差异</h3>
<table>
<tr><th>维度</th><th>Prefill</th><th>Decode</th></tr>
<tr><td>计算模式</td><td>并行处理 N 个 token</td><td>每步只处理 1 个 token</td></tr>
<tr><td>瓶颈</td><td>计算密集（矩阵乘法）</td><td>内存密集（读 KV 缓存）</td></tr>
<tr><td>GPU 利用率</td><td>高（Tensor Core 饱和）</td><td>低（大量等待显存读取）</td></tr>
<tr><td>优化方向</td><td>算子融合、FlashAttention</td><td>增大 batch、KV 缓存压缩</td></tr>
</table>
