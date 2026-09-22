"""外部数据层：演示用户档案与使用记录（SQLite）

数据来源：data/external/records.csv（CSV 是源，DB 是派生，故 demo.db 不进版本库）
初始化：uv run python -m agent.tools.external_data
"""
import csv
import sqlite3
from contextlib import contextmanager

from utils.config_handler import agent_conf
from utils.logger_handler import logger
from utils.path_tool import get_abs_path

# 演示用户所在城市（CSV 里没有城市字段，仅作演示数据）
_DEMO_CITIES = ["深圳", "合肥", "商丘", "郑州", "北京",
                "上海", "广州", "杭州", "成都", "武汉"]


def _db_path() -> str:
    return get_abs_path(agent_conf["external_db_path"])


def _connect() -> sqlite3.Connection:
    """建一个连接。SQLite 是嵌入式数据库；用短连接可避开多线程/多进程并发问题"""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _session():
    """一次数据库会话：正常提交 / 异常回滚 / 无论如何都关闭连接

    注意 `with sqlite3_conn:` 只管事务语义（正常提交、异常回滚），
    **不负责关闭连接**——所以关闭要放在 finally 里显式做。
    """
    conn = _connect()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_schema() -> None:
    """建表（已存在则跳过）"""
    with _session() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                city    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS usage_records (
                user_id     TEXT NOT NULL,
                month       TEXT NOT NULL,
                feature     TEXT,
                efficiency  TEXT,
                consumables TEXT,
                comparison  TEXT,
                PRIMARY KEY (user_id, month)
            );
        """)


def load_from_csv() -> None:
    """从 CSV 导入使用记录（幂等：先清空再写入）"""
    csv_path = get_abs_path(agent_conf["external_data_path"])
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    with _session() as conn:
        conn.execute("DELETE FROM usage_records")
        conn.executemany(
            "INSERT INTO usage_records"
            " (user_id, month, feature, efficiency, consumables, comparison)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [(r["用户ID"], r["时间"], r["特征"], r["清洁效率"],
              r["耗材"], r["对比"]) for r in rows],
        )

        conn.execute("DELETE FROM users")
        user_ids = sorted({r["用户ID"] for r in rows})
        conn.executemany(
            "INSERT INTO users (user_id, city) VALUES (?, ?)",
            [(uid, _DEMO_CITIES[i % len(_DEMO_CITIES)])
             for i, uid in enumerate(user_ids)],
        )

    logger.info(f"[external_data] 导入完成: {len(rows)} 条使用记录, {len(user_ids)} 个用户")


def get_user_city(user_id: str) -> str:
    """查用户所在城市；用户不存在返回空字符串"""
    with _session() as conn:
        row = conn.execute(
            "SELECT city FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    if row is None:
        logger.warning(f"[external_data] 用户不存在: {user_id}")
        return ""
    return row["city"]


def get_usage_record(user_id: str, month: str) -> dict | None:
    """查使用记录；未找到返回 None"""
    with _session() as conn:
        row = conn.execute(
            "SELECT feature, efficiency, consumables, comparison"
            " FROM usage_records WHERE user_id = ? AND month = ?",
            (user_id, month),
        ).fetchone()
    if row is None:
        logger.warning(f"[external_data] 未找到记录: 用户 {user_id}, 月份 {month}")
        return None
    return {"特征": row["feature"], "效率": row["efficiency"],
            "消耗": row["consumables"], "比较": row["comparison"]}


if __name__ == '__main__':
    init_schema()
    load_from_csv()
    with _session() as conn:
        n = conn.execute("SELECT COUNT(*) FROM usage_records").fetchone()[0]
        months = [r[0] for r in conn.execute(
            "SELECT DISTINCT month FROM usage_records ORDER BY month")]
    print(f"使用记录 {n} 条，月份 {months[0]} ~ {months[-1]}")