---
name: system-automation
description: 跨平台系统自动化技能。处理文件系统操作、进程管理、定时任务、资源监控、跨平台脚本编写。当需要执行操作系统级别任务、管理进程、监控系统资源、创建自动化流水线时使用此技能。
---

# 系统自动化

## 概述

提供跨平台（macOS、Linux、Windows）的系统级自动化能力。包含文件系统管理、进程控制、系统资源监控、定时任务调度、网络操作等核心自动化模式。目标是编写一次，多平台运行。

## 何时使用此技能

1. **文件与目录操作**：批量重命名、归档、清理、同步
2. **进程管理**：启动/停止服务、监控资源占用、进程优先级调整
3. **定时任务**：Cron、Launchd、Task Scheduler 配置
4. **资源监控**：CPU、内存、磁盘、网络使用率监控与报警
5. **网络操作**：端口扫描、网络测试、服务健康检查
6. **系统配置**：环境变量、用户管理、权限设置
7. **自动化流水线**：多步骤任务编排，依赖处理，错误恢复

## 核心能力

### 1. 跨平台脚本编写

**原则**：优先使用 Python 标准库，其次使用 shell 命令（确保 POSIX 兼容）。对于特定平台特性，使用条件分支检测操作系统。

**检测平台示例**：
```python
import platform
import subprocess
import sys

def is_macos():
    return platform.system() == 'Darwin'

def is_linux():
    return platform.system() == 'Linux'

def is_windows():
    return platform.system() == 'Windows'
```

**执行命令的通用函数**：
```python
def run_cmd(cmd, shell=False, timeout=30):
    """跨平台执行命令"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, '', f'Command timeout after {timeout}s'
    except Exception as e:
        return -1, '', str(e)
```

### 2. 文件系统操作

**统一路径处理**：
```python
from pathlib import Path
import os

def normalize_path(path):
    """统一路径格式，处理 ~ 和相对路径"""
    expanded = os.path.expanduser(str(path))
    return Path(expanded).resolve()
```

**批量文件操作模式**：
- 查找文件：`glob` 或 `os.walk`
- 文件筛选：按扩展名、大小、修改时间
- 批量处理：并行或串行处理大文件集

参考 `scripts/batch_file_ops.py` 实现。

### 3. 进程管理

**获取进程信息**：
```python
def get_process_info(pid=None):
    """获取进程信息"""
    if is_windows():
        # Windows 实现
        pass
    else:
        # Unix/Linux/macOS 实现
        import psutil
        return psutil.Process(pid) if pid else None
```

**资源监控**：
- CPU 使用率、内存占用、IO 统计
- 进程树分析、依赖关系
- 异常进程检测与告警

### 4. 定时任务调度

**跨平台定时任务**：
```python
def schedule_task(platform, schedule, command, task_name):
    """创建定时任务"""
    if platform == 'macos':
        # Launchd plist 生成
        create_launchd_plist(task_name, schedule, command)
    elif platform == 'linux':
        # Cron 配置
        add_cron_job(schedule, command)
    elif platform == 'windows':
        # Task Scheduler XML
        create_scheduled_task(task_name, schedule, command)
```

参考 `scripts/cross_platform_scheduler.py`。

### 5. 系统资源监控

**监控指标**：
- CPU：使用率、负载、温度（如果可用）
- 内存：使用率、交换空间、进程分布
- 磁盘：空间、IOPS、读写速度
- 网络：带宽、连接数、延迟

**告警机制**：
- 阈值检测
- 趋势分析
- 历史数据对比

### 6. 自动化流水线

**流水线模式**：
1. **收集阶段**：获取输入数据/配置
2. **处理阶段**：核心业务逻辑
3. **验证阶段**：结果检查
4. **输出阶段**：结果交付
5. **清理阶段**：临时资源释放

**错误处理策略**：
- 重试机制：指数退避
- 回滚操作：事务性变更
- 日志记录：结构化日志
- 通知机制：失败报警

## 工作流决策树

### 用户请求分析

1. **是否涉及文件操作？**
   - 是 → 检查 `scripts/batch_file_ops.py` 是否适用
   - 否 → 继续

2. **是否涉及进程管理？**
   - 是 → 参考进程管理部分，使用 `psutil` 库
   - 否 → 继续

3. **是否涉及定时任务？**
   - 是 → 参考定时任务部分，选择合适的调度器
   - 否 → 继续

4. **是否涉及资源监控？**
   - 是 → 实现监控循环，设置阈值
   - 否 → 继续

5. **是否为复杂多步骤任务？**
   - 是 → 设计自动化流水线
   - 否 → 编写直接脚本

### 平台适配策略

1. **检测用户操作系统**
2. **如果脚本需跨平台运行：**
   - 优先使用 Python 标准库
   - 条件判断处理平台差异
   - 提供替代方案或降级逻辑
3. **如果仅针对特定平台：**
   - 利用平台特有 API
   - 明确告知用户限制

## 最佳实践

### 安全性
- 永远验证用户输入
- 避免以 root 权限运行脚本
- 敏感信息使用环境变量
- 日志中不记录密码/密钥

### 可靠性
- 实现完善的错误处理
- 添加超时机制
- 保持幂等性（可重复执行）
- 提供回滚能力

### 性能
- 大文件集使用并行处理
- 避免不必要的系统调用
- 缓存重复计算结果
- 监控资源消耗

### 可维护性
- 模块化设计
- 清晰的注释
- 版本控制
- 配置与代码分离

## 脚本参考

### `scripts/batch_file_ops.py`
批量文件操作工具。支持：
- 批量重命名（模式匹配、序号生成）
- 文件过滤（扩展名、大小、日期）
- 目录同步（差异复制）
- 归档操作（压缩、解压）

### `scripts/cross_platform_scheduler.py`
跨平台定时任务调度器。支持：
- macOS：Launchd plist 生成
- Linux：Crontab 管理
- Windows：Task Scheduler XML
- 任务状态监控

### `scripts/resource_monitor.py`
系统资源监控工具。提供：
- 实时监控仪表板
- 历史数据记录
- 阈值告警
- 资源使用报告

## 参考文档

详见 `references/` 目录下的：
- `cross_platform_patterns.md`：跨平台编程模式
- `system_apis.md`：各平台系统 API 对比
- `automation_best_practices.md`：自动化最佳实践
- `security_guidelines.md`：自动化安全指南

## 资产

`assets/` 目录包含：
- `templates/`：脚本模板
- `config_examples/`：配置文件示例
- `monitoring_dashboards/`：监控面板模板

---

**提示**：使用此技能时，首先确定任务范围和平台约束，选择合适的自动化模式。复杂任务建议先设计流程图，再逐步实现。