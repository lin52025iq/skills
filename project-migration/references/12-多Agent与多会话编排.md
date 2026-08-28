# 多 Agent 与多会话迁移编排

## 一、目标

大模块迁移不应让一个 Agent 在一个超长上下文中同时承担全部研究、设计、实现、测试和审查。

当迁移范围能够按能力或稳定边界拆分时，采用 **Supervisor / Coordinator + Workstreams + Independent Review**：

```text
Supervisor / 主会话
    │
    ├── WS-001 能力工作包 → Worker Agent / 独立对话
    ├── WS-002 能力工作包 → Worker Agent / 独立对话
    ├── WS-003 数据/集成工作包 → Worker Agent / 独立对话
    └── Review / Integration → Reviewer Agent / 主会话
```

宿主支持原生 subagent、agent team 或并行 agent 时可以直接委派；不支持时，使用多个独立对话读取同一套 `.migration/` 全局事实和各自工作包，实现相同协作协议。

核心不是“多开几个 Agent”，而是：

> **稳定的全局真相 + 不重叠的所有权 + 明确交接 + 独立验收。**

---

## 二、什么时候应该拆分

优先拆分的信号：

- 一个业务模块包含多个可独立说明的能力；
- 不同能力主要修改不同目标模块；
- 源系统研究本身可以按入口、数据、集成或业务域并行；
- 目标项目研究可由不同 Agent 分别寻找架构、数据访问、测试等范例；
- 单个会话已经需要同时维护大量不相关上下文；
- 迁移计划存在清晰 DAG，可以找到多个“已满足前置依赖”的任务；
- 需要独立 Reviewer 避免实现者自我确认。

不适合并行拆分：

- 迁移语义规格尚不稳定；
- 目标实现蓝图尚未确定；
- 多个任务会频繁修改同一批文件；
- 多个任务共同修改同一数据库 Schema 或共享契约且边界还不稳定；
- 一个能力的核心决策依赖另一个尚未确认的能力；
- 任务只是为了“平均分文件”，没有独立业务结果。

不为了并行而并行。强耦合任务宁可顺序执行。

---

## 三、角色划分

### 3.1 Supervisor / 迁移协调者

Supervisor 是全局真相和最终集成的所有者。

负责：

- 迁移阶段判断与 Gate；
- 维护迁移语义规格；
- 维护目标项目画像和目标实现蓝图；
- 维护技术栈迁移规则和设计原则；
- 构建工作包 DAG；
- 决定哪些工作包允许并行；
- 分配文件/模块/数据所有权；
- 处理跨工作包冲突；
- 接收 Worker 的新发现和规则变更提案；
- 决定是否修改全局规则；
- 触发受影响工作包重新验证；
- 集成、最终验证和完成判断。

Supervisor 不应自己吞下全部大模块编码工作。大任务进入实施阶段后，应优先成为协调者和集成者。

### 3.2 Research Worker

适合只读研究：

- 某一业务能力的源行为；
- 数据和 Schema；
- 外部集成和消息；
- 目标项目某类最佳范例；
- 目标语言/框架特定语义。

Research Worker 默认不修改正式目标代码。

输出进入自己的工作流发现记录，由 Supervisor 合并到全局语义规格、目标画像或规则中。

### 3.3 Implementation Worker

只负责一个明确工作包。

必须有：

- 能力目标；
- 关联语义规格；
- 目标蓝图位置；
- 目标项目范例；
- 前置依赖；
- 可修改范围；
- 禁止修改范围；
- 验收方式；
- 交接格式。

Worker 不得重新定义整个迁移架构。

### 3.4 Reviewer

Reviewer 与 Implementer 职责分离。

重点检查：

- 能力和业务规则是否完整；
- 是否出现 Copy-Smell；
- 是否符合目标项目惯例；
- 技术栈语义是否正确；
- 测试是否真的覆盖关键行为；
- 是否越过工作包边界；
- 是否产生与其他工作包冲突的共享改动。

高风险工作包优先由不同 Agent / 不同对话进行 Review。

---

## 四、全局真相与工作包局部状态分离

### 全局产物：只由 Supervisor 合并

例如：

```text
.migration/迁移语义规格.md
.migration/业务规则台账.md
.migration/能力迁移矩阵.md
.migration/目标项目画像.md
.migration/目标实现蓝图.md
.migration/技术栈迁移规则.md
.migration/设计改进台账.md
.migration/当前状态.md
```

