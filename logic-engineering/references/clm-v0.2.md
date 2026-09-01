# 规范逻辑模型（CLM）v0.2

CLM v0.2 是语言无关的 **带类型语义模型**。目标是让业务行为既能被人理解，又能被机器验证、修改和编译。

## 1. 核心变化

```text
统一 Node Registry
Typed Value / Typed Expression AST
Symbol Table
Typed Action
Typed Scenario
Semantic Patch / Change Set
Semantic Hash
```

机器公共实现以：

`scripts/lib/model.mjs`

为统一 Node Registry、Symbol Table 和 Semantic Hash 基础。禁止各工具维护另一份节点集合。

## 2. 节点集合

```text
domain
behaviors
rules
decisions
actions
states
effects
constraints
scenarios
primitives
```

`relations` 与 `evidence` 是支持结构。

## 3. Domain 与 Symbol

Entity：

```yaml
id: domain.order
kind: entity
fields:
  - id: domain.order.status
    type: domain.order_status
    nullable: false
```

Enum：

```yaml
id: domain.order_status
kind: enum
values:
  - PENDING_PAYMENT
  - PENDING_ACCEPTANCE
  - PAID
  - CANCELLED
```

Value Type：

```yaml
id: type.money
kind: value_type
base_type: number
```

Entity field 会进入 Symbol Table，不需要在 `domain` 顶层重复建节点。

## 4. Typed Value

Symbol Reference：

```yaml
ref: domain.order.status
```

Literal：

```yaml
literal: 100
```

Enum：

```yaml
enum:
  type: domain.order_status
  value: PENDING_PAYMENT
```

Null：

```yaml
null: true
```

集合：

```yaml
set:
  - enum:
      type: domain.order_status
      value: PENDING_PAYMENT
  - enum:
      type: domain.order_status
      value: PENDING_ACCEPTANCE
```

Typed Value 必须且只能使用一种形态。

## 5. Typed Expression

比较：

```yaml
op: eq
left:
  ref: domain.order.status
right:
  enum:
    type: domain.order_status
    value: PENDING_PAYMENT
```

标准操作：

```text
eq ne lt le gt ge in not_in
all any not
```

集合判断：

```yaml
op: in
left:
  ref: domain.order.status
right:
  set:
    - enum: { type: domain.order_status, value: PENDING_PAYMENT }
    - enum: { type: domain.order_status, value: PENDING_ACCEPTANCE }
```

`in / not_in` 右侧必须使用 typed `set`，不能退回自由字符串数组。

## 6. Rule

```yaml
id: rule.order.cancel.allowed_status
kind: rule
expression:
  op: in
  left: { ref: domain.order.status }
  right:
    set:
      - enum: { type: domain.order_status, value: PENDING_PAYMENT }
      - enum: { type: domain.order_status, value: PENDING_ACCEPTANCE }
```

## 7. Decision

```yaml
id: decision.order.cancel.refund
kind: decision
when:
  op: eq
  left: { ref: domain.payment.status }
  right:
    enum: { type: domain.payment_status, value: SUCCEEDED }
then:
  - action.payment.create_refund
else: []
```

## 8. Typed Action

```yaml
id: action.order.cancel.change_status
kind: action
operation: assign
target:
  ref: domain.order.status
value:
  enum:
    type: domain.order_status
    value: CANCELLED
```

赋值两侧必须通过类型检查。

## 9. Typed Scenario

```yaml
id: scenario.order.cancel.pending
kind: scenario
given:
  - target: { ref: domain.order.status }
    value:
      enum: { type: domain.order_status, value: PENDING_PAYMENT }
when:
  - behavior.order.cancel
then:
  - target: { ref: domain.order.status }
    value:
      enum: { type: domain.order_status, value: CANCELLED }
```

Scenario 是 executable example，不重新定义 CLM 规则。

## 10. Constraint

```yaml
id: invariant.order.refund_not_exceed_payment
kind: invariant
expression:
  op: le
  left: { ref: domain.order.total_refunded }
  right: { ref: domain.order.paid_amount }
```

## 11. Symbol Table

生成：

```bash
node scripts/logic_cli.mjs symbols model.json -o symbols.json
```

用于：

- 引用检查；
- enum value 检查；
- 类型兼容；
- 测试派生；
- 中文投影；
- IIR 编译；
- 后续 Formal Projection。

## 12. 校验

结构 Gate：

```bash
node scripts/schema_validate.mjs model.json schemas/clm-v0.2.schema.json
```

语义 Gate：

```bash
node scripts/logic_cli.mjs validate-clm model.json
```

至少保证：

```text
Semantic ID 唯一
Node collection 正确
引用存在
enum type/value 合法
assign 类型兼容
Scenario 类型兼容
状态迁移不冲突
observed evidence 满足要求
```

## 13. v0.1 兼容

v0.1 只保留兼容读取与迁移能力，不再扩展新功能。

```bash
node scripts/migrate_clm_v01_to_v02.mjs old.json -o new.json
```

迁移脚本只做确定性结构转换，不猜测缺失业务含义。

## 14. Canonical Gate

进入 canonical 前至少要求：

```text
Schema valid
Semantic valid
所有关键引用可解析
所有 Typed Expression 可检查
无关键状态冲突
Legacy observed facts 有足够 Evidence
```

CLM v0.2 结构若发生破坏性变化，应升级版本，不静默重定义 v0.2。
