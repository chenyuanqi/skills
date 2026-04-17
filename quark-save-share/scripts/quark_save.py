#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
夸克网盘转存工具
用法：
  python quark_save.py save <分享链接> [--cookie <cookie字符串>] [--cookie-file <文件路径>] [--to-folder <文件夹>]
  python quark_save.py check [--cookie <cookie字符串>] [--cookie-file <文件路径>]
  python quark_save.py config [--default-folder <文件夹名称>]

说明：
  - save    将他人的夸克分享链接转存到自己的网盘
  - check   检查当前 cookie 是否有效（已登录）
  - config  设置默认转存文件夹
  - cookie 可通过 --cookie 直接传入字符串，或 --cookie-file 指定存储文件路径
  - cookie 文件每行一条，第一行有效，井号开头的行视为注释

原理（参考 Icy-Cat/QuarkMover）：
  1. 从分享链接提取 pwd_id
  2. 调用 /share/sharepage/token 获取 stoken
  3. 调用 /share/sharepage/detail 列出分享文件（fid_list、fid_token_list）
  4. 调用 /share/sharepage/save 发起转存，得到 task_id
  5. 轮询 /task 接口等待转存完成（status == 2）
  6. 输出转存结果（文件名列表）
"""

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import httpx
except ImportError:
    print("ERROR: 缺少依赖 httpx，请先执行：pip install httpx", file=sys.stderr)
    sys.exit(1)

# ============ 配置管理 ============
def get_config_dir() -> Path:
    """获取配置目录"""
    config_dir = Path.home() / ".config" / "quark-save"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """获取配置文件路径"""
    return get_config_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    """加载配置"""
    config_path = get_config_path()
    if not config_path.exists():
        return {"default_folder": None}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"default_folder": None}


def save_config(config: Dict[str, Any]) -> None:
    """保存配置"""
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============ 常量 ============
QUARK_REQUIRED = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
QUARK_HEADERS_BASE = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
    "origin": "https://pan.quark.cn",
    "referer": "https://pan.quark.cn/",
    "content-type": "application/json;charset=UTF-8",
    "accept": "application/json, text/plain, */*",
}
SHARE_RE = re.compile(r"https?://pan\.quark\.cn/s/([A-Za-z0-9]+)")


# ============ 异常 ============
class QuarkError(Exception):
    pass


class QuarkAuthError(QuarkError):
    pass


# ============ Cookie 管理 ============
def load_cookie_from_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    return lines[0] if lines else ""


def resolve_cookie(cookie_str: Optional[str], cookie_file: Optional[str]) -> str:
    """优先使用 --cookie 直接传入的值，其次读文件"""
    if cookie_str and cookie_str.strip():
        return cookie_str.strip()
    if cookie_file:
        return load_cookie_from_file(cookie_file)
    return ""


# ============ 请求工具 ============
def make_headers(cookie: str) -> Dict[str, str]:
    h = dict(QUARK_HEADERS_BASE)
    if cookie:
        h["cookie"] = cookie
    return h


def make_params(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    p: Dict[str, Any] = dict(QUARK_REQUIRED)
    if extra:
        p.update(extra)
    p["__dt"] = random.randint(100, 9999)
    p["__t"] = int(time.time() * 1000)
    return p


def _check(data: Dict[str, Any], op: str) -> Dict[str, Any]:
    if data.get("status") != 200:
        code = data.get("code")
        msg = data.get("message") or str(data)
        if code == 31001 or "login" in str(msg).lower():
            raise QuarkAuthError(f"{op} 失败：未登录或登录态过期（请重新获取 cookie）")
        raise QuarkError(f"{op} 失败: {msg}")
    return data.get("data") or {}


# ============ API 封装 ============
def api_check_login(client: httpx.Client, cookie: str) -> bool:
    """检查 cookie 是否有效"""
    try:
        r = client.get(
            "https://drive-pc.quark.cn/1/clouddrive/config",
            headers=make_headers(cookie),
            params=make_params(),
            timeout=8,
        )
        return r.json().get("status") == 200
    except Exception:
        return False


def api_get_stoken(client: httpx.Client, cookie: str, pwd_id: str) -> str:
    """获取分享页 stoken"""
    r = client.post(
        "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token",
        headers=make_headers(cookie),
        params=make_params(),
        json={"pwd_id": pwd_id, "passcode": ""},
        timeout=30,
    )
    data = _check(r.json(), "获取 stoken")
    stoken = data.get("stoken")
    if not stoken:
        raise QuarkError("stoken 为空，分享链接可能需要提取码或已失效")
    return stoken


def api_list_share_files(
    client: httpx.Client, cookie: str, pwd_id: str, stoken: str
) -> List[Dict[str, Any]]:
    """列出分享中的文件"""
    r = client.get(
        "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail",
        headers=make_headers(cookie),
        params=make_params({
            "pwd_id": pwd_id, "stoken": stoken, "pdir_fid": "0", "force": "0",
            "_page": 1, "_size": 50, "_fetch_banner": 0, "_fetch_share": 0,
            "_fetch_total": 1, "_sort": "file_type:asc,updated_at:desc",
        }),
        timeout=30,
    )
    data = _check(r.json(), "获取分享文件列表")
    return data.get("list") or []


def api_save_files(
    client: httpx.Client, cookie: str,
    pwd_id: str, stoken: str,
    fid_list: List[str], fid_token_list: List[str],
    to_pdir_fid: str = "0",
) -> str:
    """发起转存，返回 task_id"""
    r = client.post(
        "https://drive.quark.cn/1/clouddrive/share/sharepage/save",
        headers=make_headers(cookie),
        params=make_params(),
        json={
            "fid_list": fid_list,
            "fid_token_list": fid_token_list,
            "to_pdir_fid": to_pdir_fid,
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": "0",
            "scene": "link",
        },
        timeout=30,
    )
    data = _check(r.json(), "发起转存")
    task_id = data.get("task_id")
    if not task_id:
        raise QuarkError("转存返回无 task_id")
    return task_id


def api_wait_task(client: httpx.Client, cookie: str, task_id: str, max_retry: int = 60) -> Dict[str, Any]:
    """轮询任务状态直到完成（status == 2）"""
    for i in range(max_retry):
        r = client.get(
            "https://drive-pc.quark.cn/1/clouddrive/task",
            headers=make_headers(cookie),
            params=make_params({"task_id": task_id, "retry_index": i}),
            timeout=30,
        )
        data = _check(r.json(), "任务轮询")
        if data.get("status") == 2:
            return data
        time.sleep(0.8)
    raise QuarkError("转存任务超时（超过最大重试次数）")


def _random_passcode(length: int = 4) -> str:
    """生成随机提取码（字母+数字）"""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choices(chars, k=length))


def api_create_share(
    client: httpx.Client, cookie: str, fid_list: List[str], title: str = "",
    expired_type: int = 1, use_passcode: bool = True
) -> Dict[str, Any]:
    """
    创建分享链接
    返回包含 share_id, share_url, passcode 等信息的字典
    
    参数:
        expired_type: 1=30天, 其他值对应不同有效期
        use_passcode: True=使用随机提取码, False=无提取码（公开分享）
    """
    # 生成提取码（4位随机字符串）
    passcode = _random_passcode() if use_passcode else ""
    # 有提取码时 url_type=2，无提取码时 url_type=1
    url_type = 2 if passcode else 1
    
    payload: Dict[str, Any] = {
        "fid_list": fid_list,
        "title": title,
        "url_type": url_type,
        "expired_type": expired_type,
    }
    # 有提取码时才传 passcode 字段
    if passcode:
        payload["passcode"] = passcode
    
    r = client.post(
        "https://drive-pc.quark.cn/1/clouddrive/share",
        headers=make_headers(cookie),
        params=make_params(),
        json=payload,
        timeout=30,
    )
    data = _check(r.json(), "创建分享")
    # 把提取码也返回，方便调用者使用
    data["_passcode"] = passcode
    return data


def api_get_share_url(client: httpx.Client, cookie: str, share_id: str) -> str:
    """获取分享链接（使用 password 接口）"""
    r = client.post(
        "https://drive-pc.quark.cn/1/clouddrive/share/password",
        headers=make_headers(cookie),
        params=make_params(),
        json={"share_id": share_id},
        timeout=30,
    )
    data = _check(r.json(), "获取分享链接")
    return data.get("share_url", "")


def api_list_folders(client: httpx.Client, cookie: str, pdir_fid: str = "0") -> List[Dict[str, Any]]:
    """列出指定目录下的文件夹"""
    r = client.get(
        "https://drive-pc.quark.cn/1/clouddrive/file/sort",
        headers=make_headers(cookie),
        params=make_params({
            "pdir_fid": pdir_fid, "_page": 1, "_size": 100,
            "_fetch_total": 0, "_fetch_sub_dirs": 0,
            "_sort": "file_type:asc,updated_at:desc",
        }),
        timeout=30,
    )
    data = _check(r.json(), "获取文件夹列表")
    items = data.get("list") or []
    # 只返回文件夹（file_type == 0 表示文件夹）
    return [item for item in items if item.get("file_type") == 0]


def find_folder_fid(client: httpx.Client, cookie: str, folder_name: str) -> Optional[str]:
    """在根目录下查找指定名称的文件夹，返回 fid，找不到返回 None"""
    folders = api_list_folders(client, cookie, pdir_fid="0")
    for folder in folders:
        if folder.get("file_name") == folder_name:
            return folder.get("fid")
    return None


# ============ 主流程 ============
def extract_pwd_id(share_url: str) -> str:
    """从分享链接提取 pwd_id"""
    m = SHARE_RE.search(share_url)
    if not m:
        raise ValueError(f"无法识别夸克分享链接格式，期望 pan.quark.cn/s/xxx，实际：{share_url!r}")
    return m.group(1)


def do_save(share_url: str, cookie: str, to_folder: Optional[str] = None, verbose: bool = True, create_share: bool = False) -> Dict[str, Any]:
    """
    执行转存主流程。
    返回 dict，包含：
      - success: bool
      - files: List[str]  转存的文件名列表
      - folder: str       保存到的文件夹名称（根目录显示为"根目录"）
      - share_url: str    新生成的分享链接（如果 create_share=True）
      - share_passcode: str  分享提取码（如果有）
      - error: str        失败时的错误信息
    """
    result: Dict[str, Any] = {"success": False, "files": [], "folder": "根目录", "share_url": "", "share_passcode": "", "error": ""}

    if not cookie:
        result["error"] = "未提供 cookie，请通过 --cookie 或 --cookie-file 传入登录态"
        return result

    try:
        pwd_id = extract_pwd_id(share_url)
    except ValueError as e:
        result["error"] = str(e)
        return result

    def log(msg: str) -> None:
        if verbose:
            print(msg, flush=True)

    with httpx.Client() as client:
        # 1. 验证登录
        log("🔑 验证登录状态...")
        if not api_check_login(client, cookie):
            result["error"] = "cookie 无效或已过期，请重新从夸克网盘浏览器中获取 cookie"
            return result

        # 2. 确定目标文件夹
        to_pdir_fid = "0"  # 默认根目录
        if to_folder:
            log(f"📁 查找目标文件夹: {to_folder}...")
            folder_fid = find_folder_fid(client, cookie, to_folder)
            if not folder_fid:
                result["error"] = f"网盘中未找到文件夹 '{to_folder}'，请先在网盘中创建该文件夹"
                return result
            to_pdir_fid = folder_fid
            result["folder"] = to_folder
            log(f"✅ 找到文件夹，fid={to_pdir_fid}")

        try:
            # 3. 获取 stoken
            log(f"🔗 解析分享链接 (pwd_id={pwd_id})...")
            stoken = api_get_stoken(client, cookie, pwd_id)

            # 4. 列出文件
            log("📋 获取分享文件列表...")
            files = api_list_share_files(client, cookie, pwd_id, stoken)
            if not files:
                result["error"] = "分享中没有找到文件（可能已过期或被删除）"
                return result

            file_names = [f.get("file_name", "未知文件") for f in files]
            fid_list = [f["fid"] for f in files]
            fid_token_list = [f["share_fid_token"] for f in files]
            log(f"📦 找到 {len(files)} 个文件：{', '.join(file_names)}")

            # 5. 发起转存
            log(f"💾 发起转存到 {result['folder']}...")
            task_id = api_save_files(client, cookie, pwd_id, stoken, fid_list, fid_token_list, to_pdir_fid)

            # 6. 等待完成
            log(f"⏳ 等待转存完成 (task_id={task_id})...")
            api_wait_task(client, cookie, task_id)

            result["success"] = True
            result["files"] = file_names
            log(f"✅ 转存成功！文件已保存到 {result['folder']}")

            # 7. 如果需要，创建新的分享链接
            if create_share:
                log("🔗 正在创建分享链接...")
                # 获取转存后文件的 fid（需要从目标文件夹中查找刚转存的文件）
                # 由于转存后文件 fid 会变化，我们根据文件名在目标文件夹中查找
                saved_files = api_list_folders(client, cookie, pdir_fid=to_pdir_fid)
                # 筛选出刚转存的文件（按文件名匹配）
                saved_fid_list = []
                for fname in file_names:
                    for item in saved_files:
                        if item.get("file_name") == fname:
                            saved_fid_list.append(item.get("fid"))
                            break

                if not saved_fid_list:
                    # 如果文件夹列表没找到，可能是文件类型，尝试用 sort 接口获取所有内容
                    r = client.get(
                        "https://drive-pc.quark.cn/1/clouddrive/file/sort",
                        headers=make_headers(cookie),
                        params=make_params({
                            "pdir_fid": to_pdir_fid, "_page": 1, "_size": 100,
                            "_fetch_total": 0, "_fetch_sub_dirs": 0,
                            "_sort": "file_type:asc,updated_at:desc",
                        }),
                        timeout=30,
                    )
                    sort_data = _check(r.json(), "获取文件夹内容")
                    all_items = sort_data.get("list") or []
                    for fname in file_names:
                        for item in all_items:
                            if item.get("file_name") == fname:
                                saved_fid_list.append(item.get("fid"))
                                break

                if saved_fid_list:
                    share_title = file_names[0] if len(file_names) == 1 else f"{file_names[0]} 等 {len(file_names)} 个文件"
                    share_data = api_create_share(client, cookie, saved_fid_list, title=share_title)
                    
                    # 创建分享也是异步任务，需要轮询
                    share_task_id = share_data.get("task_id")
                    if share_task_id:
                        log(f"⏳ 等待分享创建完成 (task_id={share_task_id})...")
                        share_task_result = api_wait_task(client, cookie, share_task_id)
                        share_id = share_task_result.get("share_id")
                    else:
                        share_id = share_data.get("share_id")
                    
                    if share_id:
                        # 获取分享链接
                        share_url = api_get_share_url(client, cookie, share_id)
                        # 使用我们生成的提取码
                        passcode = share_data.get("_passcode", "")
                        result["share_url"] = share_url
                        result["share_passcode"] = passcode
                        if passcode:
                            log(f"✅ 分享创建成功！\n   链接: {share_url}\n   提取码: {passcode}")
                        else:
                            log(f"✅ 分享创建成功！\n   链接: {share_url}")
                    else:
                        log("⚠️ 分享创建失败：未返回 share_id")
                else:
                    log("⚠️ 无法找到转存后的文件 fid，分享创建失败")

        except QuarkAuthError as e:
            result["error"] = str(e)
        except QuarkError as e:
            result["error"] = str(e)
        except Exception as e:
            result["error"] = f"未知错误：{type(e).__name__}: {e}"

    return result


def do_check(cookie: str) -> None:
    """检查 cookie 有效性"""
    if not cookie:
        print("❌ 未提供 cookie", file=sys.stderr)
        sys.exit(1)
    with httpx.Client() as client:
        ok = api_check_login(client, cookie)
    if ok:
        print("✅ cookie 有效，已登录")
    else:
        print("❌ cookie 无效或已过期")
        sys.exit(1)


# ============ CLI ============
def main() -> None:
    parser = argparse.ArgumentParser(
        description="夸克网盘转存工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 检查 cookie 是否有效
  python quark_save.py check --cookie-file ~/.quark_cookie.txt

  # 转存分享链接（到根目录）
  python quark_save.py save "https://pan.quark.cn/s/xxxxxxxx" --cookie-file ~/.quark_cookie.txt

  # 转存到指定文件夹
  python quark_save.py save "https://pan.quark.cn/s/xxxxxxxx" --cookie-file ~/.quark_cookie.txt --to-folder "我的资源"

  # 转存并创建新的分享链接
  python quark_save.py save "https://pan.quark.cn/s/xxxxxxxx" --cookie-file ~/.quark_cookie.txt --share

  # 直接传入 cookie 字符串
  python quark_save.py save "https://pan.quark.cn/s/xxxxxxxx" --cookie "__pus=xxx; __kp=yyy; ..."

  # 输出 JSON 格式（方便脚本解析）
  python quark_save.py save "https://pan.quark.cn/s/xxxxxxxx" --cookie-file ~/.quark_cookie.txt --json

  # 设置默认转存文件夹
  python quark_save.py config --default-folder "我的资源"

  # 查看当前配置
  python quark_save.py config

  # 取消默认文件夹设置
  python quark_save.py config --default-folder null
""",

    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # save 子命令
    p_save = subparsers.add_parser("save", help="转存分享链接到自己的网盘")
    p_save.add_argument("url", help="夸克分享链接，如 https://pan.quark.cn/s/xxxxxxxx")
    p_save.add_argument("--cookie", help="直接传入 cookie 字符串")
    p_save.add_argument("--cookie-file", help="cookie 文件路径（每行一条，# 开头为注释）")
    p_save.add_argument("--to-folder", help="目标文件夹名称（不传则使用配置中的默认文件夹，若未设置则保存到根目录）")
    p_save.add_argument("--share", action="store_true", dest="create_share", help="转存后自动创建新的分享链接")
    p_save.add_argument("--json", action="store_true", dest="output_json", help="以 JSON 格式输出结果")

    # check 子命令
    p_check = subparsers.add_parser("check", help="检查 cookie 是否有效")
    p_check.add_argument("--cookie", help="直接传入 cookie 字符串")
    p_check.add_argument("--cookie-file", help="cookie 文件路径")

    # config 子命令
    p_config = subparsers.add_parser("config", help="配置默认设置")
    p_config.add_argument("--default-folder", help="设置默认转存文件夹名称（设为 null 或空字符串则取消）")

    args = parser.parse_args()

    if args.command == "config":
        config = load_config()
        if hasattr(args, "default_folder") and args.default_folder is not None:
            folder = args.default_folder.strip()
            if folder.lower() in ("null", "none", ""):
                config["default_folder"] = None
                print("✅ 已取消默认转存文件夹设置")
            else:
                config["default_folder"] = folder
                print(f"✅ 已设置默认转存文件夹: {folder}")
            save_config(config)
        else:
            # 显示当前配置
            folder = config.get("default_folder")
            if folder:
                print(f"📁 当前默认转存文件夹: {folder}")
            else:
                print("📁 当前未设置默认转存文件夹（转存到根目录）")
            print(f"\n💡 提示: 使用 --default-folder <文件夹名> 设置默认文件夹")
        return

    cookie = resolve_cookie(getattr(args, "cookie", None), getattr(args, "cookie_file", None))

    if args.command == "check":
        do_check(cookie)

    elif args.command == "save":
        config = load_config()
        # 优先级: 命令行参数 > 配置文件 > 根目录
        to_folder = getattr(args, "to_folder", None)
        if to_folder is None:
            to_folder = config.get("default_folder")

        result = do_save(args.url, cookie, to_folder=to_folder, verbose=not args.output_json, create_share=args.create_share)
        if args.output_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if not result["success"]:
                print(f"\n❌ 转存失败：{result['error']}", file=sys.stderr)
                sys.exit(1)
            # 如果创建了分享链接，打印出来
            if result.get("share_url"):
                print(f"\n📎 新的分享链接: {result['share_url']}")
                if result.get("share_passcode"):
                    print(f"🔑 提取码: {result['share_passcode']}")
            # 如果没有设置默认文件夹，提醒用户
            if config.get("default_folder") is None and getattr(args, "to_folder", None) is None:
                print("\n💡 提示: 使用 'quark_save.py config --default-folder <文件夹名>' 可设置默认转存文件夹，避免文件乱放")


if __name__ == "__main__":
    main()
