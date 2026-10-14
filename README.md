# QX-Rules

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

<!-- AUTO:BEGIN -->

| 中文配置 | 状态 | 规则数 | MitM 域名 | 一键引入地址（原始地址） |
|---|---|---|---|---|
| 酷我音乐去广告.conf | 正常 | 30 | 13 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/%E9%85%B7%E6%88%91%E9%9F%B3%E4%B9%90%E5%8E%BB%E5%B9%BF%E5%91%8A.conf |
| 酷安去广告.conf | 正常 | 7 | 2 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/%E9%85%B7%E5%AE%89%E5%8E%BB%E5%B9%BF%E5%91%8A.conf |
| 12306去广告.conf | 正常 | 2 | 3 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/12306%E5%8E%BB%E5%B9%BF%E5%91%8A.conf |
| 知乎去广告.conf | 正常 | 45 | 15 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/%E7%9F%A5%E4%B9%8E%E5%8E%BB%E5%B9%BF%E5%91%8A.conf |
| Nicegram高级版.conf | 正常 | 1 | 1 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/Nicegram%E9%AB%98%E7%BA%A7%E7%89%88.conf |
| RevenueCat多合一.conf | 正常 | 2 | 3 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/RevenueCat%E5%A4%9A%E5%90%88%E4%B8%80.conf |
| BuyiTunes多合一.conf | 正常 | 1 | 2 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/BuyiTunes%E5%A4%9A%E5%90%88%E4%B8%80.conf |
| 百度网盘去广告.conf | 正常 | 15 | 5 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/%E7%99%BE%E5%BA%A6%E7%BD%91%E7%9B%98%E5%8E%BB%E5%B9%BF%E5%91%8A.conf |
| Goodbility会员.conf | 正常 | 3 | 3 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/Goodbility%E4%BC%9A%E5%91%98.conf |
| Pixiv去广告.conf | 正常 | 2 | 3 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/Pixiv%E5%8E%BB%E5%B9%BF%E5%91%8A.conf |
| 皮皮虾去广告.conf | 正常 | 2 | 1 个 | https://raw.githubusercontent.com/levis0792/QX-Rules/main/conf/%E7%9A%AE%E7%9A%AE%E8%99%BE%E5%8E%BB%E5%B9%BF%E5%91%8A.conf |

<!-- AUTO:END -->
