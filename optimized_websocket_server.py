import json
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
from collections import deque
import threading

app = FastAPI(title="优化版 - 实时技术新闻聚合器", version="2.0.0")

# 存储活跃的WebSocket连接
active_connections: List[WebSocket] = []

# 存储最新的新闻 - 使用deque提高性能
news_buffer = deque(maxlen=1000)  # 增加缓冲区大小

# 广播队列和锁
broadcast_queue = asyncio.Queue()
connection_lock = asyncio.Lock()

# 性能统计
broadcast_stats = {
    'total_sent': 0,
    'total_errors': 0,
    'batch_sizes': deque(maxlen=100),
    'start_time': time.time()
}

class OptimizedNewsProcessor:
    def __init__(self):
        self.processed_count = 0
        self.categories_count = {}
        self.processing_times = deque(maxlen=100)  # 只保留最近100次
        
    def process_news(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """处理新闻数据"""
        start_time = time.time()
        
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            "total_processed": self.processed_count,
            "categories_distribution": dict(self.categories_count),
            "buffer_size": len(news_buffer),
            "avg_processing_time_ms": round(avg_processing_time * 1000, 2),
            "active_connections": len(active_connections),
            "broadcast_stats": {
                "total_sent": broadcast_stats['total_sent'],
                "total_errors": broadcast_stats['total_errors'],
                "avg_batch_size": sum(broadcast_stats['batch_sizes']) / len(broadcast_stats['batch_sizes']) if broadcast_stats['batch_sizes'] else 0,
                "uptime_seconds": time.time() - broadcast_stats['start_time']
            }
        }

# 全局新闻处理器
news_processor = OptimizedNewsProcessor()

