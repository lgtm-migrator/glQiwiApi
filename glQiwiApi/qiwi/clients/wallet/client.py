"""
Gracefully and lightweight wrapper to deal with QIWI API
It's an open-source project so you always can improve the quality of code/API by
adding something of your own...
Easy to integrate to Telegram bot, which was written on aiogram or another async/sync library.

"""
from __future__ import annotations

from contextlib import suppress
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from glQiwiApi.base.types.amount import AmountWithCurrency
from glQiwiApi.base.types.arbitrary import File
from glQiwiApi.core.abc.wrapper import Wrapper
from glQiwiApi.core.request_service import RequestService
from glQiwiApi.core.session.holder import AbstractSessionHolder
from glQiwiApi.ext.webhook_url import WebhookURL
from glQiwiApi.qiwi.clients.wallet.methods.authenticate_wallet import AuthenticateWallet
from glQiwiApi.qiwi.clients.wallet.methods.buy_qiwi_card import BuyQiwiCard
from glQiwiApi.qiwi.clients.wallet.methods.buy_qiwi_master import BuyQIWIMaster
from glQiwiApi.qiwi.clients.wallet.methods.check_restriction import GetRestrictions
from glQiwiApi.qiwi.clients.wallet.methods.confirm_qiwi_master_request import ConfirmQiwiMasterRequest
from glQiwiApi.qiwi.clients.wallet.methods.create_new_balance import CreateNewBalance
from glQiwiApi.qiwi.clients.wallet.methods.detect_mobile_number import DetectMobileNumber
from glQiwiApi.qiwi.clients.wallet.methods.fetch_statistics import FetchStatistics
from glQiwiApi.qiwi.clients.wallet.methods.get_account_info import GetAccountInfo
from glQiwiApi.qiwi.clients.wallet.methods.get_available_balances import GetAvailableBalances
from glQiwiApi.qiwi.clients.wallet.methods.get_balance import GetBalance
from glQiwiApi.qiwi.clients.wallet.methods.get_balances import GetBalances
from glQiwiApi.qiwi.clients.wallet.methods.get_card_id import GetCardID
from glQiwiApi.qiwi.clients.wallet.methods.get_cards import GetBoundedCards
from glQiwiApi.qiwi.clients.wallet.methods.get_cross_rates import GetCrossRates
from glQiwiApi.qiwi.clients.wallet.methods.get_identification import GetIdentification
from glQiwiApi.qiwi.clients.wallet.methods.get_limits import GetLimits, ALL_LIMIT_TYPES
from glQiwiApi.qiwi.clients.wallet.methods.get_receipt import GetReceipt
from glQiwiApi.qiwi.clients.wallet.methods.history import MAX_HISTORY_LIMIT, GetHistory
from glQiwiApi.qiwi.clients.wallet.methods.list_of_invoices import GetListOfInvoices
from glQiwiApi.qiwi.clients.wallet.methods.pay_invoice import PayInvoice
from glQiwiApi.qiwi.clients.wallet.methods.payment_by_details import MakePaymentByDetails
from glQiwiApi.qiwi.clients.wallet.methods.pre_qiwi_master import PreQIWIMasterRequest
from glQiwiApi.qiwi.clients.wallet.methods.predict_comission import PredictCommission
from glQiwiApi.qiwi.clients.wallet.methods.set_default_balance import SetDefaultBalance
from glQiwiApi.qiwi.clients.wallet.methods.transaction_info import GetTransactionInfo
from glQiwiApi.qiwi.clients.wallet.methods.transfer_money import TransferMoney
from glQiwiApi.qiwi.clients.wallet.methods.transfer_money_to_card import TransferMoneyToCard
from glQiwiApi.qiwi.clients.wallet.methods.webhook.change_webhook_secret import GenerateWebhookSecret
from glQiwiApi.qiwi.clients.wallet.methods.webhook.delete_current_webhook import DeleteWebhook
from glQiwiApi.qiwi.clients.wallet.methods.webhook.get_current_webhook import GetCurrentWebhook
from glQiwiApi.qiwi.clients.wallet.methods.webhook.get_webhook_secret import GetWebhookSecret
from glQiwiApi.qiwi.clients.wallet.methods.webhook.register_webhook import RegisterWebhook
from glQiwiApi.qiwi.clients.wallet.methods.webhook.send_test_notification import SendTestWebhookNotification
from glQiwiApi.qiwi.exceptions import APIError
from glQiwiApi.utils.helper import allow_response_code, override_error_message
from glQiwiApi.utils.payload import (
    is_transaction_exists_in_history,
)
from glQiwiApi.utils.validators import PhoneNumber, String
from .types import (
    CrossRate, PaymentDetails, OrderDetails, PaymentInfo, PaymentMethod, QiwiAccountInfo,
    Restriction, Statistic, Transaction, TransactionType, WebhookInfo, Limit, Balance, Card, Identification,
    Commission, History, Source
)
from ..p2p.types import Bill, InvoiceStatus

