from datetime import datetime, timedelta
from typing import Optional, List

import requests
from prettytable import PrettyTable
from requests import Response
from ymodel.integration.warehouse_integration import OngoingIntegration

from wms import logger
from wms.common.utility import string_to_base64_string
from wms.ongoing.constants import YaylohReturnCauses
from wms.ongoing.interface import OngoingOrder, ReturnCause


class OngoingApi:
    def __init__(self, ongoing_integration: OngoingIntegration):
        self.goods_owner_id: int = ongoing_integration.goods_owner_id
        self.base_url: str = (
            f"https://api.ongoingsystems.se/{ongoing_integration.warehouse_name}/api/v1"
        )

        auth_token: str = string_to_base64_string(
            f"{ongoing_integration.username}:{ongoing_integration.password}"
        )
        self.headers = {
            "Content-type": "application/json",
            "Authorization": f"Basic {auth_token}",
        }

        self._orders: str = f"{self.base_url}/orders"
        self._return_order: str = f"{self.base_url}/returnOrders"
        self._return_causes: str = f"{self.base_url}/returnOrders/returnCauses"

    def get_order(self, order_id: int) -> OngoingOrder:
        resp = self._make_request("get", f"{self._orders}/{order_id}")
        logger.info(f"get_order {resp.json()=}")
        return OngoingOrder(resp.json())

    def get_return_order(self, return_order_id: Optional[int]):
        if return_order_id is None:
            return None

        resp = self._make_request("get", f"{self._return_causes}/{return_order_id}")

        return resp.json()

    def create_return_cause(self, return_cause: ReturnCause):
        payload = {
            "goodsOwnerId": self.goods_owner_id,
            "code": return_cause.code,
            "name": return_cause.name,
            "isRemoveCause": return_cause.is_remove_cause,
            "isChangeCause": return_cause.is_change_cause,
            "isReturnCommentMandatory": return_cause.is_return_comment_mandatory,
        }

        return self._make_request("put", self._return_causes, payload=payload)

    def get_outgoing_order_between_dates(
        self, from_date: str, to_date: str
    ) -> Response:
        params = {
            "goodsOwnerId": self.goods_owner_id,
            "orderCreatedTimeFrom": from_date,
            "orderCreatedTimeTo": to_date,
        }
        logger.info(f"get_outgoing_order_between_dates {params=}")
        return self._make_request("get", self._orders, params=params)

    def get_order_by_goods_owner_order_id(
        self, ext_internal_order_id: str, order_date: str
    ) -> Optional[OngoingOrder]:
        # since Ongoing stores the Shopify Order_id and yayloh has Shopify order_number,
        # we have to search in a date range around order date
        # todo enrich service can call integration to get order object from oms integration

        order_date = datetime.strptime(order_date, "%Y-%m-%d %H:%M:%S")
        from_date: str = (order_date - timedelta(hours=12)).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )
        to_date: str = (order_date + timedelta(hours=12)).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )

        resp = self.get_outgoing_order_between_dates(from_date, to_date)
        logger.info(f"get_order_by_goods_owner_order_id {resp.json()}")
        resp.raise_for_status()

        for order_detail in resp.json():
            order = order_detail.get("orderInfo")
            if order.get("goodsOwnerOrderId") == ext_internal_order_id:
                return OngoingOrder(order_detail)

        return None

    def create_return_order(
        self, ongoing_order: OngoingOrder, return_details: List[dict]
    ):
        return_order_lines = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        comment = PrettyTable(
            ["SKU", "Return Type", "Return Reason", "Customer Comment"]
        )
        for order_line in ongoing_order.order_lines:
            order_line_return_detail = [
                return_detail
                for return_detail in return_details
                if return_detail["ext_order_detail_id"]
                == order_line.ext_order_detail_id
            ]
            if order_line_return_detail:
                order_line_return_detail = order_line_return_detail[0]
                return_cause: ReturnCause = YaylohReturnCauses[
                    order_line_return_detail["return_type"].upper()
                ].value
                return_order_lines.append(
                    {
                        "returnOrderRowNumber": f"{order_line.id} - {now}",
                        "customerOrderLine": {"orderLineId": order_line.id},
                        "toBeReturnedNumberOfItems": order_line_return_detail["amount"],
                        "returnCause": {
                            "code": return_cause.code,
                            "name": return_cause.name,
                        },
                    }
                )
                comment.add_row(
                    [
                        order_line_return_detail["sku_number"],
                        order_line_return_detail["return_type"],
                        order_line_return_detail["reason"],
                        order_line_return_detail["comment"],
                    ]
                )
        payload = {
            "goodsOwnerId": self.goods_owner_id,
            "returnOrderNumber": f"{ongoing_order.id} - {now}",
            "customerOrder": {"orderId": ongoing_order.id},
            "returnOrderLines": return_order_lines,
            "comment": str(comment),
        }

        logger.info(f"create_return_order {payload=}")
        return self._make_request("put", self._return_order, payload=payload)

    def _make_request(
        self, req_type: str, url: str, params: dict = None, payload: dict = None
    ) -> Response:
        response: Response = Response()
        response.headers = {}
        try:
            if req_type == "get":
                response = requests.get(url, headers=self.headers, params=params)
            elif req_type == "post":
                response = requests.post(url, headers=self.headers, json=payload)
            elif req_type == "delete":
                response = requests.delete(url, headers=self.headers)
            elif req_type == "put":
                response = requests.put(url, headers=self.headers, json=payload)

            return response

        except requests.exceptions.HTTPError as err:
            logger.warning("Ongoing api unavailable")
            logger.info(err.response.content)
            response.raise_for_status()

        except Exception as err:
            logger.exception(err)
            response.raise_for_status()
