import os
import re
import urllib.request

# 🎯 预设所有应用的默认兜底规则和 MitM 域名（确保离线或超时也能 100% 生成文件）
app_presets = {
    "酷我音乐去广告": {
        "url": "https://ddgksf2013.top/scripts/kkmusic.vip.js",
        "rules": [
            "^https?://.*kuwo\\.cn/star/upload/95/25/1764662243747_\\.png url reject-200",
            "^https?://searchrecterm\\.kuwo\\.cn/recterm\\.s url script-response-body https://ddgksf2013.top/scripts/kkmusic.vip.js",
            "^https?://appi\\.kuwo\\.cn/kuwopay/vip-tab/page/cells url script-response-body https://ddgksf2013.top/scripts/kkmusic.vip.js"
        ],
        "hosts": ["*.kuwo.cn", "kuwo.cn", "mc.tencentmusic.com"]
    },
    "Nicegram高级版": {
        "url": "https://ddgksf2013.top/scripts/nicegram.vip.js",
        "rules": [
            "^https?://nicegram\\.cloud/api/v\\d\\/(ai-assistant/purchase-list|user/info|telegram/auth) url script-response-body https://ddgksf2013.top/scripts/nicegram.vip.js"
        ],
        "hosts": ["nicegram.cloud"]
    },
    "RevenueCat多合一": {
        "url": "https://ddgksf2013.top/scripts/revenuecat.vip.js",
        "rules": [
            "^https?://(api\\.revenuecat\\.com|rc-pvt\\..*)/v\\d\\/(subscribers|receipts) url script-response-body https://ddgksf2013.top/scripts/revenuecat.vip.js"
        ],
        "hosts": ["api.revenuecat.com", "rc-pvt.acinfo.org"]
    },
    "BuyiTunes多合一": {
        "url": "https://ddgksf2013.top/scripts/buyitunes.vip.js",
        "rules": [
            "^https?://(buy\\.itunes\\.apple\\.com|sandbox\\.itunes\\.apple\\.com)/verifyReceipt url script-response-body https://ddgksf2013.top/scripts/buyitunes.vip.js"
        ],
        "hosts": ["buy.itunes.apple.com", "sandbox.itunes.apple.com"]
    },
    "Goodbility会员": {
        "url": "https://ddgksf2013.top/scripts/goodbility.vip.js",
        "rules": [
            "^https?://.*goodbility.* url script-response-body https://ddgksf2013.top/scripts/goodbility.vip.js"
        ],
        "hosts": ["*.goodnotes.com", "notability.com"]
    },
    "百度网盘去广告": {
        "url": "https://ddgksf2013.top/scripts/bdpan.ads.js",
        "rules": [
            "^https?://pan\\.baidu\\.com/act/sapi/promotion/vip.* url reject-200"
        ],
        "hosts": ["pan.baidu.com", "baidubce.com"]
    },
    "Pixiv去广告": {
        "url": "https://github.com/ddgksf2013/Scripts/raw/master/pixivAds.js",
        "rules": [
            "^https?://app-api\\.pixiv\\.net/v\\d/user/recommend url reject-200"
        ],
        "hosts": ["*.pixiv.net", "app-api.pixiv.net"]
    },
    "酷安去广告": {
        "url": "https://github.com/ddgksf2013/Scripts/raw/master/coolapk.js",
        "rules": [
            "^https?://api\\.coolapk\\.com/v6/main/init.* url script-response-body https://github.com/ddgksf2013/Scripts/raw/master/coolapk.js"
        ],
        "hosts": ["api.coolapk.com", "coolapk.com"]
    },
    "12306去广告": {
        "url": "https://github.com/ddgksf2013/Scripts/raw/master/12306.js",
        "rules": [
            "^https?://ad\\.12306\\.cn/ad/wx/home.* url reject-200"
        ],
        "hosts": ["*.12306.cn", "mobile.12306.cn"]
    },
    "知乎去广告": {
        "url": "https://ddgksf2013.top/scripts/zhihu.ads.js",
        "rules": [
            "^https?://.*zhihu\\.com/api/v\\d/topstory/recommend.* url reject-200"
        ],
        "hosts": ["*.zhihu.com", "zhihu.com"]
    }
}

print("📦 开始生成中文配置文件...")

for cn_name, data in app_presets.items():
    rewrite_rules = list(data["rules"])
    hostnames = set(data["hosts"])
    
    # 尝试联网去远程抓取更新
    try:
        print(f"正在尝试联网更新 [{cn_name}]: {data['url']}")
        req = urllib.request.Request(data["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')
            remote_rules = []
            for line in content.splitlines():
                line_str = line.strip()
                if line_str.startswith("^https?://") and "url" in line_str.lower():
                    clean_rule = re.sub(r'^[#/\s]+', '', line_str)
                    if clean_rule and clean_rule not in remote_rules:
                        remote_rules.append(clean_rule)
            if remote_rules:
                rewrite_rules = remote_rules
                print(f"✅ [{cn_name}] 成功从远程抓取到 {len(remote_rules)} 条规则")
    except Exception as e:
        print(f"⚠️ [{cn_name}] 联网更新跳过，使用本地内置规则: {e}")

    # 组装配置文件
    conf_content = f"[general]\n\n[rewrite_local]\n" + "\n".join(rewrite_rules)
    if hostnames:
        conf_content += f"\n\n[mitm]\nhostname = " + ", ".join(sorted(list(hostnames))) + "\n"

    filename = f"{cn_name}.conf"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(conf_content)
    print(f"✨ 已成功写入: {filename}")

print("🎉 所有配置文件生成完毕！")
