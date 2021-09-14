""""""
from datetime import datetime
from sys import intern
from typing import List, Dict

from pymongo import ASCENDING, MongoClient
from pymongo import cursor
from pymongo.database import Database
from pymongo.cursor import Cursor
from pymongo.collection import Collection
from pymongo.results import DeleteResult

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, TickData
from vnpy.trader.database import BaseDatabase, BarOverview
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
        self.bar_collection.create_index(
            [
                ("exchange", ASCENDING),
                ("symbol", ASCENDING),
                ("interval", ASCENDING),
                ("datetime", ASCENDING),
            ],
            unique=True
        )

        # 初始化Tick数据表
        self.tick_collection: Collection = self.db["tick_data"]
        self.tick_collection.create_index(
            [
                ("exchange", ASCENDING),
                ("symbol", ASCENDING),
                ("datetime", ASCENDING),
            ],
            unique=True
        )

        # 初始化K线概览表
        self.overview_collection: Collection = self.db["bar_overview"]
        self.overview_collection.create_index(
            [
                ("exchange", ASCENDING),
                ("symbol", ASCENDING),
                ("interval", ASCENDING),
            ],
            unique=True
        )

    def save_bar_data(self, bars: List[BarData]) -> bool:
        """保存K线数据"""
        overviews: Dict[tuple, BarOverview] = {}

        for bar in bars:
            # 逐个插入
            filter = {
                "symbol": bar.symbol,
                "exchange": bar.exchange.value,
                "datetime": bar.datetime,
                "interval": bar.interval.value,
            }

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

            self.bar_collection.replace_one(filter, d, upsert=True)

        # 更新汇总
        filter = {
            "symbol": bar.symbol,
            "exchange": bar.exchange.value,
            "interval": bar.interval.value 
        }

        overview = self.overview_collection.find_one(filter)

        if not overview:
            overview = {
                "symbol": bar.symbol,
                "exchange": bar.exchange.value,
                "interval": bar.interval.value,
                "count": len(bars),
                "start": bars[0].datetime,
                "end": bars[-1].datetime
            }
        else:
            overview["start"] = min(bars[0].datetime, overview["start"])
            overview["end"] = max(bars[-1].datetime, overview["end"])
            
            c: Cursor = self.bar_collection.find(filter)
            overview["count"] = c.count()

        self.overview_collection.update(filter, overview, upsert=True)

    def save_tick_data(self, ticks: List[TickData]) -> bool:
        """保存TICK数据"""
        for tick in ticks:
            filter = {
                "symbol": tick.symbol,
                "exchange": tick.exchange.value,
                "datetime": tick.datetime,
            }

            d = {
                "symbol": tick.symbol,
                "exchange": tick.exchange.value,
                "datetime": tick.datetime,
                "name": tick.name,
                "volume": tick.volume,
                "turnover": tick.turnover,
                "open_interest": tick.open_interest,
                "last_price": tick.last_price,
                "last_volume": tick.last_volume,
                "limit_up": tick.limit_up,
                "limit_down": tick.limit_down,
                "open_price": tick.open_price,
                "high_price": tick.high_price,
                "low_price": tick.low_price,
                "pre_close": tick.pre_close,
                "bid_price_1": tick.bid_price_1,
                "bid_price_2": tick.bid_price_2,
                "bid_price_3": tick.bid_price_3,
                "bid_price_4": tick.bid_price_4,
                "bid_price_5": tick.bid_price_5,
                "ask_price_1": tick.ask_price_1,
                "ask_price_2": tick.ask_price_2,
                "ask_price_3": tick.ask_price_3,
                "ask_price_4": tick.ask_price_4,
                "ask_price_5": tick.ask_price_5,
                "bid_volume_1": tick.bid_volume_1,
                "bid_volume_2": tick.bid_volume_2,
                "bid_volume_3": tick.bid_volume_3,
                "bid_volume_4": tick.bid_volume_4,
                "bid_volume_5": tick.bid_volume_5,
                "ask_volume_1": tick.ask_volume_1,
                "ask_volume_2": tick.ask_volume_2,
                "ask_volume_3": tick.ask_volume_3,
                "ask_volume_4": tick.ask_volume_4,
                "ask_volume_5": tick.ask_volume_5,
                "localtime": tick.localtime,
            }

            self.tick_collection.replace_one(filter, d, upsert=True)

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
            "exchange": exchange.value,
            "interval": interval.value,
            "datetime": {
                "$gte": start,
                "$lte": end
            }
        }
        
        c: Cursor = self.bar_collection.find(filter)

        bars = []
        for d in c:
            d["exchange"] = Exchange(d["exchange"])
            d["interval"] = Interval(d["interval"])
            d["gateway_name"] = "DB"
            d.pop("_id")

            bar = BarData(**d)
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
        filter = {
            "symbol": symbol,
            "exchange": exchange.values,
            "datetime": {
                "$gte": start,
                "$lte": end
            }
        }
        
        c: Cursor = self.tick_collection.find(filter)

        ticks = []
        for d in c:
            d["exhange"] = Exchange(d["exchange"])
            d["gateway_name"] = "DB"
            d.pop("_id")

            tick =  TickData(**d)
            ticks.append(tick)

        return ticks

    def delete_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval
    ) -> int:
        """删除K线数据"""
        filter = {
            "symbol": symbol,
            "exchange": exchange.value,
            "datetime": datetime,
            "interval": interval.value,
        }

        result = self.bar_collection.delete_many(filter)
        return result.deleted_count

    def delete_tick_data(
        self,
        symbol: str,
        exchange: Exchange
    ) -> int:
        """删除TICK数据"""
        filter = {
            "symbol": symbol,
            "exchange": exchange.value,
            "datetime": datetime,
        }

        result = self.tick_collection.delete_many(filter)
        return result.deleted_count

    def get_bar_overview(self) -> List[BarOverview]:
        """查询数据库中的K线汇总信息"""
        c: Cursor = self.overview_collection.find()

        overviews = []
        for d in c:
            d["exchange"] = Exchange(d["exchange"])
            d["interval"] = Interval(d["interval"])
            d.pop("_id")

            overview = BarOverview(**d)
            overviews.append(overview)

        return overviews

    def init_bar_overview(self) -> None:
        """初始化数据库中的K线汇总信息"""
        pass
