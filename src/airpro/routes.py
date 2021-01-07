from datetime import datetime

from fastapi import Depends
from starlette.requests import Request

from airpro.core import AirVisualShare, AirPro
from airpro.model import File, Config


def _airpro_dep(request: Request):
    return request.app.state.airpro


def _share_dep(request: Request):
    return request.app.state.share


def settings(share: AirVisualShare = Depends(_share_dep)):
    return share.last_config


def files(share: AirVisualShare = Depends(_share_dep)):
    config = Config()
    return [File(name=i.filename,
                 size=i.file_size,
                 created=datetime.utcfromtimestamp(i.create_time).astimezone(config.timezone_info()),
                 updated=datetime.utcfromtimestamp(i.last_write_time).astimezone(config.timezone_info()),
                 ) for i in share.list()]


def load_modified(airpro: AirPro = Depends(_airpro_dep)):
    return airpro.load_modified_files()


def load_all(airpro: AirPro = Depends(_airpro_dep)):
    return airpro.load_all_files()
