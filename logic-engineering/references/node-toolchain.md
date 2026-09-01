# Node.js 工具链

`logic-engineering` 的主执行工具链统一使用 **Node.js 20+**。

本 Skill 的确定性工具目前 **零 npm 运行时依赖**：不要求 Python，也不要求先执行 `npm install`。

`package.json` 仅提供快捷命令和 Node 版本声明。

## 1. 主要入口

统一 CLI：

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

也可以：

```bash
npm run regression
```

## 2. Schema Gate

结构校验使用内置零依赖脚本：

```bash
node scripts/schema_validate.mjs \
  model.json \
  schemas/clm-v0.2.schema.json
```

当前实现覆盖本 Skill Schema 使用的 JSON Schema 子集，包括：

```text
$ref
allOf / oneOf
if / then / else
type
required
properties
additionalProperties
items
enum / const
pattern
minLength
minItems / maxItems
uniqueItems
```

## 3. CLI 子命令

```text
validate-clm    校验 CLM 语义
symbols         生成 Symbol Table
hash            计算 Semantic Hash
render          生成中文逻辑投影
test-vectors    生成语言无关 Test Vector
compile-iir     CLM → IIR v0.2
validate-iir    校验 IIR 语义
target-tests    Test Vector + IIR → Target Test Plan
generate-ts     IIR + Target Test Plan → TypeScript/SQLite 生成产物
verify-manifest 校验 generated artifact 漂移
```

独立 Node 脚本：

```text
schema_validate.mjs
apply_patch.mjs
apply_change_set.mjs
analyze_impact.mjs
migrate_clm_v01_to_v02.mjs
run_pipeline.mjs
run_v02_regression.mjs
```

公共模块：

```text
scripts/lib/model.mjs
```

## 4. 首个参考目标

```text
TypeScript 5.x
Node.js
SQLite
Vitest
framework-agnostic
```

Reference Target 只验证目标实现投影，不改变 CLM / IIR 的语言无关设计。

## 5. 运行时原则

- 公共结构、Node Registry、Symbol Table 和 Semantic Hash 集中在 `scripts/lib/model.mjs`；
- 不允许不同 CLI 各自维护另一份 CLM Node Registry；
- 新增确定性工具默认使用 Node.js；
- 不长期维护 Python/Node 双实现；
- 旧实现完成迁移后直接删除；
- Target Generator 作为 adapter 扩展，不污染 CLM；
- SQLite 是当前 Target Profile 的持久化策略，不进入领域语义。
