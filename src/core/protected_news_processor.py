"""
新闻处理器模块
"""
import json
import time
from datetime import datetime
from collections import deque
from typing import Dict, Any, Optional, List
from src.utils.config import NEWS_CONFIG, BACKPRESSURE_CONFIG


class ProtectedNewsProcessor:
    """受保护的新闻处理器"""
    
    def __init__(self):
        self.processed_count = 0
        self.categories_count = {}
        self.processing_times = deque(maxlen=100)
        self.rejected_count = 0
        
    def process_news(self, news_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理新闻数据 - 带验证和大小限制"""
        start_time = time.time()
        
        try:
            # 验证必要字段
            required_fields = ['title', 'source', 'category', 'company']
            for field in required_fields:
                if field not in news_item or not news_item[field]:
                    print(f"⚠️ 缺少必要字段: {field}")
                    self.rejected_count += 1
                    return None
            
            # 检查数据大小
            json_size = len(json.dumps(news_item))
            if json_size > 100 * 1024:  # 100KB 限制
                print(f"⚠️ 新闻数据过大: {json_size} bytes")
                self.rejected_count += 1
                return None
            
            self.processed_count += 1
            
            # 统计分类
            category = news_item.get('category', 'Unknown')
            self.categories_count[category] = self.categories_count.get(category, 0) + 1
            
            # 添加处理时间戳
            news_item['processed_at'] = datetime.now().isoformat()
            news_item['processing_id'] = self.processed_count
            
            # 记录处理时间
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            
            return news_item
            
        except Exception as e:
            print(f"❌ 新闻处理错误: {e}")
            self.rejected_count += 1
            return None
    
    def get_statistics(self, buffer_size: int = 0, active_connections: int = 0, broadcast_stats: dict = None) -> Dict[str, Any]:
        """获取处理统计信息"""
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            "total_processed": self.processed_count,
            "rejected_count": self.rejected_count,
            "categories_distribution": dict(self.categories_count),
            "buffer_size": buffer_size,
            "avg_processing_time_ms": round(avg_processing_time * 1000, 2),
            "active_connections": active_connections,
            "broadcast_stats": broadcast_stats or {}
        }


class SafeStreamReader:
    """安全的流读取器 - 带背压控制和内存保护"""
    
    def __init__(self, backpressure_controller):
        self.backpressure_controller = backpressure_controller
        self.lines_processed = 0
        self.bytes_processed = 0
        self.errors_count = 0
        
    async def read_line_safe(self, reader) -> Optional[str]:
        """安全读取一行 - 带大小限制"""
        try:
            # 检查背压
            should_pause, reason = await self.backpressure_controller.should_pause_processing()
            if should_pause:
                await self.backpressure_controller.pause_processing(reason)
                # 使用统一的恢复逻辑
                await self.backpressure_controller.wait_for_resume()
            
            # 读取行数据，带大小限制
            line = await reader.readline()
            
            if not line:
                return None
            
            # 检查行大小
            line_size = len(line)
            if line_size > BACKPRESSURE_CONFIG['max_line_size']:
                print(f"⚠️ 行过大: {line_size} bytes > {BACKPRESSURE_CONFIG['max_line_size']} bytes")
                self.errors_count += 1
                return None  # 跳过过大的行
            
            # 解码并验证JSON
            try:
                line_str = line.decode('utf-8').strip()
                
                # 验证JSON格式
                if line_str and line_str.startswith('{'):
                    json.loads(line_str)  # 验证JSON有效性
                
                self.lines_processed += 1
                self.bytes_processed += line_size
                
                return line_str
                
            except UnicodeDecodeError as e:
                print(f"⚠️ 编码错误: {e}")
                self.errors_count += 1
                return None
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON解析错误: {e}")
                self.errors_count += 1
                return None
                
        except Exception as e:
            print(f"❌ 读取错误: {e}")
            self.errors_count += 1
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取读取统计"""
        return {
            'lines_processed': self.lines_processed,
            'bytes_processed': self.bytes_processed,
            'errors_count': self.errors_count,
            'current_queue_size': self.backpressure_controller.processing_queue.qsize(),
            'is_paused': self.backpressure_controller.is_paused,
            'pause_reason': self.backpressure_controller.pause_reason
        }
