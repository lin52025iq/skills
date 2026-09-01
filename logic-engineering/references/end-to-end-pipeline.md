# 端到端逻辑工程流水线

本文件描述当前主路径。不要在这里重复 CLM/IIR 字段定义；具体结构以对应 v0.2 规范和 Schema 为准。

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

仅分析/验证逻辑：

```bash
python scripts/run_logic_pipeline.py model.json
```

应用业务级变更：

```bash
python scripts/run_logic_pipeline.py model.json \
  --change-set change-set.json
```

生成目标实现计划：

```bash
python scripts/run_logic_pipeline.py model.json \
  --target-profile target-profile.json
```

进入 Go v0.1 生成：

```bash
python scripts/run_logic_pipeline.py model.json \
  --target-profile evals/fixtures/go-postgres.target-profile.json \
  --generate-go
```

## 3. 各阶段 Gate

### CLM Gate

必须通过：

- JSON Schema；
- Semantic ID / collection；
- 引用完整性；
- Symbol Table；
- Typed Expression / Action / Scenario；
- enum / type；
- 状态一致性；
- Evidence 要求。

### 修改 Gate

单节点独立修改可以用 Semantic Patch。

一个业务意图跨多个节点时使用 Change Set，并优先带：

```text
base_model_version
base_semantic_hash
```

修改后重新校验并执行 Impact Analysis。

### Test Gate

测试期望必须由 CLM Test Vector 产生。

Target Test Plan 只负责将语言无关期望映射到目标测试框架和 IIR 依赖，不得重写 expected behavior。

### IIR Gate

必须通过：

```bash
python scripts/validate_iir.py implementation.iir.json \
  --schema schemas/iir-v0.2.schema.json
```

`blocking unresolved` 非空时禁止进入目标代码生成。

### Generator Gate

目标生成器只能消费经过校验的 IIR + Target Test Plan。

当前 Go v0.1：

```bash
python scripts/generate_go.py implementation.iir.json target-test-plan.json -o generated-go
```

生成后立即运行：

```bash
python scripts/verify_generated_manifest.py generated-go
```

## 4. 输出目录

统一流水线默认输出：

```text
.logic-engineering-output/
├── updated.clm.json             # 有修改时
├── semantic-diff.json           # 有修改时
├── impact-analysis.json         # 有修改时
├── symbol-table.json
├── human-logic.md
├── test-vectors.json
├── implementation.iir.json      # 有 Target Profile 时
├── target-test-plan.json        # 有 Target Profile 时
└── generated-go/                # --generate-go 时
```

## 5. 失败策略

任一 Gate 失败都立即停止。

禁止：

- CLM 校验失败后继续生成 IIR；
- IIR blocking unresolved 非空仍生成代码；
- Change Set 部分成功后写出部分模型；
- Target Test Generator 从 generated code 推导预期；
- Generator 遇到未知技术语义时自行猜测；
- generated code 被人工修改后仍认为与 CLM 一致。

## 6. 回归

CLM/IIR 核心协议变化后执行：

```bash
python scripts/run_v02_regression.py
```

并检查：

- `references/clm-v0.2-freeze-checklist.md`
- `evals/iir-v0.2-evals.json`
- `evals/go-generator-v0.1-evals.json`
