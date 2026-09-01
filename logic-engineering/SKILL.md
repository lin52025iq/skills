---
name: logic-engineering
description: 将现有项目中的模块级业务实现重建为与编程语言无关、可由人直接理解和修改的规范逻辑模型（Canonical Logic Model，CLM），并支持逻辑解释、归一化、语义修改、影响分析、测试派生、实现中间表示生成、目标实现投影与一致性验证。适用于逻辑优先开发、旧代码逻辑导入、模块级自然语言解释、逻辑优化和跨语言重实现。
---

# 逻辑工程

本 Skill 把软件开发视为 **逻辑模型的维护、验证与实现投影**，而不是直接维护某一种编程语言的业务源代码。

```text
现有代码 / 人类需求
        ↓
Candidate CLM
        ↓ confirm
Canonical CLM
   ┌────┼───────────────┐
   ↓    ↓               ↓
人类视图  验证           实现投影
   ↓    ↓               ↓
中文逻辑  Test / Check   IIR / Target Code
```

## 1. 不可违反的原则

1. **CLM 是业务事实源。** canonical CLM 优先于自然语言散文和 generated code。
2. **自然语言是人类投影。** 自由文本不能静默成为 canonical 状态。
3. **生成代码是输出。** 业务修改回到 CLM / Semantic Change Set。
4. **Semantic ID 稳定。** 不因文件、类名、框架或目标语言变化而变化。
5. **忠实解释与优化分离。** 先解释“现在做什么”，再讨论“应该怎么改”。
6. **证据优先。** Legacy import 区分 OBSERVED / INFERRED / ASSUMED / UNKNOWN。
7. **LLM 负责提出，确定性 Gate 负责裁决。** Schema、类型、引用、测试和验证器优先于模型主观判断。
8. **业务语义与技术实现分层。** CLM 描述事务、幂等、顺序、互斥等要求；具体数据库、框架和 API 属于 IIR / Target Profile。
9. **测试期望从 CLM 独立派生。** 不从 generated code 反推 expected behavior。
10. **blocking unresolved 非空时禁止宣称实现完整。**

## 2. 四类工作模式

```text
UNDERSTAND
  旧代码导入、模块解释、行为重建

ENGINEER
  归一化、公共规则提取、修改、优化、Semantic Patch / Change Set

REALIZE
  CLM → IIR → Target Test Plan → Target Adapter

VERIFY
  Schema、类型、语义一致性、测试、实现符合性、形式验证
```

用户不需要知道模式名；根据目标自动选择。

## 3. CLM 版本策略

新建模型和准备进入 canonical 的模型优先使用 **CLM v0.2**。

v0.2 核心：

```text
统一 Node Registry
Typed Expression AST
Symbol Table
Typed Action
Typed Scenario
Semantic Change Set
Semantic Hash
```

旧 v0.1 只作为兼容输入；正式修改或生成前优先迁移到 v0.2。

规范：

- `references/clm-v0.2.md`
- `schemas/clm-v0.2.schema.json`
- `references/clm-validator.md`

Node 工具链与命令统一见：

- `references/node-toolchain.md`

## 4. Legacy Code → Candidate CLM

分析现有代码时，不以当前文件为边界，也不追踪所有函数。

```text
确定目标模块 / 功能
→ 找入口
→ 扫描一到两层骨架
→ 识别关键业务节点
→ 维护开放问题
→ 按价值继续追踪
→ 记录 Evidence
→ 形成 Observed Behavior
→ Candidate CLM
→ 确认
→ Canonical CLM
```

优先追踪：

- 业务规则与领域服务；
- 权限、校验和状态变化；
- 数据读写、事务、一致性；
- 事件、队列、回调；
- 重试、幂等、降级；
- 动态分派、配置和关键外部调用。

通常不深入普通日志、getter/setter、简单 DTO 映射和框架内部常规实现。

复杂项目使用：

- `references/legacy-import.md`
- `references/legacy-workspace.md`
- `templates/旧代码导入工作区模板.md`

## 5. 证据等级

```text
OBSERVED   源代码或运行事实直接证明
INFERRED   多个已观察事实组合得到
ASSUMED    依赖尚未验证的框架/运行时语义
UNKNOWN    当前证据不足
```

ASSUMED / UNKNOWN 不得静默升级为 canonical rule。

## 6. CLM 语义结构

主要节点：

```text
Domain       Entity / ValueType / Enum / Relationship
Behavior     Behavior
Rule         Rule
Decision     Decision
Action       Action / Foreach
State        StateMachine / Transition
Effect       Effect
Constraint   Constraint / Invariant
Scenario     Scenario
Primitive    Primitive
```

Node Registry、Symbol Table 和 Semantic Hash 的唯一实现入口在：

`scripts/lib/model.mjs`

禁止其他脚本维护另一份节点集合。

## 7. 人类可读逻辑

人类视图必须从 CLM 投影，不改变 CLM 事实。

优先输出：

```text
目的
前置条件
处理过程
状态变化
副作用
失败情况
约束 / 不变量
场景
未知项 / 证据
```

详细规则：`references/human-projection.md`。

## 8. 修改协议

### 单点修改

真正独立的单节点修改使用 Semantic Patch。

规范：

- `references/semantic-patch.md`
- `schemas/semantic-patch-v0.1.schema.json`

### 业务级修改

一个业务意图涉及多个 Rule / Action / Transition / Scenario / Constraint 时，使用 **Semantic Change Set v0.2**。

