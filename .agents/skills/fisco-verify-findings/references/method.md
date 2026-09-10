# 判定方法

只在逐条判定 finding 时读取。

每条 finding 都走这里的步骤。不要跳步，也不要一次把多条 finding 混在一起判。

## 1. 拆成子声称

reviewer 的一段话通常捆了四件事，它们可以各自为真或为假。逐条判定，最后才合成 verdict：

| 子声称 | 在问什么 | 需要的证据 |
|---|---|---|
| `location` | 说的代码位置在 pin 上对不对 | `git show $PIN:<path>:<lines>` 原文 + 相邻 symbol |
| `mechanism` | 说的原因对不对 | 定向干预（mutation probe）或等价的因果证据 |
| `impact` | 后果与严重性对不对 | 触发路径 + 可观察后果；"会导致 X"要有 X 的观察 |
| `premise` | 支撑论证的外部事实对不对（op-geth 行为、链接语义、配置默认值、调用方契约） | 独立查证（参考实现/构建规则/代码），**不能靠论证读起来通顺** |

真实例子（PR #5549 accessList，`review_5549.json` 首条）：

```text
claim_verbatim: "⚠️ [IMPORTANT] [BLOCKING] Non-empty accessList blanket-rejected:
                 legitimate EIP-2930 txs can never land …"
location  → 13cfac80:opstack-executor/OpstackExecutor.h:479-485 确有该检查      confirmed
mechanism → `if (!evmTx.access_list.empty()) return "..."` 无任何对照比较       confirmed
impact    → 需给出"合法 list 被拒"的可观察后果（测试或 trace）                  需复现
premise   → "op-geth 对一致的 list 不拒" 需独立查证参考实现或 fixture          需查证
```

机制被证伪但症状为真时，verdict 走 `confirmed_symptom_mechanism_differs` 并写 `mechanism_correction`——下一轮 reviewer 重读的是他自己写的因果，讲错的原因照抄进回复会在 round 里被打回。

**子声称一律相对 pin 判定**，不相对"历史上"。所以 `stale` 项的 `mechanism` 在 pin 上是 `refuted`（缺陷已被修掉），"当时为真"那一面由 `historical_evidence` 承载；不要在 `stale` 项上写 `mechanism: confirmed`。

## 2. 先证伪

拿到 finding 的第一反应是"怎么让它不响"，而不是"怎么让它响"。按下面顺序查，任一命中就说明声称不成立或需要改写：

1. **上游守卫**：有没有更早的检查/解码/准入已经排除该输入？`git grep -n <symbol> $PIN` 找所有入口与前置校验。
2. **调用方前置条件**：调用方是否已经保证该状态不可能到达这一行？读 caller，而不是读被调用者。
3. **配置与默认值**：该分支是否只在某个配置/版本/flag 下可达，而生产默认不走它？查配置默认与启动期校验。
4. **已有测试**：有没有测试已经钉住这条不变量？注意本仓库教训——"有测试"不等于覆盖，要读断言本身是否真的钉住该行为（断言 outcome 而没断言 invariant 的测试是假覆盖）。
5. **输入可构造性**：声称的输入在当前 wire 版本/解码路径下是否真能被构造出来？（历史上就有"某 key 无任何代码产生"这类声称，grep 全仓生产者即可证伪。）
6. **前提的事实性**：premise 单独查证。链接语义、参考实现行为、协议字段宽度的前提错一次，会以"论证完整"的形式活过整轮。

证伪尝试全部记入 `falsification_attempts`，成功与否都写——列表本身是"我认真试过"的证据，也是 `unreproducible` 与 `refuted` 的分界线。

## 3. 复现阶梯

按代价从低到高，能停就停：

| tier | 形态 | 何时够用 | 代价 |
|---|---|---|---|
| `static` | `git show` / `git grep` / `git log -S` / `nm` 等只读事实 | 声称本身就是关于代码结构的（重复实现、缺失生产者、规则分裂、行号错位、配置默认值） | 秒级 |
| `unit_test` | 编译并跑一个已有或新加的 test-only 用例 | 声称是行为性的，且能在单进程内构造输入 | 分钟级，需构建 |
| `integration` | 起节点/走 Engine API/跑 fixture 语料 | 声称只在端到端、多轮、跨进程或不变量在 wire 边界才显形 | 十分钟级以上，需用户确认 |

规则：

