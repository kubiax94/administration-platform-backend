from core.services.strapi import StrapiService
from core.settings import Settings


class ApplicationServices:
    def __init__(self, settings: Settings) -> None:
        self.strapi = StrapiService(settings)

    async def start(self) -> None:
        await self.strapi.start()

    async def stop(self) -> None:
        await self.strapi.stop()