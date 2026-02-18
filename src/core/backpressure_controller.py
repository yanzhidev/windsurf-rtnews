"""
系统控制器模块
"""
import asyncio
import time
import os
import psutil
from collections import deque
from typing import Tuple
from src.utils.config import BACKPRESSURE_CONFIG


class BackpressureController:
    """背压控制器"""
    
    def __init__(self):
        self.processing_queue = asyncio.Queue(maxsize=BACKPRESSURE_CONFIG['max_queue_size'])
        self.is_paused = False
        self.pause_reason = None
        self.last_memory_check = time.time()
        self.processing_times = deque(maxlen=100)
        
    async def check_memory_usage(self) -> bool:
        """检查内存使用情况"""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb > BACKPRESSURE_CONFIG['max_memory_usage'] / 1024 / 1024:
                print(f"⚠️ 内存使用过高: {memory_mb:.1f}MB > {BACKPRESSURE_CONFIG['max_memory_usage']/1024/1024}MB")
                return True
            return False
        except Exception as e:
            print(f"❌ 内存检查失败: {e}")
            return False
    
    async def check_processing_delay(self) -> bool:
        """检查处理延迟"""
        if len(self.processing_times) < 10:
            return False
            
        avg_processing_time = sum(self.processing_times) / len(self.processing_times)
        
        if avg_processing_time > BACKPRESSURE_CONFIG['processing_delay_threshold']:
            print(f"⚠️ 处理延迟过高: {avg_processing_time:.3f}s > {BACKPRESSURE_CONFIG['processing_delay_threshold']}s")
            return True
        return False
    
    async def should_pause_processing(self) -> Tuple[bool, str]:
        """判断是否应该暂停处理"""
        # 检查内存使用
        if await self.check_memory_usage():
            return True, "内存使用过高"
        
        # 检查处理延迟
        if await self.check_processing_delay():
            return True, "处理延迟过高"
        
        # 检查队列大小
        if self.processing_queue.qsize() > BACKPRESSURE_CONFIG['max_queue_size'] * 0.8:
            return True, "队列接近满载"
        
        return False, ""
    
    async def pause_processing(self, reason: str):
        """暂停处理"""
        if not self.is_paused:
            self.is_paused = True
            self.pause_reason = reason
            print(f"🛑 暂停处理: {reason}")
    
    async def resume_processing(self):
        """恢复处理"""
        if self.is_paused:
            self.is_paused = False
            self.pause_reason = None
            print(f"▶️ 恢复处理")
    
    async def wait_for_resume(self):
        """等待背压缓解并自动恢复 - 统一的恢复逻辑"""
        while self.is_paused:
            await asyncio.sleep(0.1)
            should_pause, reason = await self.should_pause_processing()
            if not should_pause:
                await self.resume_processing()
                break

    def get_stats(self) -> dict:
        """获取背压控制器统计信息"""
        return {
            'queue_size': self.processing_queue.qsize(),
            'is_paused': self.is_paused,
            'pause_reason': self.pause_reason,
            'avg_processing_time': sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0,
            'memory_check_interval': BACKPRESSURE_CONFIG['memory_check_interval']
        }
