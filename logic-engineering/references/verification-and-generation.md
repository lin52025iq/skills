# 验证与实现生成规范

本规范定义 CLM、IIR、测试与目标代码之间的验证关系。结构以 `clm-v0.2.md`、`iir-v0.2.md` 和对应 Schema 为准。

## 1. 核心原则

- 业务语义先进入 CLM，再进入 IIR；
- 代码与测试分别从 CLM/IIR 派生，不互相反推；
- LLM 可以生成候选，确定性 Node 工具负责 Gate；
- blocking unresolved 非空时停止目标代码生成；
- generated code 默认只读，人工修改必须被 drift 检测发现；
- 验证覆盖必须分层说明，不能把“通过测试”描述成“已形式证明”。

## 2. 生成链路

```text
CLM v0.2
  ├─→ Human Logic
  └─→ Test Vectors
          │
Target Profile
      │   │
      ▼   ▼
    IIR v0.2
      │   │
      │   └─→ Target Test Plan v0.2
      ▼
Target Adapter
      │
Generated Code + Manifest
      │
Optional Runtime Gate
```

## 3. 验证层级

### L0 结构合法性

- CLM Schema；
- IIR Schema；
- Change Set Schema。

### L1 语义一致性

- Semantic ID / 引用；
- Symbol Table / 类型；
- enum；
- Action / Scenario；
- 状态迁移；
- IIR dependency / strategy / traceability；
- runtime bindings。

### L2 派生一致性

- Human Projection 不新增规则；
- Test Vector 只来自 CLM；
- IIR 只做技术映射；
- Target Test Plan 不重写 expected behavior；
- Target Adapter 不重新解释 CLM。

### L3 目标实现验证

- TypeScript typecheck；
- Vitest；
- manifest / generated drift；
- 目标实现静态检查。

### L4 高价值性质验证

根据语义选择 SMT、Dafny/Why3、状态模型检查、TLA+/LTL 或 property test 等后端。

### L5 运行时符合性

后续可由 CLM temporal/invariant 生成 runtime monitor；当前尚未实现。

## 4. 测试独立性

禁止：

```text
Generated Code → 推断 Expected Test
```

正确路径：

```text
CLM → Test Vector → Target Test Plan → Target Test Code
CLM → IIR → Target Code
```

fixture 构造可以使用 IIR guard constraint，但 expected result 只能来自 CLM Test Vector。

## 5. IIR Gate

IIR 编译：

```bash
node scripts/compile_iir.mjs \
  model.json \
  target-profile.json \
  -o implementation.iir.json
```

结构与语义验证：

```bash
node scripts/schema_validate.mjs \
  implementation.iir.json \
  schemas/iir-v0.2.schema.json

node scripts/logic_cli.mjs validate-iir implementation.iir.json
```

必须确认：

- Use Case dependency 存在；
- Repository Contract / External Port 有明确契约；
- domain_types / runtime_bindings 足够支撑 Target Adapter；
- 事务/并发/重试/幂等策略满足要求；
- Primitive binding 可用；
- Traceability 覆盖；
- blocking unresolved 为 0。

## 6. Target Test Plan Gate

```bash
node scripts/compile_target_tests.mjs \
  test-vectors.json \
  implementation.iir.json \
  -o target-test-plan.json
```

Target Test Plan v0.2 区分：

```text
Rule Guard Case
Scenario Use Case Case
Unsupported Case
```

`fixture_constraints` 用于技术测试装配，例如从字段等值 guard 生成同一个哨兵值。

不能安全构造的 case 必须保留 `unsupported`，Target Adapter 应生成 `it.todo`，而不是假通过。

## 7. Target Adapter

目标生成器不得再次解释业务规则，只负责：

- 目标语言类型与语法映射；
- IIR runtime binding → 运行时对象访问；
- IIR component → 文件/接口/类；
- Target Test Plan → 测试代码；
- Manifest。

信息不足时失败或生成明确 TODO，不回头猜 CLM 语义。

当前 Reference Target：

```text
TypeScript 5.x
Node.js
SQLite
Vitest
```

当前 adapter：

`scripts/generate_typescript_v02.mjs`

## 8. TypeScript v0.2 行为生成

已支持：

```text
CLM Enum           → string literal union
Typed Expression   → TypeScript boolean expression
Rule Guard         → guard function
Typed Assignment   → 真实属性赋值
Repository Effect  → Repository save
IIR Dependency     → constructor injection
Scenario Expect    → Vitest toBe assertion
```

测试 fixture 缺失时生成 `it.todo`，禁止 `expect(true)` 假通过。

## 9. Generated Manifest

每次生成至少保存：

```text
generator version
source CLM id
source semantic hash
IIR version
Target Profile
artifact path
artifact semantic refs
artifact content hash
```

校验：

```bash
node scripts/logic_cli.mjs verify-manifest generated-ts
```

## 10. TypeScript Runtime Gate

生成目录包含 `package.json` 与 `tsconfig.json`。

环境具备工具时执行：

```bash
node scripts/verify_typescript.mjs generated-ts
```

Gate 执行：

```text
tsc --noEmit
vitest run
```

如果 `tsc` 或 `vitest` 不存在，返回 `TOOL_UNAVAILABLE`；不能把未执行描述成已通过。

## 11. Semantic Round-trip（待实现）

```text
Generated TypeScript
→ Observable Semantic Extractor
→ guards / writes / external effects / ordering / errors
→ compare CLM
```

Round-trip 是额外安全网，不替代独立测试。

## 12. Formal Projection（待实现）

形式验证后端按性质路由。Dafny、Why3、TLA+ 等是验证投影，不是 CLM 本身。

## 13. 当前实现状态

已实现：

- CLM v0.2 模型与 Node Validator；
- Semantic Patch / Change Set + semantic hash；
- Impact Analysis；
- Human Projection；
- Test Vector；
- IIR v0.2 compiler / schema / validator；
- Target Test Plan v0.2；
- TypeScript + SQLite Generator v0.2 可执行语义生成；
- Generated Manifest drift check；
- 可选 `tsc + Vitest` 执行 Gate；
- 纯 Node.js 主工具链与回归 Gate。

未实现：

- 更完整的 Repository method signature / DTO mapping；
- SQLite 表/列映射与真实 adapter 生成；
- Decision / Foreach /复杂 external port 的完整可执行生成；
- 目标代码行为级 round-trip；
- 形式验证后端；
- runtime monitor；
- 更多 Target Adapter。
