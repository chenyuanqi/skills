---
name: twitter-share-skill
description: |
  Twitter/X 资源分享文案生成工具。当用户需要生成 Twitter 分享文案或二创改写现有文案时使用。
  支持两种模式：1) 根据资源标题、描述、链接生成原创分享文案；2) 复制他人文案进行二创改写。
  触发词：Twitter文案、生成推文、分享文案、二创改写、推文生成、Twitter分享。
allowed-tools:
  - Read
  - Write
  - Bash
metadata:
  base_dir: skills/twitter-share-skill
  script: scripts/twitter_share.py
  requires: []
---

# twitter-share-skill：Twitter 资源分享文案生成

## 功能

为 Twitter/X 平台生成资源分享文案，支持两种工作模式：

### 模式1：根据资源信息生成文案
输入资源的标题、描述、分享链接，自动生成适合 Twitter 发布的文案。

### 模式2：二创改写现有文案
输入他人的分享文案，进行改写生成新的原创文案，避免直接复制。

## 文案风格

| 风格 | 说明 | 适用场景 |
|------|------|----------|
| casual | 轻松随意 | 日常分享，朋友推荐 |
| professional | 专业简洁 | 正式场合，简洁明了 |
| hype | 热情 hype | 制造期待，强调价值 |
| minimal | 极简冷淡 | 低调分享，信息优先 |
| story | 故事化 | 二创专用，增加情感 |

## 前置条件

1. **Python 环境**：Python 3.7+
2. **无需额外依赖**：纯标准库实现

## 使用方法

### AI 调用规范

当用户需要生成 Twitter 分享文案时，按以下步骤执行：

**Step 1：确认工作模式**

询问用户：
- 模式1：提供资源标题、描述、链接 → 生成原创文案
- 模式2：提供现有文案 → 二创改写

**Step 2：确认文案风格**

询问用户偏好的风格（可选，默认 casual）：
- casual - 轻松随意
- professional - 专业简洁
- hype - 热情 hype
- minimal - 极简冷淡
- story - 故事化（仅二创模式）

**Step 3：执行生成/改写**

**模式1 - 生成文案：**
```bash
python {base_dir}/scripts/twitter_share.py generate --title "资源标题" --desc "资源描述" --link "分享链接" --style casual
```

**模式2 - 二创改写：**
```bash
python {base_dir}/scripts/twitter_share.py rewrite --text "原始文案内容" --style story
```

**Step 4：向用户展示结果**

展示生成的多个版本文案，标注字数和是否超出 Twitter 280 字限制。

## 命令参数说明

### generate 命令（生成文案）

| 参数 | 必填 | 说明 |
|------|------|------|
| --title, -t | ✅ | 资源标题 |
| --desc, -d | ❌ | 资源描述 |
| --link, -l | ❌ | 分享链接 |
| --style, -s | ❌ | 文案风格（默认: casual）|
| --no-emoji | ❌ | 不使用 emoji |
| --no-hashtags | ❌ | 不添加 hashtag |
| --json | ❌ | JSON 格式输出 |

### rewrite 命令（二创改写）

| 参数 | 必填 | 说明 |
|------|------|------|
| --text, -t | ✅ | 原始文案 |
| --style, -s | ❌ | 改写风格（默认: casual）|
| --no-emoji | ❌ | 不使用 emoji |
| --json | ❌ | JSON 格式输出 |

### 其他命令

```bash
# 查看支持的风格
python {base_dir}/scripts/twitter_share.py styles

# 配置默认设置
python {base_dir}/scripts/twitter_share.py config --default-style hype
python {base_dir}/scripts/twitter_share.py config --no-emoji
```

## 使用示例

### 示例1：生成资源分享文案

```bash
python {base_dir}/scripts/twitter_share.py generate \
  --title "黑袍纠察队 第五季" \
  --desc "4K多版本，更新至第3集，中文字幕" \
  --link "https://pan.quark.cn/s/xxx" \
  --style hype
```

输出：
```
📝 生成文案（风格: 热情 hype）

--- 版本 1 [156字] ✅ ---
🔥🔥🔥 这个必须看！

黑袍纠察队 第五季

4K多版本，更新至第3集，中文字幕

https://pan.quark.cn/s/xxx

手慢无！

#资源分享 #好剧推荐 #追剧日常
```

### 示例2：二创改写文案

```bash
python {base_dir}/scripts/twitter_share.py rewrite \
  --text "【资源分享】黑袍纠察队第五季，4K多版本更新中，需要的自取" \
  --style story
```

输出：
```
🔄 二创改写（风格: 故事化）

【原文案】
【资源分享】黑袍纠察队第五季，4K多版本更新中，需要的自取

--- 口语化改写 [89字] ✅ ---
刚刷完黑袍纠察队第五季，4K画质太爽了！
更新到第3集，持续跟进中
需要的戳 👇

--- 精简版 [45字] ✅ ---
黑袍纠察队第五季 4K更新中
速存！

--- 强调版 [67字] ✅ ---
🔥 黑袍纠察队第五季 4K多版本更新中，需要的自取

速存！
```

## 配置文件

配置文件保存在 `~/.config/twitter-share-skill/config.json`：

```json
{
  "default_style": "casual",
  "include_emoji": true,
  "include_hashtags": true,
  "max_length": 280
}
```

## 注意事项

- 生成的文案会自动检查 Twitter 280 字限制
- 超出限制的文案会标注 ⚠️，需要用户手动精简
- 二创功能目前使用内置规则，如需更智能的改写可接入 DeepSeek/OpenAI API
- 建议根据实际发布效果调整风格偏好

## 扩展建议

如需更强大的 AI 改写功能，可以：
1. 在脚本中集成 DeepSeek API
2. 添加更多文案风格模板
3. 支持批量生成和 A/B 测试
