---
name: code-migration
description: 用于将一个或多个现有项目中的功能、业务规则和用户能力迁移、融合或重构到目标项目。适用于前端项目迁入新仓库、跨框架或技术栈重实现、多个旧项目能力合并、模块整合、功能删改融合、目标架构适配与渐进切流。迁移以源行为证据、目标期望行为和目标项目原生架构为中心，先建立可追踪的源行为契约和功能台账，再按 Slice / Workstream 实施、验证与清理；默认不按源文件、目录、组件或状态结构一比一翻译，并支持通过安全检查后的多 Agent 受控并行迁移。
---

# Code Migration

把代码迁移视为“业务能力在新上下文中的受控重建”，不是文件搬运、语法翻译，也不是旧架构复制。

核心链路：

```text
Source Evidence
    ↓
Source Behavior Contract
    ↓
Desired Target Behavior
    ↓
Target-native Design
    ↓
Module → Feature → Feature Item Ledger
    ↓
Slice / Controlled Workstream
    ↓
Implementation → Verification → Integration
    ↓
Cutover → Cleanup
```

## 1. 核心原则

1. **迁移的是能力，不是文件。** 文件、组件、Store、Hook、Service 只是理解源能力的证据。
2. **Source 是事实证据，不是目标规范。** 源项目说明旧系统实际做了什么，不能自动决定新系统必须继续怎样做。
3. **源行为必须可追踪。** 关键可观察行为要形成 Source Behavior，并映射到“保持 / 目标修改 / 不迁移 / 未知”。
4. **先确定目标期望行为，再设计代码。** 用户意图、目标产品要求和必须保留的 Invariant 决定目标行为。
5. **Target 决定实现形状。** Router、状态、数据层、组件、目录、错误处理、测试和工程模式遵循目标仓库稳定惯例。
6. **完整范围由功能台账维护。** Module → Feature → Feature Item 是范围和完成度的事实记录；Slice Queue 只负责调度。
7. **每个 Workstream 单焦点，全局可安全并行。** 一个 Workstream 内只推进一个主要实施焦点；多个独立 Feature 通过并行安全 Gate 后可以由不同 Implementer 同时开发。
8. **开发过程中实时更新状态。** 不允许先写完一批代码再补台账。
9. **用户规则是执行约束。** 用户可规定必须/禁止的工具、技术、测试方式和确认点。
10. **验证面向目标行为。** 保持项验证源行为没有丢失；批准变化验证新行为正确。
11. **机械变化自动化，语义变化分析，产品变化显式决策。** Codemod 只用于可证明安全的 Mechanical 变化。
12. **迁移完成不等于新代码能跑。** 还要完成集成验证、切流和遗留清理。

## 2. 启动方式

收到迁移请求后，先根据用户上下文识别：

- Source 项目；
- Target 仓库；
- 迁移目标；
- 用户明确约束；
- 已知目标架构和技术栈。

然后检查目标仓库根目录：

```text
.code-migration/
```

### 已存在工作区

优先恢复，不重新初始化：

1. 读取 `00-迁移状态总览.md`；
2. 恢复 Active Workstreams、Owner、输入基线和当前状态；
3. 读取 `06-迁移约束与开发规则.md` 中所有“生效中”规则；
4. 读取 `02-迁移模块功能点清单.md`；
5. 根据当前 Feature 读取 Source Behavior / 详细语义 / Decision / 执行计划；
6. 核对 Git、实际代码和测试状态；
7. 如有冲突，先做最小范围重新校准。

### 不存在工作区

对长周期页面、业务模块、多项目融合或整应用迁移，按需创建：

```text
.code-migration/
├── 00-迁移状态总览.md
├── 01-迁移任务上下文.md
├── 02-迁移模块功能点清单.md
├── 03-功能融合映射.md             # 多源时按需
├── 04-迁移决策记录.md             # 重大决策时按需
├── 05-迁移执行计划.md
├── 06-迁移约束与开发规则.md
├── 07-源行为与目标对齐清单.md     # 复杂 Feature/模块按需
└── modules/<module>/              # 独立规划/验证有价值时
```

单组件或很小的一次性任务可降低文档强度，不机械创建全部文件。

## 3. 三类变化

| 类型 | 含义 | 默认处理 |
|---|---|---|
| Mechanical | import、API rename、确定性的语法/结构变化 | Codemod / 小批量自动化 |
| Semantic | 业务行为、状态语义、生命周期、数据、副作用 | 理解语义后按目标架构重实现 |
| Product | 功能增加、删除、融合、规则或 UX 改变 | 按用户意图和目标产品要求决策 |

