#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
夸克转存 + Twitter 文案一键流水线

功能：看到夸克分享链接 → 转存到自己网盘 → 创建新分享 → 生成 Twitter 文案
"""

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

# ============ 配置 ============
DEFAULT_COOKIE_FILE = Path.home() / ".quark_cookie.txt"

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
def make_headers(cookie: str) -> Dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cookie": cookie,
        "Origin": "https://pan.quark.cn",
        "Referer": "https://pan.quark.cn/",
    }


def make_params() -> Dict[str, str]:
    return {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}


def _check(res: Dict[str, Any], action: str) -> Dict[str, Any]:
    code = res.get("code")
    if code != 0:
        msg = res.get("message", "未知错误")
        raise RuntimeError(f"{action}失败: {msg} (code={code})")
    return res.get("data") or res


def api_get_share_detail(client: httpx.Client, share_url: str) -> Dict[str, Any]:
    """获取分享详情"""
    match = re.search(r"/s/([a-zA-Z0-9]+)", share_url)
    if not match:
        raise ValueError("无法从 URL 解析分享 ID")
    share_id = match.group(1)
    
    pwd_id = share_id
    stoken = ""
    if "?" in share_url:
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(share_url)
        qs = parse_qs(parsed.query)
        stoken_list = qs.get("stoken", [""])
        stoken = stoken_list[0]
    
    payload: Dict[str, Any] = {"pwd_id": pwd_id}
    if stoken:
        payload["stoken"] = stoken
    
    r = client.post(
        "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail",
        headers=make_headers(""),
        params={**make_params(), "_page": "1", "_size": "50"},
        json=payload,
        timeout=30,
    )
    return _check(r.json(), "获取分享详情")


def api_save_files(
    client: httpx.Client,
    cookie: str,
    share_fid_list: List[str],
    share_uk: str,
    share_id: str,
    to_pdir_fid: str = "0",
) -> Dict[str, Any]:
    """转存文件"""
    payload = {
        "fid_list": share_fid_list,
        "fid_tokens": [],
        "to_pdir_fid": to_pdir_fid,
        "share_uk": share_uk,
        "share_id": share_id,
        "scene": "link",
    }
    r = client.post(
        "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save",
        headers=make_headers(cookie),
        params=make_params(),
        json=payload,
        timeout=30,
    )
    return _check(r.json(), "转存")


def api_wait_task(client: httpx.Client, cookie: str, task_id: str, timeout: int = 60) -> Dict[str, Any]:
    """轮询等待任务完成"""
    start = time.time()
    while time.time() - start < timeout:
        r = client.get(
            "https://drive-pc.quark.cn/1/clouddrive/task",
            headers=make_headers(cookie),
            params={**make_params(), "task_id": task_id, "retry_index": "0"},
            timeout=30,
        )
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(f"查询任务失败: {data.get('message')}")
        
        task_data = data.get("data", {})
        status = task_data.get("status")
        
        if status == 2:
            return task_data
        elif status == 4:
            raise RuntimeError("任务失败")
        
        time.sleep(1)
    
    raise TimeoutError("等待任务超时")


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
    cookie_file: Path,
    save_to: str = "0",
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
        "copies": [],
        "error": "",
    }
    
    if not cookie_file.exists():
        result["error"] = f"Cookie 文件不存在: {cookie_file}"
        return result
    
    cookie = cookie_file.read_text().strip()
    if not cookie:
        result["error"] = "Cookie 文件为空"
        return result
    
    with httpx.Client() as client:
        try:
            print(f"🚀 开始处理: {share_url}\n")
            
            # Step 1: 获取分享详情
            print("📥 步骤 1/3: 解析分享内容...")
            share_detail = api_get_share_detail(client, share_url)
            
            share_uk = share_detail.get("uk", "")
            share_id = share_detail.get("share_id", "")
            file_list = share_detail.get("list", [])
            
            if not file_list:
                result["error"] = "分享为空或已失效"
                return result
            
            share_fid_list = [f["fid"] for f in file_list]
            file_names = [f["file_name"] for f in file_list]
            
            if not title:
                title = file_names[0] if len(file_names) == 1 else f"{file_names[0]} 等 {len(file_names)} 个文件"
            
            print(f"   分享标题: {title}")
            print(f"   文件数量: {len(file_list)}\n")
            
            # Step 2: 转存
            print("📥 步骤 2/3: 转存资源...")
            save_result = api_save_files(
                client, cookie, share_fid_list, share_uk, share_id, save_to
            )
            
            task_id = save_result.get("task_id")
            if task_id:
                print(f"   等待转存完成...")
                task_result = api_wait_task(client, cookie, task_id)
                saved_fid_list = task_result.get("save_as", {}).get("saved_fid_list", [])
            else:
                saved_fid_list = save_result.get("saved_fid_list", [])
            
            if not saved_fid_list:
                result["error"] = "转存失败：未获取到保存的文件ID"
                return result
            
            print(f"   ✅ 转存成功: {title}\n")
            
            # Step 3: 创建分享
            print("📤 步骤 3/3: 创建分享...")
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
    p_run.add_argument("--save-to", default="0", help="转存目标文件夹ID")
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
            cookie_file=Path(args.cookie_file),
            save_to=args.save_to,
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
