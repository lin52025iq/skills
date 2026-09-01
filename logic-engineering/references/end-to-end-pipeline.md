# 端到端逻辑编译闭环

本文件定义从规范逻辑模型（CLM）到局部逻辑修改、中文逻辑投影、实现中间表示（IIR）的最小可执行闭环。

## 1. 目标

验证以下路径可以在不直接修改目标语言代码的情况下工作：

```text
CLM
 ↓
语义补丁
 ↓
更新后的 CLM
 ↓
中文逻辑投影
 ↓
目标配置
 ↓
IIR
 ↓
后续代码生成器
```

这个闭环的核心不是“生成一段看起来合理的代码”，而是确保：

1. 人修改的是稳定语义节点；
2. 修改能形成可审计的语义差异；
3. 中文逻辑视图随模型自动变化；
4. 技术实现决策只在目标配置和 IIR 层出现；
5. 后续生成器不得跳过未解析语义。

## 2. 当前脚本

### 2.1 校验 CLM

```bash
python scripts/validate_clm.py evals/fixtures/order-cancel.valid.json
```

### 2.2 应用语义补丁

```bash
python scripts/apply_semantic_patch.py \
  evals/fixtures/order-cancel.valid.json \
  evals/fixtures/order-cancel.add-pending-acceptance.patch.json \
  -o /tmp/order-cancel.updated.json \
  --diff-output /tmp/order-cancel.diff.json
```

预期语义差异：

```text
rule.order.cancel.allowed_status

允许状态新增：
+ PENDING_ACCEPTANCE（待接单）
```

修改前后 Semantic ID 不变。

### 2.3 再次校验

```bash
python scripts/validate_clm.py /tmp/order-cancel.updated.json
```

业务规则变化不能绕过结构和语义校验。

### 2.4 中文逻辑投影

```bash
python scripts/render_human_logic.py \
  /tmp/order-cancel.updated.json \
  -o /tmp/order-cancel.logic.md
```

中文逻辑中对应规则应自动变成：

```text
订单状态属于以下范围：
- 待支付
- 已支付
- 待接单
```

用户不需要打开 Go、Java、Rust 等实现文件才能确认这次业务变化。

### 2.5 编译 IIR

```bash
python scripts/compile_iir.py \
  /tmp/order-cancel.updated.json \
  evals/fixtures/go-postgres.target-profile.json \
  -o /tmp/order-cancel.go-postgres.iir.json
```

IIR 必须保留：

- 原始 Semantic ID；
- guard 条件；
- action 顺序；
- effect；
- constraint；
- state transition；
- primitive binding；
- unresolved 列表。

## 3. 语义修改规则

所有业务修改遵循：

```text
自然语言请求
    ↓
定位 Semantic ID
    ↓
生成 Semantic Patch Proposal
    ↓
人工确认（O4 默认需要）
    ↓
应用 Patch
    ↓
重新校验 CLM
    ↓
重新投影 / 编译 / 验证
```

禁止直接根据一句自由自然语言覆盖整个 Behavior。

例如用户说：

```text
待接单订单以后也允许取消。
```

正确结果是：

```text
Target:
rule.order.cancel.allowed_status

Operation:
ADD_MEMBER

Value:
PENDING_ACCEPTANCE
```

而不是重新生成一份新的“取消订单”逻辑描述并覆盖旧模型。

## 4. IIR 的边界

IIR 不应该重新引入源语言耦合。

错误：

```text
use @Transactional
use synchronized
use SpringApplicationEventPublisher
```

正确：

```text
atomicity requirement
exclusive write requirement
reliable event publication requirement
```

再通过 Target Profile 决定：

```text
Java Spring → @Transactional / Outbox
Go Postgres → sql.Tx / Outbox
Rust SQLx → Transaction / Outbox
```

## 5. 未解析项策略

编译器发现以下情况时必须进入 `unresolved`：

- Behavior 引用了不存在的 Rule / Action；
- Primitive 没有当前 target 的 binding；
- 动态调用没有确定实现；
- 目标技术栈无法满足某个 constraint。

后续代码生成器看到 `unresolved` 非空时，默认不得宣称实现已经完整匹配 CLM。

## 6. 回归目标

当前最小闭环至少要持续保证：

1. 合法 CLM 能通过 validator；
2. 非法 CLM 被稳定拒绝；
3. Semantic Patch 只影响目标节点；
4. Patch 前置值不匹配时拒绝应用；
5. Human Projection 不产生模型外规则；
6. 同一 CLM 在不同 Target Profile 下保持业务 guard 和状态语义一致；
7. Target-specific 决策只出现在 IIR / generated code；
8. Generated tests 的 expected behavior 仍从 CLM 派生。

## 7. 下一阶段

在该闭环稳定后，再增加：

```text
IIR → Go generator
IIR → Java generator
CLM → test-vector generator
Semantic Patch impact analyzer
CLM semantic diff engine
Round-trip observable behavior extractor
```

优先确保同一 CLM 的多个实现后端拥有一致的行为测试，而不是过早追求生成大量框架样板代码。