不得用 Mechanical 工具替代 Semantic / Product 判断。

## 4. 迁移决策

Feature 级迁移决策使用：

```text
KEEP / ADAPT / MERGE / SPLIT / REMOVE
REPLACE / REUSE_TARGET / NEW / DEFER / UNKNOWN
```

重大 `REMOVE / MERGE / REPLACE`、Invariant 变化或高风险产品行为变化应记录 Decision。

Source Behavior 级目标决策使用：

```text
保持 / 目标修改 / 不迁移 / 未知
```

其中：

- `保持`：目标必须覆盖对应可观察行为；
- `目标修改`：必须写明批准后的 Target Behavior；
- `不迁移`：必须有范围或产品依据；
- `未知`：关键行为未决时不得假装已设计完成。

## 5. 证据、Invariant 与 Source Behavior

证据等级：

```text
C3 Runtime  ：真实运行、用户路径、E2E、生产/预发布证据
C2 Contract ：测试、API/配置/设计契约、明确文档
C1 Static   ：静态代码、调用关系、样式、提交历史
C0 Unknown  ：推断或缺少可靠证据
```

优先用于确认：功能是否现役、Business Rule、Invariant、权限、金额/状态、删除/融合判断、兼容行为。

对关键 Feature 提取可观察 Source Behavior，例如：

```text
入口 / 前置条件
加载 / 空状态 / 错误状态
核心操作
权限 / Disabled / Hidden
数据格式和字段显隐
导航 / Deep Link / Back-forward
状态流转 / 表单校验
副作用 / Analytics / Integration
响应式 / Accessibility
```

不要只记录“有订单详情”这种粗粒度描述。

详见 `references/11-源行为契约与开发对齐.md`。

## 6. 八阶段迁移流程

### Phase 1 — 确定意图、范围和长期规则

明确迁移目标、保留/修改/删除/新增能力、非功能要求、发布/回滚要求和用户开发约束。

长期规则写入 `.code-migration/06-迁移约束与开发规则.md`。详见 `references/10-用户约束与开发规则.md`。

### Phase 2 — 恢复 Source 真实能力

从真实 Route/入口出发，结合调用链、权限、Flag、测试、配置和运行证据恢复真实功能。

代码存在不等于功能现役。

详见 `references/01-迁移上下文与源项目理解.md`。

### Phase 3 — 建立 Source Behavior Contract

把 Source 功能拆成可验证行为，并为重要行为分配稳定 ID：

```text
SB-<FEATURE>-001
```

每条行为至少记录：

```text
Source Behavior
Evidence
Target Decision
Desired Target Behavior
关联 Feature Item
Validation Method
```

所有“保持”的关键 Source Behavior 必须映射到至少一个范围内 Feature Item；否则视为迁移遗漏。

所有“目标修改”必须有明确批准后的 Target Behavior。

详见 `references/02-功能语义与业务规则.md` 与 `references/11-源行为契约与开发对齐.md`。

### Phase 4 — 形成 Desired Target Behavior 并解决多源冲突

多源先归一化：

```text
Source A ─┐
Source B ─┼→ Canonical Feature / Domain Model
Source C ─┘
                 ↓
         Desired Target Behavior
```

决策顺序：用户明确意图 → 目标产品要求 → 必须保留的 Invariant → 目标系统稳定约束 → C3/C2 → C1 → 推断。

关键冲突无法安全决定时进入澄清循环。

详见 `references/03-多项目融合与冲突决策.md`。

### Phase 5 — Target-native 设计

研究目标项目稳定相似实现和公共能力，再决定目标 Module、Route、Data、State、UI、Permission 和 Testing。

已有能力优先 `REUSE_TARGET`；缺失时只补最小必要 Foundation。

详见 `references/04-目标项目架构理解.md`。

### Phase 6 — 建立功能台账、依赖和 Workstream 候选

迁移范围整理成：

```text
Module
  └─ Feature
       └─ Feature Item
```

每个 Feature Item 至少维护：

```text
范围状态：范围内 / 延后 / 范围外
是否必需：是 / 否
实施状态：未开始 / 实施中 / 已实施
验证状态：未验证 / 验证中 / 通过 / 失败 / 不适用
阻塞状态：未阻塞 / 已阻塞
Source Behavior IDs
Workstream ID / Owner / Verifier
```

