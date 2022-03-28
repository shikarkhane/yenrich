from dateutil.parser import parse
from requests import Response


def get_date_obj(dt):
    return parse(dt)


def is_successful(response):
    if isinstance(response, Response):
        if response and response.status_code == 200:
            return True
    return False


def trim_it(a):
    if a and isinstance(a, str):
        return a.strip()
    return a


def remove_hashtag(ext_order_id: str) -> str:
    return ext_order_id.replace('#', '')
