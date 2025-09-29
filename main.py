"""
AstrBot 数据分析师插件 - 主模块

提供群聊数据分析、用户行为洞察、话题趋势预测等功能
支持多种数据可视化和导出格式
"""

import asyncio
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# AstrBot 核心导入
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig, logger
import astrbot.api.message_components as Comp

# 数据库
import aiosqlite

# 插件模块导入
from .models import PluginConfig, AnalysisType, ChartType, ExportFormat, TimePeriod
from .privacy import PrivacyFilter
from .database import DatabaseManager
from .charts import ChartGenerator
from .export import ExportManager
from .predictor import PredictorService
from .font_manager import FontManager
from .wordcloud_enhanced import AdvancedWordCloudGenerator
from .natural_language import NaturalLanguageProcessor, CommandType, CommandIntent
from .portrait_analyzer import UserPortraitAnalyzer, AnalysisDepth
from .portrait_visualizer import PortraitVisualizer


@register("data_analyst", "DataAnalyst Team", "智能数据分析师插件", "1.0.0")
class DataAnalystPlugin(Star):
    """
    /// 数据分析师插件主类
    /// 提供群聊数据收集、分析、可视化和导出功能
    /// 支持用户行为分析、话题热度统计、活跃度预测等高级功能
    """
    
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.raw_config = config
        self.config = PluginConfig(config)
        
        # 初始化数据目录
        self.data_dir = Path("data/plugins/data_analyst")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.data_dir / "charts").mkdir(exist_ok=True)
        (self.data_dir / "exports").mkdir(exist_ok=True)
        (self.data_dir / "cache").mkdir(exist_ok=True)
        
        # 初始化组件
        self.db_manager = None
        self.privacy_filter = PrivacyFilter(self.config.privacy_settings)
        self.font_manager = FontManager(self.data_dir)
        self.chart_generator = None
        self.export_manager = None
        self.predictor_service = None
        
        # Phase 2 新增组件
        self.advanced_wordcloud_generator = None
        self.natural_language_processor = None
        
        # Phase 3 新增组件
        self.portrait_analyzer = None
        self.portrait_visualizer = None
        
        # 缓存管理
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, float] = {}
        
        # 启动初始化任务
        asyncio.create_task(self._initialize_async())
        
        # 启动后台任务
        asyncio.create_task(self._start_background_tasks())
        
        logger.info("数据分析师插件已加载")

    async def _initialize_async(self):
        """
        /// 异步初始化组件
        /// 初始化数据库和各个服务组件
        """
        try:
            # 初始化数据库管理器
            db_path = self.data_dir / "analytics.db"
            self.db_manager = DatabaseManager(str(db_path))
            await self.db_manager.initialize()
            
            # 初始化图表生成器
            self.chart_generator = ChartGenerator(
                self.data_dir / "charts", 
                self.config,
                self.font_manager
            )
            
            # 初始化高级词云生成器
            self.advanced_wordcloud_generator = AdvancedWordCloudGenerator(
                self.data_dir / "charts",
                self.font_manager,
                self.config
            )
            
            # Phase 2 新增：初始化自然语言处理器
            try:
                self.natural_language_processor = NaturalLanguageProcessor(self.db_manager)
                logger.info("自然语言处理器初始化成功")
            except Exception as e:
                logger.error(f"自然语言处理器初始化失败: {e}")
                self.natural_language_processor = None
            
            # 初始化用户画像分析器 (Phase 3)
            try:
                self.portrait_analyzer = UserPortraitAnalyzer(
                    self.db_manager,
                    self.config
                )
                logger.info("用户画像分析器初始化成功")
            except Exception as e:
                logger.error(f"用户画像分析器初始化失败: {e}")
                self.portrait_analyzer = None
            
            # 初始化画像可视化器 (Phase 3)
            try:
                self.portrait_visualizer = PortraitVisualizer(
                    self.data_dir / "charts",
                    self.font_manager,
                    self.config
                )
                logger.info("画像可视化器初始化成功")
            except Exception as e:
                logger.error(f"画像可视化器初始化失败: {e}")
                self.portrait_visualizer = None
            
            # 初始化导出管理器
            self.export_manager = ExportManager(
                self.data_dir / "exports", 
                self.db_manager,
                self.config
            )
            
            # 初始化预测服务
            self.predictor_service = PredictorService(self.db_manager)
            
            logger.info("所有组件初始化完成")
            
        except Exception as e:
            logger.error(f"组件初始化失败: {e}")

    async def _start_background_tasks(self):
        """
        /// 启动后台任务
        /// 包括数据清理、缓存维护、定期统计等
        """
        # 每小时清理过期缓存
        asyncio.create_task(self._cache_cleanup_task())
        
        # 每天清理过期数据
        asyncio.create_task(self._data_cleanup_task())
        
        # 每6小时更新统计数据
        asyncio.create_task(self._stats_update_task())
        
        # 每天清理过期图表和导出文件
        asyncio.create_task(self._file_cleanup_task())

    async def _cache_cleanup_task(self):
        """后台缓存清理任务"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时执行一次
                await self._cleanup_expired_cache()
            except Exception as e:
                logger.error(f"缓存清理任务错误: {e}")

    async def _data_cleanup_task(self):
        """后台数据清理任务"""
        while True:
            try:
                await asyncio.sleep(86400)  # 每天执行一次
                if self.db_manager:
                    await self.db_manager.cleanup_old_data(self.config.data_retention_days)
            except Exception as e:
                logger.error(f"数据清理任务错误: {e}")

    async def _stats_update_task(self):
        """后台统计更新任务"""
        while True:
            try:
                await asyncio.sleep(21600)  # 每6小时执行一次
                if self.db_manager:
                    await self.db_manager.update_all_stats()
            except Exception as e:
                logger.error(f"统计更新任务错误: {e}")

    async def _file_cleanup_task(self):
        """后台文件清理任务"""
        while True:
            try:
                await asyncio.sleep(86400)  # 每天执行一次
                
                # 清理过期图表
                if self.chart_generator:
                    await self.chart_generator.cleanup_old_charts(24)
                
                # 清理过期导出文件
                if self.export_manager:
                    await self.export_manager.cleanup_old_exports(7)
                    
            except Exception as e:
                logger.error(f"文件清理任务错误: {e}")

    # ==================== 事件监听器 ====================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def message_collector(self, event: AstrMessageEvent):
        """
        /// 消息收集器 - 自动收集群聊数据
        /// @param event: AstrBot消息事件
        /// 在后台自动收集消息数据，不影响用户交互
        """
        # 检查是否启用自动收集
        if not self.config.enable_auto_collect:
            return
            
        # 检查群组权限
        allowed_groups = self.config.allowed_groups
        group_id = event.get_group_id()
        if allowed_groups and group_id and group_id not in allowed_groups:
            return
            
        try:
            # 自然语言命令处理 (Phase 2 新功能)
            message_text = event.message_str.strip()
            if message_text and not message_text.startswith('/') and self.natural_language_processor:
                # 注意：自然语言处理可能返回生成器，需要特殊处理
                try:
                    async for _ in self._handle_natural_language_command(event, message_text):
                        pass  # 自然语言处理的结果由该方法内部处理
                except TypeError:
                    # 如果不是生成器，直接调用
                    pass
            
            if self.db_manager:
                await self.db_manager.collect_message(event, self.privacy_filter)
        except Exception as e:
            logger.error(f"消息收集失败: {e}")

    # ==================== 命令处理器 ====================

    @filter.command("stats")
    async def quick_stats(self, event: AstrMessageEvent):
        """
        /// 快速统计命令
        /// 显示当前群组的基础统计信息
        """
        try:
            group_id = event.get_group_id()
            if not group_id:
                yield event.plain_result("此命令仅在群聊中使用")
                return
                
            if not self.db_manager:
                yield event.plain_result("数据库未初始化，请稍后重试")
                return
                
            # 获取基础统计
            stats = await self.db_manager.get_group_quick_stats(group_id)
            
            if not stats:
                yield event.plain_result("暂无数据，请先让我收集一些消息后再试")
                return
                
            result = f"""📊 群组快速统计

