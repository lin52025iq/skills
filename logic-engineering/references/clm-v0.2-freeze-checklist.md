# CLM v0.2 冻结清单

CLM v0.2 进入“可冻结”状态前，必须满足以下 Gate。

## 1. 结构 Gate

- 所有节点类型由 `scripts/clm_model.py` 统一注册。
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
- 人类视图不得暴露必须读懂的原始 AST JSON 才能理解主要逻辑。
- 投影不得创造 CLM 中不存在的业务规则。

## 4. 修改 Gate

- 单节点修改可以使用 Semantic Patch。
- 一个业务意图涉及多个节点时必须支持 Semantic Change Set。
- Change Set 任一步失败时不得输出部分修改后的 CLM。
- Change Set 可通过 `base_model_version` 和 `base_semantic_hash` 防止基于旧模型误应用。
- Diff 必须包含修改前后 semantic hash。

## 5. 测试 Gate

- Rule 能生成正例/反例或边界测试意图。
- Typed Scenario 能生成标准化 `given / when / expect` 测试向量。
- Transition / Forbidden Transition 能生成状态测试。
- Invariant / Temporal Constraint 能形成 property / integration intent。
- 测试期望只能来自 CLM，不得从 generated code 推导。

## 6. 编译 Gate

- CLM 能编译到 IIR。
- IIR 对无法解析的语义必须进入 `unresolved`，不得静默遗漏。
- Target Profile 不得反向修改 CLM 业务语义。

## 7. Legacy Gate

- v0.1 可以兼容读取。
- `scripts/migrate_clm_v01_to_v02.py` 只做确定性迁移，不猜测缺失业务含义。
- 迁移后的模型必须重新经过 v0.2 Validator。

## 8. 自动回归

执行：

```bash
python scripts/run_v02_regression.py
```

只有所有 checks 均通过，才能标记当前实现满足 CLM v0.2 基础冻结条件。

冻结表示：

> 后续 IIR / Generator 可以依赖这些核心语义结构。

冻结不表示：

> CLM 永远不再扩展。

任何破坏性结构变化必须升级版本，而不是静默改变 v0.2 语义。
