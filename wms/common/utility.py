import base64
import json
import re
from typing import Callable

from wms import create_app_for_triggered_event, logger


def get_app_context():
    app = create_app_for_triggered_event()
    app.app_context().push()


def process_sqs_messages_return_batch_failures(event: dict, sqs_processing_func: Callable) -> str:
    get_app_context()

    batch_item_failures = []
    for record in event['Records']:
        try:
            sqs_message: dict = json.loads(record["body"]["detail"]["body"])
            sqs_processing_func(sqs_message)
        except Exception:
            logger.exception(f"Sqs message couldn't be processed: {record['messageId']}")
            batch_item_failures.append({'itemIdentifier': record['messageId']})

    return json.dumps({'batchItemFailures': batch_item_failures})


def camel_case_to_snake_case(camel_case_object):
    if isinstance(camel_case_object, str):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        return pattern.sub('_', camel_case_object).lower()

    if isinstance(camel_case_object, dict):
        snake_case: dict = {}
        for k, v in camel_case_object.items():
            v = camel_case_to_snake_case(v) if isinstance(v, dict) else v
            snake_case[camel_case_to_snake_case(k)] = v
        return snake_case

    if isinstance(camel_case_object, list):
        return [camel_case_to_snake_case(camel_case_entry) for camel_case_entry in camel_case_object if
                not isinstance(camel_case_entry, str)]

    return camel_case_object


def string_to_base64_string(string_to_encode: str):
    return base64.b64encode(string_to_encode.encode()).decode()
