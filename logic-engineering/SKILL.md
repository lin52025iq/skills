---
name: logic-engineering
description: 将现有项目中的模块级业务实现重建为与编程语言无关、可由人直接理解和修改的规范逻辑模型（Canonical Logic Model，CLM），并支持逻辑解释、归一化、语义修改、影响分析、测试派生、实现中间表示生成和一致性验证。适用于逻辑优先开发、旧代码逻辑导入、模块级自然语言解释、逻辑优化和跨语言重实现。
---

# 逻辑工程

本 Skill 把软件开发视为 **逻辑模型的维护、验证与实现投影**，而不是直接维护某一种编程语言的业务源代码。

```text
现有代码 / 人类需求
        ↓
候选逻辑模型
        ↓ 确认
规范逻辑模型（CLM）
   ┌────┼────────────┐
   ↓    ↓            ↓
人类视图  验证        实现投影
   ↓    ↓            ↓
自然语言  测试/检查    IIR / 目标代码
```

## 1. 不可违反的原则

1. **逻辑是业务事实源。** canonical CLM 优先于自然语言散文和生成代码。
2. **自然语言是 CLM 的人类投影。** 自由文本只能提出修改建议，不能静默改 canonical 状态。
3. **生成代码是输出。** 业务修改回到 CLM；不要把手改 generated code 当正式业务变更。
4. **每条语义有稳定 ID。** Semantic ID 与文件路径、类名、函数名和目标语言解耦。
5. **忠实解释与优化分离。** 先说明代码实际做什么，再单独提出应该怎样优化。
6. **证据优先。** 旧代码导入必须区分：已观察、推断、假设、未知。
7. **大模型负责提出，确定性工具负责裁决。** 类型、引用、测试和验证器优先于“模型觉得正确”。
8. **业务语义与技术实现分离。** CLM 描述业务与一致性要求；IIR / Target Profile 决定技术实现。
9. **测试从 CLM 独立派生。** 不从生成代码反推预期结果。
10. **存在 blocking unresolved 时不得宣称实现完整匹配。**

## 2. 工作模式

```text
理解（UNDERSTAND）
  旧代码导入、模块逻辑解释、行为重建

工程（ENGINEER）
  逻辑归一化、公共规则提取、修改、优化、语义补丁

实现（REALIZE）
  CLM → Target Profile → IIR → 目标实现

验证（VERIFY）
  类型、语义一致性、测试、实现符合性、形式验证
```

## 3. 运行时与工具链

本 Skill 的确定性工具链统一使用 **Node.js 20+**。

```text
scripts/logic_cli.mjs       日常 CLI
scripts/run_pipeline.mjs    统一流水线
scripts/run_v02_regression.mjs  核心回归 Gate
scripts/apply_patch.mjs
scripts/apply_change_set.mjs
scripts/analyze_impact.mjs
scripts/migrate_clm_v01_to_v02.mjs
scripts/lib/model.mjs       公共语义模型与类型工具
```

不长期维护 Python / Node 双实现。旧实现完成迁移后应删除。

详细命令见 `references/node-toolchain.md`。

## 4. CLM 版本策略

新建模型、准备进入 canonical 的模型使用 **CLM v0.2**。

```text
统一 Node Registry
+ Typed Expression AST
+ Symbol Table
+ Typed Action
+ Typed Scenario
+ Semantic Change Set
```

旧 v0.1 模型仅用于兼容；正式修改前迁移：

```bash
node scripts/migrate_clm_v01_to_v02.mjs old.json -o new.json
```

主要规范：

- `references/clm-v0.2.md`
- `schemas/clm-v0.2.schema.json`
- `scripts/lib/model.mjs`

## 5. 旧代码理解

不要以当前文件为边界，也不要无差别追踪全部函数。

```text
确定模块 / 功能
→ 找入口
→ 扫描一到两层骨架
→ 找关键业务节点
→ 建立开放问题
→ 按价值继续追踪
→ 记录 Evidence
→ Observed Behavior
→ Candidate CLM
→ 人或权威规范确认
→ Canonical CLM
```

优先追踪：业务规则、权限/验证、状态变化、数据读写、事务、一致性、事件、队列、重试、幂等、动态分派和关键外部调用。

复杂项目按 `references/legacy-workspace.md` 工作；详细规则见 `references/legacy-import.md`。

## 6. 证据等级

```text
已观察（OBSERVED）  源代码直接证明
推断（INFERRED）    多个已观察事实组合得到
假设（ASSUMED）     尚未验证的框架/运行时语义
未知（UNKNOWN）     当前证据不足
```

`ASSUMED / UNKNOWN` 不得静默升级成 canonical rule。

## 7. CLM 结构与人类视图

CLM 是带类型语义图：

```text
Domain / Behavior / Rule / Decision / Action
StateMachine / Transition / Effect / Constraint
Scenario / Primitive
```

给人审阅时：

```bash
node scripts/logic_cli.mjs render model.json -o logic.md
```

自然语言投影只能解释和重排 CLM，不能增加不存在的业务规则。

详见 `references/human-projection.md`。

## 8. 修改逻辑

### 单点修改

使用 Semantic Patch：

```bash
node scripts/apply_patch.mjs model.json patch.json -o updated.json --diff-output diff.json
```

详见 `references/semantic-patch.md`。

