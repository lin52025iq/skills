# Node.js 工具链

`logic-engineering` 的主执行工具链统一使用 **Node.js 20+**。

本 Skill 的确定性工具目前 **零 npm 运行时依赖**：不要求 Python，也不要求先执行 `npm install`。

生成出来的 TypeScript 项目如果要执行真实 `tsc + Vitest` Gate，则按生成目录中的 `package.json` 准备 TypeScript/Vitest。

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

通用 CLM CLI：

```bash
node scripts/logic_cli.mjs <command> ...
```

## 2. Schema Gate

CLM：

```bash
node scripts/schema_validate.mjs model.json schemas/clm-v0.2.schema.json
```

Target Profile：

```bash
node scripts/schema_validate.mjs target-profile.json schemas/target-profile-v0.1.schema.json
```

IIR：

```bash
node scripts/schema_validate.mjs implementation.iir.json schemas/iir-v0.2.schema.json
```

内置零依赖 Schema Validator 覆盖当前 Schema 使用的 `$ref / allOf / oneOf / if-then-else / type / required / properties / additionalProperties / items / enum / const / pattern / minLength / minItems / maxItems / uniqueItems / minProperties / maxProperties`。

## 3. 通用 CLI 子命令

```text
validate-clm     校验 CLM 语义
symbols          生成 Symbol Table
hash             计算 Semantic Hash
render           生成中文逻辑投影
test-vectors     生成语言无关 Test Vector
verify-manifest  校验 generated artifact 漂移
```

IIR、Target Test 与 IIR Validator 已拆成独立工具，不再嵌入通用 CLI：

```bash
node scripts/compile_iir.mjs model.json target-profile.json -o implementation.iir.json
node scripts/validate_iir.mjs implementation.iir.json
node scripts/compile_target_tests.mjs test-vectors.json implementation.iir.json -o target-test-plan.json
```

## 4. Target Profile

Target Profile 是一等实现契约，详见 `references/target-profile-v0.1.md`。

当前 SQLite 使用 `persistence_generation=explicit_mapping` 时，table / primary key / columns 必须显式给出。

```text
Schema valid
→ 仅表示配置形状合法

IIR valid
→ 表示该 Profile 对当前 CLM 的必要 mapping/策略已经满足
```

缺失字段 mapping 时进入 blocking unresolved，不能继续生成 SQL。

## 5. TypeScript Target Adapter

```bash
node scripts/generate_typescript_v02.mjs \
  implementation.iir.json \
  target-test-plan.json \
  -o generated-ts
```

当前支持：

```text
Typed Guard / Assignment
Decision → if/else
Foreach → for...of + scoped item
显式 SQLite mapping → 稳定 upsert Repository Adapter
```

生成后固定执行两个零依赖 Gate：

```bash
node scripts/logic_cli.mjs verify-manifest generated-ts
node scripts/validate_generated_typescript.mjs generated-ts
```

如果环境已具备 `tsc` 与 `vitest`，再执行：

```bash
node scripts/verify_typescript.mjs generated-ts
```

工具不存在时返回 `TOOL_UNAVAILABLE`，不会把未执行描述成已通过。

## 6. 独立 Node 脚本

```text
schema_validate.mjs
apply_patch.mjs
apply_change_set.mjs
analyze_impact.mjs
migrate_clm_v01_to_v02.mjs
compile_iir.mjs
validate_iir.mjs
compile_target_tests.mjs
generate_typescript_v02.mjs
validate_generated_typescript.mjs
verify_typescript.mjs
run_pipeline.mjs
run_v02_regression.mjs
run_sqlite_regression.mjs
run_sqlite_mapping_negative.mjs
```

公共模块：`scripts/lib/model.mjs`。

## 7. 回归拆分

```text
npm run regression:core
npm run regression:sqlite
npm run regression:sqlite-negative
```

总入口：

```bash
npm run regression
```

回归按能力拆分，避免单个脚本无限膨胀。

## 8. 首个参考目标

```text
TypeScript 5.x
Node.js
SQLite
Vitest
framework-agnostic
```

Reference Target 只验证目标实现投影，不改变 CLM / IIR 的语言无关设计。

## 9. 运行时原则

- 公共结构、Node Registry、Symbol Table、Semantic Hash 与 scoped-ref 解析集中在 `scripts/lib/model.mjs`；
- 通用 CLI 不包含 IIR 编译、IIR Validator 或目标语言生成逻辑；
- IIR / Target Test 使用独立编译器；
- Target Adapter 独立扩展；
- 新增确定性工具默认使用 Node.js；
- 不长期维护 Python/Node、旧/新 Generator 或重复 Validator；
- 旧实现迁移完成后直接删除；
- SQLite 只属于当前 Target Profile，不进入领域语义。
