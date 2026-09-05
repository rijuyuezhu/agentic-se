# TaskForge

TaskForge 是本课程的贯穿实验系统。

它不是“最佳实践示例仓库”，而是一个**经过设计的、会逐步演化的 teaching system**：每个版本只引入足够支撑当前模块的复杂度，并故意保留后续课程需要发现和修复的问题。

## 当前版本：v0 / M02 baseline

当前系统只有四类行为：

- submit job；
- worker claim job；
- worker finish job；
- query/cancel/metrics。

它目前完全在内存中运行，不包含：

- SQLite；
- HTTP；
- async；
- remote worker；
- retry；
- crash recovery。

这些不是遗漏，而是刻意的 non-goals。课程希望先把 **abstraction / information hiding / state ownership** 看清，再逐步加入 mechanism complexity。

## 运行测试

如果有 `uv`，最省事：

```bash
uv run --with pytest --no-project python -m pytest
```

或者先安装 editable test dependencies：

```bash
python -m pip install -e '.[test]'
python -m pytest
```

课程仓库的 baseline 已实际运行过：`6 passed`。这个数字只说明当前 observable examples 通过；它**不**说明 M02 的 ownership 设计已经良好。

## 重要规则

第一次阅读时不要立刻重构。

先完成 `../02-state-ownership.md` 的 read-only reconnaissance：

1. 列出所有 state writers；
2. 列出所有 state readers；
3. 写出 lifecycle invariant；
4. 区分 contract 与 implementation accident；
5. 画 authority map。

如果一看到 module global 就直接“套 repository pattern”，你会错过本实验最重要的训练：**先建立 system model，再决定 abstraction。**

## 为什么 baseline tests 不直接把所有设计问题测出来

因为设计问题往往不是“当前输入会返回错误值”。

一个实现可以：

```text
所有 tests 都绿
```

同时仍然具有：

```text
高 change amplification
information leakage
split authority risk
representation exposure
```

M02 的目标就是学会在 bug 出现之前识别这类结构风险，并把其中能够转化为 contract 的部分补成可执行证据。
