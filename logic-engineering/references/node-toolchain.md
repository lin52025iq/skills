# Node.js 工具链

`logic-engineering` 的主执行工具链统一使用 **Node.js 20+**。

本 Skill 的确定性工具目前 **零 npm 运行时依赖**：不要求 Python，也不要求先执行 `npm install`。

`package.json` 仅提供快捷命令和 Node 版本声明。

## 1. 主要入口

通用 CLI：

```bash
node scripts/logic_cli.mjs <command> ...
```

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

## 2. Schema Gate

```bash
node scripts/schema_validate.mjs model.json schemas/clm-v0.2.schema.json
```

内置实现覆盖当前 Schema 使用的 `$ref / allOf / oneOf / if-then-else / type / required / properties / additionalProperties / items / enum / const / pattern / minLength / minItems / maxItems / uniqueItems`。

## 3. 通用 CLI 子命令

```text
validate-clm    校验 CLM 语义
symbols         生成 Symbol Table
hash            计算 Semantic Hash
render          生成中文逻辑投影
test-vectors    生成语言无关 Test Vector
compile-iir     CLM → IIR v0.2
validate-iir    校验 IIR 语义
target-tests    Test Vector + IIR → Target Test Plan
verify-manifest 校验 generated artifact 漂移
```

Target Generator 不嵌入通用 CLI。首个 adapter：

```bash
node scripts/generate_typescript.mjs \
  implementation.iir.json \
  target-test-plan.json \
  -o generated-ts
```

## 4. 独立 Node 脚本

```text
schema_validate.mjs
apply_patch.mjs
apply_change_set.mjs
analyze_impact.mjs
migrate_clm_v01_to_v02.mjs
generate_typescript.mjs
run_pipeline.mjs
run_v02_regression.mjs
```

公共模块：`scripts/lib/model.mjs`。

## 5. 首个参考目标

```text
TypeScript 5.x
Node.js
SQLite
Vitest
framework-agnostic
```

Reference Target 只验证目标实现投影，不改变 CLM / IIR 的语言无关设计。

## 6. 运行时原则

- 公共结构、Node Registry、Symbol Table 和 Semantic Hash 集中在 `scripts/lib/model.mjs`；
- 通用 CLI 不包含目标语言生成逻辑；
- Target Generator 以独立 adapter 扩展；
- 新增确定性工具默认使用 Node.js；
- 不长期维护 Python/Node 双实现；
- 旧实现迁移完成后直接删除；
- SQLite 只属于当前 Target Profile，不进入领域语义。
