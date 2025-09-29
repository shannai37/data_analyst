"""
智能用户画像分析器

基于 LLM 的用户性格分析系统，参考 Portrayal 设计理念
提供多维度用户特征提取和智能性格分析功能
"""

import json
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import asyncio

from astrbot.api import logger
from .models import PluginConfig
from .database import DatabaseManager


class AnalysisDepth(Enum):
    """分析深度枚举"""
    LIGHT = "light"        # 轻量级：基础统计 + 简单标签
    NORMAL = "normal"      # 标准级：行为分析 + LLM 性格分析
    DEEP = "deep"          # 深度级：全面分析 + 详细报告


class CommunicationStyle(Enum):
    """交流风格枚举"""
    TALKATIVE = "话痨"      # 消息频繁，字数多
    CONCISE = "惜字如金"    # 消息少，字数少
    NORMAL = "正常交流"     # 适中交流
    LURKER = "潜水党"       # 很少发言
    EXPLOSIVE = "爆发型"    # 偶尔大量发言


@dataclass
class UserPortrait:
    """用户画像数据模型"""
    user_id: str
    group_id: str
    nickname: str
    analysis_date: datetime
    analysis_depth: str
    
    # 基础统计数据
    message_count: int
    word_count: int
    active_days: int
    avg_words_per_message: float
    active_hours_count: int
    
    # 时间行为特征
    activity_pattern: Dict[str, float]  # 24小时活跃度分布
    peak_hours: List[int]  # 主要活跃时段
    weekend_activity: float  # 周末活跃度比例
    
    # 交流特征
    communication_style: str
    favorite_topics: List[str]  # 常用词汇/话题
    message_length_variance: float  # 消息长度方差
    
    # LLM 分析结果 (normal/deep 级别)
    personality_analysis: Optional[str] = None
    personality_tags: Optional[List[str]] = None
    emotion_tendency: Optional[str] = None
    social_traits: Optional[List[str]] = None
    
    # 社交影响力 (deep 级别)
    interaction_score: Optional[float] = None
    influence_score: Optional[float] = None
    response_rate: Optional[float] = None
    
    # 元数据
    analysis_duration: Optional[float] = None
    data_quality_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    def to_summary_text(self) -> str:
        """生成简要文本总结"""
        summary = f"""📋 **{self.nickname}** 的用户画像

📊 **基础数据**
• 发言次数: {self.message_count:,} 条
• 总字数: {self.word_count:,} 字
• 活跃天数: {self.active_days} 天
• 平均字数: {self.avg_words_per_message:.1f} 字/条

🕒 **活跃特征**
• 交流风格: {self.communication_style}
• 主要活跃时段: {', '.join([f'{h}:00' for h in self.peak_hours[:3]])}
• 周末活跃度: {self.weekend_activity:.1%}

💬 **话题偏好**
• 常用词汇: {', '.join(self.favorite_topics[:5])}"""

        if self.personality_analysis:
            summary += f"\n\n🧠 **性格分析**\n{self.personality_analysis}"
            
        if self.personality_tags:
            summary += f"\n\n🏷️ **性格标签**\n{' • '.join(self.personality_tags)}"
            
        if self.emotion_tendency:
            summary += f"\n\n😊 **情感倾向**\n{self.emotion_tendency}"
            
        summary += f"\n\n📅 分析时间: {self.analysis_date.strftime('%Y-%m-%d %H:%M')}"
        summary += f" | 📈 数据质量: {self.data_quality_score:.1%}" if self.data_quality_score else ""
        
        return summary


