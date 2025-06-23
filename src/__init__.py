#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
from datetime import datetime

from pytdbot import Client, types

from src.config import config
from src.modules.jobs import InactiveCallManager
from src.helpers import call, db, start_clients, save_all_cookies, i18n

__version__ = "1.2.1"

StartTime = datetime.now()



class Telegram(Client):
    """Main Telegram bot client with extended functionality."""
    def __init__(self) -> None:
        super().__init__(
            token=config.TOKEN,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            default_parse_mode="html",
            td_verbosity=2,
            td_log=types.LogStreamEmpty(),
            plugins=types.plugins.Plugins(folder="src/modules"),
            files_directory="",
            database_encryption_key="",
            options={"ignore_background_updates": config.IGNORE_BACKGROUND_UPDATES},
        )

        self.call_manager = InactiveCallManager(self)
        self.db = db

    async def start(self) -> None:
        """Start the bot and all associated services."""
        await i18n.load_translations()
        await save_all_cookies(config.COOKIES_URL)
        await self.db.ping()
        await start_clients()
        await call.add_bot(self)
        await call.register_decorators()
        await super().start()
        await self.call_manager.start_scheduler()
        uptime = (datetime.now() - StartTime).total_seconds()
        self.logger.info(f"Bot started in {uptime:.2f} seconds")
        self.logger.info(f"Version: {__version__}")

    async def stop(self) -> None:
        """Gracefully shutdown the bot and all services."""
        await asyncio.gather(
            self.db.close(),
            self.call_manager.stop_scheduler(),
            super().stop(),
        )


client: Telegram = Telegram()