📈 总消息数: {stats.get('total_messages', 0)}
👥 活跃成员: {stats.get('active_users', 0)}
📅 数据收集天数: {stats.get('data_days', 0)}
🕐 最活跃时段: {stats.get('peak_hour', 'N/A')}时
📝 平均消息长度: {stats.get('avg_message_length', 0):.1f}字

💡 使用 /analyze 获取详细分析报告"""
            
            yield event.plain_result(result)
            
        except Exception as e:
            logger.error(f"快速统计失败: {e}")
            yield event.plain_result("统计失败，请查看日志")

    @filter.command("analyze")
    async def analyze_command(self, event: AstrMessageEvent, 
                            analysis_type: str = "activity", 
                            period: str = "week"):
        """
        /// 数据分析命令
        /// @param analysis_type: 分析类型 (activity/user/topics)
        /// @param period: 时间周期 (day/week/month)
        """
        try:
            # 权限检查
            if not self._check_analysis_permission(event):
                yield event.plain_result("权限不足，请联系管理员")
                return
                
            yield event.plain_result("🔄 正在分析数据，请稍候...")
            
            group_id = event.get_group_id()
            if not group_id and analysis_type != AnalysisType.USER.value:
                yield event.plain_result("此分析类型仅在群聊中使用")
                return
                
            if not self.db_manager:
                yield event.plain_result("数据库未初始化")
                return
                
            # 执行分析
            result = None
            if analysis_type == AnalysisType.ACTIVITY.value:
                result = await self._analyze_activity(group_id, period)
            elif analysis_type == AnalysisType.USER.value:
                user_id = event.get_sender_id()
                result = await self._analyze_user_behavior(user_id, period)
            elif analysis_type == AnalysisType.TOPICS.value:
                result = await self._analyze_topics(group_id, period)
            else:
                yield event.plain_result("支持的分析类型: activity, user, topics")
                return
                
            # 发送结果
            if result:
                yield event.plain_result(result["text"])
                if result.get("chart_path") and os.path.exists(result["chart_path"]):
                    yield event.image_result(result["chart_path"])
            else:
                yield event.plain_result("数据不足，无法生成分析报告")
                
        except Exception as e:
            logger.error(f"分析命令失败: {e}\n{traceback.format_exc()}")
            yield event.plain_result("分析失败，请查看日志或联系管理员")

    @filter.command("chart")
    async def chart_command(self, event: AstrMessageEvent,
                          chart_type: str,
                          data_range: str = "week"):
        """
        /// 图表生成命令
        /// @param chart_type: 图表类型 (activity/ranking/wordcloud/heatmap)
        /// @param data_range: 数据范围
        """
        try:
            if not self._check_analysis_permission(event):
                yield event.plain_result("权限不足")
                return
                
            yield event.plain_result("🎨 正在生成图表...")
            
            group_id = event.get_group_id()
            if not group_id:
                yield event.plain_result("此命令仅在群聊中使用")
                return
                
            if not self.chart_generator:
                yield event.plain_result("图表生成器未初始化")
                return
                
            chart_path = None
            
            if chart_type == ChartType.ACTIVITY.value:
                data = await self.db_manager.get_activity_analysis(group_id, data_range)
                if data:
                    chart_path = await self.chart_generator.generate_activity_trend_chart(data, group_id)
                    
            elif chart_type == ChartType.WORDCLOUD.value:
                data = await self.db_manager.get_topics_analysis(group_id, data_range)
                if data:
                    chart_path = await self.chart_generator.generate_topics_wordcloud(data, group_id)
                    
            elif chart_type == ChartType.RANKING.value:
                # 获取用户排行数据
                async with aiosqlite.connect(self.db_manager.db_path) as db:
                    start_date = self.db_manager._calculate_start_date(data_range)
                    cursor = await db.execute('''
                        SELECT user_id, COUNT(*) as message_count, SUM(word_count) as word_count
                        FROM messages 
                        WHERE group_id = ? AND timestamp >= ?
                        GROUP BY user_id
                        ORDER BY message_count DESC
                        LIMIT ?
                    ''', (group_id, start_date, self.config.max_chart_items))
                    
                    users_data = [
                        {
                            'username': f'用户{i+1}',
                            'message_count': row[1],
                            'word_count': row[2]
                        }
                        for i, row in enumerate(await cursor.fetchall())
                    ]
                    
                    if users_data:
                        chart_path = await self.chart_generator.generate_user_ranking_chart(users_data, group_id)
                        
            elif chart_type == ChartType.HEATMAP.value:
                # 获取热力图数据
                async with aiosqlite.connect(self.db_manager.db_path) as db:
                    start_date = self.db_manager._calculate_start_date(data_range)
                    cursor = await db.execute('''
                        SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                        FROM messages 
                        WHERE group_id = ? AND timestamp >= ?
                        GROUP BY hour
                    ''', (group_id, start_date))
                    
                    hourly_data = {row[0]: row[1] for row in await cursor.fetchall()}
                    heatmap_data = {'hourly_data': hourly_data}
                    
                    if hourly_data:
                        chart_path = await self.chart_generator.generate_activity_heatmap(heatmap_data, group_id)
            else:
                yield event.plain_result("支持的图表类型: activity, ranking, wordcloud, heatmap")
                return
                
            if chart_path and os.path.exists(chart_path):
                yield event.image_result(chart_path)
            else:
                yield event.plain_result("数据不足，无法生成图表")
                
        except Exception as e:
            logger.error(f"图表生成失败: {e}")
            yield event.plain_result("图表生成失败")

    @filter.command("export")
    async def export_command(self, event: AstrMessageEvent,
                           format_type: str = "excel",
                           range_period: str = "month"):
        """
        /// 数据导出命令
        /// @param format_type: 导出格式 (excel/pdf/csv/json)
        /// @param range_period: 数据范围
        """
        try:
            # 检查管理员权限
            if not self.config.admin_users or event.get_sender_id() not in self.config.admin_users:
                yield event.plain_result("只有管理员可以导出数据")
                return
                
            yield event.plain_result("📤 正在导出数据...")
            
            group_id = event.get_group_id()
            if not group_id:
                yield event.plain_result("此命令仅在群聊中使用")
                return
                
            if not self.export_manager:
                yield event.plain_result("导出管理器未初始化")
                return
                
            file_path = None
            
            if format_type == ExportFormat.EXCEL.value:
                file_path = await self.export_manager.export_to_excel(group_id, range_period)
            elif format_type == ExportFormat.PDF.value:
                file_path = await self.export_manager.export_to_pdf(group_id, range_period)
            elif format_type == ExportFormat.CSV.value:
                file_path = await self.export_manager.export_to_csv(group_id, range_period)
            elif format_type == ExportFormat.JSON.value:
                file_path = await self.export_manager.export_to_json(group_id, range_period)
            else:
                yield event.plain_result("支持的格式: excel, pdf, csv, json")
                return
                
            if file_path and os.path.exists(file_path):
                yield event.chain_result([
                    Comp.Plain(f"导出完成: {os.path.basename(file_path)}"),
                    Comp.File(file=file_path, name=os.path.basename(file_path))
                ])
            else:
                yield event.plain_result("导出失败或数据不足")
                
        except Exception as e:
            logger.error(f"数据导出失败: {e}")
            yield event.plain_result("导出失败")

    @filter.command("predict")
    async def predict_command(self, event: AstrMessageEvent,
                            target: str = "activity",
                            days: int = 7):
        """
        /// 预测分析命令
        /// @param target: 预测目标 (activity/members)
        /// @param days: 预测天数
        """
        try:
            if not self._check_analysis_permission(event):
                yield event.plain_result("权限不足")
                return
                
            if days > 30:
                yield event.plain_result("预测天数不能超过30天")
                return
                
            yield event.plain_result("🔮 正在进行预测分析...")
            
            group_id = event.get_group_id()
            if not group_id:
                yield event.plain_result("此命令仅在群聊中使用")
                return
                
            if not self.predictor_service:
                yield event.plain_result("预测服务未初始化")
                return
                
            result = await self.predictor_service.predict(group_id, target, days)
            
            if result:
                yield event.plain_result(result.description)
                
                # 生成预测图表
                if hasattr(result, 'predictions') and result.predictions:
                    activity_data = await self.db_manager.get_activity_analysis(group_id, "month")
                    if activity_data:
                        historical = [row[1] for row in activity_data.daily_data[-14:]]  # 最近14天
                        chart_path = await self.chart_generator.generate_prediction_chart(
                            historical, result.predictions, group_id, target
                        )
                        if chart_path and os.path.exists(chart_path):
                            yield event.image_result(chart_path)
            else:
                yield event.plain_result("历史数据不足，无法进行预测")
                
        except Exception as e:
            logger.error(f"预测分析失败: {e}")
            yield event.plain_result("预测失败")

    @filter.command("help_data")
    async def help_command(self, event: AstrMessageEvent):
        """
        /// 帮助命令
        /// 显示所有可用的数据分析命令和使用方法
        """
        help_text = """📊 数据分析师插件使用指南

