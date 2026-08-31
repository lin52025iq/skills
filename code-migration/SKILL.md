---
name: code-migration
description: 用于将一个或多个现有项目中的功能、业务规则和用户能力迁移、融合或重构到目标项目。适用于前端项目迁入新仓库、跨框架或技术栈重实现、多个旧项目能力合并、模块整合、功能删改融合、目标架构适配与渐进切流。迁移以源行为证据、目标期望行为和目标项目原生架构为中心，先建立可追踪的源行为契约和功能台账，再按 Slice / Workstream 实施、验证与清理；默认不按源文件、目录、组件或状态结构一比一翻译，并支持通过安全检查后的多 Agent 受控并行迁移。
---

# Code Migration

把代码迁移视为“业务能力在新上下文中的受控重建”，不是文件搬运或旧架构复制。

```text
Source Evidence
→ Source Behavior Contract
→ Desired Target Behavior
→ Target-native Design
→ Module / Feature / Feature Item Ledger
→ Slice / Controlled Workstream
→ Implementation / Verification / Integration
→ Cutover / Cleanup
```

## 1. 核心原则

1. **迁移的是能力，不是文件。** Source 文件只是证据，不是迁移边界。
2. **Source 是事实，不是目标规范。** 它说明旧系统实际做了什么。
3. **关键源行为必须可追踪。** 形成 Source Behavior，并决定“保持 / 目标修改 / 不迁移 / 未知”。
4. **用户意图与目标产品决定目标行为。** 必须保留的 Invariant 不得因技术迁移丢失。
5. **Target 决定实现形状。** Router、状态、数据层、组件、目录、错误和测试遵循目标仓库惯例。
6. **功能台账维护完整范围。** Slice Queue 只负责调度。
7. **每个 Workstream 单焦点，全局可安全并行。** 独立 Feature 通过并行安全 Gate 后可由不同 Implementer 同时开发。
8. **实施/验证状态实时更新。** 不先批量写完再补文档。
9. **用户规则是执行约束。** 每个 Slice / Workstream 开始前检查生效规则。
10. **验证面向目标行为。** 保持项验证不回归，批准变化验证新行为正确。
11. **机械变化自动化，语义变化分析，产品变化显式决策。**
12. **迁移完成还包括集成、切流和遗留清理。**

## 2. 启动方式

先识别 Source、Target、迁移目标、用户约束和目标技术栈，再检查 Target 根目录 `.code-migration/`。

### 已有工作区

按顺序恢复：

1. `00-迁移状态总览.md`；
2. Active Workstreams、Owner、Input Baseline；
3. `06-迁移约束与开发规则.md`；
4. `02-迁移模块功能点清单.md`；
5. Source Behavior、Decision、执行计划；
6. Git、代码和测试状态。

不一致时先最小范围重新校准，不重新扫描全部 Source。

### 新工作区

长周期迁移按需创建：

```text
.code-migration/
├── 00-迁移状态总览.md
├── 01-迁移任务上下文.md
├── 02-迁移模块功能点清单.md
├── 03-功能融合映射.md             # 多源按需
├── 04-迁移决策记录.md             # 重大决策按需
├── 05-迁移执行计划.md
├── 06-迁移约束与开发规则.md
├── 07-源行为与目标对齐清单.md     # 复杂 Feature 按需
└── modules/<module>/              # 独立规划/验证有价值时
```

小任务不机械生成全部文档。

## 3. 变化与迁移决策

变化分为：

| 类型 | 默认处理 |
|---|---|
| Mechanical | Codemod / 小批量自动化 |
| Semantic | 理解语义后按目标架构重实现 |
| Product | 按用户意图和目标产品要求决策 |

Feature 决策：

```text
KEEP / ADAPT / MERGE / SPLIT / REMOVE
REPLACE / REUSE_TARGET / NEW / DEFER / UNKNOWN
```

Source Behavior 决策：

```text
保持 / 目标修改 / 不迁移 / 未知
```

重大删除、融合、替换、Invariant 变化或高风险产品变化应记录 Decision。

## 4. 证据、Invariant 与 Source Behavior

证据等级：

```text
C3 Runtime
C2 Contract
C1 Static
C0 Unknown
```

优先用于确认现役状态、业务规则、Invariant、权限、金额/状态、删除/融合和兼容行为。

关键 Feature 应提取用户可观察行为，例如：

- Entry / Precondition；
- Loading / Empty / Error / Success；
- 字段显隐与格式；
- Permission / Disabled / Hidden；
- Validation / Error Recovery；
- Navigation / Deep Link / Back-forward；
- 状态流转 / Data Contract；
- Integration / Analytics；
- Responsive / Accessibility。

详见 `references/11-源行为契约与开发对齐.md`。

