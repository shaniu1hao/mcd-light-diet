#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦门轻食策 —— 组合优化参考实现
=====================================

目标：在「预算上限 + 营养目标」双重约束下，从麦当劳菜单里找出最优点单组合。

支持两种优化目标：
  1. cheapest    —— 满足营养目标（蛋白质 >= min_protein、热量 <= max_calories）时总价最低；
  2. max_protein —— 在预算与热量上限内蛋白质总量最高（即「吃得最值」）。

说明：
  - 这是纯算法参考实现，用于展示「双约束优化」的核心思路；
  - 实际使用时，餐品数据由麦当劳 MCP 的 list-nutrition-foods / query-meals /
    query-meal-detail / calculate-price 等工具实时获取；
  - 麦当劳单店菜单规模有限（几十款），用「组合枚举 + 剪枝」即可在毫秒级得到精确解。

用法：
  python3 optimizer.py
"""

from itertools import combinations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Meal:
    """一款可选餐品（单点或套餐均可视为一个可选单位）。"""
    name: str
    price: float        # 到手价（元，已含优惠）
    calories: float     # 热量（千卡）
    protein: float      # 蛋白质（克）


@dataclass
class Combo:
    """一个点单组合及其指标。"""
    meals: List[Meal]
    total_price: float
    total_calories: float
    total_protein: float

    def __repr__(self) -> str:
        names = " + ".join(m.name for m in self.meals)
        return (
            f"{names}\n"
            f"   到手价 ¥{self.total_price:.2f} | "
            f"热量 {self.total_calories:.0f} 千卡 | "
            f"蛋白质 {self.total_protein:.1f} g"
        )


def optimize(
    meals: List[Meal],
    budget: float,
    max_calories: float,
    min_protein: float = 0.0,
    max_items: int = 6,
    objective: str = "cheapest",
) -> Optional[Combo]:
    """
    在约束下寻找最优组合。

    约束：
      - 总价 <= budget
      - 总热量 <= max_calories
      - 总蛋白质 >= min_protein
      - 组合内餐品数量 <= max_items

    目标：
      - cheapest   ：满足约束的前提下总价最低
      - max_protein：满足约束的前提下总蛋白质最高
    """
    best: Optional[Combo] = None

    # 按「蛋白质 / 价格」降序预排序，帮助更快命中更优解
    ordered = sorted(
        meals, key=lambda m: m.protein / max(m.price, 1e-6), reverse=True
    )

    for size in range(1, max_items + 1):
        for combo in combinations(ordered, size):
            price = sum(m.price for m in combo)
            if price > budget:
                continue  # 超预算，剪枝

            calories = sum(m.calories for m in combo)
            if calories > max_calories:
                continue  # 超热量上限，剪枝

            protein = sum(m.protein for m in combo)
            if protein < min_protein:
                continue  # 蛋白质不达标，剪枝

            candidate = Combo(list(combo), price, calories, protein)

            if best is None:
                best = candidate
                continue

            if objective == "cheapest":
                better = candidate.total_price < best.total_price
            elif objective == "max_protein":
                better = candidate.total_protein > best.total_protein
            else:
                raise ValueError(f"未知目标: {objective}")

            if better:
                best = candidate

    return best


# ---------------------------------------------------------------------------
# 示例：以下为演示用的模拟菜单（真实数据由麦当劳 MCP 实时提供）
# ---------------------------------------------------------------------------
SAMPLE_MENU = [
    Meal("麦辣鸡腿堡", 12.5, 460, 24.0),
    Meal("板烧鸡腿堡", 14.0, 520, 26.0),
    Meal("双层吉士汉堡", 16.5, 450, 27.0),
    Meal("原味板烧鸡腿堡", 15.0, 540, 28.0),
    Meal("麦香鸡", 11.0, 380, 16.0),
    Meal("中薯条", 11.5, 340, 4.0),
    Meal("玉米杯", 8.5, 90, 3.0),
    Meal("鲜蔬杯", 9.0, 70, 2.0),
    Meal("零度可乐(中)", 7.5, 0, 0.0),
    Meal("纯牛奶", 8.0, 130, 6.5),
]


def demo() -> None:
    print("=" * 56)
    print("麦门轻食策 · 组合优化演示")
    print("=" * 56)

    # 场景一：30 元预算，热量 <= 700 千卡，蛋白质 >= 25g，求最省钱组合
    print("\n【场景一】30 元预算 + 700 千卡内 + 蛋白质 >= 25g -> 最省钱")
    combo = optimize(
        SAMPLE_MENU, budget=30, max_calories=700,
        min_protein=25, objective="cheapest",
    )
    print(combo if combo else "无可行组合")

    # 场景二：25 元预算，热量 <= 600 千卡，求蛋白质最高组合
    print("\n【场景二】25 元预算 + 600 千卡内 -> 蛋白质最高")
    combo = optimize(
        SAMPLE_MENU, budget=25, max_calories=600,
        objective="max_protein",
    )
    print(combo if combo else "无可行组合")


if __name__ == "__main__":
    demo()
