"""
数据分析师插件 - 图表生成模块

提供各种数据可视化图表的生成功能
"""

import os
import time
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 可视化库
import matplotlib
matplotlib.use('Agg')  # 使用非GUI后端
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import seaborn as sns

# 词云生成
from wordcloud import WordCloud

from astrbot.api import logger
from .models import (
    ActivityAnalysisData, TopicsAnalysisData, 
    ChartConstants as CC, PluginConfig
)
from .font_manager import FontManager


class ChartGenerator:
    """
    /// 图表生成器
    /// 负责创建各种数据可视化图表
    /// 支持活跃度图表、词云图、排行榜等多种图表类型
    """
    
    def __init__(self, charts_dir: Path, config: PluginConfig, font_manager: FontManager = None):
        """
        /// 初始化图表生成器
        /// @param charts_dir: 图表保存目录
        /// @param config: 插件配置
        /// @param font_manager: 字体管理器实例
        """
        self.charts_dir = charts_dir
        self.config = config
        self.charts_dir.mkdir(exist_ok=True)
        
        # 初始化字体管理器
        self.font_manager = font_manager or FontManager(charts_dir.parent)
        
        # 设置matplotlib参数
        self._setup_matplotlib()
        
        logger.info(f"图表生成器已初始化: {charts_dir}")
    
    def _setup_matplotlib(self):
        """
        /// 配置matplotlib参数
        /// 设置中文字体、样式和默认参数
        """
        try:
            # 🔥 超级强力字体配置
            self.font_manager.configure_matplotlib()
            
            # 🔥 图表专用字体强化
            self._force_chinese_font_for_charts()
            
            logger.info("🎨 图表字体管理器配置完成（超级强化）")
            
            # 设置现代化图表样式
            self._apply_modern_style()
            
            # 设置默认参数
            plt.rcParams.update({
                'figure.dpi': self.config.chart_dpi,
                'figure.figsize': CC.DEFAULT_FIGURE_SIZE,
                'font.size': CC.DEFAULT_FONT_SIZE,
                'savefig.bbox': 'tight',
                'savefig.dpi': self.config.chart_dpi,
                'savefig.facecolor': 'white',
                'savefig.edgecolor': 'none',
                # 现代化样式参数
                'axes.spines.top': False,
                'axes.spines.right': False,
                'axes.grid': True,
                'axes.grid.alpha': 0.3,
                'grid.linewidth': 0.5,
                'axes.edgecolor': '#cccccc',
                'axes.linewidth': 0.8,
                'xtick.direction': 'out',
                'ytick.direction': 'out',
                'xtick.major.size': 4,
                'ytick.major.size': 4,
                # 🔧 重要：确保中文字体和负号显示
                'axes.unicode_minus': False,
                'font.family': 'sans-serif'
            })
            
            logger.info("matplotlib现代化配置完成")
            
        except Exception as e:
            logger.error(f"matplotlib配置失败: {e}")
    
    def _force_chinese_font_for_charts(self):
        """图表专用：强制中文字体配置"""
        try:
            import matplotlib.font_manager as fm
            
            # 🔥 寻找系统中文字体
            system_fonts = [f.name for f in fm.fontManager.ttflist]
            
            # 优先级字体列表
            priority_fonts = [
                'Microsoft YaHei', 'Microsoft YaHei UI', 'SimHei', 'SimSun', 'KaiTi',
                'PingFang SC', 'Heiti SC', 'STHeiti Light',
                'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'Noto Sans CJK SC'
            ]
            
            # 找到第一个可用的中文字体
            chinese_font = None
            for font in priority_fonts:
                if font in system_fonts:
                    chinese_font = font
                    logger.info(f"🎯 图表检测到中文字体: {font}")
                    break
            
            if chinese_font:
                # 🔥 超级强力设置
                font_list = [chinese_font, 'Microsoft YaHei', 'SimHei', 'DejaVu Sans']
                plt.rcParams['font.sans-serif'] = font_list
                plt.rcParams['font.serif'] = font_list
                plt.rcParams['font.monospace'] = font_list
                plt.rcParams['font.cursive'] = font_list
                plt.rcParams['font.fantasy'] = font_list
                plt.rcParams['font.family'] = 'sans-serif'
                
                # 🔥 强制所有文本使用中文字体
                plt.rcParams['axes.unicode_minus'] = False
                plt.rcParams['font.weight'] = 'normal'
                
                logger.info(f"🔥 图表强制字体配置: {chinese_font}")
            else:
                logger.warning("⚠️ 未找到系统中文字体，图表可能显示方格")
                
                # 🔥 降级方案：使用 Unicode 字体
                unicode_fonts = ['Arial Unicode MS', 'Lucida Grande', 'DejaVu Sans']
                plt.rcParams['font.sans-serif'] = unicode_fonts + plt.rcParams['font.sans-serif']
                logger.info("📝 使用 Unicode 字体降级方案")
                
        except Exception as e:
            logger.error(f"图表字体强制配置失败: {e}")
    
    def _apply_modern_style(self):
        """应用现代化图表样式"""
        try:
            # 尝试使用seaborn现代样式
            if hasattr(plt.style, 'library') and 'seaborn-v0_8' in plt.style.library:
                plt.style.use('seaborn-v0_8')
            elif 'seaborn' in str(plt.style.available):
                plt.style.use('seaborn')
            else:
                # 使用自定义现代样式
                plt.style.use('default')
                
        except Exception as e:
            logger.warning(f"样式设置失败: {e}，使用默认样式")
            plt.style.use('default')
    
    async def generate_activity_trend_chart(self, data: ActivityAnalysisData, group_id: str) -> Optional[str]:
        """
        /// 生成活跃度趋势图表
        /// @param data: 活跃度分析数据
        /// @param group_id: 群组ID
        /// @return: 图表文件路径
        """
        try:
            if not data.daily_data:
                return None
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # 处理数据
            dates = [datetime.strptime(row[0], '%Y-%m-%d') for row in data.daily_data]
            counts = [row[1] for row in data.daily_data]
            
            # 获取现代化颜色方案
            colors = self._get_color_palette(3)
            main_color = colors[0]
            gradient_color = colors[1] if len(colors) > 1 else main_color
            
            # 绘制现代化趋势线
            ax.plot(dates, counts, marker='o', linewidth=3, markersize=7, 
                   color=main_color, alpha=0.9, markerfacecolor='white',
                   markeredgewidth=2, markeredgecolor=main_color,
                   linestyle='-', antialiased=True)
            
            # 渐变填充效果
            ax.fill_between(dates, counts, alpha=0.4, 
                          color=main_color, interpolate=True)
            
            # 添加阴影效果
            shadow_offset = max(counts) * 0.02
            ax.fill_between(dates, [c - shadow_offset for c in counts], 
                          alpha=0.1, color='gray')
            
            # 添加美化的平均线
            avg_count = np.mean(counts)
            ax.axhline(y=avg_count, color='#ff6b6b', linestyle='--', alpha=0.8, 
                      linewidth=2, label=f'平均值: {avg_count:.1f}')
            
            # 添加趋势线
            if len(dates) > 2:
                z = np.polyfit(range(len(counts)), counts, 1)
                trend_line = np.poly1d(z)
                ax.plot(dates, trend_line(range(len(counts))), 
                       color='orange', linestyle=':', alpha=0.7, linewidth=2,
                       label=f'趋势: {"+" if z[0] > 0 else ""}{z[0]:.1f}/天')
            
            # 现代化标题和标签
            title = f'📈 群组活跃度趋势分析'
            subtitle = f'总消息数: {data.total_messages:,} | 活跃用户: {data.active_users} | 增长率: {data.growth_rate:+.1f}%'
            
            ax.set_title(title, fontsize=CC.TITLE_FONT_SIZE + 2, fontweight='bold', 
                        pad=25, color='#2c3e50')
            ax.text(0.5, 0.95, subtitle, transform=ax.transAxes, 
                   fontsize=CC.LABEL_FONT_SIZE, ha='center', va='top',
                   color='#7f8c8d', style='italic')
            
            ax.set_xlabel('日期', fontsize=CC.LABEL_FONT_SIZE, 
                         fontweight='medium', color='#34495e')
            ax.set_ylabel('消息数量', fontsize=CC.LABEL_FONT_SIZE, 
                         fontweight='medium', color='#34495e')
            
            # 格式化x轴
            self._format_date_axis(ax, dates)
            
            # 现代化网格和图例
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5, color='#ecf0f1')
            ax.set_axisbelow(True)
            
            # 美化图例
            legend = ax.legend(loc='upper left', frameon=True, shadow=True, 
                             fancybox=True, framealpha=0.9)
            legend.get_frame().set_facecolor('#f8f9fa')
            legend.get_frame().set_edgecolor('#dee2e6')
            
            # 现代化数据标注
            if counts:
                max_idx = np.argmax(counts)
                min_idx = np.argmin(counts)
                
                # 最高点标注
                ax.annotate(f'🔥 最高: {counts[max_idx]}', 
                           xy=(dates[max_idx], counts[max_idx]),
                           xytext=(10, 15), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', facecolor='#ff6b6b', 
                                   alpha=0.8, edgecolor='white', linewidth=2),
                           arrowprops=dict(arrowstyle='->', color='#ff6b6b', lw=2,
                                         connectionstyle='arc3,rad=0.1'),
                           fontsize=10, fontweight='bold', color='white')
                
                # 最低点标注（如果差异显著）
                if counts[max_idx] - counts[min_idx] > np.mean(counts) * 0.3:
                    ax.annotate(f'📉 最低: {counts[min_idx]}', 
                               xy=(dates[min_idx], counts[min_idx]),
                               xytext=(10, -15), textcoords='offset points',
                               bbox=dict(boxstyle='round,pad=0.5', facecolor='#74b9ff', 
                                       alpha=0.8, edgecolor='white', linewidth=2),
                               arrowprops=dict(arrowstyle='->', color='#74b9ff', lw=2,
                                             connectionstyle='arc3,rad=-0.1'),
                               fontsize=10, fontweight='bold', color='white')
            
            # 美化布局并保存
            plt.tight_layout()
            
            # 添加背景色和边框
            fig.patch.set_facecolor('#ffffff')
            ax.set_facecolor('#fdfdfd')
            
            filepath = self._save_chart(fig, CC.ACTIVITY_CHART_TEMPLATE, group_id)
            plt.close(fig)
            
            return filepath
            
        except Exception as e:
            logger.error(f"活跃度趋势图生成失败: {e}")
            return None
    
    async def generate_topics_wordcloud(self, data: TopicsAnalysisData, group_id: str) -> Optional[str]:
        """
        /// 生成话题词云图
        /// @param data: 话题分析数据
        /// @param group_id: 群组ID
        /// @return: 词云图片路径
        """
        try:
            if not data.top_topics:
                return None
            
            # 构建词频字典
            word_freq = {topic['keyword']: topic['frequency'] for topic in data.top_topics}
            
            # 生成词云
            wordcloud = WordCloud(
                width=CC.WORDCLOUD_SIZE[0], 
                height=CC.WORDCLOUD_SIZE[1],
                background_color='#fafafa',  # 温暖的背景色
                font_path=self._get_chinese_font_path(),
                max_words=min(120, len(word_freq)),  # 增加更多词数
                colormap='plasma',      # 使用现代化颜色映射
                relative_scaling=0.7,   # 优化字体大小比例
                min_font_size=14,       # 更大的最小字体
                max_font_size=140,      # 更大的最大字体
                collocations=False,     # 避免重复组合
                prefer_horizontal=0.75, # 水平文字偏好
                margin=15,              # 更大边距
                random_state=42         # 固定随机种子
            ).generate_from_frequencies(word_freq)
            
            # 现代化图表布局
            fig, ax = plt.subplots(figsize=(16, 10))  # 更大尺寸以展示更多细节
            
            # 添加精美背景和词云显示
            ax.imshow(wordcloud, interpolation='bilinear', alpha=0.95)
            ax.axis('off')
            
            # 超现代化标题设计
            from datetime import datetime
            title = f'🎆 话题热度词云精彩展示'
            subtitle = f'📊 共 {len(data.top_topics)} 个热门话题 | 💬 讨论深度: {data.discussion_depth:.1f} 次/话题 | 🔥 实时更新'
            
            # 渐变标题效果
            ax.text(0.5, 0.97, title, transform=ax.transAxes, 
                   fontsize=CC.TITLE_FONT_SIZE + 6, fontweight='bold', 
                   ha='center', va='top', color='#2c3e50',
                   bbox=dict(boxstyle='round,pad=0.8', facecolor='white', 
                           edgecolor='#3498db', linewidth=2, alpha=0.9))
            
            ax.text(0.5, 0.92, subtitle, transform=ax.transAxes, 
                   fontsize=CC.LABEL_FONT_SIZE + 1, ha='center', va='top',
                   color='#5d6d7e', style='italic', weight='medium')
            
            # 添加水印
            ax.text(0.99, 0.01, f'🤖 AstrBot 数据分析师 | {datetime.now().strftime("%Y-%m-%d %H:%M")}', 
                   transform=ax.transAxes, fontsize=8, ha='right', va='bottom',
                   alpha=0.6, color='#95a5a6', style='italic')
            
            # 精美背景设置
            fig.patch.set_facecolor('#f8f9fa')
            for spine in ax.spines.values():
                spine.set_visible(False)
            
            # 保存图片
            filepath = self._save_chart(fig, CC.WORDCLOUD_TEMPLATE, group_id)
            plt.close(fig)
            
            return filepath
            
        except Exception as e:
            logger.error(f"词云生成失败: {e}")
            return None
    
    async def generate_user_ranking_chart(self, users_data: List[Dict], group_id: str) -> Optional[str]:
        """
        /// 生成用户排行榜图表
        /// @param users_data: 用户数据列表
        /// @param group_id: 群组ID
        /// @return: 图表文件路径
        """
        try:
            if not users_data:
                return None
            
            # 限制显示数量
            display_count = min(self.config.max_chart_items, len(users_data))
            top_users = users_data[:display_count]
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 8))
            
            # 准备数据
            usernames = [user.get('username', f"用户{i+1}") for i, user in enumerate(top_users)]
            message_counts = [user.get('message_count', 0) for user in top_users]
            word_counts = [user.get('word_count', 0) for user in top_users]
            
            # 获取现代化颜色方案
            colors = self._get_color_palette(len(usernames))
            
            # 左图：消息数量排行 - 现代化设计
            bars1 = ax1.barh(range(len(usernames)), message_counts, 
                           color=colors, alpha=0.8, height=0.7,
                           edgecolor='white', linewidth=2)
            
            # 添加渐变效果
            for i, (bar, color) in enumerate(zip(bars1, colors)):
                # 为排名前三的用户添加特殊效果
                if i < 3:
                    bar.set_edgecolor('#ffd700' if i == 0 else '#c0c0c0' if i == 1 else '#cd7f32')
                    bar.set_linewidth(3)
            
            # 🔧 关键修复：用户名显示（强制使用中文字体）
            ax1.set_yticks(range(len(usernames)))
            ax1.set_yticklabels(usernames, fontsize=CC.DEFAULT_FONT_SIZE, fontfamily='sans-serif')
            ax1.set_xlabel('💬 消息数量', fontsize=CC.LABEL_FONT_SIZE, fontweight='medium', fontfamily='sans-serif')
            ax1.set_title('🏆 消息数量排行榜', fontweight='bold', 
                         fontsize=CC.TITLE_FONT_SIZE, color='#2c3e50', fontfamily='sans-serif')
            
            # 🔧 额外确保：为每个用户名标签设置正确字体
            for tick in ax1.get_yticklabels():
                tick.set_fontfamily('sans-serif')
            ax1.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
            ax1.set_axisbelow(True)
            
            # 现代化数值标签
            for i, (bar, count) in enumerate(zip(bars1, message_counts)):
                # 添加排名徽章
                rank_badge = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}"
                
                ax1.text(count + max(message_counts) * 0.02, i, 
                        f"{rank_badge} {count:,}", 
                        va='center', fontsize=10, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                alpha=0.8, edgecolor=colors[i], linewidth=1))
            
            # 右图：字数排行 - 现代化设计
            # 使用不同的颜色方案区分两个排行榜
            word_colors = self._get_color_palette(len(usernames), 'sunset')
            bars2 = ax2.barh(range(len(usernames)), word_counts, 
                           color=word_colors, alpha=0.8, height=0.7,
                           edgecolor='white', linewidth=2)
            
            # 添加渐变效果
            for i, (bar, color) in enumerate(zip(bars2, word_colors)):
                if i < 3:
                    bar.set_edgecolor('#ffd700' if i == 0 else '#c0c0c0' if i == 1 else '#cd7f32')
                    bar.set_linewidth(3)
            
            # 🔧 关键修复：用户名显示（强制使用中文字体）
            ax2.set_yticks(range(len(usernames)))
            ax2.set_yticklabels(usernames, fontsize=CC.DEFAULT_FONT_SIZE, fontfamily='sans-serif')
            ax2.set_xlabel('📝 总字数', fontsize=CC.LABEL_FONT_SIZE, fontweight='medium', fontfamily='sans-serif')
            ax2.set_title('📊 发言字数排行榜', fontweight='bold', 
                         fontsize=CC.TITLE_FONT_SIZE, color='#2c3e50', fontfamily='sans-serif')
            
            # 🔧 额外确保：为每个用户名标签设置正确字体
            for tick in ax2.get_yticklabels():
                tick.set_fontfamily('sans-serif')
            ax2.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
            ax2.set_axisbelow(True)
            
            # 现代化数值标签
            for i, (bar, count) in enumerate(zip(bars2, word_counts)):
                rank_badge = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}"
                
                ax2.text(count + max(word_counts) * 0.02, i, 
                        f"{rank_badge} {count:,}", 
                        va='center', fontsize=10, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                alpha=0.8, edgecolor=word_colors[i], linewidth=1))
            
            # 反转y轴显示顺序（第一名在顶部）
            ax1.invert_yaxis()
            ax2.invert_yaxis()
            
            # 现代化总标题和布局（强制使用中文字体）
            fig.suptitle(f'📈 用户活跃度排行榜 (Top {display_count})', 
                        fontsize=18, fontweight='bold', color='#2c3e50', y=0.98, fontfamily='sans-serif')
            
            # 美化背景
            fig.patch.set_facecolor('#ffffff')
            ax1.set_facecolor('#fdfdfd')
            ax2.set_facecolor('#fdfdfd')
            
            plt.tight_layout()
            plt.subplots_adjust(top=0.9)
            
            # 保存图表
            filepath = self._save_chart(fig, CC.RANKING_CHART_TEMPLATE, group_id)
            plt.close(fig)
            
            return filepath
            
        except Exception as e:
            logger.error(f"用户排行榜生成失败: {e}")
            return None
    
    async def generate_activity_heatmap(self, heatmap_data: Dict, group_id: str) -> Optional[str]:
        """
        /// 生成活跃时段热力图
        /// @param heatmap_data: 热力图数据
        /// @param group_id: 群组ID
        /// @return: 图表文件路径
        """
        try:
            if not heatmap_data or 'hourly_data' not in heatmap_data:
                return None
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # 处理小时数据
            hourly_data = heatmap_data['hourly_data']
            hours = list(range(24))
            hour_counts = [hourly_data.get(str(h), 0) for h in hours]
            
            # 上图：24小时活跃度柱状图
            colors = plt.cm.viridis(np.linspace(0, 1, 24))
            bars = ax1.bar(hours, hour_counts, color=colors, alpha=0.8)
            
            ax1.set_xlabel('小时')
            ax1.set_ylabel('消息数量')
            ax1.set_title('24小时活跃度分布', fontweight='bold')
            ax1.set_xticks(range(0, 24, 2))
            ax1.grid(axis='y', alpha=0.3)
            
            # 标记峰值时段
            peak_hour = np.argmax(hour_counts)
            ax1.annotate(f'峰值: {peak_hour}:00\n({hour_counts[peak_hour]}条)',
                        xy=(peak_hour, hour_counts[peak_hour]),
                        xytext=(peak_hour, hour_counts[peak_hour] + max(hour_counts) * 0.1),
                        ha='center',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='orange', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='red'))
            
            # 下图：一周活跃度分布（如果有数据）
            if 'weekly_data' in heatmap_data:
                weekly_data = heatmap_data['weekly_data']
                days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
                day_counts = [weekly_data.get(str(i), 0) for i in range(7)]
                
                bars2 = ax2.bar(days, day_counts, color=plt.cm.plasma(np.linspace(0, 1, 7)), alpha=0.8)
                ax2.set_ylabel('消息数量')
                ax2.set_title('一周活跃度分布', fontweight='bold')
                ax2.grid(axis='y', alpha=0.3)
                
                # 添加数值标签
                for bar, count in zip(bars2, day_counts):
                    height = bar.get_height()
                    ax2.text(bar.get_x() + bar.get_width()/2., height + max(day_counts) * 0.01,
                            str(count), ha='center', va='bottom', fontsize=9)
            else:
                # 创建简单的时段分布
                periods = ['凌晨\n(0-6)', '早晨\n(6-12)', '下午\n(12-18)', '晚上\n(18-24)']
                period_counts = [
                    sum(hour_counts[0:6]),
                    sum(hour_counts[6:12]), 
                    sum(hour_counts[12:18]),
                    sum(hour_counts[18:24])
                ]
                
                bars2 = ax2.bar(periods, period_counts, 
                               color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'], alpha=0.8)
                ax2.set_ylabel('消息数量')
                ax2.set_title('时段活跃度分布', fontweight='bold')
                ax2.grid(axis='y', alpha=0.3)
            
            # 美化布局
            plt.tight_layout()
            plt.subplots_adjust(hspace=0.3)
            
            # 设置背景
            fig.patch.set_facecolor('#ffffff')
            ax1.set_facecolor('#fdfdfd')
            ax2.set_facecolor('#fdfdfd')
            
            # 保存图表
            filepath = self._save_chart(fig, CC.HEATMAP_TEMPLATE, group_id)
            plt.close(fig)
            
            return filepath
            
        except Exception as e:
            logger.error(f"热力图生成失败: {e}")
            return None
    
    async def generate_prediction_chart(self, historical_data: List, predictions: List, 
                                      group_id: str, target: str) -> Optional[str]:
        """
        /// 生成预测图表
        /// @param historical_data: 历史数据
        /// @param predictions: 预测数据
        /// @param group_id: 群组ID
        /// @param target: 预测目标
        /// @return: 图表文件路径
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # 历史数据
            hist_x = list(range(len(historical_data)))
            hist_y = historical_data
            
            # 预测数据
            pred_x = list(range(len(historical_data), len(historical_data) + len(predictions)))
            pred_y = predictions
            
            # 绘制历史数据
            ax.plot(hist_x, hist_y, 'o-', color='blue', label='历史数据', linewidth=2)
            
            # 绘制预测数据
            ax.plot(pred_x, pred_y, 's--', color='red', label='预测数据', linewidth=2, alpha=0.8)
            
            # 连接线
            if hist_y and pred_y:
                ax.plot([hist_x[-1], pred_x[0]], [hist_y[-1], pred_y[0]], 
                       '--', color='gray', alpha=0.5)
            
            # 添加置信区间（简单示例）
            if len(pred_y) > 1:
                std_dev = np.std(hist_y) if hist_y else 0
                upper_bound = [p + std_dev for p in pred_y]
                lower_bound = [max(0, p - std_dev) for p in pred_y]
                ax.fill_between(pred_x, lower_bound, upper_bound, alpha=0.2, color='red')
            
            # 设置标签和标题
            ax.set_xlabel('时间（天）')
            ax.set_ylabel('数值')
            ax.set_title(f'{target}预测分析', fontsize=CC.TITLE_FONT_SIZE, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # 添加分界线
            if hist_x:
                ax.axvline(x=hist_x[-1], color='green', linestyle=':', alpha=0.7, label='预测起点')
            
            plt.tight_layout()
            
            # 保存图表
            timestamp = int(time.time())
            filename = f"prediction_{target}_{group_id}_{timestamp}.png"
            filepath = self.charts_dir / filename
            
            plt.savefig(filepath, dpi=self.config.chart_dpi, bbox_inches='tight')
            plt.close(fig)
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"预测图表生成失败: {e}")
            return None
    
    def _format_date_axis(self, ax, dates: List[datetime]):
        """格式化日期轴"""
        try:
            date_range = (max(dates) - min(dates)).days
            
            if date_range <= 7:
                # 一周内：显示每天
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator())
            elif date_range <= 30:
                # 一个月内：每3天显示一次
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
            else:
                # 超过一个月：每周显示一次
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.xaxis.set_major_locator(mdates.WeekdayLocator())
            
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
        except Exception as e:
            logger.warning(f"日期轴格式化失败: {e}")
    
    def _get_color_palette(self, n_colors: int = 10, palette_type: str = None) -> List[str]:
        """获取现代化颜色方案"""
        try:
            # 如果指定了palette_type，优先使用
            if palette_type and palette_type in CC.COLOR_PALETTES:
                target_palette = palette_type
            else:
                target_palette = self.config.color_palette
            
            # 检查是否为自定义现代化调色板
            if target_palette in CC.COLOR_PALETTES and isinstance(CC.COLOR_PALETTES[target_palette], list):
                colors = CC.COLOR_PALETTES[target_palette]
                # 如果颜色数量不够，循环使用
                while len(colors) < n_colors:
                    colors.extend(colors[:n_colors - len(colors)])
                return colors[:n_colors]
            
            # 使用seaborn调色板
            elif target_palette in CC.COLOR_PALETTES:
                return sns.color_palette(target_palette, n_colors).as_hex()
            
            # 默认使用现代蓝色调色板
            else:
                return CC.COLOR_PALETTES["modern_blue"][:n_colors] if n_colors <= 6 else sns.color_palette("husl", n_colors).as_hex()
                
        except Exception as e:
            logger.warning(f"颜色方案获取失败: {e}")
            # 备用现代化颜色
            return ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#fa709a', '#fee140'][:n_colors]
    
    def _get_chinese_font_path(self) -> Optional[str]:
        """获取中文字体路径（优化版）"""
        return self.font_manager._get_chinese_font_path()
    
    def _save_chart(self, fig, template: str, group_id: str) -> str:
        """
        /// 保存图表到文件
        /// @param fig: matplotlib图形对象
        /// @param template: 文件名模板
        /// @param group_id: 群组ID
        /// @return: 保存的文件路径
        """
        timestamp = int(time.time())
        filename = template.format(group_id=group_id, timestamp=timestamp)
        filepath = self.charts_dir / filename
        
        plt.savefig(filepath, dpi=self.config.chart_dpi, bbox_inches='tight')
        
        return str(filepath)
    
    async def cleanup_old_charts(self, max_age_hours: int = 24):
        """
        /// 清理旧图表文件
        /// @param max_age_hours: 文件最大保留时间（小时）
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            deleted_count = 0
            for chart_file in self.charts_dir.glob("*.png"):
                file_age = current_time - chart_file.stat().st_mtime
                if file_age > max_age_seconds:
                    chart_file.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"已清理 {deleted_count} 个过期图表文件")
                
        except Exception as e:
            logger.error(f"图表清理失败: {e}")
    
    def get_chart_stats(self) -> Dict[str, Any]:
        """
        /// 获取图表生成统计信息
        /// @return: 统计数据
        """
        try:
            chart_files = list(self.charts_dir.glob("*.png"))
            total_size = sum(f.stat().st_size for f in chart_files)
            
            return {
                'total_charts': len(chart_files),
                'total_size_mb': total_size / (1024 * 1024),
                'charts_dir': str(self.charts_dir),
                'oldest_chart': min((f.stat().st_mtime for f in chart_files), default=0),
                'newest_chart': max((f.stat().st_mtime for f in chart_files), default=0)
            }
        except Exception as e:
            logger.error(f"获取图表统计失败: {e}")
            return {}


