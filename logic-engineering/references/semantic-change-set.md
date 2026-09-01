# 语义变更集（Semantic Change Set）v0.2

语义变更集用于表示一个完整业务修改包含多个 CLM 节点变化的情况。

它解决的问题不是“批量修改方便”，而是保证：

```text
一个业务意图
→ 一组相关语义操作
→ 全部成功或全部失败
→ 统一影响分析
→ 统一验证
```

## 1. 什么时候使用

单个 Semantic Patch 适合：

- 修改一个 Rule 字段；
- 增加一个枚举成员；
- 调整一个节点状态；
- 不会造成其他 CLM 节点必须同步变化的局部修改。

Semantic Change Set 适合：

- 修改规则并增加 Scenario；
- 新增状态并增加 Transition；
- 抽取公共 Rule 并替换多个引用；
- 修改 Behavior 同时更新 Constraint；
- 一个修改只有整体应用才保持 CLM 一致。

## 2. 原子性

应用器必须在内存副本中执行所有操作。

```text
operation 1 ✓
operation 2 ✓
operation 3 ✗

→ 整个 Change Set 失败
→ 不写出部分更新后的 CLM
```

禁止把前三个操作分别写入磁盘后再回滚。

## 3. 基本结构

```json
{
  "change_set_id": "change.order.cancel.allow-paid",
  "intent": "允许已支付订单取消",
  "behavior_change_level": "O4_BUSINESS_CHANGE",
  "base_model_version": "0.2",
  "operations": [],
  "verification_required": []
}
```

详细 Schema：

`schemas/semantic-change-set-v0.2.schema.json`

## 4. 支持操作

v0.2 第一版支持：

```text
ADD_NODE
REMOVE_NODE
UPDATE_FIELD
ADD_MEMBER
REMOVE_MEMBER
ADD_RELATION
REMOVE_RELATION
REPLACE_REFERENCE
```

复杂语义操作如：

```text
EXTRACT_COMMON_RULE
INLINE_RULE
RENAME_SYMBOL
MOVE_NODE
```

后续应先展开成上述基础操作，再原子应用。

## 5. 应用顺序

操作按 `operations` 数组顺序执行。

如果后一个操作依赖前一个新建节点，应把 ADD_NODE 放在引用操作之前。

例如：

```text
1. ADD_NODE rule.order.operation.authorization
2. REPLACE_REFERENCE behavior.order.cancel old_rule → new_rule
3. REPLACE_REFERENCE behavior.order.edit old_rule → new_rule
4. REMOVE_NODE old_rule
```

## 6. 版本前置条件

推荐提供：

```json
"base_model_version": "0.2"
```

版本不一致时拒绝应用，避免把旧变更集误套到已经变化的 CLM。

未来还应增加 semantic hash 前置条件。

## 7. 变更等级

整个 Change Set 必须声明最高变化等级：

```text
O1_NORMALIZATION
O2_REFACTORING
O3_ROBUSTNESS
O4_BUSINESS_CHANGE
```

如果内部任何 operation 会改变业务行为，则整个 Change Set 至少是 O4。

不要通过拆分操作降低变化等级。

## 8. 验证要求

Change Set 必须显式保存验证要求，例如：

```json
[
  "schema",
  "type_check",
  "semantic_consistency",
  "scenario_tests",
  "human_confirmation"
]
```

应用完成后仍必须重新运行 CLM Validator。

## 9. 影响分析

Change Set 应汇总所有变化 Semantic ID，然后统一运行：

```bash
python scripts/analyze_impact.py updated.json <changed-id...>
```

不要只分析第一个 operation。

## 10. 人类展示

给用户展示时不要逐条暴露 JSON 操作。

优先展示：

```text
修改：允许已支付订单取消

业务规则变化：
+ 已支付

新增场景：
+ 取消已支付订单

影响：
- 取消订单行为
- 相关测试
- 目标实现

验证要求：
- 业务确认
- 场景测试
```

需要审计时再展开底层 operation。

## 11. 禁止事项

- 不把多个互相依赖的 Patch 当作独立提交静默执行。
- 不在部分操作失败后保留部分 CLM 修改。
- 不在 Change Set 中直接写目标语言代码。
- 不把 `behavior_change_level` 当装饰字段。
- 不跳过应用后的 CLM 校验和影响分析。
