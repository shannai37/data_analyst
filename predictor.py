"""
数据分析师插件 - 预测分析模块

提供基于历史数据的趋势预测和异常检测功能
"""

import numpy as np
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from astrbot.api import logger
from .models import PredictionResult, ActivityAnalysisData
from .database import DatabaseManager


class PredictorService:
    """
    /// 预测分析服务
    /// 基于历史数据进行趋势预测、异常检测和模式识别
    /// 支持多种预测算法和置信度评估
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        /// 初始化预测服务
        /// @param db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self.min_data_points = 7  # 最少需要7天数据进行预测
        self.max_prediction_days = 30  # 最大预测30天
        
        logger.info("预测分析服务已初始化")
    
    async def predict(self, group_id: str, target: str, days: int) -> Optional[PredictionResult]:
        """
        /// 执行预测分析
        /// @param group_id: 群组ID
        /// @param target: 预测目标 (activity/members/topics)
        /// @param days: 预测天数
        /// @return: 预测结果
        """
        try:
            if days <= 0 or days > self.max_prediction_days:
                logger.warning(f"预测天数超出范围: {days}")
                return None
            
            if target == "activity":
                return await self._predict_activity(group_id, days)
            elif target == "members":
                return await self._predict_member_growth(group_id, days)
            elif target == "topics":
                return await self._predict_topic_trends(group_id, days)
            else:
                logger.warning(f"不支持的预测目标: {target}")
                return None
                
        except Exception as e:
            logger.error(f"预测分析失败: {e}")
            return None
    
    async def _predict_activity(self, group_id: str, days: int) -> Optional[PredictionResult]:
        """
        /// 预测群组活跃度
        /// @param group_id: 群组ID
        /// @param days: 预测天数
        /// @return: 活跃度预测结果
        """
        try:
            # 获取历史数据（最近30天或更多）
            historical_period = max(30, days * 2)
            activity_data = await self.db_manager.get_activity_analysis(group_id, f"{historical_period}d")
            
            if not activity_data or not activity_data.daily_data:
                return None
            
            daily_data = activity_data.daily_data
            if len(daily_data) < self.min_data_points:
                return None
            
            # 准备数据
            dates = [datetime.strptime(row[0], '%Y-%m-%d') for row in daily_data]
            counts = [row[1] for row in daily_data]
            
            # 使用多种预测方法
            linear_pred = self._linear_prediction(counts, days)
            trend_pred = self._trend_analysis_prediction(counts, days)
            seasonal_pred = self._seasonal_prediction(counts, days)
            
            # 综合预测结果
            predictions = self._combine_predictions([linear_pred, trend_pred, seasonal_pred])
            
            # 计算置信度
            confidence = self._calculate_confidence(counts, predictions[:len(counts)])
            
            # 分析趋势方向
            trend_direction = self._analyze_trend_direction(counts, predictions)
            
            # 计算变化百分比
            current_avg = np.mean(counts[-7:]) if len(counts) >= 7 else np.mean(counts)
            future_avg = np.mean(predictions)
            change_percent = ((future_avg - current_avg) / current_avg * 100) if current_avg > 0 else 0
            
            # 生成描述
            description = self._generate_activity_prediction_description(
                days, future_avg, current_avg, change_percent, confidence, trend_direction
            )
            
            return PredictionResult(
                predictions=predictions,
                confidence=confidence,
                trend_direction=trend_direction,
                change_percent=change_percent,
                description=description
            )
            
        except Exception as e:
            logger.error(f"活跃度预测失败: {e}")
            return None
    
    async def _predict_member_growth(self, group_id: str, days: int) -> Optional[PredictionResult]:
        """
        /// 预测成员增长
        /// @param group_id: 群组ID
        /// @param days: 预测天数
        /// @return: 成员增长预测结果
        """
        try:
            # 获取历史用户活跃数据
            async with aiosqlite.connect(self.db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT DATE(timestamp) as date, COUNT(DISTINCT user_id) as active_users
                    FROM messages 
                    WHERE group_id = ? AND timestamp >= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                ''', (group_id, datetime.now() - timedelta(days=30)))
                
                data = await cursor.fetchall()
                
                if len(data) < self.min_data_points:
                    return None
                
                user_counts = [row[1] for row in data]
                
                # 使用线性回归预测
                predictions = self._linear_prediction(user_counts, days)
                confidence = self._calculate_confidence(user_counts, predictions[:len(user_counts)])
                
                current_avg = np.mean(user_counts[-7:]) if len(user_counts) >= 7 else np.mean(user_counts)
                future_avg = np.mean(predictions)
                change_percent = ((future_avg - current_avg) / current_avg * 100) if current_avg > 0 else 0
                
                trend_direction = "增长" if change_percent > 5 else "下降" if change_percent < -5 else "稳定"
                
                description = f"""📊 成员活跃度预测 (未来{days}天)

