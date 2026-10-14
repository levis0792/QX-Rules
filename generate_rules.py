import os
import re
import urllib.request

# 🎯 你的目标脚本及高质量标准重写规则与 MitM 域名映射表
apps_data = {
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
            "^https?://api\\.coolapk\\.com/v6/main/init.* url script-response-body https://ddgksf2013.top/scripts/coolapk.js"
        ],
        "hosts": ["api.coolapk.com", "coolapk.com"]
    }
}

print("📦 开始在 GitHub 云端生成标准 Quantumult X 配置文件...")

for cn_name, data in apps_data.items():
    extracted_rules = []
    hosts = set(data["hosts"])
    
    # 1. 尝试在线远程抓取并解包
    try:
        req = urllib.request.Request(data["url"], headers={"User-Agent": "Quantumult X/1.4.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8', errors='ignore')
            for line in content.splitlines():
                line_str = line.strip()
                # 严格匹配 QX 重写规则核心特征
                if "url" in line_str.lower() and "^https?://" in line_str:
                    clean = re.sub(r'^[#/\s]+', '', line_str)
                    if clean.startswith("^https?://") and clean not in extracted_rules:
                        extracted_rules.append(clean)
    except Exception as e:
        print(f"⚠️ [{cn_name}] 远程抓取跳过，使用内置标准规则: {e}")

    # 2. 如果远程拉取失败或为空，无缝使用高质量标准规则
    final_rules = extracted_rules if extracted_rules else data["rules"]

    # 3. 严格拼接成 QX 认得的标准 .conf 结构
    conf_content = "[general]\n\n[rewrite_local]\n" + "\n".join(final_rules) + "\n\n[mitm]\nhostname = " + ", ".join(sorted(list(hosts))) + "\n"

    # 4. 写入以中文命名的文件
    filename = f"{cn_name}.conf"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(conf_content)
    print(f"✨ 成功生成标准 QX 配置文件: {filename}")

print("🎉 所有标准 .conf 文件已就绪！")