🚀 快速命令:
/stats - 查看群组快速统计

📈 分析命令:
/analyze activity [period] - 活跃度分析
/analyze user [period] - 个人行为分析  
/analyze topics [period] - 话题热度分析

🎨 图表命令:
/chart activity [range] - 活跃度图表
/chart ranking [range] - 用户排行榜
/chart wordcloud [range] - 词云图
/chart heatmap [range] - 活跃时段热力图

📤 导出命令 (管理员):
/export excel [period] - 导出Excel报告
/export pdf [period] - 导出PDF报告
/export csv [period] - 导出CSV数据
/export json [period] - 导出JSON数据

🔮 预测命令:
/predict activity [days] - 活跃度预测

⏰ 时间参数:
- day: 今天
- week: 本周  
- month: 本月
- 3d, 7d, 30d: 最近N天

💡 提示: 需要收集足够数据后才能进行分析"""
        
        yield event.plain_result(help_text)

    # ==================== 辅助方法 ====================

    def _check_analysis_permission(self, event: AstrMessageEvent) -> bool:
        """
        /// 检查分析权限
        /// @param event: 消息事件
        /// @return: 是否有权限
        """
        admin_users = self.config.admin_users
        if not admin_users:  # 如果没有设置管理员，则所有人都可以使用
            return True
        return event.get_sender_id() in admin_users

    async def _analyze_activity(self, group_id: str, period: str) -> Optional[Dict]:
        """分析群组活跃度"""
        cache_key = f"activity_{group_id}_{period}"
        cached = await self._get_cached_result(cache_key)
        if cached:
            return cached
            
        data = await self.db_manager.get_activity_analysis(group_id, period)
        if not data:
            return None
            
        # 生成分析文本
        text = f"""📈 群组活跃度分析 ({period})

