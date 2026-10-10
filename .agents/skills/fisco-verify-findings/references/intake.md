# 入口：pin、来源归一化、工作区

只在开始一轮复核时读取。

## 启动

先输出横幅，再自检：

```text
fisco-verify-findings v1.2.0 (2026-10-08)
════════════════════════════════════════════════════════════
🔍 VERIFY START · fisco-verify-findings · <YYYY-MM-DD HH:MM>
   <PR #N | report 路径> · <finding 条数> 条待复核
════════════════════════════════════════════════════════════
```

```bash
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' \
  && command -v jq >/dev/null && python3 -m py_compile "$SKILL_DIR/scripts/validate_verification.py" || {
  echo "❌ 环境自检失败：需要 Python 3.8+、jq 与可编译的 validator"; exit 1; }
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)
[[ "$REPO" == "FISCO-BCOS/FISCO-BCOS" ]] || echo "⚠️ 非 FISCO-BCOS 主仓库（$REPO）：静态判定仍可做，PR 来源需在仓库内运行"
```

来源是 PR 时还需要 `gh auth status`；纯本地 report / 已有 artifact 复核不依赖 `gh`。

## 建立 pin

复核的全部意义绑定在这一个 revision 上，所以第一步永远是 pin：

```bash
eval "$(bash "$SKILL_DIR/scripts/verify_env.sh" "$PR")"          # 从 PR 取 head/base
eval "$(bash "$SKILL_DIR/scripts/verify_env.sh" --head "$OID" --base "$BASE_OID")"   # 从 OID 取
```

脚本产出 `SKILL_DIR`、`VERIFY_PIN` / `VERIFY_BASE_PIN`（不可变 refs，fetch 后核对 OID 一致）、`umask 700` 的 `VERIFY_ROOT`（scratch）与 `ARTIFACT_DIR`（证据，有 shared `init_artifact_dir.sh` 时复用 per-PR 目录与其锁）、`RUN_ID`，以及 `REPRO_WORKTREE`（detached at pin）。

约束：

- 复核期间 head 变了，本轮全部判定失效：重跑 pin、重定位行号，再引用旧结论。
- 证据只许 `git show "$VERIFY_PIN":<path>`。工作区文件可能属于另一个分支，禁用。
- 主工作树保持干净：所有产物落 `$ARTIFACT_DIR`，所有 repro 落 `$REPRO_WORKTREE`。
- **构建目录的 revision 陷阱**：主树 `build/` 只对主树当前 checkout 有效。要用它跑测试，必须先确认 `git -C <build 对应的 checkout> rev-parse HEAD` 等于 pin；否则在 `$REPRO_WORKTREE` 里单独配置并构建，否则你测的是另一个 revision。

## 归一化 finding 来源

每条 finding 落成一个 item，先只填 `id` / `source_ref` / `claim_verbatim`，判定留到 method。

| source | 取法 | `source_ref` 写法 |
|---|---|---|
| `pr_comment` | inline review 评论、review body、issue comment 三类都要分页拉全（见下方命令） | `comment <id>` 或 thread URL |
| `review_artifact` | `review_$PR.json` 的 `comments[]`：`{body, path, line, side}`，`body` 即 claim | `<artifact>:comments[<i>]` |
| `review_handoff` | `review_handoff_$PR.json`，只取 `status=open` | `handoff #<finding id>` |
| `report_md` | 人工/总览表（如 `pr5544_all_findings.md`） | `<file>:<行或表行>` |
| `self_review` | 自己即将发布的 `review_$PR.json` | `self review #<id>` |
| `advisory` | Copilot / bot / 静态分析评论 | `comment <id>` |

三类来源都要分页拉全，别只看第一页（少拉一页会把"没这条 finding"和"没读到"混起来）：

```bash
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
# inline review 评论（thread 内回复用 in_reply_to_id 关联）
gh api --paginate "repos/$REPO/pulls/$PR/comments?per_page=100" \
  --jq '[.[] | {id, user: .user.login, path, line: (.line // .original_line), side, in_reply_to_id, body}]'
# review body（每轮的总体意见与 scorecard）
gh api --paginate --slurp "repos/$REPO/pulls/$PR/reviews?per_page=100" \
  --jq '[.[][] | {id, user: .user.login, state, commit_id, submitted_at, body}]'
# issue comments（PR 对话区的追加要求）
gh api --paginate --slurp "repos/$REPO/issues/$PR/comments?per_page=100" \
  --jq '[.[][] | {id, user: .user.login, created_at, body}]'
```

装在同一 `$SKILLS_ROOT` 下的 `fisco-review-shared/commands.md` 有更完整的 thread 差集与 pin 建立片段，存在时可复用；不存在时上面的命令足够独立完成复核。

抽取纪律：

- `claim_verbatim` **原样引用**，含 severity 前缀和 reviewer 的措辞。改写会让一条假 finding 在判定前就被悄悄"修好"（`fisco-review-pr` 的 finding 形如 `⚠️ [IMPORTANT] [BLOCKING] <标题>` + `**影响**` / `**证据**` / `**建议**`，整段引用）。
- 一条 finding 捆绑多个缺陷时拆成多个 item，共用 `source_ref` 并在 `residual_risk` 里说明拆分依据——但**不要**把一条 finding 拆成一句话一个 item，判定要跟着 reviewer 的论述单位走。
- 来源给的 `path`/`line` 只当提示存进子声称 `location`，不当事实。
- 来源的 severity 存进报告但不参与判定：本 skill 判真伪与范围，不判"该不该修"。

## 工作区与清理

`verify_env.sh` 已经把 scratch 与证据分开：`VERIFY_ROOT` 里只有 repro worktree（可删），`ARTIFACT_DIR` 是判定证据（必须留）。清理时**只删 `VERIFY_ROOT`**：

```bash
# 复核结束后（只清理本轮 OWNERSHIP marker 标识的路径）
git worktree remove --force "$REPRO_WORKTREE"
rm -rf "$VERIFY_ROOT"
# ARTIFACT_DIR 是证据：保留，或复制到你希望长期保存的位置后再删临时目录
```

用了 shared per-PR 目录时，`init_artifact_dir.sh` 拿的是 per-PR 锁且**不会自动释放**——不释放会让同 PR 的下一次 `fisco-review-pr` / `fisco-handle-reviews` 直接报 `PR artifact directory is locked`。进来就装上 trap：

```bash
# 仅当复用了 shared per-PR 目录时（verify_env.sh 会在 stderr 打印这一行）
trap 'bash "$SKILLS_ROOT/fisco-review-shared/scripts/release_artifact_lock.sh" "$ARTIFACT_DIR" "$RUN_ID"' EXIT
```

`git worktree remove` 失败时报告残留路径，禁止 `git worktree prune` 影响其它会话。artifact 是判定证据，`verification_$PR.json` 不随临时目录删除。

## 不适用

- 用户要的是"修掉这个问题"→ `fisco-respond` / `fisco-handle-reviews`。
- 用户要的是"帮我审这个 PR"→ `fisco-review` / `fisco-review-pr`。
- 复核途中顺手发现的新问题：记成独立 item（`source_ref` 指向本轮复核），不要混进被复核 finding 的判定里。
