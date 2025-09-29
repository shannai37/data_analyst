"""
AstrBot 数据分析师插件

提供群聊数据分析、用户行为洞察、话题趋势预测等功能
支持多种数据可视化和导出格式

模块结构:
- main.py: 主插件文件，处理命令和事件
- models.py: 数据模型和配置类
- privacy.py: 隐私保护和数据脱敏
- database.py: 数据库管理和数据存储
- charts.py: 图表生成和可视化
- export.py: 数据导出和报告生成
- predictor.py: 预测分析和趋势预测
"""

__version__ = "1.0.0"
__author__ = "DataAnalyst Team"
__description__ = "智能数据分析师插件"

# 导出主要类
from .main import DataAnalystPlugin

__all__ = ["DataAnalystPlugin"]
