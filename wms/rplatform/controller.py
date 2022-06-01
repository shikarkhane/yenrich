from dataclasses import asdict
from os import environ
from typing import List

import requests

from wms.integration.interface import InspectionDetail, Inspection


class Rplatform:
    base_url = environ.get("RPLATFORM_URL")

    @classmethod
    def create_ongoing_return_order(
        cls, retailer_id: int, return_order_id: int, ext_internal_order_id: str, ext_order_detail_ids: List[int]
    ):
        payload = {
            "retailer_id": retailer_id,
            "return_order_id": return_order_id,
            "ext_internal_order_id": ext_internal_order_id,
            "ext_order_detail_ids": ext_order_detail_ids,
        }

        requests.post(f"{cls.base_url}/return/", json=payload)

    @classmethod
    def get_ongoing_return_order(cls, retailer_id: int, ext_internal_order_id: int, ext_order_detail_id: int):
        params = {
            "retailer_id": retailer_id,
            "ext_internal_order_id": ext_internal_order_id,
            "ext_order_detail_id": ext_order_detail_id,
        }

        resp = requests.get(f"{cls.base_url}/return/", params=params)

        return resp.json()["details"]["ongoing_return_id"]

    @classmethod
    def update_inspection_status(cls, retailer_id: int, inspection: Inspection):

        inspection_dict = asdict(inspection)

        response = requests.post(
            url=f"{cls.base_url}/wms/retailer-id/{retailer_id}/order_details/inspected/",
            json=inspection_dict,
        )

        response.raise_for_status()
