# 示例：把 Vue 2 订单页面迁到既有 React 项目

本示例展示标准范围迁移，重点是工作流和证据，不是固定框架答案。

## 请求

> 把旧 Vue 2 管理后台的订单详情页迁到目标 React 项目。保持现有布局、交互和权限；目标项目使用 React Router、TanStack Query、React Hook Form 和现有 Design System。

## 1. 模式与范围

- 模式：执行
- 范围：标准，一个 Route 域 `/orders/:id`
- 包含：详情、编辑备注、取消订单、权限拒绝、Loading / Error / Empty
- 排除：订单列表、支付后端、订单数据模型重构
- redesign：不允许

## 2. Rule Zero

```bash
git status --short
git diff -- package.json yarn.lock
```

发现源仓库 clean，目标仓库有与迁移无关的未提交文案修改。记录目标 dirty state，不执行 stash/reset；迁移仅修改订单 Feature 目录。

基线可信度：`exact`，源页面可在固定 commit 和 mock API 上运行。

## 3. 自动盘点

```bash
python3 <skill-root>/scripts/inventory_frontend.py ../legacy-admin \
  --output .migration/source-inventory.json
python3 <skill-root>/scripts/inventory_frontend.py ../new-admin \
  --output .migration/target-inventory.json
```

盘点线索：

- 源：Vue 2、Vue Router、Vuex、Element UI、Less；
- 目标：React、React Router、TanStack Query、React Hook Form、Design System、CSS Modules；
- 源存在 `/orders/:id` Route、`canCancelOrder` Permission 和 `legacy-order-refund` Flag；
- `legacy-order-refund` 只有注释入口且产品已有新退款页，分类为 Deprecated，不迁移。

## 4. 契约

| 能力 | 生命周期 | 源行为 | 目标决策 | 验证 |
|---|---|---|---|---|
| 查看订单 | Active | 进入 Route 后请求详情 | Query 按 orderId 获取 | E2E + request count |
| 编辑备注 | Active | Modal，失败保留输入 | DS Dialog + RHF，保留失败值 | component + E2E |
| 取消订单 | Conditional | 仅 `canCancelOrder` 且状态允许 | 目标 permission hook + mutation | 权限矩阵 |
| 旧退款入口 | Deprecated | 已注释，有替代页 | 不迁移 | 生命周期证据 |

视觉基线固定：Chromium、1440×900 / 768×1024 / 390×844、zh-CN、light theme、同一 fixture 和字体。

## 5. 目标原生蓝图

```text
/orders/:orderId
└── OrderDetailPage
    ├── OrderHeader
    ├── OrderSummaryCard
    ├── OrderTimeline
    ├── EditNoteDialog
    └── CancelOrderDialog
```

状态所有权：

- orderId：URL State；
- 订单详情：TanStack Query Server State；
- Dialog open：Local UI State；
- 表单值与验证：React Hook Form；
- 取消权限：目标 permission hook；
- 不创建与 Vuex `orderDetail` 一一对应的全局 Store。

复用目标项目的 PageShell、Card、Dialog、Button、Toast、Skeleton 和 ErrorBoundary。通过 Token 适配源视觉，不复制 Element UI DOM 和 Less 文件树。

## 6. 试迁移与波次

- Wave 0：只迁 OrderSummaryCard + Loading / Error，验证 Query、Design System 和视觉基线；
- Wave 1：Route、Header、Timeline；
- Wave 2：EditNoteDialog；
- Wave 3：CancelOrderDialog + Permission；
- Wave 4：全页面 responsive、a11y 和 visual review。

每个 Wave 运行：

```bash
pnpm lint
pnpm typecheck
pnpm test --run order-detail
pnpm playwright test order-detail
```

## 7. 验收摘要

| 维度 | 结果 |
|---|---|
| Route / Deep Link | 3 种订单 ID 和直接刷新通过 |
| 功能 | 查看、编辑备注、取消订单通过；旧退款入口未恢复 |
| UI 状态 | Default、Loading、Error、Permission Denied 通过 |
| Visual | desktop/tablet/mobile 差异均已修复或批准 |
| Interaction | Keyboard、focus trap、失败保留输入通过 |
| Console / Network | 无新增 error；详情请求无重复 |
| Accessibility | Dialog name、focus restore、button state 通过 |
| Build / Tests | lint/typecheck exit 0；相关测试全部通过 |

最终结论：通过。旧 Vue Route 在灰度结束后删除；临时 API adapter 在所有订单页面迁移后清理。
