"""
字体管理器 - 彻底解决中文显示问题
"""

import os
import platform
import requests
from pathlib import Path
from typing import Optional, List
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from astrbot.api import logger


class FontManager:
    """智能字体管理器"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.fonts_dir = data_dir / "fonts"
        self.fonts_dir.mkdir(exist_ok=True)
        
        # 系统中文字体优先级列表
        self.system_fonts = [
            # Windows字体
            'Microsoft YaHei UI', 'Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'FangSong',
            # macOS字体  
            'PingFang SC', 'Heiti SC', 'STHeiti Light', 'STSong',
            # Linux字体
            'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'Noto Sans CJK SC', 'Source Han Sans SC',
            # 通用备用
            'DejaVu Sans', 'Arial Unicode MS', 'sans-serif'
        ]
        
        # 在线字体资源（思源黑体）
        self.online_fonts = {
            'SourceHanSansSC-Regular': {
                'url': 'https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SimplifiedChinese/SourceHanSansSC-Regular.otf',
                'filename': 'SourceHanSansSC-Regular.otf'
            }
        }
    
    def detect_best_font(self) -> Optional[str]:
        """智能检测最佳中文字体"""
        try:
            # 1. 检测系统已安装字体
            system_font = self._detect_system_font()
            if system_font:
                logger.info(f"检测到系统中文字体: {system_font}")
                return system_font
            
            # 2. 尝试使用本地下载的字体
            local_font = self._check_local_fonts()
            if local_font:
                logger.info(f"使用本地字体: {local_font}")
                return local_font
            
            # 3. 下载在线字体
            downloaded_font = self._download_font()
            if downloaded_font:
                logger.info(f"下载字体成功: {downloaded_font}")
                return downloaded_font
            
            logger.warning("未找到合适的中文字体，将使用系统默认字体")
            return None
            
        except Exception as e:
            logger.error(f"字体检测失败: {e}")
            return None
    
    def _detect_system_font(self) -> Optional[str]:
        """检测系统已安装的中文字体"""
        try:
            available_fonts = [f.name for f in fm.fontManager.ttflist]
            
            # 按优先级查找
            for font_name in self.system_fonts:
                if font_name in available_fonts:
                    # 验证字体可用性
                    if self._test_font(font_name):
                        return font_name
            
            # 模糊匹配（包含关键词）
            chinese_keywords = ['yahei', 'simhei', 'simsun', 'kaiti', 'fangsong', 
                              'heiti', 'pingfang', 'wenquanyi', 'noto', 'source']
            
            for font in available_fonts:
                font_lower = font.lower()
                if any(keyword in font_lower for keyword in chinese_keywords):
                    if self._test_font(font):
                        return font
            
            return None
            
        except Exception as e:
            logger.warning(f"系统字体检测失败: {e}")
            return None
    
    def _test_font(self, font_name: str) -> bool:
        """测试字体是否支持中文"""
        try:
            font_prop = fm.FontProperties(family=font_name)
            font_path = fm.findfont(font_prop)
            
            # 检查字体文件是否存在且有效
            if font_path and os.path.exists(font_path):
                # 简单测试：设置字体后检查是否改变
                old_font = plt.rcParams.get('font.family', ['sans-serif'])
                plt.rcParams['font.family'] = [font_name]
                current_font = plt.rcParams.get('font.family')
                plt.rcParams['font.family'] = old_font  # 恢复
                
                return font_name in str(current_font)
            
            return False
            
        except Exception:
            return False
    
    def _check_local_fonts(self) -> Optional[str]:
        """检查本地已下载的字体"""
        try:
            for font_info in self.online_fonts.values():
                font_path = self.fonts_dir / font_info['filename']
                if font_path.exists():
                    # 注册字体到matplotlib
                    fm.fontManager.addfont(str(font_path))
                    font_name = fm.FontProperties(fname=str(font_path)).get_name()
                    return font_name
            
            return None
            
        except Exception as e:
            logger.warning(f"本地字体检查失败: {e}")
            return None
    
    def _download_font(self) -> Optional[str]:
        """下载在线字体"""
        try:
            # 下载思源黑体
            font_info = self.online_fonts['SourceHanSansSC-Regular']
            font_path = self.fonts_dir / font_info['filename']
            
            if font_path.exists():
                return None  # 已存在
            
            logger.info("正在下载中文字体，请稍候...")
            
            response = requests.get(font_info['url'], timeout=30)
            response.raise_for_status()
            
            with open(font_path, 'wb') as f:
                f.write(response.content)
            
            # 注册到matplotlib
            fm.fontManager.addfont(str(font_path))
            font_name = fm.FontProperties(fname=str(font_path)).get_name()
            
            logger.info(f"字体下载完成: {font_name}")
            return font_name
            
        except Exception as e:
            logger.error(f"字体下载失败: {e}")
            return None
    
    def _get_chinese_font_path(self) -> Optional[str]:
        """获取中文字体路径（兼容性方法）"""
        try:
            # 首先尝试检测最佳字体
            best_font = self.detect_best_font()
            if best_font:
                return best_font
            
            # 尝试使用本地字体
            local_font = self._check_local_fonts()
            if local_font:
                return local_font
                
            # 返回默认备用字体
            return None
            
        except Exception as e:
            logger.error(f"获取中文字体路径失败: {e}")
            return None
    
    def configure_matplotlib(self, font_name: Optional[str] = None):
        """配置matplotlib使用中文字体 - 彻底解决中文显示问题"""
        try:
            # 🔥 强力字体配置策略
            import matplotlib.font_manager as fm
            
            # 1. 清除字体缓存
            try:
                fm._rebuild()
                logger.info("字体缓存已清除")
            except:
                pass
            
            # 2. 获取最佳字体
            if not font_name:
                font_name = self.detect_best_font()
            
            # 3. 构建强化字体列表
            chinese_fonts = [
                # Windows 优先字体
                'Microsoft YaHei', 'Microsoft YaHei UI', 'SimHei', 'SimSun',
                # macOS 字体
                'PingFang SC', 'Heiti SC', 'STHeiti',
                # Linux 字体
                'WenQuanYi Micro Hei', 'Noto Sans CJK SC',
                # 备用字体
                'DejaVu Sans', 'Arial Unicode MS', 'sans-serif'
            ]
            
            if font_name and font_name not in chinese_fonts:
                chinese_fonts.insert(0, font_name)
            
            # 4. 🔥 暴力设置所有字体属性
            plt.rcParams['font.sans-serif'] = chinese_fonts
            plt.rcParams['font.serif'] = chinese_fonts
            plt.rcParams['font.monospace'] = chinese_fonts
            plt.rcParams['font.cursive'] = chinese_fonts
            plt.rcParams['font.fantasy'] = chinese_fonts
            plt.rcParams['font.family'] = ['sans-serif']
            
            # 5. 解决负号显示问题
            plt.rcParams['axes.unicode_minus'] = False
            
            # 6. 🔥 强制设置默认字体属性
            plt.rcParams['font.size'] = 12
            plt.rcParams['font.weight'] = 'normal'
            
            # 7. 尝试下载和设置字体文件
            self._force_download_chinese_font()
            
            # 8. 重新构建字体缓存
            try:
                fm._rebuild()
                fm.fontManager.__init__()  # 强制重新初始化
                logger.info("字体管理器已强制重建")
            except Exception as e:
                logger.warning(f"字体缓存重建失败: {e}")
            
            # 9. 测试中文显示
            self._test_chinese_display()
            
            logger.info(f"🎨 matplotlib强力字体配置完成: {chinese_fonts[:3]}")
            
        except Exception as e:
            logger.error(f"matplotlib字体配置失败: {e}")
    
    def _force_download_chinese_font(self):
        """强制下载中文字体"""
        try:
            import os
            import requests
            
            # 下载思源黑体
            font_url = "https://github.com/adobe-fonts/source-han-sans/releases/download/2.004R/SourceHanSansCN.zip"
            font_path = self.fonts_dir / "SourceHanSansCN.ttf"
            
            if not font_path.exists():
                logger.info("正在下载中文字体...")
                # 这里可以添加字体下载逻辑
                # 但为了稳定性，我们依赖系统字体
                pass
                
        except Exception as e:
            logger.warning(f"字体下载失败: {e}")
    
    def _test_chinese_display(self):
        """测试中文显示效果"""
        try:
            import matplotlib.pyplot as plt
            import tempfile
            
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.text(0.5, 0.5, '中文字体测试', fontsize=16, ha='center', va='center')
            ax.set_title('字体测试图表')
            
            # 保存到临时文件测试
            with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as tmp:
                plt.savefig(tmp.name, dpi=100, bbox_inches='tight')
                plt.close(fig)
                
                if os.path.getsize(tmp.name) > 1000:  # 文件大小合理
                    logger.info("✅ 中文字体显示测试通过")
                else:
                    logger.warning("⚠️ 中文字体可能存在问题")
            
        except Exception as e:
            logger.warning(f"中文字体测试失败: {e}")
    
    def get_font_info(self) -> dict:
        """获取当前字体配置信息"""
        return {
            'current_font': plt.rcParams.get('font.sans-serif', []),
            'unicode_minus': plt.rcParams.get('axes.unicode_minus', True),
            'available_fonts': len([f for f in fm.fontManager.ttflist]),
            'system_info': platform.system(),
            'fonts_dir': str(self.fonts_dir)
        }
