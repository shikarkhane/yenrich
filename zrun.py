from datetime import datetime, timedelta

from flask import Response, session
from flask.sessions import SecureCookieSessionInterface

from wms import create_app
from dashboard.common.date_utility import UTC_TIME_FORMAT

app = create_app()

session_cookie = SecureCookieSessionInterface().get_signing_serializer(app)


@app.after_request
def after_request(response: Response):
    same_cookie = session_cookie.dumps(dict(session))
    response.headers.add('Set-Cookie', f"session={same_cookie}; Secure; HttpOnly; SameSite=None; Path=/;"
                                       f"Expires={(datetime.now() + timedelta(days=1)).strftime(UTC_TIME_FORMAT)};")
    response.headers.set('Access-Control-Allow-Credentials', "true")
    return response


if __name__ == "__main__":
    app.run()
