# 语义变更集（Semantic Change Set）v0.2

语义变更集表示一个完整业务修改包含多个 CLM 节点变化的情况。

它保证：

```text
一个业务意图
→ 一组相关语义操作
→ 全部成功或全部失败
→ 统一影响分析
→ 统一验证
```

## 1. 什么时候使用

单个 Semantic Patch 适合真正独立的单节点修改。

Semantic Change Set 适合：

- 修改 Rule 并增加 Scenario；
- 新增状态并增加 Transition；
- 抽取公共 Rule 并替换多个引用；
- 修改 Behavior 同时更新 Constraint；
- 任意只有整体应用才保持 CLM 一致的业务修改。

## 2. 原子性

所有 operation 必须先在内存副本中执行。

```text
operation 1 ✓
operation 2 ✓
operation 3 ✗

→ 整个 Change Set 失败
→ 不写出部分更新后的 CLM
```

## 3. 基本结构

```json
{
  "change_set_id": "change.order.cancel.allow-paid",
  "intent": "允许已支付订单取消",
  "behavior_change_level": "O4_BUSINESS_CHANGE",
  "base_model_version": "0.2",
  "base_semantic_hash": "<64位 sha256>",
  "operations": [],
  "verification_required": []
}
```

Schema：`schemas/semantic-change-set-v0.2.schema.json`

## 4. 基础操作

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

高级操作如 `EXTRACT_COMMON_RULE / INLINE_RULE / RENAME_SYMBOL / MOVE_NODE` 应先规划为基础操作，再作为一个 Change Set 原子执行。

## 5. 应用顺序

操作按 `operations` 顺序执行。依赖新节点的引用更新必须晚于 `ADD_NODE`。

## 6. 并发修改保护

Change Set 支持两层前置条件：

```text
base_model_version
base_semantic_hash
```

`base_model_version` 防止跨模型版本误应用。

`base_semantic_hash` 防止同一个 v0.2 模型已经被其他修改改变后，旧 Change Set 仍继续应用。

哈希通过：

```bash
python scripts/semantic_hash.py model.json
```

计算。

当前 semantic hash 默认排除证据、置信度和 notes 等不会改变执行语义的元数据。

任一前置条件不匹配，必须拒绝整个 Change Set。

应用成功后的 diff 同时记录：

```text
base_semantic_hash
result_semantic_hash
```

从而形成明确的语义版本链。

## 7. 变更等级

整个 Change Set 声明内部最高变化等级：

```text
O1_NORMALIZATION
O2_REFACTORING
O3_ROBUSTNESS
O4_BUSINESS_CHANGE
```

内部任何 operation 改变业务行为时，Change Set 至少是 O4。

## 8. 验证要求

必须显式保存本次变化需要的验证，例如：

```json
[
  "schema",
  "type_check",
  "semantic_consistency",
  "scenario_tests",
  "human_confirmation"
]
```

Change Set 应用完成后必须重新执行 Validator、影响分析及相应测试生成。

## 9. 影响分析

汇总全部 `changed_semantic_ids` 后统一传播，不允许只分析第一项修改。

统一流水线：

```bash
python scripts/run_logic_pipeline.py model.json \
  --change-set change.json
```

会自动完成应用、重新校验、影响分析、中文投影和测试向量生成。

## 10. 人类展示

默认展示业务变化，不展示低层 JSON operation：

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
```

需要审计时才展开 operation、semantic hash 和完整 diff。

## 11. 与 CLM v0.2 冻结的关系

Change Set 属于 CLM v0.2 的核心写入协议。

冻结 Gate 见：

`references/clm-v0.2-freeze-checklist.md`

只要后续存在破坏 Change Set 原子性、哈希保护或 Semantic ID 稳定性的改动，就必须视为 CLM 协议破坏性变化。

## 12. 禁止事项

- 不把互相依赖的多个 Patch 当作独立业务提交。
- 不在部分操作失败后保留部分 CLM 修改。
- 不绕过 semantic hash 冲突继续强制应用旧 Change Set。
- 不在 Change Set 中写目标语言代码。
- 不跳过应用后的 CLM 校验和影响分析。
