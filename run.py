import json
import os

from flask import request, Response

from wms import create_app, logger

# if 'SERVERTYPE' in os.environ and os.environ['SERVERTYPE'] == 'AWS Lambda':


json_data = open("zappa_settings.json")
env_vars = json.load(json_data)["dev"]["environment_variables"]
for key, val in env_vars.items():
    os.environ[key] = val

app = create_app()


@app.before_request
def before_request():
    try:
        if request.method == "POST":
            logger.info(json.dumps({"request": request.json}))
    except Exception:
        pass


@app.after_request
def after_request(response: Response):
    try:
        if request.method != "OPTIONS":
            logger.info(json.dumps({"response": response.json}))
    except Exception:
        pass

    return response


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=int(os.environ.get("PORT", 8080)))
