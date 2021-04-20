from typing import Dict, Optional, Any, Union

import aiohttp

import glQiwiApi
from glQiwiApi.core.basic_requests_api import SimpleCache, HttpXParser
from glQiwiApi.types import Response
from glQiwiApi.types.basics import CachedResponse
from glQiwiApi.utils.exceptions import RequestError


class CustomParser(HttpXParser):
    """
    Немного переделанный дочерний класс HttpXParser
    под платежные системы и кэширование запросов

    """
    __slots__ = ('_without_context', 'messages', '_cache')

    def __init__(
            self,
            without_context: bool = False,
            messages: Optional[Dict[str, str]] = None,
            cache_time: Union[float, int] = 0
    ) -> None:
        super(CustomParser, self).__init__()
        self._without_context = without_context
        self.messages = messages
        self._cache = SimpleCache(cache_time)
        self._cached_key = "session"

    def clear_cache(self) -> None:
        self._cache.clear(force=True)

    def get_cached_session(self) -> Optional[aiohttp.ClientSession]:
        cached = self._cache[self._cached_key]
        if self.check_session(cached):
            return cached

    def set_cached_session(self):
        cached_session = self.get_cached_session()
        if cached_session:
            self.session = cached_session

    async def _request(self, *args, **kwargs) -> Response:
        # Получаем текущий кэш используя ссылку как ключ
        response = self._cache.get_current(kwargs.get('url'))
        if not self._cache.validate(kwargs):
            self.set_cached_session()
            response = await super()._request(*args, **kwargs)
        # Проверяем, не был ли запрос в кэше, если нет,
        # то проверяем статус код и если он не 200 - выбрасываем ошибку
        if not isinstance(response, CachedResponse):
            if response.status_code != 200:
                await self._close_session()
                self.raise_exception(
                    response.status_code,
                    json_info=response.response_data
                )

            await self._close_session()

        self._cache.update_data(
            result=response.response_data,
            kwargs=kwargs,
            status_code=response.status_code
        )
        self.cache_session(self.session)

        return response

    def raise_exception(
            self,
            status_code: Union[str, int],
            json_info: Optional[Dict[str, Any]] = None,
            message: Optional[str] = None
    ) -> None:
        if not isinstance(message, str):
            message = self.messages.get(str(status_code), "Unknown")
        raise RequestError(
            message,
            status_code,
            additional_info=f"{glQiwiApi.__version__} version api",
            json_info=json_info
        )

    def cache_session(self, session: aiohttp.ClientSession) -> None:
        if self.check_session(session):
            self._cache[self._cached_key] = session

    async def _close_session(self) -> None:
        if self._without_context:
            await self.session.close()

    @staticmethod
    def check_session(session: Any) -> bool:
        if isinstance(session, aiohttp.ClientSession):
            if not session.closed:
                return True
        return False

    def create_session(self, **kwargs) -> None:
        self.set_cached_session()
        super().create_session(**kwargs)

    @classmethod
    def filter_dict(cls, dictionary: dict):
        """
        Pop NoneType values and convert everything to str, designed?for=params
        :param dictionary: source dict
        :return: filtered dict
        """
        return {k: str(v) for k, v in dictionary.items() if v is not None}