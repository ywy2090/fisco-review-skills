---
name: fisco-verify-findings
version: 1.2.0
description: 独立复核 review finding 是否真实存在——对每条结论给出固定 revision 上的代码证据、可重放的复现命令与原始输出，并给出 confirmed / confirmed_symptom_mechanism_differs / refuted / stale / unreproducible / undecidable 判定。Use when 需要确认 reviewer、Copilot、handoff、审查报告或自己审出的问题是否真的存在（真伪、是否已在当前 head 被修掉、能否复现、影响范围到底多大），或在修复、回复、发布 review 之前先把证据落实。Not for 修改代码（fisco-respond / fisco-handle-reviews）或产出新的 review（fisco-review / fisco-review-pr）。
---

# FISCO-BCOS finding 独立复核

review 里的一条 finding 是**声称**（claim），不是事实：行号会随 head 漂移，机制会被讲错，前提会过期，结论可能是对的但影响被夸大。本 skill 只回答一个问题——**这条声称在某个固定 revision 上是否成立、证据是什么、别人怎么重放**。修不修、怎么回复是 `fisco-respond` / `fisco-handle-reviews` 的决定，本 skill 的输出是它们的输入。

## 核心原则

- **完整证据链是判定的门槛，不是加分项**。每条核实的问题都要同时给出：①**代码位置**——pin 上的 `git show <PIN>:<path>:<lines>` 引用（声称"缺失/无此类代码"时用 pin 锚定的 `git grep`/`git log` 扫描），让人能跳到那一行自己看；②**可复现的路径**——`repro`（command/expected/observed/exit_code）从干净 checkout 可重放，让人能自己跑出同样的结果。两端齐备才叫核实；只有位置没有路径是"我读了代码"，只有路径没有位置是"它坏了但不知坏在哪"，两者都只能算 hypothesis。代码位置一端任何判定都不可省（缺代码的声称用扫描锚点兜住）；唯一允许断链的判定是 `undecidable`，断的只能是可复现路径一端，且必须在 `missing_inputs` 写明缺什么输入才能把链补全。
- **判定必须能被第三方复算**。结论要么绑 `git show <PIN>:<path>` 的原文，要么绑一条别人能重放的命令加原始输出。两者都没有的东西只能写成 hypothesis，不能写成结论。
- **反证优先**。先花力气证伪，再接受成立。接受一条假 finding 会改坏代码并在下一轮被重开；无证据地拒绝一条真 finding 会让 round 不收敛。两个方向的错都只能靠证据避免，不能靠语气。
- **只对 pin 负责**。head 一变（新 commit / force-push / rebase），行号与结论同时失效。round 之间必须重跑，不能用上一轮结论代替。
- **区分"症状"与"机制"**。复现出异常只证明症状真，不证明 reviewer 说的原因对；机制要单独用定向干预（mutation probe）确认。
- **不改生产代码**。复现只在仓库外隔离 worktree 内做，允许 test-only；动了被测代码就是 mutation probe，必须标注、可逆，还原后 `git diff` 为空。

## 路径与兼容

```text
SKILL_DIR  = realpath(本 SKILL.md 所在目录)
SKILLS_ROOT = ${FISCO_SKILLS_ROOT:-SKILL_DIR/..}
```

判定产物被 `fisco-handle-reviews`（`validity` / `defect_shape` 字段）与 `fisco-respond`（triage 输入）消费的设计意图见 `references/report.md` 的交接表。**注意这是接口约定，不是已落地的自动接线**：目前 `fisco-review-pr` / `fisco-handle-reviews` 里没有任何代码引用本 skill 的产物，搬运与降级仍需人工或调用方显式执行。写本 skill 时对齐的 sibling 版本：`fisco-handle-reviews 1.10.0`（`validity` ∈ valid/invalid_premise/pending，`classification` ∈ fix/reply/resolve_candidate/historical/pending_decision，`defect_shape` 六值）、`fisco-respond 2.0.0`、`fisco-review-pr 2.13.0`。`fisco-review-shared/scripts/init_artifact_dir.sh` 存在时复用其受限目录与 per-PR 锁（锁需调用方释放，见 `references/intake.md`）。

## 执行路由

1. 读取 `references/intake.md`：版本横幅、环境自检、建立 `VERIFY_PIN`、归一化 finding 来源、创建受限 artifact 目录与隔离 repro worktree。
2. 逐 finding 判定前读取 `references/method.md`：子声称分解、反证顺序、复现阶梯、mutation probe、本仓库常见假阳性/假阴性形态、判定树。
3. 需要具体复现命令时读取 `references/repro-recipes.md`。
4. 落 JSON 与报告、跑 validator、交接给下游时读取 `references/report.md`；需要填表样例时读 `references/example-verification.json`。

不得一次性把所有 reference 读入上下文。

## 判定

