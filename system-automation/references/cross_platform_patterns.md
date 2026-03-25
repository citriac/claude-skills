# 跨平台编程模式

## 目录
1. [平台检测](#平台检测)
2. [路径处理](#路径处理)
3. [命令执行](#命令执行)
4. [文件系统操作](#文件系统操作)
5. [进程管理](#进程管理)
6. [网络操作](#网络操作)
7. [定时任务](#定时任务)
8. [错误处理](#错误处理)
9. [性能优化](#性能优化)

## 平台检测

### 基础检测
```python
import platform
import os
import sys

def get_platform_info():
    """获取完整的平台信息"""
    return {
        'system': platform.system(),  # 'Darwin', 'Linux', 'Windows'
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'architecture': platform.architecture()[0],
        'python_version': platform.python_version()
    }

def is_macos():
    return platform.system() == 'Darwin'

def is_linux():
    return platform.system() == 'Linux'

def is_windows():
    return platform.system() == 'Windows'

def is_wsl():
    """检测是否在 WSL (Windows Subsystem for Linux) 中"""
    if is_linux():
        try:
            with open('/proc/version', 'r') as f:
                return 'microsoft' in f.read().lower()
        except:
            pass
    return False
```

### 环境变量检测
```python
def get_env_info():
    """获取环境信息"""
    info = {}
    
    # 常见环境变量
    env_vars = ['HOME', 'USER', 'PATH', 'SHELL', 'TERM', 'TEMP', 'TMP']
    for var in env_vars:
        if var in os.environ:
            info[var] = os.environ[var]
    
    # 特殊检测
    if is_windows():
        info['comspec'] = os.environ.get('COMSPEC', '')
        info['windir'] = os.environ.get('WINDIR', '')
    elif is_macos():
        info['macos_version'] = platform.mac_ver()[0]
    
    return info
```

## 路径处理

### 统一路径格式
```python
from pathlib import Path
import os

def normalize_path(path_str):
    """
    统一路径格式
    处理：~扩展、相对路径、路径分隔符、大小写（Windows）
    """
    # 扩展用户目录
    expanded = os.path.expanduser(str(path_str))
    
    # 解析为 Path 对象
    path = Path(expanded)
    
    # 处理相对路径
    if not path.is_absolute():
        path = Path.cwd() / path
    
    # 规范化路径（移除 . 和 ..）
    path = path.resolve()
    
    # Windows 上统一为小写（可选）
    if is_windows():
        return Path(str(path).lower())
    
    return path

def to_posix_path(path):
    """转换为 POSIX 路径（/分隔符）"""
    path_str = str(path)
    if is_windows():
        # 将 Windows 路径转换为 POSIX 风格
        # C:\Users\name → /c/Users/name
        if path_str[1:3] == ':\\':
            drive = path_str[0].lower()
            rest = path_str[3:].replace('\\', '/')
            return f'/{drive}/{rest}'
        return path_str.replace('\\', '/')
    return path_str

def to_native_path(path):
    """转换为本地路径格式"""
    path_str = str(path)
    if is_windows():
        # 如果已经是 Windows 格式，直接返回
        if '\\' in path_str or ':' in path_str:
            return path_str
        # 将 POSIX 路径转换为 Windows 格式
        # /c/Users/name → C:\Users\name
        if path_str.startswith('/') and len(path_str) > 2 and path_str[2] == '/':
            drive = path_str[1].upper()
            rest = path_str[3:].replace('/', '\\')
            return f'{drive}:\\{rest}'
        return path_str.replace('/', '\\')
    return path_str
```

### 路径操作工具
```python
def ensure_dir(path):
    """确保目录存在"""
    path = normalize_path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_temp_path(prefix='tmp_', suffix='', directory=None):
    """获取临时文件路径"""
    import tempfile
    if directory:
        directory = normalize_path(directory)
        ensure_dir(directory)
    
    if is_windows():
        # Windows 需要处理长路径问题
        return tempfile.mktemp(prefix=prefix, suffix=suffix, dir=directory)
    else:
        return tempfile.mktemp(prefix=prefix, suffix=suffix, dir=directory)

def get_config_path(app_name, filename=None):
    """获取应用配置路径（跨平台）"""
    if is_windows():
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData/Roaming'))
    elif is_macos():
        base = Path.home() / 'Library/Application Support'
    else:  # Linux/Unix
        base = Path.home() / '.config'
    
    app_dir = base / app_name
    ensure_dir(app_dir)
    
    if filename:
        return app_dir / filename
    return app_dir
```

## 命令执行

### 基础命令执行
```python
import subprocess
import shlex

def run_command(cmd, shell=False, timeout=30, cwd=None, env=None, capture_output=True):
    """
    跨平台执行命令
    
    Args:
        cmd: 命令字符串或列表
        shell: 是否使用 shell 执行
        timeout: 超时时间（秒）
        cwd: 工作目录
        env: 环境变量
        capture_output: 是否捕获输出
    
    Returns:
        (returncode, stdout, stderr)
    """
    # 命令预处理
    if isinstance(cmd, str):
        if shell:
            # 字符串命令直接使用
            pass
        else:
            # 非 shell 模式下需要解析
            cmd = shlex.split(cmd)
    
    # 环境变量设置
    if env is None:
        env = os.environ.copy()
    
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            cwd=cwd,
            env=env,
            capture_output=capture_output,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    
    except subprocess.TimeoutExpired:
        return -1, '', f'Command timeout after {timeout}s'
    
    except FileNotFoundError:
        return -1, '', f'Command not found: {cmd[0] if isinstance(cmd, list) else cmd}'
    
    except Exception as e:
        return -1, '', str(e)

def run_command_with_pipe(cmd1, cmd2, timeout=30):
    """管道执行两个命令"""
    import subprocess
    
    try:
        p1 = subprocess.Popen(
            cmd1,
            stdout=subprocess.PIPE,
            shell=isinstance(cmd1, str)
        )
        p2 = subprocess.Popen(
            cmd2,
            stdin=p1.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=isinstance(cmd2, str)
        )
        
        p1.stdout.close()  # 允许 p1 接收 SIGPIPE
        stdout, stderr = p2.communicate(timeout=timeout)
        
        # 等待两个进程完成
        p1.wait(timeout=5)
        
        return p2.returncode, stdout.decode('utf-8', errors='replace'), stderr.decode('utf-8', errors='replace')
    
    except Exception as e:
        return -1, '', str(e)
```

### 平台特定命令
```python
def get_platform_command(base_cmd, alternatives=None):
    """
    获取平台特定的命令
    
    Args:
        base_cmd: 基础命令名
        alternatives: 各平台备选命令
    
    Returns:
        适用于当前平台的命令
    """
    if alternatives is None:
        alternatives = {}
    
    # 默认映射
    default_alternatives = {
        'ls': {'windows': 'dir'},
        'pwd': {'windows': 'cd'},
        'cat': {'windows': 'type'},
        'grep': {'windows': 'findstr'},
        'cp': {'windows': 'copy'},
        'mv': {'windows': 'move'},
        'rm': {'windows': 'del'},
    }
    
    # 合并映射
    all_alternatives = {**default_alternatives.get(base_cmd, {}), **alternatives}
    
    if is_windows():
        return all_alternatives.get('windows', base_cmd)
    else:
        return base_cmd

def which(program):
    """跨平台的 which 命令"""
    def is_exe(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)
    
    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        # 检查 PATH 环境变量
        path = os.environ.get('PATH', '')
        
        if is_windows():
            path = path.split(';')
            exe_exts = ['.exe', '.bat', '.cmd', '']
        else:
            path = path.split(':')
            exe_exts = ['']
        
        for ext in exe_exts:
            exe_name = program + ext
            for dir in path:
                exe_path = os.path.join(dir, exe_name)
                if is_exe(exe_path):
                    return exe_path
    
    return None
```

## 文件系统操作

### 权限处理
```python
def get_file_permissions(path):
    """获取文件权限（跨平台）"""
    path = normalize_path(path)
    
    try:
        stat = os.stat(path)
        
        if is_windows():
            # Windows: 简化权限表示
            import stat as stat_module
            permissions = ''
            if stat.st_mode & stat_module.S_IREAD:
                permissions += 'r'
            if stat.st_mode & stat_module.S_IWRITE:
                permissions += 'w'
            if stat.st_mode & stat_module.S_IEXEC:
                permissions += 'x'
            return permissions
        
        else:
            # Unix: 完整权限表示
            import stat as stat_module
            modes = [
                stat_module.S_IRUSR, stat_module.S_IWUSR, stat_module.S_IXUSR,
                stat_module.S_IRGRP, stat_module.S_IWGRP, stat_module.S_IXGRP,
                stat_module.S_IROTH, stat_module.S_IWOTH, stat_module.S_IXOTH
            ]
            
            perm_str = ''
            for mode in modes:
                perm_str += 'r' if mode & stat_module.S_IRUSR else \
                           'w' if mode & stat_module.S_IWUSR else \
                           'x' if mode & stat_module.S_IXUSR else \
                           'r' if mode & stat_module.S_IRGRP else \
                           'w' if mode & stat_module.S_IWGRP else \
                           'x' if mode & stat_module.S_IXGRP else \
                           'r' if mode & stat_module.S_IROTH else \
                           'w' if mode & stat_module.S_IWOTH else \
                           'x' if mode & stat_module.S_IXOTH else '-'
            
            return perm_str
    
    except OSError:
        return None

def set_file_permissions(path, mode):
    """设置文件权限（跨平台）"""
    path = normalize_path(path)
    
    if is_windows():
        # Windows: 使用 icacls 或 attrib
        # 简化实现，仅设置只读属性
        if 'w' not in mode:
            import stat as stat_module
            os.chmod(path, stat_module.S_IREAD)
        else:
            import stat as stat_module
            os.chmod(path, stat_module.S_IREAD | stat_module.S_IWRITE)
    else:
        # Unix: 使用 chmod
        import stat as stat_module
        
        # 解析权限字符串（如 'rwxr-xr--'）
        mode_val = 0
        if len(mode) >= 1 and mode[0] == 'r':
            mode_val |= stat_module.S_IRUSR
        if len(mode) >= 2 and mode[1] == 'w':
            mode_val |= stat_module.S_IWUSR
        if len(mode) >= 3 and mode[2] == 'x':
            mode_val |= stat_module.S_IXUSR
        
        if len(mode) >= 4 and mode[3] == 'r':
            mode_val |= stat_module.S_IRGRP
        if len(mode) >= 5 and mode[4] == 'w':
            mode_val |= stat_module.S_IWGRP
        if len(mode) >= 6 and mode[5] == 'x':
            mode_val |= stat_module.S_IXGRP
        
        if len(mode) >= 7 and mode[6] == 'r':
            mode_val |= stat_module.S_IROTH
        if len(mode) >= 8 and mode[7] == 'w':
            mode_val |= stat_module.S_IWOTH
        if len(mode) >= 9 and mode[8] == 'x':
            mode_val |= stat_module.S_IXOTH
        
        os.chmod(path, mode_val)
```

### 文件操作
```python
def safe_delete(path, max_retries=3):
    """安全删除文件（带重试）"""
    path = normalize_path(path)
    
    for attempt in range(max_retries):
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
            return True
        
        except PermissionError:
            if attempt < max_retries - 1:
                import time
                time.sleep(0.1 * (2 ** attempt))  # 指数退避
            else:
                raise
        
        except Exception as e:
            print(f"Delete failed: {e}")
            return False
    
    return False

def copy_with_metadata(source, dest):
    """复制文件并保留元数据（跨平台）"""
    import shutil
    import stat
    
    source = normalize_path(source)
    dest = normalize_path(dest)
    
    # 复制文件内容
    shutil.copy2(source, dest)
    
    if not is_windows():
        # Unix: 尝试保留原始权限
        try:
            src_stat = os.stat(source)
            os.chmod(dest, src_stat.st_mode & 0o777)
        except:
            pass
    
    return dest
```

## 进程管理

### 使用 psutil（推荐）
```python
try:
    import psutil
    
    def get_process_list(sort_by='cpu', limit=10):
        """获取进程列表"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # 排序
        if sort_by == 'cpu':
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        elif sort_by == 'memory':
            processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
        elif sort_by == 'name':
            processes.sort(key=lambda x: x.get('name', '').lower())
        
        return processes[:limit]
    
    def kill_process_tree(pid):
        """杀死进程及其子进程"""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # 先杀子进程
            for child in children:
                try:
                    child.terminate()
                except:
                    pass
            
            # 再杀父进程
            parent.terminate()
            
            # 等待进程结束
            gone, alive = psutil.wait_procs([parent] + children, timeout=5)
            
            # 强制杀死存活的进程
            for p in alive:
                try:
                    p.kill()
                except:
                    pass
            
            return True
        
        except psutil.NoSuchProcess:
            return True  # 进程已不存在
        except Exception as e:
            print(f"Failed to kill process tree: {e}")
            return False

except ImportError:
    # psutil 不可用时的备选方案
    pass
```

### 原生进程管理
```python
def get_process_info_native(pid=None):
    """原生方式获取进程信息"""
    if is_windows():
        cmd = ['tasklist', '/fo', 'csv', '/nh']
        if pid:
            cmd.extend(['/fi', f'PID eq {pid}'])
    else:
        cmd = ['ps', 'aux']
        if pid:
            cmd = ['ps', '-p', str(pid), '-o', 'pid,user,%cpu,%mem,command']
    
    returncode, stdout, stderr = run_command(cmd)
    if returncode == 0:
        return stdout
    return None
```

## 网络操作

### 网络检测
```python
def check_network_connectivity(host='8.8.8.8', port=53, timeout=3):
    """检测网络连通性"""
    import socket
    
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

def get_local_ip():
    """获取本地 IP 地址"""
    import socket
    
    try:
        # 创建一个 UDP 套接字连接到外部服务器（不实际发送数据）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            # 备选方案：获取主机名对应的 IP
            return socket.gethostbyname(socket.gethostname())
        except:
            return '127.0.0.1'
```

### 端口检测
```python
def check_port(host='localhost', port=80, timeout=2):
    """检测端口是否开放"""
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except:
        return False

def find_available_port(start_port=8000, end_port=9000):
    """查找可用端口"""
    import socket
    
    for port in range(start_port, end_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('localhost', port))
                return port
        except OSError:
            continue
    
    return None
```

## 定时任务

### Cron 任务（Unix/macOS）
```python
def add_cron_job(schedule, command, comment=None):
    """添加 Cron 任务"""
    if not is_windows():
        cron_line = f"{schedule} {command}"
        if comment:
            cron_line = f"# {comment}\n{cron_line}"
        
        # 添加到用户 crontab
        import tempfile
        
        # 获取当前 crontab
        returncode, stdout, stderr = run_command(['crontab', '-l'])
        current_crontab = stdout if returncode == 0 else ""
        
        # 添加新任务
        new_crontab = current_crontab.strip() + "\n" + cron_line + "\n"
        
        # 写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(new_crontab)
            temp_file = f.name
        
        try:
            # 安装新的 crontab
            run_command(['crontab', temp_file])
            return True
        finally:
            os.unlink(temp_file)
    
    return False
```

### Task Scheduler（Windows）
```python
def add_windows_task(task_name, schedule, command):
    """添加 Windows 计划任务"""
    if is_windows():
        # 使用 schtasks 命令
        # 简化实现，实际需要根据 schedule 参数生成 XML
        cmd = [
            'schtasks', '/create', '/tn', task_name,
            '/tr', command, '/sc', 'daily', '/st', '00:00'
        ]
        
        returncode, stdout, stderr = run_command(cmd)
        return returncode == 0
    
    return False
```

## 错误处理

### 异常包装
```python
class PlatformError(Exception):
    """平台相关错误"""
    def __init__(self, message, platform_info=None):
        super().__init__(message)
        self.platform_info = platform_info or get_platform_info()

def handle_platform_specific(func, *args, **kwargs):
    """
    处理平台特定函数
    
    Args:
        func: 函数字典，键为平台名
        *args: 函数参数
        **kwargs: 函数关键字参数
    
    Returns:
        函数执行结果
    """
    platform = platform.system().lower()
    
    if platform in func:
        return func[platform](*args, **kwargs)
    elif 'default' in func:
        return func['default'](*args, **kwargs)
    else:
        raise PlatformError(f"No implementation for platform: {platform}")
```

### 重试机制
```python
import time
from functools import wraps

def retry_on_exception(max_attempts=3, delay=1, backoff=2, exceptions=(Exception,)):
    """
    异常重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 退避倍数
        exceptions: 需要重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff ** attempt)
                        print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"All {max_attempts} attempts failed")
                        raise
            
            raise last_exception  # 如果循环结束但未返回
        
        return wrapper
    return decorator
```

## 性能优化

### 并行处理
```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

def parallel_map(func, items, max_workers=None, use_processes=False):
    """
    并行映射函数
    
    Args:
        func: 要执行的函数
        items: 数据项列表
        max_workers: 最大工作线程/进程数
        use_processes: 是否使用进程（CPU 密集型）
    
    Returns:
        结果列表（保持原始顺序）
    """
    if max_workers is None:
        max_workers = multiprocessing.cpu_count()
    
    Executor = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
    
    with Executor(max_workers=max_workers) as executor:
        # 提交任务
        future_to_item = {executor.submit(func, item): item for item in items}
        
        # 收集结果
        results = []
        for future in future_to_item:
            try:
                results.append(future.result())
            except Exception as e:
                results.append(e)
        
        return results

def batch_process(items, batch_size=100, func=None):
    """批量处理"""
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        if func:
            batch_results = parallel_map(func, batch)
            results.extend(batch_results)
        else:
            results.extend(batch)
        
        print(f"Processed {min(i + batch_size, len(items))}/{len(items)} items")
    
    return results
```

### 缓存优化
```python
import hashlib
import pickle
from functools import lru_cache

def get_cache_key(*args, **kwargs):
    """生成缓存键"""
    # 序列化参数
    data = pickle.dumps((args, sorted(kwargs.items())))
    
    # 生成哈希
    return hashlib.md5(data).hexdigest()

def disk_cache(cache_dir=None, max_age_seconds=3600):
    """
    磁盘缓存装饰器
    
    Args:
        cache_dir: 缓存目录
        max_age_seconds: 缓存最大年龄（秒）
    """
    if cache_dir is None:
        cache_dir = get_temp_path('cache_')
        ensure_dir(cache_dir)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = get_cache_key(*args, **kwargs)
            cache_file = cache_dir / f"{func.__name__}_{cache_key}.pkl"
            
            # 检查缓存是否有效
            if cache_file.exists():
                file_age = time.time() - cache_file.stat().st_mtime
                if file_age < max_age_seconds:
                    try:
                        with open(cache_file, 'rb') as f:
                            return pickle.load(f)
                    except:
                        pass  # 缓存读取失败，重新计算
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 保存到缓存
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(result, f)
            except:
                pass  # 缓存写入失败
            
            return result
        
        return wrapper
    return decorator
```

## 总结

跨平台编程的关键原则：

1. **检测为先**：始终检测当前平台和环境
2. **抽象接口**：定义统一的接口，背后实现平台特定逻辑
3. **优雅降级**：当某个平台不支持某个功能时，提供替代方案
4. **充分测试**：在所有目标平台上测试代码
5. **明确文档**：记录平台差异和限制

通过遵循这些模式，可以编写出健壮、可维护的跨平台自动化脚本。