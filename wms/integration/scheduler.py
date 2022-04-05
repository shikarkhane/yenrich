from wms.ongoing.controller import update_inspection_status_for_return_orders

message = {
    "article": {
        "articleSystemId": 21305,
        "articleNumber": "107 01 04 6",
        "barCode": "7350126330172"
    },
    "articleItem": {
        "articleItemId": 177357,
        "originalArticleItemId": 142146,
        "serial": "",
        "batch": "",
        "expiryDate": None,
        "numberOfItems": 1,
        "location": {
            "location": "1A-3-10",
            "locationId": 35438
        }
    },
    "byComputer": None,
    "byUser": {
        "userId": 115
    },
    "order": {
        "orderId": 70029,
        "orderNumber": "3990",
        "orderLine": {
            "orderLineId": 182129,
            "rowNumber": "10833312710721"
        }
    },
    "webhookPickingId": 1,
    "webhookEventId": 8,
    "system": "FruOlsson",
    "timestamp": "2022-03-24T11:35:29.9324850Z",
    "goodsOwnerId": 96,
    "isAllocated": True,
    "isPicked": True,
    "isPacked": False,
    "isReturned": True,
    "isDeleted": False
}

update_inspection_status_for_return_orders(message)