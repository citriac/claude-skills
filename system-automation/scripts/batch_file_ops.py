#!/usr/bin/env python3
"""
批量文件操作工具
支持：批量重命名、文件过滤、目录同步、归档操作
跨平台兼容：macOS, Linux, Windows
"""

import os
import sys
import argparse
import shutil
import fnmatch
import time
from pathlib import Path
from datetime import datetime, timedelta
import zipfile
import tarfile
import hashlib
import concurrent.futures
from typing import List, Tuple, Dict, Optional

def normalize_path(path: str) -> Path:
    """统一路径格式，处理 ~ 和相对路径"""
    expanded = os.path.expanduser(str(path))
    return Path(expanded).resolve()

def find_files(
    directory: Path,
    pattern: str = "*",
    recursive: bool = True,
    min_size: int = 0,
    max_size: int = None,
    min_age_days: int = None,
    max_age_days: int = None
) -> List[Path]:
    """
    查找符合条件的文件
    
    Args:
        directory: 搜索目录
        pattern: glob 模式，如 "*.txt", "*.{jpg,png}"
        recursive: 是否递归搜索
        min_size: 最小文件大小（字节）
        max_size: 最大文件大小（字节）
        min_age_days: 最小文件年龄（天）
        max_age_days: 最大文件年龄（天）
    
    Returns:
        符合条件的文件路径列表
    """
    files = []
    
    if recursive:
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                if fnmatch.fnmatch(filename, pattern):
                    filepath = Path(root) / filename
                    files.append(filepath)
    else:
        for item in directory.iterdir():
            if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                files.append(item)
    
    # 过滤大小
    if min_size > 0 or max_size:
        filtered = []
        for f in files:
            try:
                size = f.stat().st_size
                if min_size and size < min_size:
                    continue
                if max_size and size > max_size:
                    continue
                filtered.append(f)
            except (OSError, FileNotFoundError):
                continue
        files = filtered
    
    # 过滤时间
    if min_age_days is not None or max_age_days is not None:
        now = time.time()
        filtered = []
        for f in files:
            try:
                mtime = f.stat().st_mtime
                age_days = (now - mtime) / (24 * 3600)
                
                if min_age_days is not None and age_days < min_age_days:
                    continue
                if max_age_days is not None and age_days > max_age_days:
                    continue
                filtered.append(f)
            except (OSError, FileNotFoundError):
                continue
        files = filtered
    
    return files

def batch_rename(
    files: List[Path],
    pattern: str,
    start_index: int = 1,
    dry_run: bool = False
) -> List[Tuple[Path, Path]]:
    """
    批量重命名文件
    
    Args:
        files: 文件列表
        pattern: 命名模式，可使用 {index}, {name}, {ext}, {stem}
        start_index: 起始索引
        dry_run: 试运行，不实际重命名
    
    Returns:
        重命名前后路径的列表
    """
    renamed = []
    
    for i, filepath in enumerate(files):
        # 解析文件信息
        stem = filepath.stem
        ext = filepath.suffix
        name = filepath.name
        
        # 构建新文件名
        new_name = pattern.format(
            index=start_index + i,
            name=name,
            stem=stem,
            ext=ext[1:] if ext.startswith('.') else ext,
            i=start_index + i,
            date=datetime.now().strftime("%Y%m%d")
        )
        
        new_path = filepath.parent / new_name
        
        # 避免重复
        if new_path.exists():
            base, ext = os.path.splitext(new_name)
            counter = 1
            while new_path.exists():
                new_name = f"{base}_{counter}{ext}"
                new_path = filepath.parent / new_name
                counter += 1
        
        renamed.append((filepath, new_path))
        
        if not dry_run:
            try:
                filepath.rename(new_path)
                print(f"✓ {filepath.name} → {new_path.name}")
            except OSError as e:
                print(f"✗ Failed to rename {filepath.name}: {e}")
        else:
            print(f"[DRY RUN] {filepath.name} → {new_path.name}")
    
    return renamed