| verdict | 含义 | 证据义务 |
|---|---|---|
| `confirmed` | 缺陷在 pin 上存在且可触发 | 复现命令 + 原始输出（expected vs observed）；四个子声称均未被证伪 |
| `confirmed_symptom_mechanism_differs` | 症状为真，但 reviewer 给的原因/影响/位置不对 | 同上 + `mechanism_correction` 说明真实机制 |
| `refuted` | 声称的行为在 pin 上不发生 | 正向反证（前提不成立 / 上游已守卫 / 行为与声称相反）+ repro（反证的重放：观察到声称行为不发生）+ 证伪尝试记录 |
| `stale` | 曾为真，pin 上已修 | `fixed_at` 修复 commit + pin 上修复存在的正向证据；repro 带"修复已生效"的核对重放（结构证明 `claim_kind=structural` 即可） |
| `unreproducible` | 试过但触发不了 | repro 带"跑过但未触发"的命令与原始输出 + 证伪尝试清单 + 边界；**不得**据此 recommend fix（要修只能记 hardening） |
| `undecidable` | 缺关键输入（外部参考实现、人类决策、不可得环境） | `missing_inputs` 明确缺什么输入才能补上可复现路径（唯一允许断链的判定） |

`unreproducible` 与 `refuted` 的区别是全部意义所在：前者是"我没让它响"，后者是"我证明了它不响"。混用会把一条真缺陷变成"已排除"。

## 不可下沉的硬门禁

### 证据与 revision

- 无 pin 不判定。证据只读 `git show <PIN>:<path>`，禁止读工作区文件或可变分支冒充该 revision。代码位置是证据链的第一端：每条 finding 的 `evidence` 与 `location` 子声称都要有指向 pin 代码的锚点（`git show` 引用，或声称"无此类代码"时 pin 锚定的 `git grep`/`git log` 扫描）；测试日志、URL、评论链接只是 locator，不能充当代码位置。
- reviewer 给的行号只是提示：必须按 symbol 与相邻内容在 pin 上重定位后再引用。本仓库已有实例：`OpstackExecutor.h` 的无条件 accessList 拒绝在 `13cfac80` 位于 482 行，在当前 pin 上是 748 行（+266 漂移），而 745 行已经是取代它的逐元素绑定调用——照抄旧行号会读到完全无关的代码。
- 每条 `git show` 引用必须指向 pin、路径必须是 pin 上的 blob、行号必须在文件内；写在反引号里的代码引用还必须真的出现在所引位置（`scripts/validate_verification.py --repo .` 会强制这些，并把模式标成 `repo-checked`）。

### 复现

- 无复现不下判定：`repro` 是证据链的第二端，除 `undecidable` 外每个 verdict 都必须带（`stale` 带修复已生效的重放，`unreproducible` 带"跑过但未触发"的命令与输出）。读代码得到的只能是 hypothesis。
- 复现必须能从干净 checkout 重放：给出 setup、命令、expected、observed（原始输出）、退出码，并声明 `claim_kind`（`structural` / `behavioural`）——行为性声称不允许用 `tier: static` 结案。
- 复现不得修改被测生产代码；需要修改时按 mutation probe 处理：记录 `file` 与 diff、验证"症状消失/出现"、还原、并确认 `git diff` 为空。
- **已有测试不是覆盖证据**：必须确认那条断言真的钉住了声称的不变量（本仓库教训：断言了 outcome 没断言 invariant）。
- 环境不可得时记 `unreproducible` + 边界，不得升级为 `refuted`。

### 范围

- 显式判定可达性：live production path（附 `git grep` 调用方证据）/ 仅测试或未来 PR 接线 / 死代码。真缺陷在未接线代码上仍然为真，但 scope 必须写明，不能让"未接线"把真缺陷降级或把假缺陷升级。
- 类别性 finding（同一规则在多个位点实例化）要扫描同类位点，不能只判 reviewer 点名的那个。

### 产物与边界

- 本 skill 不产出 fix commit、不改 PR 分支、不发 GitHub、不 resolve thread。发现"确认且需修"只输出 `recommendation=fix` 交接给 `fisco-respond` / `fisco-handle-reviews`。
- 只出报告也可以：用户问"这问题是不是真的"时，交付的是判定与证据，不是修复。
- 自己产出的 review（`fisco-review` / `fisco-review-pr`）建议在发布前逐条过本 skill，把 `refuted` / `stale` 的条目挡在 PR 之外——这是本 skill 的推荐用法，不是已存在的发布硬门禁。

## 输出

最小产物是 `$ARTIFACT_DIR/verification_$PR.json`（无 PR 号时 `verification_<topic>.json`），必须能通过：

```bash
python3 "$SKILL_DIR/scripts/validate_verification.py" "$ARTIFACT_DIR/verification_$PR.json" --repo .
```

必含 `schema_version: 1`、`pin{head,base,ref,verified_at}`、`source`、非空 `items[]`；每项含原样引用的 `claim_verbatim` 与 `source_ref`、四个子声称各自判定、`verdict`、`reachability`、`evidence`（含代码位置锚点）、`repro`（含 `claim_kind`、`exit_code`；`undecidable` 可为 null 但须在 `missing_inputs` 指明断链端）、`falsification_attempts`、`boundary`、`residual_risk`、`recommendation`。字段全集、报告模板与下游交接见 `references/report.md`。

一定带 `--repo`：不带时 validator 只做结构校验（输出 `shape-only`），行号、路径、代码引用与修复血缘全部不检查。`repo-checked` 通过表示"证据存在且指向该 revision"；它**不**证明引用的代码内容或 `observed` 日志本身真实——那一步靠人复核内容，也是为什么复现命令要能被人重跑。

最终回复至少给出：PIN、各判定数量、`confirmed` 项的复现命令与 observed 摘要、`refuted`/`stale` 项的反证要点，以及本次复核未覆盖的边界。
