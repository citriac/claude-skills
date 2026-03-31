#!/usr/bin/env python3
"""
take_photo.py — 用 Photo Booth 拍摄一张照片并保存到指定目录
用法: python3 take_photo.py [--out <path>] [--no-preview]
返回: 照片文件路径（stdout）
"""
import subprocess
import os
import sys
import argparse
import time
import glob
import shutil
from datetime import datetime
from typing import Optional

# Photo Booth 默认保存目录
PHOTO_BOOTH_DIR = os.path.expanduser(
    "~/Pictures/Photo Booth Library/Pictures"
)

# 本技能默认保存目录（仅 Clavis 工作目录下）
DEFAULT_OUT_DIR = os.path.expanduser(
    "~/WorkBuddy/Claw/.workbuddy/visual/photos"
)

# AppleScript: 拍一张照片（option+enter 触发快门）
APPLESCRIPT = """
tell application "Photo Booth" to activate
delay 1
tell application "System Events"
    set frontmost of process "Photo Booth" to true
    keystroke return using {option down}
end tell
delay 2
tell application "Photo Booth" to quit
"""


def get_latest_photo(before_files: set) -> Optional[str]:
    """获取 Photo Booth 目录下最新生成的照片"""
    time.sleep(1)
    pattern = os.path.join(PHOTO_BOOTH_DIR, "*.jpg")
    all_files = set(glob.glob(pattern))
    new_files = all_files - before_files
    if new_files:
        return max(new_files, key=os.path.getmtime)
    # fallback: 直接取最新
    if all_files:
        return max(all_files, key=os.path.getmtime)
    return None


def take_photo(out_dir: str = DEFAULT_OUT_DIR) -> str:
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(PHOTO_BOOTH_DIR, exist_ok=True)

    # 记录拍照前的文件集合
    before = set(glob.glob(os.path.join(PHOTO_BOOTH_DIR, "*.jpg")))

    # 执行 AppleScript
    result = subprocess.run(
        ["osascript", "-e", APPLESCRIPT],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[ERROR] AppleScript failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # 等待文件写入
    time.sleep(2)

    src = get_latest_photo(before)
    if not src or not os.path.exists(src):
        print("[ERROR] 未找到新照片，Photo Booth 保存路径可能不同", file=sys.stderr)
        sys.exit(1)

    # 复制到目标目录，文件名含时间戳
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(out_dir, f"photo_{ts}.jpg")
    shutil.copy2(src, dst)

    return dst


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="拍一张照片")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="保存目录")
    parser.add_argument("--no-preview", action="store_true", help="不输出提示信息")
    args = parser.parse_args()

    path = take_photo(args.out)
    if not args.no_preview:
        print(f"[OK] 照片已保存: {path}")
    else:
        print(path)