📊 统计数据:
• 总消息数: {data.total_messages}
• 活跃用户数: {data.active_users}
• 平均每日消息: {data.avg_daily_messages:.1f}
• 消息增长率: {data.growth_rate:.1f}%

🕐 活跃时段:
• 最活跃时间: {data.peak_hour}:00
• 最活跃日期: {data.peak_day}

📈 趋势分析:
{data.trend_description}"""
        
        # 生成图表
        chart_path = await self.chart_generator.generate_activity_trend_chart(data, group_id)
        
        result = {"text": text, "chart_path": chart_path}
        await self._cache_result(cache_key, result)
        return result

    async def _analyze_user_behavior(self, user_id: str, period: str) -> Optional[Dict]:
        """分析用户行为"""
        cache_key = f"user_{user_id}_{period}"
        cached = await self._get_cached_result(cache_key)
        if cached:
            return cached
            
        data = await self.db_manager.get_user_analysis(user_id, period)
        if not data:
            return None
            
        text = f"""👤 个人行为分析 ({period})

📝 消息统计:
• 发送消息数: {data.message_count}
• 平均消息长度: {data.avg_length:.1f}字
• 活跃天数: {data.active_days}
• 参与度: {data.participation_rate:.1f}%

🕐 活动模式:
• 最活跃时段: {data.most_active_hour}:00
• 发言间隔: {data.avg_interval}

