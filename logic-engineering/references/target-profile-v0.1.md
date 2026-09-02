# Target Profile v0.1

Target Profile 描述 **同一份 CLM 准备在哪个技术环境中实现**。它不是业务逻辑，也不是代码模板。

```text
CLM + Target Profile
→ IIR
→ Target Adapter
```

## 1. 边界

CLM 保存业务规则、状态、行为顺序，以及原子性、幂等、并发等要求。

Target Profile 保存：目标语言、运行时、框架/架构、数据库、消息系统、事务/并发/重试实现策略、可精确支持的事务作用域、显式 persistence mapping 和测试框架。

Target Profile 变化通常不修改 CLM。

## 2. Schema Gate

结构以 `schemas/target-profile-v0.1.schema.json` 为准。

```bash
node scripts/schema_validate.mjs target-profile.json schemas/target-profile-v0.1.schema.json
```

Schema valid 只表示配置形状合法，不表示当前 CLM 一定能完整实现。实现可行性由 IIR Compiler / Validator 继续判断。

条件要求：

- 声明 `transaction_strategy` 时必须同时声明 `transaction_scope`；
- `persistence_generation=explicit_mapping` 时必须提供 `persistence_mappings`。

## 3. 当前 Reference Target

```json
{
  "target_profile": {
    "id": "ts-sqlite",
    "language": "TypeScript",
    "runtime": "Node.js",
    "persistence": "SQLite",
    "transaction_strategy": "sqlite_transaction",
    "transaction_scope": "full_behavior",
    "test_framework": "Vitest"
  }
}
```

当前 Reference Target 用于验证逻辑编译闭环，不限制未来增加其他语言、运行时或数据库 Adapter。

## 4. Persistence Generation

支持：

```text
contract_only
explicit_mapping
```

`contract_only` 只生成 Repository Contract。

`explicit_mapping` 只有在 Entity 明确声明 table、primary key 和全部必要 columns 后才允许生成 SQL：

```json
{
  "persistence_generation": "explicit_mapping",
  "persistence_mappings": {
    "domain.order": {
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

缺失或错误 mapping 进入 blocking unresolved。

## 5. SQLite Adapter

当前 TypeScript Adapter 生成驱动无关契约：

```ts
export interface SqliteExecutor {
  run(sql: string, params: readonly unknown[]): Promise<void>;
}
```

以及由 explicit mapping 确定性生成的 `INSERT ... ON CONFLICT ... DO UPDATE` Repository。

具体使用 `node:sqlite`、`better-sqlite3` 或其他驱动属于项目集成层。

## 6. Transaction Capability

Target Profile 使用：

```text
transaction_strategy
transaction_scope
```

当前 Reference Target：

```text
sqlite_transaction
full_behavior
```

`full_behavior` 表示目标实现只能在 **Atomicity members 完整覆盖 Behavior flow** 时准确生成事务。

如果 CLM 只要求 flow 中部分步骤原子，当前 Target 不能通过扩大事务范围冒充等价实现，IIR Gate 必须拒绝。

详细规则见 `references/transaction-generation.md`。

## 7. Transaction-scoped SQLite Session

事务能力必须把实际事务内 executor 暴露给 composition：

```ts
export interface SqliteTransactionRunner {
  transaction<T>(
    work: (executor: SqliteExecutor) => Promise<T>
  ): Promise<T>;
}
```

正确路径：

```text
BEGIN
→ transaction executor
→ 用 executor 构造 Repository
→ 构造 Use Case
→ execute
→ COMMIT / ROLLBACK
```

禁止提前用事务外 executor 构造 Repository，再仅在外层包一个 `transaction(...)`。

## 8. Automatic Composition

当事务 Use Case 的全部依赖都是已生成 SQLite Repository 时，Target Adapter 可以自动生成 composition factory。

如果仍存在 External Port 或没有明确 adapter 的依赖：

- 不猜第三方实现；
- manifest 标记 `manual_composition`；
- Transactional Wrapper 可以生成，但不能宣称 fully composed。

## 9. Concurrency / Retry / Idempotency

Profile 可以提供：

```text
concurrency_strategy
retry_strategy
idempotency_strategy
```

只有 CLM 已存在对应 Constraint 时才消费这些策略。禁止仅因为 Profile 有配置就给业务流程新增行为。

## 10. 版本策略

Target Profile 与 CLM/IIR 分开版本化。破坏字段语义时升级 Target Profile Schema；增加目标技术通常不需要修改 CLM。

## 11. 禁止事项

- 不在 Target Profile 中重定义业务规则。
- 不把 SQLite table/column 名写入 CLM。
- 不从 Entity 字段名猜 table/column。
- 不因 Schema valid 就跳过 IIR unresolved Gate。
- 不让 Target Adapter 补 missing mapping。
- 不扩大 Atomicity 范围后宣称等价。
- 不让事务外 Repository 冒充 transaction-scoped Repository。
