#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
夸克转存 + Twitter 文案一键流水线

功能：看到夸克分享链接 → 转存到自己网盘 → 创建新分享 → 生成 Twitter 文案
"""

import argparse
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

# ============ 配置 ============
DEFAULT_COOKIE_FILE = Path.home() / ".quark_cookie.txt"
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

# ============ 文案模板 ============
STYLE_TEMPLATES = {
    "urgent": {
        "name": "紧迫稀缺",
        "templates": [
            "⚠️ 限时资源，随时可能失效\n\n{title}\n{desc}\n\n{link}\n\n看到就存，别等没了再后悔",
            "🚨 稀缺资源预警\n\n{title}\n{desc}\n\n{link}\n\n这种好东西不常有，速存",
            "⏰ 最后机会\n\n{title}\n{desc}\n\n{link}\n\n存了就是自己的，手慢无",
        ],
    },
    "value": {
        "name": "价值强调",
        "templates": [
            "💰 这份资源值多少钱，懂的人都懂\n\n{title}\n{desc}\n\n{link}\n\n免费的就是最贵的，先存为敬",
            "🎯 花了不少时间整理的干货\n\n{title}\n{desc}\n\n{link}\n\n存了慢慢看，绝对值",
            "📦 一次性打包带走\n\n{title}\n{desc}\n\n{link}\n\n这种合集不常有，建议收藏",
        ],
    },
    "hype": {
        "name": "热情 hype",
        "templates": [
            "🔥 手慢无！这个必须存\n\n{title}\n{desc}\n\n{link}\n\n看到就是赚到，速存！",
            "💎 挖到宝了！\n\n{title}\n{desc}\n\n{link}\n\n不存后悔系列，先存为敬",
            "😱 不允许还有人没存这个！\n\n{title}\n{desc}\n\n{link}\n\n存了=赚了",
        ],
    },
    "casual": {
        "name": "轻松随意",
        "templates": [
            "刚刷到的好东西 👇\n\n{title}\n{desc}\n\n{link}\n\n看到就是赚到，存了再说",
            "今日份收获 ✨\n\n{title}\n{desc}\n\n{link}\n\n不存后悔系列",
            "这个有点东西\n\n{title}\n{desc}\n\n{link}\n\n先存为敬",
        ],
    },
    "professional": {
        "name": "专业简洁",
        "templates": [
            "【精选资源】{title}\n\n{desc}\n\n{link}\n\n建议收藏",
            "{title}\n\n{desc}\n\n→ {link}\n\n值得保存",
        ],
    },
    "minimal": {
        "name": "极简冷淡",
        "templates": [
            "{title}\n\n{link}",
            "{title}｜{desc}\n\n{link}",
        ],
    },
}


# ============ 夸克 API ============
class QuarkError(Exception):
    pass


class QuarkAuthError(QuarkError):
    pass


def ensure_httpx() -> None:
    if httpx is None:
        raise RuntimeError("缺少依赖 httpx，请先执行：pip install httpx")


def load_cookie_from_file(path: Path) -> str:
    if not path.exists():
        return ""
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return lines[0] if lines else ""


def make_headers(cookie: str) -> Dict[str, str]:
    headers = dict(QUARK_HEADERS_BASE)
    if cookie:
        headers["cookie"] = cookie
    return headers


def make_params(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = dict(QUARK_REQUIRED)
    if extra:
        params.update(extra)
    params["__dt"] = random.randint(100, 9999)
    params["__t"] = int(time.time() * 1000)
    return params


def _check(res: Dict[str, Any], action: str) -> Dict[str, Any]:
    if res.get("status") != 200:
        code = res.get("code")
        msg = res.get("message") or str(res)
        if code == 31001 or "login" in str(msg).lower():
            raise QuarkAuthError(f"{action}失败：未登录或登录态过期（请重新获取 cookie）")
        raise QuarkError(f"{action}失败: {msg}")
    return res.get("data") or {}


def extract_pwd_id(share_url: str) -> str:
    match = SHARE_RE.search(share_url)
    if not match:
        raise ValueError(f"无法识别夸克分享链接格式，期望 pan.quark.cn/s/xxx，实际：{share_url!r}")
    return match.group(1)


def api_check_login(client: httpx.Client, cookie: str) -> bool:
    try:
        response = client.get(
            "https://drive-pc.quark.cn/1/clouddrive/config",
            headers=make_headers(cookie),
            params=make_params(),
            timeout=8,
        )
        return response.json().get("status") == 200
    except Exception:
        return False


def api_get_stoken(client: httpx.Client, cookie: str, pwd_id: str) -> str:
    response = client.post(
        "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token",
        headers=make_headers(cookie),
        params=make_params(),
        json={"pwd_id": pwd_id, "passcode": ""},
        timeout=30,
    )
    data = _check(response.json(), "获取 stoken")
    stoken = data.get("stoken")
    if not stoken:
        raise QuarkError("stoken 为空，分享链接可能需要提取码或已失效")
    return stoken


def api_list_share_files(
    client: httpx.Client,
    cookie: str,
    pwd_id: str,
    stoken: str,
) -> List[Dict[str, Any]]:
    response = client.get(
        "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail",
        headers=make_headers(cookie),
        params=make_params({
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": "0",
            "force": "0",
            "_page": 1,
            "_size": 50,
            "_fetch_banner": 0,
            "_fetch_share": 0,
            "_fetch_total": 1,
            "_sort": "file_type:asc,updated_at:desc",
        }),
        timeout=30,
    )
    data = _check(response.json(), "获取分享文件列表")
    return data.get("list") or []


def api_save_files(
    client: httpx.Client,
    cookie: str,
    pwd_id: str,
    stoken: str,
    fid_list: List[str],
    fid_token_list: List[str],
    to_pdir_fid: str = "0",
) -> str:
    response = client.post(
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
    data = _check(response.json(), "发起转存")
    task_id = data.get("task_id")
    if not task_id:
        raise QuarkError("转存返回无 task_id")
    return task_id


def api_wait_task(client: httpx.Client, cookie: str, task_id: str, timeout: int = 60) -> Dict[str, Any]:
    """轮询等待任务完成"""
    start = time.time()
    retry_index = 0
    while time.time() - start < timeout:
        response = client.get(
            "https://drive-pc.quark.cn/1/clouddrive/task",
            headers=make_headers(cookie),
            params=make_params({"task_id": task_id, "retry_index": retry_index}),
            timeout=30,
        )
        task_data = _check(response.json(), "任务轮询")
        status = task_data.get("status")

        if status == 2:
            return task_data
        if status == 4:
            raise QuarkError("任务失败")

        retry_index += 1
        time.sleep(0.8)

    raise QuarkError("等待任务超时")


def api_list_items(client: httpx.Client, cookie: str, pdir_fid: str = "0") -> List[Dict[str, Any]]:
    response = client.get(
        "https://drive-pc.quark.cn/1/clouddrive/file/sort",
        headers=make_headers(cookie),
        params=make_params({
            "pdir_fid": pdir_fid,
            "_page": 1,
            "_size": 100,
            "_fetch_total": 0,
            "_fetch_sub_dirs": 0,
            "_sort": "file_type:asc,updated_at:desc",
        }),
        timeout=30,
    )
    data = _check(response.json(), "获取文件夹内容")
    return data.get("list") or []


def find_folder_fid(client: httpx.Client, cookie: str, folder_name: str) -> Optional[str]:
    for item in api_list_items(client, cookie, "0"):
        if item.get("file_type") == 0 and item.get("file_name") == folder_name:
            return item.get("fid")
    return None


def find_saved_fids(items: List[Dict[str, Any]], file_names: List[str]) -> List[str]:
    saved_fid_list: List[str] = []
    for file_name in file_names:
        for item in items:
            if item.get("file_name") == file_name:
                item_fid = item.get("fid")
                if item_fid:
                    saved_fid_list.append(item_fid)
                break
    return saved_fid_list


def _random_passcode(length: int = 4) -> str:
    """生成随机提取码"""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choices(chars, k=length))


def api_create_share(
    client: httpx.Client,
    cookie: str,
    fid_list: List[str],
    title: str = "",
    expired_type: int = 1,
    use_passcode: bool = True,
) -> Dict[str, Any]:
    """创建分享链接"""
    passcode = _random_passcode() if use_passcode else ""
    url_type = 2 if passcode else 1
    
    payload: Dict[str, Any] = {
        "fid_list": fid_list,
        "title": title,
        "url_type": url_type,
        "expired_type": expired_type,
    }
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
    data["_passcode"] = passcode
    return data


def api_get_share_url(client: httpx.Client, cookie: str, share_id: str) -> str:
    """获取分享链接"""
    r = client.post(
        "https://drive-pc.quark.cn/1/clouddrive/share/password",
        headers=make_headers(cookie),
        params=make_params(),
        json={"share_id": share_id},
        timeout=30,
    )
    data = _check(r.json(), "获取分享链接")
    return data.get("share_url", "")


# ============ 核心流程 ============
def process_share(
    share_url: str,
    cookie: Optional[str] = None,
    cookie_file: Optional[Path] = None,
    save_to: str = "0",
    to_folder: Optional[str] = None,
    title: Optional[str] = None,
    desc: Optional[str] = None,
    style: str = "urgent",
) -> Dict[str, Any]:
    """完整流程：转存 → 创建分享 → 生成文案"""
    result = {
        "success": False,
        "original_url": share_url,
        "new_share_url": "",
        "passcode": "",
        "title": "",
        "files": [],
        "copies": [],
        "error": "",
    }
    
    if cookie and cookie.strip():
        cookie = cookie.strip()
    elif cookie_file is not None:
        if not cookie_file.exists():
            result["error"] = f"Cookie 文件不存在: {cookie_file}"
            return result
        cookie = load_cookie_from_file(cookie_file)
    else:
        cookie = ""

    if not cookie:
        result["error"] = "未提供 cookie，请通过 --cookie 或 --cookie-file 传入登录态"
        return result

    ensure_httpx()

    with httpx.Client() as client:
        try:
            print(f"🚀 开始处理: {share_url}\n")

            print("🔑 验证登录状态...")
            if not api_check_login(client, cookie):
                result["error"] = "cookie 无效或已过期，请重新从夸克网盘浏览器中获取 cookie"
                return result

            target_folder_fid = save_to
            if to_folder:
                print(f"📁 查找目标文件夹: {to_folder}...")
                folder_fid = find_folder_fid(client, cookie, to_folder)
                if not folder_fid:
                    result["error"] = f"网盘中未找到文件夹 '{to_folder}'，请先在网盘中创建该文件夹"
                    return result
                target_folder_fid = folder_fid
                print(f"   ✅ 找到文件夹，fid={target_folder_fid}\n")

            pwd_id = extract_pwd_id(share_url)

            # Step 1: 获取分享详情
            print("📥 步骤 1/3: 解析分享内容...")
            stoken = api_get_stoken(client, cookie, pwd_id)
            file_list = api_list_share_files(client, cookie, pwd_id, stoken)

            if not file_list:
                result["error"] = "分享为空或已失效"
                return result

            share_fid_list = [f["fid"] for f in file_list]
            fid_token_list = [f["share_fid_token"] for f in file_list]
            file_names = [f["file_name"] for f in file_list]
            result["files"] = file_names

            if not title:
                title = file_names[0] if len(file_names) == 1 else f"{file_names[0]} 等 {len(file_names)} 个文件"

            print(f"   分享标题: {title}")
            print(f"   文件数量: {len(file_list)}\n")

            # Step 2: 转存
            print("📥 步骤 2/3: 转存资源...")
            task_id = api_save_files(
                client, cookie, pwd_id, stoken, share_fid_list, fid_token_list, target_folder_fid
            )
            print("   等待转存完成...")
            api_wait_task(client, cookie, task_id)

            print(f"   ✅ 转存成功: {title}\n")

            # Step 3: 创建分享
            print("📤 步骤 3/3: 创建分享...")
            saved_items = api_list_items(client, cookie, target_folder_fid)
            saved_fid_list = find_saved_fids(saved_items, file_names)
            if not saved_fid_list:
                result["error"] = "创建分享失败：转存后未找到文件ID"
                return result

            share_title = file_names[0] if len(file_names) == 1 else f"{file_names[0]} 等 {len(file_names)} 个文件"
            share_data = api_create_share(client, cookie, saved_fid_list, title=share_title)

            share_task_id = share_data.get("task_id")
            if share_task_id:
                print(f"   等待分享创建完成...")
                share_task_result = api_wait_task(client, cookie, share_task_id)
                new_share_id = share_task_result.get("share_id")
            else:
                new_share_id = share_data.get("share_id")
            
            if not new_share_id:
                result["error"] = "创建分享失败：未获取到分享ID"
                return result
            
            new_share_url = api_get_share_url(client, cookie, new_share_id)
            passcode = share_data.get("_passcode", "")
            
            print(f"   ✅ 分享创建成功")
            print(f"   链接: {new_share_url}")
            if passcode:
                print(f"   提取码: {passcode}\n")
            else:
                print()
            
            result["new_share_url"] = new_share_url
            result["passcode"] = passcode
            result["title"] = title

            # Step 4: 生成文案
            print("📝 生成 Twitter 文案...\n")
            copies = generate_copies(title, desc or "", new_share_url, style)
            result["copies"] = copies
            result["success"] = True

        except (ValueError, QuarkError, QuarkAuthError) as e:
            result["error"] = str(e)
        except Exception as e:
            result["error"] = str(e)
    
    return result


def generate_copies(title: str, desc: str, link: str, style: str) -> List[Dict[str, Any]]:
    """生成多个版本的文案"""
    style_config = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["urgent"])
    templates = style_config["templates"]
    
    copies = []
    for i, template in enumerate(templates):
        text = template.format(
            title=title.strip(),
            desc=desc.strip(),
            link=link.strip(),
        )
        copies.append({
            "version": i + 1,
            "text": text,
            "length": len(text),
            "within_limit": len(text) <= 280,
        })
    
    return copies


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(
        description="夸克转存 + Twitter 文案一键流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxx" --title "资源标题" --desc "资源描述"
  python quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxx" --style value
  python quark_twitter_pipeline.py styles
""",
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    p_run = subparsers.add_parser("run", help="执行完整流程")
    p_run.add_argument("link", help="夸克分享链接")
    p_run.add_argument("--title", "-t", default=None, help="资源标题")
    p_run.add_argument("--desc", "-d", default="", help="资源描述")
    p_run.add_argument("--style", "-s", default="urgent",
                       choices=list(STYLE_TEMPLATES.keys()),
                       help="文案风格（默认: urgent）")
    p_run.add_argument("--cookie", help="直接传入 cookie 字符串")
    p_run.add_argument("--save-to", default="0", help="转存目标文件夹ID")
    p_run.add_argument("--to-folder", help="按文件夹名称查找目标目录（优先于 --save-to）")
    p_run.add_argument("--cookie-file", default=str(DEFAULT_COOKIE_FILE), help="cookie 文件路径")
    
    p_styles = subparsers.add_parser("styles", help="查看支持的文案风格")
    
    args = parser.parse_args()
    
    if args.command == "styles":
        print("支持的文案风格：\n")
        for key, val in STYLE_TEMPLATES.items():
            marker = " (默认)" if key == "urgent" else ""
            print(f"  {key:12} - {val['name']}{marker}")
        print("\n推荐使用 urgent（紧迫稀缺）或 value（价值强调）")
        return
    
    if args.command == "run":
        result = process_share(
            share_url=args.link,
            cookie=args.cookie,
            cookie_file=Path(args.cookie_file),
            save_to=args.save_to,
            to_folder=args.to_folder,
            title=args.title,
            desc=args.desc,
            style=args.style,
        )
        
        if not result["success"]:
            print(f"❌ 处理失败: {result['error']}")
            sys.exit(1)
        
        print("=" * 50)
        print("📋 Twitter 文案（复制使用）：\n")
        
        for copy in result["copies"]:
            status = "✅" if copy["within_limit"] else "⚠️ 超出限制"
            print(f"--- 版本 {copy['version']} [{copy['length']}字] {status} ---")
            print(copy["text"])
            print()
        
        print("=" * 50)
        print("✅ 全部完成！直接复制上方文案发布到 Twitter")


if __name__ == "__main__":
    main()
