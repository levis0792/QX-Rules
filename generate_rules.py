import os
import re
import urllib.request

# 🎯 对应关系：中文文件名 -> 目标脚本直链
target_scripts = {
    "Nicegram高级版": "https://ddgksf2013.top/scripts/nicegram.vip.js",
    "RevenueCat多合一": "https://ddgksf2013.top/scripts/revenuecat.vip.js",
    "BuyiTunes多合一": "https://ddgksf2013.top/scripts/buyitunes.vip.js",
    "Goodbility会员": "https://ddgksf2013.top/scripts/goodbility.vip.js",
    "百度网盘去广告": "https://ddgksf2013.top/scripts/bdpan.ads.js",
    "Pixiv去广告": "https://github.com/ddgksf2013/Scripts/raw/master/pixivAds.js",
    "酷安去广告": "https://github.com/ddgksf2013/Scripts/raw/master/coolapk.js",
    "12306去广告": "https://github.com/ddgksf2013/Scripts/raw/master/12306.js",
    "知乎去广告": "https://ddgksf2013.top/scripts/zhihu.ads.js",
    "酷我音乐去广告": "https://ddgksf2013.top/scripts/kkmusic.vip.js"
}

print("📦 开始执行中文命名多文件独立远程解包...")

for cn_name, url in target_scripts.items():
    rewrite_rules = []
    hostnames = set()
    
    try:
        print(f"正在解包 [{cn_name}]: {url}")
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Quantumult X/1.4.0"}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            content = response.read().decode('utf-8', errors='ignore')
            
            for line in content.splitlines():
                line_str = line.strip()
                # 匹配重写/拒绝/脚本规则
                if re.search(r'\^https?://.*url\s+(script|reject|demux|dns|resp)', line_str, re.IGNORECASE):
                    clean_rule = re.sub(r'^[#/\s]+', '', line_str)
                    if clean_rule and clean_rule not in rewrite_rules:
                        rewrite_rules.append(clean_rule)
                
                # 提取 hostname
                if 'hostname' in line_str.lower():
                    found_hosts = re.findall(r'([a-zA-Z0-9\-\*]+\.[a-zA-Z0-9\-\.]+)', line_str)
                    for h in found_hosts:
                        if len(h) > 3 and '.' in h and 'github' not in h and 'ddgksf2013' not in h:
                            hostnames.add(h)
                            
    except Exception as e:
        print(f"❌ 解包失败 [{cn_name}]: {e}")
        continue

    # 如果没提取到规则，跳过
    if not rewrite_rules:
        continue

    # 针对不同 App 自动补充专属基础 MitM 域名
    if "酷我" in cn_name:
        hostnames.update(["*.kuwo.cn", "kuwo.cn", "mc.tencentmusic.com"])
    elif "Nicegram" in cn_name:
        hostnames.add("nicegram.cloud")
    elif "RevenueCat" in cn_name or "BuyiTunes" in cn_name:
        hostnames.update(["api.revenuecat.com", "rc-pvt.acinfo.org", "buy.itunes.apple.com", "sandbox.itunes.apple.com"])
    elif "百度网盘" in cn_name:
        hostnames.update(["pan.baidu.com", "baidubce.com"])
    elif "Pixiv" in cn_name:
        hostnames.update(["*.pixiv.net", "app-api.pixiv.net"])
    elif "酷安" in cn_name:
        hostnames.update(["api.coolapk.com", "coolapk.com"])
    elif "12306" in cn_name:
        hostnames.update(["*.12306.cn", "mobile.12306.cn"])
    elif "知乎" in cn_name:
        hostnames.update(["*.zhihu.com", "zhihu.com"])

    # 组装独立的 .conf 内容
    conf_content = f"[general]\n\n[rewrite_local]\n" + "\n".join(rewrite_rules)
    if hostnames:
        conf_content += f"\n\n[mitm]\nhostname = " + ", ".join(sorted(list(hostnames))) + "\n"

    # 使用你给的中文名保存为配置文件（如 酷我音乐去广告.conf）
    filename = f"{cn_name}.conf"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(conf_content)
    print(f"✨ 已成功生成独立配置文件: {filename}")

print("🎉 所有中文命名配置文件解包生成完毕！")