📊 行为特征:
{data.behavior_description}"""
        
        result = {"text": text}
        await self._cache_result(cache_key, result)
        return result

    async def _analyze_topics(self, group_id: str, period: str) -> Optional[Dict]:
        """分析话题热度"""
        cache_key = f"topics_{group_id}_{period}"
        cached = await self._get_cached_result(cache_key)
        if cached:
            return cached
            
        data = await self.db_manager.get_topics_analysis(group_id, period)
        if not data:
            return None
            
        # 生成热门话题列表
        topics_list = "\n".join([
            f"• {topic['keyword']}: {topic['frequency']}次"
            for topic in data.top_topics[:10]
        ])
        
        text = f"""🔥 话题热度分析 ({period})

📋 热门话题:
{topics_list}

📈 话题趋势:
• 新话题数量: {data.new_topics_count}
• 话题活跃度: {data.topic_activity:.1f}%
• 讨论深度: {data.discussion_depth:.1f}

🏷️ 话题分类:
{data.category_summary}"""
        
        # 生成词云
        chart_path = await self.chart_generator.generate_topics_wordcloud(data, group_id)
        
        result = {"text": text, "chart_path": chart_path}
        await self._cache_result(cache_key, result)
        return result

    async def _get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """获取缓存结果"""
        if cache_key in self.cache:
            cache_time = self.cache_timestamps.get(cache_key, 0)
            if time.time() - cache_time < self.config.cache_ttl:
                return self.cache[cache_key]
        return None

    async def _cache_result(self, cache_key: str, result: Dict):
        """缓存结果"""
        self.cache[cache_key] = result
        self.cache_timestamps[cache_key] = time.time()

    async def _cleanup_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        ttl = self.config.cache_ttl
        
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items()
            if current_time - timestamp > ttl
        ]
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.cache_timestamps.pop(key, None)

    # ==================== Phase 2 新增功能：自然语言处理 ====================
    
    async def _handle_natural_language_command(self, event: AstrMessageEvent, message: str):
        """
        处理自然语言命令
        """
        try:
            # 检查自然语言处理器是否已初始化
            if not self.natural_language_processor:
                logger.warning("自然语言处理器未初始化")
                return
            
            # 使用自然语言处理器解析命令
            intent = self.natural_language_processor.parse_natural_command(message)
            
            # 只处理高置信度的命令（避免误触发）
            if intent.confidence < 0.6:
                return
            
            # 根据命令类型执行相应操作
            if intent.command_type == CommandType.WORDCLOUD:
                async for result in self._handle_wordcloud_nl_command(event, intent):
                    yield result
            elif intent.command_type == CommandType.STATS:
                async for result in self._handle_stats_nl_command(event, intent):
                    yield result
            elif intent.command_type == CommandType.PORTRAIT:
                async for result in self._handle_portrait_nl_command(event, intent):
                    yield result
            elif intent.command_type == CommandType.HELP:
                async for result in self._handle_help_nl_command(event, intent):
                    yield result
                
        except Exception as e:
            logger.error(f"自然语言命令处理失败: {e}")
    
    async def _handle_wordcloud_nl_command(self, event: AstrMessageEvent, intent: CommandIntent):
        """处理词云相关自然语言命令"""
        try:
            group_id = event.get_group_id()
            if not group_id:
                yield event.plain_result("词云功能仅在群聊中使用")
                return
            
            yield event.plain_result("🎨 理解了！正在生成词云图...")
            
            if not self.db_manager:
                yield event.plain_result("❌ 数据库未初始化")
                return
                
            topics_data = await self.db_manager.get_topics_analysis(group_id, 'week')
            if not topics_data or not topics_data.top_topics:
                yield event.plain_result("暂无足够数据生成词云")
                return
            
            # 转换为词频字典
            word_freq = {topic.keyword: topic.frequency for topic in topics_data.top_topics}
            
            # 确定样式
            style_name = 'ranking'  # 默认使用排行榜样式
            if '简约' in intent.original_message or '优雅' in intent.original_message:
                style_name = 'elegant'
            elif '现代' in intent.original_message or '科技' in intent.original_message:
                style_name = 'modern'
            elif '游戏' in intent.original_message or '竞技' in intent.original_message:
                style_name = 'gaming'
            
            # 使用高级词云生成器
            if self.advanced_wordcloud_generator:
                # 检查是否需要生成对比词云
                if '对比' in intent.original_message or '变化' in intent.original_message or '趋势' in intent.original_message:
                    # 生成对比词云
                    comparison_result = await self.db_manager.compare_wordcloud_history(
                        group_id=group_id,
                        current_data=word_freq,
                        days_back=7
                    )
                    
                    if comparison_result.get('comparison_available', False):
                        yield event.plain_result("🔍 正在生成对比词云...")
                        
                        # 重构历史数据
                        from datetime import datetime, timedelta
                        historical_date = datetime.now() - timedelta(days=7)
                        historical_topics = await self.db_manager.get_topics_analysis(
                            group_id, 'week'
                        )
                        
                        if historical_topics and historical_topics.top_topics:
                            historical_word_freq = {
                                topic.keyword: topic.frequency 
                                for topic in historical_topics.top_topics
                            }
                            
                            comparison_path = await self.advanced_wordcloud_generator.generate_comparison_wordcloud(
                                current_data=word_freq,
                                historical_data=historical_word_freq,
                                group_id=group_id,
                                style_name=style_name,
                                comparison_days=7
                            )
                            
                            if comparison_path:
                                yield event.image_result(comparison_path)
                                
                                # 生成对比报告
                                changes = comparison_result
                                report = f"""📈 **7天词云对比报告**

