#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦门轻食策 —— 营养计算与方案生成核心
================================================

根据用户个人数据，生成一日三餐的减重饮食方案，包含两类套餐：
  1. 麦当劳套餐   —— 用麦当劳 MCP 下单 + 领券（"解馋也控卡"）
  2. 普通减肥食谱 —— 家常低卡高蛋白，作为替代选项

营养学依据（均为公认的通用估算，不构成专业医疗建议）：
  - 基础代谢 BMR：Mifflin-St Jeor 公式
  - 每日总消耗 TDEE = BMR × 活动系数
  - 1 kg 脂肪 ≈ 7700 千卡，据此由「目标减重斤数 + 天数」算出每日热量缺口
  - 减重期三大营养素：蛋白质 1.6 g/kg（保肌肉）、脂肪约 25%、碳水补足
  - 三餐热量分配：早餐 30% / 午餐 40% / 晚餐 30%
  - 安全下限：女性 1200 千卡 / 男性 1500 千卡，低于则提示调整目标

用法：
  python3 diet_planner.py
"""

from dataclasses import dataclass, asdict
from typing import List, Optional

from optimizer import Meal, optimize


# ---------------------------------------------------------------------------
# 1. 基础代谢与热量缺口计算
# ---------------------------------------------------------------------------

ACTIVITY_FACTORS = {
    "久坐": 1.2,        # 几乎不运动，办公室工作
    "轻度活动": 1.375,  # 每周 1-3 次运动
    "中度活动": 1.55,   # 每周 3-5 次运动
    "高强度活动": 1.725,  # 每周 6-7 次运动
}

CALORIES_PER_KG_FAT = 7700  # 1 kg 脂肪 ≈ 7700 千卡


def calc_bmr(sex: str, age: int, height_cm: float, weight_kg: float) -> float:
    """Mifflin-St Jeor 公式：基础代谢（千卡/天）。"""
    if sex == "男":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def calc_daily_target(
    bmr: float,
    target_jin: float,      # 目标减重斤数
    target_days: int,
    activity: str = "久坐",
    sex: str = "女",
) -> dict:
    """由 BMR、减重目标斤数、天数，算出每日热量目标与缺口。"""
    factor = ACTIVITY_FACTORS.get(activity, 1.2)
    tdee = bmr * factor
    total_deficit = (target_jin / 2.0) * CALORIES_PER_KG_FAT  # 斤 → kg → 总缺口
    daily_deficit = total_deficit / target_days
    daily_target = tdee - daily_deficit

    # 安全下限：女性 1200、男性 1500，避免过度节食
    floor = 1200 if sex == "女" else 1500
    warnings: List[str] = []
    if daily_target < floor:
        warnings.append(
            f"目标每日摄入 {daily_target:.0f} 千卡低于安全下限 {floor} 千卡，"
            f"建议延长减重周期或减小目标斤数"
        )
    if daily_deficit > 1000:
        warnings.append(
            f"每日热量缺口 {daily_deficit:.0f} 千卡偏大，减重过快易反弹，建议放慢节奏"
        )

    return {
        "tdee": round(tdee),
        "daily_deficit": round(daily_deficit),
        "daily_target": round(daily_target),
        "floor": floor,
        "warnings": warnings,
    }


def calc_macros(weight_kg: float, daily_target: float) -> dict:
    """减重期三大营养素分配。"""
    protein_g = weight_kg * 1.6            # 1.6 g/kg 保肌肉
    protein_kcal = protein_g * 4
    fat_kcal = daily_target * 0.25         # 脂肪 25%
    fat_g = fat_kcal / 9
    carb_kcal = daily_target - protein_kcal - fat_kcal
    carb_g = max(carb_kcal, 0.0) / 4
    return {
        "protein_g": round(protein_g),
        "fat_g": round(fat_g),
        "carb_g": round(carb_g),
    }


def split_meals(daily_target: float, protein_g: float) -> dict:
    """按 30% / 40% / 30% 分配三餐热量与蛋白质预算。"""
    ratio = {"breakfast": 0.30, "lunch": 0.40, "dinner": 0.30}
    return {
        name: {
            "kcal": round(daily_target * r),
            "protein_g": round(protein_g * r),
        }
        for name, r in ratio.items()
    }


# ---------------------------------------------------------------------------
# 2. 普通减肥食谱库（类型 B：家常低卡高蛋白）
# ---------------------------------------------------------------------------

@dataclass
class Recipe:
    name: str
    meal: str            # breakfast / lunch / dinner
    kcal: float
    protein: float
    ingredients: str
    method: str


RECIPE_DB: List[Recipe] = [
    # ---- 早餐 ----
    Recipe("水煮蛋 x2 + 全麦面包 + 无糖豆浆", "breakfast", 320, 22,
           "鸡蛋2个、全麦面包1片、无糖豆浆250ml", "鸡蛋水煮8分钟，面包烤1分钟，豆浆加热"),
    Recipe("燕麦牛奶 + 香蕉半根", "breakfast", 300, 12,
           "即食燕麦40g、脱脂牛奶250ml、香蕉半根", "燕麦加牛奶小火煮3分钟，香蕉切片加入"),
    Recipe("鸡胸肉蔬菜卷 + 黑咖啡", "breakfast", 280, 28,
           "鸡胸肉80g、生菜、全麦卷饼1张、黑咖啡", "鸡胸肉煎熟切条，卷入生菜与饼中"),
    Recipe("希腊酸奶 + 蓝莓 + 少量坚果", "breakfast", 260, 18,
           "无糖希腊酸奶150g、蓝莓50g、杏仁10g", "混合即可"),
    # ---- 午餐 ----
    Recipe("香煎鸡胸 + 糙米饭 + 西兰花", "lunch", 520, 42,
           "鸡胸肉150g、糙米60g(生)、西兰花200g", "鸡胸煎熟，糙米蒸熟，西兰花焯水"),
    Recipe("清蒸鲈鱼 + 杂粮饭 + 时蔬", "lunch", 480, 38,
           "鲈鱼150g、杂粮米60g、青菜200g", "鲈鱼清蒸8分钟，杂粮饭蒸熟，青菜快炒"),
    Recipe("牛肉炒时蔬 + 玉米一根", "lunch", 500, 36,
           "瘦牛肉120g、青椒洋葱、玉米1根", "牛肉快炒，玉米蒸熟"),
    Recipe("豆腐菌菇汤 + 全麦面包 x1", "lunch", 380, 26,
           "嫩豆腐200g、菌菇150g、全麦面包1片", "豆腐菌菇煮汤，面包烤热"),
    # ---- 晚餐 ----
    Recipe("番茄鸡胸意面（全麦）", "dinner", 450, 34,
           "鸡胸肉120g、全麦意面60g、番茄2个", "意面煮熟，鸡胸与番茄酱同炒"),
    Recipe("虾仁蔬菜沙拉 + 溏心蛋", "dinner", 320, 28,
           "虾仁120g、混合生菜、鸡蛋1个、油醋汁", "虾仁焯熟，蔬菜拌匀，蛋煮6分钟"),
    Recipe("冬瓜虾皮汤 + 鸡胸肉 + 蔬菜", "dinner", 300, 30,
           "冬瓜250g、虾皮、鸡胸肉100g、蔬菜150g", "冬瓜虾皮煮汤，鸡胸煎熟"),
    Recipe("清炒时蔬 + 水煮蛋 x2 + 小米粥", "dinner", 280, 18,
           "时蔬300g、鸡蛋2个、小米40g", "小米煮粥，蛋水煮，时蔬快炒"),
]


# ---------------------------------------------------------------------------
# 3. 麦当劳菜单（类型 A：示例数据，生产环境由 MCP 实时获取）
# ---------------------------------------------------------------------------

MCD_MENU: List[Meal] = [
    # 早餐类
    Meal("猪柳蛋麦满分", 16.0, 387, 23),
    Meal("原味板烧鸡腿麦满分", 14.5, 246, 15),
    Meal("皮蛋鸡肉粥", 9.5, 133, 6),
    Meal("脆薯饼", 6.0, 146, 1),
    # 主食类
    Meal("板烧鸡腿堡", 14.0, 391, 23),
    Meal("双层吉士汉堡", 16.5, 429, 27),
    Meal("麦香鸡", 11.0, 369, 15),
    Meal("麦香鱼", 13.0, 325, 16),
    Meal("汉堡包", 9.0, 248, 13),
    # 小食类
    Meal("中薯条", 11.5, 289, 4),
    Meal("小杯玉米杯", 6.0, 53, 2),
    Meal("麦乐鸡5块", 12.0, 213, 12),
    Meal("鲜蔬杯", 9.0, 70, 2),
    # 饮品类
    Meal("无糖可口可乐中杯", 7.5, 0, 0),
    Meal("纯牛奶(盒装)", 8.0, 129, 7),
    Meal("冰美式中杯", 9.0, 13, 1),
]


# ---------------------------------------------------------------------------
# 4. 方案生成
# ---------------------------------------------------------------------------

def generate_mcd_plan(menu: List[Meal], meal_split: dict) -> dict:
    """为每餐在麦当劳菜单中挑出满足热量/蛋白质预算的组合（求蛋白质最高的组合）。"""
    plan = {}
    for meal_name, budget in meal_split.items():
        combo = optimize(
            menu,
            budget=1e9,                       # 这里不限价，价格维度由 calculate-price 补充
            max_calories=budget["kcal"],
            min_protein=max(budget["protein_g"] - 5, 0),  # 蛋白允许略低于目标，优先不超热量
            objective="max_protein",
        )
        if combo is None:
            combo = optimize(
                menu, budget=1e9, max_calories=budget["kcal"],
                objective="max_protein",
            )
        plan[meal_name] = {
            "items": [m.name for m in combo.meals] if combo else [],
            "kcal": combo.total_calories if combo else 0,
            "protein_g": combo.total_protein if combo else 0,
        }
    return plan


def generate_homemade_plan(recipe_db: List[Recipe], meal_split: dict) -> dict:
    """为每餐从食谱库挑选最接近热量预算的食谱（默认选一份）。"""
    plan = {}
    for meal_name, budget in meal_split.items():
        candidates = [r for r in recipe_db if r.meal == meal_name]
        best = min(
            candidates,
            key=lambda r: abs(r.kcal - budget["kcal"]),
        ) if candidates else None
        plan[meal_name] = {
            "items": [best.name] if best else [],
            "kcal": best.kcal if best else 0,
            "protein_g": best.protein if best else 0,
            "ingredients": best.ingredients if best else "",
            "method": best.method if best else "",
        }
    return plan


def build_profile(
    sex: str, age: int, height_cm: float, weight_kg: float,
    target_jin: float, target_days: int, activity: str = "久坐",
    bmr: Optional[float] = None,
) -> dict:
    """组装个人数据，返回完整计算结果。用户可直接给 BMR，也可由身高体重估算。"""
    if bmr is None:
        bmr = calc_bmr(sex, age, height_cm, weight_kg)
    target = calc_daily_target(bmr, target_jin, target_days, activity, sex)
    macros = calc_macros(weight_kg, target["daily_target"])
    meal_split = split_meals(target["daily_target"], macros["protein_g"])
    return {
        "bmr": round(bmr),
        **target,
        "macros": macros,
        "meal_split": meal_split,
    }


def demo() -> None:
    print("=" * 60)
    print("麦门轻食策 · 端到端演示")
    print("=" * 60)

    # 示例用户：女，28 岁，165cm，65kg，目标 30 天减 5 斤，轻度活动
    profile = build_profile(
        sex="女", age=28, height_cm=165, weight_kg=65,
        target_jin=5, target_days=30, activity="轻度活动",
    )
    print("\n【个人数据】")
    print(f"  BMR: {profile['bmr']} 千卡 | TDEE: {profile['tdee']} 千卡")
    print(f"  每日目标摄入: {profile['daily_target']} 千卡 "
          f"(每日缺口 {profile['daily_deficit']} 千卡)")
    print(f"  蛋白质 {profile['macros']['protein_g']}g | "
          f"脂肪 {profile['macros']['fat_g']}g | 碳水 {profile['macros']['carb_g']}g")
    if profile["warnings"]:
        for w in profile["warnings"]:
            print(f"  ⚠ {w}")

    mcd = generate_mcd_plan(MCD_MENU, profile["meal_split"])
    home = generate_homemade_plan(RECIPE_DB, profile["meal_split"])

    meal_names = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"}
    print("\n【一日三餐 · 两类套餐对比】")
    print(f"{'餐次':<4} | {'麦当劳套餐':<24} | {'普通减肥食谱':<22}")
    print("-" * 60)
    for key in ["breakfast", "lunch", "dinner"]:
        m = mcd[key]
        h = home[key]
        m_items = " + ".join(m["items"]) if m["items"] else "（无可选）"
        h_items = " + ".join(h["items"]) if h["items"] else "（无可选）"
        print(f"{meal_names[key]:<4} | {m_items:<24} | {h_items:<22}")
        print(f"     | {m['kcal']:.0f}千卡/{m['protein_g']:.0f}g蛋白"
              f"{'':<6} | {h['kcal']:.0f}千卡/{h['protein_g']:.0f}g蛋白")


if __name__ == "__main__":
    demo()
