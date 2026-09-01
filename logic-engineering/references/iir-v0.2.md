# 实现中间表示（IIR）v0.2

IIR v0.2 是 CLM 与目标代码之间的技术实现模型。

CLM 回答：**系统必须做什么。**

IIR 回答：**在当前目标技术栈中，这些语义准备怎样组织成可生成的实现。**

```text
CLM
 ↓
Target Profile
 ↓
Primitive Binding / Technical Planning
 ↓
IIR v0.2
 ↓
Target Test Generator + Target Code Generator
```

## 1. 核心原则

1. IIR 不得修改业务语义。
2. 每个 IIR 节点必须通过 `semantic_refs` 回到 CLM。
3. 所有无法确定的技术映射必须进入 `unresolved`。
4. 目标生成器只能消费 IIR，不直接重新解释 CLM。
5. 目标测试生成器优先消费 CLM 派生的 test vectors，IIR 只补充测试技术装配信息。
6. IIR 中允许出现框架、数据库、消息系统等技术选择，但这些不得反向污染 CLM。

## 2. 顶层结构

```json
{
  "iir": {
    "version": "0.2",
    "source_clm_id": "module.order",
    "source_clm_version": "0.2",
    "source_semantic_hash": "...",
    "target_profile": {},
    "use_cases": [],
    "repository_contracts": [],
    "external_ports": [],
    "transaction_plans": [],
    "concurrency_plans": [],
    "retry_plans": [],
    "idempotency_plans": [],
    "error_mappings": [],
    "primitive_bindings": [],
    "generation_regions": [],
    "traceability": [],
    "unresolved": []
  }
}
```

## 3. Use Case

一个 CLM Behavior 对应至少一个 IIR Use Case。

```json
{
  "id": "usecase.order.cancel",
  "kind": "use_case",
  "semantic_refs": ["behavior.order.cancel"],
  "inputs": [],
  "guards": [],
  "steps": [],
  "outputs": [],
  "failure_refs": [],
  "dependencies": [
    "repository.order",
    "port.payment.refund"
  ]
}
```

### Guard

Guard 直接保存 CLM Typed Expression：

```json
{
  "semantic_ref": "rule.order.cancel.allowed_status",
  "expression": {},
  "failure_ref": "error.order.cancel_forbidden"
}
```

### Step

第一版支持：

```text
assign
invoke
persist
emit
foreach
decision
```

Step 必须保存原始 `semantic_ref`。

## 4. Repository Contract

如果 Use Case 需要持久化实体，IIR 生成 Repository Contract，而不是直接生成 SQL。

```json
{
  "id": "repository.order",
  "kind": "repository_contract",
  "entity_ref": "domain.order",
  "operations": [
    {
      "name": "save",
      "semantic_refs": ["effect.order.status_write"]
    }
  ],
  "binding": {
    "strategy": "relational",
    "provider": "postgres"
  }
}
```

具体 SQL、ORM、表名属于目标 Generator / Adapter 层。

## 5. External Port

外部系统调用必须进入 Port：

```json
{
  "id": "port.payment.refund",
  "kind": "external_port",
  "system": "payment_gateway",
  "operations": [
    {
      "name": "create_refund",
      "semantic_refs": ["effect.payment.refund_call"]
    }
  ],
  "generation_mode": "contract_only"
}
```

不要由业务 Use Case 直接绑定具体 SDK。

## 6. Transaction Plan

Atomicity / Transaction Constraint 映射为：

```json
{
  "id": "transaction.order.cancel",
  "kind": "transaction_plan",
  "semantic_refs": ["constraint.order.cancel.atomic"],
  "members": [
    "action.order.cancel.change_status",
    "action.order.cancel.save_reason"
  ],
  "strategy": "local_database_transaction",
  "provider": "postgres"
}
```

如果 Target Profile 无法满足 CLM atomicity，必须加入 `unresolved`。

## 7. Concurrency Plan

```json
{
  "id": "concurrency.account.balance",
  "kind": "concurrency_plan",
  "semantic_refs": ["constraint.account.balance_exclusive_write"],
  "resource_ref": "domain.account.balance",
  "scope": "same_account",
  "strategy": "database_row_lock",
  "key_ref": "domain.account.id"
}
```

## 8. Retry Plan

```json
{
  "id": "retry.inventory.release",
  "kind": "retry_plan",
  "semantic_refs": ["constraint.inventory.release_retry"],
  "operation_ref": "effect.inventory.release_call",
  "strategy": "exponential_backoff",
  "max_attempts": 3
}
```

没有 CLM retry semantics 时，不允许 Generator 自己增加业务级重试。

## 9. Idempotency Plan

```json
{
  "id": "idempotency.payment.refund",
  "kind": "idempotency_plan",
  "semantic_refs": ["constraint.payment.refund_idempotent"],
  "operation_ref": "effect.payment.refund_call",
  "key_ref": "domain.order.id",
  "strategy": "idempotency_key"
}
```

## 10. Error Mapping

```json
{
  "id": "error_mapping.order.cancel_forbidden",
  "semantic_error_ref": "error.order.cancel_forbidden",
  "target_error": "OrderCancelForbidden",
  "transport": {
    "http_status": 409
  }
}
```

Transport mapping 只有在目标应用需要 HTTP/API 层时才生成。

## 11. Primitive Binding

```json
{
  "primitive_ref": "primitive.transaction.atomic_group",
  "binding": "postgres_transaction",
  "resolved": true
}
```

未绑定 Primitive 必须进入 `unresolved`。

## 12. Generation Region

每个产物区域必须明确归属：

```json
{
  "id": "region.order.cancel.usecase",
  "mode": "generated",
  "semantic_refs": ["behavior.order.cancel"]
}
```

支持：

```text
generated       完全生成
contract_only   只生成接口/契约
handwritten     人工实现但必须满足契约
verified_binding 已验证基础能力绑定
```

## 13. Traceability

```json
{
  "implementation_id": "usecase.order.cancel",
  "semantic_refs": [
    "behavior.order.cancel",
    "rule.order.cancel.allowed_status"
  ],
  "expected_artifact_kinds": [
    "use_case",
    "unit_test"
  ]
}
```

后续 Generator 输出 manifest 时必须继续保存这条映射。

## 14. Unresolved

统一格式：

```json
{
  "semantic_ref": "effect.payment.refund_call",
  "reason": "目标配置没有 payment gateway binding",
  "required_for": "usecase.order.cancel",
  "severity": "blocking"
}
```

`unresolved` 存在 blocking 项时禁止宣称目标实现完整。

## 15. IIR v0.2 冻结边界

IIR v0.2 第一阶段只覆盖 application/domain logic：

- Use Case orchestration
- Guard / Rule
- Assignment / Decision
- Repository Contract
- External Port
- Transaction
- Concurrency
- Retry
- Idempotency
- Error Mapping
- Primitive Binding
- Generation Boundary

复杂算法、协议栈、密码学等继续作为 `handwritten / verified primitive` 处理。