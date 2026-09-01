# Semantic Patch Protocol v0.1

Semantic Patch 是 logic-engineering 中唯一的 canonical 修改协议。无论修改来自用户、Agent 优化、legacy 修复还是目标迁移，都先转成 Patch，再由系统评估、应用和验证。

## 1. 基本结构

```yaml
patch_id: patch-2026-09-01-001
intent: 待接单订单也允许取消
target_semantic_id: rule.order.cancel.allowed_status
operation: ADD_MEMBER
before:
  - PENDING_PAYMENT
  - PAID
after:
  - PENDING_PAYMENT
  - PAID
  - PENDING_ACCEPTANCE
reason: 用户明确修改业务规则
behavior_change_level: O4
affected_semantic_nodes: []
verification_required:
  - semantic_consistency
  - state_transition_tests
  - scenario_tests
status: proposed
```

## 2. 标准操作

```text
ADD_NODE
REMOVE_NODE
UPDATE_FIELD
ADD_MEMBER
REMOVE_MEMBER
ADD_RELATION
REMOVE_RELATION
EXTRACT_COMMON_RULE
REPLACE_REFERENCE
ADD_CONSTRAINT
UPDATE_CONSTRAINT
```

复杂修改可以由多个原子 Patch 组成一个 Patch Set。

## 3. Patch 生命周期

```text
proposed
→ analyzed
→ approved / rejected
→ applied
→ verified / verification_failed
```

如果变更会修改业务行为，默认不能从 `proposed` 直接进入 `applied`。

## 4. Impact Analysis

应用前沿 Canonical Logic Graph 做正向与反向依赖分析：

```text
changed node
→ dependent rules / behaviors
→ state models / constraints
→ scenarios / tests
→ implementation bindings
```

Patch 必须记录最小影响集；如果无法确定完整影响，标记 `impact_incomplete: true`。

## 5. Semantic Diff

面向人展示业务变化，而不是代码 diff。

例如：

```text
订单取消规则发生变化

允许取消的状态：
新增：待接单
保留：待支付、已支付

可能影响：
- 取消订单流程
- 订单状态机
- 取消订单场景与测试
```

## 6. Optimization Proposal

Agent 优化不得直接写入 CLM，应先产生 Patch Proposal，并标记类型：

```text
O1 lossless_normalization
O2 behavior_preserving_refactor
O3 robustness_improvement
O4 business_behavior_change
```

O2 需要 semantic equivalence；O3 需要技术行为验证；O4 默认需要人工确认。

## 7. Conflict Handling

若两个 Patch 修改同一 Semantic Node：

- 能在结构层合并时执行 semantic merge；
- 操作互斥时产生 semantic conflict；
- 禁止退化成纯文本最后写入覆盖。

示例：

```text
Patch A: ADD PENDING_ACCEPTANCE
Patch B: REMOVE PAID
```

可以合并为同一集合修改。

## 8. Free Natural Language → Patch

自由自然语言只生成 proposal。必须输出：

```text
理解到的修改目标
修改前语义
建议修改后语义
影响范围
是否改变业务行为
待确认歧义
```

存在多个合理解释时，不直接应用。
