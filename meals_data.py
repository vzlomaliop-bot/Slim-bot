MEAL_PERCENT = {
    "breakfast": 0.30,
    "lunch": 0.35,
    "dinner": 0.35,
    "snack": 0.10,
}


def scale_dish(dish, user_daily_calories, meal_type):
    """
    dish: кортеж из БД
    (id, meal_type, name, base_cal, base_prot, base_fat, base_carb, base_weight, ingredients)
    """
    percent = MEAL_PERCENT.get(meal_type, 0.33)
    target_cal = user_daily_calories * percent
    k = target_cal / dish[3]

    return {
        "name": dish[2],
        "calories": round(dish[3] * k),
        "protein": round(dish[4] * k, 1),
        "fat": round(dish[5] * k, 1),
        "carbs": round(dish[6] * k, 1),
        "weight": round(dish[7] * k),
        "ingredients": dish[8],
        "coefficient": round(k, 2),
    }


def format_scaled_dish(dish, user_daily_calories, meal_type):
    scaled = scale_dish(dish, user_daily_calories, meal_type)
    text = (
        f"✅ **{scaled['name']}**\n\n"
        f"🎯 Под твою норму ({user_daily_calories} ккал/день):\n\n"
        f"⚖️ Вес порции: **{scaled['weight']} г**\n"
        f"🔥 Калории: {scaled['calories']} ккал\n"
        f"🥩 Белки: {scaled['protein']} г\n"
        f"🥑 Жиры: {scaled['fat']} г\n"
        f"🍚 Углеводы: {scaled['carbs']} г\n\n"
        f"📝 Состав:\n{scaled['ingredients']}\n\n"
        f"_Коэффициент: ×{scaled['coefficient']}_"
    )
    return text, scaled
