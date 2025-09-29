"""
高级词云生成器 - 专业词云系统

参考 CloudRank 设计理念，提供分层布局、多样化风格的专业词云生成功能
"""

import os
import time
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter
from dataclasses import dataclass

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
from wordcloud import WordCloud
from PIL import Image, ImageDraw, ImageFont
import seaborn as sns

from astrbot.api import logger
from .models import ChartConstants as CC, PluginConfig
from .font_manager import FontManager


@dataclass
class WordCloudStyle:
    """词云样式配置"""
    name: str
    background_color: str
    colormap: str
    layout_type: str  # 'ranking', 'classic', 'circular', 'pyramid'
    special_effects: Dict[str, Any]


class AdvancedWordCloudGenerator:
    """
    高级词云生成器
    
    特色功能：
    - 分层排行榜布局
    - 多样化视觉风格  
    - 历史对比分析
    - 智能中文字体处理
    """
    
    def __init__(self, charts_dir: Path, font_manager: FontManager, config: PluginConfig):
        """
        初始化高级词云生成器
        
        Args:
            charts_dir: 图表保存目录
            font_manager: 字体管理器
            config: 插件配置
        """
        self.charts_dir = charts_dir
        self.font_manager = font_manager
        self.config = config
        
        # 创建词云专用目录
        self.wordcloud_dir = charts_dir / "wordclouds"
        self.wordcloud_dir.mkdir(exist_ok=True)
        
        # 初始化样式库
        self._initialize_styles()
        
        logger.info(f"高级词云生成器已初始化: {self.wordcloud_dir}")
    
    def _initialize_styles(self):
        """初始化词云样式库"""
        self.styles = {
            'ranking': WordCloudStyle(
                name='排行榜风格',
                background_color='#f8f9fa',
                colormap='viridis',
                layout_type='ranking',
                special_effects={
                    'gradient_bg': True,
                    'ranking_badges': True,
                    'tier_separation': True,
                    'podium_effect': True
                }
            ),
            'modern': WordCloudStyle(
                name='现代商务',
                background_color='#1a1a1a',
                colormap='plasma',
                layout_type='classic',
                special_effects={
                    'neon_glow': True,
                    'glass_effect': True,
                    'animated_colors': True
                }
            ),
            'elegant': WordCloudStyle(
                name='优雅简约',
                background_color='#ffffff',
                colormap='cool',
                layout_type='circular',
                special_effects={
                    'soft_shadows': True,
                    'pastel_colors': True,
                    'minimal_design': True
                }
            ),
            'gaming': WordCloudStyle(
                name='游戏竞技',
                background_color='#0d1421',
                colormap='hot',
                layout_type='pyramid',
                special_effects={
                    'electric_effects': True,
                    'rank_levels': True,
                    'battle_theme': True
                }
            ),
            'professional': WordCloudStyle(
                name='专业报告',
                background_color='#fafafa',
                colormap='tab10',
                layout_type='ranking',
                special_effects={
                    'chart_elements': True,
                    'statistical_info': True,
                    'corporate_design': True
                }
            )
        }
    
    async def generate_ranking_wordcloud(
        self, 
        word_data: Dict[str, int], 
        group_id: str,
        style_name: str = 'ranking',
        title: str = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        生成排行榜式分层词云
        
        Args:
            word_data: 词频数据 {word: frequency}
            group_id: 群组ID
            style_name: 样式名称
            title: 自定义标题
            metadata: 元数据信息
            
        Returns:
            生成的图片文件路径
        """
        try:
            if not word_data:
                logger.warning("词频数据为空，无法生成词云")
                return None
            
            style = self.styles.get(style_name, self.styles['ranking'])
            
            # 数据预处理：分层处理
            tier_data = self._create_tier_layout(word_data)
            
            # 创建图表画布
            fig_size = (20, 12) if style.layout_type == 'ranking' else (16, 10)
            fig, ax = plt.subplots(figsize=fig_size)
            
            # 应用样式背景
            self._apply_background_style(fig, ax, style)
            
            # 生成分层词云内容
            if style.layout_type == 'ranking':
                self._generate_ranking_layout(ax, tier_data, style)
            elif style.layout_type == 'pyramid':
                self._generate_pyramid_layout(ax, tier_data, style)
            elif style.layout_type == 'circular':
                self._generate_circular_layout(ax, tier_data, style)
            else:
                self._generate_classic_layout(ax, tier_data, style)
            
            # 添加标题和装饰
            self._add_enhanced_title(ax, title or "🏆 热词排行榜", metadata, style)
            
            # 添加特殊效果
            self._apply_special_effects(fig, ax, style, tier_data)
            
            # 添加统计信息
            self._add_statistics_panel(ax, word_data, metadata)
            
            # 保存图片
            timestamp = int(time.time())
            filename = f"wordcloud_ranking_{group_id}_{style_name}_{timestamp}.png"
            filepath = self.wordcloud_dir / filename
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight', 
                       facecolor=style.background_color, edgecolor='none')
            plt.close(fig)
            
            logger.info(f"排行榜词云生成成功: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"排行榜词云生成失败: {e}")
            return None
    
    def _create_tier_layout(self, word_data: Dict[str, int]) -> Dict[str, List[Tuple[str, int]]]:
        """
        创建分层布局数据
        
        将词频数据按热度分为不同层级：
        - 王者层 (Top 5): 最高频词汇
        - 钻石层 (6-15): 高频词汇  
        - 黄金层 (16-30): 中频词汇
        - 白银层 (31+): 低频词汇
        """
        sorted_words = sorted(word_data.items(), key=lambda x: x[1], reverse=True)
        
        tier_layout = {
            'king': sorted_words[:5],           # 王者层
            'diamond': sorted_words[5:15],      # 钻石层
            'gold': sorted_words[15:30],        # 黄金层
            'silver': sorted_words[30:60]       # 白银层
        }
        
        # 过滤空层级
        tier_layout = {k: v for k, v in tier_layout.items() if v}
        
        logger.debug(f"分层布局创建完成: {[(k, len(v)) for k, v in tier_layout.items()]}")
        return tier_layout
    
    def _generate_ranking_layout(self, ax, tier_data: Dict, style: WordCloudStyle):
        """生成排行榜布局"""
        # 定义层级配置
        tier_configs = {
            'king': {
                'y_range': (0.75, 0.95),
                'font_sizes': (80, 120),
                'colors': ['#FFD700', '#FFA500', '#FF6347'],  # 金色系
                'badge': '👑',
                'glow_intensity': 0.8
            },
            'diamond': {
                'y_range': (0.55, 0.75),
                'font_sizes': (50, 80),
                'colors': ['#87CEEB', '#4682B4', '#1E90FF'],  # 蓝色系
                'badge': '💎',
                'glow_intensity': 0.6
            },
            'gold': {
                'y_range': (0.35, 0.55),
                'font_sizes': (30, 50),
                'colors': ['#DAA520', '#B8860B', '#CD853F'],  # 金属色系
                'badge': '🥇',
                'glow_intensity': 0.4
            },
            'silver': {
                'y_range': (0.15, 0.35),
                'font_sizes': (20, 30),
                'colors': ['#C0C0C0', '#A9A9A9', '#808080'],  # 银色系
                'badge': '🥈',
                'glow_intensity': 0.2
            }
        }
        
        # 绘制分层区域
        for tier_name, tier_words in tier_data.items():
            if tier_name not in tier_configs:
                continue
                
            config = tier_configs[tier_name]
            y_min, y_max = config['y_range']
            
            # 绘制层级背景
            self._draw_tier_background(ax, y_min, y_max, tier_name, config)
            
            # 绘制该层级的词汇
            self._draw_tier_words(ax, tier_words, config, tier_name)
    
    def _draw_tier_background(self, ax, y_min: float, y_max: float, tier_name: str, config: Dict):
        """绘制层级背景区域"""
        # 创建渐变背景
        gradient_colors = config['colors']
        
        # 绘制背景矩形
        rect = FancyBboxPatch(
            (0.05, y_min), 0.9, y_max - y_min,
            boxstyle="round,pad=0.02",
            facecolor=gradient_colors[0],
            alpha=0.1,
            edgecolor=gradient_colors[1],
            linewidth=2
        )
        ax.add_patch(rect)
        
        # 添加层级标识
        badge = config['badge']
        ax.text(0.02, (y_min + y_max) / 2, f"{badge}\n{tier_name.upper()}", 
               fontsize=16, fontweight='bold', ha='left', va='center',
               color=gradient_colors[1], rotation=90)
    
    def _draw_tier_words(self, ax, tier_words: List[Tuple[str, int]], config: Dict, tier_name: str):
        """绘制层级内的词汇"""
        if not tier_words:
            return
            
        y_min, y_max = config['y_range']
        font_min, font_max = config['font_sizes']
        colors = config['colors']
        
        # 计算位置和大小
        max_freq = max(freq for _, freq in tier_words)
        min_freq = min(freq for _, freq in tier_words)
        
        for i, (word, freq) in enumerate(tier_words):
            # 计算字体大小
            if max_freq > min_freq:
                font_size = font_min + (font_max - font_min) * (freq - min_freq) / (max_freq - min_freq)
            else:
                font_size = (font_min + font_max) / 2
            
            # 计算位置
            x_pos = 0.1 + 0.8 * (i + 0.5) / len(tier_words)
            y_pos = y_min + (y_max - y_min) * 0.5
            
            # 选择颜色
            color = colors[i % len(colors)]
            
            # 绘制词汇
            text = ax.text(x_pos, y_pos, word, fontsize=font_size, 
                          ha='center', va='center', color=color, 
                          weight='bold', family=self.font_manager.detect_best_font())
            
            # 添加发光效果
            if config.get('glow_intensity', 0) > 0:
                self._add_glow_effect(ax, text, color, config['glow_intensity'])
            
            # 添加频次标注
            ax.text(x_pos, y_pos - 0.03, f"({freq})", fontsize=font_size*0.4, 
                   ha='center', va='top', color=color, alpha=0.8)
    
    def _add_glow_effect(self, ax, text_obj, color: str, intensity: float):
        """为文字添加发光效果"""
        # 简化版发光效果：添加多层阴影
        x, y = text_obj.get_position()
        content = text_obj.get_text()
        fontsize = text_obj.get_fontsize()
        
        # 创建发光层
        for offset in [3, 2, 1]:
            ax.text(x, y, content, fontsize=fontsize, 
                   ha='center', va='center', color=color,
                   alpha=intensity * 0.3 / offset, weight='bold',
                   path_effects=[plt.patheffects.withStroke(linewidth=offset, foreground=color)])
    
    def _generate_pyramid_layout(self, ax, tier_data: Dict, style: WordCloudStyle):
        """生成金字塔布局"""
        # 金字塔层级从上到下
        levels = ['king', 'diamond', 'gold', 'silver']
        level_heights = [0.15, 0.2, 0.25, 0.3]  # 每层高度比例
        y_start = 0.85  # 从顶部开始
        
        for i, level in enumerate(levels):
            if level not in tier_data:
                continue
                
            words = tier_data[level]
            height = level_heights[i]
            y_pos = y_start - sum(level_heights[:i]) - height/2
            
            # 计算该层宽度（金字塔效果）
            width_ratio = 0.3 + 0.7 * (i + 1) / len(levels)
            
            self._draw_pyramid_level(ax, words, y_pos, height, width_ratio, level)
    
    def _draw_pyramid_level(self, ax, words: List[Tuple[str, int]], y_pos: float, 
                           height: float, width_ratio: float, level: str):
        """绘制金字塔的一层"""
        if not words:
            return
            
        # 层级配色
        level_colors = {
            'king': '#FFD700',
            'diamond': '#00BFFF', 
            'gold': '#DAA520',
            'silver': '#C0C0C0'
        }
        
        base_color = level_colors.get(level, '#666666')
        
        # 在该层内排列词汇
        for i, (word, freq) in enumerate(words):
            x_center = 0.5
            x_spread = width_ratio * 0.4
            
            if len(words) == 1:
                x_pos = x_center
            else:
                x_pos = x_center - x_spread + 2 * x_spread * i / (len(words) - 1)
            
            # 字体大小基于频率和层级
            base_size = 60 - i * 10  # 层级越高，基础字体越大
            font_size = max(20, base_size * (freq / max(f for _, f in words)))
            
            ax.text(x_pos, y_pos, word, fontsize=font_size, 
                   ha='center', va='center', color=base_color,
                   weight='bold', family=self.font_manager.detect_best_font())
    
    def _generate_circular_layout(self, ax, tier_data: Dict, style: WordCloudStyle):
        """生成环形布局"""
        # 同心圆布局
        circles = ['king', 'diamond', 'gold', 'silver']
        radii = [0.15, 0.35, 0.55, 0.75]  # 各环半径
        
        center_x, center_y = 0.5, 0.5
        
        for i, circle in enumerate(circles):
            if circle not in tier_data:
                continue
                
            words = tier_data[circle]
            radius = radii[i]
            
            self._draw_circular_ring(ax, words, center_x, center_y, radius, circle)
    
    def _draw_circular_ring(self, ax, words: List[Tuple[str, int]], 
                           center_x: float, center_y: float, radius: float, level: str):
        """绘制环形圈层"""
        if not words:
            return
            
        num_words = len(words)
        angle_step = 2 * np.pi / num_words
        
        level_colors = {
            'king': '#FFD700',
            'diamond': '#00BFFF',
            'gold': '#DAA520', 
            'silver': '#C0C0C0'
        }
        
        base_color = level_colors.get(level, '#666666')
        
        for i, (word, freq) in enumerate(words):
            angle = i * angle_step
            x_pos = center_x + radius * np.cos(angle)
            y_pos = center_y + radius * np.sin(angle)
            
            # 字体大小
            font_size = 30 + freq / max(f for _, f in words) * 40
            
            # 文字旋转角度
            rotation = np.degrees(angle) if radius > 0.4 else 0
            
            ax.text(x_pos, y_pos, word, fontsize=font_size,
                   ha='center', va='center', color=base_color,
                   rotation=rotation, weight='bold',
                   family=self.font_manager.detect_best_font())
    
    def _generate_classic_layout(self, ax, tier_data: Dict, style: WordCloudStyle):
        """生成经典布局（使用WordCloud库）"""
        # 合并所有层级数据
        all_words = {}
        for tier_words in tier_data.values():
            for word, freq in tier_words:
                all_words[word] = freq
        
        # 生成传统词云
        font_path = self.font_manager._get_chinese_font_path()
        wordcloud = WordCloud(
            width=1600, height=1000,
            background_color=style.background_color,
            font_path=font_path,
            max_words=100,
            colormap=style.colormap,
            relative_scaling=0.8,
            min_font_size=20,
            max_font_size=100,
            collocations=False,
            prefer_horizontal=0.7,
            margin=20,
            random_state=42
        ).generate_from_frequencies(all_words)
        
        ax.imshow(wordcloud, interpolation='bilinear', alpha=0.9)
        ax.axis('off')
    
    def _apply_background_style(self, fig, ax, style: WordCloudStyle):
        """应用背景样式"""
        fig.patch.set_facecolor(style.background_color)
        ax.set_facecolor('transparent')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # 特殊背景效果
        if style.special_effects.get('gradient_bg', False):
            self._add_gradient_background(ax, style)
    
    def _add_gradient_background(self, ax, style: WordCloudStyle):
        """添加渐变背景"""
        # 创建渐变效果
        gradient = np.linspace(0, 1, 256).reshape(256, 1)
        gradient = np.hstack((gradient, gradient))
        
        ax.imshow(gradient, extent=[0, 1, 0, 1], alpha=0.1, 
                 cmap=style.colormap, aspect='auto', zorder=-1)
    
    def _add_enhanced_title(self, ax, title: str, metadata: Dict, style: WordCloudStyle):
        """添加增强型标题"""
        # 主标题
        ax.text(0.5, 0.97, title, fontsize=28, fontweight='bold',
               ha='center', va='top', color='#2c3e50',
               family=self.font_manager.detect_best_font(),
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                        edgecolor='#3498db', linewidth=2, alpha=0.9))
        
        # 副标题
        if metadata:
            subtitle_parts = []
            if 'total_words' in metadata:
                subtitle_parts.append(f"📊 词汇总数: {metadata['total_words']}")
            if 'time_range' in metadata:
                subtitle_parts.append(f"📅 时间范围: {metadata['time_range']}")
            if 'analysis_depth' in metadata:
                subtitle_parts.append(f"🔍 分析深度: {metadata['analysis_depth']}")
            
            if subtitle_parts:
                subtitle = " | ".join(subtitle_parts)
                ax.text(0.5, 0.93, subtitle, fontsize=14, ha='center', va='top',
                       color='#5d6d7e', style='italic', weight='medium')
    
    def _apply_special_effects(self, fig, ax, style: WordCloudStyle, tier_data: Dict):
        """应用特殊视觉效果"""
        effects = style.special_effects
        
        if effects.get('ranking_badges', False):
            self._add_ranking_badges(ax, tier_data)
        
        if effects.get('statistical_info', False):
            self._add_statistical_overlay(ax, tier_data)
    
    def _add_ranking_badges(self, ax, tier_data: Dict):
        """添加排名徽章"""
        badges = {'king': '👑', 'diamond': '💎', 'gold': '🥇', 'silver': '🥈'}
        
        for tier_name, badge in badges.items():
            if tier_name in tier_data and tier_data[tier_name]:
                # 在对应区域添加徽章
                ax.text(0.95, 0.8 - list(badges.keys()).index(tier_name) * 0.15, 
                       f"{badge}\n{tier_name.upper()}", 
                       fontsize=12, ha='right', va='center', 
                       weight='bold', alpha=0.8)
    
    def _add_statistics_panel(self, ax, word_data: Dict[str, int], metadata: Dict):
        """添加统计信息面板"""
        # 统计信息
        total_words = len(word_data)
        total_freq = sum(word_data.values())
        avg_freq = total_freq / total_words if total_words > 0 else 0
        
        stats_text = f"""📊 统计概览
🔤 词汇数量: {total_words:,}
📈 总频次: {total_freq:,}
📊 平均频次: {avg_freq:.1f}
🕐 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}"""
        
        # 在右下角添加统计面板
        ax.text(0.98, 0.02, stats_text, fontsize=10, ha='right', va='bottom',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                        alpha=0.9, edgecolor='#bdc3c7'),
               family='monospace')
    
    def get_available_styles(self) -> Dict[str, str]:
        """获取可用的词云样式"""
        return {name: style.name for name, style in self.styles.items()}
    
    async def generate_comparison_wordcloud(
        self,
        current_data: Dict[str, int],
        historical_data: Dict[str, int],
        group_id: str,
        style_name: str = 'modern',
        comparison_days: int = 7
    ) -> Optional[str]:
        """
        生成对比式词云，突出显示变化趋势
        
        Args:
            current_data: 当前词频数据
            historical_data: 历史词频数据
            group_id: 群组ID
            style_name: 样式名称
            comparison_days: 对比天数
            
        Returns:
            生成的图片文件路径
        """
        try:
            if not current_data or not historical_data:
                logger.warning("对比数据不足，无法生成对比词云")
                return None
            
            # 分析变化
            changes = self._analyze_word_changes(current_data, historical_data)
            
            # 创建对比布局
            fig, (ax_current, ax_historical, ax_changes) = plt.subplots(1, 3, figsize=(24, 8))
            
            # 生成当前词云
            self._create_single_wordcloud(ax_current, current_data, "📈 当前热词", 'plasma')
            
            # 生成历史词云
            self._create_single_wordcloud(ax_historical, historical_data, 
                                        f"📋 {comparison_days}天前热词", 'viridis')
            
            # 生成变化分析图
            self._create_changes_chart(ax_changes, changes)
            
            # 添加整体标题
            fig.suptitle(f'🔍 词云对比分析（{comparison_days}天变化）', 
                        fontsize=20, fontweight='bold', y=0.95)
            
            # 添加统计信息
            stats_text = f"""📊 对比统计
