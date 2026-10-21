# 逐段翻译规范

目标：**中文读者能准确理解原文，且每一段都能回到英文原段核对**。不是文学改写，也不是摘要。

## 对齐

- 一个英文 paragraph id → 一个中文段落；不合并、不拆分、不调序。
- 原文段落本身是公式/图表说明时，保留公式或 `Fig. 1` 引用，中文只补一句“该式定义……”/“图注说明……”。
- 原文以 `•` 开头的列表项，中文也用 `•` 起行。
- 原文有 `[12]`、`(Fig. 2A)`、`Supplementary Table S1` 这类引用，原样保留；不要改编号。

## 忠实度

- **否定词不能丢**：`did not`、`failed to`、`no significant`、`unlikely` 必须译出。
- **证据强度不能升格**：`may / suggest / indicate / associated with` → “可能/提示/表明/与……相关”，不要写成“证明/导致”。
- **相关 ≠ 因果**：`correlated with` 不能译成“由……引起”。
- **范围不能扩大**：`in Arabidopsis` 不要译成“在植物中”；`in this cohort` 不要译成“普遍而言”。
- **数字/单位/统计量原样**：`P = 0.03`、`n = 128`、`95% CI`、`2.5-fold`、`μM`、`mg kg⁻¹`；不换算、不四舍五入、不补单位。
- **物种/品系/基因名**：按原文大小写与斜体约定；中文里首次出现可写“*NLR* 基因（NLR）”。
- 原文没有的“首次”“重大突破”“显著提高”等评价性词，不要加。

## 术语

- 首次出现的专业术语：中文（English），例如“核苷酸结合位点（nucleotide-binding site, NBS）”。
- 同一术语全文统一；建立自己的小词表，不确定时保留英文。
- 常见固定译法：knockout=敲除，knockdown=敲低，overexpression=过表达，wild-type=野生型，gain-of-function=功能获得，loss-of-function=功能缺失，rescue=回补，transgenic=转基因，haplotype=单倍型，allele=等位基因，locus=位点，mapping=定位，fine-mapping=精细定位，association=关联，replication=复制/重复验证。
- 统计：significant=显著（仅当原文有统计检验），trend=趋势，effect size=效应量，power=检验效能。

## 语言

- 长句拆成 2–3 个中文短句；保持逻辑连接词（因此/然而/此外/相反）。
- 避免“进行了……的研究”“被……所”这类翻译腔；用主动语态。
- 中文标点：全角逗号、句号、分号；英文缩写与数字之间按中文习惯处理。
- 公式：变量保留斜体语义（纯文本无法斜体时用 `d_model`、`QKᵀ` 这类写法），不要写成中文变量名。

## 自查

- [ ] 每个 paragraph id 都有中文，无“待翻译”；
- [ ] 否定、限定、比较对象都还在；
- [ ] 数字、单位、P 值、样本量与原文逐一对应；
- [ ] `Fig./Table/Supplementary` 编号没变；
- [ ] 术语全文一致；
- [ ] 读一遍中文，能复述该段在论证链里的作用。
