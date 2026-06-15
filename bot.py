import os
import asyncio
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

TOKEN = "8616065366:AAG4iuYv0-cytNUtOlu5WW-rw99lDZSvjbM"

bot = Bot(token=TOKEN)
dp = Dispatcher()

db = sqlite3.connect("training.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    exercise TEXT,
    weight TEXT,
    reps TEXT
)
""")
db.commit()
try:
    cursor.execute("ALTER TABLE workouts ADD COLUMN workout_num TEXT")
    db.commit()
except sqlite3.OperationalError:
    pass
    cursor.execute("""
CREATE TABLE IF NOT EXISTS reminder_log (
    user_id INTEGER PRIMARY KEY,
    last_reminder_date TEXT
)
""")
db.commit()
cursor.execute("""
CREATE TABLE IF NOT EXISTS temp_replacements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_num TEXT,
    old_exercise TEXT,
    new_exercise TEXT
)
""")
db.commit()
cursor.execute("""
CREATE TABLE IF NOT EXISTS replacements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_num TEXT,
    old_exercise TEXT,
    new_exercise TEXT,
    is_active INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS deleted_replacements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_num TEXT,
    old_exercise TEXT,
    new_exercise TEXT
)
""")

db.commit()
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "💪 Gym Bot запущен!\n\n"
        "Для просмотра всех возможностей введи:\n"
        "/commands"
    )
@dp.message(Command("add"))
async def add_workout(message: Message):
    lines = message.text.split("\n")

    first_line = lines[0].replace("/add", "").strip()
    first_parts = first_line.split()

    if not first_parts:
        await message.answer(
            "Формат одной записи:\n"
            "/add 1 Жим лёжа 80 8\n\n"
            "Формат нескольких записей:\n"
            "/add 1\n"
            "Жим лёжа 80 8\n"
            "Жим лёжа 80 7\n"
            "Жим гантелей лёжа 20 12"
        )
        return

    workout_num = first_parts[0]

    if workout_num not in ["1", "2", "3", "4"]:
        await message.answer("Номер тренировки должен быть 1, 2, 3 или 4.")
        return

    today = datetime.now().strftime("%d.%m.%Y")
    saved = 0
    saved_text = ""

    if len(lines) == 1:
        if len(first_parts) < 4:
            await message.answer("Формат: /add 1 Жим лёжа 80 8")
            return

        exercise = " ".join(first_parts[1:-2])
        weight = first_parts[-2]
        reps = first_parts[-1]

        cursor.execute(
            "INSERT INTO workouts (date, workout_num, exercise, weight, reps) VALUES (?, ?, ?, ?, ?)",
            (today, workout_num, exercise, weight, reps)
        )

        saved = 1
        saved_text += f"{exercise} — {weight}×{reps}\n"

    else:
        for line in lines[1:]:
            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) < 3:
                continue

            exercise = " ".join(parts[:-2])
            weight = parts[-2]
            reps = parts[-1]

            cursor.execute(
                "INSERT INTO workouts (date, workout_num, exercise, weight, reps) VALUES (?, ?, ?, ?, ?)",
                (today, workout_num, exercise, weight, reps)
            )

            saved += 1
            saved_text += f"{exercise} — {weight}×{reps}\n"

    db.commit()

    if saved == 0:
        await message.answer("Не удалось сохранить записи. Проверь формат.")
        return

    await message.answer(
        f"✅ Сохранено записей: {saved}\n\n"
        f"Тренировка {workout_num}\n"
        f"{today}\n\n"
        f"{saved_text}"
    )


@dp.message(Command("today"))
async def today(message: Message):
    today_date = datetime.now().strftime("%d.%m.%Y")

    cursor.execute(
        "SELECT exercise, weight, reps FROM workouts WHERE date = ?",
        (today_date,)
    )
    rows = cursor.fetchall()

    if not rows:
        await message.answer("За сегодня пока нет записей.")
        return

    text = f"Тренировка за {today_date}:\n\n"
    for exercise, weight, reps in rows:
        text += f"{exercise} — {weight} кг × {reps}\n"

    await message.answer(text)


@dp.message(Command("history"))
async def history(message: Message):
    exercise = message.text.replace("/history", "").strip()

    if not exercise:
        await message.answer("Формат: /history Жим лёжа")
        return

    cursor.execute(
        "SELECT date, weight, reps FROM workouts WHERE exercise LIKE ? ORDER BY id",
        (f"%{exercise}%",)
    )
    rows = cursor.fetchall()

    if not rows:
        await message.answer("Истории по этому упражнению пока нет.")
        return

    text = f"История: {exercise}\n\n"
    for date, weight, reps in rows:
        text += f"{date} — {weight} кг × {reps}\n"

    await message.answer(text)
@dp.message(Command("delete_day"))
async def delete_day(message: Message):
    date_text = message.text.replace("/delete_day", "").strip()

    if not date_text:
        await message.answer("Формат: /delete_day 15.06.2026")
        return

    cursor.execute("SELECT COUNT(*) FROM workouts WHERE date = ?", (date_text,))
    count = cursor.fetchone()[0]

    if count == 0:
        await message.answer(f"За {date_text} записей не найдено.")
        return

    cursor.execute("DELETE FROM workouts WHERE date = ?", (date_text,))
    db.commit()

    await message.answer(f"🗑 Удалено записей за {date_text}: {count}")
@dp.message(Command("workout"))
async def workout(message: Message):
    workout_num = message.text.replace("/workout", "").strip()

    if workout_num not in ["1", "2", "3", "4"]:
        await message.answer(
            "Выбери тренировку:\n\n"
            "/workout 1\n"
            "/workout 2\n"
            "/workout 3\n"
            "/workout 4"
        )
        return

    plans = {
        "1": {
            "title": "Тренировка 1 — Верх тела 💪",
            "exercises": {
                "Жим лёжа": ["60×11", "60×8", "60×6", "70×2"],
                "Жим гантелей лёжа": ["15×12", "20×12", "20×10"],
                "Тяга верхнего блока": ["40×12", "45×12", "50×12", "45×10"],
                "Скамья Скотта": ["10×12", "10×12", "10×12", "10×12"],
            }
        },
        "2": {
            "title": "Тренировка 2 — Ноги + плечи 🦵💪",
            "exercises": {
                "Присед": ["50×10", "50×8", "60×6", "60×6"],
                "Жим платформы": ["40×12", "40×12", "40×12"],
                "Разведение гантелей": ["10×12", "10×12", "12.5×12"],
                "Жим штанги сидя": ["5×12", "5×12", "5×9"],
            }
        },
        "3": {
            "title": "Тренировка 3 — Спина + трицепс 💪",
            "exercises": {
                "Подтягивания": ["9", "6", "4", "3"],
                "Тяга в наклоне": ["40×12", "40×12", "50×12"],
                "Брусья": ["12", "7", "6", "5"],
                "Трицепс в пуловере": ["40×12", "45×12", "45×12", "50×8"],
            }
        },
        "4": {
            "title": "Тренировка 4 — Грудь, бицепс, плечи 💪",
            "exercises": {
                "Жим лёжа": ["60×11", "60×8", "60×6", "70×2"],
                "Жим в хаммере": ["10×12", "15×12", "15×10"],
                "Подъём гантелей на бицепс": ["15×12", "17.5×8", "17.5×8", "20×6"],
                "Молотки": ["10×12", "10×9", "10×12"],
                "Тренажёр на среднюю дельту": ["20×12", "20×12", "25×12", "25×12"],
            }
        }
    }

    plan = plans[workout_num]
    text = plan["title"] + "\n\n"

    for exercise, base_sets in plan["exercises"].items():
        original_exercise = exercise

        cursor.execute("""
            SELECT new_exercise
            FROM temp_replacements
            WHERE workout_num = ? AND old_exercise = ?
            ORDER BY id DESC
            LIMIT 1
        """, (workout_num, original_exercise.lower()))

        temp = cursor.fetchone()

        if temp:
            exercise = temp[0]

        cursor.execute("""
            SELECT new_exercise
            FROM replacements
            WHERE workout_num = ? AND old_exercise = ? AND is_active = 1
            ORDER BY id DESC
            LIMIT 1
        """, (workout_num, exercise))

        replacement = cursor.fetchone()

        if replacement:
            exercise = replacement[0]
        cursor.execute("""
            SELECT date
            FROM workouts
            WHERE workout_num = ? AND exercise = ?
            ORDER BY id DESC
            LIMIT 1
        """, (workout_num, exercise))

        last_date = cursor.fetchone()

        text += f"{exercise}\n"

        if last_date:
            date = last_date[0]

            cursor.execute("""
                SELECT weight, reps
                FROM workouts
                WHERE workout_num = ? AND exercise = ? AND date = ?
                ORDER BY id
            """, (workout_num, exercise, date))

            rows = cursor.fetchall()

            text += f"Последний результат {date}:\n"
            for weight, reps in rows:
                if weight == "0":
                    text += f"{reps}\n"
                else:
                    text += f"{weight}×{reps}\n"
        else:
            text += "Базовый результат:\n"
            for item in base_sets:
                text += f"{item}\n"

        text += "\n"

    await message.answer(text)
@dp.message(Command("delete"))
async def delete_last(message: Message):
    cursor.execute("""
        SELECT id, exercise, weight, reps, date
        FROM workouts
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()

    if not row:
        await message.answer("Нет записей для удаления.")
        return

    workout_id, exercise, weight, reps, date = row

    cursor.execute(
        "DELETE FROM workouts WHERE id = ?",
        (workout_id,)
    )
    db.commit()

    await message.answer(
        f"🗑 Удалена последняя запись:\n\n"
        f"{date}\n"
        f"{exercise} — {weight} кг × {reps}"
    )
