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
3. **生成代码是输出。** 完成逻辑优先接管后，业务修改回到 CLM；不要把手改 generated code 当正式业务变更。
4. **每条语义有稳定 ID。** Semantic ID 与文件路径、类名、函数名和目标语言解耦。
5. **忠实解释与优化分离。** 先说明代码实际做什么，再单独提出应该怎样优化。
6. **证据优先。** 旧代码导入必须区分：已观察、推断、假设、未知。
7. **大模型负责提出，确定性工具负责裁决。** Schema、类型、引用、测试、验证器比“模型觉得正确”优先。
8. **业务语义与技术实现分离。** 事务、幂等、顺序、互斥等要求进入 CLM；具体框架绑定进入 IIR / Target Profile。
9. **测试从 CLM 独立派生。** 不从生成代码反推预期结果。
10. **存在 unresolved 时不得宣称实现完整匹配。**

## 2. 四类工作模式

内部统一为四类模式；用户不需要知道模式名。

```text
理解（UNDERSTAND）
  旧代码导入、模块逻辑解释、行为重建

工程（ENGINEER）
  逻辑归一化、公共规则提取、修改、优化、语义补丁

实现（REALIZE）
  CLM → Target Profile → IIR → 目标实现

验证（VERIFY）
  Schema、类型、语义一致性、测试、实现符合性、形式验证
```

## 3. CLM 版本策略

新建模型、准备进入 canonical 的模型优先使用 **CLM v0.2**。

v0.2 的核心变化：

```text
统一 Node Registry
+ Typed Expression AST
+ Symbol Table
+ Typed Action
+ Typed Scenario
+ Semantic Change Set
```

旧 v0.1 模型可兼容读取；需要正式修改或生成时优先迁移：

```bash
python scripts/migrate_clm_v01_to_v02.py old.json -o new.json
```

详细规范见：

- `references/clm-v0.2.md`
- `schemas/clm-v0.2.schema.json`
- `scripts/clm_model.py`
- `scripts/expression_ast.py`
- `scripts/symbol_table.py`

## 4. 旧代码理解流程

分析现有项目时，不以当前文件为边界，也不追踪所有函数。

```text
确定目标模块 / 功能
→ 找入口
→ 扫描一到两层骨架
→ 识别关键业务节点
→ 维护开放问题
→ 按价值继续追踪
→ 记录 Evidence
→ 形成 Observed Behavior
→ 生成 Candidate CLM
→ 人或权威规范确认
→ Canonical CLM
```

优先追踪：

- 业务规则与领域服务；
- 权限、验证和状态变化；
- 数据读写、事务和一致性；
- 事件、队列、回调；
- 重试、幂等、降级；
- 动态分派、配置和重要外部调用。

通常不深入普通日志、getter/setter、简单 DTO 映射和框架内部常规实现。

复杂项目按 `references/legacy-workspace.md` 维护工作区；详细导入原则见 `references/legacy-import.md`。

## 5. 证据等级

```text
已观察（OBSERVED）  源代码直接证明
推断（INFERRED）    多个已观察事实组合得到
假设（ASSUMED）     依赖尚未验证的框架或运行时语义
未知（UNKNOWN）     当前证据不足
```

`ASSUMED / UNKNOWN` 不得静默升级成 canonical rule。

## 6. CLM 语义结构

CLM 是带类型的语义图，主要包含：

```text
领域      Entity / ValueType / Enum / Relationship
行为      Behavior
规则      Rule
判断      Decision
动作      Action / Foreach
状态      StateMachine / Transition
影响      Effect
约束      Constraint / Invariant
场景      Scenario
基础能力  Primitive
```

所有工具必须通过 `scripts/clm_model.py` 使用统一 Node Registry；禁止各脚本自行维护节点集合。

## 7. 人类可读逻辑

需要给人审阅时，从 CLM 投影中文逻辑：

```bash
python scripts/render_human_logic.py model.json -o logic.md
```

投影可以重排和解释，但不能增加 CLM 中不存在的新业务规则。

详细规则见 `references/human-projection.md`。

## 8. 修改逻辑

### 单点修改

简单修改可使用 Semantic Patch：

```text
修改一个 Rule 字段
新增一个枚举成员
删除一个节点
```

规范见：

