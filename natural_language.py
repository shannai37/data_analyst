"""
自然语言处理器

提供自然语言命令识别和解析功能
支持中文自然语言与插件功能的映射
"""

import re
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from astrbot.api import logger


class CommandType(Enum):
    """命令类型枚举"""
    WORDCLOUD = "wordcloud"
    STATS = "stats"  
    PORTRAIT = "portrait"    # Phase 3 新增：用户画像
    HELP = "help"
    UNKNOWN = "unknown"


class TimeRange(Enum):
    """时间范围枚举"""
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"


@dataclass
class CommandIntent:
    """命令意图数据模型"""
    command_type: CommandType
    original_message: str
    confidence: float
    time_range: Optional[TimeRange] = None
    target_user: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class NaturalLanguageProcessor:
    """
    自然语言处理器
    
    功能特色：
    - 中文自然语言命令识别
    - 意图分析和参数提取
    - 置信度评估
    - 多种命令类型支持
    """
    
    def __init__(self, db_manager=None):
        """
        初始化自然语言处理器
        
        Args:
            db_manager: 数据库管理器（可选）
        """
        self.db_manager = db_manager
        
        # 🔥 扩展中文自然语言命令关键词
        self.command_keywords = {
            CommandType.WORDCLOUD: [
                # 基础词云相关
                "词云", "热词", "关键词", "话题统计", "聊什么", "关键字", "文字云",
                "话题", "词频", "文字统计", "聊天内容", "讨论什么", "主要内容",
                "热门话题", "流行词汇", "常用词", "高频词", "话题分析",
                
                # 🔥 更自然的中文表达
                "大家都在聊什么", "最近聊什么", "主要说什么", "热门词汇",
                "看看话题", "分析话题", "群里聊什么", "最热话题",
                "关键词汇", "词汇统计", "文字分析", "内容分析",
                
                # 时间相关
                "今日词云", "今天词云", "最近词云", "本周词云", "本月词云",
                "今天聊什么", "最近热词", "本周话题", "今日热词",
                "今天的词云", "最近的热词", "这周聊什么",
                
                # 样式相关
                "简约词云", "现代词云", "游戏词云", "科技词云", "优雅词云",
                "好看的词云", "漂亮词云", "酷炫词云", "精美词云",
                
                # 对比相关
                "词云对比", "词云变化", "词云趋势", "热词变化", "话题变化",
                "对比词云", "趋势分析", "变化分析"
            ],
            
            CommandType.STATS: [
                # 基础统计相关
                "数据", "统计", "活跃度", "发言情况", "怎么样", "情况",
                "分析", "报告", "概况", "总结", "汇总", "看看",
                "群数据", "群统计", "群分析", "数据分析",
                
                # 🔥 更自然的中文表达
                "看看数据", "群里怎么样", "活跃情况", "聊天情况",
                "发言统计", "消息统计", "互动数据", "群活跃度",
                "最近怎样", "数据报告", "统计报告", "分析报告",
                "群组分析", "聊天分析", "交流情况", "活动情况",
                
                # 活跃度相关
                "活跃", "聊天", "发言", "消息", "互动", "交流",
                "谁最活跃", "活跃排行", "发言排行", "聊天排行",
                "最活跃的人", "谁话最多", "谁最爱聊天",
                
                # 时间相关
                "今日数据", "今天统计", "最近活跃", "本周数据", "本月统计",
                "今天情况", "最近情况", "这周数据", "本周活跃度",
                "今日活跃度", "最近的数据", "近期统计"
            ],
            
            CommandType.PORTRAIT: [  # Phase 3 新增
                # 基础画像相关
                "画像", "用户画像", "性格分析", "分析我", "我的画像",
                "用户分析", "性格", "特征", "特点", "人物分析",
                "个人分析", "个性分析", "角色分析", "人格分析",
                
                # 🔥 更自然的中文表达
                "分析一下我", "我是什么性格", "我的特点", "我的特征",
                "看看我的画像", "分析我的性格", "我的个性", "我的人格",
                "给我做个分析", "分析我这个人", "我是怎样的人",
                "我的聊天风格", "我的表达方式", "我的交流特点",
                
                # 对比相关
                "对比", "比较", "用户对比", "性格对比", "画像对比",
                "和谁比较", "对比分析", "比较分析", "相似度",
                "我们像吗", "我和他像吗", "性格相似", "特征对比",
                
                # 深度分析
                "深度分析", "详细分析", "性格测试", "用户特征",
                "深入分析", "全面分析", "完整分析", "详细画像",
                "深度画像", "完整画像", "全方位分析"
            ],
            
            CommandType.HELP: [
                # 帮助相关
                "帮助", "怎么用", "功能", "用法", "说明", "教程",
                "指令", "命令", "使用方法", "操作指南", "使用说明",
                
                # 🔥 更自然的中文表达
                "有什么功能", "能做什么", "怎么操作", "如何使用",
                "什么指令", "有哪些命令", "支持什么", "可以干什么",
                "使用帮助", "操作帮助", "功能介绍", "使用指南",
                "不会用", "不知道怎么用", "教教我", "怎么玩"
            ]
        }
        
        # 时间范围关键词
        self.time_keywords = {
            TimeRange.TODAY: ["今日", "今天", "当日"],
            TimeRange.WEEK: ["本周", "这周", "一周", "7天", "最近"],
            TimeRange.MONTH: ["本月", "这月", "一个月", "30天"],
            TimeRange.ALL: ["全部", "所有", "总体", "整体"]
        }
        
        # 样式关键词
        self.style_keywords = {
            "简约": ["简约", "简单", "清爽", "优雅"],
            "现代": ["现代", "科技", "时尚", "前卫"],
            "游戏": ["游戏", "竞技", "电竞", "娱乐"],
            "对比": ["对比", "变化", "趋势", "历史"]
        }
        
        logger.info("自然语言处理器已初始化")
    
    def parse_natural_command(self, message: str) -> CommandIntent:
        """
        解析自然语言命令，识别意图和参数
        
        Args:
            message: 用户输入的自然语言消息
            
        Returns:
            CommandIntent: 命令意图对象
        """
        message_lower = message.lower()
        
        # 尝试匹配词云命令
        if self._match_keywords(message_lower, self.command_keywords[CommandType.WORDCLOUD]):
            return self._parse_wordcloud_intent(message)
        
        # 尝试匹配统计命令
        if self._match_keywords(message_lower, self.command_keywords[CommandType.STATS]):
            return self._parse_stats_intent(message)
            
        # 尝试匹配用户画像命令 (Phase 3 新增)
        if self._match_keywords(message_lower, self.command_keywords[CommandType.PORTRAIT]):
            return self._parse_portrait_intent(message)
            
        # 尝试匹配帮助命令
        if self._match_keywords(message_lower, self.command_keywords[CommandType.HELP]):
            return CommandIntent(CommandType.HELP, message, 0.9)
            
        return CommandIntent(CommandType.UNKNOWN, message, 0.0)
    
    def _match_keywords(self, message: str, keywords: List[str]) -> bool:
        """检查消息是否包含关键词"""
        for keyword in keywords:
            if keyword in message:
                return True
        return False
    
    def _parse_wordcloud_intent(self, message: str) -> CommandIntent:
        """解析词云相关意图"""
        confidence = 0.7  # 基础置信度
        time_range = None
        
        # 检测时间范围
        for time_type, keywords in self.time_keywords.items():
            if any(keyword in message for keyword in keywords):
                time_range = time_type
                confidence += 0.1
                break
        
        # 检测特殊样式或功能
        if any(style in message for style in ["简约", "优雅", "现代", "科技", "游戏"]):
            confidence += 0.1
            
        if any(comp in message for comp in ["对比", "变化", "趋势"]):
            confidence += 0.2
            
        # 直接词汇匹配加分
        if "词云" in message:
            confidence += 0.1
            
        return CommandIntent(CommandType.WORDCLOUD, message, min(confidence, 1.0), time_range=time_range)
    
    def _parse_stats_intent(self, message: str) -> CommandIntent:
        """解析统计相关意图"""
        confidence = 0.6  # 基础置信度
        time_range = None
        
        # 检测时间范围
        for time_type, keywords in self.time_keywords.items():
            if any(keyword in message for keyword in keywords):
                time_range = time_type
                confidence += 0.1
                break
        
        # 检测特定统计类型
        stats_keywords = ["活跃度", "发言", "数据", "统计", "分析"]
        if any(keyword in message for keyword in stats_keywords):
            confidence += 0.2
            
        return CommandIntent(CommandType.STATS, message, min(confidence, 1.0), time_range=time_range)
    
    def _parse_portrait_intent(self, message: str) -> CommandIntent:
        """解析用户画像相关意图 (Phase 3 新增)"""
        confidence = 0.7  # 基础置信度
        target_user = None
        parameters = {}
        
        # 检测目标用户
        user_patterns = [
            r"@(\w+)",  # @用户名
            r"分析(\w+)",  # 分析某人
            r"(\w+)的画像",  # 某人的画像
        ]
        
        for pattern in user_patterns:
            match = re.search(pattern, message)
            if match:
                target_user = match.group(1)
                confidence += 0.1
                break
        
        # 检测分析深度
        if any(keyword in message for keyword in ["深度", "详细", "全面"]):
            parameters["analysis_depth"] = "deep"
            confidence += 0.1
        elif any(keyword in message for keyword in ["简单", "快速", "基础"]):
            parameters["analysis_depth"] = "light"
            
        # 检测对比请求
        if any(keyword in message for keyword in ["对比", "比较"]):
            parameters["comparison"] = True
            confidence += 0.1
            
        # 直接词汇匹配加分
        if "画像" in message:
            confidence += 0.1
            
        return CommandIntent(
            CommandType.PORTRAIT, 
            message, 
            min(confidence, 1.0),
            target_user=target_user,
            parameters=parameters
        )
    
    def extract_time_range(self, message: str) -> Optional[TimeRange]:
        """提取时间范围"""
        for time_type, keywords in self.time_keywords.items():
            if any(keyword in message for keyword in keywords):
                return time_type
        return None
    
    def extract_user_mentions(self, message: str) -> List[str]:
        """提取用户提及"""
        patterns = [
            r"@(\w+)",  # @用户名
            r"分析(\w+)",  # 分析某人
            r"(\w+)的",  # 某人的
        ]
        
        users = []
        for pattern in patterns:
            matches = re.findall(pattern, message)
            users.extend(matches)
            
        return list(set(users))  # 去重
    
    def get_command_confidence(self, message: str, command_type: CommandType) -> float:
        """获取特定命令类型的置信度"""
        if command_type not in self.command_keywords:
            return 0.0
            
        keywords = self.command_keywords[command_type]
        matched_keywords = sum(1 for keyword in keywords if keyword in message.lower())
        
        if matched_keywords == 0:
            return 0.0
            
        # 基于匹配关键词数量计算置信度
        base_confidence = min(matched_keywords / 3, 1.0)  # 3个关键词为满分
        
        # 长度惩罚：过长的消息置信度降低
        length_penalty = 1.0 if len(message) < 50 else 0.8
        
        return base_confidence * length_penalty
    
    def is_natural_command_candidate(self, message: str) -> bool:
        """
        判断消息是否可能是自然语言命令
        
        Args:
            message: 用户消息
            
        Returns:
            bool: 是否可能是命令
        """
        # 过滤条件
        if len(message) < 2 or len(message) > 100:
            return False
            
        # 排除明显不是命令的消息
        exclude_patterns = [
            r"^[a-zA-Z0-9\s]+$",  # 纯英文数字
            r"^[!@#$%^&*()]+$",    # 纯符号
            r"^https?://",         # 链接
            r"^\d+$",              # 纯数字
        ]
        
        for pattern in exclude_patterns:
            if re.match(pattern, message):
                return False
                
        # 检查是否包含任何命令关键词
        message_lower = message.lower()
        for keywords in self.command_keywords.values():
            if any(keyword in message_lower for keyword in keywords):
                return True
                
        return False
    
    def get_supported_commands(self) -> Dict[str, List[str]]:
        """获取支持的命令列表"""
        return {
            "🎨 词云生成": [
                "今日词云", "大家都在聊什么", "最近聊什么", "热门话题",
                "看看话题", "词云图", "热词统计", "话题分析",
                "简约词云", "现代词云", "好看的词云", "词云对比",
                "今天聊什么", "最近热词", "群里聊什么"
            ],
            "📊 数据统计": [
                "看看数据", "群里怎么样", "活跃情况", "聊天情况",
                "发言统计", "活跃度", "统计信息", "数据报告",
                "今日数据", "本周数据", "最近怎样", "群活跃度",
                "谁最活跃", "活跃排行", "发言排行"
            ],
            "👤 用户画像": [
                "我的画像", "分析一下我", "我是什么性格", "我的特点",
                "给我做个分析", "用户分析", "性格分析", "深度分析",
                "我和他像吗", "用户对比", "画像对比", "性格对比",
                "我是怎样的人", "我的聊天风格", "深度画像"
            ],
            "❓ 帮助功能": [
                "帮助", "有什么功能", "能做什么", "怎么用",
                "什么指令", "有哪些命令", "支持什么", "功能介绍",
                "使用说明", "不会用", "教教我", "怎么玩"
            ]
        }
    
    def get_usage_examples(self) -> List[str]:
        """获取使用示例 - 更自然的中文表达"""
        return [
            "🎨 \"今日词云\" - 生成今天的热词统计",
            "🎨 \"大家都在聊什么\" - 看看群里最热门的话题",
            "🎨 \"好看的词云\" - 生成精美样式的词云图",
            "📊 \"看看数据\" - 查看群组活跃度和统计",
            "📊 \"群里怎么样\" - 了解最近的聊天情况",
            "📊 \"谁最活跃\" - 查看发言排行榜",
            "👤 \"我的画像\" - 生成个人性格分析报告",
            "👤 \"分析一下我\" - 深度分析你的聊天特征",
            "👤 \"我和他像吗\" - 对比两个用户的特征",
            "❓ \"有什么功能\" - 查看所有可用的功能",
            "❓ \"怎么用\" - 获取详细使用说明"
        ]