@dp.message(Command("replace"))
async def replace_exercise(message: Message):
    text = message.text.replace("/replace", "").strip()

    if "|" not in text:
        await message.answer(
            "Формат:\n"
            "/replace 1 Старое упражнение | Новое упражнение\n\n"
            "Пример:\n"
            "/replace 1 Скамья Скотта | Подъем гантелей на бицепс"
        )
        return

    left, new_exercise = text.split("|", 1)
    left_parts = left.strip().split()

    if len(left_parts) < 2:
        await message.answer("Формат: /replace 1 Старое упражнение | Новое упражнение")
        return

    workout_num = left_parts[0]
    old_exercise = " ".join(left_parts[1:]).strip()
    new_exercise = new_exercise.strip()

    if workout_num not in ["1", "2", "3", "4"]:
        await message.answer("Номер тренировки должен быть 1, 2, 3 или 4.")
        return

    cursor.execute("""
        UPDATE replacements
        SET is_active = 0
        WHERE workout_num = ? AND old_exercise = ? AND is_active = 1
    """, (workout_num, old_exercise))

    cursor.execute("""
        INSERT INTO replacements (workout_num, old_exercise, new_exercise, is_active)
        VALUES (?, ?, ?, 1)
    """, (workout_num, old_exercise, new_exercise))

    db.commit()

    await message.answer(
        "✅ Замена сохранена:\n\n"
        f"Тренировка {workout_num}\n"
        f"{old_exercise} → {new_exercise}\n\n"
        "Отменить последнюю замену:\n"
        "/undo_replace"
    )