新增词汇：{len(changes['new_words'])}
消失词汇：{len(changes['disappeared_words'])}
上升词汇：{len(changes['rising_words'])}
下降词汇：{len(changes['falling_words'])}"""
            
            fig.text(0.02, 0.02, stats_text, fontsize=10, 
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
            
            # 添加时间水印
            fig.text(0.98, 0.02, f'🕰️ {datetime.now().strftime("%Y-%m-%d %H:%M")}', 
                    fontsize=8, ha='right', alpha=0.6)
            
            # 保存对比图
            timestamp = int(time.time())
            filename = f"wordcloud_comparison_{group_id}_{comparison_days}d_{timestamp}.png"
            filepath = self.wordcloud_dir / filename
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            logger.info(f"对比词云生成成功: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"对比词云生成失败: {e}")
            return None
    
    def _analyze_word_changes(self, current_data: Dict[str, int], historical_data: Dict[str, int]) -> Dict:
        """分析词汇变化"""
        current_words = set(current_data.keys())
        historical_words = set(historical_data.keys())
        
        # 新增和消失的词汇
        new_words = current_words - historical_words
        disappeared_words = historical_words - current_words
        
        # 频率变化
        rising_words = []
        falling_words = []
        stable_words = []
        
        for word in current_words & historical_words:
            current_freq = current_data[word]
            historical_freq = historical_data[word]
            change = current_freq - historical_freq
            
            if change > 0:
                rising_words.append((word, change, current_freq))
            elif change < 0:
                falling_words.append((word, abs(change), current_freq))
            else:
                stable_words.append((word, current_freq))
        
        # 按变化幅度排序
        rising_words.sort(key=lambda x: x[1], reverse=True)
        falling_words.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'new_words': list(new_words)[:10],
            'disappeared_words': list(disappeared_words)[:10],
            'rising_words': rising_words[:10],
            'falling_words': falling_words[:10],
            'stable_words': stable_words[:10]
        }
    
    def _create_single_wordcloud(self, ax, word_data: Dict[str, int], title: str, colormap: str):
        """创建单个词云"""
        if not word_data:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', fontsize=20)
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.axis('off')
            return
        
        # 生成词云
        font_path = self.font_manager._get_chinese_font_path()
        wordcloud = WordCloud(
            width=600, height=400,
            background_color='white',
            font_path=font_path,
            max_words=50,
            colormap=colormap,
            relative_scaling=0.6,
            min_font_size=12,
            max_font_size=60,
            collocations=False,
            random_state=42
        ).generate_from_frequencies(word_data)
        
        ax.imshow(wordcloud, interpolation='bilinear', alpha=0.9)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.axis('off')
    
    def _create_changes_chart(self, ax, changes: Dict):
        """创建变化分析图表"""
        # 准备数据
        categories = []
        values = []
        colors = []
        
        # 新增词汇（取前5个）
        new_words = changes['new_words'][:5]
        if new_words:
            categories.extend([f"新增: {word}" for word in new_words])
            values.extend([1] * len(new_words))  # 统一高度
            colors.extend(['#2ecc71'] * len(new_words))  # 绿色
        
        # 上升词汇（取前5个）
        rising_words = changes['rising_words'][:5]
        if rising_words:
            for word, change, freq in rising_words:
                categories.append(f"上升: {word} (+{change})")
                values.append(change)
                colors.append('#3498db')  # 蓝色
        
        # 下降词汇（取前5个）
        falling_words = changes['falling_words'][:5]
        if falling_words:
            for word, change, freq in falling_words:
                categories.append(f"下降: {word} (-{change})")
                values.append(-change)  # 负值显示
                colors.append('#e74c3c')  # 红色
        
        if not categories:
            ax.text(0.5, 0.5, '暂无变化数据', ha='center', va='center', fontsize=16)
            ax.set_title('📈 变化趋势分析', fontsize=14, fontweight='bold')
            ax.axis('off')
            return
        
        # 绘制水平条形图
        y_pos = np.arange(len(categories))
        bars = ax.barh(y_pos, values, color=colors, alpha=0.8)
        
        # 设置标签
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories, fontsize=10)
        ax.set_xlabel('变化幅度', fontsize=12)
        ax.set_title('📈 变化趋势分析', fontsize=14, fontweight='bold')
        
        # 添加数值标签
        for i, (bar, value) in enumerate(zip(bars, values)):
            if value >= 0:
                ax.text(value + 0.1, bar.get_y() + bar.get_height()/2, 
                       f'+{value}', va='center', fontsize=9, color='darkgreen')
            else:
                ax.text(value - 0.1, bar.get_y() + bar.get_height()/2, 
                       f'{value}', va='center', ha='right', fontsize=9, color='darkred')
        
        # 添加零线
        ax.axvline(x=0, color='black', linestyle='-', alpha=0.3)
        
        # 美化网格
        ax.grid(True, alpha=0.3, axis='x')
        ax.set_axisbelow(True)
    
    async def cleanup_old_wordclouds(self, max_age_hours: int = 24):
        """清理旧的词云文件"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            deleted_count = 0
            for wordcloud_file in self.wordcloud_dir.glob("wordcloud_*.png"):
                file_age = current_time - wordcloud_file.stat().st_mtime
                if file_age > max_age_seconds:
                    wordcloud_file.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"已清理 {deleted_count} 个过期词云文件")
                
        except Exception as e:
            logger.error(f"词云文件清理失败: {e}")
