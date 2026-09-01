# 目标测试生成规范 v0.1

目标测试生成位于语言无关 Test Vector 与具体测试代码之间。

```text
CLM
 ↓
generate_test_vectors.py
 ↓
Language-neutral Test Vectors
 ↓
Target Profile + IIR
 ↓
Target Test Plan
 ↓
Go/JUnit/pytest/... Test Generator
```

## 1. 为什么不能直接从 IIR 生成测试

测试的业务期望必须来自 CLM，而不是来自 IIR 或生成代码。

IIR 只负责补充：

- Use Case 入口；
- Repository / Port 依赖；
- 测试框架；
- mock/fake 边界；
- transaction / adapter 技术装配。

因此：

```text
Test Expectation ← CLM Test Vector
Test Wiring      ← IIR + Target Profile
```

## 2. Target Test Plan

```json
{
  "target_test_plan": {
    "version": "0.1",
    "language": "Go",
    "framework": "testing + testify",
    "cases": []
  }
}
```

每个 case：

```json
{
  "id": "test.scenario.order.cancel.pending.example",
  "source_semantic_id": "scenario.order.cancel.pending",
  "target_use_case": "usecase.behavior_order_cancel",
  "given": {},
  "invoke": {},
  "expect": {},
  "required_fakes": ["repository.domain_order"],
  "unsupported": []
}
```

## 3. 映射原则

- Scenario Vector → Use Case behavior invocation；
- Rule Vector → Rule/Use Case guard 测试；
- State Vector → Use Case 或 state transition 测试；
- Property Intent → property test / 目标语言等价机制；
- Temporal Intent → integration test，不降级成普通 unit test。

## 4. 不允许猜测

如果 Test Vector 缺少构造目标实体所需信息，Target Test Plan 应保留：

```json
"unsupported": [
  "缺少 domain.order 的构造策略"
]
```

不要伪造默认字段值后宣称测试已完整生成。

## 5. 第一阶段支持范围

v0.1 优先支持：

- Go `testing + testify`；
- Scenario；
- Rule guard；
- enum boundary；
- state transition；
- Repository fake / External Port fake 契约。

真正目标语言测试代码生成应在 Target Test Plan `unsupported` 为空后执行。