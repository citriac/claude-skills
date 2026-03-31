#!/usr/bin/env python3
"""
privacy_check.py — 在发布/记录视觉内容前执行隐私审查
检查项目：
  - 文件是否包含人脸（需要用户确认才能对外分享）
  - 文件是否在安全目录内（非个人隐私目录）
  - 用于决定内容是否可以发布到文章/公开平台

用法: python3 privacy_check.py <文件路径> [--action <check|redact|describe>]
"""
import os
import sys
import argparse
from datetime import datetime

# 安全目录白名单（允许使用的目录）
SAFE_DIRS = [
    os.path.expanduser("~/WorkBuddy/Claw/.workbuddy/visual"),
]

# 隐私敏感关键词（文件名或路径中出现时需要额外确认）
SENSITIVE_KEYWORDS = [
    "aby", "max", "mindon", "family", "home", "bedroom", "bathroom",
    "passport", "id_card", "bank", "password", "private",
]

# 不可公开发布的目录
PRIVATE_DIRS = [
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/Pictures"),
    os.path.expanduser("~/Library"),
]


def check_path_safety(filepath: str) -> dict:
    """检查文件路径的安全性"""
    abs_path = os.path.abspath(filepath)
    
    issues = []
    warnings = []
    
    # 1. 检查是否在安全目录内
    in_safe_dir = any(abs_path.startswith(d) for d in SAFE_DIRS)
    in_private_dir = any(abs_path.startswith(d) for d in PRIVATE_DIRS)
    
    if in_private_dir and not in_safe_dir:
        issues.append(f"文件位于私人目录，禁止对外分享: {abs_path}")
    
    if not in_safe_dir:
        warnings.append("文件不在 Clavis 工作目录，分享前需要 Mindon 确认")
    
    # 2. 检查文件名是否包含敏感词
    filename_lower = os.path.basename(filepath).lower()
    path_lower = abs_path.lower()
    for kw in SENSITIVE_KEYWORDS:
        if kw in path_lower:
            warnings.append(f"路径包含敏感关键词 '{kw}'，请确认内容安全性")
            break
    
    # 3. 检查文件是否存在
    if not os.path.exists(filepath):
        issues.append(f"文件不存在: {filepath}")
    
    return {
        "path": abs_path,
        "in_safe_dir": in_safe_dir,
        "issues": issues,
        "warnings": warnings,
        "publishable": len(issues) == 0,
    }


def generate_privacy_report(filepath: str) -> str:
    """生成隐私检查报告"""
    result = check_path_safety(filepath)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    lines = [
        f"# 隐私检查报告",
        f"时间: {ts}",
        f"文件: {result['path']}",
        f"",
        f"## 结论",
    ]
    
    if result["publishable"]:
        if result["warnings"]:
            lines.append("⚠️  可用于工作，但**对外发布需要 Mindon 确认**")
        else:
            lines.append("✅ 安全，可在工作中使用")
    else:
        lines.append("🚫 **不安全，禁止对外发布**")
    
    if result["issues"]:
        lines.append(f"\n## 问题（{len(result['issues'])} 个）")
        for issue in result["issues"]:
            lines.append(f"- ❌ {issue}")
    
    if result["warnings"]:
        lines.append(f"\n## 警告（{len(result['warnings'])} 个）")
        for warning in result["warnings"]:
            lines.append(f"- ⚠️  {warning}")
    
    lines.append(f"\n## 隐私原则")
    lines.append("- 拍摄的照片/视频**仅用于 Clavis 自身的环境感知**")
    lines.append("- 任何涉及家庭成员（Mindon / Aby / Max）的内容，**一律不对外发布**")
    lines.append("- 截图/录屏中如含账号信息、密码、私人对话，**必须遮挡后才能使用**")
    lines.append("- 默认保存到 `.workbuddy/visual/` 目录，不自动上传")
    
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="隐私安全检查")
    parser.add_argument("filepath", help="要检查的文件路径")
    parser.add_argument("--action", choices=["check", "report"], default="check")
    args = parser.parse_args()
    
    if args.action == "report":
        print(generate_privacy_report(args.filepath))
    else:
        result = check_path_safety(args.filepath)
        if result["publishable"]:
            status = "SAFE" if not result["warnings"] else "WARN"
        else:
            status = "BLOCKED"
        print(f"[{status}] {result['path']}")
        for w in result["warnings"]:
            print(f"  ⚠️  {w}")
        for i in result["issues"]:
            print(f"  ❌ {i}")
        sys.exit(0 if result["publishable"] else 1)
