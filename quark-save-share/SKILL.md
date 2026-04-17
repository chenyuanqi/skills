---
name: quark-save-share
description: |
  夸克网盘转存并分享工具。当用户提供夸克分享链接并希望转存到自己网盘，或需要生成新的分享链接时使用。
  支持：转存他人分享的夸克网盘文件、自动创建新的分享链接、验证 cookie 登录状态、指定目标文件夹、设置默认转存文件夹。
  触发词：夸克转存、转存夸克、夸克网盘转存、夸克分享、pan.quark.cn、夸克分享链接、生成分享链接。
allowed-tools:
  - Read
  - Write
  - Bash
metadata:
  base_dir: skills/quark-save-share
  script: scripts/quark_save.py
  requires: httpx
---

# quark-save-share：夸克网盘转存并分享技能

## 功能

将他人分享的夸克网盘链接（`pan.quark.cn/s/xxx`）自动转存到用户自己的夸克网盘，并可选择生成新的分享链接。

**只做转存和分享，不做二创。**

支持：
- 转存他人分享的夸克网盘文件
- 自动创建新的分享链接（`--share`）
- 指定目标文件夹（`--to-folder`）
- 设置默认转存文件夹（`config --default-folder`），避免每次手动指定

## 前置条件

1. **安装依赖**：`pip install httpx`
2. **准备 Cookie**：从浏览器中获取夸克网盘的登录 Cookie（见下方说明）
3. **设置默认转存文件夹**（首次使用建议）：避免文件散落在根目录

---

## 首次使用配置（重要）

**安装本 skill 后，首次使用时请提醒用户完成以下配置：**

### 1. 获取夸克 Cookie

1. 打开浏览器，访问 [https://pan.quark.cn](https://pan.quark.cn) 并登录
2. 按 F12 打开开发者工具 → Network（网络）标签页
3. 刷新页面，找到任意请求（如 `config`）
4. 在请求头（Request Headers）中找到 `cookie:` 字段
5. 复制完整的 cookie 字符串

**保存方式（推荐）**：将 cookie 保存到文件，如 `~/.quark_cookie.txt`

### 2. 设置默认转存文件夹（必须）

**首次使用前，必须设置默认转存文件夹，否则文件会散落在根目录。**

```bash
python {base_dir}/scripts/quark_save.py config --default-folder "我的资源"
```

建议先在夸克网盘网页版创建好这个文件夹，再执行设置命令。

---

## 使用方法

### AI 调用规范

当用户要求转存夸克链接或生成分享链接时，按以下步骤执行：

**Step 1：检查是否已配置默认文件夹**

```bash
python {base_dir}/scripts/quark_save.py config
```

如果显示"未设置默认转存文件夹"，**必须**先提醒用户设置：
> "建议先设置默认转存文件夹，避免文件散落在根目录。请先在夸克网盘创建一个文件夹（如'转存资源'），然后运行：`python scripts/quark_save.py config --default-folder '转存资源'`"

**Step 2：确认 cookie 来源**

询问用户 cookie 提供方式：
- 直接粘贴 cookie 字符串
- 指定 cookie 文件路径（如 `~/.quark_cookie.txt`）

**Step 3：验证登录状态**

```bash
python {base_dir}/scripts/quark_save.py check --cookie-file ~/.quark_cookie.txt
# 或
python {base_dir}/scripts/quark_save.py check --cookie "粘贴的cookie字符串"
```

**Step 4：执行转存（可选分享）**

仅转存：
```bash
python {base_dir}/scripts/quark_save.py save "https://pan.quark.cn/s/xxxxxxxx" --cookie-file ~/.quark_cookie.txt
```

转存并创建新的分享链接：
```bash
python {base_dir}/scripts/quark_save.py save "https://pan.quark.cn/s/xxxxxxxx" --cookie-file ~/.quark_cookie.txt --share
```

临时指定其他文件夹：
```bash
python {base_dir}/scripts/quark_save.py save "https://pan.quark.cn/s/xxxxxxxx" --cookie-file ~/.quark_cookie.txt --to-folder "其他文件夹" --share
```

**Step 5：向用户报告结果**

成功时告知：
- 已转存的文件名列表
- 文件已保存到的位置
- 新生成的分享链接和提取码（如果使用了 `--share`）

失败时根据错误信息给出建议（如 cookie 过期需重新获取、文件夹不存在需先创建）。

---

## 命令参数说明

| 命令 | 参数 | 说明 |
|------|------|------|
| `check` | `--cookie` | 直接传入 cookie 字符串 |
| `check` | `--cookie-file` | cookie 文件路径 |
| `save` | `url` | 夸克分享链接（必填） |
| `save` | `--cookie` | 直接传入 cookie 字符串 |
| `save` | `--cookie-file` | cookie 文件路径 |
| `save` | `--to-folder` | 目标文件夹名称（不传则使用默认设置，无默认则保存到根目录） |
| `save` | `--share` | 转存后自动创建新的分享链接 |
| `save` | `--json` | 以 JSON 格式输出结果 |
| `config` | `--default-folder` | 设置默认转存文件夹名称（传 null 取消） |

---

## 错误处理

| 错误信息 | 原因 | 解决方法 |
|----------|------|----------|
| cookie 无效或已过期 | 登录态失效 | 重新从浏览器获取 cookie |
| 网盘中未找到文件夹 'xxx' | 目标文件夹不存在 | 先在夸克网盘中创建该文件夹 |
| stoken 为空 | 分享需要提取码或已失效 | 确认分享链接有效，检查是否需要提取码 |
| 分享中没有找到文件 | 分享已过期或被删除 | 联系分享者重新分享 |
| 转存任务超时 | 网络问题或服务器繁忙 | 稍后重试 |

---

## 技术原理

参考 [Icy-Cat/QuarkMover](https://github.com/Icy-Cat/QuarkMover)，核心流程：

**转存流程：**
1. 从分享 URL 提取 `pwd_id`
2. 调用 `/share/sharepage/token` → 获取 `stoken`
3. 调用 `/share/sharepage/detail` → 列出文件（`fid_list`、`fid_token_list`）
4. （可选）调用 `/file/sort` → 查找目标文件夹的 `fid`
5. 调用 `/share/sharepage/save` → 发起转存（指定 `to_pdir_fid`），得到 `task_id`
6. 轮询 `/task` 接口 → 等待 `status == 2`（完成）

**分享流程：**
7. 调用 `/share` → 创建新的分享链接
8. 调用 `/share/detail` → 获取分享链接和提取码

配置文件保存在 `~/.config/quark-save/config.json`。

---

## 注意事项

- Cookie 是登录凭证，请妥善保管，不要泄露
- Cookie 通常几天后过期，过期后需重新获取
- 目标文件夹必须先在网盘中创建好，脚本不会自动创建文件夹
- 建议设置默认转存文件夹，避免文件散落在根目录
- 此工具仅实现转存和分享功能，不涉及文件内容修改或二创
- 依赖 `httpx` 库，首次使用请确保已安装
