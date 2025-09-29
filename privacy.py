"""
数据分析师插件 - 隐私保护模块

提供敏感信息检测、内容脱敏和隐私保护功能
"""

import hashlib
import re
from typing import Dict, List, Optional, Set
from astrbot.api import logger


class PrivacyFilter:
    """
    /// 隐私过滤器
    /// 负责检测和处理敏感信息，保护用户隐私
    /// 支持多种脱敏策略和敏感词检测
    """
    
    def __init__(self, privacy_settings: Dict):
        """
        /// 初始化隐私过滤器
        /// @param privacy_settings: 隐私设置配置
        """
        self.enable_content_hash = privacy_settings.get("enable_content_hash", True)
        self.sensitive_keywords = set(privacy_settings.get("sensitive_keywords", []))
        
        # 预编译常用的敏感信息正则表达式
        self._compile_patterns()
        
        # 统计信息
        self.filtered_count = 0
        self.hash_count = 0
        
        logger.info(f"隐私过滤器已初始化，敏感词数量: {len(self.sensitive_keywords)}")
    
    def _compile_patterns(self):
        """
        /// 编译常用的敏感信息检测正则表达式
        /// 包括手机号、身份证、银行卡、邮箱等
        """
        self.patterns = {
            # 中国手机号 (11位)
            'phone': re.compile(r'1[3-9]\d{9}'),
            
            # 中国身份证号 (18位)
            'id_card': re.compile(r'\d{17}[\dXx]'),
            
            # 银行卡号 (13-19位)
            'bank_card': re.compile(r'\d{13,19}'),
            
            # 邮箱地址
            'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            
            # IP地址
            'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
            
            # QQ号 (5-11位)
            'qq_number': re.compile(r'\b[1-9]\d{4,10}\b'),
        }
    
    def filter_content(self, content: str) -> str:
        """
        /// 过滤敏感内容
        /// @param content: 原始内容
        /// @return: 过滤后的内容或哈希值
        """
        if not content or not isinstance(content, str):
            return ""
        
        try:
            # 检查是否需要进行哈希处理
            if self._should_hash_content(content):
                self.hash_count += 1
                return self._hash_content(content)
            
            # 进行敏感信息脱敏
            filtered_content = self._mask_sensitive_info(content)
            
            if filtered_content != content:
                self.filtered_count += 1
            
            return filtered_content
            
        except Exception as e:
            logger.error(f"内容过滤失败: {e}")
            return self._hash_content(content)  # 出错时进行哈希处理
    
    def _should_hash_content(self, content: str) -> bool:
        """
        /// 判断是否应该对内容进行哈希处理
        /// @param content: 要检查的内容
        /// @return: 是否需要哈希处理
        """
        if not self.enable_content_hash:
            return False
        
        # 检查是否包含敏感关键词
        content_lower = content.lower()
        for keyword in self.sensitive_keywords:
            if keyword.lower() in content_lower:
                return True
        
        # 检查是否包含敏感信息模式
        for pattern_name, pattern in self.patterns.items():
            if pattern.search(content):
                logger.debug(f"检测到敏感信息模式: {pattern_name}")
                return True
        
        # 如果内容过长，也进行哈希处理
        if len(content) > 200:
            return True
        
        return False
    
    def _mask_sensitive_info(self, content: str) -> str:
        """
        /// 对敏感信息进行脱敏处理
        /// @param content: 原始内容
        /// @return: 脱敏后的内容
        """
        masked_content = content
        
        try:
            # 脱敏手机号 (保留前3位和后4位)
            masked_content = self.patterns['phone'].sub(
                lambda m: m.group()[:3] + '****' + m.group()[-4:], 
                masked_content
            )
            
            # 脱敏身份证号 (保留前6位和后4位)
            masked_content = self.patterns['id_card'].sub(
                lambda m: m.group()[:6] + '********' + m.group()[-4:], 
                masked_content
            )
            
            # 脱敏银行卡号 (保留前4位和后4位)
            masked_content = self.patterns['bank_card'].sub(
                lambda m: m.group()[:4] + '*' * (len(m.group()) - 8) + m.group()[-4:] 
                if len(m.group()) >= 8 else '*' * len(m.group()), 
                masked_content
            )
            
            # 脱敏邮箱 (保留用户名首字符和域名)
            masked_content = self.patterns['email'].sub(
                lambda m: m.group().split('@')[0][0] + '***@' + m.group().split('@')[1], 
                masked_content
            )
            
            # 脱敏IP地址 (保留前两段)
            masked_content = self.patterns['ip_address'].sub(
                lambda m: '.'.join(m.group().split('.')[:2]) + '.***.**', 
                masked_content
            )
            
            # 脱敏QQ号 (保留前3位)
            masked_content = self.patterns['qq_number'].sub(
                lambda m: m.group()[:3] + '*' * (len(m.group()) - 3), 
                masked_content
            )
            
        except Exception as e:
            logger.error(f"敏感信息脱敏失败: {e}")
            return content
        
        return masked_content
    
    def _hash_content(self, content: str) -> str:
        """
        /// 生成内容哈希值
        /// @param content: 原始内容
        /// @return: 哈希值字符串
        """
        try:
            # 使用MD5生成哈希 (考虑到性能和唯一性需求)
            hash_value = hashlib.md5(content.encode('utf-8')).hexdigest()
            return f"HASH_{hash_value[:16]}"  # 取前16位作为标识
        except Exception as e:
            logger.error(f"内容哈希失败: {e}")
            return "HASH_ERROR"
    
    def check_sensitive_content(self, content: str) -> Dict[str, List[str]]:
        """
        /// 检查内容中的敏感信息类型
        /// @param content: 要检查的内容
        /// @return: 敏感信息类型和匹配结果的字典
        """
        results = {}
        
        if not content:
            return results
        
        try:
            # 检查各种敏感信息模式
            for pattern_name, pattern in self.patterns.items():
                matches = pattern.findall(content)
                if matches:
                    results[pattern_name] = matches
            
            # 检查敏感关键词
            content_lower = content.lower()
            matched_keywords = []
            for keyword in self.sensitive_keywords:
                if keyword.lower() in content_lower:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                results['keywords'] = matched_keywords
                
        except Exception as e:
            logger.error(f"敏感内容检查失败: {e}")
        
        return results
    
    def is_content_safe(self, content: str) -> bool:
        """
        /// 判断内容是否安全（不包含敏感信息）
        /// @param content: 要检查的内容
        /// @return: 是否安全
        """
        if not content:
            return True
        
        sensitive_info = self.check_sensitive_content(content)
        return len(sensitive_info) == 0
    
    def add_sensitive_keyword(self, keyword: str):
        """
        /// 添加敏感关键词
        /// @param keyword: 要添加的关键词
        """
        if keyword and keyword.strip():
            self.sensitive_keywords.add(keyword.strip())
            logger.info(f"已添加敏感关键词: {keyword}")
    
    def remove_sensitive_keyword(self, keyword: str):
        """
        /// 移除敏感关键词
        /// @param keyword: 要移除的关键词
        """
        if keyword in self.sensitive_keywords:
            self.sensitive_keywords.remove(keyword)
            logger.info(f"已移除敏感关键词: {keyword}")
    
    def get_filter_stats(self) -> Dict[str, int]:
        """
        /// 获取过滤统计信息
        /// @return: 统计数据字典
        """
        return {
            'filtered_count': self.filtered_count,
            'hash_count': self.hash_count,
            'sensitive_keywords_count': len(self.sensitive_keywords),
            'patterns_count': len(self.patterns)
        }
    
    def reset_stats(self):
        """
        /// 重置统计计数器
        """
        self.filtered_count = 0
        self.hash_count = 0
        logger.info("隐私过滤统计已重置")


