# -*- coding: utf-8 -*-
"""
QX-Rules · 把 QX 脚本自动"解包"成中文 .conf
==========================================

原理：这些脚本的**头部注释块里本来就写好了 [rewrite_local] 和 [mitm]**。
      本脚本抓取脚本 → 解析头部 → 生成标准的 QuantumultX 远程重写资源。

相比旧版的几处关键改进：
  1. 站点按 User-Agent 分发内容。浏览器/curl 会被 302 跳回首页(看起来像链接失效)，
     这里按 Quantumult X → Loon → Shadowrocket → Surge → 浏览器 依次重试。
  2. 直接从脚本头部取规则（旧版是"含 url 且含 ^https?:// 就收"，
     会把作者注释掉的规则也激活；且只收手写的几条，规则明显不全）。
  3. [Script] 段(Surge 写法)自动映射成 [rewrite_local]；被 Base64/异或/\\xNN
     编码过的链接或正文也能还原。
  4. [mitm] 缺域名时，从重写规则里反推 (^https?:\\/\\/.*\\.kuwo\\.cn\\/... → *.kuwo.cn)，
     再并上你原来手写的域名(EXTRA_HOSTS)，不会丢。
  5. 抓取失败时**保留上一次生成的 .conf**，绝不把好文件覆盖成空文件。

本地运行：python generate_rules.py
云端运行：.github/workflows/auto_update.yml 已经在跑，不需要改。
"""

import base64
import gzip
import io
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timedelta, timezone

VERSION = "2.0.0"

# ===========================================================================
# ① 要转换的脚本：中文文件名 -> 脚本链接
#    文件名保持不变，就不会在仓库里多出重复文件
# ===========================================================================
APPS = {
    "酷我音乐去广告": "https://ddgksf2013.top/scripts/kkmusic.vip.js",
    "酷安去广告": "https://github.com/ddgksf2013/Scripts/raw/master/coolapk.js",
    "12306去广告": "https://github.com/ddgksf2013/Scripts/raw/master/12306.js",
    "知乎去广告": "https://ddgksf2013.top/scripts/zhihu.ads.js",
    "Nicegram高级版": "https://ddgksf2013.top/scripts/nicegram.vip.js",
    "RevenueCat多合一": "https://ddgksf2013.top/scripts/revenuecat.vip.js",
    "BuyiTunes多合一": "https://ddgksf2013.top/scripts/buyitunes.vip.js",
    "百度网盘去广告": "https://ddgksf2013.top/scripts/bdpan.ads.js",
    "Goodbility会员": "https://ddgksf2013.top/scripts/goodbility.vip.js",
    "Pixiv去广告": "https://github.com/ddgksf2013/Scripts/raw/master/pixivAds.js",
    "皮皮虾去广告": "https://gist.githubusercontent.com/ddgksf2013/bb1dadbd32f67c68772caebcc70b0a33/raw/pipixia.adblock.js",
}

# ===========================================================================
# ② 你原来手写的 [mitm] 域名：脚本头部里没有的会被保留下来
# ===========================================================================
EXTRA_HOSTS = {
    "酷我音乐去广告": ["kuwo.cn"],
    "酷安去广告": ["coolapk.com"],
    "12306去广告": ["*.12306.cn", "mobile.12306.cn"],
    "知乎去广告": ["*.zhihu.com", "zhihu.com"],
    "百度网盘去广告": ["baidubce.com"],
    "Goodbility会员": ["*.goodnotes.com"],
    "Pixiv去广告": ["*.pixiv.net", "app-api.pixiv.net"],
    "RevenueCat多合一": ["rc-pvt.acinfo.org"],
    "BuyiTunes多合一": ["sandbox.itunes.apple.com"],
}

# ===========================================================================
# ③ 你原来手写的重写规则：脚本头部里没有的会被保留下来
# ===========================================================================
EXTRA_RULES = {
    "Pixiv去广告": [
        r"^https?://app-api\.pixiv\.net/v\d/user/recommend url reject-200",
    ],
    "12306去广告": [
        r"^https?://ad\.12306\.cn/ad/wx/home.* url reject-200",
    ],
}

# ===========================================================================
# ④ 输出风格（想改格式改这里）
# ===========================================================================
ADD_HEADER = False   # True: 在 .conf 顶部加几行 # 注释（名称/来源/生成时间）
MITM_APPEND = False  # True: 生成 "hostname = %APPEND% ..."（远程资源想追加而不是覆盖时用）
KEEP_LAST_GOOD = True  # 抓取失败时保留上一次生成的文件