- `references/semantic-patch.md`
- `schemas/semantic-patch-v0.1.schema.json`
- `scripts/apply_semantic_patch.py`

### 业务级修改

一个业务修改涉及多个节点时，优先使用 **Semantic Change Set v0.2**。

```text
一个变更集
├─ 修改 Rule
├─ 增加 Transition
├─ 增加 Scenario
└─ 更新 Constraint
```

整个变更集必须全部成功或全部失败。

规范和工具：

- `schemas/semantic-change-set-v0.2.schema.json`
- `scripts/apply_semantic_change_set.py`

自由自然语言修改只能先转换成 Patch / Change Set Proposal，再应用。

## 9. 修改后的增量处理

逻辑修改后先分析影响，不默认全量重生成：

```bash
python scripts/analyze_impact.py model.json <changed-semantic-id...>
```

影响结果至少区分：

```text
直接影响
传递影响
需要重生成的派生产物
需要人工复核的候选影响
```

详见 `references/impact-analysis.md`。

## 10. CLM 校验

新模型必须经过：

```text
Schema
→ Semantic ID / Collection
→ 引用完整性
→ Symbol Table
→ Typed Expression
→ 枚举类型和值
→ 基础类型兼容
→ 状态迁移一致性
→ Evidence 要求
```

```bash
python scripts/validate_clm.py model.json --schema schemas/clm-v0.2.schema.json
```

详细错误语义见 `references/clm-validator.md`。

## 11. 测试派生

测试期望直接来自 CLM：

```bash
python scripts/generate_test_vectors.py model.json --output tests.json
```

优先覆盖：

- Rule 正反例；
- 数值边界；
- Scenario；
- State Transition；
- Forbidden Transition；
- Invariant / Property；
- Temporal Rule。

详细规则见 `references/test-vector-generation.md`。

## 12. 实现投影

生成链路固定为：

```text
CLM
→ Target Profile
→ Primitive Binding
→ Implementation IR（IIR）
→ Target Generator
```

```bash
python scripts/compile_iir.py model.json target-profile.json -o implementation.iir.json
```

IIR 只负责技术组织，不得改变业务规则。

详见：

- `references/implementation-ir.md`
- `references/verification-and-generation.md`

## 13. 最小统一流水线

常规流程优先使用：

```bash
python scripts/run_logic_pipeline.py model.json \
  --patch patch.json \
  --target-profile target-profile.json
```

流水线执行：

```text
版本识别
→ Schema + Semantic Validation
→ 可选语义修改
→ 再次校验
→ Impact Analysis
→ Symbol Table
→ 中文逻辑投影
→ Test Vectors
→ IIR
```

任一步失败都应终止，不继续生成“看起来合理”的后续结果。

详见 `references/end-to-end-pipeline.md`。

## 14. 逻辑优化

优化只操作 CLM，不直接优化 generated code。

```text
O1 归一化       不改变行为
O2 结构重构     预期行为不变，需要等价验证
O3 稳健性改进   事务、幂等、重试、并发等实现语义变化
O4 业务修改     真正改变业务行为，默认需要人工确认
```

重点检查：

- 重复规则；
- 缺失 case；
- 分支重叠或不可达；
- 状态机非法路径；
- 不变量冲突；
- 副作用顺序风险；
- 事务、幂等、并发问题。

没有充分业务证据时使用“潜在问题”，不要把设计偏好当确定 bug。

## 15. 默认产出

根据任务只生成最小充分集合：

```text
Candidate / Canonical CLM
中文逻辑视图
Evidence Map
Open Questions
Semantic Patch / Change Set
Semantic Diff
Impact Analysis
Symbol Table
Test Vectors
Target Profile / IIR
Verification Result
```

不要为了形式生成所有文件。

## 16. 禁止事项

- 不把当前文件摘要当模块完整逻辑。
- 不把函数名直译当业务解释。
- 不把假设当已观察。
- 不在忠实翻译阶段偷偷改业务行为。
- 不把 generated code 当业务事实源。
- 不从 generated code 生成 expected tests。
- 不把框架特有语法直接写入领域规则。
- 不因为文本相似就强行抽公共规则。
- 不在 `unresolved` 非空时宣称实现完整。
- 不宣称“CLM 正确即可自动证明任何生成实现都正确”；必须说明实际验证层级。
