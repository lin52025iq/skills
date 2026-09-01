# 目标测试生成规范 v0.2

Target Test Plan 位于语言无关 Test Vector 与具体目标测试代码之间。

```text
CLM
 ↓
Language-neutral Test Vectors
 ↓
Target Profile + IIR v0.2
 ↓
Target Test Plan v0.2
 ↓
Target Adapter Test Generator
```

## 1. 测试期望来源

测试业务期望必须来自 CLM，不来自 IIR 或 generated code。

IIR 只补充：

- Use Case 入口；
- Rule Guard 入口；
- Repository / External Port 依赖；
- runtime binding；
- 测试框架；
- fake/mock 边界；
- fixture constraint。

```text
Test Expectation ← CLM Test Vector
Test Wiring      ← IIR + Target Profile
```

## 2. 编译命令

先生成 Test Vector：

```bash
node scripts/logic_cli.mjs test-vectors \
  model.json \
  -o test-vectors.json
```

再编译 Target Test Plan：

```bash
node scripts/compile_target_tests.mjs \
  test-vectors.json \
  implementation.iir.json \
  -o target-test-plan.json
```

## 3. v0.2 结构

```json
{
  "target_test_plan": {
    "version": "0.2",
    "target_profile": "ts-sqlite",
    "source_clm": "module.order",
    "source_semantic_hash": "...",
    "cases": [],
    "summary": {
      "total": 0,
      "executable": 0,
      "unsupported": 0
    }
  }
}
```

每个 case 至少保存：

```text
id
source_semantic_id
kind
given
when
expect
target_kind
target_id
use_case_id
fake_dependencies
required_input_refs
fixture_constraints
unsupported
```

## 4. Rule Guard Case

Rule Test Vector 优先映射到引用该 Rule 的 IIR Guard：

```text
source Rule
→ IIR guard
→ target_kind = guard
```

首个 TS adapter 可以直接调用生成的 guard function 并断言 `rule_result`。

## 5. Scenario Use Case Case

Scenario：

```text
Given
+ When behavior
+ Then
```

映射为：

```text
Behavior
→ IIR Use Case
→ required_input_refs
→ fake_dependencies
→ fixture_constraints
```

`expect` 保持 CLM Scenario 的 Then，不得修改。

## 6. Fixture Constraint

测试装配允许使用 IIR Guard 约束构造技术 fixture。

例如：

```text
order.owner_id == current_user.id
```

Scenario 没有指定具体用户 ID 时，可以给两个字段写入同一个测试哨兵值：

```text
fixture-owner-1
```

这不属于新增业务期望，只是构造满足既有 precondition 的测试输入。

禁止：

- 为业务金额猜默认阈值；
- 为未知状态猜合法值；
- 绕过业务 guard；
- 根据 generated code 倒推 fixture 期望。

## 7. Unsupported Case

如果无法安全映射：

```json
{
  "unsupported": [
    "状态迁移执行器尚未生成"
  ]
}
```

Target Adapter 必须：

- 生成明确 `it.todo` / TODO；或
- 阻断正式测试生成。

禁止：

```ts
expect(true).toBe(true)
```

来伪装测试完成。

## 8. 当前映射

v0.2 当前优先支持：

```text
Rule positive / negative → guard test
Scenario                 → Use Case test
State Transition         → 保留计划，执行器未实现时 unsupported
Property Intent          → 后续 property adapter
Temporal Intent          → 后续 integration adapter
```

## 9. Reference Target

当前首个 Target：

```text
TypeScript 5.x
Node.js
SQLite
Vitest
```

SQLite 只影响 adapter / fake / persistence wiring，不改变 Test Expectation。

Target Test Plan 完成后由：

`scripts/generate_typescript_v02.mjs`

生成 Vitest 测试。
