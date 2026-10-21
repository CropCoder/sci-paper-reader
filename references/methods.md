# 方法拆解与文献溯源

## 从哪里找

1. `sections[role=methods]`（Materials and Methods / STAR Methods / Online Methods / Experimental Procedures）。
2. 图注里的关键实验条件（n、抗体、软件、统计检验）。
3. 正文 Results 中“we used / performed / analyzed with”的句子。
4. Supplementary Methods、Data Availability、Code Availability。
5. 论文 References：找每个方法的**原始文献**，而不是二手综述。

## 方法清单

按论文实际顺序列，不要按教科书分类。每条判断：

- 是**实验/湿实验**（克隆、转化、酵母双杂交、Co-IP、CRISPR、显微成像、qPCR…）
- 是**测序/组学**（RenSeq、RNA-seq、WGS、ATAC-seq、单细胞…）
- 是**计算/分析**（比对、结构域注释、系统发育、GWAS、机器学习、建模…）
- 是**统计/实验设计**（混合模型、多重检验校正、生存分析、bootstrap…）

只写这篇论文真正用了的；没有用到的通用技术不要凑数。

## 每条写什么

- `what`：一句话原理，非本领域读者能懂。
- `how`：本文的样本/对象/目的；例如“对 312 份小麦材料做 RenSeq，组装 NLRem 以注释完整 NLR”。
- `params`：关键参数、试剂/仪器、软件版本、数据库版本、统计阈值；没有就写“原文未给全”。
- `interpretation`：为什么用这个方法、它能回答什么、局限是什么。
- `used_in`：对应 `Fig. 1` / `Table 2`，方便读者回看。
- `citation`：原始方法文献 + DOI/URL；软件给官方链接/版本。

## 文献溯源

1. 在 `paper.json` 的 `references` 里找到方法名对应的编号（如 `[24]`）。
2. 用编号回查 References 条目；优先引用**首次提出该方法**的论文。
3. 核验 DOI：
   - 打开 `https://doi.org/<DOI>` 看标题/作者/年份是否匹配；
   - 或用 `web_search` 搜“方法名 + 原始文献”；
   - 不确定就写“见原文参考文献 [24]”，不要编一个 DOI。
4. 软件/数据库引用官方论文或官网，不要引二手教程。

## 常见错误

- 把综述当原始方法文献；
- 方法名对、DOI 指错论文；
- 只写“使用某软件”，不写版本/参数；
- 把“结果”写进方法（例如“证明某基因参与抗性”）；
- 把作者自己开发的新方法漏掉——这通常是论文的创新点，必须单列。