### 业务级修改

涉及多个 Rule / Action / Transition / Scenario / Constraint 时使用 Semantic Change Set v0.2：

```bash
node scripts/apply_change_set.mjs model.json change-set.json -o updated.json --diff-output diff.json
```

整个变更集必须全部成功或全部失败。重要变更优先带 `base_model_version + base_semantic_hash`。

详见 `references/semantic-change-set.md`。

自由自然语言只能先转成 Patch / Change Set Proposal，再应用。

## 9. 修改后的增量处理

```bash
node scripts/analyze_impact.mjs model.json <changed-id...> --output impact.json
```

至少区分：直接影响、传递影响、需要重生成的派生产物和需要人工复核的候选影响。

详见 `references/impact-analysis.md`。

## 10. 校验与测试派生

CLM 校验：

```bash
node scripts/logic_cli.mjs validate-clm model.json
```

Symbol Table：

```bash
node scripts/logic_cli.mjs symbols model.json -o symbols.json
```

Semantic Hash：

```bash
node scripts/logic_cli.mjs hash model.json
```

测试向量：

```bash
node scripts/logic_cli.mjs test-vectors model.json -o test-vectors.json
```

测试期望必须来自 CLM，优先覆盖 Rule、Scenario、Transition、Invariant 和边界条件。

详见：

- `references/clm-validator.md`
- `references/test-vector-generation.md`

## 11. IIR v0.2 与 Target Test Plan

固定链路：

```text
CLM
→ Target Profile
→ IIR v0.2
→ IIR Validation
→ Target Test Plan
→ Target Generator
```

```bash
node scripts/logic_cli.mjs compile-iir model.json target-profile.json -o implementation.iir.json
node scripts/logic_cli.mjs validate-iir implementation.iir.json
node scripts/logic_cli.mjs target-tests test-vectors.json implementation.iir.json -o target-test-plan.json
```

IIR 只做技术组织，不得改变业务规则。blocking unresolved 非空时禁止目标代码生成。

详见：

- `references/iir-v0.2.md`
- `references/target-test-generation.md`
- `references/verification-and-generation.md`

## 12. 首个参考目标：TypeScript + SQLite

首个 Reference Target：

```text
TypeScript 5.x
Node.js
SQLite
Vitest
framework-agnostic
```

目标配置示例：

`evals/fixtures/ts-sqlite.target-profile.json`

生成：

```bash
node scripts/logic_cli.mjs generate-ts implementation.iir.json target-test-plan.json -o generated-ts
node scripts/logic_cli.mjs verify-manifest generated-ts
```

第一版只生成高度确定的 Use Case、Repository / External Port interface、Typed Error、SQLite adapter contract、Manifest 和 Vitest 骨架。

SQLite 只是实现层选择，不进入 CLM。

详见 `references/typescript-generator-v0.1.md`。

## 13. 统一流水线

```bash
node scripts/run_pipeline.mjs model.json \
  --change-set change-set.json \
  --target-profile evals/fixtures/ts-sqlite.target-profile.json \
  --generate-ts \
  --output-dir .logic-engineering-output
```

执行顺序：

```text
CLM Validation
→ 可选 Patch / Change Set
→ 再次校验
→ Impact Analysis
→ Symbol Table
→ 中文逻辑投影
→ Test Vectors
→ IIR v0.2
→ IIR Validation
→ Target Test Plan
→ TypeScript + SQLite Generator
→ Manifest Verification
```

任一步失败都应终止。

详见 `references/end-to-end-pipeline.md`。

## 14. 回归 Gate

修改 CLM / IIR / Generator 核心协议后执行：

```bash
node scripts/run_v02_regression.mjs
```

或：

```bash
npm run regression
```

详见 `references/clm-v0.2-freeze-checklist.md`。

## 15. 逻辑优化

```text
O1 归一化       不改变行为
O2 结构重构     预期行为不变，需要等价验证
O3 稳健性改进   事务、幂等、重试、并发等实现语义变化
O4 业务修改     真正改变业务行为，默认需要人工确认
```

重点检查重复规则、缺失 case、分支重叠、状态机非法路径、不变量冲突、副作用顺序、事务、幂等和并发问题。

没有充分业务证据时写“潜在问题”，不要把设计偏好当确定 bug。

## 16. 废弃与兼容策略

- 已被新版本完整替代且没有迁移价值的文档或脚本直接删除。
- CLM v0.1 schema 暂时保留，只用于旧模型兼容。
- 新功能不得继续扩展 v0.1。
- 不同时长期维护 Python / Node 双实现。
- 删除资产后检查 Skill、Agent prompt 和 references 是否仍有死链。

## 17. 禁止事项

- 不把当前文件摘要当模块完整逻辑。
- 不把函数名直译当业务解释。
- 不把假设当已观察。
- 不在忠实翻译阶段偷偷改业务行为。
- 不把 generated code 当业务事实源。
- 不从 generated code 生成 expected tests。
- 不把框架或 SQLite 细节直接写进领域规则。
- 不因为文本相似就强行抽公共规则。
- 不在 blocking unresolved 非空时宣称实现完整。
- 不绕过 IIR Validator 直接调用目标生成器。
- 不宣称 CLM 正确即可自动证明任何生成实现都正确；必须说明实际验证层级。
