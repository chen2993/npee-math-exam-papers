# 题库的 Git 版本管理

本文档回答一个具体问题：**`.npee-math-papers/` 怎么进 git，2 GB 的 PDF/PNG 怎么办。**

## 一、三层资源，三种处理

`.npee-math-papers/` 不是一团数据，而是三层性质完全不同的东西：

| 层 | 内容 | 体量 | 性质 | 进 git？ |
| --- | --- | --- | --- | --- |
| 权威文本 | `papers/**/*.yaml`、`registry.json`、`release.json`、`index/` | **3.1 MB** | 题库**本身**；`content_hash` 由它派生 | ✅ **已跟踪** |
| 来源 PDF | `sources/**/source.pdf` | 1115 MB | 溯源证据；每份由 `source.json` 的 `sha256` 锁定 | ⚠️ 见下 |
| 页面图 | `captures/**/pages/*.png` | 879 MB | 从来源 PDF 渲染出的证据 | ⚠️ 见下 |

**关键前提**：`papers/` 才是题库，3.1 MB 而已。另外两层是**证据**，不进主对象库也不影响题库可用性。

## 二、大文件的四种方案与实测结论

| 方案 | 是否可行 | 实测/理由 |
| --- | --- | --- |
| **A. 直接 git 提交** | ❌ | 单文件最大 81.3 MB（GitHub 硬限 100 MB，警告线 50 MB）；而 `.git` 已达 **1.7 GB**——那正是首次提交把 `agent/workspace/**/source.pdf` 提进历史的结果。大二进制进历史后**无法删除**，只会永久累加 |
| **B. Git LFS** | ✅ 技术上已验证 | 本机 `git-lfs 3.5.1` 已安装、filter 已配置。实测：一条 `source.pdf` 加入暂存后变成 **127 字节指针**而非原文件（`oid sha256:…`）。规则已写入 `.gitattributes` |
| **C. 外部只读归档** | ✅ 推荐用于 PDF | 60 份 PDF 各自有 `sha256` 记录，位置不再是唯一凭据；把 PDF 放到网盘/对象存储/离线盘，保留 `source.json` 即可验证完整性 |
| **D. 不进 git，仅保留元数据** | ⚠️ 对页面图当前不可行 | 见第三节 |

### LFS 的额度现实

- 语料约 **1994 MB**；
- GitHub 免费 LFS 额度是 **1 GB 存储 + 1 GB/月流量**；
- 因此 LFS 对全部 2 GB **超出免费额度**（超量需付费，或改用自建 LFS 服务器）。

结论：**LFS 规则已就位且可用，但要不要用它托全部 2 GB 是个成本决定**，不是技术障碍。

## 三、页面图当前不可复现（这是真正的缺口）

来源 PDF 有 `sha256`，页面图**什么都没有**：

```
capture.json 现有字段：
  schema_version, capture_id, bundle, series_key, year, subject,
  source_id, question_pages, answer_pages, exclude_pages, status, notes
缺失：页面图哈希、渲染 DPI
```

而页面图是**渲染产物**——`service/capture.py` 用 `pdftoppm` 按 DPI 生成，`DEFAULT_DPI = 220`。

后果：**页面图删了就回不来**，因为

1. `capture.json` 没记 DPI，同一次捕获用不同 DPI 会得到不同图；
2. 没有页面图哈希，无法验证重新渲染出的图与当初一致。

因此现在**不能**把 `captures/` 当作"可重建的缓存"丢掉。要让它可丢弃，得先补两件事：

| 补什么 | 效果 |
| --- | --- |
| `capture.json` 记录 `dpi` 与 `pdftoppm` 版本 | 让渲染**可复现** |
| 逐页记录图片 `sha256` | 让重渲染结果**可校验** |

补完之后，`captures/` 就能降级为缓存：clone 后按需从 `sources/` 重渲染，并用哈希自检。

## 四、当前落地状态

| 项 | 状态 |
| --- | --- |
| `papers/`、`registry.json`、`release.json`、`index/` | ✅ **已提交** |
| `.gitattributes` | ✅ 新增：`* text=auto eol=lf` + PDF/PNG 标记 binary + LFS 规则 |
| `.gitignore` | ✅ 注释改写，说明三层各自归属 |
| `sources/`、`captures/` | ✅ 忽略，**不上传 GitHub**；LFS 规则已就位，若将来要托管可启用 |

### 仓库历史重置（2026-09-14）

原 `.git` 有 **1690 MB**，其中绝大部分是首次提交时误入的
`agent/workspace/**/source.pdf`（最大 81.3 MB）。这些 blob 无法通过普通删除移除。

由于仓库**从未推送**（远端无任何分支），重置代价最低，因此：

1. 把原 `.git` 打包为 `~/Desktop/jjb-git-history-20260914-181514.tar.gz`（1.65 GB），
   并生成 `.sha256` 校验文件；
2. **验证归档可恢复**：解压后 4661 文件 / 1,772,379,423 字节与原 `.git` 逐字节一致，
   `git fsck` 退出 0，`git log` 与 4123 个文件树均可读出；
3. 删除 `.git`，`git init -b main` 重建，重新配置 `origin` 与 `git lfs install --local`；
4. 以当前工作区为**初始版本**提交（591 文件）。

| 指标 | 之前 | 之后 |
| --- | --- | --- |
| `.git` 体积 | 1690 MB | **1.6 MB** |
| 提交数 | 1 | 1（全新根提交） |
| 已跟踪文件 | 4123（含 81 MB PDF） | **591**（无 >1 MB 文件） |
| 题库 | 未跟踪 | **321 套全部跟踪** |

## 五、为什么必须锁 LF（实测）

Windows 上 `core.autocrlf=true` 会把 LF 改写为 CRLF。题库 YAML 用字面量块存 LaTeX，
所以**换行曾经是内容**。实测结论：

- 全库 14258 个字面量块，**解析后 0 个字段仍含换行**（ruamel 已把换行归一化）；
- 因此 CRLF **不影响** `content_hash`（实测 LF/CRLF 两种字节得到的哈希相同）；
- 但原始**字节**会变，让工作区依赖各人本机配置。

`.gitattributes` 的 `* text=auto eol=lf` 让字节也可复现——不是靠侥幸，而是由构造保证。

## 六、验收（实测命令）

```powershell
python build\git-store-verify.py        # 从 git 索引取出全部 321 套并重新校验
python build\git-checkout-roundtrip.py  # 字节层 + 语义层往返一致性
python build\crlf-impact.py             # CRLF 是否影响 content_hash
python build\provenance-check.py        # 60 份 PDF 的 sha256 是否全部匹配
python build\large-file-audit.py        # 三层体量与可复现性审计
```

实测结果：321 套卷从**索引**解析全部通过、0 哈希不符、7062 题；git 往返逐字节一致；
60 份 PDF 哈希全部匹配。

## 七、已知的仓库历史问题

`.git` 有 **1.7 GB**，其中大部分是首次提交时误入的 `agent/workspace/**/source.pdf`
（最大 81.3 MB）。这些文件**已从工作区删除**，但 blob 仍留在历史里。

要真正瘦身需要重写历史（`git filter-repo` 或 BFG），那会改写所有 commit hash。
仓库目前只有 **1 个提交**、且尚未推送（`origin/main` 不存在），因此**现在重写代价最低**——
如果要做，就应该在首次推送之前做。
