---
id: practicum-click-issue
type: practicum
visibility: student
related: [practicum-click]
---
# Feature Request — concurrent `CliRunner` filesystem isolation

我们有一套 IDE/plugin-host 测试环境，会在**同一个 Python process** 里并发运行多个第三方 Click CLI 测试。现在每个测试都要自己做额外串行化，吞掉了并发带来的收益。

希望 Click 的 `CliRunner` 能原生支持这种场景：

- 两个独立 runner 可以同时执行，而不会因为 filesystem isolation 互相干扰；
- 每个 runner 应拥有自己的 isolated filesystem root；
- 现有 `CliRunner` API 保持 source-compatible，已有 command/test 不需要为了这个 feature 改写；
- 现有非并发行为保持不变；
- 不接受 subprocess 方案，因为我们正是为了避免大量 process startup 才使用 threads；
- 这应该是真正可并发的能力，简单把所有 runner invocation 放进一个全局锁里不满足需求。

一个看起来直接的实现方向是：给每个 runner 保存 `filesystem_root`，然后让相对路径访问从这个 root 解析，而不是修改 process working directory。请优先考虑这个方向，但如果代码库里有更合适的实现也可以调整。

请同时更新必要 tests/docs，并说明 compatibility risk。
