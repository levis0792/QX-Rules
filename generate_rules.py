# -*- coding: utf-8 -*-
"""
QX-Rules · 把 QX 脚本自动"解包"成中文 .conf
==========================================

原理：这些脚本的**头部注释块里本来就写好了 [rewrite_local] 和 [mitm]**。
      本脚本抓取脚本 → 解析头部 → 生成标准的 QuantumultX 远程重写资源。

重要：默认是**忠实模式** —— 生成出来的 .conf 就是脚本头部的原样搬运：
      规则一条不多一条不少、域名照抄脚本 [mitm] 那一行（连顺序都一样），
      脚本里没写的东西（补规则、补域名、排序）一律不出现，方便和源脚本逐行对照。
      想恢复"补充模式"，把下面的 KEEP_EXTRA 改成 True。

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
  6. 生成的文件名全英文(如 coolapk-adblock.conf)，URL 里不会出现中文/百分号编码。

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

VERSION = "3.0.0"

# ===========================================================================
# ① 要转换的脚本
#    key   = 生成的文件名, 必须全英文/数字/连字符 —— 它会出现在 URL 里,
#            中文路径(带 %E9%85%B7 这种)客户端不认, 所以这里不能写中文
#    value = (中文名, 脚本链接)   中文名只用在运行日志里, 不参与文件名和 URL
# ===========================================================================
APPS = {
    "kuwo-adblock":     ("酷我音乐去广告", "https://ddgksf2013.top/scripts/kkmusic.vip.js"),
    "coolapk-adblock":  ("酷安去广告", "https://github.com/ddgksf2013/Scripts/raw/master/coolapk.js"),
    "12306-adblock":    ("12306去广告", "https://github.com/ddgksf2013/Scripts/raw/master/12306.js"),
    "zhihu-adblock":    ("知乎去广告", "https://ddgksf2013.top/scripts/zhihu.ads.js"),
    "nicegram-premium": ("Nicegram高级版", "https://ddgksf2013.top/scripts/nicegram.vip.js"),
    "revenuecat":       ("RevenueCat多合一", "https://ddgksf2013.top/scripts/revenuecat.vip.js"),
    "buyitunes":        ("BuyiTunes多合一", "https://ddgksf2013.top/scripts/buyitunes.vip.js"),
    "baidupan-adblock": ("百度网盘去广告", "https://ddgksf2013.top/scripts/bdpan.ads.js"),
    "goodbility":       ("Goodbility会员", "https://ddgksf2013.top/scripts/goodbility.vip.js"),
    "pixiv-adblock":    ("Pixiv去广告", "https://github.com/ddgksf2013/Scripts/raw/master/pixivAds.js"),
    "pipixia-adblock":  ("皮皮虾去广告", "https://gist.githubusercontent.com/ddgksf2013/bb1dadbd32f67c68772caebcc70b0a33/raw/pipixia.adblock.js"),
}

# ===========================================================================
# ② 【默认不生效】补充模式用的表：把脚本头部里没有的域名 / 规则并进生成结果。
#    忠实模式(KEEP_EXTRA = False，默认)完全忽略这两张表 —— 生成出来的 .conf
#    就是脚本头部的原样搬运，脚本里没写的东西一个字都不会出现。
# ===========================================================================
EXTRA_HOSTS = {
    "kuwo-adblock": ["kuwo.cn"],
    "coolapk-adblock": ["coolapk.com"],
    "12306-adblock": ["*.12306.cn", "mobile.12306.cn"],
    "zhihu-adblock": ["*.zhihu.com", "zhihu.com"],
    "baidupan-adblock": ["baidubce.com"],
    "goodbility": ["*.goodnotes.com"],
    "pixiv-adblock": ["*.pixiv.net", "app-api.pixiv.net"],
    "revenuecat": ["rc-pvt.acinfo.org"],
    "buyitunes": ["sandbox.itunes.apple.com"],
}

# ===========================================================================
# ②-2 【默认不生效】见上：想恢复"补规则"，把 KEEP_EXTRA 改成 True
# ===========================================================================
EXTRA_RULES = {
    "pixiv-adblock": [
        r"^https?://app-api\.pixiv\.net/v\d/user/recommend url reject-200",
    ],
    "12306-adblock": [
        r"^https?://ad\.12306\.cn/ad/wx/home.* url reject-200",
    ],
    # 酷我：脚本头部没覆盖到的广告/推广/统计域名，取自自动更新的规则库
    # (Cats-Team/AdRules 的 qx.conf: host-suffix,xxx.kuwo.cn,reject)，整域拦截，不依赖具体路径
    "kuwo-adblock": [
        r"^https?://deliver\.kuwo\.cn/ url reject-200",
        r"^https?://g\.kuwo\.cn/ url reject-200",
        r"^https?://kwmsg\.kuwo\.cn/ url reject-200",
        r"^https?://log\.kuwo\.cn/ url reject-200",
        r"^https?://msclick2\.kuwo\.cn/ url reject-200",
        r"^https?://msphoneclick\.kuwo\.cn/ url reject-200",
        r"^https?://updatepage\.kuwo\.cn/ url reject-200",
        r"^https?://wa\.kuwo\.cn/ url reject-200",
        r"^https?://webstat\.kuwo\.cn/ url reject-200",
        # SVIP 解锁：脚本自带的规则是"精确路径"，App 一更新路径就可能落空。
        # 这里放宽到"接口前缀"，仍然交给同一个解锁脚本处理，兜住版本漂移。
        r"^https?://vip1\.kuwo\.cn/vip/ url script-response-body https://ddgksf2013.top/scripts/kkmusic.vip.js",
        r"^https?://appi\.kuwo\.cn/kuwopay/ url script-response-body https://ddgksf2013.top/scripts/kkmusic.vip.js",
        r"^https?://musicpay\.kuwo\.cn/ url script-response-body https://ddgksf2013.top/scripts/kkmusic.vip.js",
        r"^https?://.*\.kuwo\.cn/v\d/api/pay/ url script-response-body https://ddgksf2013.top/scripts/kkmusic.vip.js",
    ],
}

# ===========================================================================
# ④ 输出风格（想改格式改这里）
# ===========================================================================
# 文件顶部加几行 # 注释(名称/脚本/更新时间/规则数)。QX 认 # 注释,
# 主流规则库(blackmatrix7)也这么写; 英文文件名看不出内容, 靠这里认。
ADD_HEADER = True
KEEP_LAST_GOOD = True  # 抓取失败时保留上一次生成的文件
WRITE_README = False  # False: 脚本完全不碰 README.md（你想写什么就写什么，不会被覆盖）

# ---- 忠实模式（默认）：.conf 的内容 = 脚本头部原样，不加规则、不加域名、不改顺序 ----
KEEP_EXTRA = False      # True: 才把上面的 EXTRA_HOSTS / EXTRA_RULES 并进结果
DERIVE_HOSTS = True     # 仅当脚本自己没写 [mitm] 时，才由规则反推域名补上
# QX 的"重写引用"资源里不要写 [rewrite_local] / [mitm] 段头（实测引用时会报错），
# 正确写法是"裸规则 + 一行 hostname = ..."。想改回带段头的写法就把这里改成 True。
OUTPUT_SECTIONS = False
USE_CACHE_WHEN_OFFLINE = True  # 联网失败时改用 .cache/<key>.js（本地断网也能重新生成）
OFFLINE = bool(os.environ.get("QX_OFFLINE")) or "--offline" in sys.argv  # 完全不联网, 只读 .cache

# [mitm] 那行：默认**原样照抄脚本里写的 hostname 行**（连空格都照抄）。
# 想改成统一格式 "hostname = %APPEND% 域名..."（追加而不是覆盖）就把 VERBATIM_HOSTNAME 改 False。
VERBATIM_HOSTNAME = True
MITM_APPEND = False  # 仅在 VERBATIM_HOSTNAME = False 时才用到

# 生成的 .conf 统一放这个文件夹里, 文件夹内只会出现生成的 .conf, 不掺别的东西
CONF_DIR = "conf"
# 抓到的脚本原文留一份到这里, 断网/被抓站拦下时用它重新生成（.gitignore 里已忽略, 不会提交）
CACHE_DIR = ".cache"
# 老版本在仓库根目录生成的同名 .conf: 新位置生成成功后自动删掉, 免得两处重复
CLEAN_LEGACY_ROOT_CONFS = True

# 额外生成 conf/allinone.conf：把 11 个脚本的规则合并成一份, QX 里只引一条即可
MAKE_ALLINONE = True
ALLINONE_FILE = "allinone"

# 你自己的仓库地址（README 表格里会生成"一键引入地址"，填错会导致链接点不开）
REPO_RAW = "https://raw.githubusercontent.com/levis0792/QX-Rules/main"

# README.md 的说明部分（整个 README 由脚本生成, 想改文案就改这里）
README_INTRO = """# QX-Rules

