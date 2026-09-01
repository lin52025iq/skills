---
name: logic-engineering
description: 将现有项目中的模块级业务实现重建为与编程语言无关、可由人直接理解和修改的规范逻辑模型（Canonical Logic Model，CLM），并支持逻辑解释、归一化、语义修改、影响分析、测试派生、实现中间表示生成和一致性验证。适用于逻辑优先开发、旧代码逻辑导入、模块级自然语言解释、逻辑优化和跨语言重实现。
---

# 逻辑工程

把软件开发视为 **逻辑模型的维护、验证与实现投影**，而不是直接维护某一种编程语言的业务源代码。

```text
现有代码 / 人类需求
        ↓
Candidate CLM
        ↓ 确认
Canonical CLM
   ┌────┼──────────┐
   ↓    ↓          ↓
人类视图  验证       IIR
   ↓    ↓          ↓
自然语言  测试       Target Generator
```

## 1. 不可违反的原则

1. **CLM 是业务事实源。** canonical CLM 优先于自然语言散文和 generated code。
2. **自然语言是人类投影。** 自由文本只能提出修改建议，不能静默改 canonical 状态。
3. **Generated code 是输出。** 正式业务修改必须回到 CLM。
4. **Semantic ID 稳定。** 与文件路径、类名、函数名和目标语言解耦。
5. **忠实解释与优化分离。** 先恢复实际行为，再单独提出改进。
6. **证据优先。** 旧代码导入区分 OBSERVED / INFERRED / ASSUMED / UNKNOWN。
7. **LLM 提案，确定性工具裁决。** 类型、引用、Schema、测试和验证器优先。
8. **业务与技术分层。** CLM 保存业务及一致性语义；IIR / Target Profile 保存技术选择。
9. **测试从 CLM 独立派生。** 不从 generated code 反推 expected behavior。
10. **blocking unresolved 非空时停止生成。**

## 2. 四类工作模式

```text
UNDERSTAND  旧代码导入、模块逻辑解释、行为重建
ENGINEER   归一化、公共逻辑提取、修改、优化
REALIZE    CLM → IIR → Target Implementation
VERIFY     结构、类型、测试、实现符合性、形式验证
```

用户不需要知道内部模式名。

## 3. 工具链

确定性工具统一使用 **Node.js 20+**，当前零 npm 运行时依赖。

主入口：

```text
scripts/logic_cli.mjs
scripts/run_pipeline.mjs
scripts/run_v02_regression.mjs
```

写入与分析：

```text
scripts/apply_patch.mjs
scripts/apply_change_set.mjs
scripts/analyze_impact.mjs
scripts/migrate_clm_v01_to_v02.mjs
```

Target Adapter：

```text
scripts/generate_typescript.mjs
```

公共语义模块：

```text
scripts/lib/model.mjs
```

不要恢复已删除的 Python 双实现。详细命令统一见 `references/node-toolchain.md`。

## 4. CLM v0.2

新建或准备进入 canonical 的模型使用 CLM v0.2。

核心结构：

```text
Domain
Behavior
Rule / Decision
Action / Foreach
StateMachine / Transition
Effect
Constraint / Invariant
Scenario
Primitive
```

v0.2 必须使用：

```text
统一 Node Registry
Typed Expression AST
Symbol Table
Typed Action
Typed Scenario
Semantic Change Set
```

规范：

- `references/clm-v0.2.md`
- `schemas/clm-v0.2.schema.json`
- `references/clm-validator.md`

v0.1 只用于兼容；正式修改前优先迁移。

## 5. 旧代码导入

不要以当前文件为边界，也不要无差别追踪所有调用。

```text
确定目标模块 / 功能
→ 定位入口
→ 扫描一到两层骨架
→ 找关键业务节点
→ 建立 Open Questions
→ 按价值继续追踪
→ 记录 Evidence
→ Observed Behavior
→ Candidate CLM
→ 人或权威规范确认
→ Canonical CLM
```

优先追踪：

- 业务规则、权限、验证；
- 状态变化；
- 数据读写、事务、一致性；
- 事件、队列、回调；
- 重试、幂等、降级；
- 动态分派、配置；
- 关键外部调用。

复杂任务按：

- `references/legacy-import.md`
- `references/legacy-workspace.md`

执行。

## 6. 人类可读逻辑

人应能够通过中文逻辑视图理解主要行为，而不必阅读 AST 或 generated code。

投影只能解释、分组和重排 CLM，不能创造新规则。

详见 `references/human-projection.md`。

## 7. 修改协议

真正独立的单节点修改可使用 Semantic Patch。

