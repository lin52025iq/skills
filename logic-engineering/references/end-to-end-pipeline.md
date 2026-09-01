# 端到端逻辑工程流水线

当前确定性工具链统一使用 **Node.js 20+**。

## 1. 主链路

```text
Legacy Code / Human Requirement
        ↓
Candidate CLM
        ↓ confirm
Canonical CLM v0.2
        ↓
Semantic Patch / Change Set（可选）
        ↓
CLM Schema + Semantic Gate
        ↓
Impact Analysis
        ↓
Human Logic + Test Vectors
        ↓
Target Profile
        ↓
IIR v0.2
        ↓
IIR Schema + Semantic Gate
        ↓
Target Test Plan v0.2
        ↓
Target Adapter
        ↓
Generated Manifest Verification
        ↓
Target Runtime Gate（可选）
```

## 2. 推荐统一入口

仅分析：

```bash
node scripts/run_pipeline.mjs model.json
```

业务级变更：

```bash
node scripts/run_pipeline.mjs model.json \
  --change-set change-set.json
```

TypeScript + SQLite：

```bash
node scripts/run_pipeline.mjs model.json \
  --target-profile evals/fixtures/ts-sqlite.target-profile.json \
  --generate-ts
```

如果当前环境已经具备 `tsc` 与 `vitest`：

```bash
node scripts/run_pipeline.mjs model.json \
  --target-profile evals/fixtures/ts-sqlite.target-profile.json \
  --generate-ts \
  --verify-ts
```

## 3. Gate

### CLM Schema Gate

```bash
node scripts/schema_validate.mjs \
  model.json \
  schemas/clm-v0.2.schema.json
```

### CLM Semantic Gate

```bash
node scripts/logic_cli.mjs validate-clm model.json
```

检查 Semantic ID、Node Registry、引用、Symbol Table、Typed Expression / Action / Scenario、enum/type、状态一致性和 Evidence。

### 修改 Gate

单节点修改：

```bash
node scripts/apply_patch.mjs model.json patch.json -o updated.json
```

业务级多节点修改：

```bash
node scripts/apply_change_set.mjs model.json change-set.json -o updated.json
```

重要 Change Set 优先带：

```text
base_model_version
base_semantic_hash
```

修改后执行：

```bash
node scripts/analyze_impact.mjs updated.json <changed-id...>
```

### Test Vector Gate

```bash
node scripts/logic_cli.mjs test-vectors model.json -o test-vectors.json
```

测试期望只从 CLM 派生。

### IIR Compile Gate

```bash
node scripts/compile_iir.mjs \
  model.json \
  target-profile.json \
  -o implementation.iir.json
```

IIR v0.2 必须包含 `domain_types` 与 `runtime_bindings`，使 Target Adapter 不需要重新猜领域对象映射。

### IIR Validation Gate

```bash
node scripts/schema_validate.mjs \
  implementation.iir.json \
  schemas/iir-v0.2.schema.json

node scripts/logic_cli.mjs validate-iir implementation.iir.json
```

blocking unresolved 非空时停止。

### Target Test Plan Gate

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

fixture constraint 可以来自 IIR guard，但 expected behavior 仍然只能来自 CLM Test Vector。

### TypeScript + SQLite Generator Gate

```bash
node scripts/generate_typescript_v02.mjs \
  implementation.iir.json \
  target-test-plan.json \
  -o generated-ts

node scripts/logic_cli.mjs verify-manifest generated-ts
```

v0.2 Generator 不再生成 skeleton 假实现，而是生成当前可确定的：

```text
string literal union
entity interface
guard function
real typed assignment
repository effect call
Vitest assertion
```

信息不足的测试生成 `it.todo`。

### TypeScript Runtime Gate

当工具可用时：

```bash
node scripts/verify_typescript.mjs generated-ts
```

执行：

```text
tsc --noEmit
vitest run
```

如果工具未安装，返回 `TOOL_UNAVAILABLE`，不视为通过。

## 4. 默认输出

```text
.logic-engineering-output/
├── updated.clm.json
├── semantic-diff.json
├── impact-analysis.json
├── symbol-table.json
├── human-logic.md
├── test-vectors.json
├── implementation.iir.json
├── target-test-plan.json
└── generated-ts/
    ├── domain/
    ├── rules/
    ├── usecases/
    ├── ports/
    ├── errors/
    ├── adapters/
    ├── tests/
    ├── package.json
    ├── tsconfig.json
    └── manifest.json
```

## 5. 失败策略

任一 Gate 失败立即停止。

禁止：

- CLM 校验失败仍生成 IIR；
- IIR Schema/Semantic Gate 失败仍调用 Target Adapter；
- blocking unresolved 非空仍生成代码；
- Change Set 部分成功后写出部分模型；
- 从 generated code 推导 expected behavior；
- Generator 猜测缺失业务或存储语义；
- 使用 `expect(true)` 假装测试已完成；
- generated code 人工漂移后仍认为与 CLM 一致。

## 6. 回归

```bash
node scripts/run_v02_regression.mjs
```

或：

```bash
npm run regression
```

相关资产：

- `references/node-toolchain.md`
- `references/clm-v0.2-freeze-checklist.md`
- `evals/iir-v0.2-evals.json`
- `evals/typescript-generator-v0.2-evals.json`
