from dataclasses import dataclass
from typing import List


@dataclass
class InspectionDetail:
    ext_order_detail_id: int
    inspection_result: str
    comment: str = None
    last_changed: str = None


@dataclass
class Inspection:
    ext_internal_order_id: int
    inspected_order_details: List[InspectionDetail]
    ext_order_id: str = None