@dp.message(Command("undo_replace"))
async def undo_replace(message: Message):
    cursor.execute("""
        SELECT id, workout_num, old_exercise, new_exercise
        FROM replacements
        WHERE is_active = 1
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()

    if not row:
        await message.answer("Нет активных замен для отмены.")
        return

    replacement_id, workout_num, old_exercise, new_exercise = row

    cursor.execute("""
        UPDATE replacements
        SET is_active = 0
        WHERE id = ?
    """, (replacement_id,))

    cursor.execute("""
        INSERT INTO deleted_replacements (workout_num, old_exercise, new_exercise)
        VALUES (?, ?, ?)
    """, (workout_num, old_exercise, new_exercise))

    db.commit()

    await message.answer(
        "↩️ Последняя замена отменена:\n\n"
        f"Тренировка {workout_num}\n"
        f"{new_exercise} снова заменено на {old_exercise}"
    )
text = (
    "📋 Доступные команды:\n\n"

    "🏋️ Тренировки:\n"
    "/workout 1\n"
    "/workout 2\n"
    "/workout 3\n"
    "/workout 4\n\n"

    "➕ Добавление результатов:\n"
    "/add 1 жим лежа 60x10\n\n"

    "❌ Удаление:\n"
    "/delete\n\n"

    "📅 Сегодня:\n"
    "/today\n\n"

    "📈 История упражнения:\n"
    "/history жим лежа\n\n"

    "🔄 Замена упражнения:\n"
    "/replace 1 Скамья Скотта Молотки\n"
    "/undo_replace\n\n"

    "🏁 Завершить тренировку:\n"
    "/finish\n\n"

    "🏆 Личные рекорды:\n"
    "/pr"
)
@dp.message(Command("finish"))
async def finish_workout(message: Message):
    workout_num = message.text.replace("/finish", "").strip()

    if workout_num not in ["1", "2", "3", "4"]:
        await message.answer("Формат: /finish 1")
        return

    today = datetime.now().strftime("%d.%m.%Y")

    cursor.execute("""
        SELECT exercise, weight, reps
        FROM workouts
        WHERE workout_num = ? AND date = ?
        ORDER BY id
    """, (workout_num, today))

    rows = cursor.fetchall()

    if not rows:
        await message.answer(f"Сегодня для тренировки {workout_num} ещё нет записей.")
        return

    text = f"🏁 Тренировка {workout_num} завершена!\n\n"

    for exercise, weight, reps in rows:
        if weight == "0":
            text += f"• {exercise}: {reps}\n"
        else:
            text += f"• {exercise}: {weight}×{reps}\n"

    text += (
        "\n\n"
        "🔥 ЕБАТЬ ТИГР КРАСАВА ВАЩЕ 🔥\n"
        "ТУПО ДУШУ ТВОЮ ЦЕЛОВАЛ 😘\n"
        "КЛАСНО ПОТРЕНИЛ МАЛЬЧИК МОЙ 💪😎"
    )

    await message.answer(text)

@dp.message(Command("pr"))
async def personal_records(message: Message):
    cursor.execute("""
        SELECT exercise, weight, reps
        FROM workouts
    """)

    rows = cursor.fetchall()

    if not rows:
        await message.answer("Пока нет записей для PR.")
        return

    records = {}

    for exercise, weight, reps in rows:
        try:
            weight_num = float(str(weight).replace(",", "."))
            reps_num = int(reps)
        except ValueError:
            continue

        score = weight_num * reps_num

        if exercise not in records or score > records[exercise]["score"]:
            records[exercise] = {
                "weight": weight,
                "reps": reps,
                "score": score
            }

    text = "🏆 Твои личные рекорды:\n\n"

    for exercise, data in records.items():
        text += f"{exercise}: {data['weight']}×{data['reps']}\n"

    await message.answer(text)
    async def check_missed_workouts():
        while True:
            today = datetime.now()
            today_text = today.strftime("%d.%m.%Y")

        cursor.execute("""
            SELECT DISTINCT user_id
            FROM workouts
            WHERE user_id IS NOT NULL
        """)
        users = cursor.fetchall()

        for (user_id,) in users:
            cursor.execute("""
                SELECT date
                FROM workouts
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (user_id,))

            row = cursor.fetchone()

            if not row:
                continue

            last_date = datetime.strptime(row[0], "%d.%m.%Y")
            days_missed = (today - last_date).days

            if days_missed < 3:
                continue

            cursor.execute("""
                SELECT last_reminder_date
                FROM reminder_log
                WHERE user_id = ?
            """, (user_id,))

            reminder = cursor.fetchone()

            if reminder and reminder[0] == today_text:
                continue

            await bot.send_message(
                user_id,
                f"ТЫ ГДЕ ПРОПАЛ, ЧЕМПИОН? 🐯\n\n"
                f"Последняя тренировка была {days_missed} дня назад.\n"
                f"Пора возвращаться в зал 💪"
            )

            cursor.execute("""
                INSERT OR REPLACE INTO reminder_log (user_id, last_reminder_date)
                VALUES (?, ?)
            """, (user_id, today_text))

            db.commit()

        await asyncio.sleep(60 * 60 * 12)

