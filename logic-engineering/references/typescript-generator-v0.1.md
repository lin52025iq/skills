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

- Use Case class / execute 方法骨架；
- Guard 顺序保留；
- Typed Assignment；
- Repository Contract interface；
- External Port interface；
- Typed Error；
- SQLite adapter contract/TODO；
- Generated Manifest；
- 基于 Target Test Plan 的 Vitest 测试骨架。

暂不自动实现未绑定 Primitive、第三方 SDK adapter、复杂事务协调、分布式锁、retry/backoff、消息队列 producer 和缺少语义的数据映射。

这些情况必须出现在 IIR `unresolved` 或 generation boundary 中，不允许 Generator 自行补全。

## 2. 输入 Gate

```text
IIR v0.2 valid
blocking unresolved = 0
Target Profile language = TypeScript
Target Profile persistence = SQLite
```

## 3. 生成命令

```bash
node scripts/logic_cli.mjs generate-ts \
  implementation.iir.json \
  target-test-plan.json \
  -o generated-ts
```

生成后：

```bash
node scripts/logic_cli.mjs verify-manifest generated-ts
```

## 4. Repository Contract

IIR Repository Contract 映射为 TypeScript interface。

```ts
export interface OrderRepository {
  save(): Promise<void>;
}
```

如果输入/输出类型尚未在 IIR 确定，不允许猜测参数。

SQLite 属于目标实现策略，不进入 CLM。实际 SQLite adapter 实现生成的 Repository Contract。

## 5. External Port

外部能力映射为 interface。第三方系统 adapter 默认属于人工/独立实现区域。

## 6. Use Case

每个 IIR Use Case 映射为 class，执行顺序必须保持：

```text
guards
→ steps
→ postconditions / effects
```

依赖只能来自 IIR `dependencies`。

## 7. Typed Assignment

typed assignment 应生成确定性的 TypeScript 赋值。枚举值优先映射为 enum / literal union，不生成魔法字符串。

## 8. SQLite

目标配置：

```text
persistence = SQLite
transaction_strategy = sqlite_transaction
```

IIR 决定 Repository Contract 和事务边界；Generator 不把 SQL 细节写回 CLM。

第一版只生成 SQLite adapter contract/TODO；缺少字段映射时不猜表结构。

## 9. Tests

测试代码只消费 Target Test Plan，默认使用 Vitest。

保留 Given / When / Expect；未知 fixture 只生成明确 TODO，不虚构领域数据。

## 10. Manifest

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

## 11. Generated Code Integrity

生成代码默认不可作为业务事实源。通过 Node CLI 的 `verify-manifest` 检测人工漂移；业务修改必须回到 CLM / Change Set。