class ConnectionManager:
    """优化的连接管理器"""
    
    def __init__(self):
        self.connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """连接WebSocket"""
        await websocket.accept()
        async with self._lock:
            self.connections.append(websocket)
        print(f"🔌 新连接，当前连接数: {len(self.connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        async with self._lock:
            if websocket in self.connections:
                self.connections.remove(websocket)
        print(f"🔌 连接断开，当前连接数: {len(self.connections)}")
    
    async def broadcast_batch(self, messages: List[str]):
        """批量广播消息"""
        if not self.connections:
            return
        
        start_time = time.time()
        batch_size = len(messages)
        
        async with self._lock:
            # 创建并发任务
            tasks = []
            for connection in self.connections:
                for message in messages:
                    tasks.append(self._safe_send(connection, message))
            
            # 并发执行所有发送任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计错误
            errors = sum(1 for result in results if isinstance(result, Exception))
            
        # 更新统计
        broadcast_stats['total_sent'] += (len(tasks) - errors)
        broadcast_stats['total_errors'] += errors
        broadcast_stats['batch_sizes'].append(batch_size)
        
        broadcast_time = time.time() - start_time
        if batch_size > 1:
            print(f"📡 批量广播 {batch_size} 条消息，耗时 {broadcast_time:.3f}s，错误 {errors} 个")
    
    async def _safe_send(self, websocket: WebSocket, message: str):
        """安全发送消息"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            return e  # 返回异常用于统计
        return None

# 全局连接管理器
manager = ConnectionManager()

class BroadcastWorker:
    """广播工作器 - 专门处理消息广播"""
    
    def __init__(self):
        self.running = True
        self.batch_size = 10  # 批量大小
        self.batch_timeout = 0.1  # 批量超时时间(秒)
    
    async def start(self):
        """启动广播工作器"""
        print(f"📡 启动广播工作器，批量大小: {self.batch_size}")
        
        while self.running:
            try:
                # 收集批量消息
                messages = []
                deadline = time.time() + self.batch_timeout
                
                while len(messages) < self.batch_size and time.time() < deadline:
                    try:
                        message = await asyncio.wait_for(broadcast_queue.get(), timeout=self.batch_timeout)
                        messages.append(message)
                    except asyncio.TimeoutError:
                        break
                
                # 如果有消息，批量发送
                if messages:
                    await manager.broadcast_batch(messages)
                
            except Exception as e:
                print(f"❌ 广播工作器错误: {e}")
                await asyncio.sleep(0.1)
    
    async def stop(self):
        """停止广播工作器"""
        self.running = False

# 全局广播工作器
broadcast_worker = BroadcastWorker()

async def generate_optimized_news_stream(news_per_second: int = 1000, duration: int = 30):
    """生成优化的新闻流"""
    try:
        print(f"📡 启动优化新闻生成器: {news_per_second}条/秒，持续{duration}秒")
        
        from high_freq_news import HighFreqNewsGenerator
        generator = HighFreqNewsGenerator()
        
        start_time = time.time()
        total_generated = 0
        broadcast_counter = 0
        
        while time.time() - start_time < duration:
            second_start = time.time()
            
            # 每秒生成指定数量的新闻
            for i in range(news_per_second):
                news_item = generator.generate_news_item()
                processed_news = news_processor.process_news(news_item)
                
                # 添加到缓冲区
                news_buffer.append(processed_news)
                total_generated += 1
                
                # 每10条新闻添加到广播队列（而不是立即广播）
                if total_generated % 10 == 0:
                    await broadcast_queue.put(json.dumps(processed_news, ensure_ascii=False))
                    broadcast_counter += 1
                
                # 每100条新闻广播统计信息
                if total_generated % 100 == 0:
                    stats_message = {
                        "type": "statistics",
                        "data": news_processor.get_statistics()
                    }
                    await broadcast_queue.put(json.dumps(stats_message, ensure_ascii=False))
                
                # 每1000条打印一次进度
                if total_generated % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = total_generated / elapsed
                    print(f"📰 已生成 {total_generated} 条新闻，速率: {rate:.2f}条/秒，广播 {broadcast_counter} 批次")
            
            # 控制每秒的时间
            second_elapsed = time.time() - second_start
            if second_elapsed < 1.0:
                await asyncio.sleep(1.0 - second_elapsed)
        
        total_time = time.time() - start_time
        actual_rate = total_generated / total_time
        
        print(f"✅ 优化新闻生成完成！")
        print(f"📊 总生成: {total_generated} 条")
        print(f"⏱️ 总耗时: {total_time:.2f} 秒")
        print(f"🚀 实际速率: {actual_rate:.2f} 条/秒")
        print(f"📡 广播批次: {broadcast_counter}")
        
    except Exception as e:
        print(f"❌ 优化新闻生成错误: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """优化的WebSocket端点"""
    await manager.connect(websocket)
    
    try:
        # 发送当前统计信息
        stats_message = {
            "type": "statistics",
            "data": news_processor.get_statistics()
        }
        await broadcast_queue.put(json.dumps(stats_message, ensure_ascii=False))
        
        # 保持连接
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket错误: {e}")
        await manager.disconnect(websocket)

@app.get("/")
async def get():
    """主页"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>优化版 - 实时技术新闻聚合器</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #27ae60; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .news-item { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .news-title { font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 8px; }
            .news-meta { color: #7f8c8d; font-size: 14px; margin-bottom: 8px; }
            .stats { background: #27ae60; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .performance { background: #3498db; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }
            .optimization { background: #e74c3c; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }
            .impact-high { border-left: 4px solid #e74c3c; }
            .impact-medium { border-left: 4px solid #f39c12; }
            .impact-low { border-left: 4px solid #27ae60; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 优化版 - 实时技术新闻聚合器</h1>
                <p>WebSocket广播优化测试界面</p>
            </div>
            
            <div class="stats" id="stats">
                <h3>📊 实时统计信息</h3>
                <p>总处理新闻数: <span id="total-count">0</span></p>
                <p>当前缓冲区: <span id="buffer-size">0</span></p>
                <p>活跃连接: <span id="active-connections">0</span></p>
                <p>平均处理时间: <span id="avg-processing-time">0</span>ms</p>
            </div>
            
            <div class="optimization" id="optimization">
                <h4>⚡ 优化指标</h4>
                <p>广播总数: <span id="broadcast-total">0</span></p>
                <p>广播错误: <span id="broadcast-errors">0</span></p>
                <p>平均批量大小: <span id="avg-batch-size">0</span></p>
                <p>广播速率: <span id="broadcast-rate">0</span> 消息/秒</p>
            </div>
            
            <div class="performance" id="performance">
                <h4>📈 性能指标</h4>
                <p>WebSocket消息速率: <span id="ws-rate">0</span> 消息/秒</p>
                <p>系统状态: <span id="system-status">正常</span></p>
            </div>
            
            <div id="news-container">
                <p>🔄 等待新闻数据...</p>
            </div>
        </div>
        
        <script>
            const ws = new WebSocket('ws://localhost:8000/ws');
            const newsContainer = document.getElementById('news-container');
            const totalCount = document.getElementById('total-count');
            const bufferSize = document.getElementById('buffer-size');
            const activeConnections = document.getElementById('active-connections');
            const avgProcessingTime = document.getElementById('avg-processing-time');
            const wsRate = document.getElementById('ws-rate');
            const systemStatus = document.getElementById('system-status');
            
            // 优化指标
            const broadcastTotal = document.getElementById('broadcast-total');
            const broadcastErrors = document.getElementById('broadcast-errors');
            const avgBatchSize = document.getElementById('avg-batch-size');
            const broadcastRate = document.getElementById('broadcast-rate');
            
            let messageCount = 0;
            let lastStatsTime = Date.now();
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                messageCount++;
                
                if (data.type === 'statistics') {
                    totalCount.textContent = data.data.total_processed;
                    bufferSize.textContent = data.data.buffer_size;
                    activeConnections.textContent = data.data.active_connections;
                    avgProcessingTime.textContent = data.data.avg_processing_time_ms;
                    
                    // 更新优化指标
                    if (data.data.broadcast_stats) {
                        broadcastTotal.textContent = data.data.broadcast_stats.total_sent;
                        broadcastErrors.textContent = data.data.broadcast_stats.total_errors;
                        avgBatchSize.textContent = data.data.broadcast_stats.avg_batch_size.toFixed(1);
                        
                        const uptime = data.data.broadcast_stats.uptime_seconds;
                        const rate = data.data.broadcast_stats.total_sent / uptime;
                        broadcastRate.textContent = rate.toFixed(2);
                    }
                    
                    // 计算消息速率
                    const now = Date.now();
                    const timeDiff = (now - lastStatsTime) / 1000;
                    if (timeDiff > 0) {
                        const rate = messageCount / timeDiff;
                        wsRate.textContent = rate.toFixed(2);
                        
                        // 系统状态判断
                        if (rate > 100) {
                            systemStatus.textContent = '高性能';
                            systemStatus.style.color = '#27ae60';
                        } else if (rate > 50) {
                            systemStatus.textContent = '正常';
                            systemStatus.style.color = '#f39c12';
                        } else {
                            systemStatus.textContent = '低性能';
                            systemStatus.style.color = '#e74c3c';
                        }
                    }
                    
                    messageCount = 0;
                    lastStatsTime = now;
                } else {
                    // 添加新闻到页面（限制显示数量）
                    if (newsContainer.children.length > 50) {
                        newsContainer.removeChild(newsContainer.lastChild);
                    }
                    
                    const newsDiv = document.createElement('div');
                    newsDiv.className = 'news-item';
                    
                    if (data.impact_score >= 7) {
                        newsDiv.className += ' impact-high';
                    } else if (data.impact_score >= 4) {
                        newsDiv.className += ' impact-medium';
                    } else {
                        newsDiv.className += ' impact-low';
                    }
                    
                    newsDiv.innerHTML = `
                        <div class="news-title">${data.title}</div>
                        <div class="news-meta">
                            📰 ${data.source} | 🏷️ ${data.category} | 🏢 ${data.company} | ⭐ ${data.impact_score}/10
                        </div>
                    `;
                    
                    newsContainer.insertBefore(newsDiv, newsContainer.firstChild);
                }
            };
            
            ws.onopen = function() {
                console.log('WebSocket连接已建立');
            };
            
            ws.onclose = function() {
                console.log('WebSocket连接已关闭');
                systemStatus.textContent = '连接断开';
                systemStatus.style.color = '#e74c3c';
            };
        </script>
    </body>
    </html>
    """)

@app.get("/api/news")
async def get_latest_news():
    """获取最新新闻API"""
    return {
        "news": list(news_buffer)[-50:],  # 返回最新50条
        "statistics": news_processor.get_statistics()
    }

@app.get("/api/stats")
async def get_statistics():
    """获取统计信息API"""
    return news_processor.get_statistics()

async def main():
    """主函数"""
    print("🚀 启动优化版实时技术新闻聚合器...")
    print("📡 正在启动优化新闻生成器和广播工作器...")
    
    # 启动广播工作器
    asyncio.create_task(broadcast_worker.start())
    
    # 启动优化新闻流生成任务
    asyncio.create_task(generate_optimized_news_stream(
        news_per_second=1000,  # 每秒1000条新闻
        duration=30            # 持续30秒
    ))
    
    print("🌐 启动FastAPI服务器...")
    print("📱 访问 http://localhost:8000 查看优化测试界面")
    print("📊 访问 http://localhost:8000/api/news 获取新闻API")
    print("📈 访问 http://localhost:8000/api/stats 获取统计API")
    
    # 启动FastAPI服务器
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