🎆 **新增热词**: {', '.join(changes.get('new_words', [])[:5]) or '无'}
📉 **上升词汇**: {', '.join([f"{w}(+{c})" for w, c in changes.get('rising_words', [])[:3]]) or '无'}
📊 **下降词汇**: {', '.join([f"{w}(-{abs(c)})" for w, c in changes.get('falling_words', [])[:3]]) or '无'}
📌 **消失词汇**: {', '.join(changes.get('disappeared_words', [])[:5]) or '无'}

📊 **整体变化**: 词汇数量 {changes.get('word_growth', 0):+d}"""
                                
                                yield event.plain_result(report)
                            else:
                                yield event.plain_result("❓ 对比词云生成失败，生成普通词云...")
                        else:
                            yield event.plain_result("❓ 历史数据不足，生成普通词云...")
                    else:
                        yield event.plain_result("💬 暂无历史数据可对比，生成普通词云...")
                
                # 生成普通排行榜词云
                wordcloud_path = await self.advanced_wordcloud_generator.generate_ranking_wordcloud(
                    word_data=word_freq,
                    group_id=group_id,
                    style_name=style_name,
                    title=f"🏆 群聊热词排行榜",
                    metadata={
                        'total_words': len(word_freq),
                        'time_range': intent.time_range.value if intent.time_range else '全部',
                        'analysis_depth': '深度分析'
                    }
                )
                
                if wordcloud_path:
                    # 保存到历史记录
                    await self.db_manager.save_wordcloud_history(
                        group_id=group_id,
                        time_range=intent.time_range.value if intent.time_range else 'all',
                        word_data=word_freq,
                        style_name=style_name,
                        file_path=wordcloud_path,
                        metadata={
                            'generation_method': 'advanced_ranking',
                            'natural_language_trigger': intent.original_message,
                            'confidence': intent.confidence
                        }
                    )
                    
                    yield event.image_result(wordcloud_path)
                    yield event.plain_result(f"✨ 高级词云生成完成！样式：{style_name}")
                else:
                    # 降级到原始词云
                    async for result in self.generate_wordcloud_chart(event):
                        yield result
            else:
                # 降级到原始词云功能
                async for result in self.generate_wordcloud_chart(event):
                    yield result
                
        except Exception as e:
            logger.error(f"词云命令处理失败: {e}")
            yield event.plain_result("词云生成过程中出现错误")
    
    async def _handle_stats_nl_command(self, event: AstrMessageEvent, intent: CommandIntent):
        """处理统计相关自然语言命令"""
        yield event.plain_result("📊 明白了！让我为您查看数据...")
        # 调用现有的快速统计功能
        async for result in self.quick_stats(event):
            yield result
    
    async def _handle_help_nl_command(self, event: AstrMessageEvent, intent: CommandIntent):
        """处理帮助相关自然语言命令"""
        help_text = """🤖 智能数据分析师 - 自然语言支持

