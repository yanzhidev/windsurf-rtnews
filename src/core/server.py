import json
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
from collections import deque

app = FastAPI(title="持续优化版 - 实时技术新闻聚合器", version="2.2.0")

active_connections: List[WebSocket] = []
news_buffer = deque(maxlen=1000)
broadcast_buffer = []
last_broadcast_time = time.time()

broadcast_stats = {
    'total_sent': 0,
    'total_errors': 0,
    'batch_count': 0,
    'start_time': time.time()
}

class ContinuousOptimizedNewsProcessor:
    def __init__(self):
        self.processed_count = 0
        self.categories_count = {}
        self.processing_times = deque(maxlen=100)
        
    def process_news(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        self.processed_count += 1
        
        category = news_item.get('category', 'Unknown')
        self.categories_count[category] = self.categories_count.get(category, 0) + 1
        
        news_item['processed_at'] = datetime.now().isoformat()
        news_item['processing_id'] = self.processed_count
        
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        
        return news_item
    
    def get_statistics(self) -> Dict[str, Any]:
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
                "batch_count": broadcast_stats['batch_count'],
                "avg_batch_size": broadcast_stats['total_sent'] / max(broadcast_stats['batch_count'], 1),
                "uptime_seconds": time.time() - broadcast_stats['start_time']
            }
        }

news_processor = ContinuousOptimizedNewsProcessor()

async def optimized_broadcast_news(news_item: Dict[str, Any]):
    global broadcast_buffer, last_broadcast_time
    
    broadcast_buffer.append(news_item)
    current_time = time.time()
    
    if len(broadcast_buffer) >= 5 or current_time - last_broadcast_time > 0.2:
        await flush_broadcast_buffer()
        last_broadcast_time = current_time

async def flush_broadcast_buffer():
    global broadcast_buffer, broadcast_stats
    
    if not broadcast_buffer or not active_connections:
        return
    
    start_time = time.time()
    batch_size = len(broadcast_buffer)
    
    tasks = []
    for connection in active_connections:
        for news_item in broadcast_buffer:
            tasks.append(send_safe(connection, news_item))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = sum(1 for result in results if isinstance(result, Exception))
    success_count = len(tasks) - errors
    
    broadcast_stats['total_sent'] += success_count
    broadcast_stats['total_errors'] += errors
    broadcast_stats['batch_count'] += 1
    
    broadcast_time = time.time() - start_time
    
    print(f"📡 批量广播 {batch_size} 条到 {len(active_connections)} 客户端，耗时 {broadcast_time:.3f}s")
    
    broadcast_buffer.clear()

async def send_safe(websocket: WebSocket, news_item: Dict[str, Any]):
    try:
        message = json.dumps(news_item, ensure_ascii=False)
        await websocket.send_text(message)
    except Exception as e:
        return e
    return None

async def continuous_news_generator(news_per_second: int = 500):
    """持续新闻生成器"""
    print(f"📡 启动持续新闻生成器: {news_per_second}条/秒")
    
    from high_freq_news import HighFreqNewsGenerator
    generator = HighFreqNewsGenerator()
    
    stats_counter = 0
    
    while True:
        second_start = time.time()
        
        for i in range(news_per_second):
            news_item = generator.generate_news_item()
            processed_news = news_processor.process_news(news_item)
            
            news_buffer.append(processed_news)
            
            if processed_news['processing_id'] % 5 == 0:
                await optimized_broadcast_news(processed_news)
            
            if processed_news['processing_id'] % 50 == 0:
                await optimized_broadcast_statistics()
                stats_counter += 1
            
            if processed_news['processing_id'] % 500 == 0:
                elapsed = time.time() - (second_start - (processed_news['processing_id'] // news_per_second))
                rate = processed_news['processing_id'] / max(elapsed, 1)
                print(f"📰 已生成 {processed_news['processing_id']} 条，速率: {rate:.2f}条/秒")
        
        second_elapsed = time.time() - second_start
        if second_elapsed < 1.0:
            await asyncio.sleep(1.0 - second_elapsed)

async def optimized_broadcast_statistics():
    stats_message = {
        "type": "statistics",
        "data": news_processor.get_statistics()
    }
    
    if active_connections:
        tasks = []
        for connection in active_connections:
            tasks.append(send_safe(connection, stats_message))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = sum(1 for result in results if isinstance(result, Exception))
        
        broadcast_stats['total_sent'] += (len(tasks) - errors)
        broadcast_stats['total_errors'] += errors

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    print(f"🔌 新连接，当前: {len(active_connections)}")
    
    try:
        await optimized_broadcast_statistics()
        
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"🔌 断开，当前: {len(active_connections)}")
    except Exception as e:
        print(f"❌ WebSocket错误: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/")
async def get():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>持续优化版 - 实时新闻聚合器</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #27ae60; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .news-item { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stats { background: #27ae60; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .optimization { background: #3498db; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 持续优化版 - 实时新闻聚合器</h1>
                <p>WebSocket批量广播优化测试</p>
            </div>
            
            <div class="stats" id="stats">
                <h3>📊 实时统计</h3>
                <p>总处理: <span id="total-count">0</span></p>
                <p>连接数: <span id="active-connections">0</span></p>
                <p>广播总数: <span id="broadcast-total">0</span></p>
                <p>平均批量: <span id="avg-batch-size">0</span></p>
            </div>
            
            <div id="news-container">
                <p>🔄 等待新闻数据...</p>
            </div>
        </div>
        
        <script>
            const ws = new WebSocket('ws://localhost:8000/ws');
            const newsContainer = document.getElementById('news-container');
            let messageCount = 0;
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                messageCount++;
                
                if (data.type === 'statistics') {
                    document.getElementById('total-count').textContent = data.data.total_processed;
                    document.getElementById('active-connections').textContent = data.data.active_connections;
                    
                    if (data.data.broadcast_stats) {
                        document.getElementById('broadcast-total').textContent = data.data.broadcast_stats.total_sent;
                        document.getElementById('avg-batch-size').textContent = data.data.broadcast_stats.avg_batch_size.toFixed(1);
                    }
                } else {
                    if (newsContainer.children.length > 20) {
                        newsContainer.removeChild(newsContainer.lastChild);
                    }
                    
                    const newsDiv = document.createElement('div');
                    newsDiv.className = 'news-item';
                    newsDiv.innerHTML = `
                        <div><strong>${data.title}</strong></div>
                        <div style="color: #7f8c8d; font-size: 14px;">
                            ${data.source} | ${data.category} | ⭐ ${data.impact_score}/10
                        </div>
                    `;
                    
                    newsContainer.insertBefore(newsDiv, newsContainer.firstChild);
                }
            };
        </script>
    </body>
    </html>
    """)

@app.get("/api/stats")
async def get_statistics():
    return news_processor.get_statistics()

async def main():
    print("🚀 启动持续优化版实时新闻聚合器...")
    
    asyncio.create_task(continuous_news_generator(news_per_second=500))
    
    print("🌐 启动FastAPI服务器...")
    print("📱 访问 http://localhost:8000 查看界面")
    
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