# 生成的 .conf 统一放这个文件夹里, 文件夹内只会出现生成的 .conf, 不掺别的东西
CONF_DIR = "conf"
# 老版本在仓库根目录生成的同名 .conf: 新位置生成成功后自动删掉, 免得两处重复
CLEAN_LEGACY_ROOT_CONFS = True

# 你自己的仓库地址（README 表格里会生成"一键引入地址"，填错会导致链接点不开）
REPO_RAW = "https://raw.githubusercontent.com/levis0792/QX-Rules/main"

# README.md 的固定说明部分（表格由脚本自动维护在 AUTO 标记之间）
README_INTRO = """# QX-Rules

把 [ddgksf2013](https://github.com/ddgksf2013) 等作者的 Quantumult X 脚本，
自动"解包"成中文名 `.conf` 重写配置，每天云端自动更新。

## 怎么用

Quantumult X → 配置文件 → 重写 → 引用 → 添加，把下表里的**原始地址**整条粘进去即可。

## 自动更新

- `.github/workflows/auto_update.yml`：每天 00:00(UTC) 自动跑一次，也可以在 Actions 页手动触发
- `generate_rules.py`：抓取脚本头部注释里的 `[rewrite_local]` / `[mitm]` 生成配置
- 这类站点只对代理客户端 UA 返回脚本内容（浏览器直接打开会被 302 跳回首页，看着像失效），
  脚本已按 Quantumult X → Loon → Shadowrocket → Surge → 浏览器 的顺序自动重试
- 抓取失败时**保留上一次生成的结果**，不会把好配置覆盖成空文件

## 免责声明

所有脚本内容版权归原作者所有，本仓库只做格式转换，仅供学习交流，请勿用于商业用途。
"""

# 站点只认代理客户端 UA；浏览器/curl 会被 302 到首页
USER_AGENTS = [
    "Quantumult X/1.4.0",
    "Loon/3.1.0 (iPhone; iOS 17.0)",
    "Shadowrocket/2.2.0",
    "Surge/5.9.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]
TIMEOUT = 20
RETRIES = 3

RE_SCHEME = re.compile(r"^https?\??://", re.I)
RE_SECTION = re.compile(r"^\[(?P<name>[A-Za-z_][A-Za-z0-9_]*)\]\s*$")
RE_RULE = re.compile(r"^(?P<pattern>\S+)\s+(?P<method>url[\w\-]*)\s+(?P<action>\S+)(?:\s+(?P<rest>.*))?$", re.I)
RE_HOST_OK = re.compile(r"^[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
RE_DECORATION = re.compile(r"[=\-*_/\s]{4,}")


def log(msg=""):
    """Windows 控制台默认是 GBK, 直接 print emoji 会抛 UnicodeEncodeError。"""
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        codec = sys.stdout.encoding or "utf-8"
        print(msg.encode(codec, "replace").decode(codec, "replace"), flush=True)


def cn_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=8)))


# ---------------------------------------------------------------------------
# 链接解码：支持 Base64、Base64+单字节异或(站点索引页用的就是这种)、URL 编码等
# ---------------------------------------------------------------------------
def decode_link(raw):
    raw = (raw or "").strip().strip("\"'`")
    if raw.startswith("http"):
        return raw
    candidates = [raw]
    if "%" in raw:
        candidates.append(urllib.parse.unquote(raw))
    match = re.search(r"\]\(<?(https?://[^\s)>]+)", raw)
    if match:
        candidates.append(match.group(1))
    for text in list(candidates):
        compact = re.sub(r"\s+", "", text)
        if not re.fullmatch(r"[A-Za-z0-9+/=_\-]{12,}", compact or ""):
            continue
        for pad in ("", "=", "=="):
            try:
                blob = base64.b64decode(compact + pad)
            except Exception:
                continue
            candidates.append(blob.decode("utf-8", "ignore"))
            for key in range(0, 256):  # 单字节异或爆破
                head = bytes(c ^ key for c in blob[:8])
                if re.match(rb"(?i)^https?://", head):
                    candidates.append(bytes(c ^ key for c in blob).decode("utf-8", "ignore"))
                    break
            break
    for text in candidates:
        if text.strip().startswith("http"):
            return text.strip()
    return raw


# ---------------------------------------------------------------------------
# 抓取：换 UA 重试，只认"不是网页"的内容
# ---------------------------------------------------------------------------
def looks_like_html(text):
    head = text[:2000].lower()
    return "<!doctype html" in head or "<html" in head


