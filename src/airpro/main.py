import asyncio
import logging
import sys
from functools import partial
from logging.config import dictConfig
from typing import List

import uvicorn as uvicorn
from fastapi import FastAPI

from airpro import routes
from airpro.core import Clickhouse, AirVisualShare, AirPro
from airpro.model import File, Config

logger = logging.getLogger('root')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)-5s [%(asctime)s, %(msecs)d] %(name)s %(filename)s at %(lineno)d: %(message)s',
            'datefmt': '%Y-%b-%d %H:%M:%S',
        },
    },
    'handlers': {
        'simple': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'airpro': {
            'handlers': ['simple'],
            'level': 'DEBUG',
            'propagate': False
        },
        'root': {
            'handlers': ['simple'],
            'level': 'INFO',
        },
        'SMB': {
            'handlers': ['simple'],
            'level': 'WARN',
            'propagate': False
        }
    },
}

dictConfig(LOGGING)


async def on_startup(app):
    logging.getLogger('airpro').info('Starting..')
    try:
        app.state.db.create_schema()
    except:
        logger.exception('Error creating DDL')
        sys.exit(-1)
    task = app.state.airpro.load_task(asyncio.get_event_loop())
    asyncio.create_task(task)


async def on_shutdown(app):
    logging.getLogger('airpro').info('Shutdown..')


def app_factory():
    config = Config()

    app = FastAPI()

    app.state.share = AirVisualShare(config.device_host,
                                     config.device_username,
                                     config.device_password,
                                     config.device_service_name)
    app.state.db = Clickhouse(config.clickhouse_url)
    app.state.airpro = AirPro(app.state.share, app.state.db)

    app.add_event_handler('startup', partial(on_startup, app=app))
    app.add_event_handler('shutdown', partial(on_shutdown, app=app))

    app.add_api_route('/api/v1/settings', routes.settings)
    app.add_api_route('/api/v1/files', routes.files, response_model=List[File])
    app.add_api_route('/api/v1/load-modified', routes.load_modified)
    app.add_api_route('/api/v1/load-all', routes.load_all)
    return app


def main():
    uvicorn.run(app_factory(), host='0.0.0.0', port=9999,
                log_level=None, access_log=None, log_config=None)


if __name__ == '__main__':
    main()
