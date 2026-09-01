# TypeScript 目标生成器 v0.1

TypeScript Generator 只消费 **已经通过 IIR v0.2 校验** 的实现中间表示，不直接从 CLM 猜测技术实现。

首个参考目标：

```text
TypeScript 5.x
+ Node.js
+ SQLite
+ Vitest
+ framework-agnostic
```

## 1. 第一版范围

支持：

- Use Case class / constructor / execute 方法骨架；
- Guard 顺序保留；
- Typed Assignment；
- Repository Contract interface；
- External Port interface；
- Typed Error class；
- SQLite repository contract / transaction binding 占位；
- Generated Manifest；
- 基于 Target Test Plan 的 Vitest 测试骨架。

暂不自动实现：

- 未绑定 Primitive；
- 第三方 SDK adapter；
- 复杂事务协调；
- 分布式锁；
- retry/backoff 细节；
- 消息队列具体 producer；
- 需要业务语义猜测的数据映射。

上述情况必须出现在 IIR `unresolved` 或 generation boundary 中，不允许生成器自行补全。

## 2. 输入 Gate

生成前必须满足：

```text
IIR v0.2 schema valid
IIR semantic validator valid
blocking unresolved = 0
Target Profile language = TypeScript
```

任一不满足则拒绝生成。

## 3. 输出目录

```text
generated-ts/
├── manifest.json
├── domain/
├── usecases/
├── ports/
├── errors/
└── tests/
```

## 4. Repository Contract

IIR Repository Contract 映射为 TypeScript interface。

```ts
export interface OrderRepository {
  save(): Promise<void>;
}
```

如果参数或返回类型尚未在 IIR 确定，不允许自行猜测；骨架模式中保留 TODO，正式模式阻断。

SQLite 属于目标实现策略，不进入 CLM。实际 SQLite adapter 应实现生成的 Repository Contract。

## 5. External Port

外部能力映射为 interface。第三方系统 adapter 默认是人工/独立实现区域。

## 6. Use Case

每个 IIR Use Case 映射为 class：

```ts
export class CancelOrderUseCase {
  constructor(private readonly orderRepository: OrderRepository) {}

  async execute(): Promise<void> {
    // guards
    // steps
  }
}
```

依赖只能来自 IIR `dependencies`。

执行顺序必须严格保持：

```text
guards
→ steps
→ postconditions / effects
```

## 7. Typed Assignment

CLM / IIR 的 typed assignment 应生成确定性的 TypeScript 赋值。枚举值优先映射为生成的 enum / literal union，不生成魔法字符串。

## 8. SQLite

首个参考实现使用 SQLite。

目标配置：

```text
persistence = SQLite
transaction_strategy = sqlite_transaction
```

IIR 负责决定 Repository Contract 和事务边界；Generator 不把 SQL 细节写回 CLM。

第一版可以只生成 SQLite adapter contract/TODO，不应在缺少字段映射时猜测表结构。

## 9. Typed Error

Semantic Error 映射为稳定 TypeScript Error class：

```ts
export class OrderCancelForbiddenError extends Error {}
```

名称从 Semantic ID 确定性转换。

## 10. Tests

测试代码只消费 Target Test Plan，默认生成 Vitest：

```ts
import { describe, expect, it } from "vitest";
```

保留 Given / When / Expect，并为未知 fixture 生成明确 TODO，不虚构领域数据。

## 11. Manifest

必须生成：

```json
{
  "generator": "typescript-v0.1",
  "source_clm": "module.order",
  "source_semantic_hash": "...",
  "iir_version": "0.2",
  "target_profile": "ts-sqlite",
  "artifacts": []
}
```

每个 artifact 保存 path、semantic_refs、generation_mode、content_hash。

## 12. Generated Code Integrity

生成代码默认不可作为业务事实源。使用 `verify_generated_manifest.py` 检测人工漂移；业务修改回到 CLM / Change Set。