要求：

```text
全部成功或全部失败
base_model_version
base_semantic_hash（重要修改优先）
统一 Semantic Diff
统一 Impact Analysis
统一 Verification Requirements
```

规范：

- `references/semantic-change-set.md`
- `schemas/semantic-change-set-v0.2.schema.json`

自由自然语言只先生成 Patch / Change Set Proposal；存在歧义时不直接应用。

## 9. 修改后的增量处理

修改后先做语义影响分析，不默认全量重生成。

影响结果至少区分：

```text
DIRECT
TRANSITIVE
DERIVED
REVIEW
```

并给出需要重算的：

```text
Human Projection
Test Vectors
IIR
Target Test Plan
Target Code
Verification
```

详见 `references/impact-analysis.md`。

## 10. CLM Gate

进入实现投影前至少通过：

```text
CLM JSON Schema
Semantic ID / Collection
引用完整性
Symbol Table
Typed Expression
Typed Action / Scenario
Enum / Type
State consistency
Evidence requirements
```

Schema 失败或 Semantic Gate 失败时，不继续生成 IIR。

## 11. 测试派生

业务期望必须来自 CLM。

```text
CLM
→ Language-neutral Test Vector
→ Target Test Plan
→ Target Test Code
```

优先覆盖：

- Rule 正反例；
- enum complement case；
- 数值边界意图；
- Scenario；
- State Transition / Forbidden Transition；
- Invariant / Property；
- Temporal intent。

详见：

- `references/test-vector-generation.md`
- `references/target-test-generation.md`

## 12. IIR v0.2

实现链路：

```text
CLM
→ Target Profile
→ IIR v0.2
→ IIR Gate
→ Target Test Plan
→ Target Adapter
```

IIR v0.2 负责：

```text
Domain Types
Runtime Bindings
Use Case
Repository Contract
External Port
Transaction / Concurrency
Retry / Idempotency
Error Mapping
Primitive Binding
Generation Region
Traceability
Unresolved
```

IIR 不得改变业务规则。

规范：

- `references/iir-v0.2.md`
- `schemas/iir-v0.2.schema.json`
- `references/verification-and-generation.md`

## 13. 首个 Reference Target

当前首个目标：

```text
TypeScript 5.x
Node.js
SQLite
Vitest
framework-agnostic
```

目标配置：

`evals/fixtures/ts-sqlite.target-profile.json`

Target Adapter：

`scripts/generate_typescript_v02.mjs`

v0.2 生成确定性可执行语义：

```text
Enum             → string literal union
Typed Expression → TS boolean expression
Rule             → guard function
Typed Assignment → 真实赋值
Repository Effect→ Repository 调用
Scenario Expect  → Vitest 真实断言
```

测试信息不足时生成 `it.todo`，禁止 `expect(true)` 假通过。

SQLite 只属于 Target Profile / IIR，不得进入 CLM。

详见 `references/typescript-generator-v0.2.md`。

## 14. 统一流水线

常规任务优先使用 Node 统一流水线。

完整顺序：

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
→ Target Test Plan v0.2
→ TypeScript + SQLite Adapter v0.2（可选）
→ Manifest Verification
→ tsc + Vitest Gate（环境具备工具时，可选）
```

任一步失败立即停止。

具体命令统一见 `references/node-toolchain.md` 和 `references/end-to-end-pipeline.md`。

## 15. 逻辑优化

```text
O1 归一化       不改变行为
O2 结构重构     预期行为不变，需要等价验证
O3 稳健性改进   事务、幂等、重试、并发等实现语义变化
O4 业务修改     真正改变业务行为，默认需要人工确认
```

重点分析：

- 重复规则；
- 缺失 case；
- 分支重叠或不可达；
- 状态机非法路径；
- 不变量冲突；
- 副作用顺序；
- 事务、幂等、重试、并发风险。

没有充分业务证据时写“潜在问题”，不要把设计偏好描述成确定 bug。

## 16. 回归 Gate

修改以下核心协议后运行回归：

```text
CLM
Semantic Patch / Change Set
IIR
Target Test Plan
Target Adapter
Generated Manifest
```

冻结条件见：

`references/clm-v0.2-freeze-checklist.md`

## 17. 废弃与兼容

- 被新版本完整替代且没有迁移价值的文件直接删除。
- 不保留重复主规范或双实现。
- CLM v0.1 Schema 暂保留，只用于兼容旧模型。
- 新功能不得继续扩展 v0.1。
- 不长期维护 Python / Node 双实现。
- 不长期维护旧/新 Target Generator 双实现。
- 删除资产后检查 Skill、Agent、references、evals 和脚本是否存在死链。

## 18. 禁止事项

- 不把当前文件摘要当模块完整逻辑。
- 不把函数名直译当业务解释。
- 不把 ASSUMED 当 OBSERVED。
- 不在忠实解释阶段偷偷修改业务行为。
- 不把 generated code 当业务事实源。
- 不从 generated code 生成 expected tests。
- 不把 TypeScript、Node.js、SQLite 或框架细节写进领域规则。
- 不因为文本或代码相似就强行抽公共逻辑。
- 不在 blocking unresolved 非空时宣称实现完整。
- 不绕过 IIR Gate 直接调用 Target Adapter。
- 不用 `expect(true)` 代替真实业务断言。
- 不宣称 CLM 正确即可自动证明任意实现正确；必须说明实际验证层级。
