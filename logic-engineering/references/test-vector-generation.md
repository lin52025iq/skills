# 从 CLM 生成测试向量

测试生成必须直接读取规范逻辑模型（CLM），不得从生成代码反推 expected behavior。

## 1. 目标

```text
CLM
├── Rule          → 条件/边界测试
├── Scenario      → 示例测试
├── StateMachine  → 状态迁移测试
├── Invariant     → 性质测试种子
└── Temporal      → 集成/运行时验证计划
```

Node 命令：

```bash
node scripts/logic_cli.mjs test-vectors model.json -o test-vectors.json
```

## 2. 测试向量

```json
{
  "id": "test.rule.order.cancel.allowed_status.PENDING_PAYMENT",
  "source_semantic_id": "rule.order.cancel.allowed_status",
  "kind": "rule_positive",
  "given": {
    "domain.order.status": "PENDING_PAYMENT"
  },
  "when": null,
  "expect": {
    "rule_result": true
  }
}
```

Typed Scenario 标准化为：

```json
{
  "kind": "scenario",
  "given": {
    "domain.order.status": "PENDING_PAYMENT"
  },
  "when": {
    "behaviors": ["behavior.order.cancel"]
  },
  "expect": {
    "domain.order.status": "CANCELLED"
  }
}
```

## 3. Rule：枚举成员关系

对于 `order.status IN [...]`，集合成员生成 positive/negative case；如果 Domain Enum 可得到全集，同时生成对应反例。

## 4. 比较边界

例如 `amount <= payment_limit`：

```text
amount = limit - δ
amount = limit
amount = limit + δ
```

δ 由 ValueType 决定。无法确定精度时只输出 `boundary_intent`，不伪造数值。

## 5. all / any / not

- all：全部成立为 true，每个子条件分别失败为 false；
- any：任一成立为 true，全部失败为 false；
- not：对子条件结果取反。

不能安全构造领域对象时保留结构化测试意图。

## 6. Scenario

保持 Given → When → Then，不重新解释业务。引用不存在时由 CLM Validator 先阻止测试派生。

## 7. State Transition

每个 Transition 至少一条允许迁移测试；每个 forbidden transition 至少一条拒绝测试。

## 8. Invariant / Temporal

Invariant 先生成 property intent；Temporal 生成 integration/runtime intent，不伪装成普通 unit test。

## 9. Test ID

```text
test.<source-semantic-id>.<case>
```

目标语言变化不改变测试语义 ID。

## 10. 增量测试

逻辑修改后：

```text
Patch / Change Set
→ changed IDs
→ Node Impact Analysis
→ affected test categories
→ regenerate affected vectors
```

影响分析：

```bash
node scripts/analyze_impact.mjs model.json <changed-id...>
```

## 11. 测试与实现独立

```text
            CLM
           /   \
          /     \
     Test Vectors   IIR
         ↓           ↓
   Target Tests   Target Code
```

禁止根据 generated code 的行为反推 expected test。

首个 Target Test 实现为 TypeScript + Vitest；SQLite 只影响测试装配，不改变业务期望。
