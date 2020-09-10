# TODO: license


from werkzeug.middleware.dispatcher import DispatcherMiddleware

from pygeoapi.flask_app import APP as pygeoapi_app
from edc_ogc.app import app as edc_ogc_app

app = DispatcherMiddleware(pygeoapi_app, {'/ogc-edc': edc_ogc_app})
