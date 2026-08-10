## 70B FP16 实算

以 70B、FP16、Batch=1、生成一个 Token 为例，先忽略 KV Cache 和其他中间结果，只看权重：

| 项目 | 计算 |
|---|---:|
| 每 Token 计算量 | `2 × 70B ≈ 140 GFLOPs` |
| 权重读取量 | `70B × 2 Byte ≈ 140 GB` |
| 算术强度 | `140 GFLOPs ÷ 140 GB ≈ 1 FLOP/Byte` |

如果某 GPU 的 FP16 峰值约为 `312 TFLOPS`、HBM 带宽约为 `2 TB/s`，其机器平衡点约为：

$$I_{ridge}=\frac{312\ \mathrm{TFLOPS}}{2\ \mathrm{TB/s}}\approx156\ \mathrm{FLOP/Byte}$$

Decode 的约 `1 FLOP/Byte` 远低于 `156 FLOP/Byte`，因此即使 Tensor Core 没吃满，也不是继续堆算力就能解决，主要限制来自 HBM 读取。

## 为什么 Batch 能提高吞吐

Batch 增大后，同一份权重能服务多个请求。权重读取量不会按 Batch 等比例增长，而计算量会增长，因此权重被复用、算术强度上升。这是 Continuous Batching 提升吞吐的底层原因之一。

但 Batch 不是无限增大：

- Batch 增大会占用更多 KV Cache。
- 排队等待可能推高 TTFT。
- 长短请求混合会引入调度与尾延迟问题。
- 长上下文 Decode 还需要持续扫描更大的 KV Cache。

## 优化方向

| 瓶颈来源 | 优化方向 | 代价 |
|---|---|---|
| 权重带宽 | Continuous Batching、权重量化 | 排队延迟、精度和 Kernel 支持 |
| KV Cache 带宽/容量 | GQA/MQA、KV 量化、PagedAttention | 精度、实现复杂度 |
| 小 Kernel 与 Launch Gap | CUDA Graph、Kernel Fusion | 动态性受限、调试复杂 |
| Prefill/Decode 互相干扰 | Chunked Prefill、阶段分离 | 调度与资源治理复杂 |

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 GPU-Util 很高，Decode 吞吐仍可能很差？</div>
<div class="qa-a"><p>GPU-Util 只说明采样窗口内设备在忙，不代表 Tensor Core 或峰值 FLOPs 被充分使用。Decode 可能持续执行访存型 Kernel，使 GPU-Util 很高，但 SM 的计算管线在等 HBM。应结合 HBM 吞吐、SM Active、Tensor Core 利用率、Batch 和 Token/s 判断。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 这道题面试中如何概括？</div>
<div class="qa-a"><p>70B FP16、Batch=1 每生成一个 Token 约做 140 GFLOPs，却要读约 140 GB 权重，算术强度只有约 1 FLOP/Byte，远低于 GPU 的机器平衡点，所以 Decode 主要受 HBM 带宽限制；增大 Batch、量化权重和压缩 KV Cache都是在提高复用或减少搬运。</p></div>
</div>
