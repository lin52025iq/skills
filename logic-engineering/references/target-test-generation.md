# 目标测试生成规范 v0.1

目标测试生成位于语言无关 Test Vector 与具体测试代码之间。

```text
CLM
 ↓
Node Test Vector Generator
 ↓
Language-neutral Test Vectors
 ↓
Target Profile + IIR
 ↓
Target Test Plan
 ↓
TypeScript/Vitest Test Generator
```

## 1. 测试期望来源

测试业务期望必须来自 CLM，而不是 IIR 或 generated code。

IIR 只补充 Use Case 入口、Repository / Port 依赖、测试框架和 fake/mock 技术装配。

```text
Test Expectation ← CLM Test Vector
Test Wiring      ← IIR + Target Profile
```

## 2. Target Test Plan

```json
{
  "target_test_plan": {
    "version": "0.1",
    "target_profile": "ts-sqlite",
    "cases": []
  }
}
```

每个 case 至少保存：

```text
id
kind
given
when
expect
use_case_id
fake_dependencies
```

## 3. Node 命令

先生成语言无关 Test Vector：

```bash
node scripts/logic_cli.mjs test-vectors model.json -o test-vectors.json
```

再生成 Target Test Plan：

```bash
node scripts/logic_cli.mjs target-tests \
  test-vectors.json \
  implementation.iir.json \
  -o target-test-plan.json
```

## 4. 映射原则

- Scenario Vector → Use Case invocation；
- Rule Vector → Rule / guard 测试；
- State Vector → state transition 测试；
- Property Intent → property test；
- Temporal Intent → integration test，不降级成普通 unit test。

## 5. 不允许猜测

Test Vector 缺少实体构造信息时，Target Test Plan 保留 unsupported/TODO，不伪造默认业务数据。

## 6. 首个 Reference Target

```text
TypeScript
Node.js
SQLite
Vitest
```

SQLite 只影响测试装配和 adapter，不改变 Test Expectation。

Target Test Plan 完成后由 TypeScript Generator 生成 Vitest 骨架。
