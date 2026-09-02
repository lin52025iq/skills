# 事务语义与 TypeScript/SQLite 生成

本规范描述：

```text
CLM Atomicity
→ IIR Transaction Plan
→ Target Capability Gate
→ SQLite Transaction Runner
→ Transaction-scoped Composition
→ Generated Entry Point
```

事务是业务可观察的一致性语义，不能只靠目标代码中的装饰器或注释表示。

## 1. CLM Atomicity

CLM v0.2 的原子性约束使用：

```yaml
id: constraint.order.cancel.atomic
kind: atomicity
behavior_ref: behavior.order.cancel
members:
  - action.order.cancel.step1
  - action.order.cancel.step2
```

要求：

- `behavior_ref` 必须引用 Behavior；
- `members` 必须属于该 Behavior 顶层 flow；
- members 按 flow 顺序形成连续区间；
- 不允许由 Target Adapter 自行扩大或缩小原子范围。

CLM Validator 在 IIR 编译前检查这些条件。

## 2. IIR Transaction Plan

IIR 保存：

```json
{
  "id": "plan.constraint.order.cancel.atomic",
  "kind": "transaction_plan",
  "semantic_refs": ["constraint.order.cancel.atomic"],
  "behavior_ref": "behavior.order.cancel",
  "members": [
    "action.order.cancel.step1",
    "action.order.cancel.step2"
  ],
  "strategy": "sqlite_transaction",
  "provider": "SQLite",
  "start_index": 0,
  "end_index": 1,
  "boundary_valid": true
}
```

Use Case 通过 `transaction_plan_ids` 引用对应计划。

## 3. Target Capability

Target Profile 用：

```text
transaction_strategy
transaction_scope
```

表达可实现能力。

当前 Reference Target：

```text
transaction_strategy = sqlite_transaction
transaction_scope    = full_behavior
```

`full_behavior` 表示目标实现可以保证整个 Behavior flow 使用同一事务边界。

当前生成器不支持只包裹部分连续步骤，因此：

```text
Atomicity members = 完整 Behavior flow  → 可生成
Atomicity members = flow 的部分区间     → IIR Gate 拒绝
```

禁止为了适配生成器而扩大业务要求中的事务范围。

## 4. SQLite Transaction Runner

生成：

```ts
export interface SqliteTransactionRunner {
  transaction<T>(
    work: (executor: SqliteExecutor) => Promise<T>
  ): Promise<T>;
}
```

默认实现使用：

```text
BEGIN IMMEDIATE
→ work(transactionExecutor)
→ COMMIT
```

异常时：

```text
BEGIN IMMEDIATE
→ work(transactionExecutor)
→ error
→ ROLLBACK
→ rethrow
```

## 5. 为什么 callback 必须接收 SqliteExecutor

错误做法：

```text
提前构造 Repository
→ 提前构造 Use Case
→ transaction(() => useCase.execute())
```

这不能证明 Repository 使用的是事务内 SQLite 会话。

正确路径：

```text
transaction(executor =>
  用 executor 构造 Repository
  → 用 Repository 构造 Use Case
  → execute
)
```

因此 Transactional Use Case 接收 **transaction-scoped factory**，而不是预构造的 inner Use Case。

## 6. Transactional Wrapper

生成形态：

```ts
export type CancelOrderUseCaseFactory = (
  executor: SqliteExecutor
) => Pick<CancelOrderUseCase, "execute">;

export class TransactionalCancelOrderUseCase {
  constructor(
    private readonly createInner: CancelOrderUseCaseFactory,
    private readonly transactions: SqliteTransactionRunner,
  ) {}

  async execute(input: CancelOrderUseCaseInput): Promise<void> {
    await this.transactions.transaction(async (executor) => {
      const inner = this.createInner(executor);
      await inner.execute(input);
    });
  }
}
```

## 7. 自动 Composition

当 Use Case 的全部依赖都能由已生成 SQLite Repository Adapter 满足时，系统继续生成：

```text
composition/generated.ts
```

例如：

```ts
export function createTransactionalCancelOrderUseCase(
  db: SqliteExecutor,
): TransactionalCancelOrderUseCase {
  const transactions = new DefaultSqliteTransactionRunner(db);
  return new TransactionalCancelOrderUseCase(
    (executor) => new CancelOrderUseCase(
      new OrderSqliteRepository(executor),
    ),
    transactions,
  );
}
```

这个 factory 是当前实现推荐的正式入口。

## 8. External Port 边界

如果事务 Use Case 同时依赖：

```text
Repository
+ External Port
```

而 Target Profile 没有 External Port 的明确 adapter/composition binding，则不能自动补全 composition。

此时：

- Transactional Wrapper 仍可生成；
- manifest 记录 `manual_composition`；
- 不把 wrapper 标成 fully composed；
- 不猜第三方 SDK 或网络调用实例。

## 9. Manifest

有事务的 Use Case 应在 manifest 中保存：

```text
implementation_id
transaction_plan_id
artifact
export_name
fully_composed
requires_transaction_scoped_factory
```

如果自动 composition 成功，正式 implementation entrypoint 指向：

```text
composition/generated.ts
createTransactional...
```

而不是事务外 Base Use Case。

## 10. 测试

事务层至少生成：

1. 成功时 BEGIN → COMMIT；
2. 失败时 BEGIN → ROLLBACK；
3. callback 收到 transaction executor；
4. wrapper 在事务回调内调用 factory；
5. factory 使用 transaction executor 构造 inner；
6. inner execute 只调用一次。

专项回归：

```bash
npm run regression:transaction
```

## 11. 当前限制

当前 TypeScript + SQLite transaction layer：

- 支持 `full_behavior`；
- 不支持部分步骤事务生成；
- 不支持嵌套事务语义；
- 不自动决定外部调用是否应该位于数据库事务内；
- 不自动增加 retry；
- 不自动改变 isolation level。

这些能力必须由后续 CLM/IIR/Target Profile 明确表达后才能扩展。

## 12. 禁止事项

- 不用预构造 Repository 冒充 transaction-scoped Repository。
- 不把 partial atomicity 自动扩大成 full behavior。
- 不把 `BEGIN/COMMIT` 字符串存在代码里就视为事务正确。
- 不绕过 manifest 的正式 transaction entrypoint。
- 不让 generated transaction layer 修改 CLM 业务步骤顺序。
