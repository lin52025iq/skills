# CLM v0.1 严格结构与校验规则

本文件定义规范逻辑模型（Canonical Logic Model，CLM）v0.1 的机器可执行边界。`canonical-logic-model.md` 负责解释模型语义，本文件负责约束字段、引用、表达式和合法性。

## 1. 设计目标

CLM v0.1 必须满足：

- 同一业务逻辑可以脱离 Java、Go、Rust、Python 等具体语言保存；
- 每个可修改逻辑单元具有稳定语义标识；
- 人类可读投影不改变模型事实；
- 局部修改可表示为语义补丁，而不是重写整个模块；
- 生成器可以只依赖结构化模型和目标实现配置生成代码；
- 校验器可以在不理解自由文本的情况下完成基本合法性检查。

## 2. 顶层模型

```yaml
clm:
  schema_version: "0.1"
  id: module.order
  name: 订单模块
  status: candidate | canonical
  domain: []
  rules: []
  behaviors: []
  actions: []
  decisions: []
  state_machines: []
  effects: []
  constraints: []
  scenarios: []
  primitives: []
  relations: []
  evidence: []
```

规则：

1. `schema_version` 必须存在。
2. `id` 必须全局唯一。
3. 除 `name`、`description` 等展示字段外，关键引用必须使用语义标识，不依赖展示文本。
4. `canonical` 模型中的节点不得保留未解析的必要引用。

## 3. 通用节点字段

所有可寻址节点至少包含：

```yaml
id: behavior.order.cancel
kind: behavior
name: 取消订单
status: candidate | canonical | deprecated
origin: observed | intended | user_defined | generated
confidence: high | medium | low
```

可选字段：

```yaml
description: "..."
tags: []
evidence_refs: []
annotations: {}
```

### 3.1 语义标识规则

建议格式：

```text
<类别>.<领域>[.<子领域>...].<名称>
```

例如：

```text
domain.order
field.order.status
rule.order.cancel.allowed_status
behavior.order.cancel
action.order.cancel.change_status
constraint.order.cancelled_not_shippable
scenario.order.cancel.pending_payment
```

必须满足：

- 语义标识不使用文件路径；
- 不使用具体类名作为唯一语义；
- 不因目标语言变化而变化；
- canonical 节点改名时优先修改 `name`，避免无必要修改 `id`。

## 4. 值与类型

所有值必须属于以下之一：

```text
literal      字面值
reference    对另一个语义节点或变量的引用
expression   结构化表达式
collection   有序或无序值集合
```

示例：

```yaml
value:
  type: literal
  value: CANCELLED
```

```yaml
value:
  type: reference
  ref: input.current_user.id
```

禁止在 canonical 模型中用无法解析的自然语言句子代替关键条件和值，例如：

```yaml
condition: "订单差不多完成时不能取消"
```

这类内容只能保存在候选说明或 open question 中。

## 5. 条件表达式

条件表达式使用统一 AST。

### 5.1 比较条件

```yaml
condition:
  op: eq | ne | gt | gte | lt | lte | in | not_in
  left:
    ref: field.order.status
  right:
    value: CANCELLED
```

### 5.2 布尔组合

```yaml
condition:
  op: all
  items:
    - op: eq
      left: { ref: input.current_user.authenticated }
      right: { value: true }
    - op: eq
      left: { ref: field.order.owner_id }
      right: { ref: input.current_user.id }
```

支持：

```text
all
any
not
```

`not` 必须且只能有一个子条件。

### 5.3 存在性

```yaml
condition:
  op: exists | not_exists
  target:
    ref: field.order.payment
```

## 6. 规则 Rule

```yaml
id: rule.order.cancel.allowed_status
kind: rule
name: 允许取消的订单状态
condition:
  op: in
  left: { ref: field.order.status }
  right:
    values:
      - PENDING_PAYMENT
      - PENDING_SHIPMENT
failure_ref: error.order.cancel_forbidden
```

校验：

- `condition` 必须可求值；
- 引用必须存在；
- enum 字段使用 `in/not_in` 时值必须属于对应 enum；
- `failure_ref` 如果存在，必须引用已定义失败语义。

## 7. 行为 Behavior

```yaml
id: behavior.order.cancel
kind: behavior
name: 取消订单
inputs:
  - id: input.current_user
    type_ref: domain.user
  - id: input.order
    type_ref: domain.order
precondition_refs:
  - rule.order.cancel.authorization
  - rule.order.cancel.allowed_status
flow_refs:
  - action.order.cancel.change_status
  - decision.order.cancel.release_inventory
output_refs:
  - output.order.cancelled_order
failure_refs:
  - error.order.cancel_forbidden
postcondition_refs:
  - constraint.order.cancelled_not_shippable
```

校验：

- `flow_refs` 有顺序语义；
- 前置条件不得指向 action；
- 行为引用的 action/decision 必须存在；
- canonical 行为不能引用 `status=candidate` 且会影响关键业务行为的节点，除非显式标记允许未确认依赖。

## 8. 动作 Action

第一版标准动作：

```text
assign
create
update
delete
invoke
emit
persist
return
foreach
```

### 8.1 赋值动作

```yaml
id: action.order.cancel.change_status
kind: action
operation: assign
target: { ref: field.order.status }
value: { value: CANCELLED }
effect_refs:
  - effect.order.status_write
```

### 8.2 调用动作

```yaml
id: action.inventory.release
kind: action
operation: invoke
target_ref: behavior.inventory.release
arguments:
  order_id: { ref: field.order.id }
```

### 8.3 循环动作

```yaml
id: action.inventory.release_items
kind: action
operation: foreach
collection: { ref: field.order.items }
item_name: item
when:
  op: eq
  left: { ref: item.inventory_reserved }
  right: { value: true }
do_refs:
  - action.inventory.release_item
```