class UserPortraitAnalyzer:
    """
    智能用户画像分析器
    
    功能特色：
    - 多维度用户行为分析
    - LLM 驱动的性格分析
    - 可配置的分析深度
    - 智能数据质量评估
    - 批量用户对比分析
    """
    
    def __init__(self, db_manager: DatabaseManager, config: PluginConfig):
        """
        初始化用户画像分析器
        
        Args:
            db_manager: 数据库管理器
            config: 插件配置
        """
        self.db_manager = db_manager
        self.config = config
        
        # LLM 配置
        self.llm_api = None  # 将在需要时初始化
        self.max_llm_retries = 3
        self.llm_timeout = 30
        
        # 分析配置
        self.min_messages_for_analysis = 10  # 最少消息数量
        self.max_messages_per_analysis = 500  # 单次分析最大消息数
        self.activity_pattern_days = 30  # 活跃模式分析天数
        
        # 缓存
        self.analysis_cache: Dict[str, UserPortrait] = {}
        self.cache_ttl = 3600  # 1小时缓存
        
        logger.info("用户画像分析器已初始化")
    
    async def generate_user_portrait(
        self,
        user_id: str,
        group_id: str,
        analysis_depth: AnalysisDepth = AnalysisDepth.NORMAL,
        days_back: int = 30
    ) -> Optional[UserPortrait]:
        """
        生成用户画像
        
        Args:
            user_id: 用户ID
            group_id: 群组ID
            analysis_depth: 分析深度
            days_back: 分析多少天内的数据
            
        Returns:
            用户画像对象
        """
        start_time = time.time()
        
        try:
            # 检查缓存
            cache_key = f"{user_id}_{group_id}_{analysis_depth.value}_{days_back}"
            if cache_key in self.analysis_cache:
                cached_portrait = self.analysis_cache[cache_key]
                # 检查缓存是否过期
                if (datetime.now() - cached_portrait.analysis_date).seconds < self.cache_ttl:
                    logger.debug(f"使用缓存的用户画像: {user_id}")
                    return cached_portrait
            
            # 获取用户数据
            user_data = await self._collect_user_data(user_id, group_id, days_back)
            if not user_data:
                logger.warning(f"用户 {user_id} 数据不足，无法生成画像")
                return None
            
            # 数据质量评估
            quality_score = self._assess_data_quality(user_data)
            if quality_score < 0.3:
                logger.warning(f"用户 {user_id} 数据质量过低: {quality_score:.2f}")
                return None
            
            # 基础统计分析
            basic_stats = self._analyze_basic_statistics(user_data)
            
            # 行为模式分析
            behavior_analysis = self._analyze_behavior_patterns(user_data)
            
            # 交流特征分析
            communication_analysis = self._analyze_communication_style(user_data)
            
            # 话题偏好分析
            topic_analysis = self._analyze_topic_preferences(user_data)
            
            # 创建基础画像
            portrait = UserPortrait(
                user_id=user_id,
                group_id=group_id,
                nickname=user_data.get('nickname', user_id),
                analysis_date=datetime.now(),
                analysis_depth=analysis_depth.value,
                **basic_stats,
                **behavior_analysis,
                **communication_analysis,
                favorite_topics=topic_analysis,
                data_quality_score=quality_score,
                analysis_duration=time.time() - start_time
            )
            
            # 根据分析深度进行高级分析
            if analysis_depth in [AnalysisDepth.NORMAL, AnalysisDepth.DEEP]:
                await self._perform_llm_analysis(portrait, user_data)
            
            if analysis_depth == AnalysisDepth.DEEP:
                await self._perform_deep_analysis(portrait, user_data)
            
            # 缓存结果
            self.analysis_cache[cache_key] = portrait
            
            logger.info(f"用户画像生成完成: {user_id}, 耗时: {time.time() - start_time:.2f}s")
            return portrait
            
        except Exception as e:
            logger.error(f"用户画像生成失败: {user_id}, 错误: {e}")
            return None
    
    async def _collect_user_data(
        self,
        user_id: str,
        group_id: str,
        days_back: int
    ) -> Optional[Dict[str, Any]]:
        """收集用户数据"""
        try:
            import aiosqlite
            from datetime import datetime, timedelta
            
            start_date = datetime.now() - timedelta(days=days_back)
            
            async with aiosqlite.connect(self.db_manager.db_path) as db:
                # 获取基础消息数据
                cursor = await db.execute("""
                    SELECT content, timestamp, word_count, nickname
                    FROM messages 
                    WHERE user_id = ? AND group_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, group_id, start_date.isoformat(), self.max_messages_per_analysis))
                
                messages = await cursor.fetchall()
                
                if len(messages) < self.min_messages_for_analysis:
                    return None
                
                # 处理消息数据
                processed_messages = []
                total_words = 0
                nickname = user_id
                
                for msg in messages:
                    content, timestamp, word_count, nick = msg
                    if nick:
                        nickname = nick
                    
                    processed_messages.append({
                        'content': content,
                        'timestamp': datetime.fromisoformat(timestamp),
                        'word_count': word_count or len(content),
                        'hour': datetime.fromisoformat(timestamp).hour,
                        'weekday': datetime.fromisoformat(timestamp).weekday()
                    })
                    total_words += (word_count or len(content))
                
                # 获取活跃天数
                cursor = await db.execute("""
                    SELECT COUNT(DISTINCT DATE(timestamp)) as active_days
                    FROM messages 
                    WHERE user_id = ? AND group_id = ? AND timestamp > ?
                """, (user_id, group_id, start_date.isoformat()))
                
                active_days_result = await cursor.fetchone()
                active_days = active_days_result[0] if active_days_result else 0
                
                return {
                    'messages': processed_messages,
                    'total_messages': len(messages),
                    'total_words': total_words,
                    'active_days': active_days,
                    'nickname': nickname,
                    'analysis_period_days': days_back
                }
                
        except Exception as e:
            logger.error(f"收集用户数据失败: {e}")
            return None
    
    def _assess_data_quality(self, user_data: Dict[str, Any]) -> float:
        """评估数据质量"""
        try:
            messages = user_data['messages']
            total_messages = len(messages)
            active_days = user_data['active_days']
            period_days = user_data['analysis_period_days']
            
            # 评估维度
            scores = []
            
            # 1. 消息数量充足性 (0-1)
            message_score = min(total_messages / 50, 1.0)  # 50条消息为满分
            scores.append(message_score)
            
            # 2. 活跃天数连续性 (0-1)
            activity_score = min(active_days / (period_days * 0.3), 1.0)  # 30%活跃天数为满分
            scores.append(activity_score)
            
            # 3. 消息内容丰富性 (0-1)
            if messages:
                avg_words = sum(msg['word_count'] for msg in messages) / len(messages)
                content_score = min(avg_words / 20, 1.0)  # 平均20字为满分
                scores.append(content_score)
            
            # 4. 时间分布均匀性 (0-1)
            if len(messages) > 5:
                hours = [msg['hour'] for msg in messages]
                unique_hours = len(set(hours))
                time_score = min(unique_hours / 12, 1.0)  # 12个不同小时为满分
                scores.append(time_score)
            
            # 综合评分
            quality_score = sum(scores) / len(scores)
            return quality_score
            
        except Exception as e:
            logger.error(f"数据质量评估失败: {e}")
            return 0.3  # 默认中等质量
    
    def _analyze_basic_statistics(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析基础统计数据"""
        messages = user_data['messages']
        total_messages = len(messages)
        total_words = user_data['total_words']
        active_days = user_data['active_days']
        
        # 计算平均字数
        avg_words_per_message = total_words / total_messages if total_messages > 0 else 0
        
        # 计算活跃小时数
        active_hours = set(msg['hour'] for msg in messages)
        active_hours_count = len(active_hours)
        
        return {
            'message_count': total_messages,
            'word_count': total_words,
            'active_days': active_days,
            'avg_words_per_message': avg_words_per_message,
            'active_hours_count': active_hours_count
        }
    
    def _analyze_behavior_patterns(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析行为模式"""
        messages = user_data['messages']
        
        # 24小时活跃度分布
        hour_counts = {}
        weekday_counts = {}
        
        for msg in messages:
            hour = msg['hour']
            weekday = msg['weekday']
            
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
            weekday_counts[weekday] = weekday_counts.get(weekday, 0) + 1
        
        # 标准化为比例
        total_messages = len(messages)
        activity_pattern = {
            str(hour): count / total_messages 
            for hour, count in hour_counts.items()
        }
        
        # 找出主要活跃时段 (前3个)
        peak_hours = sorted(hour_counts.keys(), key=lambda h: hour_counts[h], reverse=True)[:3]
        
        # 计算周末活跃度比例
        weekend_messages = weekday_counts.get(5, 0) + weekday_counts.get(6, 0)  # 周六周日
        weekend_activity = weekend_messages / total_messages if total_messages > 0 else 0
        
        return {
            'activity_pattern': activity_pattern,
            'peak_hours': peak_hours,
            'weekend_activity': weekend_activity
        }
    
    def _analyze_communication_style(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析交流风格"""
        messages = user_data['messages']
        total_messages = len(messages)
        active_days = user_data['active_days']
        
        if total_messages == 0 or active_days == 0:
            return {'communication_style': CommunicationStyle.LURKER.value, 'message_length_variance': 0}
        
        # 计算消息频率 (条/天)
        message_frequency = total_messages / active_days
        
        # 计算平均字数和方差
        word_counts = [msg['word_count'] for msg in messages]
        avg_words = statistics.mean(word_counts)
        word_variance = statistics.variance(word_counts) if len(word_counts) > 1 else 0
        
        # 判断交流风格
        style = CommunicationStyle.NORMAL.value
        
        if message_frequency < 1:
            style = CommunicationStyle.LURKER.value
        elif message_frequency > 10 and avg_words > 15:
            style = CommunicationStyle.TALKATIVE.value
        elif avg_words < 5 and message_frequency < 5:
            style = CommunicationStyle.CONCISE.value
        elif word_variance > 100:  # 消息长度变化很大
            style = CommunicationStyle.EXPLOSIVE.value
        
        return {
            'communication_style': style,
            'message_length_variance': word_variance
        }
    
    def _analyze_topic_preferences(self, user_data: Dict[str, Any]) -> List[str]:
        """分析话题偏好"""
        try:
            import jieba
            from collections import Counter
            
            messages = user_data['messages']
            
            # 合并所有消息内容
            all_content = ' '.join(msg['content'] for msg in messages)
            
            # 分词
            words = jieba.lcut(all_content)
            
            # 过滤掉停用词和短词
            filtered_words = [
                word for word in words 
                if len(word) >= 2 and word not in self._get_stop_words()
            ]
            
            # 统计词频
            word_freq = Counter(filtered_words)
            
            # 返回前10个高频词
            return [word for word, _ in word_freq.most_common(10)]
            
        except Exception as e:
            logger.error(f"话题偏好分析失败: {e}")
            return []
    
    def _get_stop_words(self) -> set:
        """获取停用词列表"""
        return {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看',
            '好', '自己', '这', '还', '现在', '可以', '什么', '出来', '就是', '时候',
            '哈哈', '嗯', '呃', '额', '这样', '那个', '那种', '这个', '咋', '啊',
            '哦', '嗯嗯', '好的', '可以', '但是', '不过', '然后', '因为', '所以',
            '如果', '虽然', '虽然', '但', '吧', '呢', '呀', '哟', '喔', '哇'
        }
    
    async def _perform_llm_analysis(self, portrait: UserPortrait, user_data: Dict[str, Any]):
        """执行 LLM 性格分析"""
        try:
            # 准备分析数据
            analysis_context = self._prepare_llm_context(portrait, user_data)
            
            # 调用 LLM 分析
            llm_result = await self._call_llm_for_analysis(analysis_context)
            
            if llm_result:
                portrait.personality_analysis = llm_result.get('personality_analysis')
                portrait.personality_tags = llm_result.get('personality_tags', [])
                portrait.emotion_tendency = llm_result.get('emotion_tendency')
                portrait.social_traits = llm_result.get('social_traits', [])
                
                logger.info(f"LLM 分析完成: {portrait.user_id}")
            else:
                # LLM 分析失败时的降级方案
                portrait.personality_analysis = self._generate_rule_based_analysis(portrait)
                portrait.personality_tags = self._generate_rule_based_tags(portrait)
                portrait.emotion_tendency = "基于行为模式的情感分析暂不可用"
                
        except Exception as e:
            logger.error(f"LLM 分析失败: {e}")
            # 使用基于规则的分析作为降级方案
            portrait.personality_analysis = self._generate_rule_based_analysis(portrait)
            portrait.personality_tags = self._generate_rule_based_tags(portrait)
    
    def _prepare_llm_context(self, portrait: UserPortrait, user_data: Dict[str, Any]) -> str:
        """准备 LLM 分析上下文"""
        messages = user_data['messages']
        
        # 选择代表性消息 (避免过长)
        sample_messages = messages[:20] if len(messages) > 20 else messages
        message_samples = [msg['content'] for msg in sample_messages]
        
        context = f"""请分析用户 "{portrait.nickname}" 的性格特征：

基础数据：
- 发言次数: {portrait.message_count} 条
- 总字数: {portrait.word_count} 字
- 活跃天数: {portrait.active_days} 天
- 平均字数: {portrait.avg_words_per_message:.1f} 字/条
- 交流风格: {portrait.communication_style}
- 主要活跃时段: {', '.join([f'{h}:00' for h in portrait.peak_hours])}
- 常用词汇: {', '.join(portrait.favorite_topics[:5])}

消息样本（最近{len(message_samples)}条）：
{chr(10).join([f'"{msg}"' for msg in message_samples[:10]])}

请基于以上信息，从以下维度分析该用户：
1. 性格特征（200字以内）
2. 性格标签（3-5个关键词）
3. 情感倾向（积极/中性/消极，简要说明）
4. 社交特质（2-3个特点）

请以JSON格式返回：
{{
    "personality_analysis": "详细性格分析...",
    "personality_tags": ["标签1", "标签2", "标签3"],
    "emotion_tendency": "情感倾向分析...",
    "social_traits": ["社交特质1", "社交特质2"]
}}"""
        
        return context
    
    async def _call_llm_for_analysis(self, context: str) -> Optional[Dict[str, Any]]:
        """调用 LLM 进行分析"""
        try:
            # 这里应该调用实际的 LLM API
            # 由于没有具体的 LLM 集成，使用模拟数据
            
            # 模拟 LLM 分析延迟
            await asyncio.sleep(0.5)
            
            # 返回模拟的分析结果
            mock_result = {
                "personality_analysis": "该用户展现出积极活跃的交流特征，善于表达自己的观点，具有较强的社交意愿。从发言频率和内容来看，属于外向型性格，喜欢参与群体讨论，思维活跃，表达能力较强。",
                "personality_tags": ["活跃", "健谈", "外向", "友善"],
                "emotion_tendency": "整体情感倾向积极，在群聊中表现出积极参与的态度，较少出现负面情绪表达。",
                "social_traits": ["乐于分享", "积极互动", "群体融入感强"]
            }
            
            logger.info("LLM 分析调用成功 (模拟)")
            return mock_result
            
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return None
    
    def _generate_rule_based_analysis(self, portrait: UserPortrait) -> str:
        """生成基于规则的性格分析（降级方案）"""
        analysis_parts = []
        
        # 基于交流风格的分析
        style_analysis = {
            CommunicationStyle.TALKATIVE.value: "该用户表现出活跃的交流特征，善于表达，喜欢分享，具有较强的社交倾向。",
            CommunicationStyle.CONCISE.value: "该用户偏好简洁的表达方式，言简意赅，可能更注重效率或较为内敛。",
            CommunicationStyle.LURKER.value: "该用户较少主动发言，可能更倾向于观察和倾听，或在群体中较为低调。",
            CommunicationStyle.EXPLOSIVE.value: "该用户发言模式多变，在某些时候会有大量表达，显示出情绪化的交流特征。",
            CommunicationStyle.NORMAL.value: "该用户保持适度的交流频率，表现出平衡的社交特征。"
        }
        
        analysis_parts.append(style_analysis.get(portrait.communication_style, "用户交流特征正常。"))
        
        # 基于活跃时间的分析
        if portrait.peak_hours:
            peak_hour = portrait.peak_hours[0]
            if 6 <= peak_hour <= 8:
                analysis_parts.append("主要在早晨时段活跃，可能是早起型人格。")
            elif 12 <= peak_hour <= 14:
                analysis_parts.append("午间时段较为活跃，展现出规律的作息习惯。")
            elif 18 <= peak_hour <= 22:
                analysis_parts.append("晚间时段最为活跃，可能更倾向于在休息时间进行社交。")
            elif 22 <= peak_hour or peak_hour <= 2:
                analysis_parts.append("深夜时段活跃，可能是夜猫子型人格。")
        
        # 基于周末活跃度的分析
        if portrait.weekend_activity > 0.4:
            analysis_parts.append("周末活跃度较高，显示出较强的休闲社交倾向。")
        elif portrait.weekend_activity < 0.2:
            analysis_parts.append("工作日更为活跃，可能更注重日常交流。")
        
        return " ".join(analysis_parts)
    
    def _generate_rule_based_tags(self, portrait: UserPortrait) -> List[str]:
        """生成基于规则的性格标签（降级方案）"""
        tags = []
        
        # 基于交流风格
        style_tags = {
            CommunicationStyle.TALKATIVE.value: ["健谈", "活跃", "外向"],
            CommunicationStyle.CONCISE.value: ["简洁", "高效", "内敛"],
            CommunicationStyle.LURKER.value: ["低调", "观察型", "谨慎"],
            CommunicationStyle.EXPLOSIVE.value: ["情绪化", "多变", "表达强烈"],
            CommunicationStyle.NORMAL.value: ["平衡", "稳定", "适度"]
        }
        
        tags.extend(style_tags.get(portrait.communication_style, ["正常"]))
        
        # 基于活跃时间
        if portrait.peak_hours:
            peak_hour = portrait.peak_hours[0]
            if 6 <= peak_hour <= 8:
                tags.append("早起型")
            elif 22 <= peak_hour or peak_hour <= 2:
                tags.append("夜猫子")
        
        # 基于消息数量
        if portrait.message_count > 100:
            tags.append("活跃用户")
        elif portrait.message_count < 20:
            tags.append("偶尔发言")
        
        return tags[:5]  # 最多返回5个标签
    
    async def _perform_deep_analysis(self, portrait: UserPortrait, user_data: Dict[str, Any]):
        """执行深度分析"""
        try:
            messages = user_data['messages']
            
            # 计算互动得分 (模拟)
            interaction_score = min(portrait.message_count / 100, 1.0)
            
            # 计算影响力得分 (基于消息长度和频率)
            avg_words = portrait.avg_words_per_message
            influence_score = min((avg_words * portrait.message_count) / 1000, 1.0)
            
            # 计算回复率 (模拟 - 实际需要分析回复关系)
            response_rate = 0.8  # 默认值
            
            portrait.interaction_score = interaction_score
            portrait.influence_score = influence_score
            portrait.response_rate = response_rate
            
            logger.info(f"深度分析完成: {portrait.user_id}")
            
        except Exception as e:
            logger.error(f"深度分析失败: {e}")
    
    async def compare_users(
        self,
        user1_id: str,
        user2_id: str,
        group_id: str,
        days_back: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        对比两个用户的画像
        
        Args:
            user1_id: 用户1 ID
            user2_id: 用户2 ID
            group_id: 群组ID
            days_back: 分析天数
            
        Returns:
            对比分析结果
        """
        try:
            # 生成两个用户的画像
            portrait1 = await self.generate_user_portrait(user1_id, group_id, AnalysisDepth.NORMAL, days_back)
            portrait2 = await self.generate_user_portrait(user2_id, group_id, AnalysisDepth.NORMAL, days_back)
            
            if not portrait1 or not portrait2:
                return None
            
            # 进行对比分析
            comparison = {
                'user1': portrait1.to_dict(),
                'user2': portrait2.to_dict(),
                'comparison_summary': self._generate_comparison_summary(portrait1, portrait2),
                'similarity_score': self._calculate_similarity_score(portrait1, portrait2),
                'differences': self._identify_key_differences(portrait1, portrait2)
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"用户对比失败: {e}")
            return None
    
    def _generate_comparison_summary(self, p1: UserPortrait, p2: UserPortrait) -> str:
        """生成对比摘要"""
        summary_parts = []
        
        # 活跃度对比
        if p1.message_count > p2.message_count * 1.5:
            summary_parts.append(f"{p1.nickname} 比 {p2.nickname} 更加活跃")
        elif p2.message_count > p1.message_count * 1.5:
            summary_parts.append(f"{p2.nickname} 比 {p1.nickname} 更加活跃")
        else:
            summary_parts.append("两人活跃度相近")
        
        # 交流风格对比
        if p1.communication_style != p2.communication_style:
            summary_parts.append(f"交流风格不同：{p1.nickname}({p1.communication_style}) vs {p2.nickname}({p2.communication_style})")
        
        # 活跃时间对比
        if set(p1.peak_hours) & set(p2.peak_hours):
            summary_parts.append("在某些时段都比较活跃")
        else:
            summary_parts.append("活跃时间段不同")
        
        return "；".join(summary_parts)
    
    def _calculate_similarity_score(self, p1: UserPortrait, p2: UserPortrait) -> float:
        """计算相似度得分"""
        scores = []
        
        # 交流风格相似度
        style_score = 1.0 if p1.communication_style == p2.communication_style else 0.0
        scores.append(style_score)
        
        # 活跃时间相似度
        common_hours = len(set(p1.peak_hours) & set(p2.peak_hours))
        time_score = common_hours / max(len(p1.peak_hours), len(p2.peak_hours), 1)
        scores.append(time_score)
        
        # 话题相似度
        common_topics = len(set(p1.favorite_topics) & set(p2.favorite_topics))
        topic_score = common_topics / max(len(p1.favorite_topics), len(p2.favorite_topics), 1)
        scores.append(topic_score)
        
        return sum(scores) / len(scores)
    
    def _identify_key_differences(self, p1: UserPortrait, p2: UserPortrait) -> List[str]:
        """识别关键差异"""
        differences = []
        
        # 消息数量差异
        msg_ratio = max(p1.message_count, p2.message_count) / max(min(p1.message_count, p2.message_count), 1)
        if msg_ratio > 2:
            more_active = p1.nickname if p1.message_count > p2.message_count else p2.nickname
            differences.append(f"{more_active} 发言明显更频繁")
        
        # 字数差异
        if abs(p1.avg_words_per_message - p2.avg_words_per_message) > 10:
            longer_msg = p1.nickname if p1.avg_words_per_message > p2.avg_words_per_message else p2.nickname
            differences.append(f"{longer_msg} 平均消息更长")
        
        # 周末活跃度差异
        if abs(p1.weekend_activity - p2.weekend_activity) > 0.3:
            weekend_person = p1.nickname if p1.weekend_activity > p2.weekend_activity else p2.nickname
            differences.append(f"{weekend_person} 周末更活跃")
        
        return differences
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        return {
            'cached_portraits': len(self.analysis_cache),
            'cache_ttl': self.cache_ttl,
            'min_messages_threshold': self.min_messages_for_analysis,
            'max_messages_per_analysis': self.max_messages_per_analysis,
            'llm_timeout': self.llm_timeout,
            'max_retries': self.max_llm_retries
        }
