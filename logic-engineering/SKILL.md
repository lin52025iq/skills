---
name: logic-engineering
description: 将现有项目中的模块级业务实现重建为与编程语言无关、可由人直接理解和修改的规范逻辑模型（Canonical Logic Model，CLM），并在逻辑层完成归一化、公共逻辑提取、状态与规则分析、语义补丁修改、目标技术栈实现生成和一致性验证。适用于逻辑优先开发、旧代码逻辑导入、模块级自然语言解释、逻辑优化和跨语言重实现。
---

# 逻辑工程

把软件开发视为 **逻辑模型的维护、验证与实现投影**，而不是直接维护某一种编程语言的源代码。

```text
现有代码 / 人类需求
        ↓
   候选逻辑模型
        ↓ 确认
规范逻辑模型（CLM）
   ┌────┼────────┐
   ↓    ↓        ↓
人类视图  验证     实现投影
   ↓    ↓        ↓
自然语言 形式检查   目标代码 + 测试
```

## 1. 核心原则

1. **逻辑是事实源。** 业务逻辑的权威源是规范逻辑模型（CLM），不是散文式自然语言，也不是生成代码。
2. **自然语言是人类投影。** 用户看到的是 CLM 的人类可读视图；自由自然语言不能静默成为规范状态。
3. **自由文本只产生提案。** 用户以自由文本提出修改时，先生成语义补丁提案（Semantic Patch Proposal），再决定是否应用。
4. **生成代码是输出。** 完成逻辑优先接管后，业务修改回到 CLM；生成代码默认不作为人工修改入口。
5. **每条语义都有稳定标识。** 规则、行为、状态、约束、场景等必须有与语言和文件路径无关的语义 ID。
6. **证据优先。** 旧代码导入必须区分“已观察 / 推断 / 假设 / 未知”，并绑定源代码证据。
7. **模型提出，确定性机制裁决。** 大模型负责理解、提炼、建议和候选生成；结构校验、类型检查、约束检查、测试和验证器负责判定是否可接受。
8. **业务语义与基础设施分离。** CLM 描述事务、幂等、顺序、互斥、一致性等要求；具体框架和 API 进入实现中间表示（IIR）和目标配置。
9. **测试从逻辑派生。** 测试从 CLM 独立生成，不从生成代码反推预期行为。
10. **忠实解释与逻辑优化分离。** 已观察逻辑与期望逻辑必须分开；优化默认先以提案表达，禁止在解释阶段偷偷改变业务行为。

## 2. 工作模式

根据用户目标选择一个或多个模式：

```text
导入（import）       现有代码 → 候选 CLM
解释（explain）      现有代码 / CLM → 人类可读逻辑
归一化（normalize）  忠实逻辑 → 不改变行为的规范化 CLM
优化（optimize）     CLM → 优化提案 / 语义补丁
编辑（edit）         人类修改 → 语义补丁 → CLM
迁移（migrate）      CLM → 目标配置 → 目标实现
验证（verify）       CLM ↔ 实现 / 测试 / 形式检查
```

`import` 是已有项目进入逻辑优先工作流的入口；`edit / optimize / migrate` 应以已经确认的 CLM 为事实源。

## 3. 规范逻辑模型（CLM）

CLM 是带类型的语义图。第一版至少支持七类节点：

```text
领域       实体 / 值类型 / 枚举 / 关系
行为       目的 / 输入 / 流程 / 判断 / 输出 / 失败
状态       状态 / 状态迁移 / 禁止迁移
影响       读取 / 写入 / 外部调用 / 发布事件 / 持久化
约束       前置条件 / 后置条件 / 不变量 / 时序 / 并发
场景       前置场景 / 操作 / 结果 / 边界示例
基础能力   与语言无关的技术能力契约
```

常用关系的机器标识可以保留英文：

```text
REQUIRES       INVOKES        READS          WRITES
TRANSITIONS    EMITS          HANDLES        GUARANTEES
CONSTRAINED_BY USES_PRIMITIVE DERIVED_FROM  EVIDENCED_BY
```

详细结构见 `references/canonical-logic-model.md` 与 `references/clm-schema-v0.1.md`。

## 4. 语义 ID

语义 ID 必须与具体实现名称解耦。例如：

```text
domain.order
domain.order.status
behavior.order.cancel
rule.order.cancel.allowed_status
state.order.PAID
transition.order.pending_to_paid
invariant.order.refund_not_exceed_payment
scenario.order.cancel.pending_payment
primitive.transaction.atomic_group
```

不要把 Java 类名、Go 文件路径或 Rust module path 当作 canonical ID；实现位置通过 trace mapping 关联。

## 5. 旧代码 → 候选 CLM

对模块进行逆向理解时，不以当前文件为边界。

```text
目标问题 / 模块
      ↓
定位入口
      ↓
骨架发现
      ↓
按优先级扩展
      ↓
逻辑事实 + 证据
      ↓
候选逻辑图
      ↓
候选 CLM + 人类视图
```

### 5.1 应继续追踪

当下列依赖会实质改变目标功能解释时继续定位：

