# 复现配方（FISCO-BCOS）

只在需要具体复现命令时读取。

变量来自 `references/intake.md` 的 `eval`：`$VERIFY_PIN` `$REPRO_WORKTREE` `$VERIFY_ROOT` `$ARTIFACT_DIR`。
本文件所有命令都在 pin 上执行；证据一律 `git show "$VERIFY_PIN":...`，或跑由 **pin 源码**编出的二进制。

> **先确认测试框架再选选择器。** 本仓库模块的主流是 Boost.Test（`cmake/SearchTestCases.cmake` 生成 `<Suite>/<Case>` 用例名，选择器是 `-t` / `--run_test`），少数独立构建目录用 gtest（`--gtest_filter`）。拿不准就跑 `strings <binary> | grep -c gtest_filter`：为 0 就是 Boost.Test，`--gtest_*` 会直接报未知参数。**不要从历史文档抄选择器**——路径和用例名会随 head 漂移。
>
> 下表是**判断规则**，不是可以照抄的清单：每次复核都要用 `ctest -N | grep`、`<bin> -l all` 或 `--gtest_list_tests` 在当前 pin 上确认用例真实存在，再写进 `repro.command`。写死一个没验证过的用例名，等于给自己的 `observed` 编造留了门。

## 声称类型 → tier

| 声称类型 | tier | 首选做法 |
|---|---|---|
| 重复实现、死代码、缺失生产者、规则分裂、配置默认值、命名/注释与代码不符 | `static` | `git grep` / `git show` / `git log -S`（`claim_kind: structural`） |
| 行号、范围、文件不符 | `static` | `git show` 行范围 + `git cat-file -t` |
| 边界/枚举/错误传播/解码行为 | `unit_test` | 跑已有 `ctest -R`；不覆盖再加 test-only 用例（`claim_kind: behavioural`） |
| 状态机、重试、锁域、缓存残留 | `unit_test` | 同上，注意断言要钉住不变量 |
| wire 兼容、Engine API 应答、共识/出块、跨进程 | `integration` | air 单节点或 Engine API 脚本；单测里通常会安静 |

## 静态证据

```bash
# 引用一段原文（行号以 pin 为准）
git show "$VERIFY_PIN":opstack-executor/OpstackExecutor.h | nl -ba | sed -n '736,750p'

# 文件是否存在、是文件还是目录（目录不能给行号）
git cat-file -t "$VERIFY_PIN":opstack-executor/OpstackExecutor.h

# 全仓搜符号/字面量（生产者、调用方、同类位点）——都带 pin
git grep -n 'bindEnvelopeAccessList' "$VERIFY_PIN" -- opstack-executor
git grep -n 'isEvicted\|evicted' "$VERIFY_PIN" -- bcos-txpool
git grep -l 'BOOST_AUTO_TEST_SUITE' "$VERIFY_PIN" -- opstack-executor/tests

# 某形态的引入/演化来源（注意 -- 之前的 revision 不能漏，否则读的是工作区）
git log --oneline -S 'bindEnvelopeAccessList' "$VERIFY_PIN" -- opstack-executor/OpstackExecutor.h
git log --oneline -G 'accessList.*bound' "$VERIFY_PIN" -- opstack-executor

# 修复是否已在 pin 内（stale 判定的必要证据之一）
git merge-base --is-ancestor <fix-commit> "$VERIFY_PIN" \
  && echo "repair IS in pin" || echo "repair NOT in pin"
```

类位点扫描：类别性 finding 要给出"同类位点全部枚举"的证据（`git grep -n` 结果原样贴出），只报 reviewer 点名的实例不算完成。

## 找用例、跑用例

用例名从构建元数据读，不从记忆里写：

```bash
cd "$MAIN/build"                       # 主树构建目录
ctest -N | grep -i <关键词>            # 精确用例名（add_test 名）
ctest -R '<name>' --output-on-failure  # 跑一个用例/一个 target
```

主树是 Boost.Test，用例名形如 `<Suite>/<Case>`，选择器是 `-t`（等价 `--run_test`）：

