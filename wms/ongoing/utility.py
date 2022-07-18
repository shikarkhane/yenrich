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
