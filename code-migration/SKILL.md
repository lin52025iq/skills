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
9. **只维护必要的权威事实。** 不让多个文档重复维护同一状态。
10. **完成包括验证、集成、切流和清理。**

## 2. 权威文档边界

```text
02 = 范围 / Feature / optional Group / Atomic Item / 实施状态
07 = Source Behavior / Target 业务语义 / 行为验证（WHAT）
08 = 页面结构 + 交互体验（HOW USER EXPERIENCES IT + WHERE）
05 = Workstream + 临时 Batch + Gate
00 = 跨会话摘要
功能语义.md = 可选的复杂业务说明，不维护进度
```

已有 `.code-migration/` 时按上述权威关系恢复；不一致时只重新校准受影响范围。

## 3. 功能发现与来源真实性

中/高风险按需同时做：

```text
正向：入口 → 行为 → 状态/数据 → API → 副作用 → 用户结果
反向：API/Mutation/State/Event → 调用方 → 条件/权限/Flag → 用户场景
```

重点检查：入口、次级操作、Role、状态分支、Feature Flag、API 调用方、轮询/Event、Storage/Cache、错误恢复、URL/Back、测试隐含规则和跨模块副作用。

正式 Feature / Atomic Item 来源：

```text
源系统证据 / 用户明确新增 / 目标产品要求
目标项目强制约束 / 推断候选 / 未知
```

`推断候选 / 未知` 不能静默进入 `范围内 + 必需=是`。

Target 有现成组件只决定“如果需要该能力如何实现”，不能反向决定产品范围。

### Discovery 结束条件

不要求证明绝对无遗漏。主要入口、关键反向调用、关键条件分支、相关测试和来源分类已覆盖，且没有会改变当前实现方向的关键未知，即可进入实施。

## 4. 功能层级

统一使用：

```text
Module
└─ Feature
   ├─ Feature Group / Scenario Group（可选）
   │  ├─ Atomic Item
   │  └─ Atomic Item
   └─ Atomic Item
```

### Feature Group

只在平铺 Atomic Item 明显降低可读性，或多个项属于同一用户场景时使用。**Group 始终可选。**

### Atomic Item

Atomic Item 必须具备：

```text
一个主要产品/工程语义
+ 清晰触发或条件
+ 可观察或可证明的完成结果
+ 可独立判断实施
+ 可独立判断验证
```

如果一个条目中的不同点能独立遗漏、独立失败、独立验证、单独保留/删除，或有不同权限/状态/错误/副作用，就拆分。

不要拆成 DOM、函数、变量、CSS class 或普通实现步骤。

```text
✓ 409 后保留退款输入
✓ 提交期间禁止重复提交
✓ Mobile Drawer 全屏

✗ setLoading(true)
✗ call refundApi()
✗ setState()
```

## 5. 状态与完成派生

Atomic Item 当前状态：

```text
未开始 / 开发中 / 待验证 / 验证中 / 验证失败
已完成 / 已阻塞 / 已延后 / 不适用
```

Feature 生命周期：

```text
已发现 → 已设计 → 实施中 → 验证中 → 已迁移 → 已清理
```

Module 只维护派生摘要，例如：

```text
未开始 / 进行中 / 验证中 / 已完成 / 已阻塞
```

```text
Batch 已完成 ≠ Workstream 已完成 ≠ Feature 已迁移 ≠ Module 已完成
```

Feature 只有在全部范围内必需 Atomic Item 完成、要求的 Discovery/07/08 验证通过、必要集成验证通过后才能 `已迁移`。

Module 只有在全部范围内必需 Feature 达到目标生命周期，且模块共享边界的必要集成验证通过后才能 `已完成`。

## 6. 风险治理预算

### 低风险

```text
Feature + Atomic Item
+ Provenance
+ Target Behavior
+ 最小验证
```

不强制 Group、07、08、输入基线、Workstream 编排或 Batch。

### 中风险

按需要增加：

```text
关键 Discovery
关键 SB
关键 INT / REG
可选 Group
长任务输入基线
```

只为值得独立迁移追踪的内容建立 ID。

### 高风险

按需要启用：完整 Discovery、07、08、C3 运行证据、输入基线、独立验证、并行安全、集成验证、回滚和清理。

## 7. Source Behavior 与交互/结构边界

### 07：WHAT

记录业务必须发生什么，例如：

```text
返回列表后必须保留用户上下文
409 后必须允许用户恢复操作
```

### 08：HOW / WHERE

记录用户具体如何体验，例如：

```text
Back 后 filter/page/scroll/focus 如何恢复
Drawer 是否关闭、输入如何保留、错误定位如何呈现
Desktop/Mobile 区域怎么排列
```

不要在 07 和 08 重复写同一套交互时序。

## 8. 用户新方案

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

## 9. 执行模型

```text
Workstream = 负责人 + 修改边界 + 并行/隔离边界
Batch = 临时一起开发或验证的一组 Atomic Item
```

不维护独立 Slice 状态实体。

简单任务直接实施/验证 Atomic Item；只有多个强关联项确实需要一起处理时才创建临时 DEV/VER Batch。

Batch 完成后必须逐 Atomic Item 回写状态，Batch 自身不是长期事实源。

## 10. Ready Gate

按风险确认：

- Atomic Item 拆分合理；
- 正式项来源真实；
- 要求的 Discovery 足够进入实施；
- 要求的 07/08 目标已明确；
- 用户新方案已进入 Target；
- 验证方式、用户规则、依赖、目标落点满足；
- 并行时 Workstream 边界清晰。

## 11. 实施与验证

```text
选择 Atomic Item(s)
→ 必要时形成临时 DEV Batch
→ 实施
→ 逐项更新实施状态
→ 必要时形成临时 VER Batch
→ 执行真实用户场景
→ 逐项写验证结果
→ 派生 Group
→ 派生 Feature
→ 派生 Module
```

开发中发现新能力：先登记候选 → 证明来源 → 判断范围 → 做原子拆分 → 再实施。禁止“顺手新增”。

## 12. 并行与集成

Workstream 才是并行边界。同一 Atomic Item 同时只能有一个生产代码负责人；共享契约/公共基础必须唯一负责人。

环境不支持子 Agent / worktree / 安全隔离时，不伪造并行，保留 Workstream 模型并串行执行。

共享 Route/Layout、API/Query/State、权限、依赖/lockfile、Design System/全局样式、registry/generated 或同一发布批次时执行必要集成验证。

## 13. 禁止方式

- 不按目录树迁移；
- 不把推断候选当 Source 事实；
- 不因为 Target 有组件就新增产品功能；
- 不把复合大条目当 Atomic Item；
- 不拆到无业务意义的实现步骤；
- 不让 Group/Batch/Workstream 覆盖 Atomic Item 的真实失败；
- 不把局部完成推成 Feature / Module 完成；
- 不让 07 / 08 重复维护同一体验事实；
- 不为低风险任务机械创建完整文档和大量 ID；
- 不把用户批准的新方案修回 Source。

## 14. 结束报告

至少说明：完成能力、Atomic Item / Feature / Module 派生状态、来源真实性、关键 Discovery、用户新方案、07/08 验证、必要集成验证、阻塞/未知和下一安全动作。
