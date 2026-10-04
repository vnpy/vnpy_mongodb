from datetime import datetime

import pytest
from pymongo import ASCENDING, ReplaceOne

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import DB_TZ
from vnpy.trader.object import BarData, TickData
from vnpy.trader.setting import SETTINGS
from vnpy_mongodb.mongodb_database import MongodbDatabase
import vnpy_mongodb.mongodb_database as mongo_db


SETTINGS["database.database"] = "vnpy_test"
SETTINGS["database.host"] = "127.0.0.1"
SETTINGS["database.port"] = 27017
SETTINGS["database.user"] = ""
SETTINGS["database.password"] = ""


class _DeleteResult:
    def __init__(self, count: int) -> None:
        self.deleted_count = count


class _Collection:
    def __init__(self, name: str) -> None:
        self.name = name
        self.indexes: list[tuple[object, bool]] = []
        self.bulk: list[object] = []
        self.ordered: list[bool] = []
        self.find_filters: list[dict[str, object]] = []
        self.find_one_filters: list[dict[str, object]] = []
        self.updates: list[tuple[dict[str, object], dict[str, object], bool]] = []
        self.deleted: list[tuple[str, dict[str, object]]] = []
        self.find_docs: list[dict[str, object]] = []

    def create_index(self, keys: object, unique: bool = False) -> str:
        self.indexes.append((keys, unique))
        return "index"

    def bulk_write(self, requests: list[object], ordered: bool = True) -> None:
        self.ordered.append(ordered)
        self.bulk.extend(requests)

    def find_one(self, query: dict[str, object]) -> None:
        self.find_one_filters.append(query)
        return None

    def find(self, query: dict[str, object]) -> list[dict[str, object]]:
        self.find_filters.append(query)
        return [dict(doc) for doc in self.find_docs]

    def count_documents(self, query: dict[str, object]) -> int:
        del query
        return 0

    def update_one(
        self,
        query: dict[str, object],
        update: dict[str, object],
        upsert: bool = False,
    ) -> None:
        self.updates.append((query, update, upsert))

    def delete_many(self, query: dict[str, object]) -> _DeleteResult:
        self.deleted.append(("many", query))
        return _DeleteResult(2)

    def delete_one(self, query: dict[str, object]) -> _DeleteResult:
        self.deleted.append(("one", query))
        return _DeleteResult(1)


class _Database:
    def __init__(self) -> None:
        self.collections: dict[str, _Collection] = {}

    def __getitem__(self, name: str) -> _Collection:
        if name not in self.collections:
            self.collections[name] = _Collection(name)
        return self.collections[name]


class _Client:
    def __init__(self, *_args: object, **kwargs: object) -> None:
        self.args = _args
        self.kwargs = kwargs
        self.names: list[str] = []
        self.database = _Database()

    def __getitem__(self, name: str) -> _Database:
        self.names.append(name)
        return self.database


def _make_bars(symbol: str) -> list[BarData]:
    start: datetime = datetime(2024, 1, 15, 10, 0, tzinfo=DB_TZ)
    end: datetime = datetime(2024, 1, 15, 10, 1, tzinfo=DB_TZ)
    return [
        BarData(
            gateway_name="TEST",
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=start,
            interval=Interval.MINUTE,
            volume=12.0,
            turnover=1.5,
            open_interest=3.0,
            open_price=100.0,
            high_price=110.0,
            low_price=90.0,
            close_price=105.0,
        ),
        BarData(
            gateway_name="TEST",
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=end,
            interval=Interval.MINUTE,
            volume=8.0,
            turnover=0.0,
            open_interest=0.0,
            open_price=105.0,
            high_price=112.0,
            low_price=101.0,
            close_price=108.0,
        ),
    ]


def _make_ticks(symbol: str) -> list[TickData]:
    start: datetime = datetime(2024, 1, 16, 10, 0, tzinfo=DB_TZ)
    end: datetime = datetime(2024, 1, 16, 10, 0, 1, tzinfo=DB_TZ)
    return [
        TickData(
            gateway_name="TEST",
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=start,
            name="au",
            last_price=400.5,
            volume=20.0,
            localtime=start,
        ),
        TickData(
            gateway_name="TEST",
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=end,
            name="au",
            last_price=401.0,
            volume=21.0,
            localtime=end,
        ),
    ]


@pytest.fixture
def database(monkeypatch: pytest.MonkeyPatch) -> MongodbDatabase:
    monkeypatch.setattr(mongo_db, "MongoClient", _Client)
    return MongodbDatabase()


