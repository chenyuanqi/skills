# Skills Workspace

这个仓库收纳了 3 个围绕夸克网盘与 Twitter/X 分享流程的本地技能项目，适合在 Codex 或本地 Python 环境中直接调用。

## 项目概览

### 1. `quark-save-share`

夸克网盘转存与重新分享工具。

适用场景：
- 用户提供 `pan.quark.cn/s/...` 链接，希望转存到自己的夸克网盘
- 转存后需要重新生成新的分享链接
- 需要校验 cookie 是否有效

核心能力：
- 校验夸克登录态
- 将分享资源转存到指定目录或默认目录
- 为转存后的文件创建新的分享链接
- 支持命令行和 JSON 输出

脚本入口：
- `quark-save-share/scripts/quark_save.py`

依赖：
- Python 3.7+
- `httpx`

示例：

```bash
python quark-save-share/scripts/quark_save.py check --cookie-file ~/.quark_cookie.txt
python quark-save-share/scripts/quark_save.py save "https://pan.quark.cn/s/xxxx" --cookie-file ~/.quark_cookie.txt --share
python quark-save-share/scripts/quark_save.py config --default-folder "我的资源"
```

### 2. `quark-twitter-pipeline`

夸克分享链接的一键流水线：转存、重新分享、生成 Twitter/X 文案。

适用场景：
- 用户给出夸克链接，希望一键完成转存和重新分享
- 需要拿到新的分享链接和提取码
- 需要顺带生成可直接发布的 Twitter/X 文案

核心能力：
- 解析夸克分享内容
- 转存到自己的夸克网盘
- 为转存后的资源重新创建分享链接
- 按风格生成 3 个文案版本

脚本入口：
- `quark-twitter-pipeline/scripts/quark_twitter_pipeline.py`

依赖：
- Python 3.7+
- `httpx`

示例：

```bash
python quark-twitter-pipeline/scripts/quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxxx" --style urgent
python quark-twitter-pipeline/scripts/quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxxx" --title "资源标题" --desc "资源描述" --to-folder "我的资源"
python quark-twitter-pipeline/scripts/quark_twitter_pipeline.py styles
```

### 3. `twitter-share-skill`

Twitter/X 资源分享文案生成与二创改写工具。

适用场景：
- 根据标题、描述、链接生成分享文案
- 对已有文案做二创改写，避免直接复制
- 输出多个风格版本并检查是否超出 280 字限制

核心能力：
- 按模板生成多版本文案
- 支持改写模式
- 支持风格切换
- 支持 JSON 输出和本地默认配置

脚本入口：
- `twitter-share-skill/scripts/twitter_share.py`

依赖：
- Python 3.7+
- 标准库即可运行

示例：

```bash
python twitter-share-skill/scripts/twitter_share.py generate --title "资源标题" --desc "资源描述" --link "https://pan.quark.cn/s/xxxx" --style hype
python twitter-share-skill/scripts/twitter_share.py rewrite --text "原始文案内容" --style story
python twitter-share-skill/scripts/twitter_share.py styles
```

## 目录结构

```text
.
├── quark-save-share/
│   ├── SKILL.md
│   └── scripts/
├── quark-twitter-pipeline/
│   ├── SKILL.md
│   └── scripts/
└── twitter-share-skill/
    ├── SKILL.md
    └── scripts/
```

## 环境要求

- Python 3.7 或更高版本
- `pip` 可用
- 如需使用夸克相关项目，需要有效的夸克网盘 cookie

建议先创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install httpx
```

## 本地配置说明

这 3 个项目都偏向本地工具型脚本，运行时会依赖用户本机的配置或登录态：

- 夸克 cookie 常见存放位置：`~/.quark_cookie.txt`
- `quark-save-share` 配置文件：`~/.config/quark-save/config.json`
- `twitter-share-skill` 配置文件：`~/.config/twitter-share-skill/config.json`

这些文件属于本地运行数据，不应该提交到仓库。

## 仓库定位

这个仓库更像是一个技能集合，而不是一个统一打包发布的 Python 包：

- 每个子目录都是相对独立的 skill
- 每个 skill 通过 `SKILL.md` 描述用途、触发词和调用规范
- 实际能力主要由 `scripts/` 下的 Python 脚本提供

如果后续要继续扩展，建议保持以下约定：

- 每个 skill 独立目录
- 每个 skill 至少包含 `SKILL.md` 和 `scripts/`
- 外部依赖、配置路径、示例命令写清楚

## 注意事项

- 夸克 cookie 属于敏感登录凭证，不要提交到 Git
- 这些脚本主要面向本地调用，没有统一测试框架和发布流程
- `quark-save-share` 与 `quark-twitter-pipeline` 都依赖夸克接口稳定性，接口变化可能导致脚本失效
