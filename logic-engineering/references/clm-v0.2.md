# 规范逻辑模型（CLM）v0.2

v0.2 的目标不是增加更多业务概念，而是让现有逻辑模型从“结构化 JSON”升级为更接近编译器 IR 的 **带类型语义模型**。

## 1. v0.2 的四个核心变化

1. **统一节点注册表**：所有工具只认一份 `kind → collection` 映射。
2. **Typed Expression AST**：条件和不变量不再优先保存为自由字符串。
3. **Symbol Table**：字段、枚举和值类型都能被解析和类型检查。
4. **兼容迁移**：v0.1 仍可读，但 Validator 会给出迁移 warning。

## 2. 统一节点集合

规范集合：

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

`relations` 与 `evidence` 是支持结构，不属于普通语义节点集合。

机器实现以 `scripts/clm_model.py` 为唯一注册表。禁止各脚本自行维护 collection 列表。

## 3. Domain 与 Symbol

### Entity

```yaml
id: domain.order
kind: entity
name: 订单
fields:
  - id: domain.order.status
    type: domain.order_status
    nullable: false
  - id: domain.order.paid_amount
    type: type.money
    nullable: false
```

Entity field 本身进入 Symbol Table，但不要求在 `domain` 顶层重复成为独立节点。

### Enum

```yaml
id: domain.order_status
kind: enum
values:
  - PENDING_PAYMENT
  - PENDING_ACCEPTANCE
  - PAID
  - CANCELLED
```

### Value Type

```yaml
id: type.money
kind: value_type
base_type: number
constraints:
  - constraint.money.non_negative
```

## 4. Typed Value

表达式中不直接写不可区分的字符串，而使用 typed value：

### Symbol Reference

```yaml
ref: domain.order.status
```

### Literal

```yaml
literal: 100
```

### Enum Value

```yaml
enum:
  type: domain.order_status
  value: PENDING_PAYMENT
```

### Null

```yaml
null: true
```

一个 typed value 必须且只能使用以上一种形式。

## 5. Typed Expression AST

### 比较

```yaml
op: eq
left:
  ref: domain.order.status
right:
  enum:
    type: domain.order_status
    value: PENDING_PAYMENT
```

标准比较操作：

```text
eq ne lt le gt ge in not_in
```

### all

```yaml
op: all
items:
  - op: eq
    left: { ref: domain.order.owner_id }
    right: { ref: domain.current_user.id }
  - op: in
    left: { ref: domain.order.status }
    right:
      literal:
        - PENDING_PAYMENT
        - PENDING_ACCEPTANCE
```

### any

```yaml
op: any
items:
  - ...
  - ...
```

### not

```yaml
op: not
item:
  op: eq
  left: { ref: domain.order.status }
  right:
    enum:
      type: domain.order_status
      value: CANCELLED
```

## 6. Rule v0.2

推荐：

```yaml
id: rule.order.cancel.allowed_status
kind: rule
name: 允许取消的订单状态
expression:
  op: in
  left:
    ref: domain.order.status
  right:
    literal:
      - PENDING_PAYMENT
      - PENDING_ACCEPTANCE
failure: error.order.cancel_forbidden
```

v0.1：

```yaml
subject: domain.order.status
operator: in
value:
  - PENDING_PAYMENT
  - PENDING_ACCEPTANCE
```

仍可暂时读取，但 Validator 输出 `LEGACY_RULE_SHAPE`。

## 7. Decision v0.2

```yaml
id: decision.order.cancel.refund
kind: decision
when:
  op: eq
  left:
    ref: domain.payment.status
  right:
    enum:
      type: domain.payment_status
      value: SUCCEEDED
then:
  - action.payment.create_refund
else: []
```

## 8. Constraint v0.2

```yaml
id: invariant.order.refund_not_exceed_payment
kind: invariant
expression:
  op: le
  left:
    ref: domain.order.total_refunded
  right:
    ref: domain.order.paid_amount
```

这允许 Validator 判断两侧是否同为 `Money`。

## 9. Symbol Table

`scripts/symbol_table.py` 生成：

```json
{
  "symbols": {
    "domain.order.status": {
      "kind": "field",
      "type": "domain.order_status",
      "nullable": false,
      "owner": "domain.order"
    }
  }
}
```

Symbol Table 是以下能力的共同基础：

- 引用检查；
- enum value 检查；
- 类型兼容检查；
- 边界测试生成；
- 自然语言投影；
- IIR 编译；
- Formal Projection。

## 10. 类型校验原则

至少检查：

```text
Money <= Money             合法
integer < number           合法
OrderStatus == OrderStatus 合法
Money == OrderStatus       非法
```

Enum literal 必须属于声明 enum：

```text
PENDING_PAYMENT ∈ domain.order_status  合法
UNKNOWN_STATE   ∈ domain.order_status  非法
```

## 11. v0.1 兼容策略

v0.2 不要求一次性破坏所有既有 fixture。

Validator 对旧形态：

```text
subject/operator/value
all.args
any.args
not.arg
```

先输出迁移 warning，而不是直接阻断。

新写入的 canonical CLM 应优先使用 v0.2。

## 12. Canonical Gate 增强

节点进入 canonical 前，v0.2 推荐额外要求：

```text
所有表达式可解析
所有 symbol reference 存在
enum literal 有效
类型比较兼容
没有 NODE_COLLECTION_MISMATCH
没有 UNKNOWN_SYMBOL
没有 TYPE_MISMATCH
```

Legacy candidate 可以暂时保留 warning，但在生成生产实现前应消除。
