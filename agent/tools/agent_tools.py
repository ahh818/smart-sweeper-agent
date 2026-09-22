from rag.rag_service import RagSummarizeService
from langchain_core.tools import tool
from utils.logger_handler import logger
import httpx
from agent.tools import external_data
from datetime import datetime




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
    return external_data.get_user_city(external_data.get_current_user_id())


@tool(description="获取用户ID,以纯字符串形式返回")
def get_user_id() -> str:
    return external_data.get_current_user_id()

@tool(description="获取当前年月,以纯字符串形式返回")
def get_current_month() -> str:
    return datetime.now().strftime("%Y-%m")

# 模块级单例：整个项目共享这一个 RAG 服务
rag = RagSummarizeService()

@tool(description="从知识库中检索扫地机器人相关的专业参考资料")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)



@tool(description="从外部系统获取指定用户在指定月份的使用记录，以纯字符串形式返回，未检索到则返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str:
    record = external_data.get_usage_record(user_id, month)
    return str(record) if record else ""

@tool(description="仅在用户明确要求生成/查询个人使用报告时调用；调用后触发系统切换到报告生成模式，无入参、无返回值")
def fill_context_for_report() -> str:
    return "fill_context_for_report已调用"


if __name__ == '__main__':
    print(fetch_external_data.invoke({"user_id": "1001", "month": "2025-01"}))  # 正常查得到
    print(fetch_external_data.invoke({"user_id": "9999", "month": "2025-01"}))  # 用户不存在
    print(fetch_external_data.invoke({"user_id": "1001", "month": "2099-01"}))  # 月份不存在

