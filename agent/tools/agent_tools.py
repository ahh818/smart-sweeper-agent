from rag.rag_service import RagSummarizeService
import random
from langchain_core.tools import tool
from utils.logger_handler import logger
import os
from utils.config_handler import agent_conf
from utils.path_tool import get_abs_path
import httpx




# ============ 模拟数据（真实项目会换成真实 API / 数据库） ============
user_ids = ["1001", "1002", "1003", "1004", "1006", "1007", "10086"]
month_arr = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"]
# 使用记录"柜子"：模块级，第一次用到时由 generate_external_data 装满
external_data = {}

# ============ 天气：Open-Meteo（免费，无需 API Key）============
_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO 天气代码 → 中文描述
_WMO_CODE = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "毛毛雨", 53: "小雨", 55: "中雨",
    56: "冻毛毛雨", 57: "冻雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "阵雨", 81: "强阵雨", 82: "暴雨",
    85: "阵雪", 86: "强阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷暴伴冰雹",
}

_WIND_DIRS = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]


def _wind_direction(degrees: float) -> str:
    """风向角度 → 八方位中文"""
    return _WIND_DIRS[round(degrees / 45) % 8] + "风"


@tool(description="获取指定城市的实时天气情况")
def get_weather(city: str) -> str:
    """两步调用 Open-Meteo：地理编码拿经纬度 → 取实时天气"""
    try:
        geo = httpx.get(
            _GEO_URL,
            params={"name": city, "count": 1, "language": "zh"},
            timeout=8,
        ).json()
        results = geo.get("results")
        if not results:
            logger.warning(f"[get_weather] 找不到城市: {city}")
            return ""
        loc = results[0]

        fc = httpx.get(
            _FORECAST_URL,
            params={
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,"
                           "wind_direction_10m,weather_code",
                "timezone": "auto",
            },
            timeout=8,
        ).json()
        cur = fc["current"]

        desc = _WMO_CODE.get(cur["weather_code"], f"未知天气({cur['weather_code']})")
        return (f"{loc['name']}：{desc}，气温 {cur['temperature_2m']}°C，"
                f"相对湿度 {cur['relative_humidity_2m']}%，"
                f"{_wind_direction(cur['wind_direction_10m'])} {cur['wind_speed_10m']} km/h")
    except Exception as e:
        logger.error(f"[get_weather] 获取 {city} 天气失败: {e}")
        return ""

@tool(description="获取用户所在的城市名称,以纯字符串形式返回")
def get_user_location() -> str:
    return random.choice(["深圳", "合肥", "商丘", "郑州"])


@tool(description="获取用户ID,以纯字符串形式返回")
def get_user_id() -> str:
    return random.choice(user_ids)

@tool(description="获取当前年月,以纯字符串形式返回")
def get_current_month() -> str:
    return random.choice(month_arr)

# 模块级单例：整个项目共享这一个 RAG 服务
rag = RagSummarizeService()

@tool(description="从知识库中检索扫地机器人相关的专业参考资料")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)

def generate_external_data():
    """把 CSV 使用记录读进内存，做成二维字典
    结构: external_data[用户ID][月份] = {"特征":..., "效率":..., "消耗":..., "比较":...}
    """
    if not external_data:                                   # 只加载一次
        external_data_path = get_abs_path(agent_conf["external_data_path"])

        if not os.path.exists(external_data_path):
            raise FileExistsError(f"文件不存在: {external_data_path}")

        with open(external_data_path, "r", encoding="utf-8") as f:
            for line in f.readlines()[1:]:                  # [1:] 跳过表头
                arr = line.strip().split(",")

                user_id = arr[0].replace('"', '')
                feature = arr[1].replace('"', '')
                efficiency = arr[2].replace('"', '')
                consumables = arr[3].replace('"', '')
                comparison = arr[4].replace('"', '')
                time = arr[5].replace('"', '')

                if user_id not in external_data:
                    external_data[user_id] = {}

                external_data[user_id][time] = {
                    "特征": feature,
                    "效率": efficiency,
                    "消耗": consumables,
                    "比较": comparison,
                }

@tool(description="从外部系统获取指定用户在指定月份的使用记录，以纯字符串形式返回，未检索到则返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str:
    generate_external_data()   # 确保"柜子"已装好（惰性加载的入口）
    try:
        return str(external_data[user_id][month])
    except KeyError:
        logger.warning(f"用户ID: {user_id}, 月份: {month} 不存在，未能检索到数据")
        return ""

@tool(description="仅在用户明确要求生成/查询个人使用报告时调用；调用后触发系统切换到报告生成模式，无入参、无返回值")
def fill_context_for_report() -> str:
    return "fill_context_for_report已调用"


if __name__ == '__main__':
    print(fetch_external_data.invoke({"user_id": "1001", "month": "2025-01"}))  # 正常查得到
    print(fetch_external_data.invoke({"user_id": "9999", "month": "2025-01"}))  # 用户不存在
    print(fetch_external_data.invoke({"user_id": "1001", "month": "2099-01"}))  # 月份不存在

