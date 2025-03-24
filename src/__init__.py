from pyrogram import Client, enums

import config
from src.database import db
from src.modules.jobs import InactiveCallManager
from src.pytgcalls import call, start_clients

__version__ = "1.0.0"


class Telegram(Client):
    def __init__(self) -> None:
        self._check_config()
        super().__init__(
            name="TgMusic",
            bot_token=config.TOKEN,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            plugins={"root": "src.modules"},
            workers=5,
            parse_mode=enums.ParseMode.DEFAULT,
        )
        self.call_manager = InactiveCallManager(self)
        self.db = db

    async def start(self, use_qr=False, except_ids=None) -> None:
        await self.db.ping()
        await start_clients()
        await call.add_bot(self)
        await call.register_decorators()
        await self.call_manager.start_scheduler()
        await super().start(use_qr, except_ids)

    async def stop(self, block=True) -> None:
        await self.db.close()
        await self.call_manager.stop_scheduler()
        await super().stop(block)

    @staticmethod
    def _check_config() -> None:
        if not isinstance(config.MONGO_URI, str):
            raise TypeError("MONGO_URI must be a string")

        session_strings = [s for s in config.SESSION_STRINGS if s]
        if not session_strings:
            raise ValueError("No STRING session provided\n\nAdd STRING session in .env")


client = Telegram()
