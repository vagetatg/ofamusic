from pyrogram import types

PlayButton = types.InlineKeyboardMarkup(
    [
        [
            types.InlineKeyboardButton(
                text="▶️ Skip", callback_data="play_skip"
            ),
            types.InlineKeyboardButton(
                text="⏹️ End", callback_data="play_stop"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text="⏸️ Pause",
                callback_data="play_pause",
            ),
            types.InlineKeyboardButton(
                text="⏯️ Resume",
                callback_data="play_resume",
            ),
        ],
    ]
)

PauseButton = types.InlineKeyboardMarkup(
    [
        [
            types.InlineKeyboardButton(
                text="▶️ Skip", callback_data="play_skip"
            ),
            types.InlineKeyboardButton(
                text="⏹️ End", callback_data="play_stop"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text="⏯️ Resume",
                callback_data="play_resume",
            ),
        ],
    ]
)

ResumeButton = types.InlineKeyboardMarkup(
    [
        [
            types.InlineKeyboardButton(
                text="▶️ Skip", callback_data="play_skip"
            ),
            types.InlineKeyboardButton(
                text="⏹️ End", callback_data="play_stop"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text="⏸️ Pause",
                callback_data="play_pause",
            ),
        ],
    ]
)

SupportButton = types.InlineKeyboardMarkup(
    [
        [
            types.InlineKeyboardButton(
                text="❄ Channel",
                url="https://t.me/FallenProjects",
            ),
            types.InlineKeyboardButton(
                text="✨ Group",
                url="https://t.me/GuardxSupport",
            ),
        ]
    ]
)

AddMeButton = types.InlineKeyboardMarkup(
    [
        [
            types.InlineKeyboardButton(
                text="Add me to your group",
                url="https://t.me/FallenBeatzBot?startgroup=true",
            ),
        ],
        [
            types.InlineKeyboardButton(
                text="❄ Channel",
                url="https://t.me/FallenProjects",
            ),
            types.InlineKeyboardButton(
                text="✨ Group",
                url="https://t.me/GuardxSupport",
            ),
        ],
    ]
)
