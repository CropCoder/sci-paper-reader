# 数据文件 schema 与示例

所有路径相对于输出目录（`paper.json` 所在目录）。图片统一放 `figs/`，HTML 里的 `image` 用相对路径。

## paper.json（extract_pdf.py 生成，只读为主）

```json
{
  "source": {
    "pdf": "/abs/path/paper.pdf", "pages": 12,
    "title": "…", "authors": "…", "journal": "…", "year": "2024",
    "doi": "10.xxxx/xxxx", "corresponding": "…",
    "front_text": "首页原文，用于补元信息"
  },
  "abstract": "英文摘要",
  "sections": [
    {"id": "s1", "title": "Abstract", "role": "abstract",
     "paras": [{"id": "p1", "page": 1, "en": "…"}]}
  ],
  "figures": [
    {"id": "fig1", "label": "Figure 1", "page": 3, "caption_en": "…",
     "image": "figs/fig1.png", "fullpage": "figs/page_3.png",
     "bbox": [x0, y0, x1, y1], "confidence": "high"}
  ],
  "tables": [],
  "references": "参考文献原文",
  "extraction": {"warnings": []}
}
```

`role` 取值：`abstract | introduction | methods | results | discussion | other`。
正文段落被漏掉/串栏时可以直接改 `sections[].paras`，保持 `id` 唯一即可。

## translation.json

```json
{
  "paper_id": "stable-id-optional",
  "title_zh": "中文标题",
  "short_title": "20 字内短标题",
  "one_liner": "一句话结论（40–70 字）",
  "sections": [
    {
      "id": "s1",
      "title_zh": "摘要",
      "paras": {
        "p1": "第一段中文译文。",
        "p2": "第二段中文译文。"
      }
    }
  ]
}
```

- `sections[].id` 必须与 `paper.json` 一致；`paras` 的 key 必须是 paragraph id。
- 缺段落会导致页面显示“（本段待翻译）”；不要留空。
- `title_zh` 按论文实际章节翻译（Introduction=引言，Results=结果，Discussion=讨论，Materials and Methods=材料与方法）。

## figures.json

```json
{
  "paper_id": "stable-id-optional",
  "title_zh": "中文标题",
  "short_title": "短标题",
  "one_liner": "一句话结论",
  "overview": {
    "lead": "这组图整体在回答什么（2–4 句）。",
    "logic_summary": "图与图之间的推进关系：从结构到机制到验证。",
    "flow": [
      {"label": "Fig.1", "title": "整体架构", "desc": "回答“模型长什么样”。"},
      {"label": "Fig.2", "title": "核心机制", "desc": "回答“关键步骤怎么算”。"}
    ],
    "note": "阅读提示/颜色含义/统计标记说明（可选）。"
  },
  "figures": [
    {
      "id": "fig1",
      "short": "这张图的短标题（8–18 字）",
      "one_line": "一句话结论，必须能被图直接支持。",
      "legend_zh": "图例中译；保留 A/B/C 面板标记。",
      "what": "图中看到什么：坐标轴、分组、颜色、显著性标记、面板对应关系。",
      "meaning": "说明了什么：把图形证据翻译成生物学/方法学含义。",
      "conclusion": "结论与意义：作者想用它证明什么；不要超出数据。",
      "panels": [
        {"label": "A", "text": "面板 A 的内容与读法。"},
        {"label": "B", "text": "面板 B 的内容与读法。"}
      ],
      "caveats": ["样本量/对照/统计方法/外推限制等注意事项。"],
      "connection": "与前后图的逻辑：上一张图留下什么问题，这一张如何接上。",
      "tags": ["关键词1", "关键词2"]
    }
  ]
}
```

- `figures[].id` 必须匹配 `paper.json` 的图 id；如果论文图未抽到，先修 `paper.json`。
- `one_line` 不要写“展示了…”，要写“证明了/提示了…”。
- `caveats` 至少 1 条；没有明显局限时写“图为相关性证据，不能单独推出因果”这类具体限制。

## methods.json

```json
{
  "paper_id": "stable-id-optional",
  "title_zh": "中文标题",
  "short_title": "短标题",
  "one_liner": "一句话结论",
  "overview": "技术路线总览（2–3 句）。",
  "route": [
    {"step": "01", "name": "样本/数据", "desc": "……"},
    {"step": "02", "name": "关键实验", "desc": "……"},
    {"step": "03", "name": "数据分析", "desc": "……"}
  ],
  "methods": [
    {
      "id": "m1",
      "name": "方法中文名",
      "name_en": "English method name",
      "category": "实验 | 测序 | 计算 | 统计 | 训练",
      "what": "原理：一句话讲清楚它是什么。",
      "how": "本文怎么用：样本、对象、目的。",
      "params": "关键参数/试剂/软件版本/统计阈值。",
      "interpretation": "解读：为什么用、能回答什么、局限。",
      "used_in": ["Fig. 1", "Fig. 2"],
      "citation": {
        "text": "Author et al. Title. Journal Year;Vol:Pages.",
        "doi": "10.xxxx/xxxx",
        "url": "https://doi.org/10.xxxx/xxxx"
      }
    }
  ],
  "notes": ["方法参数以原文为准；不同实现默认值可能不同。"]
}
```

## job.md

```markdown
# <短标题>

> 一句话结论：……

- **英文标题**：……
- **期刊 / 年份**：…… / ……
- **通讯作者 / 团队**：……
- **DOI**：……

## 关键词
NLR、……、……

## 三个要点
1. ……
2. ……
3. ……

## 为什么值得读
2–3 句，说明它解决了什么、对谁有用。
```

## job.weixin.md

```markdown
# 标题（3 选 1 也可以给备选）

导语：一个现象/反差/问题，100 字内。

## 一、背景：为什么这个问题重要
## 二、科学问题：他们到底想回答什么
## 三、怎么做：一句话讲清关键设计
## 四、结果：按图讲故事
![图 1｜……](figs/fig1.png)
## 五、这意味着什么
## 六、局限与下一步
## 参考文献 / 原文链接
```

## job.talk.md

```markdown
# 组会分享：<短标题>

**发表信息**：期刊、时间、DOI
**团队**：通讯作者 / 单位
**时长**：4 分钟（可按 3–5 分钟伸缩）

## [Slide 1] 开场（20 秒）
## [Slide 2] 背景与科学问题（60 秒）
## [Slide 3] 研究设计（40 秒）
## [Slide 4] 关键结果 1（60 秒）
## [Slide 5] 关键结果 2（50 秒）
## [Slide 6] 创新点与局限（30 秒）
## [Slide 7] 我的收获 / 讨论问题（20 秒）
```