🎯 **直接说话就能用！**
• "今日词云" → 生成今天的词云图
• "大家都在聊什么" → 看看群里最热门话题
• "看看数据" → 查看群组统计
• "群里怎么样" → 分析群组活跃度
• "我的画像" → 生成个人性格分析
• "分析一下我" → 深度分析你的特征

💡 **支持的表达方式：**
• 🎨 词云：词云、热词、大家聊什么、话题分析、今天聊什么
• 📊 统计：数据、统计、活跃度、发言情况、群里怎么样
• 👤 画像：我的画像、分析我、性格分析、我是什么性格
• ❓ 帮助：有什么功能、怎么用、能做什么

🎨 **词云样式：**
• "好看的词云" → 精美样式
• "简约词云" → 优雅风格
• "现代词云" → 科技风格

📋 **传统命令：**
• /stats - 快速统计
• /chart wordcloud - 词云图
• /portrait - 用户画像
• /help_data - 完整帮助"""
        
        yield event.plain_result(help_text)
    
    # ==================== Phase 3 新增功能：用户画像系统 ====================
    
    @filter.command("portrait")
    async def generate_user_portrait(self, event: AstrMessageEvent):
        """
        生成用户画像命令
        
        用法:
        /portrait - 生成自己的画像
        /portrait @username - 生成指定用户的画像
        /portrait deep - 生成深度分析画像
        """
        try:
            group_id = event.get_group_id()
            if not group_id:
                yield event.plain_result("用户画像功能仅在群聊中使用")
                return
            
            # 检查组件初始化
            if not self.portrait_analyzer or not self.portrait_visualizer:
                yield event.plain_result("用户画像功能尚未初始化，请稍后重试")
                return
            
            # 解析命令参数
            message_parts = event.message_str.strip().split()
            target_user_id = str(event.get_sender_id())  # 默认分析自己
            analysis_depth = AnalysisDepth.NORMAL
            
            # 检查是否指定了其他用户或分析深度
            for part in message_parts[1:]:  # 跳过命令本身
                if part == "deep":
                    analysis_depth = AnalysisDepth.DEEP
                elif part == "light":
                    analysis_depth = AnalysisDepth.LIGHT
                elif part.startswith("@"):
                    # 提取用户ID（实际实现可能需要根据具体平台调整）
                    target_user_id = part[1:]
            
            yield event.plain_result("🧠 正在生成用户画像，请稍候...")
            
            # 生成用户画像
            portrait = await self.portrait_analyzer.generate_user_portrait(
                user_id=target_user_id,
                group_id=group_id,
                analysis_depth=analysis_depth,
                days_back=30
            )
            
            if not portrait:
                yield event.plain_result("❌ 用户数据不足或分析失败，请确保用户在群内有足够的发言记录")
                return
            
            # 生成可视化卡片
            card_path = await self.portrait_visualizer.generate_portrait_card(
                portrait=portrait,
                style='modern',
                include_charts=True
            )
            
            if card_path:
                # 发送画像卡片
                yield event.image_result(card_path)
                
                # 发送文字摘要
                summary = portrait.to_summary_text()
                yield event.plain_result(summary)
                
                logger.info(f"用户画像生成成功: {target_user_id}")
            else:
                # 降级：只发送文字分析
                summary = portrait.to_summary_text()
                yield event.plain_result(f"📊 用户画像分析\n\n{summary}")
                
        except Exception as e:
            logger.error(f"用户画像生成失败: {e}")
            yield event.plain_result("用户画像生成过程中出现错误，请稍后重试")
    
    @filter.command("compare")
    async def compare_users(self, event: AstrMessageEvent):
        """
        用户对比命令
        
        用法:
        /compare @user1 @user2 - 对比两个用户
        /compare @user - 与自己对比
        """
        try:
            group_id = event.get_group_id()
            if not group_id:
                yield event.plain_result("用户对比功能仅在群聊中使用")
                return
            
            # 检查组件初始化
            if not self.portrait_analyzer or not self.portrait_visualizer:
                yield event.plain_result("用户画像功能尚未初始化，请稍后重试")
                return
            
            # 解析命令参数
            message_parts = event.message_str.strip().split()
            user_mentions = [part[1:] for part in message_parts if part.startswith("@")]
            
            if len(user_mentions) == 0:
                yield event.plain_result("请指定要对比的用户，例如：/compare @user1 @user2")
                return
            elif len(user_mentions) == 1:
                # 与自己对比
                user1_id = str(event.get_sender_id())
                user2_id = user_mentions[0]
            elif len(user_mentions) >= 2:
                # 对比两个指定用户
                user1_id = user_mentions[0]
                user2_id = user_mentions[1]
            
            yield event.plain_result("📊 正在生成用户对比分析，请稍候...")
            
            # 生成对比分析
            comparison_result = await self.portrait_analyzer.compare_users(
                user1_id=user1_id,
                user2_id=user2_id,
                group_id=group_id,
                days_back=30
            )
            
            if not comparison_result:
                yield event.plain_result("❌ 用户数据不足或对比分析失败")
                return
            
            # 生成对比图表
            portrait1 = comparison_result['user1']
            portrait2 = comparison_result['user2']
            
            # 重新构造 UserPortrait 对象（从字典）
            from .portrait_analyzer import UserPortrait
            from datetime import datetime
            
            p1 = UserPortrait(**portrait1)
            p2 = UserPortrait(**portrait2)
            
            comparison_chart = await self.portrait_visualizer.generate_comparison_chart(
                portrait1=p1,
                portrait2=p2,
                style='modern'
            )
            
            if comparison_chart:
                yield event.image_result(comparison_chart)
            
            # 发送对比摘要
            summary = comparison_result['comparison_summary']
            similarity = comparison_result['similarity_score']
            differences = comparison_result['differences']
            
            comparison_text = f"""👥 **用户对比分析结果**