def test_save_bar_data_upserts_ohlcv_document(database: MongodbDatabase) -> None:
    symbol: str = "rb2405"
    bars: list[BarData] = _make_bars(symbol)
    client: _Client = database.client
    assert client.kwargs["host"] == "127.0.0.1"
    assert client.kwargs["port"] == 27017
    assert client.kwargs["tz_aware"] is True
    assert client.kwargs["tzinfo"] == DB_TZ
    assert "username" not in client.kwargs
    assert client.names == ["vnpy_test"]

    assert database.save_bar_data(bars) is True
    collection: _Collection = database.bar_collection
    assert collection.name == "bar_data"
    assert collection.ordered == [False]
    assert len(collection.bulk) == 2

    first: ReplaceOne = collection.bulk[0]
    assert isinstance(first, ReplaceOne)
    assert first._upsert is True
    assert first._filter == {
        "symbol": symbol,
        "exchange": Exchange.SHFE.value,
        "datetime": bars[0].datetime,
        "interval": Interval.MINUTE.value,
    }
    assert first._doc["open_price"] == 100.0
    assert first._doc["high_price"] == 110.0
    assert first._doc["low_price"] == 90.0
    assert first._doc["close_price"] == 105.0
    assert first._doc["volume"] == 12.0
    assert first._doc["turnover"] == 1.5
    assert first._doc["open_interest"] == 3.0
    assert "gateway_name" not in first._doc

    second: ReplaceOne = collection.bulk[1]
    assert isinstance(second, ReplaceOne)
    assert second._filter["datetime"] == bars[1].datetime
    assert second._doc["close_price"] == 108.0
    assert second._doc["volume"] == 8.0

    overview: _Collection = database.bar_overview_collection
    assert overview.find_one_filters == [
        {
            "symbol": symbol,
            "exchange": Exchange.SHFE.value,
            "interval": Interval.MINUTE.value,
        }
    ]
    query, update, upsert = overview.updates[0]
    assert upsert is True
    assert query == overview.find_one_filters[0]
    assert update["$set"]["count"] == 2
    assert update["$set"]["start"] == bars[0].datetime
    assert update["$set"]["end"] == bars[-1].datetime
    assert collection.indexes[0][1] is True
    assert collection.indexes[0][0] == [
        ("exchange", ASCENDING),
        ("symbol", ASCENDING),
        ("interval", ASCENDING),
        ("datetime", ASCENDING),
    ]


def test_load_bar_data_filters_symbol_and_datetime_bounds(database: MongodbDatabase) -> None:
    symbol: str = "rb2405"
    start: datetime = datetime(2024, 1, 1, tzinfo=DB_TZ)
    end: datetime = datetime(2024, 2, 1, tzinfo=DB_TZ)
    bar_dt: datetime = datetime(2024, 1, 15, 10, 0, tzinfo=DB_TZ)
    collection: _Collection = database.bar_collection
    collection.find_docs.append(
        {
            "_id": "bar-1",
            "symbol": symbol,
            "exchange": Exchange.SHFE.value,
            "datetime": bar_dt,
            "interval": Interval.MINUTE.value,
            "volume": 12.0,
            "turnover": 1.5,
            "open_interest": 3.0,
            "open_price": 100.0,
            "high_price": 110.0,
            "low_price": 90.0,
            "close_price": 105.0,
        }
    )

    loaded: list[BarData] = database.load_bar_data(
        symbol,
        Exchange.SHFE,
        Interval.MINUTE,
        start,
        end,
    )
    assert collection.find_filters == [
        {
            "symbol": symbol,
            "exchange": Exchange.SHFE.value,
            "interval": Interval.MINUTE.value,
            "datetime": {
                "$gte": start.astimezone(DB_TZ),
                "$lte": end.astimezone(DB_TZ),
            },
        }
    ]
    assert len(loaded) == 1
    assert loaded[0].symbol == symbol
    assert loaded[0].exchange == Exchange.SHFE
    assert loaded[0].interval == Interval.MINUTE
    assert loaded[0].datetime == bar_dt
    assert loaded[0].volume == 12.0
    assert loaded[0].open_price == 100.0
    assert loaded[0].high_price == 110.0
    assert loaded[0].low_price == 90.0
    assert loaded[0].close_price == 105.0
    assert loaded[0].gateway_name == "DB"


def test_delete_bar_data_uses_symbol_exchange_interval(database: MongodbDatabase) -> None:
    symbol: str = "rb2405"
    count: int = database.delete_bar_data(symbol, Exchange.SHFE, Interval.MINUTE)
    assert count == 2
    key: dict[str, object] = {
        "symbol": symbol,
        "exchange": Exchange.SHFE.value,
        "interval": Interval.MINUTE.value,
    }
    assert database.bar_collection.deleted == [("many", key)]
    assert database.bar_overview_collection.deleted == [("one", key)]