## 5. 八阶段迁移流程

### Phase 1 — 意图、范围和长期规则

明确保留/修改/删除/新增能力、非功能要求、发布/回滚和用户开发约束。

长期规则写入 `06-迁移约束与开发规则.md`。详见 `references/10-用户约束与开发规则.md`。

### Phase 2 — 恢复 Source 真实能力

从 Route/真实入口出发，结合调用链、权限、Flag、测试、配置和运行证据恢复功能。代码存在不等于现役。

详见 `references/01-迁移上下文与源项目理解.md`。

### Phase 3 — 建立 Source Behavior Contract

复杂 Feature 为关键行为建立稳定 ID：

```text
SB-<FEATURE>-001
```

每条记录：

```text
Source Behavior
Evidence
Target Decision
Desired Target Behavior
Feature Item
Validation Method
```

所有“保持”行为必须映射至少一个范围内 Feature Item；“目标修改”必须写明新行为。

详见 `references/02-功能语义与业务规则.md` 与 `references/11-源行为契约与开发对齐.md`。

### Phase 4 — 形成 Desired Target Behavior

多源先归一化：

```text
Source A/B/C → Canonical Feature / Domain Model → Desired Target Behavior
```

决策顺序：用户意图 → 目标产品 → Invariant → Target 稳定约束 → C3/C2 → C1 → 推断。

关键冲突无法安全决定时进入澄清循环。

详见 `references/03-多项目融合与冲突决策.md`。

### Phase 5 — Target-native 设计

研究目标项目稳定相似实现和公共能力，决定 Module、Route、Data、State、UI、Permission、Testing。已有能力优先 `REUSE_TARGET`。

详见 `references/04-目标项目架构理解.md`。

### Phase 6 — 功能台账和依赖

范围整理为：

```text
Module → Feature → Feature Item
```

Feature Item 至少维护：

```text
范围：范围内 / 延后 / 范围外
必需：是 / 否
实施：未开始 / 实施中 / 已实施
验证：未验证 / 验证中 / 通过 / 失败 / 不适用
阻塞：未阻塞 / 已阻塞
Source Behavior IDs
Workstream / Owner / Verifier
```

分析代码、数据、语义、发布依赖，形成串行/并行候选。

详见 `references/05-迁移设计与策略选择.md`、`references/06-分阶段迁移与功能切片.md`。

### Phase 7 — Slice / Workstream 实施

开始前通过 Source Coverage Gate：

- 关键 Source Behavior 已盘点并有 ID；
- 每条行为已决定“保持 / 目标修改 / 不迁移 / 未知”；
- 所有“保持”行为已映射范围内 Item；
- 所有“目标修改”有明确 Target Behavior；
- 权限、状态、错误、Loading/Empty、Navigation、Data Contract 等适用维度已覆盖；
- 不存在会改变方向的关键“未知”。

再检查用户规则、Target 准备度和依赖。

单 Workstream 内只保持一个主要实施焦点；多个独立 Feature 通过 Parallel Safety Gate 后可以并行。

详见 `references/09-迁移状态与跨会话协作.md`。

### Phase 8 — 验证、集成、切流与清理

验证分为：

```text
Workstream Validation → Integration Gate
```

Workstream Validation 验证当前 Items 与 Source/Target Behavior。

多个 Workstream 合并后，按风险执行 Integration Gate：build/typecheck、共享测试、Route/Permission、shared state/query/API、E2E、CSS/bundle、用户规则等。

必要的 Integration Gate 未通过时，不得宣布并行批次最终完成。

详见 `references/08-验证切流与遗留清理.md`。

## 6. 运行时状态

Feature 生命周期：

```text
已发现 → 已设计 → 实施中 → 验证中 → 已迁移 → 已清理
```

执行队列：

```text
待执行 / 当前执行 / 已阻塞 / 验证中 / 已完成
```

`已阻塞` 是附加状态，不替代生命周期。

## 7. Workstream Input Baseline

实施 Workstream 开始前冻结：

```text
Source Behavior / Evidence Revision
Desired Target Behavior Revision
Decision / Rule 版本
Target Mapping 基线
Started At Commit
```

关键输入变化影响当前实现时：

```text
已阻塞 → 更新基线 → 重新检查开始条件 → 再继续
```

不得按过期行为模型继续开发。

## 8. Parallel Safety Gate

并行前检查：

- 相同生产文件/组件；
- Route / Layout / Store / Query ownership；
- API / Data Contract / shared types；
- 权限模型、状态机、Invariant；
- 未完成 Foundation；
- 公共 abstraction / Adapter / Feature Flag；
- package manifest / lockfile；
- barrel/index、Route/Navigation/Permission registry；
- codegen/schema/generated/i18n aggregate；
- 共享生成器/脚本；
- 明确先后依赖。

