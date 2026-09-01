# 验证与实现生成规范 v0.1

本规范定义从规范逻辑模型（CLM）到目标实现，以及如何验证目标实现仍然符合逻辑模型。

## 1. 目标

实现生成必须满足：

- 不把源语言语法机械翻译到目标语言；
- 先恢复语言无关语义，再选择目标技术实现；
- 代码、测试、文档都从 CLM 派生；
- 对关键业务条件、状态变化、副作用和错误行为进行一致性检查；
- 对无法完全形式化验证的部分明确说明验证覆盖范围。

## 2. 生成链路

```text
规范逻辑模型（CLM）
        ↓
目标配置（Target Profile）
        ↓
基础能力绑定（Primitive Binding）
        ↓
实现中间表示（IIR）
        ↓
目标语言代码
        ↓
测试 + 一致性验证
```

## 3. 目标配置

目标配置描述“在什么技术环境中实现”，至少包含：

```yaml
language: Go
version: "1.x"
framework: Gin
architecture: clean_architecture
persistence: PostgreSQL
messaging: Kafka
transaction_strategy: database_transaction
dependency_injection: constructor
error_model: typed_error
test_framework: testify
```

CLM 不保存这些技术选择。

## 4. 实现中间表示（IIR）

IIR 用于把业务语义映射成具体实现策略，但仍尽量不绑定具体语法。

示例：

```yaml
semantic_source: constraint.account.balance_exclusive_write
strategy: database_pessimistic_lock
scope: same_account
transaction_required: true
```

再由目标生成器输出具体语言代码。

## 5. 基础能力绑定

CLM 可以引用：

```text
primitive.transaction.atomic_group
primitive.messaging.publish_reliably
primitive.concurrency.exclusive_resource_access
```

目标配置需要绑定为实际能力，例如：

```text
transaction.atomic_group
→ PostgreSQL transaction

messaging.publish_reliably
→ transactional outbox
```

如果目标环境没有可靠绑定，生成前必须报告缺口，不能用一个“差不多”的实现静默替代。

## 6. 代码区域分类

推荐区分：

### 完全生成区

适合直接从 CLM 生成：

- 业务规则；
- 状态迁移；
- 流程编排；
- 参数校验；
- 领域错误映射；
- 由规则派生的测试。

### 生成契约区

只生成接口或契约：

- 支付网关；
- 消息系统；
- 外部 API；
- 存储适配器；
- 复杂算法能力。

### 人工实现区

由工程人员实现，但必须满足生成契约：

- 第三方 SDK 适配；
- 加密算法；
- 性能敏感底层能力；
- 特殊系统调用；
- 无法安全自动生成的基础设施。

## 7. 生成代码完整性

逻辑优先接管后，生成代码默认禁止直接维护。

建议生成：

```text
来源语义版本
Semantic ID
生成器版本
目标配置版本
语义哈希
```

例如：

```text
GENERATED FROM: behavior.order.cancel@v12
DO NOT EDIT DIRECTLY
```

CI 可通过语义哈希或重新生成检查发现人工漂移。

## 8. 验证层级

### L0 结构和类型合法

检查：

- CLM schema；
- 引用存在；
- 类型匹配；
- 枚举值有效；
- 必需字段完整。

### L1 模型内部一致

检查：

- 相互矛盾的规则；
- 无效状态迁移；
- 不变量冲突；
- 不可能满足的前置条件；
- 缺失引用。

### L2 实现符合模型

验证目标实现是否保留：

- 条件；
- 状态写入；
- 外部副作用；
- 错误行为；
- 必要执行顺序；
- 原子性、幂等、并发等关键要求。

### L3 行为测试

从 CLM 独立派生：

- 示例测试；
- 边界测试；
- 状态迁移测试；
- 性质测试；
- 集成测试。

### L4 形式化验证

对关键性质按需投影到合适的验证工具。

### L5 业务意图确认

确认“模型本身是不是业务真正想要的行为”。这一级不能只靠自动验证决定。

## 9. 测试必须独立派生

禁止：

```text
生成代码
→ 根据代码生成测试
```

因为错误实现可能生成同样错误的测试。

正确方式：

```text
CLM
├─ 代码生成器 → 实现
└─ 测试生成器 → 测试
```

## 10. 边界测试

对于比较规则自动生成边界：

```text
规则：amount <= limit
```

派生：

```text
amount = limit - 1 → 允许
amount = limit     → 允许
amount = limit + 1 → 拒绝
```

对于集合规则：

```text
status IN [A, B]
```

至少验证：

```text
A → 允许
B → 允许
任一集合外状态 → 拒绝
```

## 11. 状态机测试

从 State Model 派生：

- 每一条允许迁移；
- 每一条显式禁止迁移；
- 关键终态不可继续迁移；
- 重复触发是否幂等；
- 并发迁移冲突。

## 12. 性质测试

不变量适合生成 property-based tests，例如：

```text
订单累计退款金额永远不能超过已支付金额。
```

内部性质：

```text
∀ 合法操作序列：total_refunded <= paid_amount
```

## 13. 形式化后端选择

不是所有逻辑都投影到同一种语言。

```text
函数契约 / 数据约束
→ SMT / Dafny / Why3 类工具

状态迁移
→ 状态模型检查器

并发与时序
→ TLA+ / LTL 类工具

业务示例
→ 单元 / 集成测试

运行时最终一致性
→ Runtime Monitor
```

## 14. 语义往返检查

生成代码后，可以重新执行代码逻辑抽取，得到“可观察实现语义”：

```text
Generated Code
     ↓
Observable Semantic Model
```

再比较：

```text
Expected CLM
vs
Observed Implementation Semantics
```

重点检查：

- 条件运算符是否变化；
- 边界是否变化；
- 写入的状态和值是否变化；
- 是否缺少副作用；
- 副作用顺序是否变化；
- 错误路径是否变化。

例如：

```text
期望：amount <= limit
实现：amount < limit
```

必须报告边界语义不一致。

## 15. 运行时一致性

对于难以静态证明的重要时序规则，可以从 CLM 生成运行时监控。

例如：

```text
付款成功后 5 分钟内必须生成财务流水。
```

可生成：

```text
payment_succeeded(order)
→ 在 5 分钟内最终出现 financial_record_created(order)
```

运行时违例必须能够回链到对应 Semantic ID。

## 16. 生成失败条件

以下情况不能继续生成并假装成功：

- CLM 存在未解决的关键矛盾；
- 目标配置缺少关键基础能力绑定；
- O4 业务修改尚未获得所需确认；
- 目标实现无法满足必要约束；
- 生成后验证发现关键语义不一致。

此时输出：

```text
阻塞原因
受影响语义 ID
当前可行替代方案
需要补充或确认的内容
```
