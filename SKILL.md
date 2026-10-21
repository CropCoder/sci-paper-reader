---
name: sci-paper-reader
description: 把一篇科研论文 PDF 解读成一套可直接阅读、汇报和发布的中文材料：关键短标题与摘要速览、左右对照逐段翻译网页（书签+目录导航）、Figure 图解网页、方法技术网页、微信公众号科普文章、3–5 分钟组会讲稿。
whenToUse: 当用户上传或指定一篇论文 PDF，要求解读、翻译、图解、方法梳理、公众号推文或组会汇报稿时使用；也适用于一次处理多篇论文。
metadata:
  version: "1.1.0"
  author: "DeepSeek Harness"
---

# 科研文献解读（Sci Paper Reader）

把一篇论文 PDF 变成 6 个交付物。核心不是“总结”，而是**可核对、可讲解、可传播**：每个数字、图注、方法引用都能回到原文。

## 交付物

| 文件 | 内容 |
|---|---|
| `job.md` | 关键短标题、一句话结论、5 个关键词、3 条要点、论文元信息 |
| `job.en2cn.html` | 左英文 / 右中文逐段对照；目录、搜索、书签、进度、深浅色、打印 |
| `job.fig.html` | 顶部 Figure 导航；先总览逻辑链，再逐图看原图/图例/解读/含义/结论/注意事项 |
| `job.method.html` | 按论文顺序拆解材料与方法：原理、本文怎么用、参数、解读、原始文献链接 |
| `job.weixin.md` | 微信公众号学术科普文，故事线 + 配图 + 通俗解释 |
| `job.talk.md` | 3–5 分钟组会讲稿，含发表信息、团队、期刊、背景、问题、结果、创新点 |

## 不可违背的规则

1. **不编造**：数字、样本量、统计值、作者、期刊、年份、DOI 一律以 PDF/原文为准；不确定就写“原文未说明”，不要猜。
2. **翻译逐段对齐**：英文一段、中文一段，不合并、不遗漏、不增写原文没有的结论；术语首次出现保留英文括号。
3. **看图必须真的看**：用 `read_image` 打开每一张裁剪图，确认面板、坐标轴、图例、显著性标记；自动裁剪不可靠时用 `crop_figure.py` 重裁。
4. **方法引用必须可点**：优先用论文参考文献里的原始文献；DOI/URL 不确定就写“见原文参考文献”，不要伪造链接。
5. **中文可读**：避免机翻腔；长句拆短；科普文不用“显著提升”这类没有数据支撑的夸张词。

## 工作流

设 `SKILL_DIR` 为本 skill 的根目录（加载 skill 时给出的 base directory），`OUT` 为输出目录。
默认输出到 PDF 同级的 `<pdf_stem>_解读/`，不要覆盖已有文件；若目录已存在，先询问用户或换名。

### 1. 抽取出结构

```bash
mkdir -p "$OUT"
python3 "$SKILL_DIR/scripts/extract_pdf.py" paper.pdf -o "$OUT"
```

产物：`paper.json`（front matter / sections / paragraphs / figures / tables / references）、`paper.txt`、`figs/`，以及三个可填写的空模板 `translation.template.json`、`figures.template.json`、`methods.template.json`。

然后**完整读一遍** `paper.json` 和 `paper.txt`：
- 确认 title / authors / journal / year / DOI；`source.front_text` 是首页原文，用来补元信息。
- 确认 `sections` 顺序、`role`（abstract/introduction/methods/results/discussion）和段落数；抽取器漏段/串栏时，用 `paper.txt` 对照修正 `paper.json`。
- 看 `extraction.warnings` 和每张图的 `confidence`。`low/guessed` 必须打开图检查。

### 2. 写 `job.md`

短标题控制在 8–20 个汉字，能一眼看出“对象 + 发现/方法”。结构见 `references/schemas.md#jobmd`。
这一步先定下全文的“一句话主线”，后面 5 个产物都围绕它，避免各写各的。

### 3. 逐段翻译 → `job.en2cn.html`

1. 复制模板再填，避免手写 id 出错：`cp "$OUT/translation.template.json" "$OUT/translation.json"`，然后按 `paper.json` 的 section/paragraph id 填中文；**每个 paragraph id 都要有中文**（公式段可保留公式 + 一句说明）。
2. 翻译规范见 `references/translation.md`：忠实、术语统一、数字单位不变、图表引用保留 `Fig. 1`。
3. 生成页面：

```bash
python3 "$SKILL_DIR/scripts/build_en2cn.py" \
  --paper "$OUT/paper.json" --translation "$OUT/translation.json" \
  --out "$OUT/job.en2cn.html"
```

4. 打开页面检查：目录是否覆盖全部章节、书签能否保存（localStorage）、搜索是否命中、手机上是否变成单栏。

### 4. 逐图理解 → `job.fig.html`

