from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import List

from prettytable import PrettyTable

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


@dataclass
class OngoingOrder:
    id: int
    order_number: str
    ext_internal_order_id: str
    warehouse_remark: str
    shipped_on: str
    order_lines: List[OngoingOrderLine]


@dataclass
class ReturnCause:
    code: str
    name: str
    is_remove_cause: bool
    is_change_cause: bool
    is_return_comment_mandatory: bool


class YaylohReturnCauses(Enum):
    RETURN = ReturnCause(
        code="yayloh_return",
        name="Return",
        is_remove_cause=False,
        is_change_cause=False,
        is_return_comment_mandatory=False,
    )
    EXCHANGE = ReturnCause(
        code="yayloh_exchange",
        name="Exchange",
        is_remove_cause=False,
        is_change_cause=False,
        is_return_comment_mandatory=False,
    )
    CLAIM = ReturnCause(
        code="yayloh_claim",
        name="Claim",
        is_remove_cause=False,
        is_change_cause=False,
        is_return_comment_mandatory=False,
    )


ongoing_order = None
payload = []
for i in payload:
    order = i.get("orderInfo")
    if order.get("goodsOwnerOrderId") == "4294950453313":
        order_lines: List[OngoingOrderLine] = [
            OngoingOrderLine(
                order_line.get("id"),
                order_line.get("rowNumber"),
                order_line["article"].get("articleSystemId"),
                order_line["article"].get("articleNumber"),
                order_line["article"].get("articleName"),
                order_line["article"].get("productCode"),
                order_line.get("pickedArticleItems")[0].get("returnDate"),
                order_line.get("pickedArticleItems")[0].get("returnCause"),
            )
            for order_line in i.get("orderLines")
        ]

        ongoing_order = OngoingOrder(
            order.get("orderId"),
            order.get("orderNumber"),
            order.get("goodsOwnerOrderId"),
            order.get("orderRemark"),
            order.get("shippedTime"),
            order_lines,
        )

o = {
    "retailer_id": 71,
    "ext_internal_order_id": "4294950453313",
    "order_date": "2022-04-29 05:40:08",
    "return_details": [
        {
            "ext_order_detail_id": "10972741500993",
            "amount": 1,
            "comment": "",
            "reason": "Wrong size/color/style",
            "return_type": "return",
            "sku_number": "105 01 23 5",
        },
        {
            "ext_order_detail_id": "10972741533761",
            "amount": 1,
            "comment": "",
            "reason": "Too small",
            "return_type": "return",
            "sku_number": "105 01 23 4",
        },
        {
            "ext_order_detail_id": "10972741599297",
            "amount": 1,
            "comment": "",
            "reason": "Too small",
            "return_type": "return",
            "sku_number": "105 01 24 4",
        },
    ],
}

return_details_p = o["return_details"]

return_order_lines = []
now = datetime.now().strftime("%Y-%m-%d %H:%M")
comment = PrettyTable(["SKU", "Return Type", "Return Reason", "Customer Comment"])
for order_line in ongoing_order.order_lines:
    order_line_return_detail = [
        return_detail
        for return_detail in return_details_p
        if return_detail["ext_order_detail_id"] == order_line.ext_order_detail_id
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
                "returnCause": {"code": return_cause.code, "name": return_cause.name},
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
    "goodsOwnerId": 96,
    "returnOrderNumber": f"{ongoing_order.id} - {now}",
    "customerOrder": {"orderId": ongoing_order.id},
    "returnOrderLines": return_order_lines,
    "comment": str(comment),
}

print(f"create_return_order {payload=}")
