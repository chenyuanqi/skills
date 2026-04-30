#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
夸克转存 + Twitter 文案一键流水线 v2.2

功能：看到夸克分享链接 → 转存到自己网盘 → 创建新分享 → 生成专业 Twitter 文案（含标签+配图建议）
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

# ============ 专业文案生成器 ============

class TwitterCopyGenerator:
    """Twitter运营专家级文案生成器"""

    # Hook库：开场白模板
    HOOKS = [
        "你们催更的{topic}终于来了",
        "压箱底的{topic}，今天免费送",
        "很多人都在找的{topic}，我搞到了",
        "这套{topic}，圈内人都在用",
        "最近爆火的{topic}，手慢无",
        "从业{years}年，第一次分享这个",
        "这可能是我见过最全的{topic}",
        "价值{price}的{topic}，今天限时免费",
        "后台一直有人问的{topic}，安排",
        "错过真的会后悔的{topic}",
    ]

    # 价值点描述库
    VALUE_TEMPLATES = [
        "涵盖{level}到进阶的完整学习路径",
        "包含{count}+实际案例解析",
        "附赠完整工具包和模板",
        "行业大牛实战经验总结",
        "经过{verify}验证有效的方法",
        "覆盖核心知识点和实操技巧",
        "从0到1的完整教程",
        "包含视频+文档+工具包",
    ]

    # CTA行动号召库
    CTAS = [
        "看完记得收藏，随时用到随时翻",
        "想要跟上这波红利，现在就是最好的时机",
        "评论区扣666，我发你完整版",
        "赶紧存下来，慢慢研究",
        "建议先收藏，需要的时候不迷路",
        "错过这村就没这店了",
        "懂的都懂，先保存再说",
        "手慢无，抓紧存",
    ]

    # Emoji表情库
    EMOJIS = {
        "tech": ["🚀", "💻", "⚡", "🔧", "📱", "🎯", "💡", "🔑"],
        "money": ["💰", "💵", "💎", "🏆", "📈", "🎁", "⭐", "🔥"],
        "alert": ["⚠️", "🚨", "⏰", "📢", "🔔", "❗", "💥", "⚡"],
        "learning": ["📚", "📝", "🎓", "💪", "✨", "🧠", "📖", "🎯"],
    }

    def __init__(self, title: str, link: str, topic: str = "", benefit: str = "", cta: str = "", opinion: str = "", tags: str = ""):
        self.title = title
        self.link = link
        self.topic = topic or self._extract_topic(title)
        self.benefit = benefit
        self.cta = cta
        self.opinion = opinion
        self.custom_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    def _extract_topic(self, title: str) -> str:
        """从标题中提取主题"""
        # 去除常见后缀词
        title = re.sub(r'[（\(].*?[）\)]', '', title)
        title = re.sub(r'【.*?】', '', title)
        title = re.sub(r'教程|教学|课程|攻略|资料|合集|礼包|大全|指南', '', title)
        return title.strip()[:20] or "这份资源"

    # ============ 标签生成 ============
    # 关键词 → 标签映射（基于运营实践）
    TAG_KEYWORD_MAP = {
        # 工具/AI类
        "AI": ["#AI工具", "#效率工具"],
        "ChatGPT": ["#ChatGPT", "#AI工具"],
        "GPT": ["#ChatGPT", "#AI工具"],
        "Claude": ["#Claude", "#AI工具"],
        "DeepSeek": ["#DeepSeek", "#AI工具"],
        "人工智能": ["#AI工具"],
        "工具": ["#效率工具", "#资源分享"],
        "软件": ["#效率工具", "#资源分享"],
        # 学习/教育类
        "课程": ["#自学", "#干货"],
        "教程": ["#自学", "#干货"],
        "读书": ["#读书", "#自我提升"],
        "写作": ["#写作", "#自我提升"],
        "文学": ["#读书", "#写作"],
        "英语": ["#自学", "#英语"],
        "摄影": ["#摄影", "#自学"],
        "记忆": ["#学习方法", "#自我提升"],
        "笔记": ["#学习方法", "#效率工具"],
        # 职业/副业类
        "简历": ["#求职", "#职场"],
        "面试": ["#求职", "#职场"],
        "副业": ["#副业", "#搞钱"],
        "赚钱": ["#副业", "#搞钱"],
        "摆摊": ["#副业", "#搞钱"],
        "创业": ["#副业", "#搞钱"],
        "职场": ["#职场", "#自我提升"],
        # 资源/网盘类
        "电子书": ["#电子书", "#资源分享"],
        "网盘": ["#网盘", "#数字生活"],
        "资源": ["#资源分享", "#干货"],
        "资料": ["#资源分享", "#干货"],
        "模板": ["#效率工具", "#资源分享"],
        # 生活/其他
        "避坑": ["#避坑指南", "#经验分享"],
        "省钱": ["#省钱攻略", "#生活技巧"],
        "效率": ["#效率工具", "#自我提升"],
    }

    # 默认标签池（当无法从关键词匹配时使用）
    DEFAULT_TAGS = ["#资源分享", "#效率工具", "#干货"]

    def generate_tags(self) -> List[str]:
        """根据资源标题自动生成2-3个相关标签"""
        if self.custom_tags:
            # 用户自定义标签，加上 # 前缀
            result = []
            for t in self.custom_tags[:3]:
                if not t.startswith("#"):
                    t = "#" + t
                result.append(t)
            return result

        title_lower = self.title.lower()
        matched_tags = []
        seen_tags = set()

        # 按优先级匹配关键词
        for keyword, tags in self.TAG_KEYWORD_MAP.items():
            if keyword.lower() in title_lower:
                for tag in tags:
                    if tag not in seen_tags:
                        matched_tags.append(tag)
                        seen_tags.add(tag)

        if len(matched_tags) >= 2:
            return matched_tags[:3]
        elif len(matched_tags) == 1:
            return matched_tags + [self.DEFAULT_TAGS[0]]
        else:
            return self.DEFAULT_TAGS[:2]

    def get_image_suggestion(self) -> str:
        """根据资源类型给出配图建议"""
        title_lower = self.title.lower()

        suggestions = {
            "课程": "📷 配图建议：截图课程目录页，展示课程章节结构，让人一眼看到内容丰富度",
            "视频": "📷 配图建议：用视频播放器截图，展示视频时长和画质，或截取最吸引人的画面",
            "电子书": "📷 配图建议：拍一张电子书封面/目录的截图，或者用阅读器界面展示",
            "教程": "📷 配图建议：截图教程的核心步骤或成果展示，让人看到学完能做出什么",
            "工具": "📷 配图建议：软件界面截图，展示核心功能和操作效果",
            "模板": "📷 配图建议：模板预览截图，展示模板样式和质量",
            "资料": "📷 配图建议：文件列表截图，展示资料的完整性和分类",
            "AI": "📷 配图建议：AI生成效果的对比图（前后对比最有说服力）",
        }

        for keyword, suggestion in suggestions.items():
            if keyword in title_lower:
                return suggestion

        return "📷 配图建议：资源封面截图或文件列表截图，确保图片清晰且能看出是什么内容"

    def format_with_tags(self, text: str) -> str:
        """在文案末尾追加标签"""
        tags = self.generate_tags()
        tags_line = "\n" + " ".join(tags)
        # 避免重复追加标签
        if any(tag in text for tag in tags):
            return text
        return text.rstrip() + tags_line

    def _pick_random(self, items: List[str]) -> str:
        return random.choice(items)

    def _get_emojis(self, category: str = "tech") -> str:
        emojis = self.EMOJIS.get(category, self.EMOJIS["tech"])
        return self._pick_random(emojis)

    def _build_value(self) -> str:
        """构建价值描述"""
        if self.benefit:
            return self.benefit

        values = []
        # 随机选择2-3个价值模板
        templates = random.sample(self.VALUE_TEMPLATES, min(2, len(self.VALUE_TEMPLATES)))
        for t in templates:
            t = t.replace("{level}", self._pick_random(["入门", "初级", "中级", "高级", "小白", "新手"]))
            t = t.replace("{count}", str(random.randint(10, 100)))
            t = t.replace("{verify}", self._pick_random(["1000+学员", "实战", "多年", "百万用户"]))
            values.append(t)

        return "，".join(values)

    def generate_urgent_copy(self) -> str:
        """紧迫感文案"""
        emoji = self._get_emojis("alert")
        hook = self._pick_random(self.HOOKS).format(
            topic=self.topic,
            years=random.randint(3, 10),
            price=f"{random.randint(99, 999)}元"
        )
        value = self._build_value()
        cta = self.cta or self._pick_random(self.CTAS)

        return f"""{emoji} {hook}

📦 {self.title}

{value}

🔗 {self.link}

{cta}"""

    def generate_value_copy(self) -> str:
        """价值强调文案"""
        emoji = self._get_emojis("money")
        hook = self._pick_random([
            "这份{topic}，真的值这个价",
            "整理了{time}才出来的{topic}",
            "圈内认可的{topic}，今天分享给大家",
            "做了{years}年运营，这是我的私藏",
            "很多人用了都说好的{topic}",
        ]).format(
            topic=self.topic,
            time=self._pick_random(["三天", "一周", "一个月", "三个月"]),
            years=random.randint(2, 8)
        )
        value = self._build_value()
        cta = self.cta or "觉得有用就转发给需要的朋友"

        return f"""{emoji} {hook}

💎 {self.title}

{value}

👉 {self.link}

{cta}"""

    def generate_hype_copy(self) -> str:
        """热度爆发文案"""
        emoji = self._get_emojis("alert")
        hook = self._pick_random([
            "我不允许你们没有这份{topic}！",
            "熬夜整理的{topic}，必须让你们看到",
            "压箱底的{topic}，今天拿出来了",
            "终于！{topic}来了！",
            "这波{topic}，错过血亏",
        ]).format(topic=self.topic)
        value = self._build_value()
        cta = self.cta or "先存再看，万一找不到了呢"

        return f"""{emoji} {hook}

🔥 {self.title}

{value}

{self.link}

{cta}"""

    def generate_pro_copy(self) -> str:
        """专业简洁文案"""
        emoji = self._get_emojis("learning")
        hook = self._pick_random([
            "【{topic}分享】",
            "{topic}｜运营人必备",
            "效率提升 | {topic}",
            "私藏{topic}，建议收藏",
        ]).format(topic=self.topic)
        value = self._build_value()

        return f"""{emoji} {hook}

📋 {self.title}

{value}

🔗 {self.link}

收藏备用"""

    def generate_story_copy(self) -> str:
        """故事型文案"""
        emoji = self._get_emojis("tech")
        story = self._pick_random([
            "之前有个粉丝问我，有没有好的{topic}",
            "我做运营这么多年，踩过很多坑",
            "这份{topic}是我花了{time}才整理好的",
            "上周发了{topic}，反响太好了",
            "很多人说想要一份完整的{topic}",
        ]).format(
            topic=self.topic,
            time=self._pick_random(["一周", "两周", "一个月"])
        )
        value = self._build_value()
        cta = self.cta or "需要的朋友直接保存"

        return f"""{emoji} {story}

📦 资源：{self.title}

{value}

🔗 {self.link}

{cta}"""

    def generate_ip_copy(self) -> str:
        """个人IP风格文案：资源 + 个人见解/使用体验"""
        if not self.opinion:
            # 如果没有个人见解，使用带引导的默认版本
            return f"""📦 {self.title}

{self._build_value()}

🔗 {self.link}

💬 用了感觉不错，评论区说说你的看法"""

        emoji = self._get_emojis("learning")

        # 个人见解开场
        openings = [
            "用了{time}，说说真实感受：",
            "花{time}看完这份，真实评价：",
            "这份资源我用了有一阵子了，聊聊感受：",
            "刚看完/用完，来说说我的看法：",
        ]
        opening = self._pick_random(openings).format(
            time=self._pick_random(["了一周", "了三天", "了半个月", "有一段时间"])
        )

        # 结尾引导互动
        cta = self.cta or self._pick_random([
            "你们有用过类似的吗？评论区交流一下",
            "觉得有用的转给需要的朋友",
            "先存着，以后肯定用得上",
            "觉得不错的点个赞让我知道",
        ])

        return f"""{emoji} {opening}

📦 {self.title}

{self.opinion}

🔗 {self.link}

{cta}"""

    def generate_all(self) -> List[Dict[str, Any]]:
        """生成所有版本的文案（含标签+配图建议）"""
        copies = []
        tags = self.generate_tags()
        image_suggestion = self.get_image_suggestion()

        generators = [
            ("热度爆发", self.generate_hype_copy),
            ("专业简洁", self.generate_pro_copy),
            ("故事型", self.generate_story_copy),
            ("个人IP", self.generate_ip_copy),
        ]

        for i, (name, func) in enumerate(generators):
            text = func()
            text = self.format_with_tags(text)
            copies.append({
                "version": i + 1,
                "style": name,
                "text": text,
                "length": len(text),
                "within_limit": len(text) <= 280,
                "tags": tags,
                "image_suggestion": image_suggestion,
            })

        return copies