🔍 预测结果:
• 预测平均活跃用户数: {future_avg:.1f}
• 相比当前变化: {change_percent:+.1f}%
• 预测趋势: {trend_direction}
• 置信度: {confidence * 100:.1f}%

💡 分析说明:
基于最近{len(user_counts)}天的历史数据进行预测。成员活跃度受多种因素影响，
实际情况可能因群组活动、话题热度等因素而有所不同。"""
                
                return PredictionResult(
                    predictions=predictions,
                    confidence=confidence,
                    trend_direction=trend_direction,
                    change_percent=change_percent,
                    description=description
                )
                
        except Exception as e:
            logger.error(f"成员增长预测失败: {e}")
            return None
    
    async def _predict_topic_trends(self, group_id: str, days: int) -> Optional[PredictionResult]:
        """
        /// 预测话题趋势
        /// @param group_id: 群组ID
        /// @param days: 预测天数
        /// @return: 话题趋势预测结果
        """
        try:
            # 获取话题活跃度历史数据
            async with aiosqlite.connect(self.db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT DATE(last_mentioned) as date, COUNT(DISTINCT keyword) as topic_count
                    FROM topic_keywords 
                    WHERE group_id = ? AND last_mentioned >= ?
                    GROUP BY DATE(last_mentioned)
                    ORDER BY date
                ''', (group_id, datetime.now() - timedelta(days=30)))
                
                data = await cursor.fetchall()
                
                if len(data) < self.min_data_points:
                    return None
                
                topic_counts = [row[1] for row in data]
                
                # 预测话题多样性
                predictions = self._seasonal_prediction(topic_counts, days)
                confidence = self._calculate_confidence(topic_counts, predictions[:len(topic_counts)])
                
                current_avg = np.mean(topic_counts[-7:]) if len(topic_counts) >= 7 else np.mean(topic_counts)
                future_avg = np.mean(predictions)
                change_percent = ((future_avg - current_avg) / current_avg * 100) if current_avg > 0 else 0
                
                if change_percent > 10:
                    trend_direction = "话题多样化增加"
                elif change_percent < -10:
                    trend_direction = "话题集中化趋势"
                else:
                    trend_direction = "话题稳定发展"
                
                description = f"""🔥 话题趋势预测 (未来{days}天)

📈 预测结果:
• 预测日均新话题数: {future_avg:.1f}
• 话题多样性变化: {change_percent:+.1f}%
• 趋势特征: {trend_direction}
• 置信度: {confidence * 100:.1f}%

🎯 趋势分析:
{self._generate_topic_trend_insights(change_percent, current_avg, future_avg)}

