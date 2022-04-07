import logging

from flask import Blueprint

logging.basicConfig(filename='error.log', level=logging.INFO, format='%(asctime)s %(message)s')

bp = Blueprint('yenrich', __name__, url_prefix='/')


@bp.route('/', methods=('GET',))
def server_status():
    return {'status': 'Server is running'}