- 业务 / 领域服务
- 校验与权限
- 状态迁移
- 特殊持久化 / 事务语义
- 事件 / handler / 队列
- 重试 / 回退 / 幂等
- 外部服务适配
- 运行时或配置驱动分派

通常不深入日志、普通 getter/setter、无业务影响的 DTO 映射、普通 wrapper 和框架内部常规实现。

优先采用 **先宽度发现骨架，再按价值深入关键节点**，避免从首个调用一路深挖到底。

### 5.2 开放问题驱动

探索必须维护：

```text
completed_nodes
frontier
open_questions
hypotheses
contradictions
unresolved_dynamic_edges
```

继续读取代码前先回答：“当前要关闭哪个开放问题？”

### 5.3 证据分类

```text
已观察（OBSERVED）  源代码直接证明
推断（INFERRED）    多个已观察事实合成
假设（ASSUMED）     依赖未验证的框架 / 运行时语义
未知（UNKNOWN）     当前证据不足
```

“假设 / 未知”不得静默升级成规范规则。

旧代码导入默认先建立 **已观察行为模型**；人或已有明确规范确认后，才建立期望逻辑 / 规范 CLM。

详见 `references/legacy-import.md` 与 `references/legacy-workspace.md`。

## 6. 人类可读逻辑

同一个 CLM 至少提供三层中文投影：

```text
业务视图        业务效果与核心规则
逻辑视图        条件、步骤、分支、状态变化、失败情况
技术逻辑视图    事务、并发、幂等、重试、事件顺序、一致性
```

例如：

```text
功能：取消订单
标识：behavior.order.cancel

前置条件：
- 当前用户拥有目标订单。
- 订单状态必须是“待支付”或“待发货”。

处理过程：
1. 将订单状态变更为“已取消”。
2. 保存取消原因。
3. 如果存在库存预留，则释放库存。
4. 如果存在成功支付，则发起退款。

原子性：
- 订单状态修改和取消原因保存必须全部成功或全部失败。

保证：
- 已取消订单不能再进入发货流程。
```

人类视图只能重排和解释 CLM，不能引入 CLM 中不存在的新业务规则。

详见 `references/human-projection.md`。

## 7. 结构化编辑与自由文本修改

生产级修改以结构化语义节点为中心。

用户看到：

```text
订单状态必须属于：
- 待支付
- 待发货
```

底层实际对应：

```text
rule.order.cancel.allowed_status
operator = IN
values = [PENDING_PAYMENT, PENDING_SHIPMENT]
```

如果用户自由输入：

```text
待接单订单以后也允许取消。
```

先生成语义补丁提案：

```text
Target: rule.order.cancel.allowed_status
Operation: ADD_MEMBER
Value: PENDING_ACCEPTANCE
```

## 8. 语义补丁

用户修改、Agent 优化、旧逻辑修复最终统一表示为语义补丁。

至少包含：

```text
patch_id
intent
target_semantic_id
operation
before
after
reason
behavior_change_level
affected_semantic_nodes
verification_required
```

支持：

```text
ADD_NODE / REMOVE_NODE / UPDATE_FIELD
ADD_MEMBER / REMOVE_MEMBER
ADD_RELATION / REMOVE_RELATION
EXTRACT_COMMON_RULE / REPLACE_REFERENCE
ADD_CONSTRAINT / UPDATE_CONSTRAINT
```

第一版可执行脚本：

```text
scripts/apply_semantic_patch.py
```

详见 `references/semantic-patch.md`。

## 9. 逻辑优化

优化作用于 CLM，不直接改生成代码。

### O1 无损归一化

不改变行为：

- 判断按语义分组
- 分支 / guard 归一化
- 决策表重建
- 状态机重建
- 命名与概念统一

### O2 行为保持重构

预期业务行为不变：

- 公共验证提取
- 公共规则 / 流程提取
- 重复逻辑消除
- 条件结构简化

必须做语义等价验证。

### O3 稳健性优化

通常不改变业务意图，但改变技术可靠性：

- 事务边界
- 重试
- 幂等
- 并发保护
- 可靠事件发布

必须明确列出实现语义变化。

### O4 业务行为修改

真正改变业务规则：

- 新增 / 删除允许状态
- 修改权限
- 修改价格、退款等业务规则
- 补充缺失业务分支

默认需要明确确认。

### 9.1 潜在问题识别

重点检查：

```text
缺失分支
分支重叠
不可达分支
规则冲突
非法状态迁移
不变量违反
副作用顺序风险
事务缺口
非幂等重试路径
并发竞争候选
重复逻辑不一致
```

没有明确业务证据时必须使用“潜在问题”，不要把个人设计偏好描述成确定 bug。

## 10. 公共逻辑提取

公共逻辑不能只根据文本相似度判断。至少比较：

```text
语义是否等价
领域含义是否相同
前置 / 后置条件是否相同
影响是否相同
是否具有共同变化耦合
```

确认后创建公共语义节点，让各行为通过引用复用，而不是复制自然语言文本。

## 11. 目标实现

生成链路：