def test_save_tick_data_upserts_last_price(database: MongodbDatabase) -> None:
    symbol: str = "au2406"
    ticks: list[TickData] = _make_ticks(symbol)
    assert database.save_tick_data(ticks) is True
    collection: _Collection = database.tick_collection
    assert collection.ordered == [False]
    assert len(collection.bulk) == 2
    first: ReplaceOne = collection.bulk[0]
    assert isinstance(first, ReplaceOne)
    assert first._upsert is True
    assert first._filter == {
        "symbol": symbol,
        "exchange": Exchange.SHFE.value,
        "datetime": ticks[0].datetime,
    }
    assert first._doc["name"] == "au"
    assert first._doc["last_price"] == 400.5
    assert first._doc["volume"] == 20.0
    assert first._doc["localtime"] == ticks[0].localtime
    assert "gateway_name" not in first._doc

    second: ReplaceOne = collection.bulk[1]
    assert isinstance(second, ReplaceOne)
    assert second._doc["last_price"] == 401.0
    assert second._doc["volume"] == 21.0

    overview: _Collection = database.tick_overview_collection
    query, update, upsert = overview.updates[0]
    assert upsert is True
    assert query == {"symbol": symbol, "exchange": Exchange.SHFE.value}
    assert update["$set"]["count"] == 2
    assert update["$set"]["start"] == ticks[0].datetime
    assert update["$set"]["end"] == ticks[-1].datetime


def test_load_tick_data_filters_symbol_and_datetime_bounds(database: MongodbDatabase) -> None:
    symbol: str = "au2406"
    start: datetime = datetime(2024, 1, 1, tzinfo=DB_TZ)
    end: datetime = datetime(2024, 2, 1, tzinfo=DB_TZ)
    tick_dt: datetime = datetime(2024, 1, 16, 10, 0, tzinfo=DB_TZ)
    collection: _Collection = database.tick_collection
    collection.find_docs.append(
        {
            "_id": "tick-1",
            "symbol": symbol,
            "exchange": Exchange.SHFE.value,
            "datetime": tick_dt,
            "name": "au",
            "volume": 20.0,
            "turnover": 0.0,
            "open_interest": 0.0,
            "last_price": 400.5,
            "last_volume": 0.0,
            "limit_up": 0.0,
            "limit_down": 0.0,
            "open_price": 0.0,
            "high_price": 0.0,
            "low_price": 90.0,
            "pre_close": 0.0,
            "bid_price_1": 0.0,
            "bid_price_2": 0.0,
            "bid_price_3": 0.0,
            "bid_price_4": 0.0,
            "bid_price_5": 0.0,
            "ask_price_1": 0.0,
            "ask_price_2": 0.0,
            "ask_price_3": 0.0,
            "ask_price_4": 0.0,
            "ask_price_5": 0.0,
            "bid_volume_1": 0.0,
            "bid_volume_2": 0.0,
            "bid_volume_3": 0.0,
            "bid_volume_4": 0.0,
            "bid_volume_5": 0.0,
            "ask_volume_1": 0.0,
            "ask_volume_2": 0.0,
            "ask_volume_3": 0.0,
            "ask_volume_4": 0.0,
            "ask_volume_5": 0.0,
            "localtime": tick_dt,
        }
    )
    loaded: list[TickData] = database.load_tick_data(symbol, Exchange.SHFE, start, end)
    assert collection.find_filters == [
        {
            "symbol": symbol,
            "exchange": Exchange.SHFE.value,
            "datetime": {
                "$gte": start.astimezone(DB_TZ),
                "$lte": end.astimezone(DB_TZ),
            },
        }
    ]
    assert len(loaded) == 1
    assert loaded[0].symbol == symbol
    assert loaded[0].last_price == 400.5
    assert loaded[0].low_price == 90.0
    assert loaded[0].volume == 20.0
    assert loaded[0].localtime == tick_dt
    assert loaded[0].gateway_name == "DB"


def test_delete_tick_data_uses_symbol_and_exchange(database: MongodbDatabase) -> None:
    symbol: str = "au2406"
    count: int = database.delete_tick_data(symbol, Exchange.SHFE)
    assert count == 2
    key: dict[str, object] = {
        "symbol": symbol,
        "exchange": Exchange.SHFE.value,
    }
    assert database.tick_collection.deleted == [("many", key)]
    assert database.tick_overview_collection.deleted == [("one", key)]
