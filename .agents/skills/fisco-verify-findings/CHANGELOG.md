# fisco-verify-findings Changelog

Semver policy: **MAJOR** = 判定语义或证据门禁的破坏性变更；**MINOR** = 新增判定、门禁或配方；**PATCH** = 措辞、链接、预算调整。

## [1.2.0] - 2026-10-08

新增"完整证据链"门禁（用户要求：对所有核实的问题，证据链必须含 ①代码位置 ②可复现的路径）。两端齐备才收判定；`undecidable` 是唯一允许断链的判定，且只能断可复现路径一端，`missing_inputs` 必须写明缺什么输入才能把链补全。

### Added
- **完整证据链**（核心原则首条 + 硬门禁）：每条 finding 同时给出①代码位置（pin 上 `git show <PIN>:<path>:<lines>` 引用；"缺失/无此类代码"类声称用 pin 锚定的 `git grep`/`git log` 扫描做锚点）与②可复现路径（`repro` 命令 + expected/observed/exit_code，干净 checkout 可重放）。"只有位置没有路径"= 我读了代码，"只有路径没有位置"= 知道坏不知道坏在哪，都只能算 hypothesis。
- validator 机器门禁（`--repo` 之外的 shape-only 也生效）：
  - item `evidence` 与 `location` 子声称必须含至少一个代码位置锚点（`git show` 引用或 pin 锚定扫描）；纯 locator（测试日志、URL、评论链接）不算位置；
  - `repro` 从"仅 confirmed/CSMD/refuted 必填"收紧为**除 `undecidable` 外全 verdict 必填**：`stale` 带"修复已生效"的重放（结构证明 `claim_kind=structural` 即可，不必为已修复的行为硬凑构建），`unreproducible` 带"跑过但未触发"的命令与原始输出——这正是它与 `refuted` 的分界线，之前只靠 `falsification_attempts` 文字承载；
  - `undecidable` 的 `missing_inputs` 机器上仍只强制非空；"写明缺什么输入才能补链"是文档义务，validator 的错误消息会提示。
- `references/method.md`：复现阶梯前置完整证据链规则；明确 `claim_kind` 标的是 repro 实际证明的事实形态（stale 的修复核对标 `structural`），反向冒充（行为结论用 static 收）仍被拒。
- `evals/evals.json` 新增 `complete-evidence-chain` 场景（evals 总数增至 12 个）。

### Changed
- `references/example-verification.json` 的 stale 项补上 `repro`（tier=static 结构核对 + pin 上真实 `git show` 输出），原来 `"repro": null` 在新门禁下不再通过。
- skill-creator 准则复审后同步：SKILL.md 判定表 `stale`/`unreproducible` 行补上 repro 义务（此前表格滞后于新门禁）；method.md 交付前自检措辞对齐"只能断可复现路径一端"；再次清除 `scripts/__pycache__`。
- 第二轮独立盲审（引文逐条复核）后修复：判定表 `refuted` 行与 method.md 补上 refuted 的 repro 形态（反证的重放）；report.md 的 undecidable 义务如实区分"机器强制非空 / 文档要求写明"；扫描锚点的裸 hex token 必须解析到本 artifact 的 pin（`git grep -n foo deadbeef` 不再充当代码位置）；historical_evidence 引用补 blob 类型与行范围校验；`exit_code` 拒绝布尔冒充整数；report.md schema 示例的 `--gtest_filter` 残留改为 Boost.Test 形态；intake.md 启动横幅升 v1.2.0；sibling 版本声明刷新（fisco-respond 实为 2.0.0）；清除 `.DS_Store` 并加入 `.gitignore`。
- `references/report.md` 字段义务表新增完整证据链条目，schema 示例补 `claim_kind`。

### 验证
- `scripts/test_validate_verification.py`：70 个用例通过（证据链门禁回归 9 个：URL-only 证据被拒、locator+引用通过、pin 扫描锚点通过、外来 hex 扫描被拒、pin 前缀扫描通过、location 子声称断链被拒、stale/unreproducible 缺 repro 被拒、undecidable 断链但写明缺口通过；另 historical 行范围/目录引用 2 个、exit_code 布尔冒充 1 个）。
- `references/example-verification.json` 在真实仓库上通过 `repo-checked`（sha256:00a5b8d4760d）。

## [1.1.0] - 2026-09-10

两轮独立审查（skill-creator 准则符合性 + 对抗性门禁测试）后的修复。所有结论在改动前都先在真实仓库上复核过；审查报告里有一条断言（`b5c05a1e^` 不含 `opstack-executor/`）经核对为假，未采纳。

