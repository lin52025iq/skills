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

所有 operation 必须先在内存副本中执行。任一步失败，不写出部分模型。

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

高级操作应先规划为基础操作，再作为一个 Change Set 原子执行。

## 5. 并发修改保护

两层前置条件：

```text
base_model_version
base_semantic_hash
```

计算哈希：

```bash
node scripts/logic_cli.mjs hash model.json
```

应用：

```bash
node scripts/apply_change_set.mjs model.json change.json \
  -o updated.json \
  --diff-output semantic-diff.json
```

任一前置条件不匹配，拒绝整个 Change Set。

成功 diff 记录：

```text
base_semantic_hash
result_semantic_hash
```

## 6. 变更等级

```text
O1_NORMALIZATION
O2_REFACTORING
O3_ROBUSTNESS
O4_BUSINESS_CHANGE
```

内部任何 operation 改变业务行为时，Change Set 至少是 O4。

## 7. 验证与影响分析

应用后重新执行 CLM Validator、Impact Analysis 和测试派生。

```bash
node scripts/analyze_impact.mjs updated.json <changed-id...> --output impact.json
```

统一流水线：

```bash
node scripts/run_pipeline.mjs model.json --change-set change.json
```

## 8. 人类展示

默认展示业务变化，不先展示低层 JSON operation。

```text
修改：允许已支付订单取消

业务规则变化：
+ 已支付

新增场景：
+ 取消已支付订单
```

需要审计时再展开 operation、semantic hash 和完整 diff。

## 9. 禁止事项

- 不把互相依赖的多个 Patch 当作独立业务提交。
- 不在部分操作失败后保留部分 CLM 修改。
- 不绕过 semantic hash 冲突强制应用旧 Change Set。
- 不在 Change Set 中写目标语言代码。
- 不跳过应用后的校验和影响分析。
