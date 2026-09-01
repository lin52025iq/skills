# 实现中间表示（IIR）v0.2

IIR v0.2 位于 CLM 与目标代码之间。

CLM 回答：**系统必须做什么。**

IIR 回答：**在当前 Target Profile 下准备怎样组织实现。**

```text
CLM
 ↓
Target Profile
 ↓
Technical Planning / Primitive Binding
 ↓
IIR v0.2
 ↓
Target Test Plan + Target Adapter
```

## 1. 核心原则

1. IIR 不得修改业务语义。
2. 每个实现节点必须能通过 Semantic Ref 回到 CLM。
3. 无法确定的技术映射进入 `unresolved`。
4. Target Adapter 只消费 IIR，不重新解释 CLM。
5. Target Test Plan 的 expected behavior 来自 CLM Test Vector。
6. 数据库、框架、运行时等技术选择只存在于 Target Profile / IIR。
7. Target Adapter 需要的领域运行时形状必须由 IIR 显式提供，不允许自行从 Semantic ID 猜对象结构。

## 2. 顶层结构

```json
{
  "iir": {
    "version": "0.2",
    "source_clm_id": "module.order",
    "source_clm_version": "0.2",
    "source_semantic_hash": "...",
    "target_profile": {},
    "domain_types": {
      "enums": [],
      "entities": []
    },
    "runtime_bindings": [],
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

## 3. Domain Types

CLM Domain 在 IIR 中形成目标实现所需的类型投影，但仍保留 Semantic Ref。

```json
{
  "enums": [
    {
      "semantic_ref": "domain.order_status",
      "name": "OrderStatus",
      "display_name": "订单状态",
      "values": ["PENDING_PAYMENT", "CANCELLED"]
    }
  ],
  "entities": [
    {
      "semantic_ref": "domain.order",
      "name": "Order",
      "display_name": "订单",
      "slot": "order",
      "fields": [
        {
          "semantic_ref": "domain.order.status",
          "name": "status",
          "type_ref": "domain.order_status"
        }
      ]
    }
  ]
}
```

`name` 是确定性代码名，从 Semantic ID 派生；`display_name` 可以保留中文。

禁止直接拿自然语言显示名作为目标语言标识符。

## 4. Runtime Bindings

Runtime Binding 把稳定 Semantic Ref 映射到用例运行时槽位和字段路径。

```json
[
  {
    "semantic_ref": "domain.order",
    "kind": "entity",
    "slot": "order"
  },
  {
    "semantic_ref": "domain.order.status",
    "kind": "field",
    "entity_ref": "domain.order",
    "slot": "order",
    "path": ["status"]
  }
]
```

Target Adapter 据此生成：

```text
domain.order.status
→ input.order.status
```

Target Adapter 只能做目标语言命名风格转换，不能重新猜实体关系。

## 5. Use Case

一个 CLM Behavior 至少映射一个 IIR Use Case。

```json
{
  "id": "usecase.order.cancel",
  "kind": "use_case",
  "semantic_refs": ["behavior.order.cancel"],
  "name": "OrderCancel",
  "display_name": "取消订单",
  "input_refs": ["domain.order", "domain.current_user"],
  "guards": [],
  "steps": [],
  "dependencies": ["repository.order"]
}
```

执行顺序来自 CLM，不允许 IIR 自行重排业务逻辑。

## 6. Guard

Guard 保存 CLM Typed Expression：

```json
{
  "semantic_ref": "rule.order.cancel.allowed_status",
  "expression": {
    "op": "in"
  },
  "failure_ref": null
}
```

目标语言 Generator 只做 AST → 目标语法转换。

## 7. Step

第一阶段至少支持：

```text
Action / assign
Decision
Foreach
Invoke
Persist
Emit
```

每个 Step 必须保留 `semantic_ref`。

当前 TypeScript v0.2 Adapter 已实现确定性的 `assign` 与已知 effect 调用；Decision / Foreach 的完整可执行展开仍属于下一阶段。

## 8. Repository Contract

需要持久化时先形成 Repository Contract，不直接把 SQL 写入 CLM。

```json
{
  "id": "repository.order",
  "kind": "repository_contract",
  "entity_ref": "domain.order",
  "semantic_refs": ["effect.order.status_write"],
  "operations": [
    {
      "name": "save",
      "semantic_refs": ["effect.order.status_write"]
    }
  ],
  "binding": {
    "strategy": "repository",
    "provider": "SQLite"
  }
}
```

首个 Reference Target 使用 SQLite，但表名、列名、索引和 SQL 必须来自明确 persistence mapping；缺少 mapping 时只生成 adapter boundary/TODO。

## 9. External Port

外部系统调用进入 Port：

```json
{
  "id": "port.payment_gateway",
  "kind": "external_port",
  "system": "payment_gateway",
  "semantic_refs": ["effect.payment.refund_call"],
  "operations": [
    {
      "name": "create_refund"
    }
  ],
  "generation_mode": "contract_only"
}
```

第三方 SDK adapter 默认属于 `contract_only / handwritten` 区域。

## 10. Transaction Plan

Atomicity Constraint 映射为 Transaction Plan。

```json
{
  "id": "plan.constraint.order.cancel.atomic",
  "kind": "transaction_plan",
  "semantic_refs": ["constraint.order.cancel.atomic"],
  "members": ["action.order.cancel.change_status"],
  "strategy": "sqlite_transaction",
  "provider": "SQLite"
}
```

如果 Target Profile 无法满足 atomicity，必须进入 blocking unresolved。

## 11. Concurrency / Retry / Idempotency

这些计划只在 CLM 已有对应语义时生成。

禁止 Target Adapter 自行增加业务级 retry、lock 或幂等行为。

缺少必要技术策略时进入 blocking unresolved。

## 12. Error Mapping

```json
{
  "id": "error_mapping.order.cancel_forbidden",
  "semantic_error_ref": "error.order.cancel_forbidden",
  "target_error": "OrderCancelForbiddenError"
}
```

Transport mapping 只有在目标接口协议需要时才进入 IIR。

## 13. Generation Region

```text
generated        完全生成
contract_only    只生成接口/契约
handwritten      人工实现但必须满足契约
verified_binding 已验证基础能力绑定
```

每个 Region 保留 Semantic Ref。

## 14. Traceability

```json
{
  "implementation_id": "usecase.order.cancel",
  "semantic_refs": [
    "behavior.order.cancel",
    "rule.order.cancel.allowed_status",
    "action.order.cancel.change_status"
  ]
}
```

后续 Generated Manifest 继续保存这条链。

## 15. Unresolved

统一格式：

```json
{
  "semantic_ref": "constraint.account.balance_exclusive_write",
  "reason": "Target Profile 缺少 concurrency_strategy",
  "required_for": "constraint.account.balance_exclusive_write",
  "severity": "blocking"
}
```

blocking unresolved 非空时禁止 Target Adapter 生成“完整实现”。

warning unresolved 可以继续生成，但必须保留风险说明。

## 16. IIR Gate

代码生成前至少检查：

```text
IIR Schema valid
Use Case dependency valid
Domain Types / Runtime Bindings 完整
Repository / Port 契约完整
必要技术策略已确定
Traceability 覆盖
blocking unresolved = 0
```

工具：

```bash
node scripts/compile_iir.mjs model.json target-profile.json -o implementation.iir.json
node scripts/schema_validate.mjs implementation.iir.json schemas/iir-v0.2.schema.json
node scripts/logic_cli.mjs validate-iir implementation.iir.json
```

## 17. IIR 不反向污染 CLM

例如 IIR 选择 SQLite，不意味着 CLM 可以出现：

```text
BEGIN IMMEDIATE
PRAGMA
SQL table name
```

CLM 仍只表达业务所需的原子性、互斥、持久化等语义。
