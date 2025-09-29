"""
用户画像可视化组件

生成美观的用户画像卡片和统计图表
参考现代 UI 设计，提供多种可视化样式
"""

import os
import time
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import math

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
import matplotlib.gridspec as gridspec
import seaborn as sns
from PIL import Image, ImageDraw, ImageFont

from astrbot.api import logger
from .models import ChartConstants as CC, PluginConfig
from .font_manager import FontManager
from .portrait_analyzer import UserPortrait, CommunicationStyle


class PortraitCardStyle:
    """画像卡片样式配置"""
    
    # 颜色方案
    COLOR_SCHEMES = {
        'modern': {
            'primary': '#3498db',
            'secondary': '#2ecc71', 
            'accent': '#e74c3c',
            'background': '#f8f9fa',
            'text': '#2c3e50',
            'light': '#ecf0f1'
        },
        'elegant': {
            'primary': '#8e44ad',
            'secondary': '#95a5a6',
            'accent': '#f39c12',
            'background': '#ffffff',
            'text': '#34495e',
            'light': '#bdc3c7'
        },
        'tech': {
            'primary': '#1abc9c',
            'secondary': '#34495e',
            'accent': '#e67e22',
            'background': '#2c3e50',
            'text': '#ecf0f1',
            'light': '#7f8c8d'
        },
        'warm': {
            'primary': '#ff6b6b',
            'secondary': '#4ecdc4',
            'accent': '#ffe66d',
            'background': '#fff5f5',
            'text': '#2d3436',
            'light': '#fab1a0'
        }
    }
    
    # 字体大小
    FONT_SIZES = {
        'title': 18,
        'subtitle': 14,
        'body': 12,
        'caption': 10,
        'label': 9
    }


