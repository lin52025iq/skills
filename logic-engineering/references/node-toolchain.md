# Node.js 工具链

`logic-engineering` 的主执行工具链统一使用 **Node.js 20+**。

不再要求 Python 作为本 Skill 的运行时依赖。

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

## 2. CLI 子命令

```text
validate-clm   校验 CLM
symbols        生成 Symbol Table
hash           计算 Semantic Hash
render         生成中文逻辑投影
test-vectors   生成语言无关 Test Vector
compile-iir    CLM → IIR v0.2
validate-iir   校验 IIR
target-tests   Test Vector + IIR → Target Test Plan
generate-ts    IIR + Target Test Plan → TypeScript/SQLite 生成产物
verify-manifest 校验 generated artifact 漂移
pipeline       简化流水线入口
```

独立 Node 脚本：

```text
apply_patch.mjs
apply_change_set.mjs
analyze_impact.mjs
migrate_clm_v01_to_v02.mjs
run_pipeline.mjs
run_v02_regression.mjs
```

## 3. 首个参考目标

首个可执行目标固定为：

```text
TypeScript 5.x
Node.js
SQLite
Vitest
framework-agnostic
```

这只是首个 Reference Target，不改变 CLM / IIR 的语言无关设计。

## 4. 运行时原则

- 公共结构与语义函数集中在 `scripts/lib/model.mjs`；
- 不允许不同 CLI 各自维护 CLM Node Registry；
- 新增确定性工具优先使用 Node.js；
- 不同时长期维护 Python/Node 双实现；
- 旧实现完成迁移后删除；
- 目标语言生成器作为 adapter 扩展，不污染 CLM。
