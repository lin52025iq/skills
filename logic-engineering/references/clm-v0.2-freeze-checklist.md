# CLM v0.2 冻结清单

CLM v0.2 进入“可冻结”状态前，必须满足以下 Gate。

## 1. 结构 Gate

- 所有节点类型由 `scripts/lib/model.mjs` 统一注册。
- `rules / decisions / actions` 在 Validator、Patch、Impact、Renderer、Test Vector、IIR 中均可寻址。
- v0.2 Schema 不允许 Action target/value 和 Scenario given/then 退回自由字符串。
- `in / not_in` 的集合值使用 typed `set`。

## 2. 类型 Gate

- Typed Expression 引用必须存在于 Symbol Table。
- enum type/value 必须合法。
- assign target/value 类型必须兼容。
- Scenario Given/Then target/value 类型必须兼容。
- 集合成员类型必须与被判断字段兼容。

## 3. 人类可读 Gate

- Rule、Decision、Action、Scenario、Constraint 均能投影为中文。
- 人类视图不得要求阅读 AST JSON 才能理解主要逻辑。
- 投影不得创造 CLM 中不存在的业务规则。

## 4. 修改 Gate

- 单节点修改使用 Semantic Patch。
- 一个业务意图涉及多个节点时使用 Semantic Change Set。
- Change Set 任一步失败时不得输出部分模型。
- Change Set 可通过 `base_model_version + base_semantic_hash` 防止旧修改误应用。
- Diff 保存修改前后 semantic hash。

## 5. 测试 Gate

- Rule 能生成正例/反例或边界测试意图。
- Typed Scenario 能生成标准化 `given / when / expect`。
- Transition / Forbidden Transition 能生成状态测试。
- Invariant / Temporal Constraint 能形成 property / integration intent。
- 测试期望只来自 CLM。

## 6. 编译 Gate

- CLM 能编译到 IIR v0.2。
- 无法解析的语义进入 `unresolved`。
- Target Profile 不得反向修改 CLM。
- IIR Validator 通过后才允许 Target Generator。

## 7. Legacy Gate

- v0.1 可以兼容读取。
- `scripts/migrate_clm_v01_to_v02.mjs` 只做确定性迁移。
- 迁移后重新执行 v0.2 Validator。

## 8. Node 工具链 Gate

- `logic-engineering` 主路径不依赖 Python。
- 日常 CLI 使用 `scripts/logic_cli.mjs`。
- 流水线使用 `scripts/run_pipeline.mjs`。
- 不同时维护 Python/Node 双实现。

## 9. Reference Target Gate

当前首个 Reference Target：

```text
TypeScript + Node.js + SQLite + Vitest
```

Reference Target 只验证 Target Generator，不改变 CLM/IIR 的语言无关性。

## 10. 自动回归

```bash
node scripts/run_v02_regression.mjs
```

或：

```bash
npm run regression
```

只有所有 checks 均通过，才能标记当前实现满足 CLM v0.2 基础冻结条件。

冻结表示后续 IIR / Generator 可以依赖这些核心结构；任何破坏性变化必须升级版本，而不是静默改变 v0.2。
