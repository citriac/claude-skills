#!/usr/bin/env python3
"""
take_photo.py — 用 Photo Booth 拍摄一张照片并导出到指定目录
macOS Big Sur+：Photo Booth 将照片保存到 Photos Library（沙箱保护），
本脚本通过 Photos AppleScript 导出最新照片。
"""
import subprocess
import os
import sys
import argparse
import time
from datetime import datetime
from typing import Optional

DEFAULT_OUT_DIR = os.path.expanduser(
    "~/WorkBuddy/Claw/.workbuddy/visual/photos"
)

# Step 1: 拍照 AppleScript（切换到「照片」模式再拍）
TAKE_PHOTO_SCRIPT = """
tell application "Photo Booth" to activate
delay 1
tell application "System Events" to tell process "Photo Booth"
    click radio button 2 of radio group 1 of group 1 of window 1
end tell
delay 0.5
tell application "System Events"
    set frontmost of process "Photo Booth" to true
    keystroke return using {option down}
end tell
delay 3
tell application "Photo Booth" to quit
"""

# Step 2: 从 Photos 导出最新照片
EXPORT_LATEST_PHOTO = """
set outDir to "{out_dir}"
set outFile to outDir & "/" & "{filename}"
tell application "Photos"
    set latestItem to item 1 of (get every media item)
    export {{latestItem}} to POSIX file outDir with using originals
end tell
return outFile
"""


def take_photo_via_photobooth() -> bool:
    """触发 Photo Booth 拍照"""
    result = subprocess.run(
        ["osascript", "-e", TAKE_PHOTO_SCRIPT],
        capture_output=True, text=True, timeout=15
    )
    return result.returncode == 0


def export_latest_from_photos(out_dir: str) -> Optional[str]:
    """从 Photos.app 导出最新一张照片到目标目录"""
    os.makedirs(out_dir, exist_ok=True)
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"photo_{ts}"
    
    script = EXPORT_LATEST_PHOTO.format(out_dir=out_dir, filename=filename)
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=30
    )
    
    if result.returncode != 0:
        print(f"[WARN] Photos export failed: {result.stderr.strip()}", file=sys.stderr)
        return None
    
    # 查找导出的文件（Photos 会用原始文件名，我们找最新的）
    import glob
    time.sleep(1)
    files = glob.glob(os.path.join(out_dir, "*.jpg")) + \
            glob.glob(os.path.join(out_dir, "*.heic")) + \
            glob.glob(os.path.join(out_dir, "*.jpeg"))
    if files:
        return max(files, key=os.path.getmtime)
    return None


def take_photo(out_dir: str = DEFAULT_OUT_DIR) -> Optional[str]:
    """主流程：拍照 + 导出"""
    os.makedirs(out_dir, exist_ok=True)
    
    import glob
    before = set(
        glob.glob(os.path.join(out_dir, "*.jpg")) +
        glob.glob(os.path.join(out_dir, "*.heic")) +
        glob.glob(os.path.join(out_dir, "*.jpeg"))
    )
    
    print("[1/2] 触发 Photo Booth 拍照...", file=sys.stderr)
    if not take_photo_via_photobooth():
        print("[ERROR] Photo Booth 拍照失败", file=sys.stderr)
        return None
    
    print("[2/2] 从 Photos 导出最新照片...", file=sys.stderr)
    result = export_latest_from_photos(out_dir)
    
    if result:
        return result
    
    # fallback: 看目录里有没有新文件
    time.sleep(2)
    after = set(
        glob.glob(os.path.join(out_dir, "*.jpg")) +
        glob.glob(os.path.join(out_dir, "*.heic")) +
        glob.glob(os.path.join(out_dir, "*.jpeg"))
    )
    new_files = after - before
    if new_files:
        return max(new_files, key=os.path.getmtime)
    
    print("[ERROR] 未能获取照片。可能需要在「系统偏好设置 → 安全性与隐私 → 照片」中授权此应用访问照片库。", file=sys.stderr)
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="用 Photo Booth 拍一张照片")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="保存目录")
    parser.add_argument("--quiet", action="store_true", help="只输出文件路径或错误")
    args = parser.parse_args()

    path = take_photo(args.out)
    if path:
        if not args.quiet:
            print(f"[OK] 照片已保存: {path}")
        else:
            print(path)
    else:
        sys.exit(1)
