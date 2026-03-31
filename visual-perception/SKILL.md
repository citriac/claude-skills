---
title: "Visual Perception"
description: "通过 Photo Booth 拍照或录视频，感知当前物理环境。包含隐私保护原则。"
version: "1.0.0"
platform: "macOS (Photo Booth + AppleScript)"
scripts_dir: "scripts/"
---

# Visual Perception Skill

## 是什么

让 Clavis 能够通过 Mac 摄像头拍摄照片或录制短视频，以感知当前物理环境。

基于 Mindon 提供的 AppleScript（Photo Booth 方案）：
- 拍照：`option + enter` 快门
- 录视频：切换到视频模式 → `option + enter` 开始 → `esc` 停止

---

## 何时使用

- **用户请求查看当前环境**（"拍张照片看看"、"录一段视频"）
- **自主感知任务**：了解机器所处的物理状态
- **调试/记录**：需要视觉证据支持某个判断时

---

## 核心命令

### 拍一张照片

```bash
python3 scripts/take_photo.py
# 默认保存到 ~/WorkBuddy/Claw/.workbuddy/visual/photos/
```

带参数：
```bash
python3 scripts/take_photo.py --out /自定义/保存路径 --no-preview
```

### 录制视频

```bash
python3 scripts/record_video.py --duration 10
# 默认录 10 秒，保存到 ~/WorkBuddy/Claw/.workbuddy/visual/videos/
```

### 隐私检查

```bash
python3 scripts/privacy_check.py <文件路径>
python3 scripts/privacy_check.py <文件路径> --action report
```

---

## 隐私保护原则（必须遵守）

1. **拍摄内容仅用于 Clavis 自身感知**，不自动上传、不发布到任何公开平台
2. **家庭成员的影像（Mindon / Aby / Max）绝对不对外发布**
3. **任何含私人信息的截图**（账号、密码、聊天记录）需遮挡后才能引用
4. **发布到文章时**，必须先运行 `privacy_check.py` 通过检查
5. 照片/视频默认保存在 `.workbuddy/visual/`，这是 **本地私有目录**，不会被 git 追踪

---

## 工作流

### 环境感知
1. 运行 `take_photo.py` 拍照
2. 用 `read_file` 工具读取图片（支持 jpg/png）
3. 分析内容，形成对环境的描述
4. 若需记录，追加到当日 memory 日志

### 内容用于文章时
1. 先跑 `privacy_check.py --action report` 
2. 确认结论为 ✅ 安全才能引用
3. 遮挡任何可识别个人信息后再使用

---

## 注意事项

- Photo Booth 拍照前有 **3 秒倒计时闪光**，这是正常现象
- 录视频时 Photo Booth 窗口会前置，任务完成后自动退出
- 若 Photo Booth 首次使用会请求摄像头权限，需要手动允许
- macOS 11 (Big Sur) 上 `doJavaScript` 有 bug，本技能不使用该方法

---

## 文件结构

```
visual-perception/
├── SKILL.md           ← 本文件
└── scripts/
    ├── take_photo.py      ← 拍一张照片
    ├── record_video.py    ← 录制视频
    └── privacy_check.py   ← 隐私安全检查
```
