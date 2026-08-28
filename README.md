# 项目迁移 Skill

这是一个面向 AI 编程代理的系统迁移 Skill，用于将一个项目中的功能、模块、业务域或完整能力迁移到另一个项目，并支持跨语言、跨框架、跨数据库、跨架构以及遗留系统现代化。

当前版本的目标不只是“把代码逻辑搬过去”，而是同时完成两件事：

- **迁移正确**：业务能力、规则、接口、数据、副作用和失败语义得到可验证的延续；
- **目标代码更好**：不机械复制源项目中已确认的错误设计和技术债，目标实现应符合目标项目与目标技术栈的成熟实践，结构更清晰、更容易测试和继续演进。

核心工作方式：

```text
Research 源系统真实行为
→ 蒸馏为技术无关的迁移语义规格
→ Review 目标项目语言、架构、范例和可复用能力
→ 形成目标实现蓝图
→ 按目标项目方式 Rebuild
→ 行为与质量验证
```

对于大模块，可以进一步采用：

```text
Supervisor
→ 按独立业务能力拆分 Workstreams
→ 多个 Subagent / Agent Team / 独立对话并行处理
→ 独立 Reviewer
→ Supervisor 统一集成与 Gate
```

核心原则：

- 不把源文件、类、函数列表直接变成目标迁移任务；
- 源代码主要用于回答“旧系统真实做什么”，目标代码结构由迁移语义规格、目标项目画像和目标实现蓝图决定；
- 优先研究目标项目中真实、稳定、测试充分的模块，采用目标语言和框架的惯用方式；
- 重要结论区分“证据、推断、未知”，禁止把推断伪装成事实；
- 迁移开始前允许得出“局部迁移、先解耦、暂缓或不迁移”的结论；
- 大规模实施前先建立可验证旧、新实现的裁判，并通过可丢弃试迁移压力测试规则和目标设计；
- 保留业务语义，但允许对错误边界、过度耦合、框架侵入、重复逻辑、隐式副作用等设计问题做受控现代化；
- 大模块按独立工作流而不是文件数量拆分，多 Agent 间通过工作包、所有权和交接协议协作；
- 默认采用增量迁移，每个迁移单元可验证、可审查、必要时可回滚；
- Skill 的工作语言始终为中文。

入口：[`project-migration/SKILL.md`](project-migration/SKILL.md)

方法论：[`project-migration/references/00-项目迁移方法论.md`](project-migration/references/00-项目迁移方法论.md)

目标原生重建：[`project-migration/references/11-目标原生重建.md`](project-migration/references/11-目标原生重建.md)

多 Agent / 多会话编排：[`project-migration/references/12-多Agent与多会话编排.md`](project-migration/references/12-多Agent与多会话编排.md)

设计现代化：[`project-migration/references/09-设计现代化与代码质量.md`](project-migration/references/09-设计现代化与代码质量.md)