⚠️ 注意: 话题趋势受群组活动、外部事件等多种因素影响，预测结果仅供参考。"""
                
                return PredictionResult(
                    predictions=predictions,
                    confidence=confidence,
                    trend_direction=trend_direction,
                    change_percent=change_percent,
                    description=description
                )
                
        except Exception as e:
            logger.error(f"话题趋势预测失败: {e}")
            return None
    
    def _linear_prediction(self, data: List[float], days: int) -> List[float]:
        """
        /// 线性回归预测
        /// @param data: 历史数据
        /// @param days: 预测天数
        /// @return: 预测结果
        """
        if len(data) < 2:
            return [data[0]] * days if data else [0] * days
        
        # 准备数据
        X = np.array(range(len(data))).reshape(-1, 1)
        y = np.array(data)
        
        # 训练线性回归模型
        model = LinearRegression()
        model.fit(X, y)
        
        # 预测未来数据
        future_X = np.array(range(len(data), len(data) + days)).reshape(-1, 1)
        predictions = model.predict(future_X)
        
        # 确保预测值非负
        predictions = np.maximum(predictions, 0)
        
        return predictions.tolist()
    
    def _trend_analysis_prediction(self, data: List[float], days: int) -> List[float]:
        """
        /// 趋势分析预测
        /// @param data: 历史数据
        /// @param days: 预测天数
        /// @return: 预测结果
        """
        if len(data) < 3:
            return self._linear_prediction(data, days)
        
        # 计算趋势
        recent_window = min(7, len(data) // 2)
        recent_avg = np.mean(data[-recent_window:])
        early_avg = np.mean(data[:recent_window])
        
        trend_slope = (recent_avg - early_avg) / recent_window
        
        # 基于趋势预测
        last_value = data[-1]
        predictions = []
        
        for i in range(1, days + 1):
            predicted_value = last_value + trend_slope * i
            # 添加一些随机波动
            noise = np.random.normal(0, np.std(data) * 0.1)
            predictions.append(max(0, predicted_value + noise))
        
        return predictions
    
    def _seasonal_prediction(self, data: List[float], days: int) -> List[float]:
        """
        /// 季节性预测
        /// @param data: 历史数据
        /// @param days: 预测天数
        /// @return: 预测结果
        """
        if len(data) < 7:
            return self._linear_prediction(data, days)
        
        # 简单的周期性模式检测
        week_pattern = []
        if len(data) >= 7:
            for i in range(7):
                week_values = [data[j] for j in range(i, len(data), 7)]
                week_pattern.append(np.mean(week_values))
        
        # 基于周期性模式预测
        predictions = []
        for i in range(days):
            pattern_index = i % len(week_pattern)
            base_value = week_pattern[pattern_index]
            
            # 添加趋势调整
            trend_factor = 1 + (np.mean(data[-7:]) - np.mean(data[:7])) / np.mean(data[:7])
            predicted_value = base_value * trend_factor
            
            predictions.append(max(0, predicted_value))
        
        return predictions
    
    def _combine_predictions(self, prediction_lists: List[List[float]]) -> List[float]:
        """
        /// 组合多个预测结果
        /// @param prediction_lists: 多个预测结果列表
        /// @return: 组合后的预测结果
        """
        if not prediction_lists:
            return []
        
        # 过滤空列表
        valid_predictions = [p for p in prediction_lists if p]
        if not valid_predictions:
            return []
        
        # 计算加权平均
        weights = [0.4, 0.3, 0.3]  # 线性、趋势、季节性的权重
        combined = []
        
        for i in range(len(valid_predictions[0])):
            weighted_sum = 0
            total_weight = 0
            
            for j, pred_list in enumerate(valid_predictions):
                if i < len(pred_list):
                    weight = weights[j] if j < len(weights) else 1.0 / len(valid_predictions)
                    weighted_sum += pred_list[i] * weight
                    total_weight += weight
            
            combined.append(weighted_sum / total_weight if total_weight > 0 else 0)
        
        return combined
    
    def _calculate_confidence(self, historical: List[float], fitted: List[float]) -> float:
        """
        /// 计算预测置信度
        /// @param historical: 历史真实值
        /// @param fitted: 模型拟合值
        /// @return: 置信度 (0-1)
        """
        try:
            if len(historical) != len(fitted) or len(historical) < 2:
                return 0.5  # 默认中等置信度
            
            # 计算R²决定系数
            r2 = r2_score(historical, fitted)
            
            # 计算相对误差
            mape = np.mean(np.abs((np.array(historical) - np.array(fitted)) / np.maximum(np.array(historical), 1)))
            
            # 综合置信度评估
            confidence = max(0, min(1, (r2 + (1 - mape)) / 2))
            
            return confidence
            
        except Exception:
            return 0.5
    
    def _analyze_trend_direction(self, historical: List[float], predictions: List[float]) -> str:
        """
        /// 分析趋势方向
        /// @param historical: 历史数据
        /// @param predictions: 预测数据
        /// @return: 趋势描述
        """
        if not historical or not predictions:
            return "未知"
        
        recent_avg = np.mean(historical[-7:]) if len(historical) >= 7 else np.mean(historical)
        predicted_avg = np.mean(predictions)
        
        change_rate = (predicted_avg - recent_avg) / recent_avg if recent_avg > 0 else 0
        
        if change_rate > 0.1:
            return "上升"
        elif change_rate < -0.1:
            return "下降"
        else:
            return "稳定"
    
    def _generate_activity_prediction_description(self, days: int, future_avg: float, 
                                                current_avg: float, change_percent: float, 
                                                confidence: float, trend_direction: str) -> str:
        """生成活跃度预测描述"""
        # 趋势评价
        if trend_direction == "上升":
            trend_emoji = "📈"
            trend_desc = "群组活跃度将保持上升趋势"
        elif trend_direction == "下降":
            trend_emoji = "📉"
            trend_desc = "群组活跃度可能有所下降"
        else:
            trend_emoji = "📊"
            trend_desc = "群组活跃度将保持相对稳定"
        
        # 置信度评价
        if confidence > 0.8:
            confidence_desc = "预测可信度较高"
        elif confidence > 0.6:
            confidence_desc = "预测有一定参考价值"
        else:
            confidence_desc = "预测仅供参考，实际情况可能有较大变化"
        
        # 变化幅度评价
        if abs(change_percent) > 20:
            change_desc = "变化幅度较大"
        elif abs(change_percent) > 10:
            change_desc = "有明显变化趋势"
        else:
            change_desc = "变化幅度较小"
        
        return f"""{trend_emoji} 活跃度预测 (未来{days}天)