📊 **相似度**: {similarity:.1%}

🔍 **对比摘要**:
{summary}

🎯 **主要差异**:
{chr(10).join(['• ' + diff for diff in differences]) if differences else '• 两位用户特征相似'}

💡 **分析建议**: 相似度 {'较高' if similarity > 0.6 else '中等' if similarity > 0.3 else '较低'}，{'可以' if similarity > 0.5 else '建议'} 进行更深入的交流"""
            
            yield event.plain_result(comparison_text)
            
        except Exception as e:
            logger.error(f"用户对比失败: {e}")
            yield event.plain_result("用户对比过程中出现错误，请稍后重试")
    
    async def _handle_portrait_nl_command(self, event: AstrMessageEvent, intent: CommandIntent):
        """处理用户画像相关的自然语言命令"""
        try:
            group_id = event.get_group_id()
            if not group_id:
                yield event.plain_result("用户画像功能仅在群聊中使用")
                return
            
            yield event.plain_result("🧠 明白了！正在分析用户画像...")
            
            # 检查是否指定了目标用户
            target_user_id = intent.target_user or str(event.get_sender_id())
            
            # 确定分析深度
            analysis_depth = AnalysisDepth.NORMAL
            if '深度' in intent.original_message or '详细' in intent.original_message:
                analysis_depth = AnalysisDepth.DEEP
            elif '简单' in intent.original_message or '快速' in intent.original_message:
                analysis_depth = AnalysisDepth.LIGHT
            
            # 生成用户画像
            if self.portrait_analyzer and self.portrait_visualizer:
                portrait = await self.portrait_analyzer.generate_user_portrait(
                    user_id=target_user_id,
                    group_id=group_id,
                    analysis_depth=analysis_depth,
                    days_back=30
                )
                
                if portrait:
                    # 生成摘要卡片（更适合自然语言触发）
                    card_path = await self.portrait_visualizer.generate_summary_card(
                        portrait=portrait,
                        style='elegant'
                    )
                    
                    if card_path:
                        yield event.image_result(card_path)
                    
                    # 发送关键信息
                    key_info = f"""✨ **画像分析完成**

👤 {portrait.nickname} 的关键特征：
• 🎯 交流风格：{portrait.communication_style}
• 📊 活跃程度：{portrait.message_count} 条消息
• 🕒 主要活跃：{', '.join([f'{h}:00' for h in portrait.peak_hours[:2]])}"""
                    
                    if portrait.personality_tags:
                        key_info += f"\n• 🏷️ 性格特质：{' • '.join(portrait.personality_tags[:3])}"
                    
                    yield event.plain_result(key_info)
                else:
                    yield event.plain_result("❌ 数据不足，无法生成用户画像")
            else:
                yield event.plain_result("❌ 用户画像功能尚未就绪")
                
        except Exception as e:
            logger.error(f"画像自然语言命令处理失败: {e}")
            yield event.plain_result("用户画像分析过程中出现错误")

    async def terminate(self):
        """
        /// 插件终止时的清理工作
        /// 关闭数据库连接，取消后台任务
        """
        try:
            if self.db_manager:
                await self.db_manager.close()
            
            # 清理高级词云临时文件
            if self.advanced_wordcloud_generator:
                await self.advanced_wordcloud_generator.cleanup_old_wordclouds()
            
            logger.info("数据分析师插件已卸载")
        except Exception as e:
            logger.error(f"插件卸载错误: {e}")