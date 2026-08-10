## 核心概念

<div class="card card-m">
<h3>etcd 在 K8s 中的位置</h3>
<p>API Server 是唯一直接读写 etcd 的组件。所有 K8s 资源对象（Pod、Deployment、Node、ConfigMap 等）都以 <code>/registry/&lt;resource&gt;/&lt;namespace&gt;/&lt;name&gt;</code> 的 key 格式存储在 etcd 中。etcd 负责一致性、持久化和通知分发，API Server 负责认证鉴权、版本转换和语义校验。</p>
<table>
<tr><th>维度</th><th>说明</th></tr>
<tr><td>数据模型</td><td>扁平 KV，支持按前缀查询、范围查询</td></tr>
<tr><td>一致性</td><td>Raft 协议，强一致读（默认 linearizable）</td></tr>
<tr><td>版本控制</td><td>全局单调递增 revision，每次写操作 +1</td></tr>
<tr><td>watch 能力</td><td>从任意 revision 开始订阅变更事件流</td></tr>
<tr><td>存储引擎</td><td>boltDB（嵌入式 B+tree KV 存储）</td></tr>
</table>
</div>

<div class="card card-s">
<h3>etcd 集群拓扑</h3>
<p>生产环境通常部署 3 或 5 个 etcd 节点（奇数个，保证多数派可用）。一个节点为 Leader，其余为 Follower；Leader 崩溃后自动触发选举。</p>
<table>
<tr><th>角色</th><th>职责</th></tr>
<tr><td>Leader</td><td>处理所有写请求，复制日志到 Follower，提交后应用到状态机</td></tr>
<tr><td>Follower</td><td>被动接收日志、响应读请求（默认转发给 Leader）、参与选举投票</td></tr>
<tr><td>Candidate</td><td>选举过程中的临时状态，请求投票</td></tr>
<tr><td>Learner</td><td>非投票成员，只同步数据，用于扩展读能力或灾备</td></tr>
</table>
</div>

## Raft 一致性协议

<div class="card card-m">
<h3>Raft 核心：Leader 选举</h3>
<p>Raft 将一致性问题拆分为三个子问题：Leader 选举、日志复制、安全性。选举机制基于 <strong>term（任期）</strong> 和 <strong>心跳</strong>：</p>
<ol>
<li><strong>初始状态：</strong>所有节点为 Follower，等待 Leader 心跳（默认 100ms）。</li>
<li><strong>选举触发：</strong>Follower 在随机 election timeout（150-300ms）内没收到心跳，转为 Candidate，term+1，给自己投票，向其他节点发 RequestVote RPC。</li>
<li><strong>投票规则：</strong>每个 term 每个节点只能投一票，先到先得；Candidate 必须包含自己的最后一条日志的 term 和 index，接收者只会投票给日志至少和自己一样新的 Candidate。</li>
<li><strong>当选 Leader：</strong>获得多数派（quorum = (n/2)+1）投票后成为 Leader，立即发心跳抑制其他选举。</li>
<li><strong>Leader 故障：</strong>心跳中断，Follower 发起新选举，term 增加。</li>
</ol>
<div class="qa-summary">选举安全：一个 term 最多一个 Leader；日志更新的节点才能当选，保证已提交日志不会丢失。</div>
</div>

<div class="card card-s">
<h3>日志复制</h3>
<p>Leader 收到写请求后，流程如下：</p>
<pre><code>Client → Leader (append to local log, uncommitted)
  → Leader 并发发 AppendEntries RPC 给所有 Follower
  → Follower 写入本地日志后回复 ACK
  → Leader 收到多数派 ACK 后标记为 committed
  → Leader 应用到状态机（boltDB），返回 Client
  → Leader 通过后续 AppendEntries/心跳通知 Follower 提交进度
