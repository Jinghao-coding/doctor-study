<div class="card card-w">
<h3>配额管理方案对比</h3>
<table>
<tr><th>方案</th><th>保障性</th><th>弹性</th><th>回收</th><th>公平度量</th></tr>
<tr><td>固定配额</td><td>强</td><td>无</td><td>不需要</td><td>—</td></tr>
<tr><td>ElasticQuota</td><td>min 保障</td><td>max 上限</td><td>抢占</td><td>—</td></tr>
<tr><td>弹性保障（DRA 类）</td><td>QAD ≥ 0.95</td><td>无上限（借用）</td><td>QAD 驱动回收</td><td>QAD</td></tr>
<tr><td>DRF</td><td>弱</td><td>按比例</td><td>—</td><td>Dominant Share</td></tr>
</table>

<h3>多租户隔离层次</h3>
<ol>
<li><strong>Namespace 级别</strong>：ResourceQuota 限制总量，LimitRange 限制单个 Pod。最基本的隔离</li>
<li><strong>Queue 级别</strong>：Volcano Queue / Kueue ClusterQueue。更灵活的配额管理和排队</li>
<li><strong>节点级别</strong>：NodeSelector / Taint-Toleration 把特定节点专属于特定租户</li>
<li><strong>GPU 级别</strong>：MIG 硬件切片 / MPS 软件共享。GPU 内部的隔离</li>
</ol>
</div>