校验器必须检查循环内部引用域，防止 `item` 在循环外被引用。

## 9. 决策 Decision

```yaml
id: decision.order.cancel.refund
kind: decision
condition:
  op: eq
  left: { ref: field.order.payment_status }
  right: { value: SUCCEEDED }
then_refs:
  - action.payment.create_refund
else_refs: []
```

规则：

- `then_refs` 和 `else_refs` 都是有序引用；
- `else_refs` 可为空；
- 多分支决策优先表达为 `cases`，不要构造深层嵌套文本。

多分支：

```yaml
cases:
  - when: {...}
    then_refs: [...]
  - when: {...}
    then_refs: [...]
default_refs: []
```

## 10. 状态机

```yaml
id: state_machine.order
kind: state_machine
state_type_ref: domain.order_status
initial_states:
  - CREATED
terminal_states:
  - CANCELLED
  - COMPLETED
transition_refs:
  - transition.order.created_to_paid
```

迁移：

```yaml
id: transition.order.pending_to_cancelled
kind: transition
from: PENDING_PAYMENT
to: CANCELLED
trigger_ref: behavior.order.cancel
guard_refs:
  - rule.order.cancel.allowed_status
effect_refs:
  - effect.order.status_write
```

必须检查：

- `from/to` 属于状态类型；
- 不存在引用未知状态的迁移；
- 明确禁止的迁移不能同时存在允许迁移；
- 对同一 trigger + from 的多个迁移，如果 guard 可能重叠，应产生冲突候选。

## 11. Effect

标准 effect：

```text
read
write
persist
external_call
emit
schedule
cache_read
cache_write
```

示例：

```yaml
id: effect.payment.refund_call
kind: effect
effect_type: external_call
resource_ref: external.payment_gateway
operation: create_refund
properties:
  idempotency: required
  retryable: true
```

Effect 是实现生成的重要输入，不应只存在于自然语言描述。

## 12. Constraint

第一版支持：

```text
precondition
postcondition
invariant
forbidden_transition
uniqueness
cardinality
ordering
temporal
concurrency
atomicity
idempotency
```

### 12.1 不变量

```yaml
id: constraint.order.refund_not_exceed_payment
kind: constraint
constraint_type: invariant
condition:
  op: lte
  left: { ref: field.order.total_refunded }
  right: { ref: field.order.paid_amount }
```

### 12.2 原子性

```yaml
id: constraint.order.cancel.atomicity
kind: constraint
constraint_type: atomicity
members:
  - action.order.cancel.change_status
  - action.order.cancel.save_reason
failure_policy: rollback_all
```

### 12.3 时序约束

```yaml
id: constraint.payment.record_eventually_created
kind: constraint
constraint_type: temporal
trigger_ref: event.payment.succeeded
requirement_ref: event.financial_record.created
relation: eventually_after
time_bound: 5m
```

## 13. Scenario

```yaml
id: scenario.order.cancel.pending_payment
kind: scenario
given:
  - target: { ref: field.order.status }
    value: { value: PENDING_PAYMENT }
when_ref: behavior.order.cancel
then:
  - target: { ref: field.order.status }
    assertion: eq
    value: { value: CANCELLED }
```

Scenario 不得成为独立于规则的第二套事实源。若 Scenario 与 Rule 冲突，应报告模型冲突，而不是选择其中之一。

## 14. Relation

统一结构：

```yaml
source_ref: behavior.order.cancel
relation: REQUIRES
target_ref: rule.order.cancel.allowed_status
```

标准关系：

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
EVIDENCED_BY
```

Relation 应能从节点字段派生时，字段是事实源，Relation 可作为图索引；不得出现字段和 Relation 相互冲突。

## 15. Evidence

```yaml
id: evidence.order.cancel.allowed_status.1
kind: evidence
classification: observed
source:
  repository: current
  path: src/order/service.java
  symbol: cancel
  lines: 81-96
supports_refs:
  - rule.order.cancel.allowed_status
```

推断证据：

```yaml
classification: inferred
based_on_refs:
  - evidence.a
  - evidence.b
```

校验：

- `observed` 必须有具体来源位置；
- `inferred` 必须至少有一个依据；
- `assumed` 必须有 assumption 文本；
- `unknown` 不能用于证明 canonical rule。

## 16. canonical 升级 Gate

节点从 `candidate` 升级为 `canonical` 前至少满足：

1. 所有必要引用可解析；
2. 类型检查通过；
3. 没有未处理的语义冲突；
4. legacy 导入节点有足够 Evidence 或用户/权威规格确认；
5. 若节点属于业务行为变化，必须有明确 intended 来源；
6. 对关键约束至少存在可执行的验证计划。

## 17. 最小静态校验清单

CLM v0.1 校验器至少检查：

```text
ID 唯一
引用存在
类型兼容
enum 值合法
条件操作符参数合法
循环变量作用域
状态迁移状态合法
禁止迁移冲突
行为 flow 引用合法
Scenario 与 Rule 明显冲突
Effect 缺失候选
atomicity 成员存在
canonical 节点是否依赖关键 unknown
```

## 18. 与自然语言投影的边界

自然语言投影可以：

- 修改表达顺序；
- 使用领域中文名称；
- 合并同类条件用于阅读；
- 隐藏不必要的技术字段。

自然语言投影不能：

- 新增 CLM 中不存在的条件；
- 把 `any` 解释成 `all`；
- 改变边界操作符，如 `<=` 变成 `<`；
- 把可选副作用解释为必然副作用；
- 隐藏会改变业务结果的重要 UNKNOWN。
