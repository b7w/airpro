import time
from datetime import datetime

from pytz import timezone


def _mk_format(d: datetime):
    return d.strftime('%Y-%m-%d %H:%M:%S')


def _mk_time(d: datetime):
    return int(time.mktime(d.timetuple()))


def _print(s, d):
    print(f'Date {s} {d.isoformat()} / {_mk_format(d)} / {d.timestamp()} / {_mk_time(d)}')


def test_zone_datetime():
    t = 1609794006
    print(f'Date stupid origin {t}')
    utc = timezone('UTC')
    msk = timezone('Europe/Moscow')

    d_msk = datetime.utcfromtimestamp(t).replace(tzinfo=msk)
    _print('msk1', d_msk)

    d_msk2 = datetime.fromtimestamp(t)
    _print('msk2', d_msk2)

    d_utc = d_msk.astimezone(utc)
    _print('utc1', d_utc)


if __name__ == '__main__':
    test_zone_datetime()
