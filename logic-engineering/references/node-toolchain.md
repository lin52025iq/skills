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

回归 Gate：

```bash
node scripts/run_v02_regression.mjs
```

通用 CLM/IIR CLI：

```bash
node scripts/logic_cli.mjs <command> ...
```

## 2. Schema Gate

```bash
node scripts/schema_validate.mjs model.json schemas/clm-v0.2.schema.json
```

内置实现覆盖当前 Schema 使用的 `$ref / allOf / oneOf / if-then-else / type / required / properties / additionalProperties / items / enum / const / pattern / minLength / minItems / maxItems / uniqueItems`。

## 3. 通用 CLI 子命令

```text
validate-clm     校验 CLM 语义
symbols          生成 Symbol Table
hash             计算 Semantic Hash
render           生成中文逻辑投影
test-vectors     生成语言无关 Test Vector
validate-iir     校验 IIR 语义
verify-manifest  校验 generated artifact 漂移
```

IIR 编译和 Target Test 编译已经拆成独立确定性编译器，不再由通用 CLI 承担：

```bash
node scripts/compile_iir.mjs \
  model.json \
  evals/fixtures/ts-sqlite.target-profile.json \
  -o implementation.iir.json

node scripts/compile_target_tests.mjs \
  test-vectors.json \
  implementation.iir.json \
  -o target-test-plan.json
```

## 4. Target Adapter

Target Generator 不嵌入通用 CLI。

当前 TypeScript + SQLite v0.2：

```bash
node scripts/generate_typescript_v02.mjs \
  implementation.iir.json \
  target-test-plan.json \
  -o generated-ts
```

生成后：

```bash
node scripts/logic_cli.mjs verify-manifest generated-ts
```

如果环境已具备 `tsc` 与 `vitest`：

```bash
node scripts/verify_typescript.mjs generated-ts
```

工具不存在时返回 `TOOL_UNAVAILABLE`，不会把未执行描述成已通过。

## 5. 独立 Node 脚本

```text
schema_validate.mjs
apply_patch.mjs
apply_change_set.mjs
analyze_impact.mjs
migrate_clm_v01_to_v02.mjs
compile_iir.mjs
compile_target_tests.mjs
generate_typescript_v02.mjs
verify_typescript.mjs
run_pipeline.mjs
run_v02_regression.mjs
```

公共模块：`scripts/lib/model.mjs`。

## 6. 首个参考目标

```text
TypeScript 5.x
Node.js
SQLite
Vitest
framework-agnostic
```

Reference Target 只验证目标实现投影，不改变 CLM / IIR 的语言无关设计。

## 7. 运行时原则

- 公共结构、Node Registry、Symbol Table 和 Semantic Hash 集中在 `scripts/lib/model.mjs`；
- 通用 CLI 不包含目标语言生成逻辑；
- IIR / Target Test 使用独立编译器，避免 CLI 内部出现两套实现；
- Target Generator 以独立 adapter 扩展；
- 新增确定性工具默认使用 Node.js；
- 不长期维护 Python/Node 或新旧 Generator 双实现；
- 旧实现迁移完成后直接删除；
- SQLite 只属于当前 Target Profile，不进入领域语义。
