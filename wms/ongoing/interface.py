# In Ongoing wms, 3PL users can register a return in 2 ways
# 1. Mark an outbound delivery order in Ongoing system as a return. We will call this class ReturnOnDeliveryOrder
# 2. Create a new "return order" and link it to an outbound delivery order.
#       The latter has api structure for logging return reasons.

from typing import List

from dataclasses import dataclass


@dataclass
class OrderDetail:
    ext_internal_order_detail_id: str
    article_id: str
    sku_number: str
    product_name: str
    product_code: str
    return_date: str
    return_reason: str


@dataclass
class Order:
    order_number: str
    ext_internal_order_id: str
    warehouse_remark: str
    shipped_on: str
    order_lines: List[OrderDetail]
