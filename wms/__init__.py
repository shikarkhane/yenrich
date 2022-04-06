import logging
import os

import boto3
import click

from flask import Flask
from flask.cli import with_appcontext
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

__version__ = (1, 0, 0, "dev")

# Log everything, and send it to stderr.
from sqlalchemy.orm import close_all_sessions

logging.basicConfig(filename="error.log", level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger()

db: SQLAlchemy = SQLAlchemy()

sqs = boto3.client('sqs', region_name='eu-west-1')
sns = boto3.client('sns', region_name='eu-west-1')
s3 = boto3.client('s3', region_name='eu-west-1')
is_production: bool = os.environ.get('ENV_TYPE') == 'prod'


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)

    # some deploy systems set the database url in the environ
    db_url = os.environ.get("DATABASE_URL")

    if db_url is None:
        # db_url = "mysql+mysqlconnector://root:Ay_Jok9tA}>m@localhost:3306/dev_wms_integration"
        db_url = "mysql+mysqlconnector://dev_rw:~P$xD.6A=iH9@52.49.152.11:3306/dev_wms_integration"

    app.config.from_mapping(
        # default secret that should be overridden in environ or config
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={'pool_recycle': int(os.environ.get('SQLALCHEMY_POOL_RECYCLE', "899"))}
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.update(test_config)

    # initialize Flask-SQLAlchemy and the init-db command
    db.init_app(app)
    app.cli.add_command(init_db_command)

    # apply the blueprints to the app
    # from dashboard import common, order, setting, retailer, auth, reason, statistic, communicate, shipmenttracker, \
    #     lookup, filteraction, emailreport, shippinglabel, tracking_page, integration, write_back, \
    #     data_protection, billing, feedback, intercom
    # from dashboard.integration import s3 as s3_integration
    # from dashboard.auth import shopify, zendesk, gorgias
    #
    # app.register_blueprint(common.bp)
    # app.register_blueprint(order.bp)
    # app.register_blueprint(retailer.bp)
    # app.register_blueprint(auth.bp)
    # app.register_blueprint(reason.bp)
    # app.register_blueprint(statistic.bp)
    # app.register_blueprint(communicate.bp)
    # app.register_blueprint(shipmenttracker.bp)
    # app.register_blueprint(setting.bp)
    # app.register_blueprint(lookup.bp)
    # app.register_blueprint(filteraction.bp)
    # app.register_blueprint(emailreport.bp)
    # app.register_blueprint(shippinglabel.bp)
    # app.register_blueprint(tracking_page.bp)
    # app.register_blueprint(integration.bp)
    # app.register_blueprint(write_back.bp)
    # app.register_blueprint(data_protection.bp)
    # app.register_blueprint(shopify.bp)
    # app.register_blueprint(zendesk.bp)
    # app.register_blueprint(gorgias.bp)
    # app.register_blueprint(billing.bp)
    # app.register_blueprint(feedback.bp)
    # app.register_blueprint(intercom.bp)


    return app


def create_app_for_triggered_event(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # some deploy systems set the database url in the environ
    db_url = os.environ.get("DATABASE_URL")

    if db_url is None:
        # db_url = "mysql+mysqlconnector://root:Ay_Jok9tA}>m@localhost:3306/dev_wms_integration"
        db_url = "mysql+mysqlconnector://dev_rw:~P$xD.6A=iH9@34.242.242.58:3306/dev_wms_integration"

    app.config.from_mapping(
        # default secret that should be overridden in environ or config
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.update(test_config)

    # initialize Flask-SQLAlchemy and the init-db command
    close_all_sessions()
    db.init_app(app)

    return app


def init_db():
    # db.drop_all()
    db.create_all()


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    click.echo("Initialized the database.")