</code></pre>
<table>
<tr><th>概念</th><th>含义</th></tr>
<tr><td>Log Entry</td><td>包含 term、index、command 三要素</td></tr>
<tr><td>committed</td><td>已复制到多数派节点的日志条目，持久且不可丢失</td></tr>
<tr><td>applied</td><td>已提交并应用到状态机（对客户端可见）</td></tr>
<tr><td>Log Matching</td><td>如果不同日志中两个条目有相同 index 和 term，则它们存储相同 command，且之前所有条目都相同</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Raft vs Paxos</h3>
<table>
<tr><th>维度</th><th>Raft</th><th>Paxos</th></tr>
<tr><td>设计目标</td><td>可理解性（understandability）为首要目标</td><td>理论正确性优先</td></tr>
<tr><td>Leader</td><td>强 Leader，所有写请求通过 Leader</td><td>无固定 Leader（Multi-Paxos 可优化）</td></tr>
<tr><td>选举</td><td>随机超时 + 多数派投票，简单直观</td><td>复杂的提案-批准流程</td></tr>
<tr><td>日志复制</td><td>AppendEntries + Log Matching，易于实现</td><td>Paxos 日志复制理解难度大</td></tr>
<tr><td>实现复杂度</td><td>论文给出完整实现细节，易于正确实现</td><td>工程实现需大量补充和优化</td></tr>
<tr><td>生产应用</td><td>etcd、Consul、TiKV、CockroachDB</td><td>Chubby、Spanner（Multi-Paxos 变体）</td></tr>
</table>
<p>Raft 的核心设计哲学：将问题拆解为 Leader 选举、日志复制、安全三个相对独立的子问题，并通过"强 Leader"模型极大简化系统行为。</p>
</div>

## MVCC 多版本并发控制

<div class="card card-m">
<h3>MVCC 原理</h3>
<p>etcd 使用 MVCC 实现非阻塞读和乐观并发控制。每次写操作（PUT/DELETE）都会创建一个新的 key-value 版本，而不是原地覆盖：</p>
<table>
<tr><th>字段</th><th>含义</th></tr>
<tr><td>revision</td><td>全局单调递增整数，集群范围内每次事务 +1</td></tr>
<tr><td>create_revision</td><td>key 首次创建时的 revision</td></tr>
<tr><td>mod_revision</td><td>key 最后一次修改时的 revision</td></tr>
<tr><td>version</td><td>单个 key 内的版本号，每次修改 +1，删除后重置</td></tr>
</table>
<pre><code>初始: revision=1
PUT /registry/pods/default/pod-a → revision=2, mod_revision=2, version=1
PUT /registry/pods/default/pod-a → revision=3, mod_revision=3, version=2
DELETE /registry/pods/default/pod-a → revision=4 (tombstone)
PUT /registry/pods/default/pod-a → revision=5, create_revision=5, mod_revision=5, version=1
</code></pre>
</div>

<div class="card card-d">
<h3>为什么需要 MVCC？</h3>
<ol>
<li><strong>Watch 支持：</strong>客户端可以从任意历史 revision 开始订阅，MVCC 保留了历史版本，watch 不会因为并发写而丢失事件。</li>
<li><strong>非阻塞读：</strong>线性一致读只需确认当前 Leader 身份，不需要持锁；读操作可以直接访问已提交的历史版本，写不阻塞读。</li>
<li><strong>乐观并发控制：</strong>K8s 使用 resourceVersion（即 etcd revision）实现 CAS：UPDATE 请求携带 resourceVersion，如果服务器端最新 revision 不匹配则返回 409 Conflict，避免丢失更新。</li>
<li><strong>事务隔离：</strong>每个读事务看到的是某个 revision 时刻的一致性快照。</li>
</ol>
</div>

<div class="card card-s">
<h3>Compaction 与 Defragmentation</h3>
<p>MVCC 保留所有历史版本会导致存储空间持续增长，需要 compaction 清理旧版本：</p>
<table>
<tr><th>Compaction 模式</th><th>说明</th></tr>
<tr><td>Periodic</td><td>etcd 自动按时间周期 compact（默认开启，每小时保留最近 1 小时）</td></tr>
<tr><td>Revision</td><td>手动或自动 compact 到指定 revision 之前的所有旧版本</td></tr>
<tr><td>Manual</td><td><code>etcdctl compact &lt;revision&gt;</code> 手动触发</td></tr>
</table>
<p>Compaction 只是标记旧版本可回收，不会立即释放磁盘空间。需要 <strong>defragmentation</strong>（<code>etcdctl defrag</code>）来回收空闲空间，类似文件系统的碎片整理。注意 defrag 是阻塞操作，生产环境应逐节点滚动执行。</p>
<pre><code class="language-bash"># 查看当前 revision 和 DB 大小
etcdctl endpoint status --write-out=table
# 手动 compact
etcdctl compact $(etcdctl endpoint status --write-out=json | python -c 'import sys,json; print(json.load(sys.stdin)[0]["Status"]["header"]["revision"]-1000)')
# 逐节点 defrag（非 Leader 先执行，最后处理 Leader）
etcdctl defrag --endpoints=https://node-2:2379
</code></pre>
</div>

