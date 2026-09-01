---
name: logic-engineering
description: 将现有项目中的模块级业务实现重建为与编程语言无关、可由人直接理解和修改的 Canonical Logic Model，并在逻辑层执行归一化、公共逻辑提取、状态与规则分析、Semantic Patch 修改、目标技术栈实现生成和一致性验证。适用于 logic-first 开发、旧代码逻辑导入、模块级自然语言解释、逻辑优化和跨语言重实现。
---

# Logic Engineering

把软件开发视为 **逻辑模型的维护、验证与实现投影**，而不是直接维护某一种编程语言的源代码。

```text
Existing Code / Human Requirement
            ↓
   Candidate Logic Model
            ↓ confirm
   Canonical Logic Model (CLM)
      ┌─────┼──────────┐
      ↓     ↓          ↓
 Human View Verify   Implement
      ↓     ↓          ↓
 Natural   Formal    Target Code
 Logic     Checks     + Tests
```

## 1. 核心原则

1. **Logic is Source.** 业务逻辑的权威源是 Canonical Logic Model（CLM），不是散文式自然语言，也不是生成代码。
2. **Natural Language is Projection.** 用户看到的是 CLM 的人类可读投影；自由自然语言不能静默成为 canonical 状态。
3. **Free NL only proposes.** 用户以自由文本提出修改时，先产生 Semantic Patch Proposal，再决定是否应用。
4. **Generated Code is output.** 完成 logic-first 接管后，业务修改回到 CLM；生成代码默认不作为人工修改入口。
5. **Stable Semantic Identity.** Rule、Behavior、State、Constraint、Scenario 等都有稳定、语言无关、文件路径无关的 Semantic ID。
6. **Traceability first.** Legacy import 必须区分 OBSERVED / INFERRED / ASSUMED / UNKNOWN，并绑定源代码证据。
7. **LLM proposes; checks decide.** LLM 负责理解、提炼、建议和候选生成；schema、类型、约束、测试和 verifier 负责判定是否可接受。
8. **Business and infrastructure separate.** CLM 描述事务、幂等、顺序、互斥、一致性等要求；具体框架和 API 进入 Implementation IR / Target Profile。
9. **Tests derive from logic.** 测试从 CLM 独立生成，不从生成代码反推 expected behavior。
10. **Do not silently change behavior.** Observed Logic 与 Intended Logic 必须分离；优化默认以 proposal 表达。

## 2. 工作模式

根据用户目标选择一个或多个 mode：

```text
import      Existing Code → Candidate CLM
explain     Existing Code / CLM → Human-readable Logic
normalize   Faithful Logic → lossless normalized CLM
optimize    CLM → Optimization Proposal / Semantic Patch
edit        Human change → Semantic Patch → CLM
migrate     CLM → Target Profile → Implementation
verify      CLM ↔ implementation / tests / formal checks
```

`import` 是已有项目进入 logic-first 工作流的入口；`edit / optimize / migrate` 应以已确认 CLM 为事实源。

## 3. Canonical Logic Model

CLM 是 typed semantic graph。第一版至少支持七类节点：

```text
Domain      Entity / ValueType / Enum / Relationship
Behavior    Purpose / Input / Flow / Decision / Output / Failure
State       State / Transition / Forbidden Transition
Effect      Read / Write / External Call / Emit / Persist
Constraint  Precondition / Postcondition / Invariant / Temporal / Concurrency
Scenario    Given / When / Then / Boundary Example
Primitive   language-independent technical capability contract
```

常用关系：

```text
REQUIRES       INVOKES        READS          WRITES
TRANSITIONS    EMITS          HANDLES        GUARANTEES
CONSTRAINED_BY USES_PRIMITIVE DERIVED_FROM  EVIDENCED_BY
```

详细结构见 `references/canonical-logic-model.md`。

## 4. Semantic ID

Semantic ID 必须与实现名称解耦。例如：

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

## 5. Existing Code → Candidate CLM

对模块进行逆向理解时，不以当前文件为边界。

```text
Target Question / Module
        ↓
Locate Entry Points
        ↓
Skeleton Discovery
        ↓
Best-first Expansion
        ↓
Logic Facts + Evidence
        ↓
Candidate Logic Graph
        ↓
Candidate CLM + Human Projection
```

### 5.1 应继续追踪

当下列依赖会实质改变目标功能解释时继续定位：

- business/domain services
- validators / authorization
- state transitions
- special persistence / transaction semantics
- events / handlers / queues
- retry / fallback / idempotency
- external service adapters
- runtime/config-driven dispatch

通常不深入 logging、trivial getter/setter、plain DTO mapping、无业务影响 wrapper、框架内部普通实现。

优先 **breadth-first skeleton discovery + best-first expansion**，避免从首个调用一路深挖到底。

### 5.2 Open Question 驱动

探索必须维护：

```text
completed_nodes
frontier
open_questions
hypotheses
contradictions
unresolved_dynamic_edges
```

继续读取代码前先回答：“当前要关闭哪个 open question？”

### 5.3 Evidence 分类

```text
OBSERVED  源代码直接证明
INFERRED  多个 observed fact 合成
ASSUMED   依赖未验证的框架/运行时语义
UNKNOWN   当前证据不足
```

ASSUMED / UNKNOWN 不得静默升级成 canonical rule。

Legacy import 默认先建立 **Observed Behavior Model**；人或已有明确规范确认后，才建立 Intended Logic / Canonical CLM。

详见 `references/legacy-import.md`。

## 6. Human-readable Logic

同一个 CLM 至少提供三层自然语言投影：

