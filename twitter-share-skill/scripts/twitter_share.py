#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter 资源分享文案生成工具

功能：
  1. 根据资源标题、描述生成 Twitter 分享文案（模式1）
  2. 对现有文案进行二创改写（模式2）

用法：
  python twitter_share.py generate --title "资源标题" --desc "资源描述" --link "分享链接"
  python twitter_share.py rewrite --text "原始文案" [--style "风格"]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============ 配置管理 ============
def get_config_dir() -> Path:
    """获取配置目录"""
    config_dir = Path.home() / ".config" / "twitter-share-skill"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """获取配置文件路径"""
    return get_config_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    """加载配置"""
    config_path = get_config_path()
    if not config_path.exists():
        return {
            "default_style": "urgent",
            "include_emoji": True,
            "include_hashtags": False,
            "max_length": 280,
        }
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "default_style": "urgent",
            "include_emoji": True,
            "include_hashtags": False,
            "max_length": 280,
        }


def save_config(config: Dict[str, Any]) -> None:
    """保存配置"""
    config_path = get_config_path()
    # 强制关闭 hashtag
    config["include_hashtags"] = False
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============ 文案生成模板 ============
# 特色：制造稀缺感和紧迫感，让人忍不住转存
STYLE_TEMPLATES = {
    "casual": {
        "name": "轻松随意",
        "templates": [
            "刚刷到的好东西 👇\n\n{title}\n{desc}\n\n{link}\n\n看到就是赚到，存了再说",
            "今日份收获 ✨\n\n{title}\n{desc}\n\n{link}\n\n不存后悔系列",
            "这个有点东西\n\n{title}\n{desc}\n\n{link}\n\n先存为敬",
        ],
        "hashtags": [],
    },
    "professional": {
        "name": "专业简洁",
        "templates": [
            "【精选资源】{title}\n\n{desc}\n\n{link}\n\n建议收藏",
            "{title}\n\n{desc}\n\n→ {link}\n\n值得保存",
        ],
        "hashtags": [],
    },
    "hype": {
        "name": "热情 hype",
        "templates": [
            "🔥 手慢无！这个必须存\n\n{title}\n{desc}\n\n{link}\n\n看到就是赚到，速存！",
            "💎 挖到宝了！\n\n{title}\n{desc}\n\n{link}\n\n不存后悔系列，先存为敬",
            "😱 不允许还有人没存这个！\n\n{title}\n{desc}\n\n{link}\n\n存了=赚了",
        ],
        "hashtags": [],
    },
    "minimal": {
        "name": "极简冷淡",
        "templates": [
            "{title}\n\n{link}",
            "{title}｜{desc}\n\n{link}",
        ],
        "hashtags": [],
    },
    "urgent": {
        "name": "紧迫稀缺",
        "templates": [
            "⚠️ 限时资源，随时可能失效\n\n{title}\n{desc}\n\n{link}\n\n看到就存，别等没了再后悔",
            "🚨 稀缺资源预警\n\n{title}\n{desc}\n\n{link}\n\n这种好东西不常有，速存",
            "⏰ 最后机会\n\n{title}\n{desc}\n\n{link}\n\n存了就是自己的，手慢无",
        ],
        "hashtags": [],
    },
    "value": {
        "name": "价值强调",
        "templates": [
            "💰 这份资源值多少钱，懂的人都懂\n\n{title}\n{desc}\n\n{link}\n\n免费的就是最贵的，先存为敬",
            "🎯 花了不少时间整理的干货\n\n{title}\n{desc}\n\n{link}\n\n存了慢慢看，绝对值",
            "📦 一次性打包带走\n\n{title}\n{desc}\n\n{link}\n\n这种合集不常有，建议收藏",
        ],
        "hashtags": [],
    },
}


# ============ 二创改写策略 ============
REWRITE_STRATEGIES = {
    "casual": {
        "name": "轻松随意",
        "transforms": [
            "保持原意，用更口语化的方式表达",
            "加入一些日常用语和语气词",
            "让文案读起来像朋友聊天",
        ],
    },
    "professional": {
        "name": "专业简洁",
        "transforms": [
            "去除口语化表达，改为书面语",
            "结构更清晰，信息更紧凑",
            "适合正式场合发布",
        ],
    },
    "hype": {
        "name": "热情 hype",
        "transforms": [
            "增加情绪词和强调符号",
            "制造紧迫感和期待感",
            "让文案更有感染力",
        ],
    },
    "story": {
        "name": "故事化",
        "transforms": [
            "加入个人使用体验或场景描述",
            "用第一人称讲述发现过程",
            "增加情感共鸣点",
        ],
    },
}


