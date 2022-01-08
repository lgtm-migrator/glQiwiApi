from typing import Optional

from pydantic import Field, validator

from glQiwiApi.base_types.amount import AmountWithCurrency, CurrencyModel, Type
from glQiwiApi.base_types.base import HashableBase
from glQiwiApi.utils.currency_util import Currency


class Account(HashableBase):
    """object: Account"""

    alias: str
    title: str
    fs_alias: str = Field(alias="fsAlias")
    bank_alias: str = Field(alias="bankAlias")
    has_balance: bool = Field(alias="hasBalance")
    balance: Optional[AmountWithCurrency] = None
    currency: CurrencyModel
    account_type: Optional[Type] = Field(None, alias="type")
    is_default_account: bool = Field(alias="defaultAccount")

    @validator("currency", pre=True)
    def humanize_pay_currency(cls, v):  # type: ignore
        if not isinstance(v, int):
            return v
        return Currency.get(str(v))


__all__ = "Account"