```bash
# 二进制位置以实际构建为准；构建产物未必在 build/bin
find "$MAIN/build" -name test-bcos-engine -type f | head -1
<bin> -l all                            # 列出全部用例（Boost.Test），确认名字存在
<bin> -t <Suite>/<Case>                 # 跑单个用例；名字错会报 "no test cases matching filter"
```

`opstack-executor/tests` 与 `bcos-evm/test` 里也是 Boost.Test（`find_package(Boost REQUIRED unit_test_framework)`），但 **bcos-evm 的测试编在 `bcos-evm/build`，不在主树 `build/`**——在主树里 `ctest -R BcosEvmEthTests` 会报找不到可执行文件。真实 suite 名可用 `git grep -h BOOST_AUTO_TEST_SUITE "$VERIFY_PIN" -- <dir>` 列出（例如 opstack-executor/tests 下有 `OpEnvelopeMirrorSuite`、`OpSchedulerSuite`；bcos-evm/test 下有 `OpDepositSuite`、`OpFeeParamsSuite`），case 名同理用 `BOOST_AUTO_TEST_CASE`。

只有在确认目标确实链接 gtest 时才用 gtest 选择器：

```bash
"$BIN" --gtest_list_tests
"$BIN" --gtest_filter='<Suite>.<Case>'
```

## 在 pin 上构建（repro worktree）

主树 `build/` 绑定主树源码（`CMAKE_HOME_DIRECTORY`），**不能**用它编 pin 的源码。先判断：

```bash
git -C "$REPRO_WORKTREE" rev-parse HEAD        # == $VERIFY_PIN（detached）
git -C "$MAIN" rev-parse HEAD                  # 与 pin 相同才可直接用主树 build/
```

不同则在 worktree 里单独配置，复用主树已装的 vcpkg 依赖把配置压到分钟级：

```bash
cmake -S "$REPRO_WORKTREE" -B "$VERIFY_ROOT/build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DTESTS=ON -DCOVERAGE=OFF \
  -DWITH_LIGHTNODE=ON -DWITH_CPPSDK=ON -DWITH_TIKV=OFF \
  -DWITH_TARS_SERVICES=OFF -DTOOLS=OFF \
  -DCMAKE_TOOLCHAIN_FILE="$MAIN/vcpkg/scripts/buildsystems/vcpkg.cmake" \
  -DVCPKG_INSTALLED_DIR="$MAIN/build/vcpkg_installed" \
  -DVCPKG_TARGET_TRIPLET=arm64-osx          # 取主树 CMakeCache.txt 的实际值

# 只编受影响的 target，不要全量
cmake --build "$VERIFY_ROOT/build" --target <target> -j"$(sysctl -n hw.ncpu)"
```

选项名以 `cmake/Options.cmake` 为准（是 `TOOLS` 不是 `TOOL`）。只复用 `VCPKG_INSTALLED_DIR` 的前提是 `vcpkg.json` 与主树一致；不一致时如实写进 `boundary`，不要偷偷用主树产物。

## 集成复现

集成复现要现成的可执行文件，先确认它存在（本仓库常见情况是主树只有部分 target 被构建过）：

```bash
# 脚本要求 <BUILD_DIR>/fisco-bcos-air/fisco-bcos；不存在就说明需要先构建 air
ls -l "$MAIN/build/fisco-bcos-air/fisco-bcos"
bash "$MAIN/tools/engine_integration_test.sh" "$MAIN/build" 8551   # curl smoke + mock CL
```

EEST fixture 回放需要语料（见 `.github/workflows/workflow.yml` 的下载 step）；语料缺席时相关用例会静默跳过——**跳过不等于通过**，判 `confirmed` 前先确认用例真的执行了（逐用例输出或 `-l all`）。

## test-only 复现的落盘

```bash
cd "$REPRO_WORKTREE"
# 新加/改测试（只动测试文件），命名钉住声称的行为
git diff >"$ARTIFACT_DIR/repro.patch"          # 留证据
<bin> -t <Suite>/<Case>                        # 或 ctest -R / gtest
git status --porcelain                         # 记录本次复现改了哪些文件
```

结束时确认：`git -C "$REPRO_WORKTREE" diff --stat` 只含测试文件，且主工作树 `git -C "$MAIN" status --porcelain` 与复核前一致。跨构建类型才显形的问题（ASAN/Release）在 `boundary` 里写清跑过哪种。
