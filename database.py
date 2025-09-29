"""
数据分析师插件 - 数据库管理模块

提供异步数据库操作、数据存储和查询功能
"""

import aiosqlite
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
import jieba

from .models import (
    MessageData, UserStats, GroupStats, TopicKeyword,
    ActivityAnalysisData, UserAnalysisData, TopicsAnalysisData,
    DatabaseConstants as DB, TimePeriod
)
from .privacy import PrivacyFilter


class DatabaseManager:
    """
    /// 数据库管理器
    /// 负责所有数据库操作，包括数据存储、查询、统计和维护
    /// 使用异步SQLite确保高性能和并发安全
    """
    
    def __init__(self, db_path: str):
        """
        /// 初始化数据库管理器
        /// @param db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.is_initialized = False
        
        # 创建数据库目录
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"数据库管理器初始化: {db_path}")
    
    async def initialize(self):
        """
        /// 初始化数据库表结构和索引
        /// 创建所有必要的表和优化索引
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 启用WAL模式提高并发性能
                await db.execute('PRAGMA journal_mode=WAL')
                await db.execute('PRAGMA synchronous=NORMAL')
                await db.execute('PRAGMA cache_size=10000')
                
                # 创建消息记录表
                await self._create_messages_table(db)
                
                # 创建用户统计表
                await self._create_user_stats_table(db)
                
                # 创建群组统计表
                await self._create_group_stats_table(db)
                
                # 创建话题关键词表
                await self._create_topic_keywords_table(db)
                
                # 创建分析缓存表
                await self._create_analysis_cache_table(db)
                
                # 创建索引
                await self._create_indexes(db)
                
                await db.commit()
                
                # Phase 2 新增：词云历史表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS wordcloud_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id TEXT NOT NULL,
                        time_range TEXT NOT NULL,
                        word_data TEXT NOT NULL,  -- JSON格式存储词频数据
                        style_name TEXT NOT NULL,
                        total_words INTEGER DEFAULT 0,
                        file_path TEXT,
                        metadata TEXT,  -- JSON格式存储元数据
                        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 创建词云历史索引
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_wordcloud_group_time 
                    ON wordcloud_history(group_id, time_range, generated_at DESC)
                """)
                
                # Phase 3 新增：用户画像表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_portraits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        group_id TEXT NOT NULL,
                        nickname TEXT,
                        portrait_data TEXT NOT NULL,  -- JSON格式存储画像数据
                        analysis_depth TEXT NOT NULL,
                        data_quality_score REAL,
                        analysis_duration REAL,
                        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, group_id, analysis_depth)
                    )
                """)
                
                # 创建用户画像索引
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_portraits_user_group 
                    ON user_portraits(user_id, group_id, generated_at DESC)
                """)
                
                # 画像分析历史表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS portrait_analysis_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        group_id TEXT NOT NULL,
                        analysis_type TEXT NOT NULL,  -- 'portrait', 'comparison'
                        analysis_depth TEXT NOT NULL,
                        result_summary TEXT,
                        file_paths TEXT,  -- JSON格式存储相关文件路径
                        metadata TEXT,    -- JSON格式存储元数据
                        analysis_time REAL,
                        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 创建历史索引
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_portrait_history_user 
                    ON portrait_analysis_history(user_id, group_id, generated_at DESC)
                """)
                
                await db.commit()
                
            self.is_initialized = True
            logger.info("数据库初始化完成 (包含词云历史和用户画像功能)")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def _create_messages_table(self, db: aiosqlite.Connection):
        """创建消息记录表"""
        await db.execute(f'''
            CREATE TABLE IF NOT EXISTS {DB.TABLE_MESSAGES} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                user_id TEXT NOT NULL,
                group_id TEXT,
                platform TEXT NOT NULL,
                content_hash TEXT,
                message_type TEXT DEFAULT '{DB.MESSAGE_TYPE_TEXT}',
                timestamp DATETIME NOT NULL,
                word_count INTEGER DEFAULT {DB.DEFAULT_WORD_COUNT},
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    async def _create_user_stats_table(self, db: aiosqlite.Connection):
        """创建用户统计表"""
        await db.execute(f'''
            CREATE TABLE IF NOT EXISTS {DB.TABLE_USER_STATS} (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                total_messages INTEGER DEFAULT 0,
                total_words INTEGER DEFAULT 0,
                first_seen DATETIME,
                last_seen DATETIME,
                active_days INTEGER DEFAULT 0,
                avg_words_per_msg REAL DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    async def _create_group_stats_table(self, db: aiosqlite.Connection):
        """创建群组统计表"""
        await db.execute(f'''
            CREATE TABLE IF NOT EXISTS {DB.TABLE_GROUP_STATS} (
                group_id TEXT PRIMARY KEY,
                group_name TEXT,
                total_messages INTEGER DEFAULT 0,
                total_members INTEGER DEFAULT 0,
                peak_hour INTEGER DEFAULT 0,
                most_active_day TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    async def _create_topic_keywords_table(self, db: aiosqlite.Connection):
        """创建话题关键词表"""
        await db.execute(f'''
            CREATE TABLE IF NOT EXISTS {DB.TABLE_TOPIC_KEYWORDS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                group_id TEXT,
                frequency INTEGER DEFAULT {DB.DEFAULT_FREQUENCY},
                last_mentioned DATETIME,
                sentiment_score REAL DEFAULT {DB.DEFAULT_SENTIMENT},
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    async def _create_analysis_cache_table(self, db: aiosqlite.Connection):
        """创建分析缓存表"""
        await db.execute(f'''
            CREATE TABLE IF NOT EXISTS {DB.TABLE_ANALYSIS_CACHE} (
                cache_key TEXT PRIMARY KEY,
                analysis_type TEXT NOT NULL,
                result_data TEXT,
                expires_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    async def _create_indexes(self, db: aiosqlite.Connection):
        """创建优化索引"""
        indexes = [
            f'CREATE INDEX IF NOT EXISTS {DB.IDX_MESSAGES_TIMESTAMP} ON {DB.TABLE_MESSAGES}(timestamp)',
            f'CREATE INDEX IF NOT EXISTS {DB.IDX_MESSAGES_GROUP_ID} ON {DB.TABLE_MESSAGES}(group_id)',
            f'CREATE INDEX IF NOT EXISTS {DB.IDX_MESSAGES_USER_ID} ON {DB.TABLE_MESSAGES}(user_id)',
            f'CREATE INDEX IF NOT EXISTS {DB.IDX_TOPIC_KEYWORDS_GROUP_ID} ON {DB.TABLE_TOPIC_KEYWORDS}(group_id)',
            f'CREATE INDEX IF NOT EXISTS idx_user_stats_updated ON {DB.TABLE_USER_STATS}(updated_at)',
            f'CREATE INDEX IF NOT EXISTS idx_topic_keywords_frequency ON {DB.TABLE_TOPIC_KEYWORDS}(frequency DESC)',
            f'CREATE INDEX IF NOT EXISTS idx_analysis_cache_expires ON {DB.TABLE_ANALYSIS_CACHE}(expires_at)'
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)
    
    async def collect_message(self, event: AstrMessageEvent, privacy_filter: PrivacyFilter):
        """
        /// 收集消息数据
        /// @param event: AstrBot消息事件
        /// @param privacy_filter: 隐私过滤器
        """
        try:
            # 提取消息基础信息
            message_data = self._extract_message_data(event, privacy_filter)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 插入消息记录
                await self._insert_message(db, message_data)
                
                # 更新用户统计
                await self._update_user_stats(db, message_data)
                
                # 更新群组统计
                if message_data.group_id:
                    await self._update_group_stats(db, message_data)
                
                # 提取和存储关键词
                if message_data.message_type == DB.MESSAGE_TYPE_TEXT and message_data.word_count > 2:
                    await self._extract_and_store_keywords(db, event.message_str, message_data)
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"消息收集失败: {e}")
    
    def _extract_message_data(self, event: AstrMessageEvent, privacy_filter: PrivacyFilter) -> MessageData:
        """提取消息数据"""
        # 生成消息ID
        message_id = getattr(event.message_obj, 'message_id', 
                           f"{event.get_sender_id()}_{int(time.time())}")
        
        # 获取基础信息
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        platform = event.get_platform_name()
        content = event.message_str or ""
        
        # 过滤内容
        filtered_content = privacy_filter.filter_content(content)
        word_count = len(content) if content else 0
        
        # 确定消息类型
        message_type = self._determine_message_type(event)
        
        return MessageData(
            message_id=message_id,
            user_id=user_id,
            group_id=group_id,
            platform=platform,
            content_hash=filtered_content,
            message_type=message_type,
            timestamp=datetime.now(),
            word_count=word_count
        )
    
    def _determine_message_type(self, event: AstrMessageEvent) -> str:
        """确定消息类型"""
        if hasattr(event.message_obj, 'message') and event.message_obj.message:
            for msg_seg in event.message_obj.message:
                if hasattr(msg_seg, 'type'):
                    if msg_seg.type in ['image', 'voice', 'video', 'file']:
                        return msg_seg.type
        return DB.MESSAGE_TYPE_TEXT
    
    async def _insert_message(self, db: aiosqlite.Connection, message_data: MessageData):
        """插入消息记录"""
        await db.execute(f'''
            INSERT OR REPLACE INTO {DB.TABLE_MESSAGES} 
            (message_id, user_id, group_id, platform, content_hash, message_type, timestamp, word_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_data.message_id,
            message_data.user_id,
            message_data.group_id,
            message_data.platform,
            message_data.content_hash,
            message_data.message_type,
            message_data.timestamp,
            message_data.word_count
        ))
    
    async def _update_user_stats(self, db: aiosqlite.Connection, message_data: MessageData):
        """更新用户统计"""
        await db.execute(f'''
            INSERT OR REPLACE INTO {DB.TABLE_USER_STATS} 
            (user_id, username, total_messages, total_words, first_seen, last_seen, updated_at)
            VALUES (
                ?, '', 
                COALESCE((SELECT total_messages FROM {DB.TABLE_USER_STATS} WHERE user_id = ?), 0) + 1,
                COALESCE((SELECT total_words FROM {DB.TABLE_USER_STATS} WHERE user_id = ?), 0) + ?,
                COALESCE((SELECT first_seen FROM {DB.TABLE_USER_STATS} WHERE user_id = ?), ?),
                ?,
                ?
            )
        ''', (
            message_data.user_id, message_data.user_id, message_data.user_id,
            message_data.word_count, message_data.user_id, message_data.timestamp,
            message_data.timestamp, message_data.timestamp
        ))
    
    async def _update_group_stats(self, db: aiosqlite.Connection, message_data: MessageData):
        """更新群组统计"""
        await db.execute(f'''
            INSERT OR REPLACE INTO {DB.TABLE_GROUP_STATS} 
            (group_id, total_messages, updated_at)
            VALUES (
                ?, 
                COALESCE((SELECT total_messages FROM {DB.TABLE_GROUP_STATS} WHERE group_id = ?), 0) + 1,
                ?
            )
        ''', (message_data.group_id, message_data.group_id, message_data.timestamp))
    
    async def _extract_and_store_keywords(self, db: aiosqlite.Connection, content: str, message_data: MessageData):
        """提取并存储关键词"""
        try:
            # 使用jieba分词
            words = jieba.cut(content)
            keywords = [word.strip() for word in words 
                       if len(word.strip()) > 1 and word.strip().isalpha()]
            
            # 存储关键词（限制数量避免垃圾数据）
            for keyword in keywords[:10]:
                await db.execute(f'''
                    INSERT OR REPLACE INTO {DB.TABLE_TOPIC_KEYWORDS} 
                    (keyword, group_id, frequency, last_mentioned)
                    VALUES (
                        ?, ?,
                        COALESCE((SELECT frequency FROM {DB.TABLE_TOPIC_KEYWORDS} WHERE keyword = ? AND group_id = ?), 0) + 1,
                        ?
                    )
                ''', (keyword, message_data.group_id, keyword, message_data.group_id, message_data.timestamp))
                
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
    
    async def get_group_quick_stats(self, group_id: str) -> Dict:
        """
        /// 获取群组快速统计
        /// @param group_id: 群组ID
        /// @return: 统计数据字典
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 基础统计
                cursor = await db.execute(f'''
                    SELECT 
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT user_id) as active_users,
                        AVG(word_count) as avg_length,
                        MIN(timestamp) as first_message,
                        MAX(timestamp) as last_message
                    FROM {DB.TABLE_MESSAGES} 
                    WHERE group_id = ?
                ''', (group_id,))
                
                row = await cursor.fetchone()
                if not row or row[0] == 0:
                    return {}
                
                # 计算数据收集天数
                first_date = datetime.fromisoformat(row[3]) if row[3] else datetime.now()
                data_days = (datetime.now() - first_date).days + 1
                
                # 获取最活跃时段
                cursor = await db.execute(f'''
                    SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                    FROM {DB.TABLE_MESSAGES} 
                    WHERE group_id = ?
                    GROUP BY hour
                    ORDER BY count DESC
                    LIMIT 1
                ''', (group_id,))
                
                peak_hour_row = await cursor.fetchone()
                peak_hour = peak_hour_row[0] if peak_hour_row else 'N/A'
                
                return {
                    'total_messages': row[0],
                    'active_users': row[1],
                    'avg_message_length': row[2] or 0,
                    'data_days': data_days,
                    'peak_hour': peak_hour
                }
                
        except Exception as e:
            logger.error(f"快速统计查询失败: {e}")
            return {}
    
    async def get_activity_analysis(self, group_id: str, period: str) -> Optional[ActivityAnalysisData]:
        """
        /// 获取活跃度分析数据
        /// @param group_id: 群组ID
        /// @param period: 时间周期
        /// @return: 活跃度分析数据
        """
        try:
            start_date = self._calculate_start_date(period)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取每日数据
                cursor = await db.execute(f'''
                    SELECT DATE(timestamp) as date, COUNT(*) as daily_count
                    FROM {DB.TABLE_MESSAGES} 
                    WHERE group_id = ? AND timestamp >= ?
                    GROUP BY date
                    ORDER BY date
                ''', (group_id, start_date))
                
                daily_data = await cursor.fetchall()
                if not daily_data:
                    return None
                
                # 基础统计
                total_messages = sum(row[1] for row in daily_data)
                
                cursor = await db.execute(f'''
                    SELECT COUNT(DISTINCT user_id) as active_users
                    FROM {DB.TABLE_MESSAGES} 
                    WHERE group_id = ? AND timestamp >= ?
                ''', (group_id, start_date))
                
                active_users = (await cursor.fetchone())[0]
                
                # 最活跃时段
                cursor = await db.execute(f'''
                    SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                    FROM {DB.TABLE_MESSAGES} 
                    WHERE group_id = ? AND timestamp >= ?
                    GROUP BY hour
                    ORDER BY count DESC
                    LIMIT 1
                ''', (group_id, start_date))
                
                peak_hour_row = await cursor.fetchone()
                peak_hour = peak_hour_row[0] if peak_hour_row else 'N/A'
                
                # 计算趋势
                avg_daily_messages = total_messages / max(1, len(daily_data))
                growth_rate = self._calculate_growth_rate(daily_data)
                trend_description = self._generate_trend_description(growth_rate)
                
                return ActivityAnalysisData(
                    total_messages=total_messages,
                    active_users=active_users,
                    avg_daily_messages=avg_daily_messages,
                    growth_rate=growth_rate,
                    peak_hour=peak_hour,
                    peak_day=daily_data[-1][0] if daily_data else 'N/A',
                    trend_description=trend_description,
                    daily_data=daily_data,
                    timespan_days=len(daily_data)
                )
                
        except Exception as e:
            logger.error(f"活跃度分析失败: {e}")
            return None
    
    async def get_user_analysis(self, user_id: str, period: str) -> Optional[UserAnalysisData]:
        """
        /// 获取用户行为分析
        /// @param user_id: 用户ID
        /// @param period: 时间周期
        /// @return: 用户分析数据
        """
        try:
            start_date = self._calculate_start_date(period)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 用户基础数据
                cursor = await db.execute(f'''
                    SELECT 
                        COUNT(*) as message_count,
                        AVG(word_count) as avg_length,
                        COUNT(DISTINCT DATE(timestamp)) as active_days
                    FROM {DB.TABLE_MESSAGES} 
                    WHERE user_id = ? AND timestamp >= ?
                ''', (user_id, start_date))
                
                row = await cursor.fetchone()
                if not row or row[0] == 0:
                    return None
                
                message_count, avg_length, active_days = row
                
                # 最活跃时段
                cursor = await db.execute(f'''
                    SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                    FROM {DB.TABLE_MESSAGES} 
                    WHERE user_id = ? AND timestamp >= ?
                    GROUP BY hour
                    ORDER BY count DESC
                    LIMIT 1
                ''', (user_id, start_date))
                
                hour_row = await cursor.fetchone()
                most_active_hour = hour_row[0] if hour_row else 'N/A'
                
                # 计算参与度
                participation_rate = await self._calculate_participation_rate(db, user_id, start_date, message_count, active_days)
                
                # 生成行为描述
                behavior_description = self._generate_behavior_description(
                    message_count, avg_length, active_days, participation_rate
                )
                
                return UserAnalysisData(
                    message_count=message_count,
                    avg_length=avg_length or 0,
                    active_days=active_days,
                    participation_rate=min(100, participation_rate),
                    most_active_hour=most_active_hour,
                    avg_interval='正常' if message_count > 10 else '较少',
                    behavior_description=behavior_description
                )
                
        except Exception as e:
            logger.error(f"用户分析失败: {e}")
            return None
    
    async def get_topics_analysis(self, group_id: str, period: str) -> Optional[TopicsAnalysisData]:
        """
        /// 获取话题分析数据
        /// @param group_id: 群组ID
        /// @param period: 时间周期
        /// @return: 话题分析数据
        """
        try:
            start_date = self._calculate_start_date(period)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取热门话题
                cursor = await db.execute(f'''
                    SELECT keyword, frequency, last_mentioned
                    FROM {DB.TABLE_TOPIC_KEYWORDS} 
                    WHERE group_id = ? AND last_mentioned >= ?
                    ORDER BY frequency DESC
                    LIMIT 20
                ''', (group_id, start_date))
                
                topics = await cursor.fetchall()
                if not topics:
                    return None
                
                top_topics = [
                    {
                        'keyword': row[0],
                        'frequency': row[1],
                        'last_mentioned': row[2]
                    }
                    for row in topics
                ]
                
                # 新话题数量
                cursor = await db.execute(f'''
                    SELECT COUNT(DISTINCT keyword)
                    FROM {DB.TABLE_TOPIC_KEYWORDS} 
                    WHERE group_id = ? AND created_at >= ?
                ''', (group_id, start_date))
                
                new_topics_count = (await cursor.fetchone())[0]
                
                # 话题活跃度
                total_keywords = len(topics)
                active_topics = len([t for t in top_topics if t['frequency'] > 2])
                topic_activity = (active_topics / max(1, total_keywords)) * 100
                
                # 讨论深度
                discussion_depth = sum(t['frequency'] for t in top_topics) / max(1, len(top_topics))
                
                return TopicsAnalysisData(
                    top_topics=top_topics,
                    new_topics_count=new_topics_count,
                    topic_activity=topic_activity,
                    discussion_depth=discussion_depth,
                    category_summary="话题类型多样，涵盖日常交流、兴趣爱好等各个方面"
                )
                
        except Exception as e:
            logger.error(f"话题分析失败: {e}")
            return None
    
    def _calculate_start_date(self, period: str) -> datetime:
        """计算开始日期"""
        now = datetime.now()
        
        if period == TimePeriod.DAY.value:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == TimePeriod.WEEK.value:
            return now - timedelta(days=7)
        elif period == TimePeriod.MONTH.value:
            return now - timedelta(days=30)
        else:
            # 解析如 "3d", "7d" 格式
            if period.endswith('d') and period[:-1].isdigit():
                days = int(period[:-1])
                return now - timedelta(days=days)
            else:
                return now - timedelta(days=7)  # 默认一周
    
    def _calculate_growth_rate(self, daily_data: List[Tuple]) -> float:
        """计算增长率"""
        if len(daily_data) < 2:
            return 0.0
        
        # 比较最近3天和前3天的平均值
        recent_avg = sum(row[1] for row in daily_data[-3:]) / min(3, len(daily_data))
        early_avg = sum(row[1] for row in daily_data[:3]) / min(3, len(daily_data))
        
        if early_avg > 0:
            return ((recent_avg - early_avg) / early_avg) * 100
        return 0.0
    
    def _generate_trend_description(self, growth_rate: float) -> str:
        """生成趋势描述"""
        if growth_rate > 10:
            return "📈 群组活跃度呈上升趋势"
        elif growth_rate < -10:
            return "📉 群组活跃度有所下降"
        else:
            return "📊 群组活跃度保持稳定"
    
    async def _calculate_participation_rate(self, db: aiosqlite.Connection, user_id: str, 
                                          start_date: datetime, message_count: int, active_days: int) -> float:
        """计算参与度"""
        try:
            # 获取群组平均值
            cursor = await db.execute(f'''
                SELECT AVG(daily_messages) as group_avg
                FROM (
                    SELECT COUNT(*) as daily_messages
                    FROM {DB.TABLE_MESSAGES} 
                    WHERE group_id = (
                        SELECT group_id FROM {DB.TABLE_MESSAGES} WHERE user_id = ? LIMIT 1
                    ) AND timestamp >= ?
                    GROUP BY user_id, DATE(timestamp)
                )
            ''', (user_id, start_date))
            
            group_avg_row = await cursor.fetchone()
            group_avg = group_avg_row[0] if group_avg_row and group_avg_row[0] else 1
            
            user_daily_avg = message_count / max(1, active_days)
            return (user_daily_avg / group_avg) * 100
            
        except Exception:
            return 50.0  # 默认中等参与度
    
    def _generate_behavior_description(self, message_count: int, avg_length: float, 
                                     active_days: int, participation_rate: float) -> str:
        """生成行为描述"""
        if participation_rate > 150:
            return "🌟 您是群组中的活跃用户，发言频率较高"
        elif avg_length > 20:
            return "📝 您倾向于发送较长的消息，内容较为丰富"
        elif active_days >= 5:
            return "⏰ 您经常参与群组讨论，是活跃成员"
        else:
            return "👤 您的参与度中等，可以尝试更多互动"
    
    async def cleanup_old_data(self, retention_days: int):
        """
        /// 清理过期数据
        /// @param retention_days: 保留天数
        """
        if retention_days <= 0:
            return
            
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 清理旧消息
                cursor = await db.execute(f'DELETE FROM {DB.TABLE_MESSAGES} WHERE timestamp < ?', (cutoff_date,))
                deleted_messages = cursor.rowcount
                
                # 清理过期缓存
                await db.execute(f'DELETE FROM {DB.TABLE_ANALYSIS_CACHE} WHERE expires_at < ?', (datetime.now(),))
                
                # 清理孤立的关键词记录
                await db.execute(f'DELETE FROM {DB.TABLE_TOPIC_KEYWORDS} WHERE last_mentioned < ?', (cutoff_date,))
                
                await db.commit()
                logger.info(f"已清理 {retention_days} 天前的数据，删除消息数: {deleted_messages}")
                
        except Exception as e:
            logger.error(f"数据清理失败: {e}")
    
    async def update_all_stats(self):
        """
        /// 更新所有统计数据
        /// 重新计算用户和群组的统计信息
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 更新用户统计中的平均字数
                await db.execute(f'''
                    UPDATE {DB.TABLE_USER_STATS} 
                    SET avg_words_per_msg = total_words * 1.0 / NULLIF(total_messages, 0),
                        updated_at = ?
                    WHERE total_messages > 0
                ''', (datetime.now(),))
                
                # 更新活跃天数
                await db.execute(f'''
                    UPDATE {DB.TABLE_USER_STATS} 
                    SET active_days = (
                        SELECT COUNT(DISTINCT DATE(timestamp))
                        FROM {DB.TABLE_MESSAGES}
                        WHERE {DB.TABLE_MESSAGES}.user_id = {DB.TABLE_USER_STATS}.user_id
                    )
                ''')
                
                await db.commit()
                logger.info("统计数据更新完成")
                
        except Exception as e:
            logger.error(f"统计更新失败: {e}")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """
        /// 获取数据库统计信息
        /// @return: 数据库状态信息
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                # 表行数统计
                for table in [DB.TABLE_MESSAGES, DB.TABLE_USER_STATS, 
                             DB.TABLE_GROUP_STATS, DB.TABLE_TOPIC_KEYWORDS]:
                    cursor = await db.execute(f'SELECT COUNT(*) FROM {table}')
                    stats[f'{table}_count'] = (await cursor.fetchone())[0]
                
                # 数据库文件大小
                db_path = Path(self.db_path)
                if db_path.exists():
                    stats['db_size_mb'] = db_path.stat().st_size / (1024 * 1024)
                
                return stats
                
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {}
    
    # ==================== Phase 2 新增：词云历史管理 ====================
    
    async def save_wordcloud_history(
        self,
        group_id: str,
        time_range: str,
        word_data: Dict[str, int],
        style_name: str,
        file_path: str = None,
        metadata: Dict = None
    ) -> int:
        """
        保存词云历史记录
        """
        try:
            import json
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO wordcloud_history 
                    (group_id, time_range, word_data, style_name, total_words, file_path, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    group_id,
                    time_range,
                    json.dumps(word_data, ensure_ascii=False),
                    style_name,
                    len(word_data),
                    file_path,
                    json.dumps(metadata or {}, ensure_ascii=False)
                ))
                
                await db.commit()
                record_id = cursor.lastrowid
                logger.info(f"词云历史记录已保存: {record_id}")
                return record_id
                
        except Exception as e:
            logger.error(f"保存词云历史失败: {e}")
            return None
    
    async def get_wordcloud_history(
        self,
        group_id: str,
        limit: int = 10,
        time_range: str = None
    ) -> List[Dict]:
        """获取词云历史记录"""
        try:
            import json
            
            async with aiosqlite.connect(self.db_path) as db:
                if time_range:
                    cursor = await db.execute("""
                        SELECT * FROM wordcloud_history 
                        WHERE group_id = ? AND time_range = ?
                        ORDER BY generated_at DESC 
                        LIMIT ?
                    """, (group_id, time_range, limit))
                else:
                    cursor = await db.execute("""
                        SELECT * FROM wordcloud_history 
                        WHERE group_id = ?
                        ORDER BY generated_at DESC 
                        LIMIT ?
                    """, (group_id, limit))
                
                rows = await cursor.fetchall()
                
                # 转换为字典格式
                history = []
                for row in rows:
                    record = {
                        'id': row[0],
                        'group_id': row[1],
                        'time_range': row[2],
                        'word_data': json.loads(row[3]),
                        'style_name': row[4],
                        'total_words': row[5],
                        'file_path': row[6],
                        'metadata': json.loads(row[7]) if row[7] else {},
                        'generated_at': row[8],
                        'created_at': row[9]
                    }
                    history.append(record)
                
                return history
                
        except Exception as e:
            logger.error(f"获取词云历史失败: {e}")
            return []
    
    async def compare_wordcloud_history(
        self,
        group_id: str,
        current_data: Dict[str, int],
        days_back: int = 7
    ) -> Dict[str, Any]:
        """对比词云历史数据"""
        try:
            import json
            from datetime import datetime, timedelta
            
            # 获取历史数据
            compare_date = datetime.now() - timedelta(days=days_back)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT word_data, generated_at FROM wordcloud_history 
                    WHERE group_id = ? AND generated_at <= ?
                    ORDER BY generated_at DESC 
                    LIMIT 1
                """, (group_id, compare_date.isoformat()))
                
                row = await cursor.fetchone()
                
                if not row:
                    return {
                        'comparison_available': False,
                        'message': f'没有找到{days_back}天前的词云数据'
                    }
                
                historical_data = json.loads(row[0])
                historical_date = row[1]
                
                # 进行对比分析
                comparison = self._analyze_wordcloud_changes(
                    current_data, historical_data, historical_date
                )
                
                return {
                    'comparison_available': True,
                    'historical_date': historical_date,
                    'days_compared': days_back,
                    **comparison
                }
                
        except Exception as e:
            logger.error(f"词云历史对比失败: {e}")
            return {'comparison_available': False, 'error': str(e)}
    
    def _analyze_wordcloud_changes(
        self, 
        current_data: Dict[str, int], 
        historical_data: Dict[str, int],
        historical_date: str
    ) -> Dict[str, Any]:
        """分析词云数据变化"""
        # 新增词汇
        new_words = set(current_data.keys()) - set(historical_data.keys())
        
        # 消失词汇
        disappeared_words = set(historical_data.keys()) - set(current_data.keys())
        
        # 频率变化
        frequency_changes = {}
        for word in set(current_data.keys()) & set(historical_data.keys()):
            current_freq = current_data[word]
            historical_freq = historical_data[word]
            change = current_freq - historical_freq
            if change != 0:
                frequency_changes[word] = {
                    'current': current_freq,
                    'historical': historical_freq,
                    'change': change,
                    'change_percent': (change / historical_freq) * 100 if historical_freq > 0 else 100
                }
        
        # 热度上升词汇
        rising_words = sorted(
            [(word, data['change']) for word, data in frequency_changes.items() if data['change'] > 0],
            key=lambda x: x[1], reverse=True
        )[:5]
        
        # 热度下降词汇
        falling_words = sorted(
            [(word, data['change']) for word, data in frequency_changes.items() if data['change'] < 0],
            key=lambda x: x[1]
        )[:5]
        
        return {
            'new_words': list(new_words)[:10],
            'disappeared_words': list(disappeared_words)[:10],
            'rising_words': rising_words,
            'falling_words': falling_words,
            'total_current_words': len(current_data),
            'total_historical_words': len(historical_data),
            'word_growth': len(current_data) - len(historical_data),
            'frequency_changes_count': len(frequency_changes)
        }
    
    # ==================== Phase 3 新增：用户画像数据管理 ====================
    
    async def save_user_portrait(
        self,
        user_portrait
    ) -> Optional[int]:
        """
        保存用户画像到数据库
        
        Args:
            user_portrait: UserPortrait 对象
            
        Returns:
            画像记录ID
        """
        try:
            import json
            
            async with aiosqlite.connect(self.db_path) as db:
                # 使用 REPLACE 来更新或插入
                cursor = await db.execute("""
                    REPLACE INTO user_portraits 
                    (user_id, group_id, nickname, portrait_data, analysis_depth, 
                     data_quality_score, analysis_duration, generated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_portrait.user_id,
                    user_portrait.group_id,
                    user_portrait.nickname,
                    json.dumps(user_portrait.to_dict(), ensure_ascii=False),
                    user_portrait.analysis_depth,
                    user_portrait.data_quality_score,
                    user_portrait.analysis_duration,
                    user_portrait.analysis_date.isoformat()
                ))
                
                await db.commit()
                record_id = cursor.lastrowid
                
                logger.info(f"用户画像已保存: {user_portrait.user_id} (ID: {record_id})")
                return record_id
                
        except Exception as e:
            logger.error(f"保存用户画像失败: {e}")
            return None
    
    async def get_user_portrait(
        self,
        user_id: str,
        group_id: str,
        analysis_depth: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户画像
        
        Args:
            user_id: 用户ID
            group_id: 群组ID
            analysis_depth: 分析深度（可选）
            
        Returns:
            用户画像数据
        """
        try:
            import json
            
            async with aiosqlite.connect(self.db_path) as db:
                if analysis_depth:
                    cursor = await db.execute("""
                        SELECT portrait_data, generated_at FROM user_portraits 
                        WHERE user_id = ? AND group_id = ? AND analysis_depth = ?
                        ORDER BY generated_at DESC 
                        LIMIT 1
                    """, (user_id, group_id, analysis_depth))
                else:
                    cursor = await db.execute("""
                        SELECT portrait_data, generated_at FROM user_portraits 
                        WHERE user_id = ? AND group_id = ?
                        ORDER BY generated_at DESC 
                        LIMIT 1
                    """, (user_id, group_id))
                
                row = await cursor.fetchone()
                
                if row:
                    portrait_data = json.loads(row[0])
                    return portrait_data
                
                return None
                
        except Exception as e:
            logger.error(f"获取用户画像失败: {e}")
            return None
    
    async def get_user_portrait_history(
        self,
        user_id: str,
        group_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取用户画像历史记录
        
        Args:
            user_id: 用户ID
            group_id: 群组ID
            limit: 记录数量限制
            
        Returns:
            画像历史记录列表
        """
        try:
            import json
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT analysis_type, analysis_depth, result_summary, 
                           file_paths, metadata, analysis_time, generated_at
                    FROM portrait_analysis_history 
                    WHERE user_id = ? AND group_id = ?
                    ORDER BY generated_at DESC 
                    LIMIT ?
                """, (user_id, group_id, limit))
                
                rows = await cursor.fetchall()
                
                history = []
                for row in rows:
                    record = {
                        'analysis_type': row[0],
                        'analysis_depth': row[1],
                        'result_summary': row[2],
                        'file_paths': json.loads(row[3]) if row[3] else [],
                        'metadata': json.loads(row[4]) if row[4] else {},
                        'analysis_time': row[5],
                        'generated_at': row[6]
                    }
                    history.append(record)
                
                return history
                
        except Exception as e:
            logger.error(f"获取用户画像历史失败: {e}")
            return []
    
    async def save_portrait_analysis_history(
        self,
        user_id: str,
        group_id: str,
        analysis_type: str,
        analysis_depth: str,
        result_summary: str = None,
        file_paths: List[str] = None,
        metadata: Dict[str, Any] = None,
        analysis_time: float = None
    ) -> Optional[int]:
        """
        保存画像分析历史记录
        
        Args:
            user_id: 用户ID
            group_id: 群组ID
            analysis_type: 分析类型 ('portrait', 'comparison')
            analysis_depth: 分析深度
            result_summary: 结果摘要
            file_paths: 相关文件路径列表
            metadata: 元数据
            analysis_time: 分析耗时
            
        Returns:
            历史记录ID
        """
        try:
            import json
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO portrait_analysis_history 
                    (user_id, group_id, analysis_type, analysis_depth, 
                     result_summary, file_paths, metadata, analysis_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    group_id,
                    analysis_type,
                    analysis_depth,
                    result_summary,
                    json.dumps(file_paths or [], ensure_ascii=False),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    analysis_time
                ))
                
                await db.commit()
                record_id = cursor.lastrowid
                
                logger.info(f"画像分析历史已保存: {user_id} (ID: {record_id})")
                return record_id
                
        except Exception as e:
            logger.error(f"保存画像分析历史失败: {e}")
            return None
    
    async def get_group_portrait_statistics(
        self,
        group_id: str
    ) -> Dict[str, Any]:
        """
        获取群组画像统计信息
        
        Args:
            group_id: 群组ID
            
        Returns:
            群组画像统计数据
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 统计用户画像数量
                cursor = await db.execute("""
                    SELECT COUNT(DISTINCT user_id) as unique_users,
                           COUNT(*) as total_portraits,
                           analysis_depth,
                           AVG(data_quality_score) as avg_quality,
                           AVG(analysis_duration) as avg_duration
                    FROM user_portraits 
                    WHERE group_id = ?
                    GROUP BY analysis_depth
                """, (group_id,))
                
                portrait_stats = await cursor.fetchall()
                
                # 统计分析历史
                cursor = await db.execute("""
                    SELECT analysis_type, COUNT(*) as count,
                           AVG(analysis_time) as avg_time
                    FROM portrait_analysis_history 
                    WHERE group_id = ?
                    GROUP BY analysis_type
                """, (group_id,))
                
                history_stats = await cursor.fetchall()
                
                # 最近活动
                cursor = await db.execute("""
                    SELECT COUNT(*) as recent_analyses
                    FROM portrait_analysis_history 
                    WHERE group_id = ? AND generated_at > datetime('now', '-7 days')
                """, (group_id,))
                
                recent_activity = await cursor.fetchone()
                
                return {
                    'portrait_statistics': [
                        {
                            'unique_users': row[0],
                            'total_portraits': row[1],
                            'analysis_depth': row[2],
                            'avg_quality_score': row[3],
                            'avg_duration': row[4]
                        }
                        for row in portrait_stats
                    ],
                    'analysis_history': [
                        {
                            'analysis_type': row[0],
                            'count': row[1],
                            'avg_time': row[2]
                        }
                        for row in history_stats
                    ],
                    'recent_activity': {
                        'analyses_last_7_days': recent_activity[0] if recent_activity else 0
                    }
                }
                
        except Exception as e:
            logger.error(f"获取群组画像统计失败: {e}")
            return {}
    
    async def cleanup_old_portraits(self, days_to_keep: int = 30):
        """
        清理旧的用户画像记录
        
        Args:
            days_to_keep: 保留多少天的记录
        """
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 清理用户画像
                cursor = await db.execute("""
                    DELETE FROM user_portraits 
                    WHERE generated_at < ?
                """, (cutoff_date.isoformat(),))
                
                portraits_deleted = cursor.rowcount
                
                # 清理分析历史
                cursor = await db.execute("""
                    DELETE FROM portrait_analysis_history 
                    WHERE generated_at < ?
                """, (cutoff_date.isoformat(),))
                
                history_deleted = cursor.rowcount
                
                await db.commit()
                
                if portraits_deleted > 0 or history_deleted > 0:
                    logger.info(f"已清理用户画像: {portraits_deleted} 条，分析历史: {history_deleted} 条")
                
        except Exception as e:
            logger.error(f"清理用户画像记录失败: {e}")
    
    async def get_portrait_cache_key(
        self,
        user_id: str,
        group_id: str,
        analysis_depth: str,
        days_back: int
    ) -> str:
        """
        生成画像缓存键
        
        Args:
            user_id: 用户ID
            group_id: 群组ID
            analysis_depth: 分析深度
            days_back: 分析天数
            
        Returns:
            缓存键
        """
        return f"portrait_{user_id}_{group_id}_{analysis_depth}_{days_back}"
    
    async def is_portrait_cache_valid(
        self,
        user_id: str,
        group_id: str,
        analysis_depth: str,
        cache_ttl_hours: int = 24
    ) -> bool:
        """
        检查画像缓存是否有效
        
        Args:
            user_id: 用户ID
            group_id: 群组ID
            analysis_depth: 分析深度
            cache_ttl_hours: 缓存有效期（小时）
            
        Returns:
            缓存是否有效
        """
        try:
            from datetime import datetime, timedelta
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT generated_at FROM user_portraits 
                    WHERE user_id = ? AND group_id = ? AND analysis_depth = ?
                    ORDER BY generated_at DESC 
                    LIMIT 1
                """, (user_id, group_id, analysis_depth))
                
                row = await cursor.fetchone()
                
                if row:
                    last_generated = datetime.fromisoformat(row[0])
                    cache_cutoff = datetime.now() - timedelta(hours=cache_ttl_hours)
                    return last_generated > cache_cutoff
                
                return False
                
        except Exception as e:
            logger.error(f"检查画像缓存有效性失败: {e}")
            return False

    async def close(self):
        """
        /// 关闭数据库连接
        /// 清理资源
        """
        # aiosqlite 每次操作都会自动管理连接，无需显式关闭
        self.is_initialized = False
        logger.info("数据库管理器已关闭")