- `static` 不能用来判 `confirmed` 的**行为性**声称：`repro.claim_kind=behavioural` 配 `tier=static` 会被 validator 直接拒（这条规则靠显式声明生效，所以要如实标 `structural` / `behavioural`）。"这段代码看起来会返回 INVALID"只是 hypothesis；`confirmed` 需要一个观察到的返回。
- 优先复用已有测试：`ctest -R` 或直接跑测试二进制比新写用例更快且更可信。只有当现有用例不覆盖声称的形态时才新加 test-only 用例。
- 新加用例放在 `$REPRO_WORKTREE`，命名钉住声称的行为（如 `new_payload_honest_retry_does_not_recommit` 式命名），跑完把用例 diff 与输出一起留在报告里；不要把测试留在 PR 分支上（这是 `fisco-respond` 的活）。
- 打不到 `integration` 时如实记 `unreproducible` 并写清边界与已试过的替代路径，**不要**用"代码读起来一定有问题"升格为 `confirmed`。

## 4. mutation probe

要确认**机制**（而不只是症状），做定向干预：把声称的原因改掉，看症状是否消失；改回来，看症状是否回来。

```bash
cd "$REPRO_WORKTREE"            # detached at pin，随便造
# 1) 记录基线：复现命令的输出
# 2) 只改声称的那一处（最小改动，别顺手重构）
# 3) 重跑同一命令，记录输出
# 4) git checkout -- <file> 还原；确认 git diff 为空
```

报告里必填 `file`、`diff` 原文、`symptom_disappeared`、`restored: true`、`post_restore_diff_empty: true`。症状不随干预改变，说明声称的机制不是主因——这本身就是重要结论。

## 5. 判定树

```text
入口 → 位置在 pin 上对吗？
  ├─ 不对（文件/行号/symbol 不符） → 按 symbol 重定位；若声称的代码在 pin 上不存在
  │     → refuted（若前提也错）或 confirmed_symptom_mechanism_differs（若缺陷在别处仍真）
  └─ 对 → 声称的行为能观察到吗？
        ├─ 能 → 机制与干预一致？ → confirmed
        │                      → 不一致 → confirmed_symptom_mechanism_differs
        ├─ 不能，且我有正向反证 → refuted
        ├─ 不能，且 pin 上已有修复 → stale（给 fixed_at + pin 上修复存在的证据）
        ├─ 不能，但我没能构造出触发条件 → unreproducible（列尝试 + 边界）
        └─ 不能，且缺关键输入 → undecidable（列 missing_inputs）
```

`stale` 要双向证据：修复 commit 是 pin 的祖先（`git merge-base --is-ancestor <fix> $PIN`），且 pin 上的代码确实已不含该缺陷。只看到"行号对不上"就报 stale 是错的——代码可能只是被挪走了。

## 6. 本仓库常见形态

**容易把真缺陷判成假（假阳性）：**

- stale 行号照抄：行号漂移后读到无关代码，得出"不存在"。必须按 symbol 重定位。
- 只看 diff 不看调用方：缺陷在 diff 之外的上游未接线代码里；反过来也有——新代码没有生产调用方（"仅测试接线"），scope 要写清而不是直接降级为假。
- premise 靠推论：`PRIVATE`/`LINK_ONLY`、参考实现行为、版本窗口这类前提必须独立查证，读起来通的论证不等于对的前提。
- "重复实现"一律当真缺陷：本仓库有多处重复是**已接受成本**（历史记录里 `publishBuiltPayload` 两份重复就是显式接受项）。确认重复为真，但 `recommendation` 应是 `defer` 并注明已有接受记录，而不是 `fix`。
- 断言存在即覆盖：测试文件里有相关名字的用例不等于钉住了声称的不变量。

**容易把假缺陷判成真 / 把真缺陷判成"复现不了"（假阴性）：**

- 只跑默认构建类型：UB / 越界在某些构建（Release vs ASAN）下才显形。跑不动就写进 `boundary`。
- 单进程视角：需要多节点、多轮 FCU、跨进程或特定 fixture 语料才能显形的问题，单测里安静。
- 语料缺失：依赖外部 fixture 的路径在没有语料时静默跳过（历史上就有 S6 无语料必败的例子），"测试是绿的"不代表路径被执行过。
- 配置门：只在某个 config/启动模式下可达。默认配置跑一遍就宣布 refuted 是错的，要说过的是哪个配置。

## 7. 交付前自检

逐条问自己：

- 一个没参与复核的人，拿着 `pin` + `command` + `observed` 能不能自己复算出我的 verdict？
- 这条证据是**观察**还是**推理**？推理要么补观察，要么降级措辞。
- reviewer 会不会指着某个子声称说"你没回应我这条"？四个子声称都要有落点。
- `boundary` 写的是我没覆盖什么，而不是"测试通过"。
- 如果 verdict 是 `refuted`：我的反证是不是正向的（观察到它不发生），而不是"我没让它发生"？