1. 用 `read_image` 打开 `figs/fig1.png` … 每一张；对照 `caption_en` 和正文中引用该图的句子。
2. 如果图被裁掉/混入正文/只截到半张，立即重裁：

```bash
python3 "$SKILL_DIR/scripts/crop_figure.py" --paper "$OUT/paper.json" --list
python3 "$SKILL_DIR/scripts/crop_figure.py" --paper "$OUT/paper.json" \
  --fig fig2 --bbox 70,85,530,350 --out "$OUT/figs/fig2.png" --update
```

3. 复制模板再填：`cp "$OUT/figures.template.json" "$OUT/figures.json"`。写 `figures.json`（schema 见 `references/schemas.md#figuresjson`），至少包含：
   - `overview.lead`：这组图整体在回答什么；
   - `overview.logic_summary` + `flow`：图与图的推进关系（不是“Fig.1 是…Fig.2 是…”的流水账）；
   - 每图：`short`、`one_line`、`legend_zh`、`what`、`meaning`、`conclusion`、`panels`、`caveats`、`connection`。
4. 生成页面：

```bash
python3 "$SKILL_DIR/scripts/build_fig.py" \
  --paper "$OUT/paper.json" --figures "$OUT/figures.json" \
  --out "$OUT/job.fig.html"
```

5. 检查：顶部 Fig 切换、`#fig2` 深链、图片放大、左右方向键、每张图是否都有“结论 + 注意事项”。

### 5. 方法拆解 → `job.method.html`

1. 复制模板再填：`cp "$OUT/methods.template.json" "$OUT/methods.json"`。
2. 从 `sections[role=methods]` 和正文里提取实际用到的技术，按论文顺序排列；不要把所有通用技术都塞进去，只写“这篇论文真的用了”的。
3. 每项写：原理（是什么）、本文怎么用、关键参数、解读（为什么这样做/局限）、用于哪些图、原始文献。
4. 原始文献优先取论文 References 中对应条目；用 `web_search` / `web_fetch` 核验 DOI 后再写。
5. 生成页面：

```bash
python3 "$SKILL_DIR/scripts/build_method.py" \
  --paper "$OUT/paper.json" --methods "$OUT/methods.json" \
  --out "$OUT/job.method.html"
```

详见 `references/methods.md`。

### 6. 微信公众号文章 → `job.weixin.md`

- 1500–3000 中文字；标题给 3 个备选。
- **每个自然段不少于 200 个中文字**；用完整段落推进，不要拆成大量短句、碎片列表或连续设问。
- **问句最多 1–2 个**；用陈述句把“背景 → 科学问题 → 方法 → 结果 → 意义 → 局限”讲成一条完整故事线，段与段之间要有承接。
- 解读要具体：数字代表什么、图怎么看、这个结果为什么重要、和上一段是什么关系，都要说清楚；不要只贴结论。
- 适当插入 `![图注](figs/fig1.png)`；每张图配一句“这张图在说什么”，不要把图注原样贴上去。
- 语气：学术科普博主，通俗易懂但不夸大；术语第一次出现用一句人话解释。
- 结构模板见 `references/wechat.md`。

### 7. 组会讲稿 → `job.talk.md`

- 3–5 分钟，约 900–1300 中文字；按 4 分钟设计，标出时间点。
- 必须包含：发表时间、期刊、通讯作者/团队、背景、科学问题、主要结果（2–3 个）、创新点、个人收获/启示。
- 写成“能直接念”的口语稿，不要写成论文摘要；每页 PPT 对应一段，标 `[Slide 1]`。
- 结构模板见 `references/talk.md`。

### 8. 自检与交付

```bash
python3 "$SKILL_DIR/scripts/check_outputs.py" "$OUT"
```

然后逐项检查：
- [ ] 6 个文件齐全，HTML 能离线打开，图片路径正确；
- [ ] 翻译覆盖率 100%，无“待翻译”；数字/单位与原文一致；
- [ ] 每张主图都有裁剪图 + 图例中译 + 解读 + 注意事项；
- [ ] 方法引用链接可打开，DOI 与文献匹配；
- [ ] 公众号文有配图、有故事线，不是论文缩写；
- [ ] 讲稿 3–5 分钟能念完，发表信息齐全。

最后向用户报告：输出目录、6 个文件、任何不确定/需人工复核的地方（图裁剪、参考文献链接、作者团队）。

## 资源导航

| 需要时读 | 文件 |
|---|---|
| JSON 字段与完整示例 | `references/schemas.md` |
| 翻译规范、术语、长句处理 | `references/translation.md` |
| 读图方法、面板拆解、常见坑 | `references/figures.md` |
| 方法溯源与文献核验 | `references/methods.md` |
| 公众号文章结构/语气/标题 | `references/wechat.md` |
| 组会讲稿结构与时间分配 | `references/talk.md` |
| 交付前检查清单 | `references/qa.md` |