## Watch 机制

<div class="card card-m">
<h3>Watch 工作原理</h3>
<p>Watch 是 etcd 支撑 K8s 声明式控制循环的核心能力。客户端通过 <code>Watch(key, opts...)</code> 建立长连接（gRPC stream），接收后续发生的变更事件。</p>
<table>
<tr><th>特性</th><th>说明</th></tr>
<tr><td>从指定 revision 开始</td><td>支持从历史 revision 开始 watch，避免断连后丢事件</td></tr>
<tr><td>事件类型</td><td>PUT（新增/更新）、DELETE（删除，含 tombstone）</td></tr>
<tr><td>前缀 watch</td><td><code>WithPrefix()</code> 订阅某个前缀下所有 key 的变化（K8s Informer 用这个）</td></tr>
<tr><td>Progress Notify</td><td>即使没有事件也会周期性发送 progress 通知，客户端可用于检测连接存活</td></tr>
<tr><td>bookmark</td><td>K8s API Server 使用 bookmark 事件传递当前最新 revision，加速 watch 重连</td></tr>
</table>
<p>Watch 事件历史保存在 etcd 的 <strong>watch cache</strong>（环形缓冲区）中。如果客户端请求的 revision 已被 compact，etcd 会返回 <code>compaction revision error</code>，客户端必须重新 List 获取全量数据，再从新的 resourceVersion 开始 watch。这就是 K8s 中 "too old resource version" 错误的来源。</p>
</div>

## 性能与调优

<div class="card card-s">
<h3>boltDB 存储引擎</h3>
<p>etcd v3 使用 boltDB（LMDB 的 Go 变种）作为底层持久化存储。boltDB 是基于 B+tree 的嵌入式事务 KV 存储，特点是：</p>
<ul>
<li>单写者多读者模型（MVCC 实现），读事务无锁</li>
<li>使用 mmap 将 DB 文件映射到内存，读走内存，写通过 WAL + B+tree 落盘</li>
<li>每个写事务触发 B+tree 节点分裂/合并和 fsync，延迟直接受磁盘 IOPS 影响</li>
</ul>
<p><strong>关键约束：单 key-value 大小不要超过 1.5MB（官方推荐控制在 1MB 以内）</strong>。过大的 value 会导致：Raft 日志复制变慢、boltDB 页分裂频繁、写延迟飙升、内存压力增大。K8s 中过大的 ConfigMap/Secret/CRD 对象会直接影响 etcd 性能。</p>
</div>

<div class="card card-d">
<h3>关键调优参数</h3>
<table>
<tr><th>参数</th><th>默认值</th><th>说明</th></tr>
<tr><td><code>--quota-backend-bytes</code></td><td>2GB（建议 8GB）</td><td>后端 DB 大小上限；达到上限后 etcd 变为只读，触发 "mvcc: database space exceeded" 告警</td></tr>
<tr><td><code>--auto-compaction-mode</code></td><td>periodic</td><td>自动压缩模式，建议设为 periodic 配合 <code>--auto-compaction-retention=1h</code></td></tr>
<tr><td><code>--snapshot-count</code></td><td>100000</td><td>每提交多少条日志后触发一次 snapshot 并截断 Raft 日志</td></tr>
<tr><td><code>--heartbeat-interval</code></td><td>100ms</td><td>Leader 心跳间隔，跨机房部署可适当调大</td></tr>
<tr><td><code>--election-timeout</code></td><td>1000ms</td><td>选举超时，应至少为 heartbeat-interval 的 10 倍</td></tr>
<tr><td><code>--max-request-bytes</code></td><td>1.5MB</td><td>单请求最大字节数，限制大 value 写入</td></tr>
</table>
<pre><code class="language-yaml"># 生产环境 etcd 启动参数片段
- --quota-backend-bytes=8589934592  # 8GB
- --auto-compaction-mode=periodic
- --auto-compaction-retention=1h
- --snapshot-count=50000
- --max-request-bytes=10485760      # 10MB（如有大对象需求）
</code></pre>
</div>

