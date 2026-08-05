## 一句话结论

多线程程序卡死时，先保存现场，再用 GDB 查看所有线程栈和锁等待关系；崩溃问题优先依赖带符号的 Core Dump。调试目标不是找到“某个线程在 mutex”，而是重建谁持有锁、谁等待锁以及为什么没有前进。

## 诊断入口

```bash
gdb -p <pid>
(gdb) set pagination off
(gdb) info threads
(gdb) thread apply all bt
(gdb) thread <id>
(gdb) frame <n>
(gdb) info locals
```

Attach 会暂停进程，生产环境必须先确认影响；如果不能暂停，可先使用 `gcore`、Core Dump、采样 Profiler 或受控副本保存现场。

## 排查路径

```flow
确认现象 | CPU 忙循环、阻塞、死锁还是进程崩溃
保存现场 | PID、日志、线程数、Core、构建版本和符号
查看所有线程栈 | 寻找 futex、mutex、condition_variable、join、I/O
重建等待关系 | 谁持锁、谁等锁、锁顺序是否反转
结合源码验证 | 生命周期、异常路径、遗漏 notify、数据竞争
最小化复现 | Sanitizer、压力测试、故障注入
```

## 典型现象

| 现场 | 可能原因 | 下一步 |
|---|---|---|
| 多个线程停在 `pthread_mutex_lock` | 锁顺序反转或持锁线程异常 | 找持锁线程栈和获取顺序 |
| 全部 Worker 停在 `condition_variable::wait` | 没有生产者或漏掉 notify | 检查 predicate 和生产者状态 |
| 主线程卡在 `join` | 子线程未退出 | 查看子线程阻塞点与停止条件 |
| 单线程 CPU 100% | 忙循环、无退避重试 | 查看热点栈并用 perf 辅助 |
| Core 中指针非法 | 生命周期、越界、Use-after-free | ASan/UBSan 复现并检查所有权 |

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何判断是死锁而不是正常等待？</div>
<div class="qa-a"><p>正常等待应存在能够推进状态的生产者、I/O 或定时事件；死锁则形成循环等待，所有相关线程都无法产生解除条件。要结合多次线程栈、锁持有关系、队列长度和业务进度判断，不能只因为看到 <code>futex</code> 就下结论。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 智能指针的知识放在哪里复习？</div>
<div class="qa-a"><p>所有权和 RAII 放在“C++ 系统编程/内存管理”，<code>shared_ptr</code> 控制块、线程安全边界和 <code>weak_ptr</code> 放在“现代 C++”。编译、链接与动态库问题统一放在“Binary 与编译链接”，避免把三个主题混成一页。</p></div>
</div>
