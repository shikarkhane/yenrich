import requests

from wms.common.utility import string_to_base64_string

username = "WSIStiksenYayloh"
password = "LxAcwM5HyoaZDGEANX4z"

auth_token: str = string_to_base64_string(f"{username}:{password}")
headers = {"Content-type": "application/json", "Authorization": f"Basic {auth_token}"}

last_id = 117
a = []
for i in range(1, last_id):
    url = f"https://api.ongoingsystems.se/fruolsson/api/v1/returnOrders/{i}"
    resp = requests.get(url, headers=headers)
    return_order_info = resp.json()["returnOrderInfo"]
    print(
        f"{return_order_info['returnOrderId']} {return_order_info['returnOrderNumber']}"
    )
    for order_line in resp.json()["returnOrderLines"]:
        if order_line['returnedRemovedByInventoryNumberOfItems'] != 0.0:
            print("It was rejected!")
        print(f"\t{order_line['returnedRemovedByInventoryNumberOfItems']}")
    if len(resp.json()["returnOrderLines"]) > 1:
        a.append(return_order_info["returnOrderNumber"].split("-")[0].strip())

print(resp.json())
print(a)