同时分析 Feature 间的代码、数据、语义和发布依赖，决定串行或并行候选。

详见 `references/05-迁移设计与策略选择.md` 与 `references/06-分阶段迁移与功能切片.md`。

### Phase 7 — Slice / Workstream 实施

每个 Slice 开始前先通过 Source Coverage Gate：

- 关键 Source Behavior 已盘点；
- 每条关键行为已决定“保持 / 目标修改 / 不迁移 / 未知”；
- 所有“保持”行为都有 Feature Item；
- “目标修改”有明确 Target Behavior；
- 权限、状态、错误、Loading/Empty、Navigation 等关键维度已覆盖；
- 不存在会改变方向的关键 Unknown。

再检查用户规则和目标实现准备度。

单 Workstream 内只保持一个主要实施焦点。

多个独立 Feature 若通过 Parallel Safety Gate，可以建立多个 Active Workstreams 并由不同 Implementer 同时开发。

详见 `references/09-迁移状态与跨会话协作.md`。

### Phase 8 — 验证、集成、切流与清理

验证分两层：

```text
Workstream Validation
→ Integration Gate
```

Workstream Validation 验证当前 Feature Items 和 Source/Target Behavior。

多个并行 Workstream 合并后必须做 Integration Gate，按风险检查 build/typecheck、共享测试、Route/Permission、shared state/query/API、E2E、CSS/bundle、用户规则等。

只有独立验证和必要的 Integration Gate 都通过，才能把相关 Feature 视为最终完成并进入后续切流/清理。

详见 `references/08-验证切流与遗留清理.md`。

## 7. 运行时状态

Feature 生命周期：

```text
已发现 → 已设计 → 实施中 → 验证中 → 已迁移 → 已清理
```

Feature Item：

```text
范围状态：范围内 / 延后 / 范围外
实施状态：未开始 / 实施中 / 已实施
验证状态：未验证 / 验证中 / 通过 / 失败 / 不适用
阻塞状态：未阻塞 / 已阻塞
```

执行队列：

```text
待执行 / 当前执行 / 已阻塞 / 验证中 / 已完成
```

`已阻塞` 是附加状态，不替代生命周期。

## 8. Workstream Input Baseline

每个实施 Workstream 开始前冻结：

```text
Source Behavior / Evidence Revision
Desired Target Behavior Revision
Decision / Rule 版本
Target Mapping 基线
Started At Commit
```

若实施过程中 Source Behavior、Decision、规则或 Target Behavior 发生影响当前实现的变化：

```text
暂停相关 Items
→ 标记已阻塞
→ 更新输入基线
→ 重新检查开始条件
→ 再继续
```

不得让 Implementer 按已过期的行为模型继续开发。

## 9. Parallel Safety Gate

并行实施前检查：

- 相同生产文件/组件；
- Route / Layout / Store / Query ownership；
- API / Data Contract / shared types；
- 权限模型、状态机、Invariant；
- 未完成 Foundation；
- 公共组件 / abstraction；
- Adapter / Feature Flag / 切流路径；
- package manifest / lockfile；
- barrel/index、Route/Navigation/Permission registry；
- codegen/schema/generated/i18n aggregate 输出；
- 共享生成器或脚本；
- 明确先后依赖。

判断独立性必须同时覆盖：

```text
代码边界 + 数据/契约 + 业务语义 + 发布/合并路径
```

有高风险重叠时，拆 Foundation、指定唯一 Owner 或退回串行。

真正并行写代码时优先使用独立 branch / worktree / isolated workspace；共享 working tree 无法可靠隔离写入时退回串行。

## 10. Ownership 与状态写入

同一个 Feature Item 同一时刻只能有一个生产代码 Owner；共享 Contract / Foundation 也必须有唯一 Owner。

默认写入边界：

- Implementer：更新自己拥有的 Feature Item 实施状态；
- Verifier：更新自己负责的验证结果；
- Source/Target Analyst：更新其分析输出，不写生产代码；
- Coordinator：汇总 Active Workstreams、跨 Workstream 依赖、冲突和 `00-迁移状态总览.md`。

Coordinator 不是所有细粒度状态的唯一写入者；但同一状态块同一时刻只能有一个 Owner。

## 11. Slice / Workstream 开始条件

开始实施前确认：

- Source Coverage Gate 已通过；
- 目标期望行为足够明确；
- Feature / Items 已进入功能台账；
- Workstream Input Baseline 已记录；
- Target 落点和项目惯例明确；
- 依赖和验证方法存在；
- 已检查所有“生效中”用户规则；
- 并行时已通过 Parallel Safety Gate 并明确 Workspace Isolation / Ownership。

