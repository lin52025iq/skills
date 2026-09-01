---
name: code-migration
description: 用于将一个或多个现有项目中的真实业务能力迁移、融合或重构到目标项目。适用于跨仓库、跨框架、多项目融合、前端页面重建、用户新 UX/布局方案、功能删改融合和渐进切流。迁移以 Source 证据、来源真实性、目标期望行为、交互语义、页面结构和 Target 原生架构为中心；以原子功能项作为最小完成事实源，并按风险控制建模深度、验证强度、跨会话恢复和受控并行。
---

# Code Migration

把迁移视为 **业务能力在新上下文中的受控重建**。

```text
Source Evidence
→ Discovery + Provenance
→ Target Behavior / UX
→ Target-native Design
→ Module / Feature / optional Group / Atomic Item
→ Implement + Verify
→ Derived Feature / Module Completion
→ Integration / Cutover / Cleanup
```

## 1. 核心原则

1. **迁移能力，不迁移文件结构。**
2. **Source 是事实，不是 Target 规范。**
3. **既防漏，也防幻觉。** 正式范围必须有来源依据。
4. **Atomic Item 是最小完成事实源。** Group、Feature、Module 状态只能派生。
5. **拆分粒度与执行粒度分离。** 多个 Atomic Item 可以一起开发/验证，但结果逐项落账。
6. **用户新方案决定目标变化。** 已确认的新功能、交互、布局方案优先于 Source 旧形态。
7. **Target 决定实现形状。** 遵循目标仓库稳定架构、组件和 Design System。
8. **治理按风险自适应。** 风险决定文档数量、ID 密度、Gate 数量和验证粒度。
9. **顶层做索引，全量模块事实只维护一处。** 不让顶层和模块目录重复维护同一 Atomic Item 状态。
10. **Checkbox 只是完成投影。** `[x]` 由真实状态派生，不能作为状态输入。
11. **完成包括验证、集成、切流和清理。**

## 2. 迁移产出文档与编号

标准顶层产物：

```text
00-迁移状态总览.md
01-迁移任务上下文.md
02-迁移约束与开发规则.md
03-迁移模块索引与进度.md
04-功能语义.md
05-源行为与目标对齐清单.md
06-页面结构与交互对齐清单.md
07-功能融合映射.md
08-迁移决策记录.md
09-迁移执行计划.md
```

编号语义：

```text
00       = 跨会话入口 / 恢复索引
01–02    = 任务与执行约束
03       = Module 导航 / 派生进度
04–06    = 全局或跨模块语义、行为、交互与页面结构契约
07–08    = 多源融合与重大目标决策
09       = Workstream / 临时 Batch / Gate
```

不是每次迁移都必须生成全部文件；风险和任务类型决定实际产物。只要标准模板落地到 `.code-migration/` 顶层，就保持标准编号和用途。

## 3. 模块化工作区

### 顶层和模块目录职责

```text
03-迁移模块索引与进度.md
= Module Index + Derived Progress + links

modules/<module>/01-模块功能点.md
= 该 Module 的 Feature / Group / Atomic Item / 实施状态权威源
```

模块化后，顶层 `03` 不复制该模块全部 Atomic Item。

标准模块目录：

```text
modules/<module>/
├── 00-模块总览.md              # 模块入口、Feature Checklist、派生摘要
├── 01-模块功能点.md            # Feature / Atomic Item 权威源
├── 02-功能语义.md              # 复杂模块业务语义按需
├── 03-源行为对齐.md            # 中/高风险 WHAT 按需
└── 04-页面结构与交互.md        # 复杂前端 HOW / WHERE 按需
```

### 何时创建模块目录

以下任一情况成立时优先模块化：

- 模块有多个需要独立追踪的 Feature；
- Atomic Item 平铺在顶层会明显降低可读性；
- 模块需要跨会话持续推进；
- 模块有独立 Workstream / 并行边界；
- 模块需要自己的 `02 / 03 / 04` 契约；
- 模块风险较高，需要独立验证或集成结论。

