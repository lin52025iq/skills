# 从 CLM 生成测试向量

测试生成必须直接读取规范逻辑模型（CLM），不得从生成代码反推 expected behavior。

## 1. 目标

把 CLM 中可以执行验证的语义转成与目标编程语言无关的测试向量：

```text
CLM
├── Rule          → 条件/边界测试
├── Scenario      → 示例测试
├── StateMachine  → 状态迁移测试
├── Invariant     → 性质测试种子
└── Temporal      → 集成/运行时验证计划
```

第一版脚本重点支持前三类，并为 invariant / temporal 产生待扩展的 test intent。

## 2. 测试向量结构

建议：

```json
{
  "id": "test.rule.order.cancel.allowed_status.allowed.1",
  "source_semantic_id": "rule.order.cancel.allowed_status",
  "kind": "rule_positive",
  "given": {
    "order.status": "PENDING_PAYMENT"
  },
  "when": null,
  "expect": {
    "rule_result": true
  }
}
```

Scenario：

```json
{
  "id": "test.scenario.order.cancel.pending_payment",
  "source_semantic_id": "scenario.order.cancel.pending_payment",
  "kind": "scenario",
  "given": ["order.status = PENDING_PAYMENT"],
  "when": ["behavior.order.cancel"],
  "expect": ["order.status = CANCELLED"]
}
```

## 3. Rule：枚举成员关系

对于：

```text
order.status IN [PENDING_PAYMENT, PENDING_SHIPMENT]
```

至少生成：

```text
PENDING_PAYMENT  → true
PENDING_SHIPMENT → true
```

如果能够从 Domain Enum 找到全集，还应为不在集合内的值生成 negative case：

```text
PAID      → false
SHIPPED   → false
CANCELLED → false
```

## 4. Rule：比较边界

例如：

```text
amount <= payment_limit
```

理想测试：

```text
amount = limit - δ → true
amount = limit     → true
amount = limit + δ → false
```

其中 δ 取决于类型：

```text
integer → 1
Money   → 最小货币单位
float   → 不应自行猜测，除非 ValueType 定义精度
```

第一版如果无法确定 δ，应输出 `boundary_intent` 而不是伪造具体值。

## 5. Rule：all / any / not

### all

至少生成：

- 全部成立 → true；
- 每个子条件分别单独失败 → false。

### any

至少生成：

- 每个子条件分别单独成立 → true；
- 全部失败 → false。

### not

子条件 true / false 各生成一个反向结果。

如果不能安全构造具体输入，保留结构化 `condition_assignment`。

## 6. Scenario

Scenario 本身就是 executable example。

生成时保持：

```text
Given
When
Then
```

顺序，不重新解释业务。

如果 Scenario 引用不存在的 Behavior，CLM Validator 应先阻止测试生成。

## 7. State Transition

每个显式 Transition 至少生成一条允许迁移测试：

```text
from state
+ trigger
→ to state
```

每个 `forbidden_transition` 至少生成一条拒绝测试。

如果同一状态 + trigger 存在多个目标状态，应由 Validator 报冲突，不生成自相矛盾的测试。

## 8. Invariant

第一版可以先生成：

```json
{
  "kind": "property_intent",
  "property": "order.total_refunded <= order.paid_amount"
}
```

后续由目标语言 property-test generator 决定 QuickCheck/Hypothesis 等具体实现。

## 9. Temporal Constraint

例如：

```text
payment.succeeded
→ 5m 内 financial_record.created
```

输出 integration intent：

```text
trigger: payment.succeeded
expect_eventually: financial_record.created
time_bound: 5m
```

不在普通 unit test 中假装已经验证时序正确性。

## 10. Test ID

测试 ID 必须稳定，并可回溯到 Semantic ID：

```text
test.<source-semantic-id>.<case>
```

Semantic Node 没改变时，不应仅因目标语言变化而重新定义测试含义。

## 11. 修改后的测试增量生成

结合 `analyze_impact.py`：

```text
Semantic Patch
→ changed IDs
→ impact analysis
→ affected test categories
→ regenerate only affected vectors
```

例如允许状态新增一个 enum member：

```text
原有正例保留
+ 新增一个正例
- 对应旧 negative case 删除/变更
```

这比全量重新生成测试更容易做 semantic diff。

## 12. 测试和实现独立

最终结构必须保持：

```text
            CLM
           /   \
          /     \
     Test Vectors   IIR
         ↓           ↓
   Target Tests   Target Code
```

禁止：

```text
Generated Code
      ↓
根据代码行为生成 expected test
```

否则生成错误可能同时污染实现与测试。
