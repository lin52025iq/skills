# Go 目标生成器 v0.1

Go Generator 只消费 **已经通过 IIR v0.2 校验** 的实现中间表示，不直接读取 CLM 做技术猜测。

## 1. 第一版范围

支持：

- Use Case struct / constructor / method skeleton；
- Guard 条件占位与顺序；
- Typed Assignment；
- Repository Contract interface；
- External Port interface；
- Typed Error；
- Generated Manifest；
- 基于 Target Test Plan 的 `testing + testify` 测试骨架。

暂不自动实现：

- 第三方 SDK adapter；
- 未绑定 Primitive；
- 复杂事务协调；
- 分布式锁；
- retry/backoff 细节；
- Kafka producer / outbox 具体代码；
- 需要业务语义猜测的 DTO mapping。

这些情况必须由 IIR 的 `unresolved` / `generation_regions` 暴露，不能由 Generator 自行补全。

## 2. 输入 Gate

生成前必须满足：

```text
IIR v0.2 schema valid
IIR semantic validator valid
blocking unresolved = 0
Target Profile language = Go
```

任一不满足则拒绝生成。

## 3. 输出目录

默认：

```text
generated-go/
├── manifest.json
├── domain/
├── usecase/
├── ports/
└── tests/
```

文件布局可以由 Target Profile 调整，但 manifest 必须记录最终路径。

## 4. Repository Contract

IIR：

```json
{
  "id": "repository.order",
  "operations": ["save", "load"]
}
```

Go：

```go
type OrderRepository interface {
    Save(ctx context.Context, order *Order) error
    Load(ctx context.Context, id OrderID) (*Order, error)
}
```

如果输入/输出类型无法从 IIR 确定，不要猜参数；应生成 contract TODO 并标记 unresolved，正式生成模式则阻断。

## 5. External Port

IIR external port 映射为 interface。

第三方 SDK 实现属于 handwritten adapter，不生成真实调用代码。

## 6. Use Case

每个 IIR Use Case 生成：

```go
type CancelOrderUseCase struct {
    orderRepository OrderRepository
}
```

依赖只允许来自 IIR dependencies。

执行顺序必须严格按照：

```text
guards
→ steps
→ postconditions / effects
```

## 7. Typed Assignment

IIR assignment：

```text
domain.order.status = CANCELLED
```

映射到 Go 时必须使用已生成的领域字段/枚举类型，而不是自由字符串常量。

## 8. Error

IIR Error Mapping：

```text
error.order.cancel_forbidden
```

生成稳定 typed error，例如：

```go
var ErrOrderCancelForbidden = errors.New("order cancel forbidden")
```

错误名称来自 Semantic ID 的确定性命名转换。

## 9. Tests

测试代码只能消费 Target Test Plan。

第一版生成：

- test function；
- fixture variables；
- fake dependency slots；
- Given / When / Expect 注释和断言骨架。

如果某个 Test Plan 仍需业务 fixture，生成明确 TODO，不虚构对象内容。

## 10. Manifest

每次生成必须写：

```json
{
  "generator": "go-v0.1",
  "source_clm": "module.order",
  "source_semantic_hash": "...",
  "iir_version": "0.2",
  "target_profile": "go-postgres",
  "artifacts": []
}
```

每个 artifact 保存：

- path；
- semantic refs；
- generation mode；
- content hash。

## 11. 生成代码不可直接作为业务事实源

生成代码默认只读。业务修改必须回到 CLM / Semantic Change Set。

后续 CI 应使用 manifest + semantic hash + regen diff 检测人工漂移。