简单低风险模块可以直接留在顶层 `03`，不为了形式创建目录。

### 全局与模块私有事实

```text
顶层 04 / 05 / 06
= 全局、共享、跨模块语义 / 行为 / App Shell / 共享体验

modules/<module>/02 / 03 / 04
= 该模块私有语义 / 行为 / 页面体验
```

同一事实只维护一处；另一侧通过链接或 ID 引用。

## 4. Checkbox 完成投影

Checkbox 可以用于 Module、Feature、Atomic Item 的快速扫描，但只能由状态派生：

```text
Atomic Item 当前状态 = 已完成       → [x]
Feature 生命周期 = 已迁移 / 已清理  → [x]
Module 派生状态 = 已完成            → [x]
其他状态                            → [ ]
```

未完成项同时显示真实状态，例如：

```text
- [ ] F-REFUND 退款 — 验证中 · 3/4
- [ ] F-REFUND-I03 409 恢复 — 验证失败
```

**禁止手工勾选 Checkbox 代替更新真实状态。**

## 5. 导航与链接

顶层 `03` 链接模块入口：

```text
[M-ORDER 订单中心](modules/order/00-模块总览.md)
```

模块入口提供双向链接：

```text
../../00-迁移状态总览.md
../../03-迁移模块索引与进度.md
01-模块功能点.md
02/03/04（实际存在时）
```

只保留真实存在的可选文档链接。死链接、错链或指向旧文件名的链接属于工作区一致性问题。

## 6. 功能发现与来源真实性

中/高风险按需同时做：

```text
正向：入口 → 行为 → 状态/数据 → API → 副作用 → 用户结果
反向：API/Mutation/State/Event → 调用方 → 条件/权限/Flag → 用户场景
```

重点检查入口、次级操作、Role、状态分支、Feature Flag、API 调用方、轮询/Event、Storage/Cache、错误恢复、URL/Back、测试隐含规则和跨模块副作用。

正式 Feature / Atomic Item 来源：

```text
源系统证据 / 用户明确新增 / 目标产品要求
目标项目强制约束 / 推断候选 / 未知
```

`推断候选 / 未知` 不能静默进入 `范围内 + 必需=是`。Target 有现成组件只决定“如果需要该能力如何实现”，不能反向决定产品范围。

### Discovery 结束条件

不要求证明绝对无遗漏。主要入口、关键反向调用、关键条件分支、相关测试和来源分类已覆盖，且没有会改变当前实现方向的关键未知，即可进入实施。

## 7. 功能层级

统一使用：

```text
Module
└─ Feature
   ├─ Feature Group / Scenario Group（可选）
   │  ├─ Atomic Item
   │  └─ Atomic Item
   └─ Atomic Item
```

Group 只在平铺 Atomic Item 明显降低可读性，或多个项属于同一用户场景时使用。

Atomic Item 必须具备：

```text
一个主要产品/工程语义
+ 清晰触发或条件
+ 可观察或可证明的完成结果
+ 可独立判断实施
+ 可独立判断验证
```

不要拆成 DOM、函数、变量、CSS class 或普通实现步骤。

## 8. 状态与完成派生

Atomic Item 当前状态：

```text
未开始 / 开发中 / 待验证 / 验证中 / 验证失败
已完成 / 已阻塞 / 已延后 / 不适用
```

Feature 生命周期：

```text
已发现 → 已设计 → 实施中 → 验证中 → 已迁移 → 已清理
```

Module 只维护派生摘要：

```text
未开始 / 进行中 / 验证中 / 已完成 / 已阻塞
```

```text
Batch 已完成 ≠ Workstream 已完成 ≠ Feature 已迁移 ≠ Module 已完成
```

Feature 只有在全部范围内必需 Atomic Item 完成、要求的行为/体验验证通过、必要集成验证通过后才能 `已迁移`。Module 只有在全部范围内必需 Feature 达标且模块共享边界集成验证通过后才能 `已完成`。

