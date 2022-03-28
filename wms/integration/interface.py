from dataclasses import dataclass
from typing import List


# @bp.route("/wms/retailer-id/<int:retailer_id>/order_details/inspected/",
#           methods=("POST",))
# def update_order_details_after_warehouse_inspection_by_ext_oms_order_id(retailer_id: int):
#     retailer: Retailer = Retailer.get(retailer_id)
#     json_data: dict = request.json
#
#     if retailer and json_data:
#         inspected_order_details: List[dict] = json_data['inspected_order_details']
#         for inspected_order_detail in inspected_order_details:
#             order: Optional[Order] = Order.get_by_ext_id(json_data['ext_order_id'], retailer.retailer_id)
#             if not order:
#                 order: Optional[Order] = \
#                     Order.get_by_ext_internal_id(json_data['ext_internal_order_id'], retailer.retailer_id)
#             if order:
#                 is_approved: int = 1 if inspected_order_detail['inspection_result'] == "OK" else 0
#                 od: Optional[OrderDetail] = \
#                     OrderDetail.get_by_ext_order_detail_id(order.order_id,
#                                                            inspected_order_detail['ext_internal_order_detail_id'])
#                 if od:
#                     WarehouseInbound.upsert(order_detail_id=od.order_detail_id,
#                                             is_approved=is_approved,
#                                             comment=inspected_order_detail['comment'],
#                                             creation_date=datetime.datetime.strptime(
#                                                 inspected_order_detail['last_changed'],
#                                                 GOOGLE_SHEET_DATE_FORMAT))
#         return jsonify({"status": "ok", "message": "WMS - Inspected Order Details Updated"})
#     abort(HTTPStatus.BAD_REQUEST)
#


@dataclass
class InspectionDetail:
    ext_internal_order_detail_id: int
    order_detail_id: int
    inspection_result: str
    comment: str
    last_changed: str


@dataclass
class Inspection:
    ext_order_id: int
    ext_internal_order_id: int
    inspected_order_details: List[InspectionDetail]
