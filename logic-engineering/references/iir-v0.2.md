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
    "domain_types": { "enums": [], "entities": [] },
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
  "entities": [
    {
      "semantic_ref": "domain.order",
      "name": "Order",
      "display_name": "订单",
      "slot": "order",
      "fields": [
        {
          "semantic_ref": "domain.order.items",
          "name": "items",
          "type_ref": "domain.order_item",
          "cardinality": "many"
        }
      ]
    }
  ]
}
```

`name` 是确定性代码名；`display_name` 可以保留中文。

`cardinality` 必须保留到 IIR，因为 Target Adapter 需要据此区分标量与数组/集合。

## 4. Runtime Bindings

Runtime Binding 把稳定 Semantic Ref 映射到用例运行时槽位和字段路径。

```json
{
  "semantic_ref": "domain.order.status",
  "kind": "field",
  "entity_ref": "domain.order",
  "slot": "order",
  "path": ["status"],
  "type_ref": "domain.order_status"
}
```

Target Adapter 据此生成：

```text
domain.order.status
→ input.order.status
```

Target Adapter 不能重新猜实体关系。

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
  "expression": { "op": "in" },
  "failure_ref": null
}
```

目标语言 Adapter 只做 AST → 目标语法转换。

## 7. Step

当前确定性 Step 至少覆盖：

```text
Action / assign
Decision
Foreach
```

Invoke / Persist / Emit 等通过 Effect + Port/Repository Contract 映射。

每个 Step 必须保留 `semantic_ref`。

### 7.1 Decision

IIR 不保留裸 `then/else` ID 列表，而是递归展开：

```json
{
  "kind": "decision",
  "semantic_ref": "decision.order.route",
  "when": {},
  "then_steps": [],
  "else_steps": []
}
```

这样 Target Adapter 可以确定性生成 `if/else`，并继续追踪分支内 Effect 和 dependency。

### 7.2 Foreach

```json
{
  "kind": "foreach",
  "semantic_ref": "action.order.foreach_reserved_items",
  "collection_ref": "domain.order.items",
  "item_alias": "item",
  "item_type": "domain.order_item",
  "when": {},
  "do_steps": []
}
```

其中：

- `collection_ref` 必须来自 `cardinality=many` 的 Entity field；
- `item_type` 由 collection field 的 `type_ref` 推导；
- `do_steps` 使用 scoped item 语义；
- 子步骤可以引用 `item.xxx`，但这些 scoped refs 不进入 Use Case 的全局 `input_refs`。

当前 v0.2 暂不支持内层 foreach 的 collection 来自外层 `item.xxx`。这种情况进入 blocking unresolved。

## 8. Repository Contract 与 Persistence Mapping

需要持久化时先形成 Repository Contract，不直接把 SQL 写入 CLM。

```json
{
  "id": "repository.order",
  "kind": "repository_contract",
  "entity_ref": "domain.order",
  "semantic_refs": ["effect.order.status_write"],
  "operations": [
    { "name": "save", "semantic_refs": ["effect.order.status_write"] }
  ],
  "binding": {
    "strategy": "repository",
    "provider": "SQLite",
    "mapping": {
      "table": "orders",
      "primary_key": "domain.order.id",
      "columns": {
        "domain.order.id": "id",
        "domain.order.status": "status"
      }
    }
  }
}
```

显式 mapping 来自 Target Profile，不由 IIR 或 Generator 猜测。

`persistence_generation=explicit_mapping` 时，IIR Compiler 必须检查：

- Entity mapping 存在；
- table / column 是安全 identifier；
- primary key 属于当前 Entity；
- primary key 已映射；
- save 所需 Entity 字段均有 column mapping。

不满足时进入 blocking unresolved。

详见 `references/target-profile-v0.1.md`。

## 9. External Port

外部系统调用进入 Port，第三方 SDK adapter 默认属于 `contract_only / handwritten` 区域。

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

## 13. Generation Region

```text
generated        完全生成
contract_only    只生成接口/契约
handwritten      人工实现但必须满足契约
verified_binding 已验证基础能力绑定
```

## 14. Traceability

Traceability 必须递归覆盖 Decision/Foreach 子步骤中的 Semantic ID，不只记录顶层 Flow。

## 15. Unresolved

```json
{
  "semantic_ref": "constraint.account.balance_exclusive_write",
  "reason": "Target Profile 缺少 concurrency_strategy",
  "required_for": "constraint.account.balance_exclusive_write",
  "severity": "blocking"
}
```

blocking unresolved 非空时禁止 Target Adapter 生成“完整实现”。

## 16. IIR Gate

```bash
node scripts/compile_iir.mjs model.json target-profile.json -o implementation.iir.json
node scripts/schema_validate.mjs implementation.iir.json schemas/iir-v0.2.schema.json
node scripts/validate_iir.mjs implementation.iir.json
```

至少确认：

```text
IIR Schema valid
Use Case dependency valid
Domain Types / Runtime Bindings 完整
Decision/Foreach 结构完整
显式 Persistence Mapping 完整
必要技术策略已确定
Traceability 覆盖
blocking unresolved = 0
```

## 17. IIR 不反向污染 CLM

SQLite、TypeScript、Node.js、`for...of`、SQL 等都属于 Target 层，不得写回 CLM 业务语义。