一个业务意图涉及多个 Rule / Action / Transition / Scenario / Constraint 时使用 **Semantic Change Set v0.2**。

Change Set 必须：

```text
原子应用
+ base_model_version
+ 可选 base_semantic_hash
+ Semantic Diff
+ 修改后重新校验
+ Impact Analysis
```

自由自然语言只能先转换为 Patch / Change Set Proposal。

详见：

- `references/semantic-patch.md`
- `references/semantic-change-set.md`
- `references/impact-analysis.md`

## 8. 测试

测试期望只来自 CLM。

```text
CLM
├─→ Test Vectors → Target Test Plan → Target Tests
└─→ IIR → Target Code
```

两条路径独立派生，最终在目标运行时汇合。

重点覆盖：

- Rule 正反例；
- 边界；
- Scenario；
- State Transition；
- Invariant / Property；
- Temporal Intent。

详见：

- `references/test-vector-generation.md`
- `references/target-test-generation.md`

## 9. IIR v0.2

固定链路：

```text
CLM
→ Target Profile
→ IIR v0.2
→ IIR Validation
→ Target Test Plan
→ Target Adapter
```

IIR 负责：

```text
Use Case
Repository Contract
External Port
Transaction / Concurrency
Retry / Idempotency
Error Mapping
Primitive Binding
Generation Boundary
Traceability
Unresolved
```

IIR 不得改变业务规则。blocking unresolved 非空时禁止调用 Target Adapter。

详见：

- `references/iir-v0.2.md`
- `schemas/iir-v0.2.schema.json`
- `references/verification-and-generation.md`

## 10. 首个 Reference Target

当前首个参考目标：

```text
TypeScript 5.x
Node.js
SQLite
Vitest
framework-agnostic
```

目标配置：

`evals/fixtures/ts-sqlite.target-profile.json`

TypeScript Generator 是独立 adapter：

`scripts/generate_typescript.mjs`

SQLite 只属于 Target Profile / IIR，不得进入 CLM 领域语义。

详见 `references/typescript-generator-v0.1.md`。

## 11. 默认流水线

常规任务优先使用：

```bash
node scripts/run_pipeline.mjs model.json \
  --target-profile evals/fixtures/ts-sqlite.target-profile.json \
  --generate-ts
```

顺序：

```text
CLM Schema Gate
→ CLM Semantic Gate
→ 可选 Patch / Change Set
→ Impact Analysis
→ Symbol Table
→ 中文逻辑投影
→ Test Vectors
→ IIR v0.2
→ IIR Schema + Semantic Gate
→ Target Test Plan
→ TypeScript + SQLite Adapter
→ Manifest Verification
```

任一步失败立即停止。

详见 `references/end-to-end-pipeline.md`。

## 12. 逻辑优化

```text
O1 归一化       不改变行为
O2 结构重构     预期行为不变，需要等价验证
O3 稳健性改进   事务、幂等、重试、并发等实现语义变化
O4 业务修改     真正改变业务行为，默认需要人工确认
```

重点分析：重复规则、缺失 case、分支冲突、状态机漏洞、不变量冲突、副作用顺序、事务、幂等和并发风险。

没有充分证据时写“潜在问题”，不要把设计偏好描述成确定 bug。

## 13. 回归 Gate

修改 CLM / IIR / 写入协议 / Target Adapter 核心结构后执行：

```bash
node scripts/run_v02_regression.mjs
```

检查：

`references/clm-v0.2-freeze-checklist.md`

## 14. 废弃与兼容

- 被新版本完整替代且没有迁移价值的文件直接删除。
- 不保留重复主规范。
- CLM v0.1 Schema 暂保留，只用于兼容旧模型。
- 新功能不得继续扩展 v0.1。
- 不长期维护 Python / Node 双实现。
- Target Adapter 与通用 CLM/IIR 工具分离。
- 删除资产后必须检查 Skill、Agent prompt、references 和 evals 是否存在死链。

## 15. 禁止事项

- 不把当前文件摘要当模块完整逻辑。
- 不把函数名直译当业务解释。
- 不把 ASSUMED 当 OBSERVED。
- 不在忠实翻译阶段偷偷改业务行为。
- 不把 generated code 当业务事实源。
- 不从 generated code 生成 expected tests。
- 不把框架、Node.js 或 SQLite 细节写进领域规则。
- 不因为文本相似就强行抽公共逻辑。
- 不在 blocking unresolved 非空时宣称实现完整。
- 不绕过 IIR Gate 直接调用 Target Adapter。
- 不宣称 CLM 正确即可自动证明任意实现正确；必须说明实际验证层级。
