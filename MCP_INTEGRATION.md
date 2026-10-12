# MCP 集成说明（MCP_INTEGRATION）

本文档说明「麦门轻食策」实际使用的麦当劳 MCP Server、Tool、调用流程和业务价值。

## 1. 使用的 MCP Server

| 项 | 值 |
|---|---|
| Server 名称 | `mcd-mcp` |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 认证方式 | 请求头 `Authorization: Bearer <MCP_TOKEN>` |
| 官方指南 | https://github.com/M-China/mcd-mcp-server |

## 2. 使用的 Tool

| Tool | 用途 | 在本项目中的角色 |
|---|---|---|
| `auto-bind-coupons` | 一键领取麦麦省所有可用券 | **领券入口**：减重方案麦当劳套餐的省钱第一步 |
| `available-coupons` / `query-my-coupons` / `query-store-coupons` | 查询可领/已领/门店可用券 | 确认可用优惠，供算价使用 |
| `query-nearby-stores` / `delivery-query-stores` | 查询附近/可配送门店 | 下单前定位门店 |
| `query-meals` | 查询门店可售餐品菜单（含商品编码） | 获取候选餐品与下单所需编码 |
| `query-meal-detail` | 查询餐品/套餐详情与替换项 | 拆解套餐组成，支持单品替换 |
| `list-nutrition-foods` | 查询餐品营养（能量/蛋白质/脂肪/碳水/钠/钙） | 提供「营养」维度的真实数据 |
| `calculate-price` | 按商品列表（含券）计算到手价/优惠/配送费 | 提供「价格」维度的真实数据 |
| `create-order` | 创建订单，返回支付链接 | **下单入口**：把方案直接变成可支付的订单 |

## 3. 调用流程

### 3.1 减重方案生成流程

```
用户输入个人数据（性别/年龄/身高/体重/基础代谢/减重斤数/天数/活动水平）
        │
        ▼
① diet_planner.build_profile   计算 BMR / TDEE / 每日缺口 / 每日目标摄入
   （三大营养素 + 三餐热量分配 30%/40%/30%）
        │
        ├──► ② 麦当劳套餐：list-nutrition-foods + query-meals 取数据
        │        generate_mcd_plan() 在每餐预算内求最优组合
        │
        └──► ③ 普通食谱：generate_homemade_plan() 从内置食谱库匹配
        │
        ▼
④ 并排对比展示两类套餐（热量 / 蛋白质 / 价格 / 做法），支持切换
        │
        ▼
⑤（麦当劳套餐）领券 + 下单：
   auto-bind-coupons（一键领券）
   → query-nearby-stores（定位）
   → query-meals（取商品编码）
   → calculate-price（算到手价）
   → create-order（下单，返回支付链接）
```

### 3.2 省钱 + 营养双约束点单流程

```
auto-bind-coupons → query-meals + list-nutrition-foods + calculate-price
        │
        ▼
optimizer.optimize（总价 ≤ 预算；热量 ≤ 上限；蛋白质 ≥ 下限）
        │
        ▼
输出组合清单 + 到手总价 + 营养汇总 + 省钱金额
```

## 4. 业务价值

- **对用户**：把「减重」从「算不清楚」变成「照着点就行」，并提供麦当劳/家常两条路，降低坚持门槛。
- **对平台**：将麦当劳 MCP 的「领券 + 菜单 + 营养 + 算价 + 下单」全链路能力，组合成一个高频、刚需、高粘性的减重场景，充分展示 MCP 生态的落地想象力。
- **差异化**：榜单上「省钱」「控卡」类项目众多，但本项目的「个人化热量缺口计算 + 麦当劳/家常双套餐切换 + 下单领券闭环」组合，具备更强的辨识度与完整度。
