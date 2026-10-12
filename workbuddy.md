# workbuddy.md — 开发对话上下文

> 本文件记录「麦门轻食策」使用 WorkBuddy 开发时的关键对话上下文，用于核验 WorkBuddy 联动活动奖励条件。

## 项目概况

- **项目名称**：麦门轻食策（mcd-light-diet）
- **一句话定位**：输入身体数据与减重目标，生成一日三餐方案，提供「麦当劳套餐（领券+下单）」与「普通减肥食谱」两类可选并支持对比切换。
- **开发工具**：腾讯 WorkBuddy（官方合作伙伴）

## 选题决策

- 最初候选方向：省钱助手 / 控卡营养师 / 麦麦派对管家 / 趣味出圈款。
- 第一版选定「省钱 + 营养」双约束点单；后按需求升级为 **「麦门轻食策」**：把「个人化热量缺口计算」与「麦当劳/家常双套餐切换」组合，差异化更强、完整度更高。

## 核心设计

- 营养计算：Mifflin-St Jeor 计算 BMR；TDEE = BMR × 活动系数；每日缺口 = 目标斤数 ÷ 2 × 7700 ÷ 天数；蛋白 1.6g/kg、脂肪 25%、碳水补足；三餐 30%/40%/30%。
- 安全下限：女 1200 / 男 1500 千卡，低于则提示调整目标。
- 两类套餐：麦当劳套餐（`generate_mcd_plan` + 组合优化）与普通减肥食谱（`generate_homemade_plan` + 内置食谱库）。
- 实现方式：WorkBuddy Skill（SKILL.md）+ `diet_planner.py`（营养计算与方案生成）+ `optimizer.py`（组合优化）。
- 数据来源：麦当劳 MCP 实时接口，不编造价格与营养数据。

## 使用到的麦当劳 MCP 工具

`auto-bind-coupons`、`query-meals`、`query-meal-detail`、`list-nutrition-foods`、`calculate-price`、`create-order`、`available-coupons`、`query-my-coupons`、`query-store-coupons`、`query-nearby-stores`、`delivery-query-stores`。

## 开发备注

- `diet_planner.py`、`optimizer.py` 均已本地运行验证通过（端到端可生成两类套餐对比）。
- 已实测连接麦当劳 MCP 并拉取 160 款餐品真实营养数据。
- `mcp-config.example.json` 仅使用环境变量占位符 `${MCD_MCP_TOKEN}`，不含真实 Token。
- 参赛声明 `CONTEST_DECLARATION.md` 使用官方模板原文，未做修改。