规则处理：

- `必须` 未满足 → 不得开始；
- 会违反 `禁止` → 改方案；
- `必须询问` 未确认 → 标记“已阻塞”；
- 偏离 `建议` → 记录原因。

## 12. 完成条件与 Integration Gate

Slice / Workstream 完成至少满足：

- 覆盖 Feature Items 状态真实；
- Source Behavior 映射无遗漏；
- Workstream Validation 通过；
- 新发现必要 Item 已补入台账；
- Business Rule / Invariant / Permission / Data Contract / Error Path 已覆盖；
- 当前 Feature 生命周期已重新计算；
- 未静默扩大 Scope 或违反用户规则。

多个 Workstream 合并后，如果存在共享运行边界，必须再通过 Integration Gate。

Integration Gate 失败时，相关 Workstream 不得进入最终完成状态，由 Coordinator 指定修复 Owner。

## 13. 澄清循环

运行时类型：

```text
必须询问 / 可推断 / 可延后
```

只有证据不足且答案会实质改变目标行为或不可逆方向时才“必须询问”。普通目标工程惯例优先“可推断”。

## 14. 用户规则

规则结构：

```text
作用域 + 触发条件 + 强度 + 动作/约束
```

强度：

```text
必须 / 禁止 / 必须询问 / 建议
```

状态：

```text
生效中 / 已暂停 / 已失效
```

必须使用的工具不可用、无权限或不适配环境时，不得静默替换；相关操作标记“已阻塞”，由用户决定启用、替代、修改规则或延后。

详见 `references/10-用户约束与开发规则.md`。

## 15. 跨会话恢复

`.code-migration/00-迁移状态总览.md` 是恢复入口，不是高于真实代码、测试、规则和 Decision 的绝对事实源。

新对话恢复：

1. 总体状态和 Active Workstreams；
2. 生效用户规则；
3. Feature / Feature Item 台账；
4. Source Behavior / Decision / Workstream Input Baseline；
5. 当前执行计划；
6. Git、working tree、代码和测试；
7. 不一致时最小重新校准。

详见 `references/09-迁移状态与跨会话协作.md`。

## 16. 自动化约束

Codemod、正则替换或批量脚本只用于可证明的 Mechanical 变化。先代表性样本验证，再扩大批次。

自动修改至少能说明：`What / Why / Scope / Expected Change / Validation / Rollback`。

详见 `references/07-自动化与增量实施.md`。

## 17. 禁止的迁移方式

- 不按文件或源目录树一一迁移；
- 不把旧 Store/API abstraction/组件层机械复刻；
- 不因为代码存在就自动恢复废弃能力；
- 不用 Slice Queue 代替完整功能台账；
- 不让 Slice“已完成”掩盖未完成 Feature Item；
- 不在关键 Source Behavior 未覆盖时进入大规模实施；
- 不让多个 Agent 并行写同一 Feature Item、共享契约或无法隔离的工作区；
- 不因为各 Workstream 单独通过就跳过必要的 Integration Gate；
- 不让 Implementer 在输入基线过期后继续开发；
- 不静默违反用户工具/技术/确认规则；
- 不通过放宽阈值、删除断言或隐藏错误证明迁移成功。

## 18. 文档强度按规模自适应

| 范围 | 默认产物 |
|---|---|
| 单组件/短任务 | 对话内行为契约和验证即可 |
| 单页面且单会话 | 功能台账 + 简化执行计划 |
| 长周期页面/业务模块 | 状态总览 + 上下文 + 功能台账 + 行为对齐 + 执行计划 + 用户规则 |
| 多项目融合 | 再增加融合映射和必要 Decision |
| 整应用迁移 | 完整模块台账、行为契约、规则、Workstreams、交接、集成验证、切流与清理记录 |

文档服务于迁移，不机械创建全部模板。

## 19. 结束报告

至少说明：

1. 总体目标与本轮完成的目标能力；
2. 当前 Feature / Feature Items 状态；
3. Source Behavior Coverage 和批准变化；
4. Workstream / Owner / Input Baseline；
5. Workstream Validation / Integration Gate 结果；
6. 已阻塞 / 已延后 / 必须询问；
7. 生效关键用户规则；
8. 下一推荐 Slice / Workstream；
9. `.code-migration/` 是否已同步。