# ============ 核心功能 ============
def generate_from_resource(
    title: str,
    description: str = "",
    link: str = "",
    style: str = "casual",
    include_emoji: bool = True,
    include_hashtags: bool = True,
    max_length: int = 280,
) -> Dict[str, Any]:
    """
    根据资源信息生成 Twitter 分享文案
    
    返回包含多个版本文案的字典
    """
    result = {
        "title": title,
        "description": description,
        "link": link,
        "style": style,
        "copies": [],
    }
    
    style_config = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["casual"])
    templates = style_config["templates"]
    hashtags = style_config["hashtags"] if include_hashtags else []
    
    # 处理描述文本
    desc = description.strip() if description else ""
    
    # 生成多个版本
    for i, template in enumerate(templates):
        # 填充模板
        text = template.format(
            title=title.strip(),
            desc=desc,
            link=link.strip() if link else "",
        )
        
        # 添加 hashtag
        if hashtags and include_hashtags:
            hashtag_str = " ".join(hashtags[:3])  # 最多3个标签
            text = text + "\n\n" + hashtag_str
        
        # 如果不使用 emoji，移除常见 emoji
        if not include_emoji:
            text = remove_emoji(text)
        
        # 检查长度
        length_ok = len(text) <= max_length
        
        result["copies"].append({
            "version": i + 1,
            "text": text,
            "length": len(text),
            "within_limit": length_ok,
        })
    
    return result


def rewrite_copy(
    original_text: str,
    style: str = "casual",
    include_emoji: bool = True,
    max_length: int = 280,
) -> Dict[str, Any]:
    """
    对现有文案进行二创改写
    
    返回改写后的文案字典
    """
    result = {
        "original": original_text,
        "style": style,
        "rewrites": [],
    }
    
    style_config = REWRITE_STRATEGIES.get(style, REWRITE_STRATEGIES["casual"])
    
    # 基于不同策略生成改写版本
    strategies = [
        ("口语化改写", "将原文案改写成更口语化、更自然的表达"),
        ("精简版", "保留核心信息，去除冗余描述，更简洁"),
        ("强调版", "突出资源价值，增加吸引力和点击欲望"),
    ]
    
    for i, (name, desc) in enumerate(strategies):
        # 这里使用简单的文本变换作为示例
        # 实际使用时可以接入 AI API 进行更智能的改写
        rewritten = apply_rewrite_strategy(original_text, name, style)
        
        if not include_emoji:
            rewritten = remove_emoji(rewritten)
        
        length_ok = len(rewritten) <= max_length
        
        result["rewrites"].append({
            "version": i + 1,
            "strategy": name,
            "description": desc,
            "text": rewritten,
            "length": len(rewritten),
            "within_limit": length_ok,
        })
    
    return result


def apply_rewrite_strategy(text: str, strategy: str, style: str) -> str:
    """应用改写策略（简化版，实际可接入 AI）"""
    # 这里提供基础改写逻辑，作为示例
    # 实际使用时建议接入 DeepSeek/OpenAI 等 API
    
    if strategy == "口语化改写":
        # 简单的口语化转换
        replacements = [
            ("【", ""),
            ("】", " "),
            ("推荐", "安利"),
            ("资源", "好东西"),
            ("分享", "给大家"),
        ]
        result = text
        for old, new in replacements:
            result = result.replace(old, new)
        return result + " 👀"
    
    elif strategy == "精简版":
        # 提取关键信息，简化表达
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) >= 2:
            return f"{lines[0]}\n\n{lines[-1]}"
        return text
    
    elif strategy == "强调版":
        # 增加强调元素
        return f"🔥 {text}\n\n速存！"
    
    return text


def remove_emoji(text: str) -> str:
    """移除文本中的 emoji"""
    import re
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r"", text)


# ============ CLI ============
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Twitter 资源分享文案生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 模式1：根据资源信息生成文案
  python twitter_share.py generate --title "黑袍纠察队 第五季" --desc "4K多版本，更新至第3集" --link "https://pan.quark.cn/s/xxx"

  # 模式2：二创改写现有文案
  python twitter_share.py rewrite --text "【资源分享】黑袍纠察队第五季..."

  # 指定风格
  python twitter_share.py generate --title "xxx" --style hype
  python twitter_share.py rewrite --text "xxx" --style story

  # 查看支持的风格
  python twitter_share.py styles
