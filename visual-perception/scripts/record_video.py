#!/usr/bin/env python3
"""
record_video.py — 用 Photo Booth 录制一段视频并保存到指定目录
用法: python3 record_video.py [--duration <秒>] [--out <path>]
默认录制 10 秒
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

# Photo Booth 视频默认保存目录
PHOTO_BOOTH_VIDEOS_DIR = os.path.expanduser(
    "~/Pictures/Photo Booth Library/Videos"
)

# 本技能默认保存目录
DEFAULT_OUT_DIR = os.path.expanduser(
    "~/WorkBuddy/Claw/.workbuddy/visual/videos"
)

def make_record_script(duration: int) -> str:
    """生成录视频 AppleScript（duration 秒后按 ESC 停止）"""
    return f"""
tell application "Photo Booth" to activate
delay 1
tell application "System Events" to tell process "Photo Booth"
    click radio button 3 of radio group 1 of group 1 of window "Photo Booth"
end tell
tell application "System Events"
    set frontmost of process "Photo Booth" to true
    keystroke return using {{option down}}
end tell
delay {duration}
tell application "System Events"
    key code 53
end tell
delay 2
tell application "Photo Booth" to quit
"""


def get_latest_video(before_files: set) -> Optional[str]:
    """获取 Photo Booth Videos 目录下最新的视频"""
    time.sleep(1)
    for ext in ("*.mov", "*.mp4", "*.m4v"):
        pattern = os.path.join(PHOTO_BOOTH_VIDEOS_DIR, ext)
        all_files = set(glob.glob(pattern))
        new_files = all_files - before_files
        if new_files:
            return max(new_files, key=os.path.getmtime)
    # fallback
    for ext in ("*.mov", "*.mp4", "*.m4v"):
        pattern = os.path.join(PHOTO_BOOTH_VIDEOS_DIR, ext)
        all_files = set(glob.glob(pattern))
        if all_files:
            return max(all_files, key=os.path.getmtime)
    return None


def record_video(duration: int = 10, out_dir: str = DEFAULT_OUT_DIR) -> str:
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(PHOTO_BOOTH_VIDEOS_DIR, exist_ok=True)

    # 记录录制前的文件集合
    before = set()
    for ext in ("*.mov", "*.mp4", "*.m4v"):
        before |= set(glob.glob(os.path.join(PHOTO_BOOTH_VIDEOS_DIR, ext)))

    script = make_record_script(duration)
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[ERROR] AppleScript failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # 等待文件写入
    time.sleep(3)

    src = get_latest_video(before)
    if not src or not os.path.exists(src):
        print("[ERROR] 未找到新视频，Photo Booth 保存路径可能不同", file=sys.stderr)
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(src)[1]
    dst = os.path.join(out_dir, f"video_{ts}{ext}")
    shutil.copy2(src, dst)

    return dst


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="录制一段视频")
    parser.add_argument("--duration", type=int, default=10, help="录制时长（秒），默认10")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="保存目录")
    parser.add_argument("--quiet", action="store_true", help="只输出文件路径")
    args = parser.parse_args()

    path = record_video(args.duration, args.out)
    if not args.quiet:
        print(f"[OK] 视频已保存: {path}")
    else:
        print(path)
