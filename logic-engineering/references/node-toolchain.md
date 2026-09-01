# Node.js 工具链

`logic-engineering` 的主执行工具链统一使用 **Node.js 20+**。

本 Skill 的确定性工具本身保持零 npm 运行时依赖；生成出来的 TypeScript 项目只有在执行真实 `tsc + Vitest` Gate 时才需要安装对应开发依赖。

## 1. 主要入口

统一流水线：

```bash
node scripts/run_pipeline.mjs model.json \
  --target-profile evals/fixtures/ts-sqlite.target-profile.json \
  --generate-ts
```

全部回归：

```bash
npm run regression
```

## 2. 三类 Validator

结构 Schema：

```bash
node scripts/schema_validate.mjs model.json schemas/clm-v0.2.schema.json
```

CLM 语义：

```bash
node scripts/validate_clm.mjs model.json
```

IIR 语义：

```bash
node scripts/validate_iir.mjs implementation.iir.json
```

CLM 与 IIR Validator 都已经从通用 CLI 拆出，禁止恢复重复实现。

## 3. 通用 CLI

`logic_cli.mjs` 只承担轻量语言无关操作：

```text
symbols          Symbol Table
hash             Semantic Hash
render           中文逻辑投影
test-vectors     语言无关 Test Vector
verify-manifest  Generated artifact 漂移检查
```

例如：

```bash
node scripts/logic_cli.mjs render model.json -o human-logic.md
node scripts/logic_cli.mjs test-vectors model.json -o test-vectors.json
```

## 4. 编译链

```bash
node scripts/compile_iir.mjs model.json target-profile.json -o implementation.iir.json
node scripts/validate_iir.mjs implementation.iir.json
node scripts/compile_target_tests.mjs test-vectors.json implementation.iir.json -o target-test-plan.json
```

当前 CLM/IIR 已支持：

```text
Typed Guard / Assignment
Decision → then_steps / else_steps
Foreach → typed scoped item
Structured list/object Scenario
Atomicity → transaction plan
显式 SQLite persistence mapping
```

## 5. TypeScript + SQLite Adapter

基础业务实现：

```bash
node scripts/generate_typescript_v02.mjs \
  implementation.iir.json \
  target-test-plan.json \
  -o generated-ts
```

事务层：

```bash
node scripts/generate_typescript_transactions.mjs \
  implementation.iir.json \
  generated-ts
```

统一流水线会自动按这个顺序执行。

当前生成能力包括：

```text
Rule Guard → TypeScript boolean function
Typed Assignment → 属性赋值
Decision → if/else
Foreach → for...of + scoped item
list/object Scenario → 数组/对象 fixture + toEqual
explicit SQLite mapping → INSERT ... ON CONFLICT upsert
Atomicity full_behavior → Transactional Use Case wrapper
sqlite_transaction → BEGIN IMMEDIATE / COMMIT / ROLLBACK runner
```

## 6. Generated Gate

生成后固定执行：

```bash
node scripts/logic_cli.mjs verify-manifest generated-ts
node scripts/validate_generated_typescript.mjs generated-ts
```

有 `tsc` / `vitest` 时进一步：

```bash
node scripts/verify_typescript.mjs generated-ts
```

工具不存在时必须报告 `TOOL_UNAVAILABLE`，不能描述成已通过。

## 7. Target Profile

Target Profile 是一等实现契约，详见 `references/target-profile-v0.1.md`。

当前 SQLite Profile 支持：

```text
persistence_generation = explicit_mapping
transaction_strategy    = sqlite_transaction
transaction_scope       = full_behavior
```

Table / primary key / columns 必须显式配置。

事务 wrapper 与 Repository Adapter 必须绑定同一 SQLite transaction/session context。

## 8. 独立 Node 脚本

```text
schema_validate.mjs
validate_clm.mjs
apply_patch.mjs
apply_change_set.mjs
analyze_impact.mjs
migrate_clm_v01_to_v02.mjs
compile_iir.mjs
validate_iir.mjs
compile_target_tests.mjs
generate_typescript_v02.mjs
generate_typescript_transactions.mjs
validate_generated_typescript.mjs
verify_typescript.mjs
run_pipeline.mjs
run_v02_regression.mjs
run_sqlite_regression.mjs
run_sqlite_mapping_negative.mjs
run_transaction_regression.mjs
```

公共模型：`scripts/lib/model.mjs`。

## 9. 回归拆分

```text
npm run regression:core
npm run regression:sqlite
npm run regression:sqlite-negative
npm run regression:transaction
```

总入口：

```bash
npm run regression
```

## 10. 运行时原则

- Node Registry、Symbol Table、Semantic Hash、scoped-ref 和 Typed Value 公共行为集中在 `scripts/lib/model.mjs`；
- Validator、Compiler、Target Adapter 各自独立，不在通用 CLI 中维护第二套实现；
- 替代完成的旧实现直接删除；
- SQLite/Node.js/TypeScript 只属于 Target 层，不进入 CLM 领域语义；
- Generator 遇到未支持或不确定语义必须阻断或输出明确 unsupported，不得猜测。
