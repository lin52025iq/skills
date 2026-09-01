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

## 2. v0.2 可执行语义

```text
CLM Enum           → TypeScript string literal union
Entity cardinality → 标量 / 数组类型
Typed Expression   → TypeScript boolean expression
Rule Guard         → 可调用 guard function
Typed Assignment   → 真实属性赋值
Decision           → if / else
Foreach            → for...of + scoped item
Write/Persist      → 已知 Repository save 调用
IIR Dependency     → constructor dependency
Scenario Expect    → Vitest 真实断言
```

测试 fixture 信息不足时输出 `it.todo`，不生成假通过断言。

## 3. 生成命令

```bash
node scripts/generate_typescript_v02.mjs \
  implementation.iir.json \
  target-test-plan.json \
  -o generated-ts
```

生成后：

```bash
node scripts/logic_cli.mjs verify-manifest generated-ts
node scripts/validate_generated_typescript.mjs generated-ts
```

环境具备 TypeScript/Vitest 时进一步执行：

```bash
node scripts/verify_typescript.mjs generated-ts
```

## 4. 领域类型

IIR `domain_types` 生成：

- Enum → string literal union；
- Entity → interface；
- nullable 保持可空约束；
- `cardinality=many` → `T[]`。

例如：

```ts
export type OrderStatus = "PENDING_PAYMENT" | "CANCELLED";

export interface Order {
  items: OrderItem[];
}
```

代码标识符从 Semantic ID 确定性派生；中文名称只作为显示信息。

## 5. Runtime Binding

IIR `runtime_bindings` 将稳定 Semantic Ref 映射为目标运行时路径，例如：

```text
domain.order.status
→ input.order.status
```

Target Adapter 不重新猜领域对象关系。

Foreach scoped ref 不进入全局 runtime binding，而由 IIR Foreach Step 的 `item_alias / item_type` 提供上下文。

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

每个 Behavior precondition Rule 生成独立 guard function。

## 7. Use Case

Use Case：

- 输入实体只来自 IIR `input_refs`；
- 依赖只来自 IIR `dependencies`；
- guard / step 顺序保持；
- typed assignment 生成真实赋值；
- repository / port effect 按 IIR dependency 执行。

未知语义不得由 Generator 自行补全。

## 8. Decision

IIR：

```text
when
then_steps
else_steps
```

生成：

```ts
if (condition) {
  // then_steps
} else {
  // else_steps
}
```

分支中的 Assignment、Effect、嵌套 Decision/Foreach 递归生成，不能扁平化或漏执行。

## 9. Foreach

IIR：

```text
collection_ref
item_alias
item_type
when
do_steps
```

生成：

```ts
for (const item of input.order.items) {
  if (!(item.reserved === true)) continue;
  item.released = true;
}
```

规则：

- collection 必须来自 `cardinality=many` 的 entity field；
- `item.xxx` 只在循环作用域内解析；
- `when` 映射为循环过滤条件；
- `do_steps` 保持顺序并递归生成；
- scoped item 对应 Repository effect 时，可以直接把局部 item 传给匹配的 Repository contract。

当前暂不支持内层 foreach 的 collection 来自外层 scoped item，例如 `item.children`；IIR 会将其标记为 blocking unresolved，而不是 Generator 猜测。

## 10. SQLite

SQLite 只属于 Target Profile / IIR / Adapter 层。

v0.2 当前生成 SQLite adapter boundary 与 TODO，不在缺少明确 persistence mapping 时猜表名、列名或 SQL。

## 11. Target Test

Target Test Plan 区分：

```text
Rule Guard Case
Scenario Use Case Case
Unsupported Case
```

Rule Case 调用真实 guard。

Scenario Case根据 CLM Given、IIR runtime bindings 与 guard fixture constraints 构造技术 fixture。

当前结构化 Scenario 主要覆盖标量字段；foreach 集合对象场景将在结构化集合 fixture 协议加入后转为可执行测试。在此之前，不伪造集合业务对象。

## 12. Generated Project

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

## 13. 生成质量 Gate

`validate_generated_typescript.mjs` 零依赖检查：

- 禁止 skeleton throw；
- 禁止 `expect(true)`；
- 禁止 unresolved Semantic Ref 动态访问；
- 必要 generated files 必须存在。

`verify_typescript.mjs` 在环境具备工具时执行：

1. `tsc --noEmit`；
2. `vitest run`。

工具不存在返回 `TOOL_UNAVAILABLE`，不把跳过描述成通过。

## 14. Generated Code Integrity

Manifest 保存 generator version、source CLM、semantic hash、IIR version、Target Profile、artifact path、semantic refs 与 content hash。

业务修改必须回到 CLM / Semantic Change Set；直接修改 generated code 会由 manifest drift 检测发现。
