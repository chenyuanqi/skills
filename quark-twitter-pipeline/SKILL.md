---
name: quark-twitter-pipeline
description: "接收夸克分享链接，执行转存、重新分享，并生成可直接发布的 Twitter 文案。"
triggers:
    - "夸克链接"
    - "pan.quark.cn"
    - "转存夸克分享"
    - "重新分享夸克资源"
    - "生成 Twitter 文案"
    - "资源分享文案"
---

# quark-twitter-pipeline

## 用途

这个 skill 用于处理夸克网盘分享链接，完成以下固定流程：

1. 读取原始分享内容。
2. 转存到当前账号网盘。
3. 为转存后的文件创建新的分享链接。
4. 生成 3 个可直接发布的 Twitter 文案版本。

适用场景：

- 用户给出一个夸克分享链接，希望转存到自己的网盘。
- 用户需要拿到新的夸克分享链接和提取码。
- 用户希望顺手生成一段或多段 Twitter 发布文案。

## 入口脚本

脚本路径：scripts/quark_twitter_pipeline.py

主命令：

```bash
python scripts/quark_twitter_pipeline.py run "<夸克分享链接>"
```

查看支持的文案风格：

```bash
python scripts/quark_twitter_pipeline.py styles
```

## 前置条件

执行前需要满足以下条件：

1. 已安装 Python 3.7 或更高版本。
2. 已安装依赖 httpx。
3. 本机存在夸克 cookie 文件，默认路径为 ~/.quark_cookie.txt。

安装依赖示例：

```bash
pip install httpx
```

如果默认 cookie 文件不存在，可以通过参数显式指定路径。

## 输入参数

### 必填参数

| 参数 | 说明 |
|------|------|
| link | 夸克分享链接，必须包含 /s/xxx 形式的分享 ID |

### 可选参数

| 参数 | 说明 |
|------|------|
| --title, -t | 资源标题；未提供时，脚本会根据原分享内容自动推断 |
| --desc, -d | 资源描述，用于生成文案 |
| --style, -s | 文案风格，默认 urgent |
| --save-to | 转存目标文件夹 ID，默认 0，即根目录 |
| --cookie-file | cookie 文件路径，默认 ~/.quark_cookie.txt |

## 文案风格

支持以下 style 值：

| 风格 | 说明 |
|------|------|
| urgent | 紧迫感导向，默认值 |
| value | 强调资源价值 |
| hype | 情绪更强，偏传播向 |
| casual | 语气较轻松 |
| professional | 更克制、简洁 |
| minimal | 极简输出 |

## 执行规则

当用户请求处理夸克分享链接时，按下面的顺序执行：

1. 从用户输入中提取夸克分享链接。
2. 确认是否需要覆盖默认参数，例如 title、desc、style、save-to、cookie-file。
3. 运行脚本的 run 子命令。
4. 等待脚本完成转存和重新分享。
5. 从结果中提取新分享链接、提取码和 3 个文案版本。
6. 将结果整理后返回给用户。

如果用户没有明确指定 style，使用 urgent。

## 推荐调用方式

完整示例：

```bash
python scripts/quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxx" \
    --title "资源标题" \
    --desc "资源描述" \
    --style urgent
```

## 返回结果

正常情况下，应向用户返回以下信息：

1. 新的夸克分享链接。
2. 提取码。如果脚本返回了提取码，则一并展示。
3. 3 个 Twitter 文案版本。
4. 每个文案是否在 280 字以内。

## 失败处理

出现以下情况时，应直接向用户说明失败原因：

- 分享链接无法解析。
- 原始分享为空或已失效。
- cookie 文件不存在或为空。
- 转存任务失败或超时。
- 新分享创建失败。

不要伪造分享结果，也不要在失败时编造文案。

## 输出约束

- 文案基于脚本实际生成结果返回，不要额外改写出与原输出风格不一致的内容。
- 如果用户只要新的分享链接，不必强行展开全部 3 个文案版本。
- 如果用户明确要“发推文案”，优先展示脚本输出的 3 个版本。
- 不要省略错误信息中的关键原因。
