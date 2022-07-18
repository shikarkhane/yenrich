from typing import List

from ymodel.integration.warehouse_integration import (
    OngoingIntegration,
    RetailerWarehouseIntegration,
)

from wms import logger
from wms.common.constants import WarehouseIntegrationType
from wms.common.utility import (
    get_app_context,
    process_sqs_messages_return_batch_failures,
)
from wms.integration.interface import InspectionDetail, Inspection
from wms.ongoing.api import OngoingApi
from wms.ongoing.constants import YaylohReturnCauses
from wms.ongoing.interface import (
    OngoingWebhookOrder,
)
from wms.rplatform.controller import Rplatform


def enrich_return_requests(event: dict):
    get_app_context()
    process_sqs_messages_return_batch_failures(event, push_to_ongoing)


def push_to_ongoing(sqs_message: dict):
    retailer_id: int = sqs_message["retailer_id"]
    warehouse_integration = RetailerWarehouseIntegration.get_first(
        retailer_id=retailer_id,
        warehouse_integration_type_id=WarehouseIntegrationType.ONGOING,
    )
    if warehouse_integration:
        ongoing_integration = OngoingIntegration.get(warehouse_integration.id)
        if ongoing_integration:
            ext_internal_order_id: str = sqs_message["ext_internal_order_id"]

            ongoing_api = OngoingApi(ongoing_integration)
            ongoing_order = ongoing_api.get_order_by_goods_owner_order_id(
                ext_internal_order_id, sqs_message["order_date"]
            )
            logger.info(f"{ongoing_order=}")

            if ongoing_order:
                for return_cause in YaylohReturnCauses:
                    ongoing_api.create_return_cause(return_cause.value)

                return_details: List[dict] = sqs_message["return_details"]
                resp = ongoing_api.create_return_order(ongoing_order, return_details)
                logger.info(f"create return order resp: {resp.json()}")

                resp.raise_for_status()

                return_order_id = resp.json()["returnOrderId"]
                ext_order_detail_ids = [return_detail["ext_order_detail_id"] for return_detail in return_details]
                Rplatform.create_ongoing_return_order(
                    retailer_id=retailer_id,
                    return_order_id=return_order_id,
                    ext_internal_order_id=ext_internal_order_id,
                    ext_order_detail_ids=ext_order_detail_ids,
                )
            else:
                logger.warning(f"Ongoing order not found for {sqs_message['ext_internal_order_id']=}")


def ongoing_return_order_webhook(event: dict):
    get_app_context()
    process_sqs_messages_return_batch_failures(event, update_inspection_status_for_return_orders)


def get_retailer_id_from_goods_owner_id(goods_owner_id: int) -> int:
    ongoing_integration = OngoingIntegration.get_first(goods_owner_id=goods_owner_id)
    warehouse_integration = RetailerWarehouseIntegration.get(ongoing_integration.warehouse_integration_id)
    return warehouse_integration.retailer_id


def update_inspection_status_for_return_orders(sqs_message: dict):
    retailer_id = get_retailer_id_from_goods_owner_id(sqs_message["goodsOwnerId"])

    if warehouse_integration := RetailerWarehouseIntegration.get_first(
            retailer_id=retailer_id, warehouse_integration_type_id=WarehouseIntegrationType.ONGOING
    ):
        if ongoing_integration := OngoingIntegration.get(warehouse_integration.id):
            ongoing_api = OngoingApi(ongoing_integration)

            if sqs_message["isReturned"]:
                webhook_order = OngoingWebhookOrder(**sqs_message["order"])
                ongoing_order = ongoing_api.get_order(webhook_order.orderId)
                if ongoing_order.ext_internal_order_id and webhook_order.orderLine.rowNumber:
                    return_order_id = Rplatform.get_ongoing_return_order(
                        retailer_id=retailer_id,
                        ext_internal_order_id=int(ongoing_order.ext_internal_order_id),
                        ext_order_detail_id=int(webhook_order.orderLine.rowNumber),
                    )

                    if return_order := ongoing_api.get_return_order(return_order_id):
                        inspection_details: List[InspectionDetail] = []
                        for return_order_line in return_order["returnOrderLines"]:
                            inspection_result = (
                                "OK" if return_order_line["returnedRemovedByInventoryNumberOfItems"] == 0 else "NOT OK"
                            )
                            comment = ongoing_order.warehouse_remark[ongoing_order.warehouse_remark.find(" ") + 1:]
                            inspection_details.append(
                                InspectionDetail(
                                    ext_order_detail_id=int(webhook_order.orderLine.rowNumber),
                                    inspection_result=inspection_result,
                                    comment=comment,
                                )
                            )

                        inspection: Inspection = Inspection(
                            ext_internal_order_id=int(ongoing_order.ext_internal_order_id),
                            inspected_order_details=inspection_details,
                        )

                        Rplatform.update_inspection_status(retailer_id=retailer_id, inspection=inspection)