def sync_directories(
    source: Path,
    destination: Path,
    pattern: str = "*",
    delete_missing: bool = False,
    compare_content: bool = False
) -> Dict[str, List[str]]:
    """
    同步两个目录
    
    Args:
        source: 源目录
        destination: 目标目录
        pattern: 文件模式
        delete_missing: 是否删除目标中源没有的文件
        compare_content: 是否比较文件内容而不仅是修改时间
    
    Returns:
        同步统计信息
    """
    stats = {
        "copied": [],
        "skipped": [],
        "deleted": [],
        "errors": []
    }
    
    # 确保目标目录存在
    destination.mkdir(parents=True, exist_ok=True)
    
    # 收集源文件
    source_files = {}
    for root, dirs, files in os.walk(source):
        rel_root = Path(root).relative_to(source)
        
        for dirname in dirs:
            target_dir = destination / rel_root / dirname
            target_dir.mkdir(parents=True, exist_ok=True)
        
        for filename in files:
            if fnmatch.fnmatch(filename, pattern):
                source_file = Path(root) / filename
                rel_path = rel_root / filename
                source_files[rel_path] = source_file
    
    # 收集目标文件（如果启用删除）
    dest_files = set()
    if delete_missing:
        for root, dirs, files in os.walk(destination):
            rel_root = Path(root).relative_to(destination)
            for filename in files:
                rel_path = rel_root / filename
                dest_files.add(rel_path)
    
    # 复制或更新文件
    for rel_path, source_file in source_files.items():
        dest_file = destination / rel_path
        
        copy_needed = False
        
        if not dest_file.exists():
            copy_needed = True
        else:
            # 比较文件属性
            src_stat = source_file.stat()
            dst_stat = dest_file.stat()
            
            if compare_content:
                # 比较文件哈希
                def file_hash(path: Path) -> str:
                    hasher = hashlib.md5()
                    with open(path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hasher.update(chunk)
                    return hasher.hexdigest()
                
                if file_hash(source_file) != file_hash(dest_file):
                    copy_needed = True
            elif src_stat.st_mtime > dst_stat.st_mtime or src_stat.st_size != dst_stat.st_size:
                copy_needed = True
        
        if copy_needed:
            try:
                shutil.copy2(source_file, dest_file)
                stats["copied"].append(str(rel_path))
                print(f"✓ Copied: {rel_path}")
            except Exception as e:
                stats["errors"].append(f"{rel_path}: {e}")
                print(f"✗ Failed to copy {rel_path}: {e}")
        else:
            stats["skipped"].append(str(rel_path))
            print(f"○ Skipped (unchanged): {rel_path}")
    
    # 删除源中没有的文件
    if delete_missing:
        for rel_path in dest_files - set(source_files.keys()):
            dest_file = destination / rel_path
            try:
                dest_file.unlink()
                stats["deleted"].append(str(rel_path))
                print(f"🗑️  Deleted: {rel_path}")
            except Exception as e:
                stats["errors"].append(f"{rel_path}: {e}")
                print(f"✗ Failed to delete {rel_path}: {e}")
    
    return stats

def archive_files(
    files: List[Path],
    output_path: Path,
    format: str = "zip",
    compression: str = "normal"
) -> bool:
    """
    归档文件
    
    Args:
        files: 文件列表
        output_path: 输出路径
        format: 归档格式：zip, tar, tar.gz, tar.bz2
        compression: 压缩级别：store, fast, normal, maximum
    
    Returns:
        是否成功
    """
    compression_map = {
        "store": zipfile.ZIP_STORED,
        "fast": zipfile.ZIP_DEFLATED,
        "normal": zipfile.ZIP_DEFLATED,
        "maximum": zipfile.ZIP_DEFLATED
    }
    
    try:
        if format == "zip":
            comp = compression_map.get(compression, zipfile.ZIP_DEFLATED)
            compresslevel = 9 if compression == "maximum" else 6 if compression == "normal" else 1
            
            with zipfile.ZipFile(
                output_path, 'w', compression=comp, compresslevel=compresslevel
            ) as zf:
                for filepath in files:
                    arcname = filepath.name
                    zf.write(filepath, arcname=arcname)
                    print(f"✓ Added: {filepath.name}")
        
        elif format.startswith("tar"):
            mode = "w"
            if format.endswith(".gz"):
                mode += ":gz"
            elif format.endswith(".bz2"):
                mode += ":bz2"
            elif format.endswith(".xz"):
                mode += ":xz"
            
            with tarfile.open(output_path, mode) as tf:
                for filepath in files:
                    arcname = filepath.name
                    tf.add(filepath, arcname=arcname)
                    print(f"✓ Added: {filepath.name}")
        
        else:
            print(f"✗ Unsupported format: {format}")
            return False
        
        print(f"✅ Archive created: {output_path}")
        return True
    
    except Exception as e:
        print(f"✗ Failed to create archive: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="批量文件操作工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # find 命令
    find_parser = subparsers.add_parser("find", help="查找文件")
    find_parser.add_argument("directory", help="搜索目录")
    find_parser.add_argument("-p", "--pattern", default="*", help="文件模式")
    find_parser.add_argument("-r", "--recursive", action="store_true", help="递归搜索")
    find_parser.add_argument("--min-size", type=int, default=0, help="最小文件大小（字节）")
    find_parser.add_argument("--max-size", type=int, help="最大文件大小（字节）")
    find_parser.add_argument("--min-age", type=int, help="最小文件年龄（天）")
    find_parser.add_argument("--max-age", type=int, help="最大文件年龄（天）")
    
    # rename 命令
    rename_parser = subparsers.add_parser("rename", help="批量重命名")
    rename_parser.add_argument("directory", help="目录")
    rename_parser.add_argument("pattern", help="命名模式，可用变量：{index}, {name}, {stem}, {ext}, {date}")
    rename_parser.add_argument("-p", "--file-pattern", default="*", help="文件模式")
    rename_parser.add_argument("-s", "--start-index", type=int, default=1, help="起始索引")
    rename_parser.add_argument("-d", "--dry-run", action="store_true", help="试运行")
    
    # sync 命令
    sync_parser = subparsers.add_parser("sync", help="目录同步")
    sync_parser.add_argument("source", help="源目录")
    sync_parser.add_argument("destination", help="目标目录")
    sync_parser.add_argument("-p", "--pattern", default="*", help="文件模式")
    sync_parser.add_argument("--delete", action="store_true", help="删除目标中源没有的文件")
    sync_parser.add_argument("--compare-content", action="store_true", help="比较文件内容")
    
    # archive 命令
    archive_parser = subparsers.add_parser("archive", help="归档文件")
    archive_parser.add_argument("files", nargs="+", help="要归档的文件")
    archive_parser.add_argument("-o", "--output", required=True, help="输出文件")
    archive_parser.add_argument("-f", "--format", choices=["zip", "tar", "tar.gz", "tar.bz2"], default="zip")
    archive_parser.add_argument("-c", "--compression", choices=["store", "fast", "normal", "maximum"], default="normal")
    
    args = parser.parse_args()
    
    if args.command == "find":
        directory = normalize_path(args.directory)
        if not directory.exists():
            print(f"✗ Directory not found: {directory}")
            sys.exit(1)
        
        files = find_files(
            directory,
            pattern=args.pattern,
            recursive=args.recursive,
            min_size=args.min_size,
            max_size=args.max_size,
            min_age_days=args.min_age,
            max_age_days=args.max_age
        )
        
        for f in files:
            size = f.stat().st_size
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            print(f"{f} ({size:,} bytes, {mtime:%Y-%m-%d %H:%M})")
        
        print(f"\nFound {len(files)} file(s)")
    
    elif args.command == "rename":
        directory = normalize_path(args.directory)
        if not directory.exists():
            print(f"✗ Directory not found: {directory}")
            sys.exit(1)
        
        files = find_files(directory, pattern=args.file_pattern, recursive=False)
        
        if not files:
            print("No files found matching pattern")
            sys.exit(1)
        
        batch_rename(files, args.pattern, args.start_index, args.dry_run)
    
    elif args.command == "sync":
        source = normalize_path(args.source)
        destination = normalize_path(args.destination)
        
        if not source.exists():
            print(f"✗ Source directory not found: {source}")
            sys.exit(1)
        
        stats = sync_directories(
            source, destination,
            pattern=args.pattern,
            delete_missing=args.delete,
            compare_content=args.compare_content
        )
        
        print(f"\n--- Statistics ---")
        print(f"Copied: {len(stats['copied'])}")
        print(f"Skipped: {len(stats['skipped'])}")
        print(f"Deleted: {len(stats['deleted'])}")
        print(f"Errors: {len(stats['errors'])}")
        
        if stats["errors"]:
            print("\nErrors:")
            for error in stats["errors"]:
                print(f"  {error}")
    
    elif args.command == "archive":
        files = [normalize_path(f) for f in args.files]
        output = normalize_path(args.output)
        
        missing = [f for f in files if not f.exists()]
        if missing:
            print("Missing files:")
            for f in missing:
                print(f"  {f}")
            sys.exit(1)
        
        success = archive_files(files, output, args.format, args.compression)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()