import asyncio
import csv
import json
import logging
import re
import time
from asyncio.base_events import BaseEventLoop
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from io import BytesIO, TextIOWrapper
from typing import Iterable, TypeVar, List, Tuple

from clickhouse_driver import Client
from smb.SMBConnection import SMBConnection

from airpro.model import Event, Config

T = TypeVar('T')

logger = logging.getLogger('airpro')


def iter_batch(iterable: Iterable[T], size) -> Iterable[List[T]]:
    buf = []
    for it in iterable:
        buf.append(it)
        if len(buf) == size:
            yield buf
            buf = []
    if buf:
        yield buf


def timeit(f):
    logger = logging.getLogger('airpro.timeit')

    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            return f(*args, **kwargs)
        finally:
            elapsed = int(time.time() - start)
            logger.debug('## {0} complete in {1:d} min {2:d} sec'.format(f.__name__, elapsed // 60, elapsed % 60))

    return wrapper


class Clickhouse:
    def __init__(self, dsn):
        self._client = Client.from_url(dsn)

    def create_schema(self, ):
        sql = """
        CREATE TABLE if NOT EXISTS airpro
        (
            timestamp      DateTime('UTC'),
            tz             String,
            pm2_5          Decimal(3, 2),
            aqi_us         UInt16,
            aqi_ch         UInt16,
            pm10           Decimal(3, 2),
            pm1            Decimal(3, 2),
            outdoor_aqi_us UInt16,
            outdoor_aqi_ch UInt16,
            temperature    Decimal(2, 2),
            humidity       UInt16,
            co2            UInt16
        ) ENGINE = ReplacingMergeTree()
        PARTITION BY toYYYYMM(timestamp)
        PRIMARY KEY timestamp
        ORDER BY (timestamp)
        """
        self._client.execute(sql)

    def insert(self, events):
        sql = """
        INSERT INTO airpro (
            timestamp,
            tz,
            pm2_5,
            aqi_us,
            aqi_ch,
            pm10,
            pm1,
            outdoor_aqi_us,
            outdoor_aqi_ch,
            temperature,
            humidity,
            co2
        ) VALUES
        """
        return self._client.execute(sql, events)


class AirVisualShare:
    RE = r'\d+_AirVisual_values.\w+'
    EXCLUDE = 'latest_config_measurements.json'

    def __init__(self, host, username, password, service):
        super().__init__()
        self._host = host
        self._username = username
        self._password = password
        self._service = service

    @contextmanager
    def _connect(self):
        with SMBConnection(self._username, self._password, '127.0.0.1', self._host, use_ntlm_v2=True) as conn:
            assert conn.connect(self._host, 139, timeout=10)
            yield conn

    def _list(self, c):
        raw = c.listPath(self._service, '/', timeout=10)
        data = sorted(raw, key=lambda i: i.filename)
        return [i for i in data if re.match(self.RE, i.filename) and i.filename != self.EXCLUDE]

    def _retrieve(self, c, fname, offset) -> Tuple[int, BytesIO]:
        buf = BytesIO()
        _, size = c.retrieveFileFromOffset(self._service, fname, buf, offset)
        buf.seek(0)
        return offset + size, buf

    @property
    def last_config(self):
        with self._connect() as c:
            buf = BytesIO()
            c.retrieveFile(self._service, '/latest_config_measurements.json', buf)
            buf.seek(0)
            return json.load(buf)

    def list(self):
        with self._connect() as c:
            return self._list(c)

    def retrieve_all(self) -> Iterable[BytesIO]:
        with self._connect() as c:
            for f in self._list(c):
                buf = BytesIO()
                c.retrieveFile(self._service, f.filename, buf)
                buf.seek(0)
                yield f.filename, buf

    def tail(self, updated_after, offsets, tz):
        with self._connect() as c:
            for f in self._list(c):
                if datetime.utcfromtimestamp(f.last_write_time).astimezone(tz) >= updated_after:
                    fname = f.filename
                    offset, buffer = self._retrieve(c, fname, offsets.get(fname, 0))
                    yield fname, offset, buffer


class AirPro:

    def __init__(self, share: AirVisualShare, db: Clickhouse):
        self._share = share
        self._db = db
        self._fieldnames = ('Date', 'Time', 'Timestamp', 'PM2_5(ug/m3)', 'AQI(US)', 'AQI(CN)', 'PM10(ug/m3)',
                            'PM1(ug/m3)', 'Outdoor AQI(US)', 'Outdoor AQI(CN)', 'Temperature(C)', 'Temperature(F)',
                            'Humidity(%RH)', 'CO2(ppm)')
        self._last_read = None
        self._offsets = {}

    def _file2events(self, buffer: BytesIO) -> Iterable[Event]:
        tz = Config().timezone_info()
        reader = csv.DictReader(TextIOWrapper(buffer), fieldnames=self._fieldnames, delimiter=';')
        for row in reader:
            if row['Timestamp'] != 'Timestamp':
                value = row['Timestamp']
                timestamp = (datetime
                             # parse without machine tz
                             .utcfromtimestamp(int(value))
                             # override real tz
                             .replace(tzinfo=tz)
                             # convert to utc
                             .astimezone(timezone.utc)
                             # remove tz for driver to skip conversion
                             .replace(tzinfo=None))
                yield Event(timestamp=timestamp,
                            tz=str(tz),
                            pm1=row['PM1(ug/m3)'],
                            pm2_5=row['PM2_5(ug/m3)'],
                            pm10=row['PM10(ug/m3)'],
                            aqi_us=row['AQI(US)'],
                            aqi_ch=row['AQI(CN)'],
                            outdoor_aqi_us=row['Outdoor AQI(US)'],
                            outdoor_aqi_ch=row['Outdoor AQI(CN)'],
                            temperature=row['Temperature(C)'],
                            humidity=row['Humidity(%RH)'],
                            co2=row['CO2(ppm)'])

    def _load_buffer(self, buf: BytesIO):
        cnt = 0
        events = iter_batch(self._file2events(buf), 512)
        for batch in events:
            cnt += self._db.insert([i.dict() for i in batch])
        return cnt

    @timeit
    def load_all_files(self):
        cnt = 0
        for name, buf in self._share.retrieve_all():
            cnt += self._load_buffer(buf)
            logger.info('Load %s events from %s', cnt, name)
        return cnt

    @timeit
    def load_modified_files(self):
        tz = Config().timezone_info()
        cnt = 0
        now = datetime.now(tz=tz)
        if not self._last_read:
            self._last_read = datetime.fromtimestamp(0, tz)
        logger.debug('Read last modified from %s with offsets %s', self._last_read.isoformat(), self._offsets)
        for name, offset, buffer in self._share.tail(self._last_read, self._offsets, tz):
            logger.debug('Read %s bytes from %s', buffer.__sizeof__(), name)
            cnt += self._load_buffer(buffer)
            self._offsets[name] = offset
        self._last_read = now
        logger.info('Load %s events', cnt)
        return cnt

    async def load_task(self, loop: BaseEventLoop):
        await asyncio.sleep(2)
        delta = Config().refresh_duration
        logger.info('Start task for loading events every %s', delta)
        while loop.is_running():
            await loop.run_in_executor(None, self.load_modified_files)
            await asyncio.sleep(delta.total_seconds())
