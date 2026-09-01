# 实现中间表示（IIR）规范 v0.1

实现中间表示（Implementation IR，IIR）位于规范逻辑模型（CLM）与具体编程语言代码之间。

CLM 回答“系统必须做什么”，IIR 回答“在当前目标平台上准备怎样实现”。两者必须严格分层。

```text
CLM
 ↓
目标配置
 ↓
基础能力绑定
 ↓
IIR
 ↓
目标语言代码
```

## 1. 为什么需要 IIR

如果直接让模型把 CLM 翻译成代码，容易把技术选择和业务规则混在一起，并导致同一逻辑每次生成不同架构。

IIR 用于固定：

- 模块边界；
- 接口与依赖；
- 持久化策略；
- 事务策略；
- 并发策略；
- 消息与事件策略；
- 错误模型；
- 重试与幂等实现；
- 生成代码与人工适配器的边界。

## 2. 顶层结构

```yaml
iir:
  version: "0.1"
  source_clm: module.order
  target_profile: go-postgres-kafka
  modules: []
  components: []
  primitive_bindings: []
  persistence: []
  messaging: []
  transactions: []
  concurrency: []
  error_mappings: []
  traceability: []
```

## 3. Component

```yaml
id: component.order.cancel_usecase
kind: use_case
implements:
  - behavior.order.cancel
inputs:
  - current_user
  - order_id
dependencies:
  - port.order_repository
  - port.inventory_service
```

`implements` 必须引用 CLM Behavior。

IIR component 的命名可以受目标语言习惯影响，但不能替代 Semantic ID。

## 4. Port

当业务需要外部能力时，优先生成契约端口：

```yaml
id: port.inventory_service
kind: port
contract_ref: behavior.inventory.release
operations:
  - release_reservation
```

目标项目再绑定：

```text
port.inventory_service
→ existing InventoryClient
```

或生成 adapter contract 供人工实现。

## 5. Primitive Binding

CLM：

```text
primitive.transaction.atomic_group
```

IIR：

```yaml
primitive_ref: primitive.transaction.atomic_group
binding: database_transaction
provider: postgres
scope:
  - action.order.cancel.change_status
  - action.order.cancel.save_reason
```

目标代码生成器根据语言/框架选择具体 API。

## 6. Transaction Plan

事务不能由生成器临时猜测。

```yaml
id: transaction.order.cancel
atomic_members:
  - action.order.cancel.change_status
  - action.order.cancel.save_reason
strategy: local_database_transaction
out_of_transaction:
  - action.inventory.release
  - action.payment.create_refund
```

必须与 CLM atomicity constraint 一致。

如果无法在目标平台实现 CLM 要求，生成必须失败或产生明确阻塞项，不能静默降级。

## 7. Persistence Plan

```yaml
id: persistence.order
entity_ref: domain.order
repository_port: port.order_repository
strategy: relational
mapping:
  status: order_status
  paid_amount: paid_amount
```

CLM 不存表名；表名、索引等属于 IIR。

## 8. Messaging Plan

```yaml
id: messaging.order_cancelled
semantic_event_ref: event.order.cancelled
transport: kafka
delivery: at_least_once
producer_strategy: transactional_outbox
idempotency_key: order_id
```

如果 CLM 要求可靠发布而目标配置没有绑定可靠策略，应报告缺失 binding。

## 9. Concurrency Plan

CLM：

```text
同一账户余额修改必须互斥。
```

IIR 可以选择：

```yaml
resource_ref: field.account.balance
strategy: database_row_lock
key_ref: field.account.id
```

或：

```yaml
strategy: optimistic_version_check
```

只要能够证明满足 CLM contract。

## 10. Error Mapping

CLM failure：

```text
error.order.cancel_forbidden
```

IIR：

```yaml
semantic_error_ref: error.order.cancel_forbidden
target_error: OrderCancelForbidden
transport_mapping:
  http_status: 409
```

HTTP 状态码不是业务事实，除非产品契约明确将其作为外部可观察行为。

## 11. 生成区域

IIR 将代码区域分成三类：

### 11.1 完全生成

适合：

- 规则判断；
- 状态迁移；
- 用例编排；
- 数据转换；
- 从 CLM 派生的测试。

### 11.2 生成契约，人工实现

适合：

- 第三方 SDK；
- 复杂外部系统适配；
- 专有基础设施。

### 11.3 已验证基础能力

已有稳定 primitive/adapter 时直接绑定，不重复生成。

## 12. Traceability

每个生成 component 必须能够回到 CLM：

```yaml
implementation_id: component.order.cancel_usecase
semantic_refs:
  - behavior.order.cancel
  - rule.order.cancel.allowed_status
generated_artifacts:
  - internal/order/cancel.go
  - internal/order/cancel_test.go
```

代码行号是易变信息，可以作为派生索引；Semantic ID 才是稳定映射主键。

## 13. IIR 校验

生成代码前至少检查：

```text
每个 Behavior 是否存在实现映射
每个关键 Effect 是否有实现策略
每个 Primitive 是否已绑定
Atomicity 是否可满足
Concurrency constraint 是否有策略
External effect 是否有端口/adapter
Error 是否有目标映射
生成区域与人工区域是否冲突
```

## 14. 不允许从 IIR 反向污染 CLM

例如 IIR 选择 PostgreSQL，并不意味着 CLM 可以出现：

```text
SELECT FOR UPDATE
```

CLM 仍应保持：

```text
同一资源写入必须互斥。
```

平台变化时只替换目标配置和 IIR，不应重写业务模型。