def fetch(url):
    last = ""
    for ua in USER_AGENTS:
        for attempt in range(1, RETRIES + 1):
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": ua,
                    "Accept": "text/html,application/javascript,application/json,*/*",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                })
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    raw = resp.read()
                    enc = (resp.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                elif "deflate" in enc:
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                for codec in ("utf-8-sig", "utf-8", "gb18030"):
                    try:
                        text = raw.decode(codec)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    text = raw.decode("utf-8", "replace")
                if looks_like_html(text):
                    last = f"{ua.split('/')[0]} 拿到的是网页(被站点拦下来了)"
                    break  # 换下一个 UA
                return text, ua.split("/")[0]
            except Exception as exc:  # noqa: BLE001
                last = f"{ua.split('/')[0]}: {type(exc).__name__}: {exc}"
                time.sleep(1.5 * attempt)
    raise RuntimeError(last or "抓取失败")


# ---------------------------------------------------------------------------
# 解析脚本头部
# ---------------------------------------------------------------------------
def split_sections(comment):
    """把 /* ... */ 头部注释拆成 {段名: [规则行]}；[Script] 视同 [rewrite_local]。"""
    sections = {}
    current = None
    for line in comment.splitlines():
        text = line.rstrip()
        found = RE_SECTION.match(text.strip())
        if found:
            current = found.group("name").lower()
            if current == "script":
                current = "rewrite_local"
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(text)
    out = {}
    for name, lines in sections.items():
        block = [ln.rstrip() for ln in lines]
        while block and not block[-1].strip():
            block.pop()
        while block and RE_DECORATION.fullmatch(block[-1].strip()):
            block.pop()  # 去掉 /******/ 这类收尾装饰
            while block and not block[-1].strip():
                block.pop()
        if block:
            out[name] = block
    return out


def find_section_anywhere(text, name):
    pattern = re.compile(r"^[ \t]*\[" + re.escape(name) + r"\][ \t]*\r?\n(?P<body>(?:(?!^[ \t]*\[).*(?:\r?\n|$))*)", re.M | re.I)
    found = pattern.search(text)
    if not found:
        return []
    return [ln.rstrip() for ln in found.group("body").splitlines() if ln.strip()]


def host_from_pattern(pattern):
    """^https?:\\/\\/.*\\.kuwo\\.cn\\/v2\\/... -> *.kuwo.cn"""
    text = re.sub(r"\\(.)", r"\1", pattern.lstrip("^"))
    text = RE_SCHEME.sub("", text)
    wildcard = False
    for prefix in (".*", "*."):
        if text.startswith(prefix):
            wildcard = True
            text = text[len(prefix):].lstrip(".")
            break
    head = re.split(r"[/?$#\s]", text)[0]
    if any(ch in head for ch in "[(*+|{}]"):
        return None
    host = head.strip().strip(".")
    if not host or ".." in host or not re.fullmatch(r"[A-Za-z0-9.\-]+", host):
        return None
    is_ip = bool(re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", host))
    if not is_ip and not RE_HOST_OK.match(host):
        return None
    return ("*." if wildcard else "") + host


def parse_script(text):
    """返回 (规则列表, [mitm] 域名集合)"""
    sections = {}
    comment = re.match(r"^\s*/\*(?P<body>.*?)\*/", text[:60000], re.S)
    if comment:
        sections = split_sections(comment.group("body"))
    for name in ("rewrite_local", "rewrite_remote"):
        if not sections.get(name):
            extra = find_section_anywhere(text, name)
            if extra:
                sections[name] = extra
    if not sections.get("rewrite_local"):
        extra = find_section_anywhere(text, "Script")
        if extra:
            sections["rewrite_local"] = extra
    if not sections.get("mitm"):
        extra = find_section_anywhere(text, "mitm")
        if extra:
            sections["mitm"] = extra

    rules, hosts = [], set()
    for name in ("rewrite_local", "rewrite_remote"):
        for line in sections.get(name, []):
            rule = line.strip()
            if not rule or rule.startswith("#"):
                continue
            if not RE_RULE.match(rule):
                continue
            if rule not in rules:
                rules.append(rule)
            host = host_from_pattern(rule.split()[0])
            if host:
                hosts.add(host)

    for line in sections.get("mitm", []):
        found = re.match(r"^hostname\s*=\s*(?P<value>.+)$", line.strip(), re.I)
        if not found:
            continue
        value = re.sub(r"^%APPEND%\s*", "", found.group("value"), flags=re.I)
        for item in re.split(r"[,\s]+", value):
            item = item.strip().strip(".")
            if item:
                hosts.add(item)
    return rules, hosts, sections


# ---------------------------------------------------------------------------
# 生成 .conf
# ---------------------------------------------------------------------------
def build_conf(name, url, rules, hosts, extra_note=""):
    lines = []
    if ADD_HEADER:
        lines += [
            "# " + "=" * 60,
            f"# 名称：{name}",
            f"# 脚本：{url}",
            f"# 生成：{cn_now():%Y-%m-%d %H:%M:%S} · generate_rules.py v{VERSION}",
            "# 用法：QuantumultX → 配置文件 → 重写 → 引用 本文件远程地址",
        ]
        if extra_note:
            lines.append(f"# 备注：{extra_note}")
        lines += ["# " + "=" * 60, ""]
    lines += ["[general]", "", "[rewrite_local]"]
    lines += rules
    lines += ["", "[mitm]"]
    prefix = "%APPEND% " if MITM_APPEND else ""
    lines.append(f"hostname = {prefix}" + ", ".join(sorted(hosts)))
    return "\n".join(lines) + "\n"


def conf_has_rules(path):
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return False
    body = text.split("[mitm]")[0]
    return any(ln.strip() and not ln.strip().startswith("#") and " url " in ln for ln in body.splitlines())


def clean_stale(keep):
    """conf/ 里只保留这一轮生成的文件；顺带清掉旧位置(仓库根目录)的同名遗留文件。"""
    if os.path.isdir(CONF_DIR):
        for entry in sorted(os.listdir(CONF_DIR)):
            path = os.path.join(CONF_DIR, entry)
            if entry.endswith(".conf") and os.path.isfile(path) and entry not in keep:
                try:
                    os.remove(path)
                    log(f"🧹 删掉已经不用的 {CONF_DIR}/{entry}")
                except OSError:
                    pass
    if not CLEAN_LEGACY_ROOT_CONFS:
        return
    for name in keep:
        if os.path.isfile(name) and os.path.isfile(os.path.join(CONF_DIR, name)):
            try:
                os.remove(name)
                log(f"🧹 移除旧位置的 {name}（已移到 {CONF_DIR}/）")
            except OSError:
                pass


def update_readme(rows):
    begin, end = "<!-- AUTO:BEGIN -->", "<!-- AUTO:END -->"
    table = ["| 中文配置 | 状态 | 规则数 | MitM 域名 | 一键引入地址（原始地址） |",
             "|---|---|---|---|---|"]
    table += rows
    block = begin + "\n\n" + "\n".join(table) + "\n\n" + end + "\n"
    text = ""
    if os.path.isfile("README.md"):
        with open("README.md", "r", encoding="utf-8") as fh:
            text = fh.read()
    if begin in text and end in text:
        text = re.sub(re.escape(begin) + r".*?" + re.escape(end), lambda _m: block.rstrip("\n"), text, flags=re.S)
    elif len(text.strip()) < 120:
        # 还是初始的占位 README(比如只有一行标题), 直接换成完整说明
        text = README_INTRO.rstrip() + "\n\n" + block
    else:
        text = text.rstrip() + "\n\n" + block
    with open("README.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main():
    log(f"📦 generate_rules.py v{VERSION} · 共 {len(APPS)} 个脚本 · {cn_now():%Y-%m-%d %H:%M}")
    log()
    os.makedirs(CONF_DIR, exist_ok=True)
    rows, failed = [], []
    for name, raw_url in APPS.items():
        url = decode_link(raw_url)
        filename = f"{name}.conf"
        path = os.path.join(CONF_DIR, filename)
        try:
            text, ua = fetch(url)
            rules, hosts, _ = parse_script(text)
            note = f"UA={ua}"
        except Exception as exc:  # noqa: BLE001
            rules, hosts, note = [], set(), f"抓取失败: {exc}"
            log(f"⚠️  [{name}] {note}")
        rules = list(rules) + [r for r in EXTRA_RULES.get(name, []) if r not in rules]
        hosts |= set(EXTRA_HOSTS.get(name, []))

        remote = f"{REPO_RAW}/{CONF_DIR}/{urllib.parse.quote(filename)}" if REPO_RAW else url
        if not rules:
            if KEEP_LAST_GOOD and conf_has_rules(path):
                log(f"🛡️  [{name}] 本次没抓到规则, 保留已有的 {CONF_DIR}/{filename}")
                rows.append(f"| {filename} | 保留上次结果 | — | — | {remote} |")
                continue
            failed.append(name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(build_conf(name, url, rules, hosts, note if not rules else ""))
        log(f"✨ [{name}] {len(rules)} 条规则 · {len(hosts)} 个域名 · {note}")
        rows.append(f"| {filename} | {'正常' if rules else '无规则'} | {len(rules)} | "
                    f"{len(hosts)} 个 | {remote} |")

    clean_stale({f"{name}.conf" for name in APPS})
    update_readme(rows)
    log()
    log(f"🎉 完成：{len(APPS) - len(failed)}/{len(APPS)} 个脚本成功生成 .conf")
    if failed:
        log("   需要人工补充: " + ", ".join(failed))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## QX-Rules 生成结果\n\n" + "\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
