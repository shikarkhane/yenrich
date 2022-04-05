from dataclasses import dataclass
from typing import List


@dataclass
class InspectionDetail:
    ext_internal_order_detail_id: int
    order_detail_id: int
    inspection_result: str
    comment: str
    last_changed: str


@dataclass
class Inspection:
    ext_order_id: str
    ext_internal_order_id: int
    inspected_order_details: List[InspectionDetail]
