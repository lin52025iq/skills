# CLM 语义校验器规范

CLM 校验分成两层：结构校验与语义校验。

结构校验由 JSON Schema 完成；语义校验负责处理跨节点引用、类型、状态、场景、约束与证据一致性。

## 1. 校验顺序

```text
JSON Schema
→ 语义 ID 唯一性
→ 引用完整性
→ 类型一致性
→ 条件表达式合法性
→ 行为流程完整性
→ 状态机一致性
→ 约束一致性
→ 场景一致性
→ 证据完整性
→ Canonical Gate
```

## 2. 语义 ID 唯一性

所有 Semantic Node 的 `id` 必须全局唯一。

禁止：

```text
rule.order.cancel.allowed_status
```

同时出现在两个不同节点。

发现重复 ID 时直接判定 CLM 无效。

## 3. 引用完整性

以下字段中的 Semantic ID 必须能解析：

- Behavior.preconditions
- Behavior.flow
- Behavior.postconditions
- Rule.failure
- Decision.then / else
- Action.effects
- StateMachine.transitions
- Transition.trigger
- Relation.source / target
- Evidence.supports
- Primitive references

若引用缺失：

```text
错误类型：BROKEN_REFERENCE
```

Candidate CLM 可以存在显式 unresolved reference，但必须使用专用 unresolved 节点，不允许静默悬空。

## 4. 类型一致性

条件比较必须遵循类型规则。

例如：

```text
order.status == PAID
```

要求：

```text
order.status : enum<OrderStatus>
PAID         : OrderStatus
```

以下应判定错误：

```text
order.amount == PAID
```

除非模型明确声明可转换关系。

至少检查：

- 比较两侧类型兼容；
- `in` 的元素类型和 subject 类型一致；
- 数值运算只用于数值或支持的 ValueType；
- 布尔运算结果必须是 boolean；
- nullable 值使用前满足对应空值语义；
- 单位类型不能无转换混用，例如 CNY 与 USD。

## 5. 条件表达式合法性

组合条件：

```text
all
any
not
```

规则：

- `all` 至少包含 1 个子条件；
- `any` 至少包含 1 个子条件；
- `not` 必须且只能包含 1 个子条件；
- 不允许出现无限递归的条件引用；
- 同一个组合条件中的完全重复条件应给出警告；
- 明显矛盾条件应给出错误或高优先级警告。

例如：

```text
all:
- order.status == PAID
- order.status == CANCELLED
```

若 `status` 为单值 enum，应标记为不可满足条件。

## 6. Behavior 校验

Behavior 至少需要：

```text
id
kind
name 或可读语义
flow 或明确的纯查询结果
```

检查：

- precondition 引用 Rule / Constraint；
- flow 引用可执行节点；
- failure 引用失败语义；
- postcondition 引用 Constraint / Invariant；
- 输出在成功路径中可产生；
- 不允许流程引用自身形成无解释递归，除非显式声明 recursive behavior。

## 7. Flow 可达性

对于 Decision：

- `then` / `else` 中的节点必须存在；
- 如果条件恒真或恒假，标记不可达分支；
- 如果多个互斥分支被错误建模为并行执行，给出结构问题。

对于 foreach：

- collection 必须是集合类型；
- item 在子作用域内有效；
- 退出 foreach 后 item 不再可引用。

## 8. 状态机一致性

检查：

1. StateMachine 中所有状态唯一；
2. Transition 的 from / to 状态存在；
3. Trigger 引用 Behavior / Event；
4. Forbidden Transition 不能同时存在同条件的允许 Transition；
5. 同一触发条件下存在多个目标状态时，必须有互斥 guard；
6. 可选检查 unreachable state；
7. 可选检查没有出边的 terminal state 是否符合声明。

例如：

```text
PAID --cancel--> CANCELLED
PAID --cancel--> REFUNDED
```

如果没有互斥条件，应报告：

```text
NON_DETERMINISTIC_TRANSITION
```

## 9. Constraint 一致性

重点检查：

- invariant 与允许 state transition 是否冲突；
- precondition 与 scenario given 是否冲突；
- postcondition 是否被 flow 的 effects 明显违反；
- atomicity group 中引用的 action 是否存在；
- idempotency 约束是否绑定到外部或可重复副作用；
- temporal constraint 的 trigger / requirement 可解析。

## 10. Effect 一致性

Action 声明的 Effect 和语义应匹配。

例如：

```text
operation: assign
 target: order.status
```

至少应存在对应 write effect，或由模型规则显式推导。

外部调用如果可重试且不是天然幂等，应要求：

```text
idempotency strategy
```

否则给出高风险警告。

## 11. Scenario 一致性

Scenario 用于验证 CLM，而不是重新定义 CLM。

检查：

- Given 中的字段与值类型合法；
- When 引用已存在 Behavior / Event；
- Then 不应与 Behavior postcondition 或 state transition 冲突；
- Scenario 不得包含 CLM 中不存在且未标记为 candidate 的业务规则。

如果 Scenario 与 CLM 冲突，应报告：

```text
SCENARIO_MODEL_MISMATCH
```

而不是静默修改 CLM。

## 12. Evidence 完整性

对于 `origin: observed` 的 Candidate Node：

- 至少存在一个 evidence_refs；
- Evidence source 应包含 repository/path/symbol 或其他可定位信息；
- inferred evidence 必须有 based_on；
- assumed / unknown 不允许作为 canonical promotion 的唯一依据。

## 13. Canonical Gate

节点升级为 canonical 前至少检查：

```text
schema_valid = true
semantic_valid = true
no_broken_reference = true
no_critical_contradiction = true
```

从 legacy code 导入的节点还应满足：

```text
evidence sufficient
AND
(user confirmed OR authoritative specification matched OR explicit low-risk policy)
```

## 14. 校验结果格式

建议统一输出：

```json
{
  "valid": false,
  "errors": [
    {
      "code": "BROKEN_REFERENCE",
      "semantic_id": "behavior.order.cancel",
      "path": "flow[2]",
      "message": "引用的节点 action.inventory.release 不存在"
    }
  ],
  "warnings": [],
  "stats": {
    "nodes": 42,
    "relations": 61,
    "canonical": 18,
    "candidate": 24
  }
}
```

错误表示模型当前不能进入生成阶段；警告表示模型仍可处理，但需要关注风险。

## 15. 第一版错误码

```text
DUPLICATE_SEMANTIC_ID
BROKEN_REFERENCE
TYPE_MISMATCH
INVALID_CONDITION
UNSATISFIABLE_CONDITION
UNREACHABLE_BRANCH
INVALID_FLOW_REFERENCE
INVALID_STATE_REFERENCE
NON_DETERMINISTIC_TRANSITION
FORBIDDEN_TRANSITION_CONFLICT
CONSTRAINT_CONFLICT
SCENARIO_MODEL_MISMATCH
MISSING_EVIDENCE
INSUFFICIENT_CANONICAL_EVIDENCE
NON_IDEMPOTENT_RETRY_RISK
```

后续实现校验脚本时应优先保持错误码稳定，避免自然语言错误消息成为机器接口。