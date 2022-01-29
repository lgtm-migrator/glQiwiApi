from __future__ import annotations

import typing

from pydantic import parse_obj_as

from glQiwiApi.core.abc.wrapper import Wrapper
from glQiwiApi.core.request_service import RequestService
from glQiwiApi.core.session.holder import AbstractSessionHolder
from glQiwiApi.qiwi.clients.maps.types.polygon import Polygon
from glQiwiApi.qiwi.clients.maps.types.terminal import Terminal
from glQiwiApi.qiwi.clients.wallet.types import Partner
from glQiwiApi.utils.payload import filter_dictionary_none_values


class QiwiMaps(Wrapper):
    """
    QIWI Terminal Maps API allows you to locate
    QIWI terminals on the territory of the Russian Federation

    """

    def __init__(
            self,
            cache_time: int = 0,
            session_holder: typing.Optional[AbstractSessionHolder[typing.Any]] = None,
    ) -> None:
        self._request_service = RequestService(
            cache_time=cache_time, session_holder=session_holder
        )

    async def terminals(
            self,
            polygon: Polygon,
            zoom: typing.Optional[int] = None,
            pop_if_inactive_x_mins: int = 30,
            include_partners: typing.Optional[bool] = None,
            partners_ids: typing.Optional[typing.List[typing.Any]] = None,
            cache_terminals: typing.Optional[bool] = None,
            card_terminals: typing.Optional[bool] = None,
            identification_types: typing.Optional[int] = None,
            terminal_groups: typing.Optional[typing.List[typing.Any]] = None,
    ) -> typing.List[Terminal]:
        """
        Get map of terminals sent for passed polygon with additional params

        :param polygon: glQiwiApi.types.Polygon object
        :param zoom:
         https://tech.yandex.ru/maps/doc/staticapi/1.x/dg/concepts/map_scale-docpage/
        :param pop_if_inactive_x_mins: do not show if terminal
         was inactive for X minutes default 0.5 hours
        :param include_partners: result will include/exclude partner terminals
        :param partners_ids: Not fixed IDS array look at docs
        :param cache_terminals: result will include or exclude
         cache-acceptable terminals
        :param card_terminals: result will include or
         exclude card-acceptable terminals
        :param identification_types: `0` - not identified, `1` -
         partly identified, `2` - fully identified
        :param terminal_groups: look at QiwiMaps.partners
        :return: list of Terminal instances
        """
        params = filter_dictionary_none_values(
            {
                **polygon.dict,
                "zoom": zoom,
                "activeWithinMinutes": pop_if_inactive_x_mins,
                "withRefillWallet": include_partners,
                "ttpIds": partners_ids,
                "cacheAllowed": cache_terminals,
                "cardAllowed": card_terminals,
                "identificationTypes": identification_types,
                "ttpGroups": terminal_groups,
            }
        )
        url = "http://edge.qiwi.com/locator/v3/nearest/clusters?parameters"
        response = await self._request_service.emit_request(url, "GET", params=params)
        return parse_obj_as(typing.List[Terminal], response)

    async def partners(self) -> typing.List[Partner]:
        """
        Get terminal partners for ttpGroups
        :return: list of TTPGroups
        """
        url = "http://edge.qiwi.com/locator/v3/ttp-groups"
        response = await self._request_service.emit_request(
            url, "GET", headers={"Content-type": "text/json"}
        )
        return parse_obj_as(typing.List[Partner], response)