"""
数据分析师插件 - 数据模型模块

定义插件使用的数据模型、配置类和常量
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class AnalysisType(Enum):
    """分析类型枚举"""
    ACTIVITY = "activity"
    USER = "user" 
    TOPICS = "topics"


class ChartType(Enum):
    """图表类型枚举"""
    ACTIVITY = "activity"
    RANKING = "ranking"
    WORDCLOUD = "wordcloud"
    HEATMAP = "heatmap"


class ExportFormat(Enum):
    """导出格式枚举"""
    EXCEL = "excel"
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"


class TimePeriod(Enum):
    """时间周期枚举"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class MessageData:
    """
    /// 消息数据模型
    /// 表示单条消息的基础信息
    """
    message_id: str
    user_id: str
    group_id: Optional[str]
    platform: str
    content_hash: str
    message_type: str = "text"
    timestamp: datetime = None
    word_count: int = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class UserStats:
    """
    /// 用户统计数据模型
    /// 包含用户的活跃度和行为统计
    """
    user_id: str
    username: str = ""
    total_messages: int = 0
    total_words: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    active_days: int = 0
    avg_words_per_msg: float = 0.0
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class GroupStats:
    """
    /// 群组统计数据模型
    /// 包含群组的整体活跃度信息
    """
    group_id: str
    group_name: str = ""
    total_messages: int = 0
    total_members: int = 0
    peak_hour: int = 0
    most_active_day: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class TopicKeyword:
    """
    /// 话题关键词数据模型
    /// 表示单个关键词的统计信息
    """
    keyword: str
    group_id: str
    frequency: int = 1
    last_mentioned: datetime = None
    sentiment_score: float = 0.0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.last_mentioned is None:
            self.last_mentioned = datetime.now()
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class AnalysisResult:
    """
    /// 分析结果数据模型
    /// 统一的分析结果格式
    """
    analysis_type: str
    text_result: str
    chart_path: Optional[str] = None
    data: Optional[Dict] = None
    metadata: Optional[Dict] = None
    generated_at: datetime = None
    
    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()


@dataclass
class ActivityAnalysisData:
    """
    /// 活跃度分析数据模型
    /// 包含活跃度分析的所有统计信息
    """
    total_messages: int
    active_users: int
    avg_daily_messages: float
    growth_rate: float
    peak_hour: str
    peak_day: str
    trend_description: str
    daily_data: List[tuple]
    timespan_days: int = 0
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'total_messages': self.total_messages,
            'active_users': self.active_users,
            'avg_daily_messages': self.avg_daily_messages,
            'growth_rate': self.growth_rate,
            'peak_hour': self.peak_hour,
            'peak_day': self.peak_day,
            'trend_description': self.trend_description,
            'daily_data': self.daily_data,
            'timespan_days': self.timespan_days
        }


@dataclass
class UserAnalysisData:
    """
    /// 用户行为分析数据模型
    /// 包含个人用户的行为分析结果
    """
    message_count: int
    avg_length: float
    active_days: int
    participation_rate: float
    most_active_hour: str
    avg_interval: str
    behavior_description: str
    activity_pattern: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'message_count': self.message_count,
            'avg_length': self.avg_length,
            'active_days': self.active_days,
            'participation_rate': self.participation_rate,
            'most_active_hour': self.most_active_hour,
            'avg_interval': self.avg_interval,
            'behavior_description': self.behavior_description,
            'activity_pattern': self.activity_pattern or {}
        }


@dataclass
class TopicsAnalysisData:
    """
    /// 话题分析数据模型
    /// 包含话题热度和关键词分析结果
    """
    top_topics: List[Dict]
    new_topics_count: int
    topic_activity: float
    discussion_depth: float
    category_summary: str
    keywords_data: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'top_topics': self.top_topics,
            'new_topics_count': self.new_topics_count,
            'topic_activity': self.topic_activity,
            'discussion_depth': self.discussion_depth,
            'category_summary': self.category_summary,
            'keywords_data': self.keywords_data or {}
        }


