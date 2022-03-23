import base64
import logging
from requests import Response
import requests
from wms import logger
import os
from wms.ongoing.utility import is_successful
from typing import List
from wms.ongoing.interface import Order, OrderDetail
from wms.integration.interface import InspectionDetail, Inspection
import datetime
from typing import Optional

logging.basicConfig(filename='error.log', level=logging.DEBUG, format='%(asctime)s %(message)s')


class OngoingApi:
    def __init__(self, username, password, warehouse, goods_owner_id):
        self.username = username
        self.password = password
        self.base_url = 'https://api.ongoingsystems.se/{0}/api/v1'.format(warehouse)
        self.goods_owner_id = goods_owner_id
        self.headers = {
            "Content-type": "application/json",
            "Authorization":
                "Basic {0}".format((base64.b64encode(f"{username}:{password}".encode('utf-8'))).decode('utf-8'))
        }
        self._orders = f"{self.base_url}/orders"
        self._return_order = f"{self.base_url}/returnOrders"

    def get_orders_returned_since(self, from_date):
        params = {
            "goodsOwnerId": self.goods_owner_id,
            "lastReturnedFrom": from_date
        }
        return self._make_request("get", self._orders, params=params)

    def get_order_between_dates(self, from_date, to_date):
        params = {
            "goodsOwnerId": self.goods_owner_id,
            "orderCreatedTimeFrom": from_date,
            "orderCreatedTimeTo": to_date
        }

        return self._make_request("get", self._orders, params=params)

    def get_order_by_goods_owner_order_id(self, ext_internal_order_id, order_date) -> Optional[Order]:
        # since Ongoing stores the Shopify Order_id and yayloh has Shopify order_number,
        # we have to search in a date range around order date
        # todo enrich service can call integration to get order object from oms integration

        from_date = order_date - datetime.timedelta(minutes=5)
        to_date = order_date + datetime.timedelta(minutes=5)

        response = self.get_order_between_dates(from_date, to_date)
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

    def create_return_order(self) -> None:
        body = {
                  "goodsOwnerId": self.goods_owner_id,
                  "returnOrderNumber": "string",
                  "customerOrder": {
                    "orderId": 0
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

    def _make_request(self, req_type: str, url: str, params: dict = None, payload: dict = None) -> Response:
        response: Response = Response()
        response.headers = {}
        try:
            if req_type == "get":
                response = requests.get(url, headers=self.headers, params=params)
            if req_type == "post":
                response = requests.post(url, headers=self.headers, json=payload)
            if req_type == "delete":
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


class Account:
    def __init__(self):
        self.username = os.environ.get("username")
        self.password = os.environ.get("password"),
        self.warehouse = os.environ.get("warehouse")
        self.goods_owner_id = os.environ.get("goods_owner_id")
        self.ongoing_api = OngoingApi(username=os.environ.get("username"), password=os.environ.get("password"),
                                      warehouse=os.environ.get("warehouse"),
                                      goods_owner_id=os.environ.get("goods_owner_id"))

    def get_returned_outgoing_orders(self, from_date) -> List[Inspection]:
        raw_orders: List[Inspection] = []
        o = self.ongoing_api
        response = o.get_orders_returned_since(from_date)
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
                        details=inspection_lines
                    )
                )
        return raw_orders


def push_to_ongoing():
    # this function will do the following
    # 1. listen to a queue for new yayloh return requests
    # 2. get "ongoing order" object for a yayloh return request
    # 3. create an "ongoing return order"
    pass


def consume_webhook():
    # this function will do the following
    # 1. listen to ongoing webhook queue
    # 2. get "ongoing order" and corresponding yayloh order object
    # 3. get "return order status from ongoing"
    # 4. Call yayloh to update inspection status
    pass


