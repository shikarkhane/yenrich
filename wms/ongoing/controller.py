from dataclasses import asdict
from datetime import timedelta, datetime
from http import HTTPStatus
from typing import List
from typing import Optional

import requests
from requests import Response
from werkzeug.exceptions import abort
from ymodel.integration.warehouse_integration import OngoingIntegration, RetailerWarehouseIntegration

from wms import logger
from wms.common.constants import YaylohServices, RetailerWarehouseIntegrationType
from wms.common.utility import process_sqs_messages_return_batch_failures, string_to_base64_string
from wms.integration.interface import InspectionDetail, Inspection
from wms.ongoing.interface import Order, OrderDetail, OngoingReturnOrder
from wms.ongoing.utility import is_successful


class OngoingApi:
    def __init__(self, retailer_id: int):
        warehouse_integration = RetailerWarehouseIntegration.get_first(retailer_id=retailer_id,
                                                                       warehouse_integration_type_id=RetailerWarehouseIntegrationType.ONGOING)
        ongoing_integration = OngoingIntegration.get(warehouse_integration.id)

        if not ongoing_integration:
            abort(HTTPStatus.BAD_REQUEST, f"Ongoing integration for {retailer_id=} does not exist!")

        self.goods_owner_id: int = ongoing_integration.goods_owner_id
        self.base_url: str = f"https://api.ongoingsystems.se/{ongoing_integration.warehouse_name}/api/v1"

        auth_token: str = string_to_base64_string(f'{ongoing_integration.username}:{ongoing_integration.password}')
        self.headers = {
            "Content-type": "application/json",
            "Authorization":
                f"Basic {auth_token}"
        }

        self._orders: str = f"{self.base_url}/orders"
        self._return_order: str = f"{self.base_url}/returnOrders"

    def get_order(self, order_number: str) -> Response:
        params = {
            "goodsOwnerId": self.goods_owner_id,
            "orderNumber": order_number
        }
        return self._make_request("get", self._orders, params=params)

    def get_outgoing_orders_returned_since(self, from_date: str) -> Response:
        params = {
            "goodsOwnerId": self.goods_owner_id,
            "lastReturnedFrom": from_date
        }
        return self._make_request("get", self._orders, params=params)

    def get_outgoing_order_between_dates(self, from_date: str, to_date: str) -> Response:
        params = {
            "goodsOwnerId": self.goods_owner_id,
            "orderCreatedTimeFrom": from_date,
            "orderCreatedTimeTo": to_date
        }
        logger.info(f"get_outgoing_order_between_dates {params=}")
        return self._make_request("get", self._orders, params=params)

    def get_order_by_goods_owner_order_id(self, ext_internal_order_id: str, order_date: datetime) -> Optional[Order]:
        # since Ongoing stores the Shopify Order_id and yayloh has Shopify order_number,
        # we have to search in a date range around order date
        # todo enrich service can call integration to get order object from oms integration

        from_date: str = (order_date - timedelta(minutes=5)).strftime("%Y-%m-%d")
        to_date: str = (order_date + timedelta(minutes=5)).strftime("%Y-%m-%d")

        response = self.get_outgoing_order_between_dates(from_date, to_date)
        logger.info(f"get_order_by_goods_owner_order_id {response.json()}")
        if is_successful(response):
            for i in response.json():
                order = i.get("orderInfo")
                if order.get("goodsOwnerOrderId") == ext_internal_order_id:
                    order_lines: List[OrderDetail] = [
                        OrderDetail(
                            order_line.get("rowNumber"),
                            order_line.get("articleSystemId"),
                            order_line.get("articleNumber"),
                            order_line.get("articleName"),
                            order_line.get("productCode"),
                            order_line.get("pickedArticleItems")[0].get("returnDate"),
                            order_line.get("pickedArticleItems")[0].get("returnCause")
                        )
                        for order_line in i.get("orderLines")]

                    return(
                        Order(
                            order.get("orderNumber"),
                            order.get("goodsOwnerOrderId"),
                            order.get("orderRemark"),
                            order.get("shippedTime"),
                            order_lines
                        )
                    )
        return None

    def create_return_order(self, order_id: int):
        payload = {
            "goodsOwnerId": self.goods_owner_id,
            "returnOrderNumber": "string",
            "customerOrder": {
                "orderId": order_id
            },
            "returnOrderLines": [
                {
                    "returnOrderRowNumber": "string",
                    "customerOrderLine": {
                        "orderLineId": 0
                    },
                    "toBeReturnedNumberOfItems": 0
                }
            ]
        }

        logger.info(f"create_return_order {payload=}")
        # return self._make_request("put", self._return_order, payload=payload)

    def get_return_orders(self, return_order_numbers: List[str]) -> List[dict]:
        params = {
            "goodsOwnerId": self.goods_owner_id,
            "returnOrderNumbers": return_order_numbers
        }

        response = self._make_request("get", self._return_order, params=params)

        response.raise_for_status()

        return response.json()

    def _make_request(self, req_type: str, url: str, params: dict = None, payload: dict = None) -> Response:
        response: Response = Response()
        response.headers = {}
        try:
            if req_type == "get":
                response = requests.get(url, headers=self.headers, params=params)
            elif req_type == "post":
                response = requests.post(url, headers=self.headers, json=payload)
            elif req_type == "delete":
                response = requests.delete(url, headers=self.headers)

            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as err:
            logger.warning("Ongoing api unavailable")
            logger.info(err.response.content)
            response.raise_for_status()

        except Exception as err:
            logger.exception(err)
            response.raise_for_status()