Worker 可以提出变更建议，但并行执行时不应多个 Worker 同时直接修改这些全局文件，否则非常容易出现覆盖、冲突和真相漂移。

### 工作包局部状态

推荐：

```text
.migration/workstreams/
└── WS-001-create-order/
    ├── 工作包.md
    ├── 状态.md
    ├── 发现.md
    ├── 验证.md
    ├── 交接.md
    └── 审查.md
```

不要求每个工作包都创建全部文件，小工作包可以只使用 `工作包.md` + `交接.md`。

---

## 五、工作包必须围绕能力，而不是文件

错误：

```text
WS-001 迁移 OrderService.java
WS-002 迁移 OrderRepository.java
WS-003 迁移 OrderUtils.java
```

正确：

```text
WS-001 创建订单能力
WS-002 取消订单能力
WS-003 订单持久化与事务边界
WS-004 OrderCreated 事件与幂等
```

每个工作包应尽量形成一个可验证的独立业务结果。

---

## 六、工作包合同

每个 Worker 启动前必须拿到一个完整合同：

```text
工作包 ID
目标
工作类型：研究 / 设计 / 实现 / 验证 / 审查
关联能力
关联业务规则
关联迁移语义规格
关联目标实现蓝图
目标项目范例
前置依赖
允许读取范围
允许修改范围
禁止修改范围
共享契约
验收条件
验证命令/方式
必须输出的交接内容
```

对于多对话模式，这个合同就是新对话的启动上下文。

Worker 不应该需要重新猜“整个迁移为什么这么做”。

---

## 七、所有权与冲突规则

### 7.1 默认单写者

同一时间，一个正式源码文件、一个核心 Schema、一个共享契约或一个目标模块，优先只有一个工作包拥有写权限。

如果两个工作包必须修改同一位置：

- 合并为一个工作包；或
- 抽出共享前置工作包；或
- 明确顺序执行；或
- 由 Supervisor 在集成阶段统一修改。

不要让两个 Agent “最后 Git 合并解决”。文本冲突容易解决，语义冲突不容易。

### 7.2 全局规则只读

Worker 默认把以下内容视为只读：

- 迁移语义规格；
- 目标项目画像；
- 目标实现蓝图；
- 技术栈迁移规则；
- 关键业务规则。

发现错误时写入 `发现.md` 或 `交接.md`，标记：

```text
RULE-CHANGE-PROPOSAL
SEMANTIC-CHANGE-PROPOSAL
BLUEPRINT-CHANGE-PROPOSAL
```

由 Supervisor 决定是否修改。

### 7.3 规则变更必须扇出

Supervisor 修改全局规则后：

1. 标记受影响工作包；
2. 暂停依赖旧规则且尚未完成的 Worker；
3. 对已完成任务重新判断是否需要验证；
4. 更新工作包版本或基线。

不能只更新文档然后假设其他 Agent 自动知道。

---

## 八、并行执行 Gate

Supervisor 只有在以下条件满足时才让工作包并行：

- 工作包目标独立；
- 前置依赖已满足；
- 共享语义和契约稳定；
- 修改所有权不冲突；
- 每个 Worker 有自己的验收方式；
- 失败不会让其他并行工作包产生不可逆副作用。

可以用：

```text
Ready
→ Running
→ Ready for Review
→ Changes Requested / Verified
→ Integrated
```

阻塞状态：

```text
Blocked by Dependency
Blocked by Rule Change
Blocked by Conflict
Blocked by Unknown
```

---

## 九、原生 Subagent 模式

宿主支持 subagent / agent team 时：

1. Supervisor 先完成全局语义、目标画像和蓝图；
2. 为每个子 Agent 只提供必要上下文和对应工作包；
3. 让子 Agent 使用隔离上下文，避免把 Supervisor 的全部推理历史无意义复制过去；
4. 并行只用于真正独立的工作包；
5. 让 Reviewer 与 Implementer 分离；
6. 子 Agent 返回结构化交接，而不是只说“完成了”。

优先让子 Agent承担：

- 深度只读研究；
- 独立能力实现；
- 测试与对照验证；
- 代码审查；
- 噪声较大的日志/失败分析。

Supervisor 保留架构和全局决策。

---

## 十、多对话模拟模式

宿主没有原生 subagent 时，也可以使用多个独立对话。

### Supervisor 对话

负责生成：