<div class="card card-r">
<h3>磁盘性能是 etcd 性能的生命线</h3>
<p>etcd 写路径必须经过 WAL fsync，99 百分位延迟直接受磁盘 fsync 延迟影响。生产环境要求：</p>
<ul>
<li>使用本地 SSD（NVMe 最佳），禁止使用网络存储（NAS/SAN）</li>
<li>WAL 目录建议和 DB 文件放在不同磁盘（减少 IO 争抢）</li>
<li>fsync 延迟 P99 应 &lt; 10ms，超过 25ms 就会导致频繁 Leader 选举和 API 超时</li>
<li>使用 <code>etcdctl check perf</code> 验证集群性能基线</li>
</ul>
</div>

## K8s 集成细节

<div class="card card-m">
<h3>etcd 与 K8s 对象的映射</h3>
<pre><code>K8s 资源对象的 etcd key 格式：
/registry/&lt;resource-plural&gt;/&lt;namespace&gt;/&lt;name&gt;

示例：
/registry/pods/default/nginx-6799fc88d8-2xk4z
/registry/deployments/kube-system/coredns
/registry/nodes/node-1
/registry/configmaps/kube-system/kube-proxy

集群范围资源没有 namespace 段：
/registry/clusterroles/cluster-admin
/registry/namespaces/default
</code></pre>
<table>
<tr><th>K8s 概念</th><th>etcd 映射</th></tr>
<tr><td>resourceVersion</td><td>= etcd revision（全局）</td></tr>
<tr><td>object UID</td><td>etcd key 不直接存，value 的 metadata.uid 中</td></tr>
<tr><td>乐观并发</td><td>UPDATE 时携带 metadata.resourceVersion，与 etcd mod_revision 比对</td></tr>
<tr><td>List 分页</td><td>API Server 的 continue token 基于 etcd revision + key 范围</td></tr>
<tr><td>Watch 断连</td><td>API Server 从上次 resourceVersion 重新 watch，如果已 compact 则触发 relist</td></tr>
</table>
</div>

<div class="card card-s">
<h3>乐观并发控制（CAS）</h3>
<pre><code>// K8s UPDATE 语义（简化）
func Update(obj *Pod) error {
    // 1. 先 GET 获取当前对象及其 resourceVersion
    current := Get(obj.Name)
    
    // 2. 修改 spec/metadata（不碰 status 以外的非预期字段）
    obj.ResourceVersion = current.ResourceVersion // 携带版本号
    
    // 3. 发 UPDATE 请求到 API Server
    //    API Server 转成 etcd Txn：
    //    IF mod_revision == resourceVersion THEN put
    //    ELSE return 409 Conflict
    err := apiServer.Update(obj)
    
    if errors.IsConflict(err) {
        // 409: 别人已更新，必须重新 GET 再试
        return retry()
    }
    return err
}
</code></pre>
</div>

## 故障排查

<div class="card card-r">
<h3>常见 etcd 问题与排查</h3>
<table>
<tr><th>现象</th><th>根因</th><th>排查与修复</th></tr>
<tr><td>API Server 请求延迟突增、超时</td><td>etcd Leader 选举中（无 Leader 期间无法写）</td><td><code>etcdctl endpoint status</code> 查看是否无 Leader；检查网络分区、磁盘 IO 延迟</td></tr>
<tr><td>"mvcc: database space exceeded"</td><td>DB 达到 quota-backend-bytes 上限，etcd 进入只读模式</td><td>先获取/调大 quota，compact 旧版本，defrag 回收空间，最后解除告警 <code>etcdctl alarm disarm</code></td></tr>
<tr><td>慢 WAL 写（wal: sync duration 高）</td><td>磁盘 IO 瓶颈、磁盘故障、IO 争抢</td><td>检查 <code>iostat -x 1</code>、<code>dmesg</code> 磁盘错误；换 SSD、隔离 WAL 目录</td></tr>
<tr><td>频繁 Leader 切换</td><td>网络抖动、磁盘慢、CPU 节流、跨机房高延迟</td><td>检查网络 RTT、磁盘 fsync 延迟、CPU steal time；调整 heartbeat/election timeout</td></tr>
<tr><td>etcd OOM</td><td>大 value 过多、watch 连接数爆炸、boltdb mmap 过大</td><td>限制 ConfigMap/Secret/CRD 大小；检查 watch 客户端是否泄漏；控制 DB 大小</td></tr>
<tr><td>节点间数据不一致</td><td>少数派节点网络隔离恢复后追日志</td><td>正常情况 Raft 会自动同步；如果节点数据损坏，<code>etcdctl endpoint status</code> 检查 dbSize/raftIndex，必要时移除成员重新加入</td></tr>
</table>
<pre><code class="language-bash"># 快速诊断命令
export ETCDCTL_API=3
export ETCDCTL_ENDPOINTS=https://127.0.0.1:2379
export ETCDCTL_CACERT=/etc/kubernetes/pki/etcd/ca.crt
export ETCDCTL_CERT=/etc/kubernetes/pki/etcd/healthcheck-client.crt
export ETCDCTL_KEY=/etc/kubernetes/pki/etcd/healthcheck-client.key