@dp.message(Command("commands"))
async def commands(message: Message):
    await message.answer(
        "📋 Команды:\n\n"
        "/workout — выбрать тренировку\n"
        "/add — добавить результат\n"
        "/delete — удалить последнюю запись\n"
        "/replace — заменить упражнение\n"
        "/undo_replace — отменить замену упражнения\n"
        "/undo — отменить замену упражнения сегодня\n"
        "/finish — завершить тренировку\n"
        "/pr — личные рекорды\n"
        "/commands — список команд\n"
    )

@dp.message(Command("replace_today"))
async def replace_today(message: Message):
    text = message.text.replace("/replace_today", "").strip()
    parts = [p.strip() for p in text.split("|")]

    if len(parts) != 3:
        await message.answer(
            "Формат:\n"
            "/replace_today 1 | Скамья Скотта | Сгибания на блоке"
        )
        return

    workout_num, old_exercise, new_exercise = parts

    cursor.execute("""
        INSERT INTO temp_replacements (workout_num, old_exercise, new_exercise)
        VALUES (?, ?, ?)
    """, (workout_num, old_exercise.lower(), new_exercise))

    db.commit()

    await message.answer(
        f"✅ Замена на сегодня:\n{old_exercise} → {new_exercise}"
    )
@dp.message(Command("undo"))
async def undo_replace(message: Message):
    cursor.execute("""
        SELECT id, old_exercise
        FROM temp_replacements
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()

    if not row:
        await message.answer("Нечего отменять.")
        return

    cursor.execute(
        "DELETE FROM temp_replacements WHERE id = ?",
        (row[0],)
    )

    db.commit()

    await message.answer(f"↩️ Вернул: {row[1]}")
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
