import os
import re
import urllib.request

# 🎯 目标脚本及其全套高质量默认/兜底规则与 MitM 域名
app_configs = {
    "酷我音乐去广告": {
        "url": "https://ddgksf2013.top/scripts/kkmusic.vip.js",
        "fallback_rules": [
            "^https?://.*kuwo\\.cn/star/upload/95/25/1764662243747_\\.png url reject-200",
            "^https?://searchrecterm\\.kuwo\\.cn/recterm\\.s url script-response-body https://ddgksf2013.top/scripts/kkmusic.vip.js",
            "^https?://appi\\.kuwo\\.cn/kuwopay/vip-tab/page/cells url script-response-body https://ddgksf2013.top/scripts/kkmusic.vip.js",
            "^https?://appi\\.kuwo\\.cn/kuwopay/vip-tab/setting url script-response-body https://ddgksf2013.top/scripts/kkmusic.vip.js",
            "^https?://musicpay\\.kuwo\\.cn/music\\.pay\\?newver url script-response-body https://ddgksf2013.top/scripts/kkmusic.vip.js"
        ],
        "hosts": ["*.kuwo.cn", "kuwo.cn", "mc.tencentmusic.com"]
    },
    "Nicegram高级版": {
        "url": "https://ddgksf2013.top/scripts/nicegram.vip.js",
        "fallback_rules": [
            "^https?://nicegram\\.cloud/api/v\\d\\/(ai-assistant/purchase-list|user/info|telegram/auth) url script-response-body https://ddgksf2013.top/scripts/nicegram.vip.js"
        ],
        "hosts": ["nicegram.cloud"]
    },
    "RevenueCat多合一": {
        "url": "https://ddgksf2013.top/scripts/revenuecat.vip.js",
        "fallback_rules": [
            "^https?://(api\\.revenuecat\\.com|rc-pvt\\..*)/v\\d\\/(subscribers|receipts) url script-response-body https://ddgksf2013.top/scripts/revenuecat.vip.js"
        ],
        "hosts": ["api.revenuecat.com", "rc-pvt.acinfo.org"]
    },
    "BuyiTunes多合一": {
        "url": "https://ddgksf2013.top/scripts/buyitunes.vip.js",
        "fallback_rules": [
            "^https?://(buy\\.itunes\\.apple\\.com|sandbox\\.itunes\\.apple\\.com)/verifyReceipt url script-response-body https://ddgksf2013.top/scripts/buyitunes.vip.js"
        ],
        "hosts": ["buy.itunes.apple.com", "sandbox.itunes.apple.com"]
    },
    "Goodbility会员": {
        "url": "https://ddgksf2013.top/scripts/goodbility.vip.js",
        "fallback_rules": [
            "^https?://.*goodbility.* url script-response-body https://ddgksf2013.top/scripts/goodbility.vip.js"
        ],
        "hosts": ["*.goodnotes.com", "notability.com"]
    },
    "百度网盘去广告": {
        "url": "https://ddgksf2013.top/scripts/bdpan.ads.js",
        "fallback_rules": [
            "^https?://pan\\.baidu\\.com/act/sapi/promotion/vip.* url reject-200"
        ],
        "hosts": ["pan.baidu.com", "baidubce.com"]
    },
    "Pixiv去广告": {
        "url": "https://github.com/ddgksf2013/Scripts/raw/master/pixivAds.js",
        "fallback_rules": [
            "^https?://app-api\\.pixiv\\.net/v\\d/user/recommend url reject-200"
        ],
        "hosts": ["*.pixiv.net", "app-api.pixiv.net"]
    },
    "酷安去广告": {
        "url": "https://github.com/ddgksf2013/Scripts/raw/master/coolapk.js",
        "fallback_rules": [
            "^https?://api\\.coolapk\\.com/v6/main/init.* url script-response-body https://github.com/ddgksf2013.top/scripts/coolapk.js"
        ],
        "hosts": ["api.coolapk.com", "coolapk.com"]
    },
    "12306去广告": {
        "url": "https://github.com/ddgksf2013/Scripts/raw/master/12306.js",
        "fallback_rules": [
            "^https?://ad\\.12306\\.cn/ad/wx/home.* url reject-200"
        ],
        "hosts": ["*.12306.cn", "mobile.12306.cn"]
    },
    "知乎去广告": {
        "url": "https://ddgksf2013.top/scripts/zhihu.ads.js",
        "fallback_rules": [
            "^https?://.*zhihu\\.com/api/v\\d/topstory/recommend.* url reject-200"
        ],
        "hosts": ["*.zhihu.com", "zhihu.com"]
    }
}

print("📦 开始执行通用万能解包与智能兜底...")

for cn_name, config in app_configs.itemsURL := config["url"]
    extracted_rules = []
    hostnames = set(config["hosts"])
    
    try:
        print(f"正在智能解包 [{cn_name}]: {config['url']}")
        req = urllib.request.Request(
            config['url'], 
            headers={"User-Agent": "Quantumult X/1.4.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8', errors='ignore')
            
            for line in content.splitlines():
                line_str = line.strip()
                
                # 🌐 通用万能匹配逻辑：只要行里同时包含 ^https?:// 和 url，不管它带没带 # 注释、或在代码的哪个位置，全都能识别出来
                if "url" in line_str.lower() and "^https?://" in line_str:
                    # 剥离行首所有的注释符（#）、斜杠（/）和空格
                    clean_rule = re.sub(r'^[#/\s]+', '', line_str)
                    if clean_rule.startswith("^https?://") and clean_rule not in extracted_rules:
                        extracted_rules.append(clean_rule)
                
                # 自动从文本中提取更多潜在的 hostname
                if 'hostname' in line_str.lower():
                    found_hosts = re.findall(r'([a-zA-Z0-9\-\*]+\.[a-zA-Z0-9\-\.]+)', line_str)
                    for h in found_hosts:
                        if len(h) > 3 and '.' in h and 'github' not in h and 'ddgksf2013' not in h:
                            hostnames.add(h)
                            
    except Exception as e:
        print(f"⚠️ [{cn_name}] 远程抓取遇到阻碍: {e}")

    # 💡 智能合并：如果远程成功解包出了规则，就用远程的；如果远程没抓到或部分漏掉，自动用高质量兜底规则补齐，确保完美生效
    final_rules = extracted_rules if extracted_rules else config["fallback_rules"]
    if extracted_rules:
        print(f"✅ [{cn_name}] 成功在线解包提取到 {len(extracted_rules)} 条规则")
    else:
        print(f"🔄 [{cn_name}] 已无缝启用高质量本地兜底规则")

    # 组装标准的 .conf 结构
    conf_content = f"[general]\n\n[rewrite_local]\n" + "\n".join(final_rules)
    if hostnames:
        conf_content += f"\n\n[mitm]\nhostname = " + ", ".join(sorted(list(hostnames))) + "\n"

    filename = f"{cn_name}.conf"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(conf_content)
    print(f"✨ 成功生成配置文件: {filename}\n")

print("🎉 所有配置文件完美解包与生成完毕！")
