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
