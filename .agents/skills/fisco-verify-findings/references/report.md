# 产物、报告与交接

只在落 JSON、写报告、跑 validator 或交接下游时读取。

## 文件

| 文件 | 作用 |
|---|---|
| `$ARTIFACT_DIR/verification_$PR.json` | 机器可读判定，下游 skill 的输入 |
| `$ARTIFACT_DIR/verify_$PR.md` | 人读报告（reviewer / 自己在 PR 上引用） |
| `$ARTIFACT_DIR/repro.patch` | test-only 复现用例的 diff（若有） |
| `$ARTIFACT_DIR/probe.patch` | mutation probe 的 diff（若有） |

## JSON schema（`schema_version: 1`）

```json
{
  "schema_version": 1,
  "pin": {"head": "<40hex>", "base": "<40hex>", "ref": "refs/verify/pr-5549/head-<oid>", "verified_at": "<ISO8601>"},
  "source": "pr_comment|review_artifact|review_handoff|self_review|issue_comment|report_md|advisory",
  "items": [
    {
      "id": "F1",
      "source_ref": "comment 2601958823 | review_5549.json:comments[0] | handoff #3",
      "claim_verbatim": "⚠️ [IMPORTANT] [BLOCKING] Non-empty accessList blanket-rejected: ...",
      "subclaims": {
        "location":  {"text": "OpstackExecutor.h:479-485", "verdict": "confirmed", "evidence": ["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — 无对照比较"]},
        "mechanism": {"text": "任何非空 list 一律拒绝", "verdict": "confirmed", "evidence": ["git show $PIN:opstack-executor/OpstackExecutor.h:482-483"]},
        "impact":    {"text": "op-geth 合法块被判 INVALID", "verdict": "confirmed", "evidence": ["opstack-executor-tests --gtest_filter=*AccessList* 输出"]},
        "premise":   {"text": "op-geth 接受一致的 list", "verdict": "not_claimed", "note": "本条未依赖外部参考实现行为"}
      },
      "verdict": "confirmed",
      "evidence": ["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — `if (!evmTx.access_list.empty()) return \"accessList is not bound to the signed envelope\";`"],
      "reachability": {"on_live_path": true, "evidence": ["git grep -n envelopeExecutionFieldsMismatch $PIN -- opstack-executor"], "scope_note": "由 OpBlockExecute 的块校验路径调用"},
      "repro": {"tier": "unit_test", "command": "…", "expected": "…", "observed": "…", "exit_code": 1, "duration_s": 12, "modifies_production_code": false},
      "falsification_attempts": [{"attempt": "查上游是否已拒绝该形态", "result": "无上游守卫，检查无条件执行"}],
      "mutation_probe": null,
      "boundary": "单节点、Release、仅 accessList 路径；未跑 OP 主网回放",
      "residual_risk": "未覆盖镜像与信封双向不一致的其它组合",
      "recommendation": "fix",
      "historical_evidence": [],
      "fixed_at": null,
      "resolution_evidence": [],
      "mechanism_correction": [],
      "missing_inputs": []
    }
  ],
  "totals": {"confirmed": 1}
}
```

字段义务（`scripts/validate_verification.py` 强制；带 `--repo` 时另加 revision/路径/行号/引用内容/修复血缘的机械校验）：

- 通用：`id` 唯一且非空、`source_ref` 非空、`claim_verbatim` 原样且 ≥20 字、`evidence` 非空、四个子声称各有 verdict 与证据（`not_claimed` 要写 `note`）、`reachability` 显式且 `scope_note` 非空、`boundary` 与 `residual_risk` 非空、`recommendation` 取值合法。
- 每条证据里的每个 `git show` 引用都要指向本 artifact 的 pin（head 或 base，均为不可变 revision）、路径在该 revision 上是 **blob**、行范围在文件内；写在反引号里的代码片段必须真的出现在所引位置（shell 命令与变量插值除外）。仅 `stale` 的 `historical_evidence` 可引其它 revision，且不得引 pin 自身，引用的 revision 必须可解析。
- 子声称一律相对 pin 判定：`stale` 项的 `mechanism` 在 pin 上必须是 `refuted`（缺陷已修掉），修复前为真的一面写进 `historical_evidence`。任一子声称被判 `refuted` 时 item verdict 不得是 `confirmed`（机制错但症状真 → `confirmed_symptom_mechanism_differs`）；`premise` 为 `undecidable` 时同样不得写 `confirmed`。
- `repro` 必须含 `tier`、`claim_kind`、`command`、`expected`、`observed`、`exit_code`：`claim_kind=behavioural` 不允许配 `tier=static`；`exit_code` 为整数或 `null`（静态检查用 null）。
- `repro.modifies_production_code=true` 时必须有 `mutation_probe`（含 `file`、`diff`、`symptom_disappeared`、`restored=true`、`post_restore_diff_empty=true`）与非空 `repro.worktree`。
- `refuted` / `unreproducible` / `stale` / `undecidable` 都**不得** `recommendation=fix`（`unreproducible` 要修只能记 `hardening`）。
- `stale`：`fixed_at` 为 40-hex OID、在 `--repo` 中是 commit 且是 pin 的祖先；`resolution_evidence` 至少含一条可解析的 `git show` 引用；`historical_evidence` 非空，且当修复前的 revision 与修复 commit 不同 lineage（rebase / force-push）时必须写 `historical_evidence_note` 说明两者关系。
- `undecidable`：`missing_inputs` 非空。
- `confirmed_symptom_mechanism_differs`：`mechanism_correction` 非空。
- `totals` 若给出，必须是对象、键只能是 verdict、且与 `items` 的实际分布完全一致（缺键按 0 比较）。
- `recommendation` 是给下游动作的建议，与 verdict 不是一个维度：`stale` 用 `reject_with_reason`（回复"pin 上已修"）或 `defer`；`confirmed` 用 `fix`；`unreproducible` 用 `hardening` / `needs_human`。
- 未提供 `--repo` 时只做结构校验（输出会标成 `shape-only`）；`repo-checked` 表示证据存在且指向该 revision，**不**表示引用的代码内容或 `observed` 日志本身已核实。

```bash
python3 "$SKILL_DIR/scripts/validate_verification.py" "$ARTIFACT_DIR/verification_$PR.json" --repo "$MAIN"
python3 "$SKILL_DIR/scripts/test_validate_verification.py"   # validator 自身的回归
```

## Markdown 报告

````markdown
# Finding 复核 · PR #<N> @ <head-short-sha>（base <base-short-sha>）

复核时间 <ISO8601>；证据均读自 `refs/verify/pr-<N>/head-<oid>`。
判定：confirmed <n> · mechanism_differs <n> · refuted <n> · stale <n> · unreproducible <n> · undecidable <n>

## F1 [原有 severity] <标题> — **confirmed**

- **原样引用**：> <claim_verbatim>
- **子声称**：location ✅ · mechanism ✅ · impact ✅ · premise ✅|❓
- **证据**：`git show <pin>:<path>:<lines>` — <原文摘录>
- **复现**（tier=unit_test）：`<command>`
  - expected：<声称预测的结果>
  - observed：<原始输出；失败行原样粘贴>
- **证伪尝试**：<试过什么> → <结果>
- **可达性**：live path（`git grep` 命中 <symbol>）；scope：<说明>
- **边界**：<未覆盖的构建/配置/语料>
- **建议**：fix（交接 `fisco-respond`）

## F2 … — **refuted**
- <正向反证，例如：pin 上无任何代码产生该 key（`git grep -n '<lit>' <pin>` 无命中）>
- <证伪尝试清单>
````

报告纪律：每条 finding 的判定要能被没参与复核的人从 `pin`+`command`+`observed` 复算；`observed` 用原始输出而不是转述。

## 下游交接

`items[]` 直接映射到 `fisco-handle-reviews` 的 handling 账本字段：

| verdict | `validity` | `classification` | `defect_shape`（若适用） |
|---|---|---|---|
| `confirmed` | `valid` | `fix`（需修）或 `reply` | `other` / `shared_rule_split` / `silent_default_sibling` / `wire_boundary_gap` / `discriminator_test_gap` / `layout_coverage_gap` |
| `confirmed_symptom_mechanism_differs` | `valid` | `fix` + 在回复里更正机制 | 按真实机制取 |
| `refuted` | `invalid_premise` | `reply`（带反证拒绝） | `other` |
| `stale` | `valid` | `reply`（说明已在 pin 修复） | `stale_claim` |
| `unreproducible` | `pending` | `pending_decision` | `other` |
| `undecidable` | `pending` | `pending_decision` | `other` |

给 `fisco-respond` 的额外输入：`repro.command`/`observed` 就是它回归测试要钉住的行为，`boundary` 是它验证闭合时不能宣称的覆盖面。给 `fisco-review` / `fisco-review-pr` 的用法：发布 review 前对本轮 `items[]` 跑一遍，`refuted` 与 `stale` 的条目都不要发布。`fisco-review-pr` 的 CRITICAL 独立验证字段（`critical_verification` ∈ confirmed/disproved/inconclusive）可由本表映射：`confirmed` → `confirmed`，`refuted` → `disproved`，`unreproducible` / `undecidable` / `stale` → `inconclusive`（不要用它填 `confirmed`）。

## 保留

`verification_$PR.json` 是判定证据，不随临时目录删除、不做 wildcard 清理；跨会话继续复核时按 PR 号复用它，head 变了则整轮重跑而不是增量修补结论。
