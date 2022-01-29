from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime
from typing import Any, Dict, Optional, Union, TYPE_CHECKING, cast

from pydantic import Extra, Field, BaseConfig

from glQiwiApi.base.types.amount import HashableOptionalSum, PlainAmount
from glQiwiApi.base.types.base import HashableBase
from glQiwiApi.base.types.exceptions import WebhookSignatureUnverifiedError

if TYPE_CHECKING:
    from glQiwiApi.qiwi.clients.p2p import QiwiP2PClient  # noqa


class Customer(HashableBase):
    """Object: Customer"""

    phone: Optional[str] = None
    email: Optional[str] = None
    account: Optional[str] = None


class BillStatus(HashableBase):
    """Object: BillStatus"""

    value: str
    changed_datetime: Optional[datetime] = Field(None, alias="changedDateTime")


class CustomFields(HashableBase):
    """Object: CustomFields"""

    pay_sources_filter: Optional[str] = Field(None, alias="paySourcesFilter")
    theme_code: Optional[str] = Field(None, alias="themeCode")


class BillError(HashableBase):
    """Object: BillError"""

    service_name: str = Field(..., alias="serviceName")
    error_code: str = Field(..., alias="errorCode")
    description: str
    user_message: str = Field(..., alias="userMessage")
    datetime: str = Field(..., alias="dateTime")
    trace_id: str = Field(..., alias="traceId")


class Bill(HashableBase):
    """Object: Bill"""

    amount: HashableOptionalSum
    status: BillStatus
    site_id: str = Field(..., alias="siteId")
    id: str = Field(..., alias="billId")
    creation_date_time: datetime = Field(..., alias="creationDateTime")
    expiration_date_time: datetime = Field(..., alias="expirationDateTime")
    pay_url: str = Field(..., alias="payUrl")
    customer: Optional[Customer] = None
    custom_fields: Optional[CustomFields] = Field(None, alias="customFields")

    class Config(BaseConfig):
        extra = Extra.allow
        allow_mutation = True

    @property
    def _client(self) -> QiwiP2PClient:
        return cast(QiwiP2PClient, self._client_ctx["p2p_client"])

    @property
    def invoice_uid(self) -> str:
        return self.pay_url[-36:]

    @property
    def shim_url(self) -> str:
        if self._client._shim_server_url is None:
            raise Exception("QiwiP2PClient has no shim url -> can't create shim url for bill")

        return self._client._shim_server_url.format(self.invoice_uid)


class RefundedBill(HashableBase):
    """object: RefundedBill"""

    amount: PlainAmount
    datetime: datetime
    refund_id: str = Field(..., alias="refundId")
    status: str

    def as_str(self) -> str:
        return f"№{self.refund_id} {self.status} {self.amount} {self.datetime}"

    def get_value(self) -> Union[float, int]:
        return self.amount.value


class BillWebhookPayload(Bill):
    pay_url: None = Field(None, exclude=True)  # type: ignore


class BillWebhook(HashableBase):
    """Object: BillWebhook"""

    version: str = Field(..., alias="version")
    bill: BillWebhookPayload = Field(..., alias="bill")

    def __repr__(self) -> str:
        return f"#{self.bill.id} {self.bill.amount} {self.bill.status} "

    def verify_signature(self, sha256_signature: str, secret_p2p_key: str) -> None:
        webhook_key = base64.b64decode(bytes(secret_p2p_key, "utf-8"))
        bill = self.bill

        invoice_params = f"{bill.amount.currency}|{bill.amount.value}|{bill.id}|{bill.site_id}|{bill.status.value}"
        generated_signature = hmac.new(
            webhook_key, invoice_params.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if generated_signature != sha256_signature:
            raise WebhookSignatureUnverifiedError()


class PairOfP2PKeys(HashableBase):
    public_key: str = Field(..., alias="PublicKey")
    secret_key: str = Field(..., alias="SecretKey")


class InvoiceStatus(HashableBase):
    invoice_status: str
    is_sms_confirm: bool
    pay_results: Dict[Any, Any] = Field(..., alias="WALLET_ACCEPT_PAY_RESULT")


__all__ = (
    "Bill",
    "BillError",
    "RefundedBill",
    "BillWebhook",
    "PairOfP2PKeys",
    "InvoiceStatus",
    "BillStatus",
)