```text
.migration/workstreams/WS-XXX/工作包.md
```

### Worker 对话启动方式

新对话只需要：

> 使用 project-migration，执行 `.migration/workstreams/WS-003/工作包.md`。先读取工作包中列出的全局只读文档，只处理本工作包允许范围。完成后写入 `交接.md`，不要自行改变全局迁移规则。

### Worker 完成后

至少留下：

- 实际完成内容；
- 修改文件；
- 验证结果；
- 新发现；
- 全局规则变更建议；
- 未解决问题；
- 后续依赖方需要知道的事项。

Supervisor 再统一读取这些交接并集成。

这样多会话之间不依赖聊天历史，而依赖仓库中的可持久化协议。

---

## 十一、版本控制隔离

宿主支持 Git worktree / branch 时，大型并行实现优先让不同 Worker 使用独立分支或 worktree。

但版本控制隔离不能代替所有权设计：

- 两个 Worker 即使在不同分支，也不要同时重构同一个核心模块；
- 数据库 Schema、公共 API、共享类型等仍需要单一所有者或前置契约工作包；
- 合并顺序由依赖 DAG 决定，不按“谁先写完”决定。

---

## 十二、Supervisor 集成协议

每一批 Worker 完成后，Supervisor：

1. 收集所有交接；
2. 先处理规则/语义/蓝图变更提案；
3. 检查工作包之间是否产生矛盾；
4. 检查共享契约和数据所有权；
5. 按依赖顺序集成；
6. 执行跨工作包测试；
7. 做 Copy-Smell 和目标原生审查；
8. 更新全局能力矩阵、规则台账和当前状态；
9. 再释放下一批 Ready 工作包。

单个 Worker 测试通过不代表整个批次通过。

---

## 十三、不要过度生成 Agent

多 Agent 有额外上下文、同步、冲突和验证成本。

以下任务通常不值得再拆子 Agent：

- 很小且单一的代码修改；
- 强依赖同一核心设计；
- 同一文件内高度耦合的工作；
- 一个 Worker 很快就能完成且验证简单的任务。

原则：

> Agent 数量由独立工作流数量决定，不由模块文件数量决定。

---

## 十四、推荐的大模块迁移队形

### 研究阶段

可以并行：

```text
Research-A：核心业务行为
Research-B：数据 / Schema / 事务
Research-C：外部集成 / 事件 / Job
Research-D：目标项目架构与语言范例
```

Supervisor 汇总成语义规格和目标项目画像。

### 设计阶段

不宜让多个 Worker 各自决定最终架构。

可以让不同 Agent 提出候选方案或进行对抗审查，但由 Supervisor 合并成唯一目标实现蓝图。

### 实施阶段

按能力 DAG 并行，例如：

```text
           ┌─ WS-101 Create Order
Core Types ├─ WS-102 Cancel Order
           └─ WS-103 Query Order
                    ↓
              WS-201 Events
                    ↓
              Integration Gate
```

### 验证阶段

可并行：

- 行为对照；
- 数据一致性；
- 安全权限；
- Copy-Smell / 目标原生审查；
- 性能。

最终完成判断仍由 Supervisor 统一执行。

---

## 十五、社区经验依据

本方法吸收以下经验：

- OpenAI GPT-5.6 multi-agent：主 Agent 负责协调多个并行子 Agent 并最终综合，适用于可以清晰拆成独立工作流的复杂任务：https://openai.com/index/builders-guide-to-gpt-5-6/
- OpenAI Codex 实践：大型变更先计划，Agent 更适合结构清晰、范围明确的工作单元；任务队列可以作为轻量 backlog：https://openai.com/business/guides-and-resources/how-openai-uses-codex/
- OpenAI Symphony：把任务系统作为 Agent orchestration 的控制面，每个开放任务对应独立 Agent，最终由人和控制面审查结果：https://openai.com/index/open-source-codex-orchestration-symphony/
- Anthropic Claude Code Advanced Patterns：Subagents 适合隔离上下文的聚焦子任务，Agent Teams 适合大型任务中的独立协作工作流：https://www.anthropic.com/webinars/claude-code-advanced-patterns
- Anthropic Agent Teams C Compiler 实践：并行 Agent 能扩大任务规模，但需要强测试、明确工作拆分和协调机制：https://www.anthropic.com/engineering/building-c-compiler

这些经验支持“按独立工作流拆分”，而不是简单增加 Agent 数量。
