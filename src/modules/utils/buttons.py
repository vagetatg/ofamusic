#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.


from pytdbot import types

import config

PlayButton = types.ReplyMarkupInlineKeyboard(
        [
                [
                        types.InlineKeyboardButton(
                                text="▶️ Skip", type=types.InlineKeyboardButtonTypeCallback(b"play_skip")
                        ),
                        types.InlineKeyboardButton(
                                text="⏹️ End", type=types.InlineKeyboardButtonTypeCallback(b"play_stop")
                        ),
                ],
                [
                        types.InlineKeyboardButton(
                                text="⏸️ Pause",
                                type=types.InlineKeyboardButtonTypeCallback(b"play_pause"),
                        ),
                        types.InlineKeyboardButton(
                                text="⏯️ Resume",
                                type=types.InlineKeyboardButtonTypeCallback(b"play_resume"),
                        ),
                ],
        ]
)

PauseButton = types.ReplyMarkupInlineKeyboard(
        [
                [
                        types.InlineKeyboardButton(
                                text="▶️ Skip", type=types.InlineKeyboardButtonTypeCallback(b"play_skip")
                        ),
                        types.InlineKeyboardButton(
                                text="⏹️ End", type=types.InlineKeyboardButtonTypeCallback(b"play_stop")
                        ),
                ],
                [
                        types.InlineKeyboardButton(
                                text="⏯️ Resume",
                                type=types.InlineKeyboardButtonTypeCallback(b"play_resume"),
                        ),
                ],
        ]
)

ResumeButton = types.ReplyMarkupInlineKeyboard(
        [
                [
                        types.InlineKeyboardButton(
                                text="▶️ Skip", type=types.InlineKeyboardButtonTypeCallback(b"play_skip")
                        ),
                        types.InlineKeyboardButton(
                                text="⏹️ End", type=types.InlineKeyboardButtonTypeCallback(b"play_stop")
                        ),
                ],
                [
                        types.InlineKeyboardButton(
                                text="⏸️ Pause",
                                type=types.InlineKeyboardButtonTypeCallback(b"play_pause"),
                        ),
                ],
        ]
)

SupportButton = types.ReplyMarkupInlineKeyboard(
        [
                [
                        types.InlineKeyboardButton(
                                text="❄ Channel",
                                type=types.InlineKeyboardButtonTypeUrl(config.SUPPORT_CHANNEL),
                        ),
                        types.InlineKeyboardButton(
                                text="✨ Group",
                                type=types.InlineKeyboardButtonTypeUrl(config.SUPPORT_GROUP),
                        ),
                ]
        ]
)


def add_me_button(username: str) -> types.ReplyMarkupInlineKeyboard:
    """Create an inline keyboard with 'Add me' button using the specified username.
    Args:
        username: The bot's username (without @)

    Returns:
        types.ReplyMarkupInlineKeyboard: Configured inline keyboard markup
    """
    return types.ReplyMarkupInlineKeyboard(
            [
                    [
                            types.InlineKeyboardButton(
                                    text="Add me to your group",
                                    type=types.InlineKeyboardButtonTypeUrl(
                                            f"https://t.me/{username}?startgroup=true"
                                    ),
                            ),
                    ],
                    [
                            types.InlineKeyboardButton(
                                    text="❄ Channel",
                                    type=types.InlineKeyboardButtonTypeUrl(config.SUPPORT_CHANNEL),
                            ),
                            types.InlineKeyboardButton(
                                    text="✨ Group",
                                    type=types.InlineKeyboardButtonTypeUrl(config.SUPPORT_GROUP),
                            ),
                    ],
            ]
    )
