# 实现中间表示（IIR）v0.2

IIR v0.2 位于 CLM 与目标代码之间。

CLM 回答：**系统必须做什么。**

IIR 回答：**在当前 Target Profile 下准备怎样组织实现。**

```text
CLM
 ↓
Target Profile
 ↓
Primitive Binding / Technical Planning
 ↓
IIR v0.2
 ↓
Target Test Plan + Target Generator
```

## 1. 核心原则

1. IIR 不得修改业务语义。
2. 每个 IIR 节点通过 semantic refs 回到 CLM。
3. 无法确定的技术映射进入 `unresolved`。
4. Target Generator 只消费 IIR，不重新解释 CLM。
5. Target Test Plan 的 expected behavior 来自 CLM Test Vector。
6. 数据库、框架、运行时等技术选择只存在于 Target Profile / IIR。

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
    "transactions": [],
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

一个 CLM Behavior 至少映射一个 IIR Use Case。

```json
{
  "id": "usecase.order.cancel",
  "kind": "use_case",
  "semantic_id": "behavior.order.cancel",
  "guards": [],
  "steps": [],
  "dependencies": ["repository.order"]
}
```

执行顺序来自 CLM，不允许 IIR 自行重排业务逻辑。

## 4. Repository Contract

需要持久化时先生成 Repository Contract，不直接生成 SQL。

```json
{
  "id": "repository.order",
  "kind": "repository_contract",
  "semantic_refs": ["effect.order.status_write"],
  "operations": ["save"]
}
```

首个 Reference Target 使用 SQLite，但表名、列名、索引和 SQL 必须来自明确 mapping，不允许 Generator 猜测。

## 5. External Port

外部系统调用进入 Port：

```json
{
  "id": "port.payment_gateway",
  "kind": "external_port",
  "semantic_refs": ["effect.payment.refund_call"],
  "operations": ["create_refund"]
}
```

第三方 SDK adapter 默认属于 `contract_only / handwritten` 区域。

## 6. Transaction Plan

Atomicity Constraint 映射为 Transaction Plan。

首个 SQLite Target 可选择：

```json
{
  "id": "transaction.order.cancel",
  "semantic_refs": ["constraint.order.cancel.atomic"],
  "members": ["action.order.cancel.change_status"],
  "strategy": "sqlite_transaction",
  "provider": "SQLite"
}
```

SQLite 只是当前 Target Profile 的绑定，不进入 CLM。

## 7. Concurrency Plan

IIR 可以根据 Target Profile 选择 SQLite 能实际支持的并发策略。

如果 CLM 的并发要求无法被 SQLite Target 满足，必须产生 blocking unresolved，不能静默降级。

## 8. Retry / Idempotency

只有 CLM 明确存在 retry / idempotency 语义时才建立对应 Plan。

Generator 不得自行添加业务级重试或幂等规则。

## 9. Error Mapping

Semantic Error 映射到目标语言错误类型。

TypeScript Reference Target 例如：

```text
error.order.cancel_forbidden
→ OrderCancelForbiddenError
```

HTTP 状态等 transport 信息只有在 Target Profile 明确需要 API transport 时才加入。

## 10. Primitive Binding

```json
{
  "primitive_ref": "primitive.transaction.atomic_group",
  "binding": "sqlite_transaction",
  "resolved": true
}
```

未绑定 Primitive 进入 `unresolved`。

## 11. Generation Region

```text
generated        完全生成
contract_only    只生成接口/契约
handwritten      人工实现但满足契约
verified_binding 已验证基础能力绑定
```

首个 Reference Target 中：

- Use Case / Port interface / tests 可 generated；
- SQLite adapter 在 mapping 不充分时只生成 contract/TODO；
- 第三方 SDK adapter 为 handwritten。

## 12. Traceability

IIR 与 generated manifest 都必须保留 Semantic ID 映射。

```json
{
  "implementation_id": "usecase.order.cancel",
  "semantic_refs": ["behavior.order.cancel"]
}
```

## 13. Unresolved

统一表示缺失技术映射：

```json
{
  "semantic_ref": "effect.payment.refund_call",
  "reason": "目标配置没有 payment gateway binding",
  "severity": "blocking"
}
```

blocking unresolved 非空时禁止进入 Target Generator。

## 14. Node 工具

编译：

```bash
node scripts/logic_cli.mjs compile-iir model.json target-profile.json -o implementation.iir.json
```

校验：

```bash
node scripts/logic_cli.mjs validate-iir implementation.iir.json
```

## 15. v0.2 范围

当前覆盖 application/domain logic：Use Case、Guard、Assignment、Decision、Repository Contract、External Port、Transaction、Concurrency、Retry、Idempotency、Error Mapping、Primitive Binding 与 Generation Boundary。

复杂算法、协议栈、密码学等仍作为 handwritten / verified primitive 处理。
