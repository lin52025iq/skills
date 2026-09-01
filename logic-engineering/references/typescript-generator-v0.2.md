# TypeScript 目标生成器 v0.2

TypeScript Generator v0.2 是独立 Target Adapter，只消费 **已经通过 IIR v0.2 校验** 的实现中间表示和 Target Test Plan，不直接重新解释 CLM。

首个 Reference Target：

```text
TypeScript 5.x
Node.js
SQLite
Vitest
framework-agnostic
```

## 1. 输入 Gate

生成前必须满足：

```text
IIR v0.2 Schema + Semantic Gate 通过
blocking unresolved = 0
Target Profile language = TypeScript
Target Profile persistence = SQLite
Target Test Plan 已生成
```

## 2. v0.2 相比 v0.1

v0.1 只生成安全骨架；v0.2 开始生成确定性可执行语义：

```text
CLM Enum           → TypeScript string literal union
Typed Expression   → TypeScript boolean expression
Rule Guard         → 可调用 guard function
Typed Assignment   → 真实属性赋值
Write/Persist      → 已知 Repository save 调用
IIR Dependency     → constructor dependency
Scenario Expect    → Vitest 真实断言
```

如果测试 fixture 信息不足，不生成假通过断言，而是输出 `it.todo`。

## 3. 生成命令

```bash
node scripts/generate_typescript_v02.mjs \
  implementation.iir.json \
  target-test-plan.json \
  -o generated-ts
```

生成后先执行 manifest 校验：

```bash
node scripts/logic_cli.mjs verify-manifest generated-ts
```

环境已经具备 TypeScript/Vitest 时，可以进一步执行：

```bash
node scripts/verify_typescript.mjs generated-ts
```

## 4. 领域类型

IIR `domain_types` 生成：

- Enum → string literal union；
- Entity → interface；
- nullable/cardinality 保持类型约束。

例如：

```ts
export type OrderStatus =
  | "PENDING_PAYMENT"
  | "PENDING_ACCEPTANCE"
  | "PAID"
  | "CANCELLED";
```

CLM 中文名称只用于显示，不直接作为代码标识符。代码标识符从 Semantic ID 确定性派生。

## 5. Runtime Binding

IIR `runtime_bindings` 将：

```text
domain.order.status
```

映射为用例运行时槽位及字段路径，例如：

```text
order.status
```

Target Adapter 只做命名风格转换，不重新猜领域对象关系。

## 6. Guard

Typed Expression AST 确定性映射：

```text
eq      → ===
ne      → !==
lt/le   → </<=
gt/ge   → >/>=
in      → set.includes(value)
not_in  → !set.includes(value)
all     → &&
any     → ||
not     → !
```

每个 Rule Guard 生成独立函数，方便 Use Case 和测试共同调用。

## 7. Use Case

Use Case：

- 输入实体只来自 IIR `input_refs`；
- 依赖只来自 IIR `dependencies`；
- guard 顺序保持；
- action 顺序保持；
- typed assignment 生成真实赋值；
- 已知 repository effect 生成 Repository 方法调用。

未知外部语义不得由 Generator 自行补全。

## 8. SQLite

SQLite 只属于 Target Profile / IIR / Adapter 层。

v0.2 当前生成 SQLite adapter boundary 与 TODO，不在缺少明确 persistence mapping 时猜表名、列名或 SQL。

## 9. Target Test

Target Test Plan 区分：

```text
Rule Guard Case
Scenario Use Case Case
Unsupported Case
```

Rule Case 调用真实生成 guard 并断言结果。

Scenario Case 根据：

- CLM Given；
- IIR runtime bindings；
- guard fixture constraints；

构造技术测试 fixture。等值约束可以生成相同测试哨兵值；这属于测试装配，不改变业务期望。

缺少可安全构造的信息时生成 `it.todo`，禁止 `expect(true)` 伪通过。

## 10. Generated Project

生成目录至少包含：

```text
domain/generated.ts
ports/generated.ts
errors/generated.ts
rules/generated.ts
usecases/generated.ts
adapters/sqlite.ts
tests/generated.test.ts
package.json
tsconfig.json
manifest.json
```

## 11. 执行 Gate

`verify_typescript.mjs`：

1. 检查必要生成文件；
2. 查找本地或全局 `tsc`；
3. 执行 TypeScript typecheck；
4. 查找本地或全局 `vitest`；
5. 执行 Vitest。

如果工具未安装，显式返回 `TOOL_UNAVAILABLE`，不得把跳过描述成通过。

## 12. Generated Code Integrity

Manifest 保存：

- generator version；
- source CLM；
- source semantic hash；
- IIR version；
- Target Profile；
- artifact path；
- semantic refs；
- content hash。

业务修改必须回到 CLM / Semantic Change Set；直接修改 generated code 会由 manifest drift 检测发现。
