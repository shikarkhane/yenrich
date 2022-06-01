from dataclasses import dataclass
from typing import List


@dataclass
class ReturnCause:
    code: str
    name: str
    is_remove_cause: bool
    is_change_cause: bool
    is_return_comment_mandatory: bool


@dataclass
class OngoingOrderLine:
    id: int
    ext_order_detail_id: str
    article_id: str
    sku_number: str
    product_name: str
    product_code: str
    return_date: str
    return_reason: str

    def __init__(self, order_line: dict):
        self.id = order_line.get("id")
        self.ext_order_detail_id = order_line.get("rowNumber")

        article = order_line["article"]
        self.article_id = article.get("articleSystemId")
        self.sku_number = article.get("articleNumber")
        self.product_name = article.get("articleName")
        self.product_code = article.get("productCode")

        picked_article_item = order_line.get("pickedArticleItems")[0]
        self.return_date = picked_article_item.get("returnDate")
        self.return_reason = picked_article_item.get("returnCause")


@dataclass
class OngoingOrder:
    id: int
    order_number: str
    ext_internal_order_id: str
    warehouse_remark: str
    shipped_on: str
    order_lines: List[OngoingOrderLine]

    def __init__(self, order_details: dict):
        order = order_details.get("orderInfo")

        self.id = order.get("orderId")
        self.order_number = order.get("orderNumber")
        self.ext_internal_order_id = order.get("goodsOwnerOrderId")
        self.warehouse_remark = order.get("orderRemark")
        self.shipped_on = order.get("shippedTime")
        self.order_lines = [
            OngoingOrderLine(order_line)
            for order_line in order_details.get("orderLines")
        ]


@dataclass
class OngoingWebhookOrderLine:
    orderLineId: int
    rowNumber: str


@dataclass
class OngoingWebhookOrder:
    orderId: int
    orderNumber: str
    orderLine: OngoingWebhookOrderLine
