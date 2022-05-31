from dateutil.parser import parse
from requests import Response


def get_date_obj(dt):
    return parse(dt)


def is_successful(response: Response):
    if isinstance(response, Response) and response.status_code == 200:
        return True
    return False


def trim_it(string):
    if isinstance(string, str):
        return string.strip()
    return string


def remove_hashtag(ext_order_id: str) -> str:
    return ext_order_id.replace("#", "")


a = {
    "body": {
        "article": {
            "articleSystemId": 21287,
            "articleNumber": "105 01 04 6",
            "barCode": "7350126330141",
        },
        "articleItem": {
            "articleItemId": 183495,
            "originalArticleItemId": 181631,
            "serial": "",
            "batch": "",
            "expiryDate": null,
            "numberOfItems": 1,
            "location": {"location": "1B-3-5", "locationId": 35658},
        },
        "byComputer": null,
        "byUser": {"userId": 73},
        "order": {
            "orderId": 73414,
            "orderNumber": "4305",
            "orderLine": {"orderLineId": 191665, "rowNumber": "10945987215425"},
        },
        "webhookPickingId": 1,
        "webhookEventId": 139,
        "system": "FruOlsson",
        "timestamp": "2022-05-20T10:19:17.1798694Z",
        "goodsOwnerId": 96,
        "isAllocated": true,
        "isPicked": true,
        "isPacked": false,
        "isReturned": true,
        "isDeleted": false,
    }
}
