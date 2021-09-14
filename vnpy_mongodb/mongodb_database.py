""""""
from datetime import datetime
from typing import List

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database
from pymongo.cursor import Cursor
from pymongo.collection import Collection

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, TickData
from vnpy.trader.database import (
    BaseDatabase,
    BarOverview,
    DB_TZ,
    convert_tz
)
from vnpy.trader.setting import SETTINGS


class MongodbDatabase(BaseDatabase):
    """MongoDB数据库接口"""

    def __init__(self) -> None:
        """"""
        # 读取配置
        self.database: str = SETTINGS["database.database"]
        self.host: str = SETTINGS["database.host"]
        self.port: int = SETTINGS["database.port"]
        self.username: str = SETTINGS["database.user"]
        self.password: str = SETTINGS["database.password"]

        # 创建客户端
        if self.username and self.password:
            self.client: MongoClient = MongoClient(
                host=self.host,
                port=self.port,
                tz_aware=True,
                username=self.username,
                password=self.password
            )
        else:
            self.client: MongoClient = MongoClient(
                host=self.host,
                port=self.port,
                tz_aware=True
            )

        # 初始化数据库
        self.db: Database = self.client[self.database]

        # 初始化K线数据表
        self.bar_collection: Collection = self.db["bar_data"]
        self.bar_collection.create_index([
            ("exchange", ASCENDING),
            ("symbol", ASCENDING),
            ("interval", ASCENDING),
            ("datetime", ASCENDING),
        ])

        # 初始化Tick数据表
        self.tick_collection: Collection = self.db["tick_data"]

        # 初始化K线概览表
        self.overview_collection: Collection = self.db["bar_overview"]

    def save_bar_data(self, bars: List[BarData]) -> bool:
        """保存K线数据"""
        data = []

        for bar in bars:
            d = {
                "symbol": bar.symbol,
                "exchange": bar.exchange.value,
                "datetime": bar.datetime,
                "interval": bar.interval.value,
                "volume": bar.volume,
                "turnover": bar.turnover,
                "open_interest": bar.open_interest,
                "open_price": bar.open_price,
                "high_price": bar.high_price,
                "low_price": bar.low_price,
                "close_price": bar.close_price,
            }
            data.append(d)

        self.bar_collection.update_many(data)

    def save_tick_data(self, ticks: List[TickData]) -> bool:
        """保存TICK数据"""
        pass

    def load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """读取K线数据"""
        filter = {
            "symbol": symbol,
            "exchange": exchange.values,
            "interval": interval.value,
            "datetime": {
                "$gte": start,
                "$lte": end
            }
        }
        
        c: Cursor = self.bar_collection.find(filter)

        bars = []
        for d in c:
            bar = BarData(
                symbol=d["symbol"],
                exchange=Exchange(d["exchange"]),
                datetime=d["datetime"],
                interval=Interval(d["interval"]),
                volume=d["volume"],
                turnover=d["turnover"],
                open_interest=d["open_interest"],
                open_price=d["open_price"],
                high_price=d["high_price"],
                low_price=d["low_price"],
                close_price=d["close_price"],
            )
            bars.append(bar)
        
        return bars

    def load_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """读取TICK数据"""
        pass

    def delete_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval
    ) -> int:
        """删除K线数据"""
        pass

    def delete_tick_data(
        self,
        symbol: str,
        exchange: Exchange
    ) -> int:
        """删除TICK数据"""
        pass

    def get_bar_overview(self) -> List[BarOverview]:
        """查询数据库中的K线汇总信息"""
        pass

    def init_bar_overview(self) -> None:
        """初始化数据库中的K线汇总信息"""
        pass