class PortraitVisualizer:
    """
    用户画像可视化器
    
    功能特色：
    - 生成精美的用户画像卡片
    - 多种视觉风格支持
    - 24小时活跃度图表
    - 性格标签可视化  
    - 用户对比图表
    - 响应式布局设计
    """
    
    def __init__(self, charts_dir: Path, font_manager: FontManager, config: PluginConfig):
        """
        初始化画像可视化器
        
        Args:
            charts_dir: 图表保存目录
            font_manager: 字体管理器
            config: 插件配置
        """
        self.charts_dir = charts_dir
        self.font_manager = font_manager
        self.config = config
        
        # 创建画像专用目录
        self.portrait_dir = charts_dir / "portraits"
        self.portrait_dir.mkdir(exist_ok=True)
        
        # 配置 matplotlib
        self._setup_matplotlib()
        
        logger.info(f"用户画像可视化器已初始化: {self.portrait_dir}")
    
    def _setup_matplotlib(self):
        """配置 matplotlib"""
        try:
            # 使用字体管理器配置
            self.font_manager.configure_matplotlib()
            
            # 设置样式
            plt.style.use('default')
            plt.rcParams.update({
                'figure.dpi': 150,
                'savefig.dpi': 300,
                'savefig.bbox': 'tight',
                'axes.spines.top': False,
                'axes.spines.right': False,
                'axes.grid': True,
                'axes.grid.alpha': 0.3,
                'grid.linewidth': 0.5,
                'font.size': 10
            })
            
            logger.info("画像可视化器 matplotlib 配置完成")
            
        except Exception as e:
            logger.error(f"matplotlib 配置失败: {e}")
    
    async def generate_portrait_card(
        self,
        portrait: UserPortrait,
        style: str = 'modern',
        include_charts: bool = True
    ) -> Optional[str]:
        """
        生成用户画像卡片
        
        Args:
            portrait: 用户画像数据
            style: 视觉风格
            include_charts: 是否包含图表
            
        Returns:
            生成的卡片图片路径
        """
        try:
            # 获取颜色方案
            colors = PortraitCardStyle.COLOR_SCHEMES.get(style, PortraitCardStyle.COLOR_SCHEMES['modern'])
            
            # 创建画布
            if include_charts:
                fig = plt.figure(figsize=(16, 12))
                gs = gridspec.GridSpec(4, 4, figure=fig, hspace=0.3, wspace=0.3)
            else:
                fig = plt.figure(figsize=(12, 8))
                gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
            
            # 设置背景色
            fig.patch.set_facecolor(colors['background'])
            
            # 1. 标题区域
            self._create_title_section(fig, gs, portrait, colors)
            
            # 2. 基础信息区域
            self._create_basic_info_section(fig, gs, portrait, colors)
            
            # 3. 性格分析区域
            self._create_personality_section(fig, gs, portrait, colors)
            
            if include_charts:
                # 4. 活跃度图表
                self._create_activity_chart(fig, gs, portrait, colors)
                
                # 5. 性格标签云
                self._create_personality_tags_visual(fig, gs, portrait, colors)
                
                # 6. 行为模式雷达图
                self._create_behavior_radar(fig, gs, portrait, colors)
            
            # 添加装饰元素
            self._add_decorative_elements(fig, colors)
            
            # 添加水印
            self._add_watermark(fig, colors)
            
            # 保存图片
            timestamp = int(time.time())
            filename = f"portrait_{portrait.user_id}_{style}_{timestamp}.png"
            filepath = self.portrait_dir / filename
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight', 
                       facecolor=colors['background'], edgecolor='none')
            plt.close(fig)
            
            logger.info(f"用户画像卡片生成成功: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"用户画像卡片生成失败: {e}")
            return None
    
    def _create_title_section(self, fig, gs, portrait: UserPortrait, colors: Dict[str, str]):
        """创建标题区域"""
        ax = fig.add_subplot(gs[0, :2])
        ax.axis('off')
        
        # 主标题
        title_text = f"👤 {portrait.nickname} 的用户画像"
        ax.text(0.05, 0.7, title_text, fontsize=PortraitCardStyle.FONT_SIZES['title'], 
               fontweight='bold', color=colors['text'], transform=ax.transAxes)
        
        # 副标题
        subtitle_text = f"分析深度: {portrait.analysis_depth.upper()} | 分析时间: {portrait.analysis_date.strftime('%Y-%m-%d %H:%M')}"
        ax.text(0.05, 0.3, subtitle_text, fontsize=PortraitCardStyle.FONT_SIZES['caption'], 
               color=colors['light'], transform=ax.transAxes)
        
        # 数据质量指示器
        if portrait.data_quality_score:
            quality_color = colors['secondary'] if portrait.data_quality_score > 0.7 else colors['accent']
            ax.text(0.05, 0.1, f"📊 数据质量: {portrait.data_quality_score:.1%}", 
                   fontsize=PortraitCardStyle.FONT_SIZES['caption'], color=quality_color, 
                   transform=ax.transAxes)
    
    def _create_basic_info_section(self, fig, gs, portrait: UserPortrait, colors: Dict[str, str]):
        """创建基础信息区域"""
        ax = fig.add_subplot(gs[0, 2:])
        ax.axis('off')
        
        # 创建信息卡片背景
        bbox = FancyBboxPatch((0.05, 0.1), 0.9, 0.8, 
                             boxstyle="round,pad=0.02",
                             facecolor=colors['light'], 
                             edgecolor=colors['primary'],
                             linewidth=2, alpha=0.3)
        ax.add_patch(bbox)
        
        # 基础统计信息
        info_lines = [
            f"💬 发言次数: {portrait.message_count:,} 条",
            f"📝 总字数: {portrait.word_count:,} 字", 
            f"⚡ 平均字数: {portrait.avg_words_per_message:.1f} 字/条",
            f"📅 活跃天数: {portrait.active_days} 天",
            f"🕒 活跃时段: {len(portrait.peak_hours)} 个",
            f"🎯 交流风格: {portrait.communication_style}"
        ]
        
        for i, line in enumerate(info_lines):
            y_pos = 0.8 - i * 0.12
            ax.text(0.1, y_pos, line, fontsize=PortraitCardStyle.FONT_SIZES['body'], 
                   color=colors['text'], transform=ax.transAxes)
    
    def _create_personality_section(self, fig, gs, portrait: UserPortrait, colors: Dict[str, str]):
        """创建性格分析区域"""
        ax = fig.add_subplot(gs[1, :])
        ax.axis('off')
        
        # 标题
        ax.text(0.02, 0.9, "🧠 性格分析", fontsize=PortraitCardStyle.FONT_SIZES['subtitle'], 
               fontweight='bold', color=colors['primary'], transform=ax.transAxes)
        
        # 性格分析文本
        if portrait.personality_analysis:
            # 将长文本分段显示
            analysis_text = portrait.personality_analysis
            wrapped_text = self._wrap_text(analysis_text, 100)  # 每行100字符
            
            y_start = 0.75
            for i, line in enumerate(wrapped_text[:4]):  # 最多显示4行
                y_pos = y_start - i * 0.15
                ax.text(0.02, y_pos, line, fontsize=PortraitCardStyle.FONT_SIZES['body'], 
                       color=colors['text'], transform=ax.transAxes)
        else:
            ax.text(0.02, 0.6, "基于用户行为模式的性格分析", 
                   fontsize=PortraitCardStyle.FONT_SIZES['body'], 
                   color=colors['text'], style='italic', transform=ax.transAxes)
        
        # 情感倾向
        if portrait.emotion_tendency:
            ax.text(0.02, 0.1, f"😊 情感倾向: {portrait.emotion_tendency}", 
                   fontsize=PortraitCardStyle.FONT_SIZES['body'], 
                   color=colors['secondary'], transform=ax.transAxes)
    
    def _create_activity_chart(self, fig, gs, portrait: UserPortrait, colors: Dict[str, str]):
        """创建24小时活跃度图表"""
        ax = fig.add_subplot(gs[2, :2])
        
        # 准备数据
        hours = list(range(24))
        activity_values = [portrait.activity_pattern.get(str(h), 0) for h in hours]
        
        # 创建极坐标图
        ax.remove()
        ax = fig.add_subplot(gs[2, :2], projection='polar')
        
        # 转换为弧度
        theta = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        
        # 绘制活跃度
        bars = ax.bar(theta, activity_values, width=0.25, alpha=0.8, 
                     color=colors['primary'], edgecolor=colors['background'], linewidth=1)
        
        # 突出显示峰值时段
        for i, peak_hour in enumerate(portrait.peak_hours[:3]):
            if peak_hour < 24:
                bars[peak_hour].set_color(colors['accent'])
                bars[peak_hour].set_alpha(1.0)
        
        # 设置标签
        ax.set_xticks(theta)
        ax.set_xticklabels([f'{h}:00' for h in hours], fontsize=8)
        ax.set_ylim(0, max(activity_values) * 1.2 if activity_values else 0.1)
        ax.set_title('🕒 24小时活跃度分布', fontsize=PortraitCardStyle.FONT_SIZES['subtitle'], 
                    fontweight='bold', color=colors['text'], pad=20)
        ax.grid(True, alpha=0.3)
    
    def _create_personality_tags_visual(self, fig, gs, portrait: UserPortrait, colors: Dict[str, str]):
        """创建性格标签可视化"""
        ax = fig.add_subplot(gs[2, 2:])
        ax.axis('off')
        
        # 标题
        ax.text(0.5, 0.9, "🏷️ 性格标签", fontsize=PortraitCardStyle.FONT_SIZES['subtitle'], 
               fontweight='bold', color=colors['primary'], transform=ax.transAxes, ha='center')
        
        if portrait.personality_tags:
            # 创建标签云效果
            tags = portrait.personality_tags[:6]  # 最多显示6个标签
            
            # 计算标签位置
            positions = self._calculate_tag_positions(len(tags))
            
            for i, (tag, pos) in enumerate(zip(tags, positions)):
                x, y = pos
                
                # 创建标签背景
                tag_color = colors['primary'] if i % 2 == 0 else colors['secondary']
                
                # 绘制标签
                bbox = dict(boxstyle="round,pad=0.3", facecolor=tag_color, alpha=0.8, edgecolor='none')
                ax.text(x, y, tag, fontsize=PortraitCardStyle.FONT_SIZES['body'], 
                       color='white', fontweight='bold', ha='center', va='center',
                       transform=ax.transAxes, bbox=bbox)
        else:
            ax.text(0.5, 0.5, "暂无标签数据", fontsize=PortraitCardStyle.FONT_SIZES['body'], 
                   color=colors['light'], transform=ax.transAxes, ha='center', va='center')
    
    def _create_behavior_radar(self, fig, gs, portrait: UserPortrait, colors: Dict[str, str]):
        """创建行为模式雷达图"""
        ax = fig.add_subplot(gs[3, :2], projection='polar')
        
        # 定义维度
        dimensions = ['活跃度', '话题丰富度', '互动频率', '表达长度', '时间规律性']
        values = self._calculate_behavior_scores(portrait)
        
        # 角度
        angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
        values += values[:1]  # 闭合图形
        angles += angles[:1]
        
        # 绘制雷达图
        ax.plot(angles, values, 'o-', linewidth=2, color=colors['primary'], alpha=0.8)
        ax.fill(angles, values, alpha=0.25, color=colors['primary'])
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(dimensions, fontsize=PortraitCardStyle.FONT_SIZES['caption'])
        ax.set_ylim(0, 1)
        ax.set_title('📊 行为模式分析', fontsize=PortraitCardStyle.FONT_SIZES['subtitle'], 
                    fontweight='bold', color=colors['text'], pad=20)
        ax.grid(True, alpha=0.3)
    
    def _calculate_tag_positions(self, num_tags: int) -> List[Tuple[float, float]]:
        """计算标签位置"""
        if num_tags <= 2:
            return [(0.25, 0.5), (0.75, 0.5)][:num_tags]
        elif num_tags <= 4:
            return [(0.25, 0.7), (0.75, 0.7), (0.25, 0.3), (0.75, 0.3)][:num_tags]
        else:
            return [(0.2, 0.7), (0.5, 0.8), (0.8, 0.7), 
                   (0.2, 0.4), (0.5, 0.3), (0.8, 0.4)][:num_tags]
    
    def _calculate_behavior_scores(self, portrait: UserPortrait) -> List[float]:
        """计算行为维度得分"""
        scores = []
        
        # 活跃度得分 (基于消息数量)
        activity_score = min(portrait.message_count / 100, 1.0)
        scores.append(activity_score)
        
        # 话题丰富度得分 (基于常用词汇数量)
        topic_score = min(len(portrait.favorite_topics) / 10, 1.0)
        scores.append(topic_score)
        
        # 互动频率得分 (基于平均活跃天数)
        if portrait.active_days > 0:
            interaction_score = min(portrait.message_count / portrait.active_days / 5, 1.0)
        else:
            interaction_score = 0
        scores.append(interaction_score)
        
        # 表达长度得分 (基于平均字数)
        expression_score = min(portrait.avg_words_per_message / 30, 1.0)
        scores.append(expression_score)
        
        # 时间规律性得分 (基于活跃时段集中度)
        if portrait.peak_hours:
            regularity_score = min(len(portrait.peak_hours) / 8, 1.0)
        else:
            regularity_score = 0
        scores.append(regularity_score)
        
        return scores
    
    def _wrap_text(self, text: str, width: int) -> List[str]:
        """文本换行"""
        if not text:
            return []
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _add_decorative_elements(self, fig, colors: Dict[str, str]):
        """添加装饰元素"""
        # 添加顶部装饰线
        fig.text(0.1, 0.95, '━' * 50, fontsize=12, color=colors['primary'], alpha=0.6)
        fig.text(0.1, 0.05, '━' * 50, fontsize=12, color=colors['primary'], alpha=0.6)
    
    def _add_watermark(self, fig, colors: Dict[str, str]):
        """添加水印"""
        watermark_text = f"🤖 AstrBot 数据分析师 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        fig.text(0.99, 0.01, watermark_text, fontsize=8, color=colors['light'], 
                alpha=0.6, ha='right', va='bottom')
    
    async def generate_comparison_chart(
        self,
        portrait1: UserPortrait,
        portrait2: UserPortrait,
        style: str = 'modern'
    ) -> Optional[str]:
        """
        生成用户对比图表
        
        Args:
            portrait1: 用户1画像
            portrait2: 用户2画像
            style: 视觉风格
            
        Returns:
            生成的对比图表路径
        """
        try:
            colors = PortraitCardStyle.COLOR_SCHEMES.get(style, PortraitCardStyle.COLOR_SCHEMES['modern'])
            
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.patch.set_facecolor(colors['background'])
            
            # 1. 基础数据对比
            self._create_basic_comparison(axes[0, 0], portrait1, portrait2, colors)
            
            # 2. 活跃时间对比
            self._create_activity_comparison(axes[0, 1], portrait1, portrait2, colors)
            
            # 3. 行为模式对比
            self._create_behavior_comparison(axes[1, 0], portrait1, portrait2, colors)
            
            # 4. 性格标签对比
            self._create_tags_comparison(axes[1, 1], portrait1, portrait2, colors)
            
            # 添加整体标题
            fig.suptitle(f'👥 用户对比分析: {portrait1.nickname} vs {portrait2.nickname}', 
                        fontsize=18, fontweight='bold', color=colors['text'])
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            
            # 保存图片
            timestamp = int(time.time())
            filename = f"comparison_{portrait1.user_id}_{portrait2.user_id}_{timestamp}.png"
            filepath = self.portrait_dir / filename
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight', 
                       facecolor=colors['background'], edgecolor='none')
            plt.close(fig)
            
            logger.info(f"用户对比图表生成成功: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"用户对比图表生成失败: {e}")
            return None
    
    def _create_basic_comparison(self, ax, p1: UserPortrait, p2: UserPortrait, colors: Dict[str, str]):
        """创建基础数据对比"""
        metrics = ['消息数量', '总字数', '活跃天数', '平均字数']
        values1 = [p1.message_count, p1.word_count, p1.active_days, p1.avg_words_per_message]
        values2 = [p2.message_count, p2.word_count, p2.active_days, p2.avg_words_per_message]
        
        # 标准化数据
        max_values = [max(v1, v2) for v1, v2 in zip(values1, values2)]
        norm_values1 = [v1/max_v if max_v > 0 else 0 for v1, max_v in zip(values1, max_values)]
        norm_values2 = [v2/max_v if max_v > 0 else 0 for v2, max_v in zip(values2, max_values)]
        
        x = np.arange(len(metrics))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, norm_values1, width, label=p1.nickname, 
                      color=colors['primary'], alpha=0.8)
        bars2 = ax.bar(x + width/2, norm_values2, width, label=p2.nickname, 
                      color=colors['secondary'], alpha=0.8)
        
        ax.set_xlabel('指标', fontsize=12, color=colors['text'])
        ax.set_ylabel('相对值', fontsize=12, color=colors['text'])
        ax.set_title('📊 基础数据对比', fontsize=14, fontweight='bold', color=colors['text'])
        ax.set_xticks(x)
        ax.set_xticklabels(metrics, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _create_activity_comparison(self, ax, p1: UserPortrait, p2: UserPortrait, colors: Dict[str, str]):
        """创建活跃时间对比"""
        hours = list(range(24))
        activity1 = [p1.activity_pattern.get(str(h), 0) for h in hours]
        activity2 = [p2.activity_pattern.get(str(h), 0) for h in hours]
        
        ax.plot(hours, activity1, 'o-', label=p1.nickname, color=colors['primary'], linewidth=2)
        ax.plot(hours, activity2, 's-', label=p2.nickname, color=colors['secondary'], linewidth=2)
        
        ax.set_xlabel('小时', fontsize=12, color=colors['text'])
        ax.set_ylabel('活跃度', fontsize=12, color=colors['text'])
        ax.set_title('🕒 24小时活跃度对比', fontsize=14, fontweight='bold', color=colors['text'])
        ax.set_xticks(range(0, 24, 4))
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _create_behavior_comparison(self, ax, p1: UserPortrait, p2: UserPortrait, colors: Dict[str, str]):
        """创建行为模式对比"""
        dimensions = ['活跃度', '话题丰富度', '互动频率', '表达长度', '时间规律性']
        values1 = self._calculate_behavior_scores(p1)
        values2 = self._calculate_behavior_scores(p2)
        
        angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
        values1 += values1[:1]
        values2 += values2[:1]
        angles += angles[:1]
        
        ax.remove()
        ax = plt.subplot(2, 2, 3, projection='polar')
        
        ax.plot(angles, values1, 'o-', linewidth=2, label=p1.nickname, color=colors['primary'])
        ax.fill(angles, values1, alpha=0.25, color=colors['primary'])
        
        ax.plot(angles, values2, 's-', linewidth=2, label=p2.nickname, color=colors['secondary'])
        ax.fill(angles, values2, alpha=0.25, color=colors['secondary'])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(dimensions, fontsize=10)
        ax.set_ylim(0, 1)
        ax.set_title('📊 行为模式对比', fontsize=14, fontweight='bold', color=colors['text'], pad=20)
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _create_tags_comparison(self, ax, p1: UserPortrait, p2: UserPortrait, colors: Dict[str, str]):
        """创建性格标签对比"""
        ax.axis('off')
        ax.set_title('🏷️ 性格标签对比', fontsize=14, fontweight='bold', color=colors['text'])
        
        # 用户1标签
        ax.text(0.02, 0.8, f"{p1.nickname}:", fontsize=12, fontweight='bold', 
               color=colors['primary'], transform=ax.transAxes)
        
        if p1.personality_tags:
            tags1_text = ' • '.join(p1.personality_tags[:5])
            ax.text(0.02, 0.65, tags1_text, fontsize=10, color=colors['text'], 
                   transform=ax.transAxes, wrap=True)
        else:
            ax.text(0.02, 0.65, "暂无标签", fontsize=10, color=colors['light'], 
                   transform=ax.transAxes)
        
        # 用户2标签
        ax.text(0.02, 0.45, f"{p2.nickname}:", fontsize=12, fontweight='bold', 
               color=colors['secondary'], transform=ax.transAxes)
        
        if p2.personality_tags:
            tags2_text = ' • '.join(p2.personality_tags[:5])
            ax.text(0.02, 0.3, tags2_text, fontsize=10, color=colors['text'], 
                   transform=ax.transAxes, wrap=True)
        else:
            ax.text(0.02, 0.3, "暂无标签", fontsize=10, color=colors['light'], 
                   transform=ax.transAxes)
        
        # 共同标签
        if p1.personality_tags and p2.personality_tags:
            common_tags = set(p1.personality_tags) & set(p2.personality_tags)
            if common_tags:
                ax.text(0.02, 0.1, f"共同特质: {' • '.join(common_tags)}", 
                       fontsize=10, color=colors['accent'], fontweight='bold',
                       transform=ax.transAxes)
    
    async def generate_summary_card(
        self,
        portrait: UserPortrait,
        style: str = 'modern'
    ) -> Optional[str]:
        """
        生成简洁的摘要卡片
        
        Args:
            portrait: 用户画像
            style: 视觉风格
            
        Returns:
            生成的摘要卡片路径
        """
        try:
            colors = PortraitCardStyle.COLOR_SCHEMES.get(style, PortraitCardStyle.COLOR_SCHEMES['modern'])
            
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor(colors['background'])
            ax.axis('off')
            
            # 主标题
            ax.text(0.5, 0.9, f"👤 {portrait.nickname}", fontsize=20, fontweight='bold', 
                   color=colors['text'], ha='center', transform=ax.transAxes)
            
            # 关键信息
            key_info = [
                f"💬 {portrait.message_count:,} 条消息 | 📝 {portrait.word_count:,} 字",
                f"🎯 {portrait.communication_style} | 📅 活跃 {portrait.active_days} 天",
                f"🕒 主要活跃: {', '.join([f'{h}:00' for h in portrait.peak_hours[:3]])}"
            ]
            
            for i, info in enumerate(key_info):
                y_pos = 0.7 - i * 0.1
                ax.text(0.5, y_pos, info, fontsize=14, color=colors['text'], 
                       ha='center', transform=ax.transAxes)
            
            # 性格标签
            if portrait.personality_tags:
                tags_text = " • ".join(portrait.personality_tags[:4])
                ax.text(0.5, 0.35, f"🏷️ {tags_text}", fontsize=12, color=colors['primary'], 
                       ha='center', transform=ax.transAxes, fontweight='bold')
            
            # 性格分析摘要
            if portrait.personality_analysis:
                summary = portrait.personality_analysis[:80] + "..." if len(portrait.personality_analysis) > 80 else portrait.personality_analysis
                ax.text(0.5, 0.2, summary, fontsize=11, color=colors['text'], 
                       ha='center', transform=ax.transAxes, style='italic')
            
            # 装饰边框
            bbox = FancyBboxPatch((0.05, 0.05), 0.9, 0.9, 
                                 boxstyle="round,pad=0.02",
                                 facecolor='none', 
                                 edgecolor=colors['primary'],
                                 linewidth=3, alpha=0.6)
            ax.add_patch(bbox)
            
            # 水印
            ax.text(0.95, 0.05, f"📊 {datetime.now().strftime('%Y-%m-%d')}", 
                   fontsize=8, color=colors['light'], alpha=0.6,
                   ha='right', transform=ax.transAxes)
            
            # 保存图片
            timestamp = int(time.time())
            filename = f"summary_{portrait.user_id}_{timestamp}.png"
            filepath = self.portrait_dir / filename
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight', 
                       facecolor=colors['background'], edgecolor='none')
            plt.close(fig)
            
            logger.info(f"用户摘要卡片生成成功: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"用户摘要卡片生成失败: {e}")
            return None
    
    def get_available_styles(self) -> List[str]:
        """获取可用的可视化样式"""
        return list(PortraitCardStyle.COLOR_SCHEMES.keys())
    
    async def cleanup_old_portraits(self, max_age_hours: int = 24):
        """清理旧的画像文件"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            deleted_count = 0
            for portrait_file in self.portrait_dir.glob("*.png"):
                file_age = current_time - portrait_file.stat().st_mtime
                if file_age > max_age_seconds:
                    portrait_file.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"已清理 {deleted_count} 个过期画像文件")
                
        except Exception as e:
            logger.error(f"画像文件清理失败: {e}")
