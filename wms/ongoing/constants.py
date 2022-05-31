from enum import Enum

from wms.ongoing.interface import ReturnCause


class YaylohReturnCauses(Enum):
    RETURN = ReturnCause(code="yayloh_return", name="Return", is_remove_cause=False, is_change_cause=False,
                         is_return_comment_mandatory=False)
    EXCHANGE = ReturnCause(code="yayloh_exchange", name="Exchange", is_remove_cause=False, is_change_cause=False,
                           is_return_comment_mandatory=False)
    CLAIM = ReturnCause(code="yayloh_claim", name="Claim", is_remove_cause=False, is_change_cause=False,
                        is_return_comment_mandatory=False)