class ChartStyleManager:
    """
    /// 图表样式管理器
    /// 管理不同类型图表的样式和主题
    """
    
    @staticmethod
    def get_activity_chart_style() -> Dict[str, Any]:
        """获取活跃度图表样式"""
        return {
            'line_color': '#1f77b4',
            'fill_alpha': 0.3,
            'marker_size': 5,
            'line_width': 2.5,
            'grid_alpha': 0.3
        }
    
    @staticmethod
    def get_ranking_chart_style() -> Dict[str, Any]:
        """获取排行榜图表样式"""
        return {
            'bar_colors': ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#6c5ce7'],
            'bar_alpha': 0.8,
            'text_offset': 0.01,
            'grid_alpha': 0.3
        }
    
    @staticmethod
    def get_heatmap_style() -> Dict[str, Any]:
        """获取热力图样式"""
        return {
            'colormap': 'viridis',
            'alpha': 0.8,
            'annotation_color': 'white',
            'grid_alpha': 0.3
        }
    
    @staticmethod
    def apply_dark_theme():
        """应用深色主题"""
        plt.style.use('dark_background')
        plt.rcParams.update({
            'text.color': 'white',
            'axes.labelcolor': 'white',
            'xtick.color': 'white',
            'ytick.color': 'white',
            'axes.edgecolor': 'white',
            'axes.facecolor': '#2e2e2e',
            'figure.facecolor': '#1e1e1e'
        })
    
    @staticmethod
    def apply_light_theme():
        """应用浅色主题"""
        plt.style.use('default')
        plt.rcParams.update({
            'text.color': 'black',
            'axes.labelcolor': 'black',
            'xtick.color': 'black',
            'ytick.color': 'black',
            'axes.edgecolor': 'black',
            'axes.facecolor': 'white',
            'figure.facecolor': 'white'
        })
