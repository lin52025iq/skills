# 语义影响分析

语义影响分析回答：**一个逻辑节点变化以后，哪些逻辑、测试、IIR、目标实现和验证需要重新计算？**

目标是最小充分重算集合，而不是任何修改都全量生成。

## 1. 输入

```text
当前 CLM
+ 一个或多个 changed Semantic ID
```

Node 工具：

```bash
node scripts/analyze_impact.mjs model.json <changed-id...> --output impact.json
```

## 2. 影响等级

```text
DIRECT       直接依赖变化节点
TRANSITIVE   经其他语义节点间接受影响
DERIVED      Human View、Tests、IIR、Generated Code 等派生产物
REVIEW       无法确定是否改变，需要复核
```

## 3. 传播关系

默认反向传播：

```text
REQUIRES
INVOKES
READS
WRITES
TRANSITIONS
EMITS
HANDLES
GUARANTEES
CONSTRAINED_BY
USES_PRIMITIVE
DERIVED_FROM
```

同时识别节点内部引用，例如 Behavior.preconditions/flow/postconditions、Decision、Action.effects、StateMachine.transitions、Scenario.when、Rule Typed Expression refs。

Evidence pointer 默认不传播业务影响；证据变化主要影响置信度和 canonical gate。

## 4. Domain 变化

Domain / Enum / ValueType 属于高扩散变化。

例如新增订单状态后，应复核：

- 引用该 enum 的 Rule；
- State Machine completeness；
- Decision 是否缺 case；
- Scenario 覆盖；
- IIR / Target type；
- persistence mapping（若已显式建立）。

不要自动修改所有规则；无法证明时进入 REVIEW。

## 5. Rule / Behavior 变化

通常传播：

```text
Rule
→ Behavior
→ Scenario / Tests
→ IIR
→ Target Implementation
```

Rule 同时作为 Transition guard 时还需重新验证状态模型。

## 6. Action / Effect 变化

至少重新检查：

```text
Behavior
读写冲突
事务边界
并发约束
幂等要求
副作用顺序
IIR
integration/property tests
```

## 7. State / Constraint 变化

状态变化需要重算状态约束、Transition completeness、Forbidden Transition、Scenario 和 Target state type。

Constraint 变化影响验证计划、property/formal projection；如果被 Behavior 显式依赖，也传播到 IIR 与 Target Implementation。

## 8. Primitive 变化

Primitive contract 变化属于语义变化，传播到全部使用者。

如果只是某个 Target Profile 的具体 binding 改变、contract 不变：

```text
CLM 不变
IIR / Target Code / Integration Tests 重算
```

不要把某一种目标语言或数据库的实现替换误认为领域逻辑变化。

## 9. 派生产物

典型派生产物：

```text
human_projection
scenario_tests
boundary_tests
property_tests
state_tests
formal_projection
target_iir
generated_code
runtime_monitor
```

## 10. 输出

```json
{
  "changed": ["rule.order.cancel.allowed_status"],
  "affected_nodes": [
    {
      "id": "behavior.order.cancel",
      "level": "DIRECT",
      "reason": "Behavior.preconditions 引用了发生变化的规则"
    }
  ],
  "derived_artifacts": [
    "human_projection",
    "scenario_tests",
    "target_iir",
    "generated_code"
  ],
  "review_candidates": []
}
```

## 11. 停止原则

- 已访问节点不重复传播；
- 明确不传播业务影响的关系停止；
- 仅 Evidence pointer 变化时不扩散执行语义；
- 跨模块只有存在显式语义引用时才继续。

不要按照源码 import 图无限传播。影响分析关注的是 **Semantic Dependency**。
