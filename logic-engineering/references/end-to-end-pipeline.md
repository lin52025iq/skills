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
CLM Validation + Impact Analysis
        ↓
Human Logic + Test Vectors
        ↓
Target Profile
        ↓
IIR v0.2
        ↓
IIR Validation
        ↓
Target Test Plan
        ↓
Target Generator
        ↓
Generated Manifest Verification
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

首个参考目标 TypeScript + SQLite：

```bash
node scripts/run_pipeline.mjs model.json \
  --target-profile evals/fixtures/ts-sqlite.target-profile.json \
  --generate-ts
```

## 3. Gate

### CLM Gate

检查 Semantic ID、Node Registry、引用、Symbol Table、Typed Expression / Action / Scenario、enum/type、状态一致性和 Evidence。

```bash
node scripts/logic_cli.mjs validate-clm model.json
```

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

### Test Gate

测试期望只从 CLM 派生：

```bash
node scripts/logic_cli.mjs test-vectors model.json -o test-vectors.json
```

### IIR Gate

```bash
node scripts/logic_cli.mjs compile-iir model.json target-profile.json -o implementation.iir.json
node scripts/logic_cli.mjs validate-iir implementation.iir.json
```

blocking unresolved 非空时停止。

### Target Test Gate

```bash
node scripts/logic_cli.mjs target-tests test-vectors.json implementation.iir.json -o target-test-plan.json
```

### TypeScript + SQLite Generator Gate

```bash
node scripts/logic_cli.mjs generate-ts implementation.iir.json target-test-plan.json -o generated-ts
node scripts/logic_cli.mjs verify-manifest generated-ts
```

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
```

## 5. 失败策略

任一 Gate 失败立即停止。

禁止：

- CLM 校验失败仍生成 IIR；
- blocking unresolved 非空仍生成代码；
- Change Set 部分成功后写出部分模型；
- 从 generated code 推导 expected behavior；
- Generator 猜测缺失业务或存储语义；
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
- `evals/typescript-generator-v0.1-evals.json`
