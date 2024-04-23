from datetime import datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, AnyUrl
from pydantic_settings import BaseSettings
from pytz import timezone


class Config(BaseSettings):
    clickhouse_url: AnyUrl
    device_service_name: str = 'airvisual'
    device_host: str
    device_username: str = 'airvisual'
    device_password: str
    refresh_duration: timedelta = timedelta(minutes=10)
    timezone: str

    def timezone_info(self):
        return timezone(self.timezone)


class Event(BaseModel):
    timestamp: datetime
    tz: str
    pm1: Decimal
    pm2_5: Decimal
    pm10: Decimal
    aqi_us: int
    aqi_ch: int
    outdoor_aqi_us: int
    outdoor_aqi_ch: int
    temperature: Decimal
    humidity: int
    co2: int


class File(BaseModel):
    name: str
    size: int
    created: datetime
    updated: datetime