AmountType = Union[int, float]

ERROR_CODE_MATCHES = {
    400: "Query syntax error (invalid data format). Can be related to wrong arguments,"
         " that you have passed to method",
    401: "Invalid token or API token was expired",
    403: "No permission for this request(API token has insufficient permissions)",
    404: "Object was not found or there are no objects with the specified characteristics",
    423: "Too many requests, the service is temporarily unavailable",
    422: "The domain / subnet / host is incorrectly specified"
         "webhook (in the new_url parameter for the webhook URL),"
         "the hook type or transaction type is incorrectly specified,"
         "an attempt to create a hook if there is one already created",
    405: "Error related to the type of API request, contact the developer or open an issue",
    500: "Internal service error",
    0: "An error related to using a proxy or library problems",
}


class QiwiWallet(Wrapper):
    # declarative validators for fields
    phone_number = PhoneNumber(maxsize=15, minsize=11, optional=True)
    _api_access_token = String(optional=False)

    def __init__(
            self,
            api_access_token: str,
            phone_number: Optional[str] = None,
            cache_time_in_seconds: Union[float, int] = 0,
            session_holder: Optional[AbstractSessionHolder[Any]] = None
    ) -> None:
        """
        :param api_access_token: QIWI API token received from https://qiwi.com/api
        :param phone_number: your phone number starting with +
        :param cache_time_in_seconds: Time to cache requests in seconds,
                           default 0, respectively the request will not use the cache by default
        :param session_holder: obtains session and helps to manage session lifecycle. You can pass
                               your own session holder, for example using httpx lib and use it
        """
        self.phone_number = phone_number
        self._api_access_token = api_access_token

        self._request_service = RequestService(
            error_messages=ERROR_CODE_MATCHES,
            cache_time=cache_time_in_seconds,
            session_holder=session_holder,
            base_headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self._api_access_token}",
                "Host": "edge.qiwi.com",
            }
        )

    async def register_webhook(self, url: str, txn_type: int = 2) -> WebhookInfo:
        """
        This method register a new webhook

        :param url: service url
        :param txn_type:  0 => incoming, 1 => outgoing, 2 => all
        :return: Active Hooks
        """
        return await self._request_service.emit_request_to_api(
            RegisterWebhook(webhook_url=url, txn_type=txn_type)
        )

    async def get_current_webhook(self) -> WebhookInfo:
        """
        List of active (active) notification handlers, associated with your wallet can be obtained with this request.
        Since now only one type of hook is used - webhook, then the response contains only one data object
        """
        return await self._request_service.emit_request_to_api(GetCurrentWebhook())

    async def send_test_webhook_notification(self) -> Dict[Any, Any]:
        """
        Use this request to test your webhooks handler.
        Test notification is sent to the address specified during the call register_webhook
        """
        return await self._request_service.emit_request_to_api(SendTestWebhookNotification())

    async def get_webhook_secret_key(self, hook_id: str) -> str:
        """
        Each notification contains a digital signature of the message, encrypted with a key.
        To obtain a signature verification key, use this request.

        :param hook_id: UUID of webhook
        :return: Base64 encoded key
        """
        return await self._request_service.emit_request_to_api(GetWebhookSecret(hook_id=hook_id))

    async def delete_current_webhook(self) -> Dict[Any, Any]:
        """Method to delete webhook"""
        try:
            hook = await self.get_current_webhook()
        except APIError as ex:
            raise APIError(
                message=" You didn't register any webhook to delete ",
                status_code="422",
                request_data=ex.request_data,
            ) from None
        return await self._request_service.emit_request_to_api(DeleteWebhook(hook_id=hook.id))

    async def generate_new_webhook_secret(self, hook_id: str) -> str:
        """
        Use this request to change the encryption key for notifications.

        :param hook_id: UUID of webhook
        :return: Base64 encoded key
        """
        return await self._request_service.emit_request_to_api(GenerateWebhookSecret(hook_id=hook_id))

    async def bind_webhook(
            self,
            url: Union[str, WebhookURL],
            *,
            transactions_type: int = 2,
            send_test_notification: bool = False,
            delete_old: bool = False,
    ) -> Tuple[WebhookInfo, str]:
        """
        [NON-API] EXCLUSIVE method to register new webhook or get old

        :param url: service url
        :param transactions_type: 0 => incoming, 1 => outgoing, 2 => all
        :param send_test_notification:  test_qiwi will transfer_money
         you test webhook update
        :param delete_old: boolean, if True - delete old webhook

        :return: Tuple of Hook and Base64-encoded key
        """
        if isinstance(url, WebhookURL):
            url = url.render()

        if delete_old:
            with suppress(APIError):
                await self.delete_current_webhook()

        webhook = await self.register_webhook(url, transactions_type)
        key = await self.get_webhook_secret_key(webhook.id)

        if send_test_notification is True:
            await self.send_test_webhook_notification()

        return webhook, key

    @override_error_message(
        {
            404: {
                "message": "Wrong card number entered, possibly"
                           "the card to which you transfer is blocked"
            }
        }
    )
    async def _detect_mobile_number(self, phone_number: str) -> str:
        """https://developer.qiwi.com/ru/qiwi-wallet-personal/?python#search-providers"""
        return await self._request_service.emit_request_to_api(DetectMobileNumber(phone_number=phone_number))

    async def get_balance(self, *, account_number: int = 1) -> AmountWithCurrency:
        resp: List[Balance] = await self._request_service.emit_request_to_api(
            GetBalance(account_number=account_number),
            phone_number=self.phone_number,
        )
        return resp[account_number - 1].balance

    async def history(
            self,
            rows: int = MAX_HISTORY_LIMIT,
            transaction_type: TransactionType = TransactionType.ALL,
            sources: Optional[List[Source]] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
    ) -> History:
        """
        Method for receiving transactions history on the account
        More detailed documentation:
        https://developer.qiwi.com/ru/qiwi-wallet-personal/?http#payments_list

        :param rows: number of operation_history you want to receive
        :param transaction_type: The type of operations in the report for selection.
        :param sources: List of payment sources, for filter
        :param start_date: The starting date for searching for payments. Used only in conjunction with end_date.
        :param end_date: the end date of the search for payments. Used only in conjunction with start_date.
        """
        return await self._request_service.emit_request_to_api(
            GetHistory(
                rows=rows,
                transaction_type=transaction_type,
                sources=sources,
                start_date=start_date,
                end_date=end_date
            ),
            phone_number=self.phone_number_without_plus_sign
        )

    async def transaction_info(
            self, transaction_id: Union[str, int], transaction_type: TransactionType
    ) -> Transaction:
        """
        Method for obtaining complete information about a transaction

        Detailed documentation:
        https://developer.qiwi.com/ru/qiwi-wallet-personal/?python#txn_info

        :param transaction_id:
        :param transaction_type: only IN or OUT
        :return: Transaction object
        """
        return await self._request_service.emit_request_to_api(
            GetTransactionInfo(transaction_id=transaction_id, transaction_type=transaction_type),
            transaction_id=transaction_id,
        )

    async def get_restrictions(self) -> List[Restriction]:
        """
        Method to check limits on your qiwi wallet
        Detailed documentation:
        https://developer.qiwi.com/ru/qiwi-wallet-personal/?python#restrictions

        :return: List where the dictionary is located with restrictions,
         if there are no restrictions, it returns an empty list
        """
        return await self._request_service.emit_request_to_api(
            GetRestrictions(),
            phone_number=self.phone_number_without_plus_sign,
        )

    async def get_identification(self) -> Identification:
        """
        This method allows get your wallet identification data
        More detailed documentation:
        https://developer.qiwi.com/ru/qiwi-wallet-personal/?http#ident
        """
        return await self._request_service.emit_request_to_api(
            GetIdentification(),
            phone_number=self.phone_number,
        )

    async def check_transaction(
            self,
            amount: AmountType,
            transaction_type: TransactionType = TransactionType.IN,
            sender: Optional[str] = None,
            rows_num: int = 50,
            comment: Optional[str] = None,
    ) -> bool:
        """
        [ NON API METHOD ]

        Method for verifying a transaction.
        This method uses self.history (rows = rows) "under the hood" to check payment.

        For a little optimization, you can decrease rows by setting it,
        however, this does not guarantee the correct result

        Possible values for the transaction_type parameter:
         - 'IN'
         - 'OUT'
         - 'QIWI_CARD'


        :param amount: amount of payment
        :param transaction_type: type of payment
        :param sender: number of receiver
        :param rows_num: number of payments to be checked
        :param comment: comment by which the transaction will be verified
        """
        history = await self.history(rows=rows_num)
        return is_transaction_exists_in_history(
            history=history,
            transaction_type=transaction_type,
            comment=comment,
            amount=amount,
            sender=sender,
        )

    async def get_limits(self, limit_types: List[str] = ALL_LIMIT_TYPES) -> Dict[str, Limit]:
        """
        Function for getting limits on the qiwi wallet account
        Returns wallet limits as a list,
        if there is no limit for a certain country, then it does not include it in the list
        payload of limit types must be dict in format like array of strings {
            "types[0]": "Some type",
            "types[1]": "some other type",
            "types[n]": "n type"
        }

        Detailed documentation:

        https://developer.qiwi.com/ru/qiwi-wallet-personal/?http#limits
        """
        phone_number_without_plus_sign = self.phone_number[1:]

        return await self._request_service.emit_request_to_api(
            GetLimits(limit_types=limit_types),
            phone_number=phone_number_without_plus_sign
        )

    async def get_list_of_cards(self) -> List[Card]:
        return await self._request_service.emit_request_to_api(GetBoundedCards())

    async def authenticate(
            self,
            birth_date: str,
            first_name: str,
            last_name: str,
            middle_name: str,
            passport: str,
            oms: Optional[str] = None,
            inn: Optional[str] = None,
            snils: Optional[str] = None,
    ) -> Dict[Any, Any]:
        """
        This request allows you to transfer data to identify your QIWI wallet.
        It is allowed to identify no more than 5 wallets per owner

        To identify the wallet, you must transfer your full name, passport series number and date of birth.
        If the data has been verified, then the response will display
        your TIN and simplified wallet identification will be installed.
        If the data has not been verified,
        the wallet remains in the "Minimum" status.

        :param birth_date: Date of birth as a format string 1998-02-11
        :param first_name: First name
        :param last_name: Last name
        :param middle_name: Middle name
        :param passport: Series / Number of the passport. Ex: 4400111222
        :param oms:
        :param snils:
        :param inn:
        """
        return await self._request_service.emit_request_to_api(
            AuthenticateWallet(
                birth_date=birth_date,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                passport=passport,
                oms=oms,
                inn=inn,
                snils=snils
            )
        )

    @override_error_message(
        {
            422: {
                "message": "It is impossible to receive a check due to the fact that "
                           "the transaction for this ID has not been completed,"
                           "that is, an error occurred during the transaction"
            }
        }
    )
    async def get_receipt(
            self,
            transaction_id: Union[str, int],
            transaction_type: TransactionType,
            file_format: str = "PDF",
    ) -> File:
        """
        Method for receiving a receipt in byte format or file. \n
        Possible transaction_type values:
         - 'IN'
         - 'OUT'
         - 'QIWI_CARD'

        :param transaction_id: transaction id, can be obtained by calling the transfer_money method,
         transfer_money_to_card
        :param transaction_type: type of transaction: 'IN', 'OUT', 'QIWI_CARD'
        :param file_format: format of file(JPEG or PDF)
        """
        return await self._request_service.emit_request_to_api(
            GetReceipt(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                file_format=file_format
            )
        )

    async def get_account_info(self) -> QiwiAccountInfo:
        """
        Метод для получения информации об аккаунте

        """
        return await self._request_service.emit_request_to_api(GetAccountInfo())

    async def fetch_statistics(
            self,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            operation: TransactionType = TransactionType.ALL,
            sources: Optional[List[str]] = None,
    ) -> Statistic:
        """
        This query is used to get summary statistics
        by the amount of payments for a given period.
        More detailed documentation:
        https://developer.qiwi.com/ru/qiwi-wallet-personal/?http#payments_list

        :param start_date:The start date of the statistics period.
        :param end_date: End date of the statistics period.
        :param operation: The type of operations taken into account when calculating statistics.
         Allowed values:
            ALL - все операции,
            IN - только пополнения,
            OUT - только платежи,
            QIWI_CARD - только платежи по картам QIWI (QVC, QVP).
            По умолчанию ALL.
        :param sources: The sources of payments
            QW_RUB - рублевый счет кошелька,
            QW_USD - счет кошелька в долларах,
            QW_EUR - счет кошелька в евро,
            CARD - привязанные и непривязанные к кошельку банковские карты,
            MK - счет мобильного оператора. Если не указан,
            учитываются все источники платежа.
        """
        kw = {
            "start_date": start_date,
            "end_date": end_date,
            "operation": operation,
            "sources": sources
        }

        return await self._request_service.emit_request_to_api(
            FetchStatistics(**{k: v for k, v in kw.items() if v is not None}),
            phone_number=self.phone_number_without_plus_sign
        )

    async def list_of_balances(self) -> List[Balance]:
        """
        The request gets the current account balances of your QIWI Wallet.
        More detailed documentation:
        https://developer.qiwi.com/ru/qiwi-wallet-personal/?http#balances_list

        """
        return await self._request_service.emit_request_to_api(
            GetBalances(),
            phone_number=self.phone_number_without_plus_sign
        )

    @allow_response_code(201)
    async def create_new_balance(self, currency_alias: str) -> Dict[str, bool]:
        """
        The request creates a new account and balance in your QIWI Wallet

        :param currency_alias: New account alias
        """
        return await self._request_service.emit_request_to_api(
            CreateNewBalance(currency_alias=currency_alias),
            phone_number=self.phone_number_without_plus_sign
        )

    async def available_balances(self) -> List[Balance]:
        """
        The request displays account aliases, available for creation in your QIWI Wallet

        """
        return await self._request_service.emit_request_to_api(
            GetAvailableBalances(),
            phone_number=self.phone_number_without_plus_sign
        )

    @allow_response_code(204)
    async def set_default_balance(self, currency_alias: str) -> Dict[Any, Any]:
        """
        The request sets up an account for your QIWI Wallet, whose balance will be used for funding
        all payments by default.
        The account must be contained in the list of accounts, you can get the list by calling
        list_of_balances method

        :param currency_alias:
        """
        return await self._request_service.emit_request_to_api(
            SetDefaultBalance(
                currency_alias=currency_alias
            )
        )

    @override_error_message({400: {"message": "Not enough funds to execute this operation"}})
    async def transfer_money(
            self,
            to_phone_number: str,
            amount: Union[AmountType, str],
            comment: Optional[str] = None,
    ) -> PaymentInfo:
        """
        Method for transferring funds to wallet

        Detailed documentation:
        https://developer.qiwi.com/ru/qiwi-wallet-personal/?python#p2p

        :param to_phone_number: recipient number
        :param amount: the amount of money you want to transfer
        :param comment: payment comment
        """
        return await self._request_service.emit_request_to_api(
            TransferMoney(
                amount=amount,
                comment=comment,
                to_wallet=to_phone_number
            )
        )

    async def transfer_money_to_card(self, amount: AmountType, card_number: str) -> PaymentInfo:
        """
        Method for sending funds to the card.

        More detailed documentation:
        https://developer.qiwi.com/ru/qiwi-wallet-personal/#cards
        """
        private_card_id = await self.get_card_id(card_number=card_number)
        return await self._request_service.emit_request_to_api(
            TransferMoneyToCard(
                private_card_id=private_card_id,
                amount=amount,
                card_number=card_number
            )
        )

    async def get_card_id(self, card_number: str) -> str:
        """
        Method for getting card ID

        https://developer.qiwi.com/ru/qiwi-wallet-personal/?python#cards
        """
        return await self._request_service.emit_request_to_api(GetCardID(card_number=card_number))

    async def predict_commission(self, to_account: str, invoice_amount: AmountType) -> Commission:
        """
        Full calc_commission of QIWI Wallet is refunded for payment in favor of the specified provider
        taking into account all tariffs for a given set of payment details.

        :param to_account:
        :param invoice_amount:
        :return: Commission object
        """
        card_code = "99" if len(to_account) <= 15 else None
        if not card_code:
            card_code = await self.get_card_id(to_account)

        return await self._request_service.emit_request_to_api(
            PredictCommission(
                private_card_id=card_code,
                invoice_amount=invoice_amount,
                to_account=to_account
            )
        )

    async def get_cross_rates(self) -> List[CrossRate]:
        """
        The method returns the current exchange rates and cross-rates of the QIWI Bank's currencies.

        """
        return await self._request_service.emit_request_to_api(GetCrossRates())

    async def payment_by_payment_details(
            self,
            payment_sum: AmountWithCurrency,
            payment_method: PaymentMethod,
            fields: PaymentDetails,
            payment_id: Optional[str] = None,
    ) -> PaymentInfo:
        """
        Payment for services of commercial organizations according to their bank details.

        :param payment_id: payment id, if not transmitted, is used uuid4 by default
        :param payment_sum: a Sum object, which indicates the amount of the payment
        :param payment_method: payment method
        :param fields: payment details
        """
        return await self._request_service.emit_request_to_api(
            MakePaymentByDetails(
                payment_sum=payment_sum,
                payment_method=payment_method,
                details=fields,
                payment_id=payment_id
            )
        )

    async def buy_qiwi_master(self) -> PaymentInfo:
        """
        Method for buying QIWI Master package
        To call API methods, you need the QIWI Wallet API token with permissions to do the following:
        1. Management of virtual cards,
        2. Request information about the wallet profile,
        3. View payment history,
        4. Making payments without SMS.
        You can choose these rights when creating a new api token, to use api QIWI Master
        """
        return await self._request_service.emit_request_to_api(BuyQIWIMaster(phone_number=self.phone_number))

    async def issue_qiwi_master_card(self, card_alias: str = "qvc-cpa") -> Optional[OrderDetails]:
        """
        Issuing a new card using the Qiwi Master API

        When issuing a card, 3, and possibly 3 requests are made, namely,
        according to the following scheme:
            - _pre_qiwi_master_request - this method creates a request
            - _confirm_qiwi_master_request - confirms the issue of the card
            - _buy_new_qiwi_card - buys a new card,
              if such a card is not free
        Detailed documentation:
        https://developer.qiwi.com/ru/qiwi-wallet-personal/#qiwi-master-issue-card
        """
        pre_response = await self._confirm_qiwi_master_request(card_alias)
        if pre_response.status == "COMPLETED":
            return pre_response
        return await self._buy_new_qiwi_card(
            ph_number=self.phone_number, order_id=pre_response.order_id
        )

    async def _pre_qiwi_master_request(self, card_alias: str = "qvc-cpa") -> OrderDetails:
        """Method for Issuing QIWI Master Virtual Card"""
        return await self._request_service.emit_request_to_api(PreQIWIMasterRequest(
            card_alias=card_alias
        ), phone_number=self.phone_number_without_plus_sign)

    async def _confirm_qiwi_master_request(self, card_alias: str = "qvc-cpa") -> OrderDetails:
        """Confirmation of the card issue order"""
        details = await self._pre_qiwi_master_request(card_alias)
        return await self._request_service.emit_request_to_api(
            ConfirmQiwiMasterRequest(order_id=details.order_id)
        )

    async def _buy_new_qiwi_card(self, **kwargs: Any) -> Optional[OrderDetails]:
        return await self._request_service.emit_request_to_api(BuyQiwiCard(**kwargs))

    async def list_of_invoices(self, rows: int, statuses: str = "READY_FOR_PAY") -> List[Bill]:
        """
        A method for getting a list of your wallet's outstanding bills.

        The list is built in reverse chronological order.

        By default, the list is paginated with 50 items each,
        but you can specify a different number of elements (no more than 50).

        Filters by billing time can be used in the request,
        the initial account identifier.
        """
        return await self._request_service.emit_request_to_api(
            GetListOfInvoices(rows=rows, statuses=statuses)
        )

    async def pay_the_invoice(self, invoice_uid: str, currency: str) -> InvoiceStatus:
        """
        Execution of unconditional payment of the invoice without SMS-confirmation.

        ! Warning !
        To use this method correctly you need to tick "Проведение платежей без SMS"
        when registering QIWI API and retrieve token

        :param invoice_uid: Bill ID in QIWI system
        :param currency:
        """
        return await self._request_service.emit_request_to_api(
            PayInvoice(invoice_uid=invoice_uid, currency=currency)
        )

    @property
    def phone_number_without_plus_sign(self) -> str:
        if self.phone_number is None:
            raise RuntimeError("Phone number is empty")
        return self.phone_number[1:]