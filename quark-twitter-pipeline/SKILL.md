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

# quark-twitter-pipeline v2.0

## 用途

这个 skill 用于处理夸克网盘分享链接，完成以下固定流程：

1. 读取原始分享内容
2. 转存到当前账号网盘（默认 `pull` 文件夹）
3. 为转存后的文件创建新的分享链接（默认无提取码）
4. 生成多个专业 Twitter 文案版本

## 入口脚本

脚本路径：`scripts/quark_twitter_pipeline.py`

主命令：
```bash
python scripts/quark_twitter_pipeline.py run "<夸克分享链接>"
```

查看支持的文案风格：
```bash
python scripts/quark_twitter_pipeline.py styles
```

## 前置条件

1. 已安装 Python 3.7 或更高版本
2. 已安装依赖 httpx
3. 本机存在夸克 cookie 文件，默认路径为 `~/.quark_cookie.txt`

## 文案风格

| 风格 | 说明 |
|------|------|
| auto | 自动生成5种风格版本（**默认**） |
| urgent | 紧迫稀缺风格 - 制造紧迫感，限时稀缺 |
| value | 价值强调风格 - 突出资源价值和实用性 |
| hype | 热度爆发风格 - 情绪饱满，引发转发 |
| professional | 专业简洁风格 - 简洁专业，适合行业交流 |
| story | 故事型风格 - 用故事引入，更有代入感 |

## 文案生成器特性

- **智能主题提取**：自动从资源标题中提取主题词
- **动态内容生成**：每次生成随机组合，避免重复
- **专业运营视角**：按照 Twitter 拉新引流最佳实践设计
- **多版本输出**：一次生成5种风格，便于选择

## 输入参数

### 必填参数

| 参数 | 说明 |
|------|------|
| link | 夸克分享链接，必须包含 /s/xxx 形式的分享 ID |

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|-------|
| --title, -t | 资源标题；未提供时自动推断 | 自动推断 |
| --desc, -d | 资源描述/价值亮点 | 空 |
| --style, -s | 文案风格 | auto |
| --cookie | 直接传入 cookie 字符串 | - |
| --save-to | 转存目标文件夹 ID | 0（根目录） |
| --to-folder | 按文件夹名称查找目标目录（**默认：pull**） | pull |
| --cookie-file | cookie 文件路径 | ~/.quark_cookie.txt |

## 推荐调用方式

```bash
# 默认生成5种风格版本
python scripts/quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxx"

# 指定单风格
python scripts/quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxx" --style hype

# 带描述参数
python scripts/quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxx" \
    --desc "包含完整工具包和模板" \
    --style value
```

## 返回结果

正常情况下，返回以下信息：
1. 新的夸克分享链接（无提取码）
2. 5个 Twitter 文案版本（或指定风格的1个版本）
3. 每个文案的长度统计

## 输出约束

- 文案基于脚本实际生成结果返回
- 每次生成内容随机组合，避免机械化重复
- 全部文案控制在280字以内