# Target Profile v0.1

Target Profile 描述 **同一份 CLM 准备在哪个技术环境中实现**。

它不是业务逻辑，也不是代码模板。

```text
CLM
 +
Target Profile
 ↓
IIR
 ↓
Target Adapter
```

## 1. 边界

CLM 保存：

- 业务规则；
- 状态；
- 行为顺序；
- 原子性、幂等、并发等要求。

Target Profile 保存：

- 目标语言；
- 运行时；
- 框架/架构；
- 数据库；
- 消息系统；
- 事务/并发/重试实现策略；
- 目标可精确支持的事务作用域；
- 明确的持久化 mapping；
- 测试框架。

Target Profile 变化通常不修改 CLM。

## 2. Schema Gate

结构以 `schemas/target-profile-v0.1.schema.json` 为准。

统一流水线在 IIR 编译前先校验：

```bash
node scripts/schema_validate.mjs \
  target-profile.json \
  schemas/target-profile-v0.1.schema.json
```

Schema valid 只表示配置形状合法，不表示当前 CLM 一定能在该 Profile 下完整实现。实现可行性由 IIR Compiler / Validator 继续判断。

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

### contract_only

只生成 Repository Contract，不生成真实 SQL。

适用于数据结构尚未确定、目标项目已有 ORM/Repository、或需要人工绑定已有数据库层。

### explicit_mapping

只有提供明确 mapping 后，Target Adapter 才可以生成 SQL/持久化 Adapter。

```json
{
  "persistence_generation": "explicit_mapping",
  "persistence_mappings": {
    "domain.order": {
      "table": "orders",
      "primary_key": "domain.order.id",
      "columns": {
        "domain.order.id": "id",
        "domain.order.status": "status",
        "domain.order.owner_id": "owner_id"
      }
    }
  }
}
```

## 5. Explicit Mapping Gate

当前 save/upsert 生成要求：

1. Repository 对应 Entity 必须有 mapping；
2. `table` 是安全 SQL identifier；
3. `primary_key` 必须引用该 Entity 的字段；
4. `primary_key` 必须存在于 `columns`；
5. save 所需 Entity 字段都有 column mapping；
6. column 名必须是安全 SQL identifier；
7. 不允许 mapping 引用其他 Entity 的字段。

缺失时进入 blocking unresolved。

```text
Target Profile Schema valid
≠
Target Profile 对当前 CLM 可完整生成
```

## 6. SQLite Adapter

当前 TypeScript Adapter 不绑定某个 SQLite npm 驱动，而生成驱动无关契约：

```ts
export interface SqliteExecutor {
  run(sql: string, params: readonly unknown[]): Promise<void>;
}
```

并根据 explicit mapping 生成稳定的 `INSERT ... ON CONFLICT ... DO UPDATE` Repository 实现。

实际项目可以把 `node:sqlite`、`better-sqlite3`、`sqlite3` 或已有数据库封装绑定到这个接口。驱动选择属于项目集成层，不反向影响 CLM。

## 7. Transaction Capability

Target Profile 使用两个字段描述事务能力：

```text
transaction_strategy
transaction_scope
```

当前 Reference Target：

```json
{
  "transaction_strategy": "sqlite_transaction",
  "transaction_scope": "full_behavior"
}
```

`transaction_scope` 当前允许：

```text
full_behavior       可以精确把整个 Behavior 实现放入一个事务
contiguous_steps    可以精确包裹 Behavior flow 中连续的一段步骤
```

当前 TypeScript + SQLite transaction layer 只实现 `full_behavior`。

因此 Atomicity Constraint 必须满足：

```text
atomicity.behavior_ref = 目标 Behavior
atomicity.members      = 该 Behavior 完整 flow，且顺序一致
```

如果 CLM 只要求部分步骤原子，而当前 Target Profile 只有 `full_behavior`，不得扩大事务范围后假装等价，IIR Gate 必须拒绝。

### 共享 SQLite 会话契约

事务 wrapper 与其内部调用的生成 Repository Adapter 必须绑定到同一个 SQLite transaction/session context。

Target Adapter 当前生成：

```ts
export interface SqliteTransactionRunner {
  transaction<T>(work: () => Promise<T>): Promise<T>;
}
```

项目集成层负责保证 `work` 内的 Repository `run(...)` 使用同一事务上下文。不能用彼此独立的数据库连接实例冒充同一事务。

## 8. Concurrency / Retry / Idempotency

Target Profile 可以提供：

```text
concurrency_strategy
retry_strategy
idempotency_strategy
```

只有 CLM 存在对应 Constraint 时才消费这些策略。

禁止仅因为 Profile 提供 retry/lock 就自动给业务流程增加行为。

## 9. Profile 版本策略

Target Profile 与 CLM/IIR 分开版本化。

破坏字段语义时升级 Target Profile Schema 版本；新增可选目标技术通常不需要升级 CLM。

## 10. 禁止事项

- 不在 Target Profile 中重定义业务规则。
- 不把 SQLite table/column 名写入 CLM。
- 不从 Entity 字段名自动猜 table/column。
- 不因 Schema valid 就跳过 IIR unresolved Gate。
- 不让 Target Adapter 自行补 missing mapping。
- 不把目标不支持的部分事务范围扩大成 whole behavior 后宣称语义等价。