def get_returned_outgoing_orders(retailer_id: int, from_date: str) -> List[Inspection]:
    raw_orders: List[Inspection] = []
    response = OngoingApi(retailer_id).get_outgoing_orders_returned_since(from_date)
    if is_successful(response):
        for i in response.json():
            order = i.get("orderInfo")
            inspection_lines: List[InspectionDetail] = []
            for order_line in i.get("orderLines"):
                # 'orderRemark': '220221 kan lagerföras' means it can be put back to sell
                if "220221" in order.get("orderRemark"):
                    inspection_result = "OK"
                else:
                    inspection_result = "Not OK"
                inspect_line = InspectionDetail(
                    ext_internal_order_detail_id=order_line.get("rowNumber"),
                    order_detail_id=None,
                    inspection_result=inspection_result,
                    comment=order.get("orderRemark"),
                    last_changed=order_line.get("pickedArticleItems")[0].get("returnDate")
                )
                inspection_lines.append(inspect_line)

                raw_orders.append(
                    Inspection(
                        ext_order_id=None,
                        ext_internal_order_id=order.get("goodsOwnerOrderId"),
                        inspected_order_details=inspection_lines
                    )
                )
        return raw_orders


def enrich_return_requests(event: dict):
    process_sqs_messages_return_batch_failures(event, push_to_ongoing)


def push_to_ongoing(sqs_message: dict):
    # this function will do the following
    # 1. get "ongoing order" object for a yayloh return request
    ongoing_api = OngoingApi(sqs_message['retailer_id'])
    ongoing_order = ongoing_api.get_order_by_goods_owner_order_id(sqs_message['ext_internal_order_id'],
                                                                  sqs_message['order_date'])
    logger.info(ongoing_order)
    # 2. create an "ongoing return order"
    ongoing_api.create_return_order(ongoing_order.ext_internal_order_id)


def ongoing_return_order_webhook(event: dict):
    process_sqs_messages_return_batch_failures(event, update_inspection_status_for_return_orders)


def ongoing_return_on_delivery_order_webhook(event: dict):
    process_sqs_messages_return_batch_failures(event, update_inspection_status_for_return_on_delivery_orders)


def get_retailer_id_from_goods_owner_id(goods_owner_id: int) -> int:
    ongoing_integration = OngoingIntegration.get_first(goods_owner_id=goods_owner_id)
    warehouse_integration = RetailerWarehouseIntegration.get(ongoing_integration.warehouse_integration_id)
    return warehouse_integration.retailer_id


def update_inspection_status_for_return_orders(sqs_message: dict):
    # this function will do the following
    inspection_dict = {}

    # 1. parse webhook payload
    retailer_id = get_retailer_id_from_goods_owner_id(sqs_message['goodsOwnerId'])
    return_order = parse_return_order_webhook_payload(sqs_message)
    customer_order_info: dict = sqs_message['customerOrderInfo']

    # 2. get "ongoing return order" and corresponding yayloh order object
    ongoing_api = OngoingApi(retailer_id)
    if return_orders := ongoing_api.get_return_orders([return_order.returnOrderNumber]):
        # 3. get "return order status from ongoing"
        inspection_details: List[InspectionDetail] = get_ongoing_inspection_statuses(return_orders)
        inspection: Inspection = Inspection(ext_order_id=customer_order_info['orderNumber'],
                                            ext_internal_order_id=customer_order_info['orderId'],
                                            inspected_order_details=inspection_details)
        inspection_dict = asdict(inspection)

    # 4. Call yayloh to update inspection status
    response = requests.post(url=f"{YaylohServices.RPLATFORM}/wms/retailer-id/{retailer_id}/order_details/inspected/",
                             json=inspection_dict)

    response.raise_for_status()


def update_inspection_status_for_return_on_delivery_orders(sqs_message: dict):
    pass
    # return_on_delivery_order = account.ongoing_api.get_order(order.orderNumber)


def parse_return_order_webhook_payload(sqs_message: dict) -> OngoingReturnOrder:
    return OngoingReturnOrder(**sqs_message['returnOrder'])


def get_ongoing_inspection_statuses(return_orders: List[dict]) -> List[InspectionDetail]:
    if len(return_orders) == 1:
        return_order = return_orders[0]
        inspection_details: List[InspectionDetail] = []
        for return_order_line in return_order['returnOrderLines']:
            inspection_detail = InspectionDetail(return_order_line['returnOrderRowNumber'],
                                                 None, "Not OK",
                                                 return_order['returnOrderInfo']['comment'],
                                                 return_order['returnOrderInfo']['inDate'])
            if return_order['returnOrderInfo']['returnOrderStatus']['text'] == "Returnerad":
                inspection_detail.inspection_result = "OK"
            inspection_details.append(inspection_detail)

        return inspection_details

    return []