# 集群状态
etcdctl endpoint status --write-out=table
etcdctl endpoint health --write-out=table

# 告警查看
etcdctl alarm list

# 性能检测
etcdctl check perf

# 查看 Leader
etcdctl endpoint status --write-out=json | jq -r '.[] | "\(.Endpoint): \(.Status.leaderId == .Status.header.memberId and "LEADER" or "FOLLOWER")"'
</code></pre>
</div>

<div class="card card-w">
<h3>Raft 脑裂问题</h3>
<p>网络分区可能导致集群中出现两个节点各自认为自己是 Leader（同一 term 内不会发生；不同 term 可能短暂存在）。Raft 通过以下机制保证安全：</p>
<ol>
<li><strong>多数派原则：</strong>任何写操作必须得到多数派确认才能 committed。少数派分区的 Leader 无法提交新日志。</li>
<li><strong>term 校验：</strong>分区恢复后，拥有更高 term 的 Leader 胜出，旧 Leader 的未提交日志会被覆盖。</li>
<li><strong>Leader lease：</strong>etcd 使用 Leader lease（基于选举超时）保证线性一致读，少数派 Leader 即使存在也无法提供一致读。</li>
</ol>
<p><strong>生产环境必须部署奇数节点（3/5/7）</strong>，且 Raft 网络必须低延迟、高可靠。跨可用区部署可容忍单个 AZ 故障，但跨地域部署需谨慎（高 RTT 会导致频繁选举）。</p>
</div>

