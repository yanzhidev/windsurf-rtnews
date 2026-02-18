"""
WebSocket管理器模块
"""
import asyncio
import json
import time
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from src.utils.config import WS_CONFIG


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.broadcast_stats = {
            'total_sent': 0,
            'total_errors': 0,
            'start_time': time.time(),
            'memory_protection_triggers': 0,
            'backpressure_events': 0
        }
    
    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 新连接，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"🔌 连接断开，当前连接数: {len(self.active_connections)}")
    
    async def send_safe(self, websocket: WebSocket, data: Dict[str, Any]) -> Exception:
        """安全发送消息"""
        try:
            message = json.dumps(data, ensure_ascii=False)
            await websocket.send_text(message)
            return None
        except Exception as e:
            return e
    
    async def broadcast_news(self, news_item: Dict[str, Any], backpressure_controller):
        """安全的新闻广播"""
        if not self.active_connections:
            return
        
        start_time = time.time()
        
        # 创建并发发送任务
        tasks = []
        for connection in self.active_connections:
            tasks.append(self.send_safe(connection, news_item))
        
        # 并发执行所有发送任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        errors = sum(1 for result in results if isinstance(result, Exception))
        success_count = len(tasks) - errors
        
        # 更新统计
        self.broadcast_stats['total_sent'] += success_count
        self.broadcast_stats['total_errors'] += errors
        
        broadcast_time = time.time() - start_time
        
        # 记录处理时间到背压控制器
        backpressure_controller.processing_times.append(broadcast_time)
        
        # 只在广播时间较长时打印日志
        if broadcast_time > 0.01:  # 超过10ms才打印
            print(f"📡 广播1条新闻到{len(self.active_connections)}客户端，耗时{broadcast_time:.3f}s，成功{success_count}，失败{errors}")
    
    async def broadcast_statistics(self, statistics: Dict[str, Any]):
        """安全的统计信息广播"""
        stats_message = {
            "type": "statistics",
            "data": statistics
        }
        
        if self.active_connections:
            tasks = []
            for connection in self.active_connections:
                tasks.append(self.send_safe(connection, stats_message))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            errors = sum(1 for result in results if isinstance(result, Exception))
            
            self.broadcast_stats['total_sent'] += (len(tasks) - errors)
            self.broadcast_stats['total_errors'] += errors
    
    def get_stats(self) -> Dict[str, Any]:
        """获取WebSocket统计信息"""
        return {
            'active_connections': len(self.active_connections),
            'broadcast_stats': {
                "total_sent": self.broadcast_stats['total_sent'],
                "total_errors": self.broadcast_stats['total_errors'],
                "memory_protection_triggers": self.broadcast_stats['memory_protection_triggers'],
                "backpressure_events": self.broadcast_stats['backpressure_events'],
                "uptime_seconds": time.time() - self.broadcast_stats['start_time']
            }
        }


class WebSocketEndpoint:
    """WebSocket端点处理器"""
    
    def __init__(self, ws_manager: WebSocketManager, news_processor):
        self.ws_manager = ws_manager
        self.news_processor = news_processor
    
    async def handle_websocket(self, websocket: WebSocket):
        """WebSocket端点处理"""
        await self.ws_manager.connect(websocket)
        
        try:
            # 发送当前统计信息
            stats = self.news_processor.get_statistics(
                buffer_size=0,  # 将在main中传入
                active_connections=len(self.ws_manager.active_connections),
                broadcast_stats=self.ws_manager.broadcast_stats
            )
            await self.ws_manager.broadcast_statistics(stats)
            
            # 保持连接
            while True:
                await websocket.receive_text()
                
        except WebSocketDisconnect:
            self.ws_manager.disconnect(websocket)
        except Exception as e:
            print(f"❌ WebSocket错误: {e}")
            self.ws_manager.disconnect(websocket)