@dataclass
class PredictionResult:
    """
    /// 预测结果数据模型
    /// 包含预测分析的结果和置信度
    """
    predictions: List[float]
    confidence: float
    trend_direction: str
    change_percent: float
    description: str
    chart_path: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'predictions': self.predictions,
            'confidence': self.confidence,
            'trend_direction': self.trend_direction,
            'change_percent': self.change_percent,
            'description': self.description,
            'chart_path': self.chart_path
        }


class PluginConfig:
    """
    /// 插件配置管理类
    /// 统一管理所有配置项的访问和默认值
    """
    
    def __init__(self, config: Dict):
        self.config = config
    
    @property
    def data_retention_days(self) -> int:
        """数据保留天数"""
        return self.config.get("data_retention_days", 90)
    
    @property
    def privacy_settings(self) -> Dict:
        """隐私设置"""
        return self.config.get("privacy_settings", {})
    
    @property
    def enable_content_hash(self) -> bool:
        """是否启用内容哈希"""
        return self.privacy_settings.get("enable_content_hash", True)
    
    @property
    def sensitive_keywords(self) -> List[str]:
        """敏感关键词列表"""
        return self.privacy_settings.get("sensitive_keywords", 
                                       ["手机", "身份证", "密码", "银行卡", "地址"])
    
    @property
    def analysis_settings(self) -> Dict:
        """分析设置"""
        return self.config.get("analysis_settings", {})
    
    @property
    def cache_ttl(self) -> int:
        """缓存有效期"""
        return self.analysis_settings.get("cache_ttl", 1800)
    
    @property
    def min_data_threshold(self) -> int:
        """最小数据阈值"""
        return self.analysis_settings.get("min_data_threshold", 10)
    
    @property
    def max_chart_items(self) -> int:
        """图表最大项目数"""
        return self.analysis_settings.get("max_chart_items", 20)
    
    @property
    def permission_control(self) -> Dict:
        """权限控制设置"""
        return self.config.get("permission_control", {})
    
    @property
    def admin_users(self) -> List[str]:
        """管理员用户列表"""
        return self.permission_control.get("admin_users", [])
    
    @property
    def allowed_groups(self) -> List[str]:
        """允许使用的群组列表"""
        return self.permission_control.get("allowed_groups", [])
    
    @property
    def enable_auto_collect(self) -> bool:
        """是否启用自动收集"""
        return self.permission_control.get("enable_auto_collect", True)
    
    @property
    def chart_settings(self) -> Dict:
        """图表设置"""
        return self.config.get("chart_settings", {})
    
    @property
    def chart_dpi(self) -> int:
        """图表DPI"""
        return self.chart_settings.get("dpi", 150)
    
    @property
    def chart_style(self) -> str:
        """图表样式"""
        return self.chart_settings.get("style", "seaborn-v0_8")
    
    @property
    def color_palette(self) -> str:
        """色彩方案"""
        return self.chart_settings.get("color_palette", "husl")


class DatabaseConstants:
    """
    /// 数据库常量定义
    /// 统一管理数据库相关的常量
    """
    
    # 表名
    TABLE_MESSAGES = "messages"
    TABLE_USER_STATS = "user_stats"
    TABLE_GROUP_STATS = "group_stats"
    TABLE_TOPIC_KEYWORDS = "topic_keywords"
    TABLE_ANALYSIS_CACHE = "analysis_cache"
    
    # 消息类型
    MESSAGE_TYPE_TEXT = "text"
    MESSAGE_TYPE_IMAGE = "image"
    MESSAGE_TYPE_VOICE = "voice"
    MESSAGE_TYPE_VIDEO = "video"
    MESSAGE_TYPE_FILE = "file"
    
    # 默认值
    DEFAULT_WORD_COUNT = 0
    DEFAULT_FREQUENCY = 1
    DEFAULT_SENTIMENT = 0.0
    
    # 索引名称
    IDX_MESSAGES_TIMESTAMP = "idx_messages_timestamp"
    IDX_MESSAGES_GROUP_ID = "idx_messages_group_id"
    IDX_MESSAGES_USER_ID = "idx_messages_user_id"
    IDX_TOPIC_KEYWORDS_GROUP_ID = "idx_topic_keywords_group_id"


