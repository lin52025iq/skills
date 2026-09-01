# 语义影响分析

语义影响分析用于回答：**一个逻辑节点发生变化以后，哪些逻辑、测试、实现和验证必须重新计算？**

它服务于局部修改，而不是重新生成整个模块。

## 1. 输入

影响分析至少接受：

```text
当前 CLM
+ 一个或多个发生变化的 Semantic ID
+ 可选 Semantic Patch
```

变化来源可以是：

- 用户编辑；
- 语义补丁；
- 逻辑优化提案被接受；
- legacy import 重新确认；
- 公共规则抽取；
- Primitive contract 变化。

## 2. 影响图

影响分析以 CLM 的有向语义关系为基础，同时补充节点内部引用。

需要建立反向依赖：

```text
被引用节点
    ↑
引用它的 Behavior / Rule / Decision / State / Scenario / Constraint
```

例如：

```text
rule.order.cancel.allowed_status
        ↑ REQUIRES
behavior.order.cancel
        ↑ trigger
transition.order.pending_to_cancelled
        ↑ covered_by
scenario.order.cancel.pending_payment
```

修改 `rule.order.cancel.allowed_status` 时，上述节点都属于影响候选。

## 3. 影响等级

统一分为四级：

```text
DIRECT       直接引用变化节点
TRANSITIVE   经其他节点间接受影响
DERIVED      由受影响节点派生的投影、测试、IIR、代码
REVIEW       不确定是否改变，需要人工/Agent 检查
```

## 4. 默认传播关系

以下关系默认向反方向传播影响：

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

`EVIDENCED_BY` 默认不表示业务依赖；Evidence 变化通常只影响置信度和 canonical gate，不自动判定业务语义变化。

## 5. 节点内部引用传播

除 `relations` 外，还必须识别：

- Behavior.preconditions / flow / postconditions / failures；
- Decision.then / else；
- Action.effects；
- StateMachine.transitions；
- Transition.trigger；
- Scenario.when 中的 behavior；
- Constraint 绑定的资源、行为或状态；
- Primitive bindings；
- Rule 对 Domain field / enum 的引用。

## 6. 领域模型变化

Domain 节点变化属于高扩散变化。

例如枚举新增值：

```text
domain.order_status
+ PENDING_ACCEPTANCE
```

至少检查：

- 所有引用该枚举的 Rule；
- State Machine 是否需要新增 State；
- Decision Table 是否存在遗漏 case；
- Scenario 是否覆盖新值；
- target-language enum / type；
- serialization / persistence binding（如果 IIR 声明）。

不要因为新增 enum value 就自动修改所有规则；应把可能缺失 case 标为 `REVIEW`。

## 7. Rule 变化

Rule 改变通常直接影响：

```text
引用 Rule 的 Behavior
→ Behavior 对应 Scenario / Tests
→ Behavior IIR
→ Generated implementation
```

如果 Rule 同时参与 State transition guard，应额外重新验证 State Machine。

## 8. Action / Effect 变化

Action 或 Effect 改变时至少重新计算：

- 包含该 Action 的 Behavior；
- 读写冲突；
- 事务边界；
- 并发约束；
- 幂等要求；
- Side-effect ordering；
- IIR；
- integration / property tests。

## 9. State 变化

状态或迁移变化应触发：

- 所有状态约束；
- Transition completeness 检查；
- forbidden transition 检查；
- Scenario transition tests；
- 使用该状态的 Rule / Decision；
- generated state type；
- runtime monitor（如存在）。

## 10. Constraint 变化

Constraint 变化至少影响：

```text
验证计划
property tests
formal projection
runtime monitor（适用时）
```

如果 Constraint 被 Behavior 显式 `REQUIRES / GUARANTEES / CONSTRAINED_BY`，则 Behavior 及其实现也进入影响集合。

## 11. Primitive 变化

Primitive contract 与 binding 必须区分。

### Contract 变化

例如：

```text
primitive.messaging.publish_reliably
保证从 at-least-once 改为 exactly-once
```

属于语义变化，应影响全部 `USES_PRIMITIVE` 节点。

### Target binding 变化

如果只是 Java/Go 具体实现替换，但 contract 不变：

```text
CLM 不变
IIR / generated code / integration tests 重算
```

## 12. 派生产物

影响分析必须显式输出派生产物：

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

不是所有变化都需要全部重算。

## 13. 输出格式

建议：

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
    "boundary_tests",
    "target_iir",
    "generated_code"
  ],
  "review_candidates": [],
  "revalidation": [
    "clm_validator",
    "scenario_consistency"
  ]
}
```

## 14. 停止条件

影响传播在以下情况停止：

- 已经访问过节点；
- 关系明确不传播业务影响；
- 仅为 Evidence pointer 且语义内容未改变；
- 达到模块边界且跨模块没有显式语义引用。

不要根据文件 import 关系无限传播；影响分析针对**语义依赖**，不是源码依赖。

## 15. 保守原则

无法证明“不受影响”时，可以进入 `REVIEW`，但不要把所有节点都标为受影响。

目标是：

```text
最小充分重算集合
```

而不是：

```text
任何修改 → 全仓库重新生成
```
