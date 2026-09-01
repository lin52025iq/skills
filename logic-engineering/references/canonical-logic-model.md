# Canonical Logic Model v0.1

CLM 是 logic-engineering Skill 的核心事实模型。它必须同时满足：

- 与具体编程语言、类名、文件路径解耦；
- 可投影为自然语言供人阅读；
- 可被机器结构化处理、diff、验证和生成实现；
- 支持从 legacy code 导入时绑定证据与置信度；
- 支持局部 Semantic Patch，不要求重写整份逻辑。

## 1. 顶层结构

```yaml
clm:
  id: module.order
  version: 1
  domain: []
  behaviors: []
  states: []
  effects: []
  constraints: []
  scenarios: []
  primitives: []
  relations: []
  evidence: []
```

YAML 仅作为可读序列化示例；实现可以使用 JSON、数据库或图结构。

## 2. 通用 Semantic Node

所有节点共享：

```yaml
id: behavior.order.cancel
kind: behavior
name: 取消订单
description: 允许符合条件的用户取消订单
status: candidate | canonical | deprecated
origin: observed | intended | user_defined | generated
confidence: high | medium | low
```

可选：

```yaml
tags: []
references: []
evidence_refs: []
```

Semantic ID 一旦成为 canonical，不应因为实现类名、文件移动或目标语言改变而修改。

## 3. Domain

### Entity

```yaml
id: domain.order
kind: entity
fields:
  - id: domain.order.status
    type: domain.order_status
  - id: domain.order.paid_amount
    type: type.money
```

### Value Type

```yaml
id: type.money
kind: value_type
constraints:
  - value >= 0
```

### Enum

```yaml
id: domain.order_status
kind: enum
values:
  - PENDING_PAYMENT
  - PAID
  - SHIPPED
  - CANCELLED
```

## 4. Behavior

```yaml
id: behavior.order.cancel
kind: behavior
inputs:
  - current_user
  - order
  - cancel_reason
preconditions:
  - rule.order.cancel.authorization
  - rule.order.cancel.allowed_status
flow:
  - action.order.cancel.change_status
  - action.order.cancel.save_reason
  - decision.order.cancel.release_inventory
  - decision.order.cancel.refund
outputs:
  - cancelled_order
failures:
  - error.order.not_found
  - error.order.cancel_forbidden
postconditions:
  - invariant.order.cancelled_not_shippable
```

Flow 中保存的是 Semantic Node reference，不应内嵌不可寻址的大段自由文本。

## 5. Rule / Condition / Decision

### Rule

```yaml
id: rule.order.cancel.allowed_status
kind: rule
subject: domain.order.status
operator: in
value:
  - PENDING_PAYMENT
  - PAID
failure: error.order.cancel_forbidden
```

### Composite condition

```yaml
id: rule.order.operation.authorization
kind: rule
operator: all
conditions:
  - current_user.authenticated == true
  - order.owner_id == current_user.id
```

### Decision

```yaml
id: decision.order.cancel.refund
kind: decision
when: order.payment.status == SUCCEEDED
then:
  - action.payment.create_refund
else: []
```

组合条件必须显式区分 `all / any / not`，不要依赖自然语言中的模糊连接词。

## 6. Action

```yaml
id: action.order.cancel.change_status
kind: action
operation: assign
target: order.status
value: CANCELLED
effects:
  - effect.order.status_write
```

循环：

```yaml
id: action.inventory.release_order_items
kind: foreach
collection: order.items
item: item
when: item.inventory_reserved == true
do:
  - action.inventory.release_item
```

## 7. State

```yaml
id: state_machine.order
kind: state_machine
states:
  - PENDING_PAYMENT
  - PAID
  - SHIPPED
  - CANCELLED
transitions:
  - transition.order.pending_to_cancelled
```

```yaml
id: transition.order.pending_to_cancelled
kind: transition
from: PENDING_PAYMENT
to: CANCELLED
trigger: behavior.order.cancel
```

禁止迁移应显式保存，而不是只依赖“没有 transition”：

```yaml
id: constraint.order.shipped_not_cancelled
kind: forbidden_transition
from: SHIPPED
to: CANCELLED
```

## 8. Effect

Effect 描述 Action 对系统世界的影响。

```yaml
id: effect.order.status_write
kind: write
resource: order.status
```

```yaml
id: effect.payment.refund_call
kind: external_call
system: payment_gateway
operation: create_refund
idempotency: required
```

支持：

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

## 9. Constraint

统一支持：

```text
precondition
postcondition
invariant
uniqueness
cardinality
ordering
temporal
concurrency
atomicity
idempotency
```

例如：

```yaml
id: invariant.order.refund_not_exceed_payment
kind: invariant
expression: order.total_refunded <= order.paid_amount
```

```yaml
id: constraint.payment.record_eventually_created
kind: temporal
trigger: payment.succeeded
requirement: financial_record.created
time_bound: 5m
```

```yaml
id: constraint.account.balance_exclusive_write
kind: concurrency
resource: account.balance
scope: same_account
policy: exclusive_write
```

## 10. Scenario

```yaml
id: scenario.order.cancel.pending_payment
kind: scenario
given:
  - order.status = PENDING_PAYMENT
  - current_user = order.owner
when:
  - behavior.order.cancel
then:
  - order.status = CANCELLED
```

Scenario 同时用于：

- Human explanation；
- example tests；
- CLM consistency checks；
- legacy behavior comparison。

## 11. Primitive

```yaml
id: primitive.transaction.atomic_group
kind: primitive
contract:
  description: 一组状态修改必须全部成功或全部失败
  guarantees:
    - no_partial_commit
bindings:
  java-spring: spring_transaction
  go-postgres: sql_transaction
```

Primitive 只暴露逻辑契约。Target binding 属于实现层，不得污染 Domain Rule。

## 12. Relation

```yaml
source: behavior.order.cancel
relation: REQUIRES
target: rule.order.cancel.allowed_status
```

第一版标准关系：

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

## 13. Evidence

Legacy import 节点应保留：

```yaml
id: evidence.order.cancel.allowed_status.1
classification: observed
source:
  repository: current
  path: src/order/service.java
  symbol: cancel
  lines: 81-96
supports:
  - rule.order.cancel.allowed_status
```

如果只是推断：

```yaml
classification: inferred
based_on:
  - evidence.a
  - evidence.b
```

## 14. Human Projection Rules

Projection 的职责只是把 Semantic Node 排列成自然语言，不改变模型。

Rule：

```text
order.status IN [PENDING_PAYMENT, PAID]
```

可投影：

```text
订单只有处于“待支付”或“已支付”状态时才满足该条件。
```

Behavior 默认顺序：

```text
目的
输入
前置条件
处理过程
状态变化
副作用
失败情况
原子性/并发/幂等
完成条件
保证/不变量
```

## 15. Candidate 与 Canonical

Legacy code 重建结果默认 `candidate`。

只有满足以下任一条件才升级：

- 用户明确确认；
- 已存在权威规格与代码事实一致；
- 工作流明确允许某类低风险 observed facts 自动接受。

Observed code behavior 与 Intended business behavior 冲突时必须同时保存，不允许覆盖证据。
