from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from gigachat import GigaChat
import os

from database import get_user
from keyboards import main_menu

router = Router()


class AIDialog(StatesGroup):
    waiting_question = State()


@router.message(F.text == "🤖 AI-помощник")
async def ai_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "🤖 **Привет! Я твой AI-помощник.**\n\n"
        "Могу ответить на вопросы о питании, тренировках, мотивации. "
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
        f"Отвечай кратко (2-4 предложения), по делу, на русском. "
        f"{context}\n\n"
        f"Вопрос: {msg.text}"
    )

    try:
        credentials = os.getenv("GIGACHAT_CREDENTIALS")
        with GigaChat(
            credentials=credentials,
            scope="GIGACHAT_API_PERS",   # 👈 обязательно для физлиц
            verify_ssl_certs=False,
        ) as client:
            response = client.chat(prompt)
            answer = response.choices[0].message.content
            await msg.answer(answer, parse_mode="Markdown")
    except Exception as e:
        await msg.answer(f"⚠️ Ошибка AI: {e}")

    await msg.answer("Ещё вопрос? Или нажми ⬅️ В меню.")
