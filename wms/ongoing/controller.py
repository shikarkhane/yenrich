import base64
import logging
from requests import Response
import requests
from wms import logger
import os
from wms.ongoing.utility import is_successful
from typing import List
from wms.ongoing.interface import Order, OrderDetail

logging.basicConfig(filename='error.log', level=logging.DEBUG, format='%(asctime)s %(message)s')


class OngoingApi:
    def __init__(self, username, password, warehouse, goods_owner_id):
        self.username = username
        self.password = password
        self.base_url = 'https://api.ongoingsystems.se/{0}/api/v1/'.format(warehouse)
        self.goods_owner_id = goods_owner_id
        self.headers = {
            "Content-type": "application/json",
            "Authorization": "Basic {0}".format(base64.b64encode(username + ":" + password))
        }
        self._returned_orders_since = f"{self.base_url}/orders"

    def get_orders_returned_since(self, from_date):
        params = {
            "goodsOwnerId": self.goods_owner_id,
            "lastReturnedFrom": from_date
        }
        return self._make_request("get", self._returned_orders_since, params=params)

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


def get_returned_orders(from_date) -> List[Order]:
    returned_orders = []
    o = OngoingApi(username=os.environ.get("username"), password=os.environ.get("password"),
                   warehouse=os.environ.get("warehouse"), goods_owner_id=os.environ.get("goods_owner_id"))
    response = o.get_orders_returned_since(from_date)
    if is_successful(response):
        orders = [i.get("orderInfo") for i in response.json()]
        for order in orders:
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
                for order_line in order.get("orderLines")]

            returned_orders.append(
                Order(
                    order.get("orderNumber"),
                    order.get("goodsOwnerOrderId"),
                    order.get("orderRemark"),
                    order.get("shippedTime"),
                    order_lines
                )
            )
    return returned_orders
