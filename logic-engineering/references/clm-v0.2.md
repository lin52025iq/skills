# 规范逻辑模型（CLM）v0.2

CLM v0.2 是语言无关的 **带类型语义模型**。目标是让业务行为既能被人理解，又能被机器验证、修改和编译。

## 1. 核心变化

```text
统一 Node Registry
Typed Value / Typed Expression AST
Symbol Table
Typed Action / Decision / Foreach
Typed Scenario
Semantic Patch / Change Set
Semantic Hash
```

机器公共实现以 `scripts/lib/model.mjs` 为统一 Node Registry、Symbol Table、Semantic Hash 和 scoped-ref 解析基础。禁止各工具维护另一份节点集合或类型规则。

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
  - id: domain.order.items
    type: domain.order_item
    cardinality: many
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

`cardinality: many` 表示字段是该类型的集合；它是 foreach typed collection 的类型依据。

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
  - enum: { type: domain.order_status, value: PENDING_PAYMENT }
  - enum: { type: domain.order_status, value: PENDING_ACCEPTANCE }
```

Typed Value 必须且只能使用一种形态。

## 5. Typed Expression

标准操作：

```text
eq ne lt le gt ge in not_in
all any not
```

例如：

```yaml
op: in
left:
  ref: domain.order.status
right:
  set:
    - enum: { type: domain.order_status, value: PENDING_PAYMENT }
    - enum: { type: domain.order_status, value: PENDING_ACCEPTANCE }
```

`in / not_in` 右侧必须使用 typed `set`。

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
id: decision.order.route
kind: decision
when:
  op: eq
  left: { ref: domain.order.priority }
  right: { literal: VIP }
then:
  - action.order.route.fast
else:
  - action.order.route.standard
```

IIR 必须保持分支顺序和嵌套结构，不能把 then/else 扁平化成无条件执行。

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

## 9. Foreach 与局部作用域

Foreach 使用现有 v0.2 字段，不引入新的序列化形状：

```yaml
id: action.order.foreach_reserved_items
kind: foreach
collection:
  ref: domain.order.items
item: item
when:
  op: eq
  left: { ref: item.reserved }
  right: { literal: true }
do:
  - action.order.release_item
```

子 Action：

```yaml
id: action.order.release_item
kind: action
operation: assign
target: { ref: item.released }
value: { literal: true }
```

### 9.1 Collection Gate

`foreach.collection` 必须：

1. 引用已存在 field；
2. field `cardinality = many`；
3. field `type` 指向 Entity。

否则 `INVALID_FOREACH_COLLECTION`。

### 9.2 Scoped Ref

`item.xxx` 不是全局 Semantic ID，而是上下文型 scoped ref。

```text
foreach.item = item
collection.type = domain.order_item
item.released
→ domain.order_item.released 的类型/字段语义
```

Scoped ref 只在：

- foreach 自身 `when`；
- foreach `do` 引用的子步骤；
- 子 Decision 分支；

范围内合法。

离开该作用域后 `item.xxx` 必须重新判定为非法引用。

同一 Action 被两个类型不同的 foreach 作为 `do` 节点复用时，报告 `FOREACH_SCOPE_CONFLICT`，不要让节点的局部类型依赖调用方碰巧成立。

### 9.3 当前嵌套边界

v0.2 当前支持单层 typed foreach。

如果内层 foreach 的 `collection` 本身引用外层 scoped item，例如：

```text
item.children
```

当前进入 `blocking unresolved`。后续如果需要支持，应明确扩展 scoped collection resolution，不在 Generator 中临时猜测。

## 10. Typed Scenario

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

当前 Scenario assignment 主要覆盖标量字段；复杂集合对象 fixture 应通过后续结构化 fixture 协议扩展，不用自由 JSON 绕过类型系统。

## 11. Constraint

```yaml
id: invariant.order.refund_not_exceed_payment
kind: invariant
expression:
  op: le
  left: { ref: domain.order.total_refunded }
  right: { ref: domain.order.paid_amount }
```

## 12. Symbol Table

```bash
node scripts/logic_cli.mjs symbols model.json -o symbols.json
```

用于引用检查、enum、类型兼容、foreach item 类型、测试派生、中文投影、IIR 编译和后续 Formal Projection。

## 13. 校验

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
全局引用存在
foreach scoped ref 不越界
enum type/value 合法
assign 类型兼容
Scenario 类型兼容
状态迁移不冲突
observed evidence 满足要求
```

## 14. v0.1 兼容

v0.1 只保留兼容读取与迁移能力，不再扩展新功能。

```bash
node scripts/migrate_clm_v01_to_v02.mjs old.json -o new.json
```

迁移脚本只做确定性结构转换，不猜测缺失业务含义。

## 15. Canonical Gate

进入 canonical 前至少要求：

```text
Schema valid
Semantic valid
所有关键引用可解析
所有 Typed Expression 可检查
foreach scope 可解析
无关键状态冲突
Legacy observed facts 有足够 Evidence
```

CLM v0.2 结构若发生破坏性变化，应升级版本，不静默重定义 v0.2。
