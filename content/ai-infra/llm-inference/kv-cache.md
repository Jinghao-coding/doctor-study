KV 缓存是 LLM serving 的核心资源瓶颈。它的大小和 batch size、上下文长度、层数、head 维度、精度相关。

```text
KV cache size = 2 × layers × kv_heads × head_dim × seq_len × dtype_size
```

PagedAttention 的核心思想是把 KV cache 切成 block，用 block table 做逻辑到物理的映射，从而减少连续预分配带来的内部碎片。

面试追问可以这样答：Continuous Batching 解决的是 decode 阶段 batch 动态变化的问题，PagedAttention 解决的是 KV cache 内存管理的问题，两者配合提升 serving 吞吐和显存利用率。