class ChartConstants:
    """
    /// 图表常量定义
    /// 统一管理图表相关的常量和配置
    """
    
    # 默认图表尺寸
    DEFAULT_FIGURE_SIZE = (10, 6)
    WORDCLOUD_SIZE = (800, 400)
    HEATMAP_SIZE = (12, 8)
    
    # 现代化颜色方案
    COLOR_PALETTES = {
        "modern_blue": ["#667eea", "#764ba2", "#f093fb", "#f5576c", "#4facfe", "#00f2fe"],
        "sunset": ["#fa709a", "#fee140", "#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4"],
        "ocean": ["#667db6", "#0082c8", "#0078ff", "#00d2ff", "#3a7bd5", "#3a6073"],
        "forest": ["#11998e", "#38ef7d", "#56ab2f", "#a8edea", "#fed6e3", "#d299c2"],
        "vibrant": ["#ff6b6b", "#4ecdc4", "#45b7d1", "#f9ca24", "#6c5ce7", "#fd79a8"],
        "professional": ["#2d3436", "#636e72", "#74b9ff", "#0984e3", "#00b894", "#00cec9"],
        "husl": "husl",
        "Set2": "Set2", 
        "viridis": "viridis",
        "plasma": "plasma",
        "tab10": "tab10"
    }
    
    # 渐变色方案
    GRADIENT_COLORS = {
        "blue_gradient": ["#667eea", "#764ba2"],
        "sunset_gradient": ["#fa709a", "#fee140"],
        "ocean_gradient": ["#667db6", "#0082c8"],
        "green_gradient": ["#11998e", "#38ef7d"]
    }
    
    # 字体设置 - 优化中文字体支持
    CHINESE_FONTS = [
        'Microsoft YaHei',     # 微软雅黑 (Windows 推荐)
        'SimHei',              # 黑体
        'SimSun',              # 宋体
        'KaiTi',               # 楷体
        'FangSong',            # 仿宋
        'Heiti SC',            # macOS 黑体
        'PingFang SC',         # macOS 苹方
        'WenQuanYi Micro Hei', # Linux 文泉驿
        'Noto Sans CJK SC',    # Google Noto
        'DejaVu Sans',         # 备用字体
        'Arial Unicode MS',    # 备用字体
        'sans-serif'           # 系统默认
    ]
    DEFAULT_FONT_SIZE = 11
    TITLE_FONT_SIZE = 16
    LABEL_FONT_SIZE = 12
    
    # 文件名模板
    ACTIVITY_CHART_TEMPLATE = "activity_trend_{group_id}_{timestamp}.png"
    WORDCLOUD_TEMPLATE = "topics_wordcloud_{group_id}_{timestamp}.png"
    RANKING_CHART_TEMPLATE = "user_ranking_{group_id}_{timestamp}.png"
    HEATMAP_TEMPLATE = "activity_heatmap_{group_id}_{timestamp}.png"


class ExportConstants:
    """
    /// 导出常量定义
    /// 统一管理导出功能的常量
    """
    
    # 文件名模板
    EXCEL_TEMPLATE = "analysis_report_{group_id}_{period}_{timestamp}.xlsx"
    PDF_TEMPLATE = "analysis_report_{group_id}_{period}_{timestamp}.pdf"
    CSV_TEMPLATE = "analysis_data_{group_id}_{period}_{timestamp}.csv"
    JSON_TEMPLATE = "analysis_data_{group_id}_{period}_{timestamp}.json"
    
    # Excel工作表名称
    SHEET_ACTIVITY = "活跃度统计"
    SHEET_TOPICS = "热门话题"
    SHEET_SUMMARY = "分析摘要"
    SHEET_USER_RANKING = "用户排行"
    
    # 报告标题
    REPORT_TITLE = "群组数据分析报告"
    
    # 最大导出行数
    MAX_EXPORT_ROWS = 10000