### Fixed
- **BLOCKER** `verify_env.sh` 用 `awk -F'"'` 解析 shared init 的 `%q` 输出，普通路径下取到空串：per-PR 目录与锁从未生效，却已由 init 脚本加锁且无人释放，会让同 PR 的下一次 `fisco-review-pr` / `fisco-handle-reviews` 报 `PR artifact directory is locked`。改为按 family 惯例 `eval` 解析，导出 `RUN_ID`，并打印释放命令；`references/intake.md` 补 trap 说明。
- **IMPORTANT** validator 不接受 `$VERIFY_PIN`（本 skill 自己文档里用的变量），导致照文档写证据反而假失败。已接受 `$VERIFY_PIN` / `$VERIFY_BASE_PIN` / `$HEAD_OID` / `$BASE_OID`。
- **IMPORTANT** 引用门只覆盖 `evidence` 与 `historical_evidence`：四个子声称、`reachability`、`resolution_evidence` 里的 `git show` 引用完全未解析；同一字符串里的第二个引用也不解析。现覆盖全部证据位点，并用 `finditer` 检查每一个引用。
- **IMPORTANT** `repro-recipes.md` 的 gtest 段是错的：`opstack-executor-tests` 与 `bcos-evm-*` 都是 Boost.Test（链接 `Boost::unit_test_framework`），`--gtest_filter` 不适用；示例里的 suite/case 名多为臆造且在 pin 上不存在。已按实测重写，并明确"选择器必须每次在 pin 上确认"。
- **IMPORTANT** `pin.head` 未在 `--repo` 中校验：pin 不存在时所有引用都会因路径失败而误报。现单独校验 pin 存在性，且失败后降级为 shape 检查以免级联误报。
- **IMPORTANT** 大意为"证据位置对就行"的内容漏洞：引号内的代码引用若在所引位置不存在，现在会被拒（跨行引用按去空白比较，shell 命令与变量插值豁免）。这是对抗测试指出的"引用只证位置、不证内容"。
- **IMPORTANT** `stale` 的双向证据此前只是文档：`fixed_at` 现须是 `--repo` 中的 commit 且为 pin 的祖先；`resolution_evidence` 须含可解析引用；`historical_evidence` 不得引 pin 自身。修复前 revision 与修复 commit 不同 lineage（rebase/force-push）时必须写 `historical_evidence_note`。
- **IMPORTANT** `undecidable` 可以 `recommendation=fix`；`totals` 对未出现的 verdict 键形同虚设、非对象直接跳过；非对象子声称触发 `AttributeError` 而非门禁消息；多处用真值判断而非 `strip()`（`id`/`source_ref`/`pin.ref`/`fixed_at` 等空白串可通过）。均已修复。
- **IMPORTANT** `--repo` 缺省时的降级没有对外信号：现在输出明确标注 `shape-only` / `repo-checked`，`SKILL.md` 说明该指令为何承重。
- **SUGGESTION** 未标 `$VERIFY_PIN` 的模糊短前缀可解析到别的 revision；现用 `rev-parse` 消歧并拒绝 ambiguous 前缀。目录（tree）引用冒充文件行号的情况也已拒。
- **SUGGESTION** 兼容性声称过度：原文称 sibling skill 已消费本产物，实际仓库内无任何引用。改为明确标注"接口约定、尚未接线"并列出对齐的 sibling 版本；`fisco-review-pr` 的 `critical_verification` 映射补齐。
- **NIT** `SKILL.md` 行号漂移的算术自相矛盾（745 对 +266）；按实测改为 482 → 748（+266），745 为取代它的绑定调用。
- 删除随包发布的 `scripts/__pycache__`，加 `.gitignore`；四个 reference 补齐 family 的"只在…时读取"首行；`report.md` 的字段义务表与 validator 实际强制项对齐（原文有 4 处低估、3 处高估）。

### Changed
- `repro` 新增 `claim_kind`（`structural` / `behavioural`）与 `exit_code`：行为性声称配 `tier=static` 现被直接拒绝——此前 `method.md` 的这条规则无法被机器执行。
- `evals/evals.json` 增至 11 个场景：修正 3 条 skill 自己不推动的期望（未接线 scope 的下游承接、`stale` 不可发布、drift 场景的 lineage 前提），新增"伪造 artifact 复核"、"未带 `--repo` 校验的 artifact"、"rebase 后的 stale"三个场景。

### 验证
- `scripts/test_validate_verification.py`：59 个用例通过（含 21 个针对上述洞的回归）。
- 对抗测试的 10 个攻击在真实仓库上复测：全部已闭合；两个合法用例（`$VERIFY_PIN` 引用、shape-only 模式）仍通过。
- `references/example-verification.json` 在真实仓库上通过 `repo-checked`（sha256:f4c253ebcd71）；其 `historical_evidence_note` 是本次新门禁在真实 rebase 案例上逼出来的。

## [1.0.0] - 2026-09-10

- 首版：独立复核 review finding 是否真实存在，输出绑定固定 revision 的判定（`confirmed` / `confirmed_symptom_mechanism_differs` / `refuted` / `stale` / `unreproducible` / `undecidable`），每条含可重放的复现命令与原始输出。
- 子声称分解（location / mechanism / impact / premise）：机制被证伪时禁止写成 plain `confirmed`。
- `unreproducible` 与 `refuted` 显式分离：无法触发不等于已排除；`unreproducible` 禁止 `recommendation=fix`。
- `stale` 需双向证据：修复 commit 为 pin 祖先 + `historical_evidence` 证明修复前确为真（"行号挪了"不算 stale）。
- 复现纪律：只读 `git show $PIN:`；repro 允许 test-only，动生产代码必须走 mutation probe 并还原干净。
- `scripts/validate_verification.py`：确定性门禁，机械校验 pin/路径/行范围、各 verdict 的证据义务与 totals 一致性；`--repo` 时对真实仓库生效。
- `scripts/test_validate_verification.py`：回归用例（含 pin 引用、行号漂移、mutation probe 未还原、totals 不一致等）。
- `scripts/verify_env.sh`：建立不可变 pin refs + 受限 artifact 目录 + detached repro worktree。
- `references/example-verification.json`：真实案例（PR #5549 accessList finding 在 pin 上为 `stale`）。
- 首次 with-skill 实测（`stale-line-drift` 场景，真实 PR #5549 双 head）暴露"`stale` 项子声称仍写 confirmed"的语义歧义，据此明确子声称一律相对 pin 判定并加门禁。