def generate_copies(title: str, desc: str, link: str, style: str = "auto", opinion: str = "", tags: str = "") -> List[Dict[str, Any]]:
    """生成多个版本的文案（兼容原接口，含标签+配图建议）"""
    generator = TwitterCopyGenerator(
        title=title,
        link=link,
        topic="",  # 自动从标题提取
        benefit=desc,
        opinion=opinion,
        tags=tags,
    )

    all_tags = generator.generate_tags()
    image_suggestion = generator.get_image_suggestion()

    if style == "auto":
        return generator.generate_all()
    elif style == "urgent":
        text = generator.format_with_tags(generator.generate_urgent_copy())
        return [{"version": 1, "style": "紧迫稀缺", "text": text, "length": len(text),
                 "within_limit": True, "tags": all_tags, "image_suggestion": image_suggestion}]
    elif style == "value":
        text = generator.format_with_tags(generator.generate_value_copy())
        return [{"version": 1, "style": "价值强调", "text": text, "length": len(text),
                 "within_limit": True, "tags": all_tags, "image_suggestion": image_suggestion}]
    elif style == "hype":
        text = generator.format_with_tags(generator.generate_hype_copy())
        return [{"version": 1, "style": "热度爆发", "text": text, "length": len(text),
                 "within_limit": True, "tags": all_tags, "image_suggestion": image_suggestion}]
    elif style == "professional":
        text = generator.format_with_tags(generator.generate_pro_copy())
        return [{"version": 1, "style": "专业简洁", "text": text, "length": len(text),
                 "within_limit": True, "tags": all_tags, "image_suggestion": image_suggestion}]
    elif style == "story":
        text = generator.format_with_tags(generator.generate_story_copy())
        return [{"version": 1, "style": "故事型", "text": text, "length": len(text),
                 "within_limit": True, "tags": all_tags, "image_suggestion": image_suggestion}]
    elif style == "ip":
        text = generator.format_with_tags(generator.generate_ip_copy())
        return [{"version": 1, "style": "个人IP", "text": text, "length": len(text),
                 "within_limit": True, "tags": all_tags, "image_suggestion": image_suggestion}]
    else:
        return generator.generate_all()


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
    use_passcode: bool = False,
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
    opinion: str = "",
    style: str = "auto",
    tags: str = "",
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
            copies = generate_copies(title, desc or "", new_share_url, style, opinion, tags)
            result["copies"] = copies
            result["success"] = True

        except (ValueError, QuarkError, QuarkAuthError) as e:
            result["error"] = str(e)
        except Exception as e:
            result["error"] = str(e)

    return result


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(
        description="夸克转存 + Twitter 文案一键流水线 v2.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
文案风格说明：
  auto          - 自动生成4种风格版本（默认，含标签+配图建议）
  urgent        - 紧迫稀缺风格
  value         - 价值强调风格
  hype          - 热度爆发风格
  professional  - 专业简洁风格
  story         - 故事型风格
  ip            - 个人IP风格（推荐配合 --opinion 使用）

标签说明：
  --tags 可自定义标签（逗号分隔），不传则根据资源标题自动生成相关标签
  每条文案自动附带 2-3 个相关 hashtag

示例:
  python quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxx"
  python quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxx" --style ip --opinion "用了三天，真不错"
  python quark_twitter_pipeline.py run "https://pan.quark.cn/s/xxx" --tags "资源分享,AI工具"
  python quark_twitter_pipeline.py styles
""",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_run = subparsers.add_parser("run", help="执行完整流程")
    p_run.add_argument("link", help="夸克分享链接")
    p_run.add_argument("--title", "-t", default=None, help="资源标题")
    p_run.add_argument("--desc", "-d", default="", help="资源描述/价值亮点")
    p_run.add_argument("--opinion", "-o", default="", help="个人见解/使用体验（支持多行，会生成个人IP风格文案）")
    p_run.add_argument("--style", "-s", default="auto",
                       choices=["auto", "urgent", "value", "hype", "professional", "story", "ip"],
                       help="文案风格（默认: auto，生成4种）")
    p_run.add_argument("--tags", default="", help="自定义标签（逗号分隔，如 '资源分享,AI工具'），不传则自动生成")
    p_run.add_argument("--cookie", help="直接传入 cookie 字符串")
    p_run.add_argument("--save-to", default="0", help="转存目标文件夹ID")
    p_run.add_argument("--to-folder", default="pull", help="按文件夹名称查找目标目录（默认: pull）")
    p_run.add_argument("--cookie-file", default=str(DEFAULT_COOKIE_FILE), help="cookie 文件路径")

    p_styles = subparsers.add_parser("styles", help="查看支持的文案风格")

    args = parser.parse_args()

    if args.command == "styles":
        print("支持的文案风格：\n")
        styles = [
            ("auto", "自动模式", "生成4种风格版本（默认），含标签+配图建议"),
            ("urgent", "紧迫稀缺", "制造紧迫感，限时稀缺"),
            ("value", "价值强调", "突出资源价值和实用性"),
            ("hype", "热度爆发", "情绪饱满，引发转发"),
            ("professional", "专业简洁", "简洁专业，适合行业交流"),
            ("story", "故事型", "用故事引入，更有代入感"),
            ("ip", "个人IP", "资源 + 个人见解/使用体验（推荐配合 --opinion 使用）"),
        ]
        for key, name, desc in styles:
            marker = " (默认)" if key == "auto" else ""
            print(f"  {key:14} - {name}{marker}")
            print(f"                  {desc}\n")
        print("  所有风格均自动附带 2-3 个相关标签和配图建议\n")
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
            opinion=args.opinion,
            style=args.style,
            tags=args.tags,
        )

        if not result["success"]:
            print(f"❌ 处理失败: {result['error']}")
            sys.exit(1)

        print("=" * 60)
        print("📋 Twitter 文案（可直接复制使用）：\n")

        for i, copy in enumerate(result["copies"]):
            status = "✅" if copy["within_limit"] else "⚠️ 超出限制"
            style_name = copy.get('style', f"版本{copy['version']}")
            print(f"--- {style_name} [{copy['length']}字] {status} ---")
            print(copy["text"])
            # 显示标签
            if "tags" in copy and copy["tags"]:
                print(f"\n🏷️ 标签: {' '.join(copy['tags'])}")
            # 显示配图建议（只在第一个版本显示）
            if i == 0 and "image_suggestion" in copy:
                print(f"{copy['image_suggestion']}")
            print()

        print("=" * 60)
        print("✅ 全部完成！记得：①配上图片 ②选个好时间发（9-11点或20-22点）")


if __name__ == "__main__":
    main()