QuantumultX 重写配置，脚本自动解包生成，每天云端自动更新。
用法：Quantumult X → 配置文件 → 重写 → 引用 → 添加，粘贴下面任一条地址。"""

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
def looks_like_js(text):
    """区分"QX 脚本 .js" 和 "裸格式 .conf 资源", 后者才需要按裸规则扫描。"""
    if text.lstrip().startswith("{") or re.match(r"^\s*/\*", text[:60000], re.S):
        return True
    return any(token in text for token in ("$done", "$response", "$request", "function(", "=>"))


def hosts_from_value(value):
    value = re.sub(r"^%APPEND%\s*", "", value, flags=re.I)
    return {item.strip() for item in re.split(r"[,\s]+", value) if item.strip()}


def hosts_from_value_ordered(value):
    """按脚本里写的原样/原顺序返回域名列表（只去空、去重，不排序、不增删）。"""
    value = re.sub(r"^%APPEND%\s*", "", value, flags=re.I)
    out = []
    for item in re.split(r"[,\s]+", value):
        item = item.strip().strip(".")
        if item and item not in out:
            out.append(item)
    return out


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
    if not sections.get("rewrite_local") and not looks_like_js(text):
        # 裸格式资源：QX 官方 sample-import-rewrite.snippet、blackmatrix7 的
        # QuantumultX/Advertising.conf、ddgksf2013 的 EmbyPlugin.conf 都是这种写法,
        # 文件里直接就是规则行, 没有 [段名]。
        bare = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped[:1] in "#;/":
                continue
            if re.match(r"^hostname\s*=", stripped, re.I):
                continue
            if " url " in stripped and RE_RULE.match(stripped):
                bare.append(stripped)
        if bare:
            sections["rewrite_local"] = bare

    rules, derived = [], []
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
            if host and host not in derived:
                derived.append(host)

    # 域名一律照抄脚本 [mitm] 里写的（原顺序、原写法，不排序、不补域名）。
    # 只有脚本自己压根没写 [mitm] 时，才退回"从规则反推"，否则脚本没写的域名不会出现。
    declared = []
    hostname_line = ""
    for line in sections.get("mitm", []):
        found = re.match(r"^hostname\s*=\s*(?P<value>.+)$", line.strip(), re.I)
        if not found:
            continue
        if not hostname_line:
            hostname_line = line.strip()  # 原样留着（连空格一起照抄）
        for item in hosts_from_value_ordered(found.group("value")):
            if item not in declared:
                declared.append(item)
    for line in text.splitlines():  # 裸格式里的 hostname 行
        found = re.match(r"^\s*hostname\s*=\s*(?P<value>.+)$", line, re.I)
        if found:
            if not hostname_line:
                hostname_line = line.strip()
            for item in hosts_from_value_ordered(found.group("value")):
                if item not in declared:
                    declared.append(item)

    if declared:
        hosts, hosts_declared = declared, True
    elif DERIVE_HOSTS:
        hosts, hosts_declared = derived, False  # 脚本没写 [mitm]，只能从规则反推
    else:
        hosts, hosts_declared = [], False
    return rules, hosts, sections, hosts_declared, hostname_line


# ---------------------------------------------------------------------------
# 生成 .conf
# ---------------------------------------------------------------------------
def build_conf(name, url, rules, hosts, extra_note="", hostname_line=""):
    """
    忠实模式：正文 = 脚本头部原样（规则照抄、域名照抄原顺序）。
    结构用 [rewrite_local] + [mitm] 段头，和脚本头部、QX 官方
    sample-import-rewrite.snippet 一样，方便拿源脚本逐行核对。
    [mitm] 那一行优先用 hostname_line（脚本里原样的那行），没有才自己拼。
    """
    lines = []
    if ADD_HEADER:
        lines += [
            f"# NAME: {name}",
            f"# SCRIPT: {url}",
            f"# RULES: {len(rules)}",
            f"# MITM: {len(hosts)}",
        ]
        if extra_note:
            lines.append(f"# NOTE: {extra_note}")
        lines.append("")
    if OUTPUT_SECTIONS:
        lines.append("[rewrite_local]")
    lines += rules
    lines.append("")
    if OUTPUT_SECTIONS:
        lines += ["[mitm]", ""]
    if VERBATIM_HOSTNAME and hostname_line:
        lines.append(hostname_line)
    else:
        prefix = "%APPEND% " if MITM_APPEND else ""
        lines.append(f"hostname = {prefix}" + ", ".join(hosts))
    return "\n".join(lines).rstrip() + "\n"


def conf_has_rules(path):
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return False
    return any(ln.strip() and not ln.strip().startswith("#") and " url " in ln for ln in text.splitlines())


def cache_path(key):
    return os.path.join(CACHE_DIR, f"{key}.js")


def save_cache(key, text):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path(key), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError:
        pass


def load_cache(key):
    try:
        with open(cache_path(key), "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def lookup_script(key, url):
    """返回 (脚本原文, 说明)。离线模式直接读缓存；联网失败也退回缓存。"""
    if OFFLINE:
        cached = load_cache(key)
        if cached:
            return cached, "离线模式: 用本地 .cache 里的脚本"
        raise RuntimeError("离线模式, 且 .cache 里没有这份脚本")
    try:
        text, ua = fetch(url)
        save_cache(key, text)
        return text, f"UA={ua}"
    except Exception as exc:  # noqa: BLE001
        cached = load_cache(key) if USE_CACHE_WHEN_OFFLINE else ""
        if cached:
            return cached, f"联网失败({type(exc).__name__}) → 用本地缓存"
        raise


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


def clean_nested_conf_dir():
    """
    清掉 conf/conf/ 这种"套娃"重复目录（多半是网页上传时选错目录留下的），
    免得 QX 引用到里面那份旧配置。只有当里面全是 .conf 时才动它。
    """
    outer = os.path.abspath(CONF_DIR)
    nested = os.path.abspath(os.path.join(CONF_DIR, "conf"))
    if nested == outer or not nested.startswith(outer + os.sep) or not os.path.isdir(nested):
        return
    entries = sorted(os.listdir(nested))
    if not entries or not all(e.lower().endswith(".conf") for e in entries):
        return  # 里面还掺着别的东西，就不碰
    for entry in entries:
        try:
            os.remove(os.path.join(nested, entry))
        except OSError:
            pass
    try:
        os.rmdir(nested)
        log(f"🧹 清掉重复的 {CONF_DIR}/conf/（{len(entries)} 个旧 .conf）")
    except OSError:
        pass


def read_conf(path):
    """读回一份已生成的 .conf，返回 (规则行, 域名列表)。合集就是靠它拼的。"""
    rules, hosts = [], []
    if not os.path.isfile(path):
        return rules, hosts
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if RE_SECTION.match(stripped):  # 跳过 [rewrite_local] / [mitm] 段头
                continue
            found = re.match(r"^hostname\s*=\s*(.+)$", stripped, re.I)
            if found:
                for item in hosts_from_value_ordered(found.group(1)):
                    if item not in hosts:
                        hosts.append(item)
            elif " url " in stripped and stripped not in rules:
                rules.append(stripped)
    return rules, hosts


def build_allinone(entries):
    """entries: [(中文名, 文件名, 规则列表, 域名列表), ...]"""
    lines = ["# NAME: allinone（全部脚本合集）", ""]
    if OUTPUT_SECTIONS:
        lines.append("[rewrite_local]")
    seen, all_hosts, total = set(), [], 0
    for cn_name, filename, rules, hosts in entries:
        fresh = [rule for rule in rules if rule not in seen]
        if not fresh:
            continue
        lines.append(f"# ===== {cn_name}（{filename}）=====")
        for rule in fresh:
            seen.add(rule)
            lines.append(rule)
            total += 1
        lines.append("")
        for host in hosts:
            if host not in all_hosts:
                all_hosts.append(host)
    if OUTPUT_SECTIONS:
        lines.append("[mitm]")
        lines.append("")
    prefix = "%APPEND% " if MITM_APPEND else ""
    lines.append(f"hostname = {prefix}" + ", ".join(all_hosts))
    return "\n".join(lines).rstrip() + "\n", total


def update_readme(urls, notes):
    """仅当 WRITE_README = True 时调用；README 会被整份覆盖, 手改无效。"""
    text = README_INTRO.rstrip() + "\n"
    if urls:
        text += "\n```\n" + "\n".join(urls) + "\n```\n"
    if notes:
        text += "\n" + "\n".join(notes) + "\n"
    with open("README.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    log(f"📝 README.md 已更新（{len(urls)} 条引入地址）")


def main():
    mode = "离线(只读 .cache)" if OFFLINE else ("补充模式" if KEEP_EXTRA else "忠实模式")
    log(f"📦 generate_rules.py v{VERSION} · {mode} · 共 {len(APPS)} 个脚本 · {cn_now():%Y-%m-%d %H:%M}")
    log()
    os.makedirs(CONF_DIR, exist_ok=True)
    urls, notes, failed = [], [], []
    for key, (cn_name, raw_url) in APPS.items():
        url = decode_link(raw_url)
        filename = f"{key}.conf"
        path = os.path.join(CONF_DIR, filename)
        try:
            text, note = lookup_script(key, url)
            rules, hosts, _sections, hosts_declared, hostname_line = parse_script(text)
        except Exception as exc:  # noqa: BLE001
            rules, hosts, hosts_declared, hostname_line, note = [], [], True, "", f"抓取失败: {exc}"
            log(f"⚠️  [{cn_name}] {note}")
        if KEEP_EXTRA:  # 补充模式（默认关）：才把 EXTRA_RULES / EXTRA_HOSTS 并进来
            rules = list(rules) + [r for r in EXTRA_RULES.get(key, []) if r not in rules]
            for host in EXTRA_HOSTS.get(key, []):
                if host not in hosts:
                    hosts.append(host)
            hostname_line = ""  # 域名被改过, 就不能再照抄脚本那行了

        conf_note = note if not rules else ""
        if hosts and not hosts_declared:
            conf_note = (conf_note + "；" if conf_note else "") + "脚本头部没写 [mitm]，域名由规则反推"
        urls.append(f"{REPO_RAW}/{CONF_DIR}/{urllib.parse.quote(filename)}" if REPO_RAW else url)
        if not rules:
            if KEEP_LAST_GOOD and conf_has_rules(path):
                log(f"🛡️  [{cn_name}] 本次没抓到规则, 保留已有的 {CONF_DIR}/{filename}")
                notes.append(f"⚠️ {cn_name}（{filename}）本次抓取失败，已保留上次生成的配置")
                continue
            failed.append(cn_name)
            notes.append(f"⚠️ {cn_name}（{filename}）这次没抓到任何规则")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(build_conf(cn_name, url, rules, hosts, conf_note, hostname_line))
        log(f"✨ [{cn_name}] {filename} · {len(rules)} 条规则 · {len(hosts)} 个域名 · {note}")

    keep = {f"{key}.conf" for key in APPS}
    if MAKE_ALLINONE:
        entries = []
        for key, (cn_name, _unused) in APPS.items():
            filename = f"{key}.conf"
            rules, hosts = read_conf(os.path.join(CONF_DIR, filename))
            entries.append((cn_name, filename, rules, hosts))
        content, total = build_allinone(entries)
        allinone = f"{ALLINONE_FILE}.conf"
        with open(os.path.join(CONF_DIR, allinone), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        keep.add(allinone)
        log(f"📚 合集 {CONF_DIR}/{allinone} · {len(entries)} 个脚本 · 去重后 {total} 条规则")
        if REPO_RAW:
            urls.insert(0, f"{REPO_RAW}/{CONF_DIR}/{allinone}")
    clean_stale(keep)
    clean_nested_conf_dir()
    if WRITE_README:
        update_readme(urls, notes)
    log()
    log(f"🎉 完成：{len(APPS) - len(failed)}/{len(APPS)} 个脚本成功生成 .conf")
    if failed:
        log("   需要人工补充: " + ", ".join(failed))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"## QX-Rules 生成结果\n\n成功 {len(APPS) - len(failed)}/{len(APPS)}\n")
            for line in notes:
                fh.write(f"- {line}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