```text
Business View         业务效果与核心规则
Logic View            条件、步骤、分支、状态变化、失败情况
Technical Logic View  事务、并发、幂等、重试、事件顺序、一致性
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

Human Projection 只能重排和解释 CLM，不能引入 CLM 中不存在的新业务规则。

## 7. Structured Editing 与自由文本修改

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

先生成 Semantic Patch Proposal：

```text
Target: rule.order.cancel.allowed_status
Operation: ADD_MEMBER
Value: PENDING_ACCEPTANCE
```

## 8. Semantic Patch

用户修改、Agent 优化、legacy 修复最终统一表示为 Semantic Patch。

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

详见 `references/semantic-patch.md`。

## 9. 逻辑优化

优化作用于 CLM，不直接改 generated code。

### O1 Lossless Normalization

不改变行为：

- 判断按语义分组
- branch / guard 归一化
- Decision Table 重建
- State Machine 重建
- 命名与概念统一

### O2 Behavior-preserving Refactoring

预期业务行为不变：

- 公共验证提取
- 公共 rule / flow 提取
- 重复逻辑消除
- 条件结构简化

必须做 semantic equivalence verification。

### O3 Robustness Improvement

通常不改变业务意图，但改变技术可靠性：

- transaction boundary
- retry
- idempotency
- concurrency protection
- reliable event publication

必须明确列出实现语义变化。

### O4 Business Behavior Change

真正改变业务规则：

- 新增/删除允许状态
- 修改权限
- 修改价格、退款等业务规则
- 补充缺失业务分支

默认需要明确确认。

### 9.1 潜在问题识别

重点检查：

```text
missing case
branch overlap
unreachable branch
contradicting rules
invalid state transition
invariant violation
side-effect ordering risk
transaction gap
non-idempotent retry path
concurrency race candidate
inconsistent duplicate rules
```

没有明确业务证据时必须使用 `potential`，不要把个人设计偏好描述成确定 bug。

## 10. 公共逻辑提取

公共逻辑不能只根据文本相似度判断。至少比较：

```text
semantic equivalence
same domain meaning
same pre/postconditions
same effects
likely change coupling
```

确认后创建公共 Semantic Node，让各 Behavior 通过引用复用，而不是复制自然语言文本。

## 11. Target Implementation

生成链路：

```text
CLM
 ↓
Target Profile
 ↓
Primitive Binding
 ↓
Implementation IR (IIR)
 ↓
Target Code Generator
```

Target Profile 至少描述：

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

不要把源语言技术语法机械翻译。例如 `synchronized` 应先恢复为“同一资源修改必须互斥”的语义要求，再由目标 Profile 选择锁实现。

## 12. Primitive Library

复杂底层能力以 Primitive contract 提供，例如：

```text
transaction.atomic_group
concurrency.exclusive_resource_access
messaging.publish_reliably
persistence.compare_and_set
payment.charge
crypto.verify_signature
```

Primitive 应描述：

```text
human description
input/output contract
pre/postconditions
effects
failure semantics
idempotency / atomicity properties
per-target implementation binding
verification / tests
```

CLM 使用 Primitive，不复制底层代码细节。

## 13. Verification

建议分层：

```text
L0 Schema / type validity
L1 Internal semantic consistency
L2 Implementation conformance
L3 Scenario / boundary / property tests
L4 Formal verification for selected properties
L5 Human confirmation of business intent
```

根据语义选择验证后端，而不是要求单一工具验证所有性质：

```text
function contracts     → SMT / Dafny / Why3 类工具
state transitions      → state model checking
concurrency / temporal → TLA+/LTL 类工具
examples               → unit/integration tests
invariants             → property tests + optional proof
```

生成代码后可重新抽取 Observable Semantic Model，与 CLM 的 conditions、state writes、external effects、ordering、errors 比较。Round-trip 是额外防线，不替代独立测试。

详见 `references/verification-and-generation.md`。

## 14. Tests 从 CLM 派生

```text
Scenario        → example tests
Condition       → boundary tests
Invariant       → property tests
State Machine   → transition tests
Temporal Rule   → integration/runtime monitor
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

## 15. Context Compression

大型模块分析使用：

```text
L0 Source Evidence
 ↓
L1 Logic Node Summary
 ↓
L2 Sub-flow Summary
 ↓
L3 Candidate CLM / Human Logic
```

压缩后必须保留 evidence pointer；出现矛盾或需要验证时重新读取源代码。

## 16. 停止条件

Legacy exploration 满足以下条件即可停止主要路径扩展：

```text
critical open questions resolved
main execution / data / state path closed
important effects identified
important failures identified
no unresolved dependency likely to change the explanation
```

单独分支若继续读取不会显著改变当前目标解释，可以提前停止。

必要时设置 max_nodes / max_reads / max_depth 作为资源保险；达到预算时明确输出 Known / Unknown / Next Investigation，不伪装成已完整理解。

## 17. 默认产出

根据 mode 生成所需内容，常见产出：

```text
Candidate / Canonical Logic Model
Human-readable Logic
Logic Graph / State Model / Decision Table
Evidence Map
Open Questions / Unknowns
Optimization Proposals
Semantic Patches
Target Profile / Implementation IR
Generated implementation plan
Verification plan / test vectors
Semantic Diff
```

不要为了形式一次性生成所有产物；只生成当前目标所需的最小充分集合。

## 18. 禁止事项

- 不把当前文件摘要当作模块完整逻辑。
- 不把函数名直译当作业务解释。
- 不把 ASSUMED 当 OBSERVED。
- 不在“忠实翻译”阶段偷偷优化业务行为。
- 不以 generated code 作为业务逻辑的反向事实源。
- 不从 generated code 生成 expected tests。
- 不把语言/框架特有语法写进 Canonical Domain Logic。
- 不因为多个代码片段相似就强行抽公共规则。
- 不宣称“逻辑正确即可数学保证任意实现正确”；必须说明实际验证层级。
