# 旧代码导入工作区协议

本协议定义 Agent 在大型真实项目中执行“代码 → 候选逻辑模型”时如何持续记录探索状态，避免跨文件、跨模块、跨会话时丢失上下文。

## 1. 工作区目标

旧代码导入不是一次性摘要，而是一个持续收敛过程：

```text
目标问题 / 模块
→ 入口定位
→ 代码探索
→ 逻辑事实
→ 证据绑定
→ 候选语义节点
→ 候选 CLM
→ 人类可读逻辑
```

工作区必须回答：

- 当前正在理解什么；
- 已经确认了什么；
- 哪些结论只是推断；
- 哪些问题还没有关闭；
- 下一步应该读取哪里；
- 哪些源代码支撑哪些逻辑节点。

## 2. 推荐目录

在目标项目内按需创建：

```text
.logic-engineering/
├── 00-导入状态.md
├── 01-分析目标.md
├── 02-探索队列.md
├── 03-逻辑事实.md
├── 04-开放问题.md
├── 05-证据索引.md
├── 06-候选逻辑模型.json
├── 07-人类可读逻辑.md
└── modules/
    └── <module>/
        ├── 00-模块状态.md
        ├── 01-入口与边界.md
        ├── 02-节点摘要.md
        ├── 03-局部逻辑图.md
        └── 04-未决问题.md
```

简单任务不必生成全部文件；复杂任务才持久化完整工作区。

## 3. 00-导入状态

用于跨会话恢复，至少记录：

```text
目标模块
当前阶段
主要入口
已完成节点数
待探索节点数
关键开放问题
关键未知
候选 CLM 状态
最后一次更新时间
```

## 4. 分析目标

示例：

```yaml
target:
  module: order
  question: 订单取消功能完整逻辑是什么
  expected:
    - 入口
    - 前置条件
    - 状态变化
    - 库存影响
    - 退款影响
    - 失败路径
    - 事务和事件顺序
  exclusions:
    - 页面样式
    - 日志格式
```

目标要尽量限制“最小充分子图”，禁止默认尝试理解整个仓库。

## 5. 探索队列

每个 frontier item 至少包含：

```yaml
- symbol: InventoryService.release
  location: src/inventory/service.go
  priority: critical
  reason: 决定取消订单后库存实际如何变化
  resolves:
    - q.inventory_release_semantics
  discovered_from:
    - OrderCancelService.cancel
  status: pending
```

状态：

```text
pending
reading
completed
skipped
blocked
```

## 6. 优先级规则

优先级由以下因素综合决定：

```text
问题相关性
业务重要性
降低未知的价值
结构位置
副作用重要性
探索成本
```

优先追：

- 状态修改；
- 业务判断；
- 权限和校验；
- 事务边界；
- 外部副作用；
- Event / Queue / Callback；
- 动态实现选择；
- 错误与补偿路径。

默认低优先级：

- logging；
- trivial DTO mapping；
- getter/setter；
- 无语义 wrapper；
- 普通框架内部实现。

## 7. 逻辑事实

读取代码后先记录事实，不直接写最终故事。

```yaml
fact_id: fact.order.cancel.status_check
classification: observed
statement: 订单状态只有 PENDING_PAYMENT 和 PAID 时继续取消流程
source:
  path: src/order/CancelService.java
  symbol: cancel
  lines: 88-94
supports_candidate:
  - rule.order.cancel.allowed_status
```

事实与 Semantic Node 分离，允许多个事实共同支撑一个节点。

## 8. 节点摘要

完成一个重要节点后，压缩为：

```yaml
symbol: InventoryService.release
role: 释放订单已预留库存
inputs:
  - order_items
conditions:
  - 只处理 inventory_reserved = true 的商品
state_reads:
  - inventory.reserved
state_writes:
  - inventory.reserved
side_effects:
  - 数据库写入
failures:
  - inventory release error
calls:
  - InventoryRepository.release
confidence: high
evidence_refs:
  - evidence.inventory.release.1
```

后续优先使用节点摘要，只有出现冲突或需要进一步证明时重新加载源码。

## 9. 开放问题

开放问题是探索驱动力。

```yaml
- id: q.order.cancel.transaction
  question: 订单状态修改与取消原因是否处于同一事务
  importance: critical
  status: unresolved
  candidates:
    - OrderCancelService.cancel
    - transaction configuration
```

状态：

```text
unresolved
partially_resolved
resolved
blocked
```

每次继续探索前优先说明当前读取要关闭哪个问题。

## 10. 动态调用

无法静态解析时不得强行选择实现。

```yaml
dynamic_edge:
  caller: PaymentService.refund
  abstraction: PaymentGateway
  candidates:
    - StripeGateway
    - PaypalGateway
  resolver:
    kind: dependency_injection
    location: payment/config
  status: unresolved
```

继续寻找 factory、DI、registry、feature flag、配置或运行时条件。

## 11. 证据索引

证据应可反查 Semantic Node：

```text
evidence.order.cancel.allowed_status.1
→ rule.order.cancel.allowed_status
→ src/order/CancelService.java:88-94
```

最终 Human Projection 中的重要结论也应可回到 Evidence。

## 12. 候选 CLM 更新策略

不要等全部代码看完后才构造模型。

循环：

```text
读取
→ 提取事实
→ 更新候选节点
→ 更新关系
→ 更新开放问题
→ 排序 frontier
→ 下一轮
```

Candidate CLM 应增量收敛。

## 13. 冲突处理

如果出现：

```text
Fact A: PAID 可以取消
Fact B: State machine 声明 PAID 不允许取消
```

不要覆盖任意一方。

记录：

```yaml
contradiction:
  id: conflict.order.cancel.paid
  facts:
    - fact.a
    - fact.b
  impact:
    - rule.order.cancel.allowed_status
  status: unresolved
```

最终作为潜在逻辑问题或模型不确定性输出。

## 14. 停止条件

主要探索可以停止，当：

- 所有 critical open question 已关闭或明确 blocked；
- 主流程已经形成闭环；
- 关键状态变化已明确；
- 关键副作用已明确；
- 关键失败路径已明确；
- 没有一个未解析依赖可能明显改变当前解释。

达到预算但未满足条件时必须明确：

```text
已知
未知
可能影响
下一步建议探索
```

## 15. 生成候选人类逻辑

只有 Candidate CLM 已形成后再生成自然语言。

优先顺序：

```text
功能目的
前置条件
主流程
判断分支
状态变化
外部影响
失败路径
事务/并发/幂等
完成条件
未知与潜在问题
```

禁止直接按文件阅读顺序输出。

## 16. 从 Candidate 到 Canonical

Legacy import 默认结束于 Candidate。

升级需要：

```text
证据充分
+ 结构/语义校验通过
+ 没有关键冲突
+ 人确认或存在明确权威规格
```

旧代码“现在这样做”不能自动等价为“业务应该这样做”。