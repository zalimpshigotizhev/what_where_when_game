main_keyboard = {
    "inline_keyboard": [
        [{"text": "🎮 Начать игру", "callback_data": "start_game"}],
        [
            {"text": "📋 Правила", "callback_data": "show_rules"},
            {"text": "⭐ Рейтинг", "callback_data": "show_rating"},
        ],
    ]
}

start_game_keyboard = {
    "inline_keyboard": [
        [{"text": "Присоединиться к игре", "callback_data": "join_game"}],
        [{"text": "Начать игру", "callback_data": "start_game_from_captain"}],
        [{"text": "Закончить игру", "callback_data": "finish_game"}],
    ]
}

are_ready_keyboard = {
    "inline_keyboard": [
        [{"text": "Готов!", "callback_data": "ready"}],
    ]
}

yes_or_no_for_dispute = {
    "inline_keyboard": [
        [{"text": "Да", "callback_data": "yes_dispute"}],
        [{"text": "Нет", "callback_data": "no_dispute"}],
    ]
}

are_ready_keyboard_or_dispute_answer = {
    "inline_keyboard": [
        [{"text": "Готов!", "callback_data": "ready"}],
        [{"text": "Оспорить прошлый ответ", "callback_data": "disput_answer"}],
    ]
}
