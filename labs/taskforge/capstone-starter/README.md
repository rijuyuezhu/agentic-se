# TaskForge Capstone Starter

这是 M13 的独立 starting point。它代表一个已经运行过多个版本、现在需要继续演化的 TaskForge，而不是前面 v0 teaching baseline 的直接替换。

它故意包含：

- 一个已有 CLI 依赖的 legacy public API；
- SQLite durable schema v1；
- background maintenance scan；
- remote-worker claim / finish protocol；
- 一个可确定性复现的 double-claim race；
- 一个历史 compatibility quirk：v1 finish 只有 `job_id + exit_code`，没有 worker/attempt identity；
- 一组全部绿色但明显不完整的 baseline tests；
- [`ISSUE.md`](ISSUE.md) 中一份看似合理、实际包含互相冲突 guarantee 的 feature request。

## Baseline

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

然后运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/capstone_baseline_probe.py
```

不要在第一次阅读 issue 后立刻实现。M13 要求先完成 issue review、system model、contract/invariant inventory、migration/rollback reasoning 与 staged plan。

## 目录

```text
src/taskforge_capstone/
  db.py
  service.py
  api.py
  remote_worker.py
  maintenance.py

tests/test_baseline.py
fixtures/legacy-worker-finish.json
tools/capstone_baseline_probe.py
ISSUE.md
```

## 一个重要约束

Starter 中的 `operator_requeue()` 是历史 emergency operation，不代表自动 lease recovery 的正确设计。它存在的目的之一就是让你观察：如果旧 completion protocol 没有 attempt identity，requeue 后的 stale worker 可以怎样污染新的 attempt。
