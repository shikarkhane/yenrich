from wms.ongoing.controller import Account


def import_ongoing_returned_outgoing_orders():
    stiksen_acct = Account()
    stiksen_acct.get_returned_outgoing_orders("2022-01-01")
