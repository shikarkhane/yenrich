import json

from flask import request, Response

from wms import create_app, logger

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


if __name__ == "__main__":
    app.run()
