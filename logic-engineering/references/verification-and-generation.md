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
      │   └─→ Target Test Plan
      ▼
Target Generator
      │
Generated Code + Manifest
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
- IIR dependency / strategy / traceability。

### L2 派生一致性

- Human Projection 不新增规则；
- Test Vector 只来自 CLM；
- IIR 只做技术映射；
- Target Test Plan 不重写 expected behavior。

### L3 目标实现验证

- TypeScript 类型检查/编译；
- Vitest 单元/集成测试；
- manifest / generated drift；
- 实现级静态检查。

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

## 5. IIR Gate

```bash
node scripts/logic_cli.mjs validate-iir implementation.iir.json
```

必须确认：

- Use Case dependency 存在；
- Repository Contract / External Port 有明确契约；
- 事务/并发/重试/幂等策略满足要求；
- Primitive binding 可用；
- Traceability 覆盖；
- blocking unresolved 为 0。

## 6. Target Generator

目标生成器不得再次解释业务规则，只负责目标语言语法、IIR component 映射、Primitive binding、Target Test Plan 映射和 Manifest。

信息不足时应失败或要求补充 IIR，不回头猜 CLM 语义。

当前 Reference Target：

```text
TypeScript + Node.js + SQLite + Vitest
```

## 7. Generated Manifest

每次生成至少保存 generator version、source CLM id、source semantic hash、IIR version、Target Profile 和 artifact content hash。

校验：

```bash
node scripts/logic_cli.mjs verify-manifest generated-ts
```

## 8. Semantic Round-trip（待实现）

```text
Generated TypeScript
→ Observable Semantic Extractor
→ guards / writes / external effects / ordering / errors
→ compare CLM
```

Round-trip 是额外安全网，不替代独立测试。

## 9. Formal Projection（待实现）

形式验证后端按性质路由。Dafny、Why3、TLA+ 等是验证投影，不是 CLM 本身。

## 10. 当前实现状态

已实现：

- CLM v0.2 模型与 Node Validator；
- Semantic Patch / Change Set + semantic hash；
- Impact Analysis；
- Human Projection；
- Test Vector；
- IIR v0.2 compiler / validator；
- Target Test Plan；
- TypeScript + SQLite Generator v0.1 skeleton；
- Generated Manifest drift check；
- 纯 Node.js 主工具链与回归 Gate。

未实现：

- TypeScript 业务语句级完整生成；
- TypeScript `tsc` / Vitest 自动执行 harness；
- 目标代码行为级 round-trip；
- 形式验证后端；
- runtime monitor；
- 更多 Target Generator。
