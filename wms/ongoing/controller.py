from dataclasses import asdict
from datetime import timedelta, datetime
from typing import List
from typing import Optional

import requests
from prettytable import PrettyTable
from requests import Response
from ymodel.integration.warehouse_integration import OngoingIntegration, RetailerWarehouseIntegration

from wms import logger
from wms.common.constants import YaylohServices, WarehouseIntegrationType
from wms.common.utility import process_sqs_messages_return_batch_failures, string_to_base64_string
from wms.integration.interface import InspectionDetail, Inspection
from wms.ongoing.constants import YaylohReturnCauses
from wms.ongoing.interface import OngoingOrder, OngoingOrderLine, OngoingReturnOrder, ReturnCause
from wms.ongoing.utility import is_successful


class OngoingApi:
    def __init__(self, ongoing_integration: OngoingIntegration):
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
        self._return_causes: str = f"{self.base_url}/returnOrders/returnCauses"

    def get_order(self, order_number: str) -> Response:
        params = {
            "goodsOwnerId": self.goods_owner_id,
            "orderNumber": order_number
        }
        return self._make_request("get", self._orders, params=params)

    def create_return_cause(self, return_cause: ReturnCause):
        payload = {
            "goodsOwnerId": self.goods_owner_id,
            "code": return_cause.code,
            "name": return_cause.name,
            "isRemoveCause": return_cause.is_remove_cause,
            "isChangeCause": return_cause.is_change_cause,
            "isReturnCommentMandatory": return_cause.is_return_comment_mandatory
        }

        return self._make_request("put", self._return_causes, payload=payload)

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

    def get_order_by_goods_owner_order_id(self, ext_internal_order_id: str, order_date: str) -> Optional[OngoingOrder]:
        # since Ongoing stores the Shopify Order_id and yayloh has Shopify order_number,
        # we have to search in a date range around order date
        # todo enrich service can call integration to get order object from oms integration

        order_date = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S')
        from_date: str = (order_date - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S%z")
        to_date: str = (order_date + timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S%z")

        response = self.get_outgoing_order_between_dates(from_date, to_date)
        logger.info(f"get_order_by_goods_owner_order_id {response.json()}")
        if is_successful(response):
            for i in response.json():
                order = i.get("orderInfo")
                if order.get("goodsOwnerOrderId") == ext_internal_order_id:
                    order_lines: List[OngoingOrderLine] = [
                        OngoingOrderLine(
                            order_line.get('id'),
                            order_line.get("rowNumber"),
                            order_line['article'].get("articleSystemId"),
                            order_line['article'].get("articleNumber"),
                            order_line['article'].get("articleName"),
                            order_line['article'].get("productCode"),
                            order_line.get("pickedArticleItems")[0].get("returnDate"),
                            order_line.get("pickedArticleItems")[0].get("returnCause")
                        )
                        for order_line in i.get("orderLines")]

                    return (
                        OngoingOrder(
                            order.get("orderId"),
                            order.get("orderNumber"),
                            order.get("goodsOwnerOrderId"),
                            order.get("orderRemark"),
                            order.get("shippedTime"),
                            order_lines
                        )
                    )
        return None

    def create_return_order(self, ongoing_order: OngoingOrder, return_details: List[dict]):
        return_order_lines = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        comment = PrettyTable(['SKU', 'Return Type', 'Return Reason', 'Customer Comment'])
        for order_line in ongoing_order.order_lines:
            order_line_return_detail = [
                return_detail for return_detail in return_details if
                return_detail['ext_order_detail_id'] == order_line.ext_order_detail_id]
            if order_line_return_detail:
                order_line_return_detail = order_line_return_detail[0]
                return_cause: ReturnCause = YaylohReturnCauses[order_line_return_detail['return_type'].upper()].value
                return_order_lines.append({
                    "returnOrderRowNumber": f"{order_line.id} - {now}",
                    "customerOrderLine": {
                        "orderLineId": order_line.id
                    },
                    "toBeReturnedNumberOfItems": order_line_return_detail['amount'],
                    "returnCause": {
                        "code": return_cause.code,
                        "name": return_cause.name
                    }
                })
                comment.add_row([order_line_return_detail['sku_number'], order_line_return_detail['return_type'],
                                 order_line_return_detail['reason'], order_line_return_detail['comment']])
        payload = {
            "goodsOwnerId": self.goods_owner_id,
            "returnOrderNumber": f"{ongoing_order.id} - {now}",
            "customerOrder": {
                "orderId": ongoing_order.id
            },
            "returnOrderLines": return_order_lines,
            "comment": str(comment)
        }

        logger.info(f"create_return_order {payload=}")
        return self._make_request("put", self._return_order, payload=payload)

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
    warehouse_integration = RetailerWarehouseIntegration.get_first(retailer_id=sqs_message['retailer_id'],
                                                                   warehouse_integration_type_id=WarehouseIntegrationType.ONGOING)
    if warehouse_integration:
        ongoing_integration = OngoingIntegration.get(warehouse_integration.id)
        if ongoing_integration:
            ongoing_api = OngoingApi(ongoing_integration)
            ongoing_order = ongoing_api.get_order_by_goods_owner_order_id(sqs_message['ext_internal_order_id'],
                                                                          sqs_message['order_date'])
            logger.info(ongoing_order)

            # create return causes
            for return_cause in YaylohReturnCauses:
                ongoing_api.create_return_cause(return_cause.value)

            # 2. create an "ongoing return order"
            resp = ongoing_api.create_return_order(ongoing_order, sqs_message['return_details'])
            logger.info(f"create return order resp: {resp.json()}")


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
    warehouse_integration = RetailerWarehouseIntegration.get_first(retailer_id=sqs_message['retailer_id'],
                                                                   warehouse_integration_type_id=WarehouseIntegrationType.ONGOING)
    if warehouse_integration:
        ongoing_integration = OngoingIntegration.get(warehouse_integration.id)
        if ongoing_integration:
            ongoing_api = OngoingApi(ongoing_integration)
            if return_orders := ongoing_api.get_return_orders([return_order.returnOrderNumber]):
                # 3. get "return order status from ongoing"
                inspection_details: List[InspectionDetail] = get_ongoing_inspection_statuses(return_orders)
                inspection: Inspection = Inspection(ext_order_id=customer_order_info['orderNumber'],
                                                    ext_internal_order_id=customer_order_info['orderId'],
                                                    inspected_order_details=inspection_details)
                inspection_dict = asdict(inspection)

            # 4. Call yayloh to update inspection status
            response = requests.post(
                url=f"{YaylohServices.RPLATFORM}/wms/retailer-id/{retailer_id}/order_details/inspected/",
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