## 9. 风险治理预算

### 低风险

```text
Feature + Atomic Item + Provenance + Target Behavior + 最小验证
```

不强制模块目录、Group、复杂契约、输入基线、Workstream 编排或 Batch。

### 中风险

按需增加模块目录、关键 Discovery、关键 SB、关键 INT/REG、可选 Group、可选模块语义和长任务输入基线。

### 高风险

按需启用完整模块目录、Source Behavior、前端体验契约、C3 运行证据、输入基线、独立验证、并行安全、集成验证、回滚和清理。

## 10. WHAT / HOW-WHERE 边界

```text
顶层 05 / 模块 03 = WHAT
顶层 06 / 模块 04 = HOW USER EXPERIENCES IT + WHERE
```

不要在行为和体验契约中重复写同一套时序。

## 11. 用户新方案

Target 决策优先级：

```text
用户当前明确方案
→ 目标产品要求
→ 必须保留的 Invariant
→ Target 稳定模式
→ Source C3/C2
→ Source C1
→ 推断
```

C3 证明 Source 真实形态，但不能覆盖已确认的新 Target UX / 布局 / 交互方案。

## 12. 执行模型

```text
Workstream = 负责人 + 修改边界 + 并行/隔离边界
Batch = 临时一起开发或验证的一组 Atomic Item
```

简单任务直接实施/验证 Atomic Item；多个强关联项才创建临时 DEV/VER Batch。Batch 结束后逐 Atomic Item 回写状态。

## 13. Ready Gate

按风险确认：

- Atomic Item 拆分合理；
- 正式项来源真实；
- 要求的 Discovery 足够进入实施；
- 要求的行为 / 页面体验目标已明确；
- 用户新方案已进入 Target；
- `02` 中当前生效规则已检查；
- 验证方式、依赖、目标落点满足；
- 并行时 Workstream 边界清晰；
- 模块化后 `03 ↔ modules/<module>/00` 导航有效。

## 14. 实施与验证

```text
选择 Atomic Item(s)
→ 必要时形成临时 DEV Batch
→ 实施
→ 逐项更新真实状态
→ 必要时形成临时 VER Batch
→ 验证真实用户场景
→ 逐项写验证结果
→ 派生 Feature
→ 派生 Module
→ 同步 Checklist 投影和顶层摘要
```

开发中发现新能力：先登记候选 → 证明来源 → 判断范围 → 原子拆分 → 再实施。禁止“顺手新增”。

## 15. 并行与集成

Workstream 才是并行边界。同一 Atomic Item 同时只能有一个生产代码负责人；共享契约/公共基础必须唯一负责人。

环境不支持子 Agent / worktree / 安全隔离时，不伪造并行，保留 Workstream 模型并串行执行。

共享 Route/Layout、API/Query/State、权限、依赖/lockfile、Design System/全局样式、registry/generated 或同一发布批次时执行必要集成验证。

## 16. 禁止方式

- 不按 Source 目录树机械拆 Module；
- 不把推断候选当 Source 事实；
- 不因为 Target 有组件就新增产品功能；
- 不把复合大条目当 Atomic Item；
- 不拆到无业务意义的实现步骤；
- 不在顶层 `03` 与模块 `01` 双写同一 Atomic Item 状态；
- 不让 Checkbox 成为新的状态输入；
- 不让 Group/Batch/Workstream 覆盖 Atomic Item 的真实失败；
- 不把局部完成推成 Feature / Module 完成；
- 不为低风险任务机械创建完整模块目录；
- 不保留失效的相对链接；
- 不把用户批准的新方案修回 Source。

## 17. 结束报告

至少说明：完成能力、模块导航入口、Atomic Item / Feature / Module 派生状态、来源真实性、关键 Discovery、用户新方案、行为/体验验证、必要集成验证、阻塞/未知和下一安全动作。
