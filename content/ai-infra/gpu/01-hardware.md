<div class="card card-m">
<h3>GPU 架构要点</h3>
<table>
<tr><th>概念</th><th>说明</th></tr>
<tr><td>SM（Streaming Multiprocessor）</td><td>GPU 基本计算单元，包含若干 CUDA Core 和 Tensor Core。A100 有 108 个 SM</td></tr>
<tr><td>Tensor Core</td><td>矩阵乘加专用硬件。A100 第三代支持 TF32/FP16/BF16/INT8，H100 第四代新增 FP8</td></tr>
<tr><td>HBM（High Bandwidth Memory）</td><td>高带宽显存。A100 80GB 版带宽 2TB/s，H100 80GB 版 3.35TB/s</td></tr>
<tr><td>NVLink</td><td>GPU 间高速互联。A100 NVLink 3.0 单向 300GB/s（6 条），H100 NVLink 4.0 单向 450GB/s</td></tr>
<tr><td>NVSwitch</td><td>多 GPU 全互联交换芯片。DGX A100 用 6 个 NVSwitch 连 8 块 GPU</td></tr>
<tr><td>PCIe</td><td>CPU-GPU 互联。Gen4 x16 单向 32GB/s，Gen5 翻倍到 64GB/s</td></tr>
</table>
</div>

<div class="card card-s">
<h3>主流 GPU 对比</h3>
<table>
<tr><th>指标</th><th>A100 (80GB)</th><th>H100 (80GB)</th><th>H200 (141GB)</th></tr>
<tr><td>架构</td><td>Ampere</td><td>Hopper</td><td>Hopper</td></tr>
<tr><td>SM 数</td><td>108</td><td>132</td><td>132</td></tr>
<tr><td>FP16 算力</td><td>312 TFLOPS</td><td>989 TFLOPS</td><td>989 TFLOPS</td></tr>
<tr><td>显存</td><td>80GB HBM2e</td><td>80GB HBM3</td><td>141GB HBM3e</td></tr>
<tr><td>带宽</td><td>2.0 TB/s</td><td>3.35 TB/s</td><td>4.8 TB/s</td></tr>
<tr><td>TDP</td><td>400W</td><td>700W</td><td>700W</td></tr>
</table>
</div>