📊 预测结果:
• 预测平均日消息数: {future_avg:.1f}
• 相比当前变化: {change_percent:+.1f}%
• 置信度: {confidence * 100:.1f}%

📈 趋势分析:
{trend_desc}，{change_desc}。

🎯 预测评估:
{confidence_desc}。建议结合实际群组活动和外部因素综合判断。

⚠️ 注意: 预测结果基于历史数据模式，实际情况可能受群组事件、节假日、话题热度等多种因素影响。"""
    
    def _generate_topic_trend_insights(self, change_percent: float, current_avg: float, future_avg: float) -> str:
        """生成话题趋势洞察"""
        if change_percent > 15:
            return "预计群组话题将更加多样化，可能出现更多新的讨论方向。建议关注新兴话题，适时引导讨论。"
        elif change_percent < -15:
            return "预计群组话题将趋于集中化，讨论可能围绕少数热门话题。建议主动引入新话题，保持讨论活力。"
        else:
            return "预计群组话题将保持当前的多样性水平，讨论内容相对稳定。"
    
    async def detect_anomalies(self, group_id: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """
        /// 异常检测
        /// @param group_id: 群组ID
        /// @param days: 检测时间范围
        /// @return: 异常检测结果
        """
        try:
            activity_data = await self.db_manager.get_activity_analysis(group_id, f"{days}d")
            if not activity_data or not activity_data.daily_data:
                return None
            
            counts = [row[1] for row in activity_data.daily_data]
            
            # 使用统计方法检测异常
            mean_val = np.mean(counts)
            std_val = np.std(counts)
            threshold = 2 * std_val  # 2倍标准差
            
            anomalies = []
            for i, count in enumerate(counts):
                if abs(count - mean_val) > threshold:
                    anomalies.append({
                        'date': activity_data.daily_data[i][0],
                        'value': count,
                        'deviation': abs(count - mean_val),
                        'type': 'high' if count > mean_val else 'low'
                    })
            
            return {
                'total_anomalies': len(anomalies),
                'anomalies': anomalies,
                'mean_value': mean_val,
                'std_value': std_val,
                'detection_threshold': threshold
            }
            
        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            return None