class ContentValidator:
    """
    /// 内容验证器
    /// 提供内容格式和安全性验证功能
    """
    
    @staticmethod
    def is_valid_user_id(user_id: str) -> bool:
        """
        /// 验证用户ID格式
        /// @param user_id: 用户ID
        /// @return: 是否有效
        """
        if not user_id or not isinstance(user_id, str):
            return False
        
        # 基本长度检查
        if len(user_id) < 3 or len(user_id) > 50:
            return False
        
        # 字符检查 (允许字母、数字、下划线、连字符)
        import string
        allowed_chars = string.ascii_letters + string.digits + '_-'
        return all(c in allowed_chars for c in user_id)
    
    @staticmethod
    def is_valid_group_id(group_id: str) -> bool:
        """
        /// 验证群组ID格式
        /// @param group_id: 群组ID
        /// @return: 是否有效
        """
        if not group_id or not isinstance(group_id, str):
            return False
        
        # QQ群号一般是5-10位数字
        if group_id.isdigit() and 5 <= len(group_id) <= 15:
            return True
        
        # 其他平台的群组ID格式检查
        return ContentValidator.is_valid_user_id(group_id)
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        /// 清理文件名，移除不安全的字符
        /// @param filename: 原始文件名
        /// @return: 清理后的文件名
        """
        if not filename:
            return "unnamed"
        
        # 移除或替换不安全的字符
        import string
        safe_chars = string.ascii_letters + string.digits + '_.-'
        sanitized = ''.join(c if c in safe_chars else '_' for c in filename)
        
        # 确保不以点开头，避免隐藏文件
        if sanitized.startswith('.'):
            sanitized = 'file_' + sanitized[1:]
        
        # 限制长度
        return sanitized[:50] if len(sanitized) > 50 else sanitized
    
    @staticmethod
    def validate_keyword(keyword: str) -> bool:
        """
        /// 验证关键词格式
        /// @param keyword: 关键词
        /// @return: 是否有效
        """
        if not keyword or not isinstance(keyword, str):
            return False
        
        keyword = keyword.strip()
        
        # 长度检查
        if len(keyword) < 1 or len(keyword) > 20:
            return False
        
        # 不能全是数字或特殊字符
        if keyword.isdigit() or not any(c.isalnum() for c in keyword):
            return False
        
        return True


class DataAnonymizer:
    """
    /// 数据匿名化工具
    /// 提供数据匿名化和去标识化功能
    """
    
    def __init__(self):
        self.user_mapping = {}  # 用户ID映射
        self.group_mapping = {}  # 群组ID映射
        self.counter = 1
    
    def anonymize_user_id(self, user_id: str) -> str:
        """
        /// 匿名化用户ID
        /// @param user_id: 原始用户ID
        /// @return: 匿名化后的ID
        """
        if user_id not in self.user_mapping:
            self.user_mapping[user_id] = f"USER_{self.counter:06d}"
            self.counter += 1
        
        return self.user_mapping[user_id]
    
    def anonymize_group_id(self, group_id: str) -> str:
        """
        /// 匿名化群组ID
        /// @param group_id: 原始群组ID
        /// @return: 匿名化后的ID
        """
        if group_id not in self.group_mapping:
            self.group_mapping[group_id] = f"GROUP_{len(self.group_mapping) + 1:04d}"
        
        return self.group_mapping[group_id]
    
    def get_mapping_stats(self) -> Dict[str, int]:
        """
        /// 获取映射统计信息
        /// @return: 统计数据
        """
        return {
            'users_mapped': len(self.user_mapping),
            'groups_mapped': len(self.group_mapping),
            'next_counter': self.counter
        }
    
    def clear_mappings(self):
        """
        /// 清除所有映射关系
        """
        self.user_mapping.clear()
        self.group_mapping.clear()
        self.counter = 1
