# In Ongoing wms, 3PL users can register a return in 2 ways
# 1. Mark an outbound delivery order in Ongoing system as a return. We will call this class ReturnOnDeliveryOrder
# 2. Create a new "return order" and link it to an outbound delivery order.
#       The latter has api structure for logging return reasons.

from typing import Tuple, Optional, List


class OrderDetail:
    def __init__(self,
                 row_number,
                 article_id,
                 article_number,
                 article_name,
                 product_code,
                 returned_on,
                 return_cause
                 ):
        self.ext_internal_order_detail_id = row_number
        self.article_id = article_id
        self.sku_number = article_number
        self.product_name = article_name
        self.product_code = product_code
        self.return_date = returned_on
        self.return_reason = return_cause

    def repr_json(self):
        return dict(ext_internal_order_detail_id=self.ext_internal_order_detail_id, article_id=self.article_id,
                    sku_number=self.sku_number, product_name=self.product_name,
                    product_code=self.product_code,
                    return_date=self.return_date, return_reason=self.return_reason)


class Order:
    def __init__(self,
                 order_number: str,
                 goods_owner_order_id: str,
                 warehouse_remark: str,
                 shipped_on: str,
                 order_lines: List[OrderDetail]):
        self.order_number = order_number
        self.ext_internal_order_id = goods_owner_order_id
        self.warehouse_remark = warehouse_remark
        self.shipped_on = shipped_on
        self.order_lines: List[OrderDetail] = order_lines

    def repr_json(self):
        return dict(order_number=self.order_number, ext_internal_order_id=self.ext_internal_order_id,
                    warehouse_remark=self.warehouse_remark, shipped_on=self.shipped_on,
                    order_lines=self.order_lines)



