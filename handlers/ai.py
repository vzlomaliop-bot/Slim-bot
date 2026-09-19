from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from openai import AsyncOpenAI
import os

from database import get_user
from keyboards import main_menu

router = Router()

# Настраиваем клиент на GigaChat через OpenAI-совместимый API
ai_client = AsyncOpenAI(
    api_key=os.getenv("GIGACHAT_API_KEY"),
    base_url="https://gigachat.devices.sberbank.ru/api/v1"
)

class AIDialog(StatesGroup):
    waiting_question = State()

@router.message(F.text == "🤖 AI-помощник")
async def ai_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "🤖 **Привет! Я твой AI-помощник.**\n\n"
        "Могу ответить на вопросы о питании, тренировках, мотивации или просто поддержать. "
        "Что тебя интересует?\n\n"
        "Напиши вопрос, а я постараюсь помочь.\n\n"
        "Чтобы выйти — нажми ⬅️ В меню.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await state.set_state(AIDialog.waiting_question)

@router.message(AIDialog.waiting_question)
async def ai_answer(msg: Message, state: FSMContext):
    if msg.text == "⬅️ В меню":
        await state.clear()
        await msg.answer("Возвращаюсь в меню.", reply_markup=main_menu())
        return
    
    user = get_user(msg.from_user.id)
    context = ""
    if user:
        context = (
            f"Контекст: пользователь, цель {user['goal_weight']} кг, "
            f"текущий вес {user['current_weight']} кг, норма {user['daily_calories']} ккал."
        )

    prompt = (
        f"Ты — дружелюбный помощник по похудению и фитнесу. "
        f"Отвечай кратко (2-4 предложения), по делу, на русском языке. "
        f"{context}\n\n"
        f"Вопрос пользователя: {msg.text}"
    )

    try:
        response = await ai_client.chat.completions.create(
            model="GigaChat",  # или GigaChat-Pro
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        answer = response.choices[0].message.content
        await msg.answer(answer, parse_mode="Markdown")
    except Exception as e:
        await msg.answer(f"⚠️ Ошибка AI: {e}")

    await msg.answer("Ещё вопрос? Или нажми ⬅️ В меню.", reply_markup=ReplyKeyboardRemove())
