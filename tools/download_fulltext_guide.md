# MISQ 全文 PDF 下载操作指引（深圳大学 · EBSCO）

> 目标：把 MISQ 2020–今天的论文全文 PDF 下载到本地，供画像凝练 / 后续 RAG 使用。

## 一、权限确认（已核实）

深圳大学已订阅 **Business Source Ultimate (EBSCO BSU)**，MIS Quarterly 全文收录在内。

- 数据库入口：<https://www.lib.szu.edu.cn/er/bsu>
- 使用指引：<https://www.lib.szu.edu.cn/v9/sites/default/files/er/%E6%B7%B1%E5%9C%B3%E5%A4%A7%E5%AD%A6-EBSCO%E4%BD%BF%E7%94%A8%E6%8C%87%E5%BC%95.pdf>

## 二、访问方式（二选一）

| 场景 | 做法 |
|---|---|
| 校内 / 校园网 | 直接打开上面数据库入口，EBSCO 自动识别机构 |
| 校外 | 先登录深圳大学 **WebVPN**（或 CARSI 统一认证），再从 VPN 内进 EBSCO |

> 判断是否成功：EBSCO 页面顶部出现 "Shenzhen University" 或不再提示登录，即为已授权。

## 三、第一步：确认 MISQ 的 embargo（决定你能下到哪一年）

1. EBSCO 首页顶部菜单 → **Publications**（出版物）
2. 搜索 `MIS Quarterly`
3. 点进期刊详情页，看 **Full Text** 那一栏，会标注类似：
   - `Full Text: 1990 - present`
   - `Full Text Delay: 18 months`（← 这就是 embargo，最新 18 个月只有摘要）
4. **记住这个 embargo 月数**，它决定 2025–2026 的论文能否下到全文。

## 四、批量下载（两种方式）

### 方式 A：Zotero「查找可用 PDF」半自动（推荐）

前提：已用 `misq_recent5y.ris` 把 381 条导入 Zotero。

1. Zotero → 设置 → 高级 → **OpenURL / Resolver**，填入深圳大学图书馆的 resolver 地址（在图书馆官网搜 "OpenURL" 或 "SFX" 可得）。
2. 保持学校 VPN 开启。
3. 选中一批条目（每批 **20–30 条**）→ 右键 → **查找可用 PDF**。
4. Zotero 会带机构代理自动从 EBSCO 抓 PDF；抓不到的条目会跳过，最后会列出失败清单。

### 方式 B：EBSCO 站内直接批量

1. EBSCO → Publications → `MIS Quarterly` → 进入期刊浏览。
2. 按 **年份 / 卷期** 逐期进入，勾选目标文章 → **Export / Download PDF**。
3. 同样每批 **20–30 篇**，避免限流。

## 五、预期结果（诚实说明）

- **2024 年及以前**（约 380 篇）：大概率能下全。
- **2025–2026**（约 138 篇）：受 embargo 影响，可能只有摘要、无全文。
- 缺的这 100 多篇：等 embargo 到期后，用 `fetch_misq.py` 增量补拉元数据，再重复下载即可。

## 六、下载后的存放规范

```
journal-socratic-reviewer/corpus/
├── 2020/    # 论文 PDF
├── 2021/
├── ...
├── 2025/
├── 2026/
└── editorial/   # 手动抓的 Editor's Comments（画像灵魂材料，单独放）
```

> editorial 优先：Editor's Comments 是画像"审稿标准/拒稿理由"维度的核心原料，务必单独下齐。

## 七、备选：过 embargo 的旧文可从 AIS eLibrary 免费下

embargo 约 5 年后，AIS eLibrary（aisel.aisnet.org/misq）会开放旧文。但实测公网直连会被 Cloudflare 拦，需在**校园网 / VPN 内**用浏览器（带登录态）配合 **Zotero Connector** 逐篇抓。