""",
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # generate 子命令
    p_gen = subparsers.add_parser("generate", help="根据资源信息生成文案")
    p_gen.add_argument("--title", "-t", required=True, help="资源标题")
    p_gen.add_argument("--desc", "-d", default="", help="资源描述（可选）")
    p_gen.add_argument("--link", "-l", default="", help="分享链接（可选）")
    p_gen.add_argument("--style", "-s", default="urgent", 
                       choices=list(STYLE_TEMPLATES.keys()),
                       help="文案风格（默认: urgent）")
    p_gen.add_argument("--no-emoji", action="store_true", help="不使用 emoji")
    p_gen.add_argument("--no-hashtags", action="store_true", help="不添加 hashtag")
    p_gen.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    
    # rewrite 子命令
    p_rewrite = subparsers.add_parser("rewrite", help="二创改写现有文案")
    p_rewrite.add_argument("--text", "-t", required=True, help="原始文案")
    p_rewrite.add_argument("--style", "-s", default="casual",
                           choices=list(REWRITE_STRATEGIES.keys()),
                           help="改写风格（默认: casual）")
    p_rewrite.add_argument("--no-emoji", action="store_true", help="不使用 emoji")
    p_rewrite.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    
    # styles 子命令
    p_styles = subparsers.add_parser("styles", help="查看支持的文案风格")
    
    # config 子命令
    p_config = subparsers.add_parser("config", help="配置默认设置")
    p_config.add_argument("--default-style", help="设置默认文案风格")
    p_config.add_argument("--no-emoji", action="store_true", help="默认不使用 emoji")
    p_config.add_argument("--emoji", action="store_true", help="默认使用 emoji")
    
    args = parser.parse_args()
    config = load_config()
    
    if args.command == "styles":
        print("支持的文案风格：\n")
        print("【生成模式】")
        for key, val in STYLE_TEMPLATES.items():
            print(f"  {key:12} - {val['name']}")
        print("\n【二创模式】")
        for key, val in REWRITE_STRATEGIES.items():
            print(f"  {key:12} - {val['name']}")
        return
    
    if args.command == "config":
        if hasattr(args, "default_style") and args.default_style:
            config["default_style"] = args.default_style
            print(f"✅ 已设置默认风格: {args.default_style}")
        
        if hasattr(args, "emoji") and args.emoji:
            config["include_emoji"] = True
            print("✅ 已设置默认使用 emoji")
        elif hasattr(args, "no_emoji") and args.no_emoji:
            config["include_emoji"] = False
            print("✅ 已设置默认不使用 emoji")
        
        save_config(config)
        
        # 显示当前配置
        print(f"\n当前配置:")
        print(f"  默认风格: {config.get('default_style', 'urgent')}")
        print(f"  使用 emoji: {config.get('include_emoji', True)}")
        print(f"  使用 hashtag: 已关闭")
        return
    
    if args.command == "generate":
        result = generate_from_resource(
            title=args.title,
            description=args.desc,
            link=args.link,
            style=args.style,
            include_emoji=not args.no_emoji,
            include_hashtags=not args.no_hashtags,
        )
        
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"📝 生成文案（风格: {STYLE_TEMPLATES[args.style]['name']}）\n")
            for copy in result["copies"]:
                status = "✅" if copy["within_limit"] else "⚠️ 超出限制"
                print(f"--- 版本 {copy['version']} [{copy['length']}字] {status} ---")
                print(copy["text"])
                print()
    
    elif args.command == "rewrite":
        result = rewrite_copy(
            original_text=args.text,
            style=args.style,
            include_emoji=not args.no_emoji,
        )
        
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"🔄 二创改写（风格: {REWRITE_STRATEGIES[args.style]['name']}）\n")
            print(f"【原文案】")
            print(result["original"])
            print()
            for rewrite in result["rewrites"]:
                status = "✅" if rewrite["within_limit"] else "⚠️ 超出限制"
                print(f"--- {rewrite['strategy']} [{rewrite['length']}字] {status} ---")
                print(rewrite["text"])
                print()


if __name__ == "__main__":
    main()