```text
CLM
 ↓
目标配置（Target Profile）
 ↓
基础能力绑定（Primitive Binding）
 ↓
实现中间表示（IIR）
 ↓
目标代码生成器
```

目标配置至少描述：

```text
language / version
framework
architecture
persistence
messaging
dependency injection
transaction strategy
error model
test framework
```

不要把源语言技术语法机械翻译。例如 `synchronized` 应先恢复为“同一资源修改必须互斥”的语义要求，再由目标配置选择锁实现。

第一版最小编译器：

```text
scripts/compile_iir.py
```

详见 `references/implementation-ir.md`。

## 12. 基础能力库

复杂底层能力以基础能力契约（Primitive contract）提供，例如：

```text
transaction.atomic_group
concurrency.exclusive_resource_access
messaging.publish_reliably
persistence.compare_and_set
payment.charge
crypto.verify_signature
```

基础能力应描述：

```text
人类说明
输入 / 输出契约
前置 / 后置条件
影响
失败语义
幂等 / 原子性属性
各目标平台实现绑定
验证 / 测试
```

CLM 使用基础能力，不复制底层代码细节。

## 13. 验证

建议分层：

```text
L0 结构 / 类型有效
L1 内部语义一致
L2 实现符合 CLM
L3 场景 / 边界 / 性质测试
L4 选定属性的形式验证
L5 人工确认业务意图
```

根据语义选择验证后端，而不是要求单一工具验证所有性质：

```text
函数契约            → SMT / Dafny / Why3 类工具
状态迁移            → 状态模型检查
并发 / 时序         → TLA+ / LTL 类工具
示例场景            → 单元 / 集成测试
不变量              → 性质测试 + 可选形式证明
```

生成代码后可重新抽取“可观察语义模型”，与 CLM 的条件、状态写入、外部影响、顺序、错误比较。Round-trip 是额外防线，不替代独立测试。

第一版语义校验器：

```text
scripts/validate_clm.py
```

详见 `references/clm-validator.md` 与 `references/verification-and-generation.md`。

## 14. 测试从 CLM 派生

```text
场景            → 示例测试
条件            → 边界测试
不变量          → 性质测试
状态机          → 迁移测试
时序规则        → 集成测试 / 运行时监控
```

例如：

```text
Rule: amount <= payment_limit
```

至少派生：

```text
amount = limit - 1 → allowed
amount = limit     → allowed
amount = limit + 1 → rejected
```

## 15. 上下文压缩

大型模块分析使用：

```text
L0 源代码证据
 ↓
L1 逻辑节点摘要
 ↓
L2 子流程摘要
 ↓
L3 候选 CLM / 中文逻辑
```

压缩后必须保留 evidence pointer；出现矛盾或需要验证时重新读取源代码。

## 16. 停止条件

旧代码探索满足以下条件即可停止主要路径扩展：

```text
关键开放问题已经解决
主执行 / 数据 / 状态路径已经闭合
重要副作用已经识别
重要失败路径已经识别
不存在可能改变当前解释的关键未解析依赖
```

单独分支若继续读取不会显著改变当前目标解释，可以提前停止。

必要时设置 `max_nodes / max_reads / max_depth` 作为资源保险；达到预算时明确输出“已知 / 未知 / 下一步需要调查”，不得伪装成已经完整理解。

## 17. 最小可执行流水线

当任务涉及“修改逻辑并重新生成实现语义”时，优先使用统一流水线：

```text
scripts/run_logic_pipeline.py
```

执行顺序：

```text
校验原始 CLM
   ↓
可选应用语义补丁
   ↓
校验更新后的 CLM
   ↓
生成中文逻辑投影
   ↓
可选编译 IIR
```

示例：

```bash
python scripts/run_logic_pipeline.py \
  evals/fixtures/order-cancel.valid.json \
  --patch evals/fixtures/order-cancel.add-pending-acceptance.patch.json \
  --target-profile evals/fixtures/go-postgres.target-profile.json
```

任何一步失败都应立即终止，不得继续生成“看起来合理”的后续结果。

详见 `references/end-to-end-pipeline.md`。

## 18. 默认产出

根据模式生成当前任务所需的最小充分集合：

```text
候选 / 规范逻辑模型
人类可读逻辑
逻辑图 / 状态模型 / 决策表
证据映射
开放问题 / 未知项
优化提案
语义补丁
目标配置 / 实现中间表示
目标实现计划
验证计划 / 测试向量
语义差异
```

不要为了形式一次性生成所有产物。

## 19. 禁止事项

- 不把当前文件摘要当作模块完整逻辑。
- 不把函数名直译当作业务解释。
- 不把“假设”当作“已观察”。
- 不在忠实翻译阶段偷偷优化业务行为。
- 不把生成代码作为业务逻辑的反向事实源。
- 不从生成代码生成预期测试。
- 不把语言或框架特有语法写进规范领域逻辑。
- 不因为多个代码片段相似就强行抽公共规则。
- 不在 IIR 存在 `unresolved` 时宣称实现已经完整匹配 CLM。
- 不宣称“逻辑正确即可数学保证任意实现正确”；必须说明实际使用的验证层级。
