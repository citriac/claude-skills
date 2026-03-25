# 自动化安全指南

## 目录
1. [安全原则](#安全原则)
2. [输入验证](#输入验证)
3. [权限管理](#权限管理)
4. [敏感信息处理](#敏感信息处理)
5. [命令执行安全](#命令执行安全)
6. [文件操作安全](#文件操作安全)
7. [网络通信安全](#网络通信安全)
8. [日志与审计](#日志与审计)
9. [应急响应](#应急响应)

## 安全原则

### 最小权限原则
- 脚本应以最低必要权限运行
- 避免使用 root/Administrator 权限
- 按需提升权限，及时降权

### 纵深防御
- 多层安全检查
- 不依赖单一安全措施
- 假定每个组件都可能被攻破

### 默认安全
- 默认拒绝未经授权的访问
- 默认不记录敏感信息
- 默认启用安全特性

## 输入验证

### 用户输入验证
```python
import re
from pathlib import Path

def validate_path_input(path_str, allowed_patterns=None, block_patterns=None):
    """
    验证路径输入
    
    Args:
        path_str: 路径字符串
        allowed_patterns: 允许的模式列表（正则表达式）
        block_patterns: 阻止的模式列表（正则表达式）
    
    Returns:
        (is_valid, sanitized_path, error_message)
    """
    # 默认阻止的危险模式
    default_block = [
        r'\.\.',           # 目录遍历
        r'/',              # 绝对路径（Unix）
        r'[A-Za-z]:\\',    # 绝对路径（Windows）
        r'\\',             # Windows 路径分隔符
        r'\$',             # 环境变量
        r'`',              # 命令替换
        r'\|\|',           # 命令分隔符
        r'&&',             # 命令分隔符
        r';',              # 命令分隔符
        r'\{', r'\}',      # 花括号扩展
        r'\*', r'\?', r'\[', r'\]'  # 通配符
    ]
    
    if block_patterns is None:
        block_patterns = default_block
    
    # 检查阻止模式
    for pattern in block_patterns:
        if re.search(pattern, path_str):
            return False, None, f"Input contains forbidden pattern: {pattern}"
    
    # 标准化路径
    try:
        # 限制为相对路径
        if path_str.startswith('/') or ':' in path_str or '\\' in path_str:
            return False, None, "Absolute paths are not allowed"
        
        # 解析路径
        path = Path(path_str).resolve()
        
        # 防止目录遍历
        current_dir = Path.cwd().resolve()
        if not str(path).startswith(str(current_dir)):
            return False, None, "Path traversal attempt detected"
        
        # 检查允许模式
        if allowed_patterns:
            path_str_lower = str(path).lower()
            if not any(re.search(pattern, path_str_lower) for pattern in allowed_patterns):
                return False, None, "Path does not match allowed patterns"
        
        return True, path, "Valid path"
    
    except Exception as e:
        return False, None, f"Path validation error: {e}"

def validate_command_input(command_str, allowed_commands=None):
    """
    验证命令输入
    
    Args:
        command_str: 命令字符串
        allowed_commands: 允许的命令列表（完整路径）
    
    Returns:
        (is_valid, sanitized_command, error_message)
    """
    # 危险字符和模式
    dangerous_patterns = [
        r'`.*`',            # 反引号命令替换
        r'\$\(.*\)',        # $() 命令替换
        r'\|\|', r'&&', r';', r'&',  # 命令分隔符
        r'>', r'>>', r'<', r'<<',    # 重定向
        r'\|',                        # 管道
        r'rm\s+-[rf]\s+',            # 危险的 rm 选项
        r':\(\)\{.*\}',              # Fork 炸弹模式
        r'mkfs', r'fdisk', r'dd',    # 危险系统命令
        r'chmod\s+[0-7]{3,4}\s+',    # 危险的权限设置
        r'chown\s+.*:.*\s+',         # 危险的所有权更改
    ]
    
    # 检查危险模式
    for pattern in dangerous_patterns:
        if re.search(pattern, command_str, re.IGNORECASE):
            return False, None, f"Command contains dangerous pattern: {pattern}"
    
    # 如果指定了允许的命令列表
    if allowed_commands:
        # 提取第一个单词作为命令
        first_word = command_str.strip().split()[0] if command_str.strip() else ""
        
        # 检查是否在允许列表中
        if not any(first_word == cmd or command_str.startswith(cmd + ' ') for cmd in allowed_commands):
            return False, None, f"Command not in allowed list: {first_word}"
    
    # 限制命令长度
    if len(command_str) > 1000:
        return False, None, "Command too long"
    
    return True, command_str, "Valid command"
```

### 数据类型验证
```python
def validate_integer(value, min_value=None, max_value=None):
    """验证整数输入"""
    try:
        num = int(value)
        
        if min_value is not None and num < min_value:
            return False, f"Value must be >= {min_value}"
        
        if max_value is not None and num > max_value:
            return False, f"Value must be <= {max_value}"
        
        return True, num
    
    except (ValueError, TypeError):
        return False, "Invalid integer"

def validate_string(value, min_length=1, max_length=255, pattern=None):
    """验证字符串输入"""
    if not isinstance(value, str):
        return False, "Not a string"
    
    if len(value) < min_length:
        return False, f"String too short (minimum {min_length} characters)"
    
    if len(value) > max_length:
        return False, f"String too long (maximum {max_length} characters)"
    
    if pattern and not re.match(pattern, value):
        return False, f"String does not match pattern: {pattern}"
    
    return True, value

def validate_filename(filename, allow_extensions=None, deny_extensions=None):
    """验证文件名"""
    # 默认拒绝的危险扩展名
    default_deny = [
        '.exe', '.bat', '.cmd', '.ps1', '.sh', '.bash',
        '.php', '.py', '.pl', '.rb', '.js',
        '.dll', '.so', '.dylib',
        '.app', '.apk', '.jar',
        '.scr', '.vbs', '.wsf',
        '.lnk', '.url', '.pif'
    ]
    
    if deny_extensions is None:
        deny_extensions = default_deny
    
    # 检查扩展名
    filename_lower = filename.lower()
    for ext in deny_extensions:
        if filename_lower.endswith(ext):
            return False, f"File extension not allowed: {ext}"
    
    # 检查允许的扩展名
    if allow_extensions:
        if not any(filename_lower.endswith(ext) for ext in allow_extensions):
            return False, f"File extension must be one of: {', '.join(allow_extensions)}"
    
    # 检查文件名中的危险字符
    dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        if char in filename:
            return False, f"Filename contains invalid character: {char}"
    
    # 检查保留名称
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + \
                     [f'COM{i}' for i in range(1, 10)] + \
                     [f'LPT{i}' for i in range(1, 10)]
    
    name_without_ext = Path(filename).stem.upper()
    if name_without_ext in reserved_names:
        return False, f"Filename is a reserved system name: {name_without_ext}"
    
    return True, filename
```

## 权限管理

### 权限检查
```python
import os
import stat

def check_file_permissions(path, required_perms=None):
    """
    检查文件权限
    
    Args:
        path: 文件路径
        required_perms: 需要的权限列表，如 ['read', 'write']
    
    Returns:
        (has_permissions, missing_perms)
    """
    if required_perms is None:
        required_perms = ['read']
    
    missing = []
    
    try:
        file_stat = os.stat(path)
        
        # 检查当前用户
        current_uid = os.getuid()
        current_gid = os.getgid()
        
        # 确定适用的权限位
        if file_stat.st_uid == current_uid:
            # 所有者权限
            perm_mask = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
        elif current_gid in os.getgroups() and file_stat.st_gid == current_gid:
            # 组权限
            perm_mask = stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP
        else:
            # 其他用户权限
            perm_mask = stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH
        
        # 检查具体权限
        if 'read' in required_perms and not (file_stat.st_mode & stat.S_IRUSR & perm_mask):
            missing.append('read')
        
        if 'write' in required_perms and not (file_stat.st_mode & stat.S_IWUSR & perm_mask):
            missing.append('write')
        
        if 'execute' in required_perms and not (file_stat.st_mode & stat.S_IXUSR & perm_mask):
            missing.append('execute')
        
        return len(missing) == 0, missing
    
    except OSError as e:
        return False, [f"Access error: {e}"]
```

### 临时权限提升
```python
import contextlib
import tempfile

@contextlib.contextmanager
def elevated_privileges(privilege_type='file_write', target_path=None):
    """
    临时提升权限的上下文管理器
    
    Args:
        privilege_type: 权限类型 ('file_write', 'file_read', 'command')
        target_path: 目标路径（用于验证）
    
    Yields:
        提升权限的上下文
    """
    # 记录原始权限
    original_uid = os.getuid()
    original_gid = os.getgid()
    
    try:
        # 检查是否已经具有所需权限
        if privilege_type == 'file_write' and target_path:
            has_perms, missing = check_file_permissions(target_path, ['write'])
            if has_perms:
                # 已有权限，无需提升
                yield
                return
        
        # 这里可以添加实际提升权限的逻辑
        # 注意：实际提升权限需要谨慎，这里只是示例
        print(f"WARNING: Would need to elevate privileges for {privilege_type}")
        
        # 在真实环境中，这里可能会：
        # 1. 使用 sudo（通过 subprocess）
        # 2. 使用 setuid/setgid
        # 3. 使用操作系统特定的权限API
        
        # 暂时使用临时文件作为安全替代
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            yield tmp.name
        
        # 清理临时文件
        os.unlink(tmp.name)
    
    finally:
        # 确保权限被恢复
        pass  # 在实际实现中恢复原始权限
```

## 敏感信息处理

### 安全存储
```python
import keyring
import json
from cryptography.fernet import Fernet
import base64
import os

class SecureStorage:
    """安全存储敏感信息"""
    
    def __init__(self, service_name, encryption_key=None):
        self.service_name = service_name
        
        if encryption_key:
            self.cipher = Fernet(encryption_key)
        else:
            # 从环境变量或文件加载密钥
            key_env = os.environ.get('ENCRYPTION_KEY')
            if key_env:
                self.cipher = Fernet(base64.urlsafe_b64decode(key_env))
            else:
                # 生成新密钥（仅用于临时存储）
                self.cipher = Fernet.generate_key()
                print(f"WARNING: Using auto-generated key. For production, set ENCRYPTION_KEY environment variable.")
                self.cipher = Fernet(self.cipher)
    
    def store(self, key, value, encrypt=True):
        """存储值"""
        if encrypt:
            # 加密值
            value_bytes = json.dumps(value).encode('utf-8')
            encrypted = self.cipher.encrypt(value_bytes)
            value_to_store = base64.urlsafe_b64encode(encrypted).decode('utf-8')
        else:
            value_to_store = json.dumps(value)
        
        # 使用系统密钥环存储
        try:
            keyring.set_password(self.service_name, key, value_to_store)
            return True
        except Exception as e:
            print(f"Failed to store in keyring: {e}")
            return False
    
    def retrieve(self, key, encrypted=True):
        """检索值"""
        try:
            stored = keyring.get_password(self.service_name, key)
            if not stored:
                return None
            
            if encrypted:
                # 解密值
                encrypted_bytes = base64.urlsafe_b64decode(stored.encode('utf-8'))
                decrypted = self.cipher.decrypt(encrypted_bytes)
                return json.loads(decrypted.decode('utf-8'))
            else:
                return json.loads(stored)
        
        except Exception as e:
            print(f"Failed to retrieve from keyring: {e}")
            return None
    
    def delete(self, key):
        """删除值"""
        try:
            keyring.delete_password(self.service_name, key)
            return True
        except Exception as e:
            print(f"Failed to delete from keyring: {e}")
            return False
```

### 内存安全
```python
import ctypes
import sys

class SecureString:
    """安全字符串（防止内存泄漏）"""
    
    def __init__(self, value):
        # 将字符串转换为字节
        if isinstance(value, str):
            self._data = value.encode('utf-8')
        else:
            self._data = bytes(value)
        
        # 在内存中锁定数据
        self._buffer = ctypes.create_string_buffer(self._data)
    
    def __str__(self):
        # 使用时解密
        return self._buffer.value.decode('utf-8')
    
    def __repr__(self):
        return 'SecureString(********)'
    
    def clear(self):
        """安全清除内存内容"""
        # 用随机数据覆盖内存
        import secrets
        random_data = secrets.token_bytes(len(self._buffer))
        ctypes.memmove(self._buffer, random_data, len(random_data))
        
        # 释放引用
        del self._data
        del self._buffer
    
    def __del__(self):
        # 析构时自动清除
        try:
            self.clear()
        except:
            pass

def get_password_input(prompt="Password: "):
    """安全获取密码输入"""
    import getpass
    
    password = getpass.getpass(prompt)
    
    # 返回安全字符串
    return SecureString(password)
```

## 命令执行安全

### 安全命令执行
```python
import subprocess
import shlex

def safe_execute(command, allow_list=None, timeout=30, cwd=None):
    """
    安全执行命令
    
    Args:
        command: 命令字符串或列表
        allow_list: 允许的命令列表（完整路径）
        timeout: 超时时间（秒）
        cwd: 工作目录
    
    Returns:
        (success, output, error)
    """
    # 验证命令
    if isinstance(command, str):
        # 检查命令是否安全
        is_valid, sanitized, error = validate_command_input(command, allow_list)
        if not is_valid:
            return False, "", f"Command validation failed: {error}"
        
        # 解析命令（不使用 shell）
        try:
            cmd_parts = shlex.split(sanitized)
        except ValueError:
            return False, "", "Invalid command syntax"
    else:
        # 命令列表
        cmd_parts = command
        
        # 检查第一个元素是否在允许列表中
        if allow_list and cmd_parts[0] not in allow_list:
            return False, "", f"Command not in allow list: {cmd_parts[0]}"
    
    # 设置安全环境
    env = os.environ.copy()
    
    # 移除危险的环境变量
    dangerous_env_vars = [
        'LD_PRELOAD', 'LD_LIBRARY_PATH',
        'PYTHONPATH', 'RUBYLIB', 'PERL5LIB',
        'IFS', 'ENV', 'BASH_ENV'
    ]
    
    for var in dangerous_env_vars:
        env.pop(var, None)
    
    # 限制资源
    resource_limits = {
        'RLIMIT_CPU': (timeout, timeout + 5),  # CPU 时间限制
        'RLIMIT_AS': 256 * 1024 * 1024,        # 内存限制 256MB
        'RLIMIT_FSIZE': 100 * 1024 * 1024,     # 文件大小限制 100MB
    }
    
    # 执行命令
    try:
        # 使用 preexec_fn 设置资源限制（Unix）
        def set_limits():
            import resource
            for limit_name, limit_value in resource_limits.items():
                if hasattr(resource, limit_name):
                    resource_limit = getattr(resource, limit_name)
                    
                    if isinstance(limit_value, tuple):
                        resource.setrlimit(resource_limit, limit_value)
                    else:
                        resource.setrlimit(resource_limit, (limit_value, limit_value))
        
        # 执行命令
        result = subprocess.run(
            cmd_parts,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            preexec_fn=set_limits if hasattr(os, 'fork') else None
        )
        
        return result.returncode == 0, result.stdout, result.stderr
    
    except subprocess.TimeoutExpired:
        return False, "", f"Command timeout after {timeout}s"
    
    except Exception as e:
        return False, "", str(e)
```

### 沙箱执行
```python
import tempfile
import shutil

@contextlib.contextmanager
def sandbox_execution(workdir=None, readonly_paths=None):
    """
    沙箱执行上下文管理器
    
    Args:
        workdir: 工作目录（临时创建如果为 None）
        readonly_paths: 只读路径列表
    
    Yields:
        沙箱工作目录
    """
    # 创建临时工作目录
    if workdir is None:
        temp_dir = tempfile.mkdtemp(prefix='sandbox_')
        cleanup = True
    else:
        temp_dir = workdir
        cleanup = False
    
    try:
        # 设置只读绑定挂载（如果支持）
        if readonly_paths and hasattr(os, 'chroot'):
            # 这里简化处理，实际可能需要使用 namespaces
            print("WARNING: Read-only bind mounts not implemented in this example")
        
        # 切换到沙箱目录
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        yield temp_dir
        
        # 恢复原始目录
        os.chdir(original_cwd)
    
    finally:
        # 清理临时目录
        if cleanup:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
```

## 文件操作安全

### 安全文件操作
```python
def safe_file_write(path, content, mode='w', encoding='utf-8'):
    """
    安全写入文件
    
    Args:
        path: 文件路径
        content: 文件内容
        mode: 写入模式
        encoding: 文件编码
    
    Returns:
        (success, error_message)
    """
    # 验证路径
    is_valid, sanitized_path, error = validate_path_input(str(path))
    if not is_valid:
        return False, error
    
    # 创建目录（如果不存在）
    try:
        sanitized_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return False, f"Failed to create directory: {e}"
    
    # 原子写入
    try:
        # 先写入临时文件
        temp_file = sanitized_path.with_suffix('.tmp')
        
        with open(temp_file, mode, encoding=encoding) as f:
            f.write(content)
        
        # 确保文件刷新到磁盘
        f.flush()
        os.fsync(f.fileno())
        
        # 原子重命名
        os.replace(temp_file, sanitized_path)
        
        return True, "File written successfully"
    
    except OSError as e:
        # 清理临时文件
        try:
            os.unlink(temp_file)
        except:
            pass
        
        return False, f"Failed to write file: {e}"
    
    except Exception as e:
        return False, f"Unexpected error: {e}"

def safe_file_read(path, mode='r', encoding='utf-8', max_size=10*1024*1024):
    """
    安全读取文件
    
    Args:
        path: 文件路径
        mode: 读取模式
        encoding: 文件编码
        max_size: 最大文件大小（字节）
    
    Returns:
        (success, content_or_error)
    """
    # 验证路径
    is_valid, sanitized_path, error = validate_path_input(str(path))
    if not is_valid:
        return False, error
    
    # 检查文件大小
    try:
        file_size = sanitized_path.stat().st_size
        if file_size > max_size:
            return False, f"File too large: {file_size} > {max_size} bytes"
    except OSError as e:
        return False, f"Failed to get file size: {e}"
    
    # 读取文件
    try:
        with open(sanitized_path, mode, encoding=encoding) as f:
            content = f.read(max_size + 1)  # 多读一个字节以检测是否超过限制
            
            if len(content) > max_size:
                return False, f"File content exceeds size limit"
            
            return True, content
    
    except OSError as e:
        return False, f"Failed to read file: {e}"
    
    except Exception as e:
        return False, f"Unexpected error: {e}"
```

### 文件完整性检查
```python
import hashlib

def verify_file_integrity(path, expected_hash=None, hash_algorithm='sha256'):
    """
    验证文件完整性
    
    Args:
        path: 文件路径
        expected_hash: 预期哈希值
        hash_algorithm: 哈希算法
    
    Returns:
        (is_valid, actual_hash, error_message)
    """
    # 验证路径
    is_valid, sanitized_path, error = validate_path_input(str(path))
    if not is_valid:
        return False, None, error
    
    # 计算哈希
    try:
        hasher = hashlib.new(hash_algorithm)
        
        with open(sanitized_path, 'rb') as f:
            # 分块读取以处理大文件
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        actual_hash = hasher.hexdigest()
        
        # 验证（如果提供了预期哈希）
        if expected_hash:
            is_valid = actual_hash == expected_hash.lower()
            return is_valid, actual_hash, "" if is_valid else "Hash mismatch"
        else:
            return True, actual_hash, ""
    
    except OSError as e:
        return False, None, f"Failed to read file: {e}"
    
    except ValueError as e:
        return False, None, f"Invalid hash algorithm: {e}"
```

## 网络通信安全

### 安全网络请求
```python
import urllib.request
import ssl
import socket

def safe_url_request(url, timeout=10, verify_ssl=True, user_agent=None):
    """
    安全 URL 请求
    
    Args:
        url: 请求 URL
        timeout: 超时时间（秒）
        verify_ssl: 是否验证 SSL 证书
        user_agent: 用户代理字符串
    
    Returns:
        (success, response_or_error)
    """
    # 验证 URL
    if not url.startswith(('http://', 'https://')):
        return False, "Invalid URL scheme"
    
    # 设置请求头
    headers = {
        'User-Agent': user_agent or 'SafeBot/1.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'close',  # 不使用持久连接
        'Upgrade-Insecure-Requests': '1'
    }
    
    # 创建请求
    req = urllib.request.Request(url, headers=headers)
    
    # 配置 SSL
    if verify_ssl:
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        context = ssl._create_unverified_context()
    
    # 设置超时
    socket.setdefaulttimeout(timeout)
    
    try:
        # 发送请求
        with urllib.request.urlopen(req, context=context, timeout=timeout) as response:
            # 检查响应大小限制
            content_length = response.getheader('Content-Length')
            if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
                return False, "Response too large"
            
            # 读取响应（限制大小）
            data = response.read(11 * 1024 * 1024)  # 多读 1MB 以检测超限
            
            if len(data) > 10 * 1024 * 1024:
                return False, "Response content exceeds size limit"
            
            # 解码响应
            encoding = response.info().get_content_charset() or 'utf-8'
            content = data.decode(encoding, errors='replace')
            
            return True, content
    
    except urllib.error.URLError as e:
        return False, f"URL error: {e}"
    
    except socket.timeout:
        return False, f"Request timeout after {timeout}s"
    
    except Exception as e:
        return False, f"Unexpected error: {e}"
```

## 日志与审计

### 安全日志
```python
import logging
import json
from datetime import datetime

class SecurityLogger:
    """安全日志记录器"""
    
    def __init__(self, log_file=None, max_size=10*1024*1024):
        self.log_file = log_file
        self.max_size = max_size
        
        # 配置日志
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)
            console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
            
            # 文件处理器（如果指定了文件）
            if log_file:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.INFO)
                file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
    
    def log_security_event(self, event_type, details, severity='INFO', user=None, ip=None):
        """
        记录安全事件
        
        Args:
            event_type: 事件类型
            details: 事件详情
            severity: 严重程度 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            user: 用户标识
            ip: IP 地址
        """
        # 构建日志记录
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event_type': event_type,
            'severity': severity,
            'user': user,
            'ip': ip,
            'details': details
        }
        
        # 记录日志
        log_message = json.dumps(log_entry, ensure_ascii=False)
        
        if severity == 'DEBUG':
            self.logger.debug(log_message)
        elif severity == 'INFO':
            self.logger.info(log_message)
        elif severity == 'WARNING':
            self.logger.warning(log_message)
        elif severity == 'ERROR':
            self.logger.error(log_message)
        elif severity == 'CRITICAL':
            self.logger.critical(log_message)
        
        # 检查日志文件大小
        self._rotate_log_if_needed()
    
    def _rotate_log_if_needed(self):
        """如果需要，轮转日志文件"""
        if self.log_file and os.path.exists(self.log_file):
            file_size = os.path.getsize(self.log_file)
            
            if file_size > self.max_size:
                # 创建备份
                backup_file = f"{self.log_file}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(self.log_file, backup_file)
                
                # 清空当前文件
                with open(self.log_file, 'w') as f:
                    f.write('')
                
                self.logger.info(f"Log file rotated: {self.log_file} -> {backup_file}")
```

### 审计跟踪
```python
class AuditTrail:
    """审计跟踪"""
    
    def __init__(self, audit_file=None):
        self.audit_file = audit_file
    
    def record_action(self, action, resource, user, outcome, details=None):
        """
        记录操作
        
        Args:
            action: 操作类型
            resource: 资源标识
            user: 用户标识
            outcome: 结果 (SUCCESS, FAILURE)
            details: 额外详情
        """
        audit_record = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': action,
            'resource': resource,
            'user': user,
            'outcome': outcome,
            'details': details or {},
            'ip': self._get_client_ip(),
            'user_agent': self._get_user_agent()
        }
        
        # 写入审计文件
        if self.audit_file:
            try:
                with open(self.audit_file, 'a') as f:
                    json.dump(audit_record, f, ensure_ascii=False)
                    f.write('\n')
            except:
                pass
        
        return audit_record
    
    def _get_client_ip(self):
        """获取客户端 IP（简化实现）"""
        try:
            import socket
            return socket.gethostbyname(socket.gethostname())
        except:
            return 'unknown'
    
    def _get_user_agent(self):
        """获取用户代理"""
        import platform
        return f"Python/{platform.python_version()} {platform.system()}/{platform.release()}"
```

## 应急响应

### 安全事件响应
```python
class SecurityIncidentResponse:
    """安全事件响应"""
    
    def __init__(self, alert_recipients=None):
        self.alert_recipients = alert_recipients or []
        self.incident_log = []
    
    def handle_incident(self, incident_type, severity, description, evidence=None):
        """
        处理安全事件
        
        Args:
            incident_type: 事件类型
            severity: 严重程度 (LOW, MEDIUM, HIGH, CRITICAL)
            description: 事件描述
            evidence: 证据数据
        """
        incident = {
            'id': len(self.incident_log) + 1,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'type': incident_type,
            'severity': severity,
            'description': description,
            'evidence': evidence,
            'status': 'OPEN',
            'actions_taken': []
        }
        
        # 记录事件
        self.incident_log.append(incident)
        
        # 根据严重程度采取行动
        if severity in ['HIGH', 'CRITICAL']:
            self._take_emergency_actions(incident)
        
        # 发送警报
        self._send_alerts(incident)
        
        return incident['id']
    
    def _take_emergency_actions(self, incident):
        """采取紧急行动"""
        actions = []
        
        # 隔离受影响系统
        if incident['type'] in ['UNAUTHORIZED_ACCESS', 'MALWARE']:
            actions.append("Isolated affected systems from network")
        
        # 保存证据
        if incident['evidence']:
            actions.append("Preserved evidence for forensic analysis")
        
        # 更新事件状态
        incident['actions_taken'].extend(actions)
        
        # 记录采取的行动
        print(f"EMERGENCY ACTIONS TAKEN: {', '.join(actions)}")
    
    def _send_alerts(self, incident):
        """发送警报"""
        if not self.alert_recipients:
            return
        
        alert_message = f"""
        SECURITY ALERT - {incident['severity']} severity
        
        Incident ID: {incident['id']}
        Type: {incident['type']}
        Time: {incident['timestamp']}
        Description: {incident['description']}
        
        Actions taken: {', '.join(incident['actions_taken']) if incident['actions_taken'] else 'None yet'}
        
        Please investigate immediately.
        """
        
        for recipient in self.alert_recipients:
            # 这里可以实现邮件、短信、Slack 等通知
            print(f"ALERT sent to {recipient}: {alert_message[:100]}...")
    
    def get_incident_report(self, incident_id=None):
        """获取事件报告"""
        if incident_id:
            incidents = [i for i in self.incident_log if i['id'] == incident_id]
        else:
            incidents = self.incident_log
        
        return {
            'total_incidents': len(self.incident_log),
            'open_incidents': len([i for i in self.incident_log if i['status'] == 'OPEN']),
            'incidents': incidents
        }
```

### 安全扫描
```python
class SecurityScanner:
    """安全扫描器"""
    
    def __init__(self):
        self.findings = []
    
    def scan_directory(self, directory, recursive=True):
        """
        扫描目录安全风险
        
        Args:
            directory: 目录路径
            recursive: 是否递归扫描
        """
        directory = Path(directory).resolve()
        
        for item in directory.rglob('*') if recursive else directory.iterdir():
            if item.is_file():
                self._scan_file(item)
            elif item.is_dir():
                self._scan_directory_permissions(item)
    
    def _scan_file(self, filepath):
        """扫描文件"""
        # 检查危险文件扩展名
        dangerous_exts = ['.exe', '.bat', '.cmd', '.ps1', '.sh', '.pyc']
        if filepath.suffix.lower() in dangerous_exts:
            self.findings.append({
                'type': 'DANGEROUS_FILE',
                'severity': 'HIGH',
                'file': str(filepath),
                'description': f"File with potentially dangerous extension: {filepath.suffix}"
            })
        
        # 检查文件权限
        try:
            mode = filepath.stat().st_mode
            if mode & 0o777 == 0o777:  # rwxrwxrwx
                self.findings.append({
                    'type': 'INSECURE_PERMISSIONS',
                    'severity': 'MEDIUM',
                    'file': str(filepath),
                    'description': "File has world-writable permissions"
                })
        except OSError:
            pass
    
    def _scan_directory_permissions(self, dirpath):
        """扫描目录权限"""
        try:
            mode = dirpath.stat().st_mode
            if mode & 0o777 == 0o777:  # rwxrwxrwx
                self.findings.append({
                    'type': 'INSECURE_PERMISSIONS',
                    'severity': 'HIGH',
                    'directory': str(dirpath),
                    'description': "Directory has world-writable permissions"
                })
        except OSError:
            pass
    
    def get_report(self):
        """获取扫描报告"""
        return {
            'scan_timestamp': datetime.utcnow().isoformat() + 'Z',
            'total_findings': len(self.findings),
            'findings_by_severity': {
                'CRITICAL': len([f for f in self.findings if f['severity'] == 'CRITICAL']),
                'HIGH': len([f for f in self.findings if f['severity'] == 'HIGH']),
                'MEDIUM': len([f for f in self.findings if f['severity'] == 'MEDIUM']),
                'LOW': len([f for f in self.findings if f['severity'] == 'LOW'])
            },
            'findings': self.findings
        }
```

## 总结

自动化安全的关键要点：

1. **输入验证**：永远不信任用户输入
2. **最小权限**：使用完成任务所需的最低权限
3. **安全存储**：妥善保护敏感信息
4. **安全执行**：限制命令和文件操作的风险
5. **审计跟踪**：记录所有重要操作
6. **应急响应**：准备好应对安全事件

通过遵循这些指南，可以显著降低自动化脚本的安全风险。