独立性必须同时覆盖：

```text
代码边界 + 数据/契约 + 业务语义 + 发布/合并路径
```

有高风险重叠时拆 Foundation、指定唯一 Owner 或退回串行。

并行写代码优先独立 branch / worktree / isolated workspace；共享 working tree 无法可靠隔离时退回串行。

## 9. Ownership 与状态写入

- 同一 Feature Item 同时只能有一个生产代码 Owner；
- 共享 Contract / Foundation 必须唯一 Owner；
- Implementer 更新自己拥有的 Item 实施状态；
- Verifier 更新自己负责的验证结果；
- Analyst 更新分析输出，不写生产代码；
- Coordinator 汇总 Active Workstreams、跨 Workstream 依赖/冲突和 `00-迁移状态总览.md`。

Coordinator 不是所有细粒度状态的唯一 Writer，但同一状态块同时只能有一个 Owner。

## 10. Slice / Workstream 开始条件

实施前确认：

- Source Coverage Gate 已通过；
- Target Behavior 和 Feature Items 已明确；
- Input Baseline 已记录；
- Target 落点、依赖、验证方式存在；
- 生效用户规则检查通过；
- 并行时 Parallel Safety Gate、Workspace Isolation、Ownership 明确。

规则处理：

```text
必须未满足 → 不开始
违反禁止 → 改方案
必须询问未确认 → 已阻塞
偏离建议 → 记录原因
```

## 11. 完成条件与 Integration Gate

Slice / Workstream 完成至少满足：

- Items 状态与实际代码一致；
- Source Behavior 映射无遗漏；
- Workstream Validation 通过；
- 新发现 Behavior / Item 已写回；
- 输入基线无未处理漂移；
- 业务规则、Invariant、Permission、Data Contract、Error Path 已覆盖；
- 未违反生效用户规则。

存在共享运行边界的多个 Workstream 合并后必须再通过 Integration Gate。

## 12. 澄清循环

```text
必须询问 / 可推断 / 可延后
```

只有证据不足且会实质改变目标行为或不可逆方向时才“必须询问”。目标仓库稳定工程惯例优先“可推断”。

## 13. 用户规则

规则：

```text
作用域 + 触发条件 + 强度 + 动作/约束
```

强度：`必须 / 禁止 / 必须询问 / 建议`；状态：`生效中 / 已暂停 / 已失效`。

必须工具不可用时不得静默替代，相关操作标记“已阻塞”，由用户决定启用、替代、改规则或延后。

详见 `references/10-用户约束与开发规则.md`。

## 14. 跨会话恢复

新对话恢复：

1. 总体状态和 Active Workstreams；
2. 生效用户规则；
3. Feature / Item 台账；
4. Source Behavior / Decision / Input Baseline；
5. 执行计划；
6. Git、working tree、代码和测试；
7. 不一致时最小重新校准。

详见 `references/09-迁移状态与跨会话协作.md`。

## 15. 自动化约束

Codemod/批量脚本只用于可证明的 Mechanical 变化，先代表性验证再扩大。至少说明：`What / Why / Scope / Expected Change / Validation / Rollback`。

详见 `references/07-自动化与增量实施.md`。

## 16. 禁止方式

- 不按文件或源目录树一一迁移；
- 不机械复制旧 Store/API/组件层；
- 不因为代码存在就恢复废弃能力；
- 不用 Slice Queue 代替功能台账；
- 不让 Slice“已完成”掩盖未完成 Item；
- 不在关键 Source Behavior 未覆盖时大规模实施；
- 不让多个 Agent 并行写同一 Item、共享契约或无法隔离的工作区；
- 不因各 Workstream 单独通过就跳过必要 Integration Gate；
- 不在 Input Baseline 过期后继续开发；
- 不静默违反用户规则；
- 不通过放宽测试阈值或删除断言证明成功。

## 17. 文档强度

| 范围 | 默认产物 |
|---|---|
| 单组件/短任务 | 对话内行为契约和验证 |
| 单页面单会话 | 功能台账 + 简化执行计划 |
| 长周期页面/模块 | 状态总览 + 上下文 + 台账 + 行为对齐 + 执行计划 + 用户规则 |
| 多项目融合 | 再增加融合映射和必要 Decision |
| 整应用 | 模块台账、行为契约、规则、Workstreams、集成验证、切流/清理 |

## 18. 结束报告

至少说明：目标与完成能力、Feature/Item 状态、Source Coverage、Workstream/Owner/Input Baseline、Workstream Validation/Integration Gate、阻塞/延后/澄清、关键用户规则、下一动作和 `.code-migration/` 同步状态。