## 高频问答

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: etcd 为什么适合做 K8s 的存储？</div>
<div class="qa-a">
<p>四个核心原因：</p>
<div class="qa-section"><div class="qa-section-title">1. 强一致性</div><p>Raft 协议保证线性一致读（linearizable），API Server 读到的一定是已提交的最新数据，不会出现脏读。这对 K8s 的状态协调至关重要——Controller/Scheduler 的决策必须基于最新的集群状态。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Watch 机制</div><p>etcd 原生支持从任意 revision 开始的持续 watch，这是 K8s Informer 机制的基础。Controller 通过 watch 实时感知对象变化，不需要轮询，延迟低且 API Server 压力小。</p></div>
<div class="qa-section"><div class="qa-section-title">3. MVCC + 乐观并发</div><p>MVCC 提供非阻塞读写，revision 机制天然支撑 K8s 的 resourceVersion 乐观并发控制——多个 Controller 更新同一个对象时不会丢失更新。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 简洁可靠</div><p>etcd 是专门为分布式协调设计的 KV 存储，API 简单、实现成熟、社区验证充分。相比使用通用数据库（如 MySQL），etcd 在一致性保证、watch 能力、集群运维方面更匹配 K8s 的需求。</p></div>
<div class="qa-summary">面试口径：强一致 + watch + MVCC 乐观并发 + 成熟可靠，恰好匹配 K8s 声明式协调系统对存储的全部需求。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: resourceVersion 和 etcd revision 是什么关系？</div>
<div class="qa-a">
<p><strong>resourceVersion 就是 etcd 的全局 revision</strong>，它们本质上是同一个值——etcd 中每次写操作（PUT/DELETE/Txn）都会让全局 revision 单调递增，API Server 把这个值透传到对象的 metadata.resourceVersion 字段。</p>
<p>关键语义：</p>
<ul>
<li>resourceVersion 在对象创建时设置，每次更新时变化。</li>
<li>它是全局的，不是 per-object 的——修改 Pod A 也会让 Pod B 的 resourceVersion（如果在 list/watch 响应中）体现为更高的 revision（但单个对象的 mod_revision 只反映自己最后被修改的 revision）。</li>
<li>API Server 的 list 响应带 resourceVersion，watch 请求从该版本开始，断连重连时传上次的 resourceVersion 即可续传。</li>
<li>UPDATE/PATCH 请求如果携带的 resourceVersion 与服务器端 mod_revision 不一致，返回 409 Conflict。</li>
<li>注意：不要把 resourceVersion 当作数字比较大小来做业务逻辑，只能用于传回去做条件更新或 watch 续传。</li>
</ul>
<div class="qa-summary">面试口径：resourceVersion = etcd revision，是全局单调递增的；用于乐观并发控制（CAS）和 watch 断点续传。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: etcd 满了怎么办（mvcc: database space exceeded）？</div>
<div class="qa-a">
<p>这是 etcd DB 达到 <code>--quota-backend-bytes</code> 上限（默认 2GB）的保护性告警，etcd 会进入只读模式拒绝写入。修复步骤：</p>
<div class="qa-section"><div class="qa-section-title">1. 紧急恢复可写</div><p>如果只是配额太小且磁盘还有空间，可以先调大配额（需要重启 etcd），或者临时调大后 compact + defrag 再降回来。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Compact 旧版本</div><p>MVCC 积累的历史版本是 DB 增长的主因。执行 <code>etcdctl compact &lt;revision&gt;</code>（或依赖自动 compact），清理旧版本记录。</p></div>
<div class="qa-section"><div class="qa-section-title">3. Defrag 回收空间</div><p>compact 只是标记可回收，不会释放磁盘空间。需要逐节点执行 <code>etcdctl defrag</code>（先 Follower，最后 Leader，避免集群不可用）。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 解除告警</div><p><code>etcdctl alarm disarm</code> 解除 NOSPACE 告警，etcd 恢复可写。</p></div>
<div class="qa-section"><div class="qa-section-title">5. 预防措施</div><p>生产环境设置 <code>--auto-compaction-mode=periodic --auto-compaction-retention=1h</code>，设置合理的 quota（建议 8GB），监控 <code>etcd_mvcc_db_total_size_in_bytes</code> 和 <code>etcd_server_quota_backend_bytes</code>，定期检查 defrag 需求。避免存储大 value（>1MB）。</p></div>
<div class="qa-summary">面试口径：compact 清理历史版本 → defrag 回收磁盘 → alarm disarm 恢复写入，根因预防靠自动 compact + 监控 + 控制 value 大小。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Raft 脑裂怎么处理？</div>
<div class="qa-a">
<p>Raft 协议在设计上已经避免了脑裂导致数据不一致，但网络分区时可能出现短暂的"双 Leader"现象：</p>
<div class="qa-section"><div class="qa-section-title">Raft 的安全保证</div><p>同一 term 内最多只有一个 Leader；新 Leader 当选必须包含所有已提交的日志；少数派分区的 Leader 无法获得多数派 ACK，因此不能 commit 任何新日志。这意味着即使出现网络分区，只有多数派侧的 Leader 能处理写请求，少数派侧的写都会失败，不会出现数据分叉。</p></div>
<div class="qa-section"><div class="qa-section-title">网络分区恢复</div><p>分区恢复后，term 更高的 Leader 会成为合法 Leader。旧 Leader 发现更高的 term 后会退回 Follower，其未提交的日志会被新 Leader 的日志覆盖。对于已经返回客户端成功的写（即已 commit），一定存在于多数派节点上，新 Leader 一定包含这些日志，不会丢失。</p></div>
<div class="qa-section"><div class="qa-section-title">读请求的处理</div><p>etcd 默认使用 linearizable read：Leader 在处理读请求前先通过心跳确认自己仍是合法 Leader（大部分情况下用 ReadIndex 优化，不需要心跳盘），因此不会从少数派侧的旧 Leader 读到陈旧数据。</p></div>
<div class="qa-section"><div class="qa-section-title">运维实践</div><p>部署奇数节点（3/5）；避免跨地域部署；监控 etcd Leader 切换频率（<code>etcd_server_leader_changes_seen_total</code>）；保证 Raft 网络低延迟高可靠；使用 Learner 节点做跨区域灾备而非投票成员。</p></div>
<div class="qa-summary">面试口径：Raft 通过多数派投票、term 机制和日志匹配保证不会发生脑裂数据不一致；少数派分区的旧 Leader 无法提交新日志，分区恢复后自动收敛。</div>
</div>
</div>
