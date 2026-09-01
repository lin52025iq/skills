# 验证与实现生成规范

本规范定义 CLM、IIR、测试与目标代码之间的验证关系。版本化结构以 `clm-v0.2.md`、`iir-v0.2.md` 和对应 Schema 为准。

## 1. 核心原则

- 业务语义先进入 CLM，再进入 IIR；
- 代码与测试分别从 CLM/IIR 派生，不互相反推；
- LLM 可以生成候选，确定性校验器负责 Gate；
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

- CLM JSON Schema；
- IIR JSON Schema；
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

- 目标语言编译；
- 单元/集成测试；
- manifest / generated drift；
- 实现级静态检查。

### L4 高价值性质验证

根据语义选择：

```text
函数契约 / 数值性质 → SMT / Dafny / Why3 类工具
状态机              → model checking
时序 / 并发          → TLA+/LTL 类工具
不变量              → property test + optional proof
```

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

两个分支在目标执行时汇合。

## 5. IIR Gate

代码生成前必须运行：

```bash
python scripts/validate_iir.py implementation.iir.json \
  --schema schemas/iir-v0.2.schema.json
```

必须确认：

- Use Case dependency 存在；
- Repository Contract / External Port 有明确契约；
- Transaction/Concurrency/Retry/Idempotency strategy 已确定；
- Primitive binding 可用；
- Traceability 覆盖；
- blocking unresolved 为 0。

## 6. Target Generator

目标生成器不得再次解释业务规则。

它只能做：

- 命名与目标语言语法映射；
- IIR component → 文件/类型/接口；
- Primitive binding → 平台代码；
- Target Test Plan → 测试代码；
- Manifest 记录。

如果 Generator 发现 IIR 信息不足，应失败或要求补充 IIR，不回头自行猜 CLM 语义。

## 7. Generated Manifest

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

使用：

```bash
python scripts/verify_generated_manifest.py generated-dir
```

检测人工修改造成的 drift。

## 8. Semantic Round-trip（待实现）

未来目标：

```text
Generated Code
→ Observable Semantic Extractor
→ guards / writes / external effects / ordering / errors
→ compare CLM
```

Round-trip 是额外安全网，不替代从 CLM 独立生成的测试。

## 9. Formal Projection（待实现）

形式验证后端应按性质路由，不强制单一形式化语言。

CLM 需要保持高层业务语义；Dafny、Why3、TLA+ 等是验证投影，不是 CLM 本身。

## 10. 当前实现状态

已实现：

- CLM v0.2 Schema / Validator；
- Semantic Change Set + semantic hash；
- Test Vector；
- IIR v0.2 compiler / schema / validator；
- Target Test Plan；
- Go Generator v0.1 skeleton；
- Generated Manifest drift check。

未实现：

- 目标代码行为级 round-trip；
- 形式验证后端；
- runtime monitor；
- 完整多语言 generator；
- 自动编译/执行生成 Go 项目的 CI harness。
