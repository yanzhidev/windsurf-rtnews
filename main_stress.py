import json
import asyncio
import sys
from typing import Dict, Any
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="压力测试版 - 实时技术新闻聚合器", version="1.0.0")

# 存储活跃的WebSocket连接
active_connections: list[WebSocket] = []

# 存储最新的新闻
news_buffer: list[Dict[str, Any]] = []
MAX_BUFFER_SIZE = 1000  # 增加缓冲区大小用于压力测试

class NewsProcessor:
    def __init__(self):
        self.processed_count = 0
        self.categories_count = {}
        self.processing_times = []
        
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
        avg_processing_time = sum(self.processing_times[-100:]) / min(len(self.processing_times), 100) if self.processing_times else 0
        
        return {
            "total_processed": self.processed_count,
            "categories_distribution": self.categories_count,
            "buffer_size": len(news_buffer),
            "avg_processing_time_ms": round(avg_processing_time * 1000, 2),
            "active_connections": len(active_connections)
        }

# 全局新闻处理器
news_processor = NewsProcessor()

async def generate_high_freq_news_stream(news_per_second: int = 1000, duration: int = 30):
    """生成高频新闻流"""
    try:
        print(f"📡 启动高频新闻生成器: {news_per_second}条/秒，持续{duration}秒")
        
        # 导入高频新闻生成器
        from high_freq_news import HighFreqNewsGenerator
        generator = HighFreqNewsGenerator()
        
        start_time = time.time()
        total_generated = 0
        
        while time.time() - start_time < duration:
            second_start = time.time()
            
            # 每秒生成指定数量的新闻
            for i in range(news_per_second):
                news_item = generator.generate_news_item()
                processed_news = news_processor.process_news(news_item)
                
                # 添加到缓冲区
                news_buffer.append(processed_news)
                if len(news_buffer) > MAX_BUFFER_SIZE:
                    news_buffer.pop(0)
                
                total_generated += 1
                
                # 每100条新闻广播一次（避免过度广播）
                if total_generated % 100 == 0:
                    await broadcast_news(processed_news)
                    await broadcast_statistics()
                
                # 每1000条打印一次进度
                if total_generated % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = total_generated / elapsed
                    print(f"📰 已生成 {total_generated} 条新闻，速率: {rate:.2f}条/秒")
            
            # 控制每秒的时间
            second_elapsed = time.time() - second_start
            if second_elapsed < 1.0:
                await asyncio.sleep(1.0 - second_elapsed)
        
        total_time = time.time() - start_time
        actual_rate = total_generated / total_time
        
        print(f"✅ 高频新闻生成完成！")
        print(f"📊 总生成: {total_generated} 条")
        print(f"⏱️ 总耗时: {total_time:.2f} 秒")
        print(f"🚀 实际速率: {actual_rate:.2f} 条/秒")
        
    except Exception as e:
        print(f"❌ 高频新闻生成错误: {e}")

async def broadcast_news(news_item: Dict[str, Any]):
    """向所有连接的客户端广播新闻"""
    if active_connections:
        disconnected_clients = []
        
        for connection in active_connections:
            try:
                await connection.send_text(json.dumps(news_item, ensure_ascii=False))
            except Exception as e:
                print(f"⚠️ WebSocket发送失败: {e}")
                disconnected_clients.append(connection)
        
        # 移除断开的连接
        for client in disconnected_clients:
            active_connections.remove(client)

async def broadcast_statistics():
    """向所有连接的客户端广播统计信息"""
    if active_connections:
        disconnected_clients = []
        stats_message = {
            "type": "statistics",
            "data": news_processor.get_statistics()
        }
        
        for connection in active_connections:
            try:
                await connection.send_text(json.dumps(stats_message, ensure_ascii=False))
            except Exception as e:
                print(f"⚠️ 统计信息发送失败: {e}")
                disconnected_clients.append(connection)
        
        # 移除断开的连接
        for client in disconnected_clients:
            active_connections.remove(client)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点"""
    await websocket.accept()
    active_connections.append(websocket)
    print(f"🔌 新的WebSocket连接，当前连接数: {len(active_connections)}")
    
    try:
        # 发送当前统计信息
        await websocket.send_text(json.dumps({
            "type": "statistics",
            "data": news_processor.get_statistics()
        }))
        
        # 保持连接
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"🔌 WebSocket连接断开，当前连接数: {len(active_connections)}")
    except Exception as e:
        print(f"❌ WebSocket错误: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/")
async def get():
    """主页"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>压力测试版 - 实时技术新闻聚合器</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .news-item { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .news-title { font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 8px; }
            .news-meta { color: #7f8c8d; font-size: 14px; margin-bottom: 8px; }
            .news-summary { color: #34495e; line-height: 1.5; }
            .stats { background: #e74c3c; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .impact-high { border-left: 4px solid #e74c3c; }
            .impact-medium { border-left: 4px solid #f39c12; }
            .impact-low { border-left: 4px solid #27ae60; }
            .performance { background: #3498db; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔥 压力测试版 - 实时技术新闻聚合器</h1>
                <p>高频新闻流压力测试界面</p>
            </div>
            
            <div class="stats" id="stats">
                <h3>📊 实时统计信息</h3>
                <p>总处理新闻数: <span id="total-count">0</span></p>
                <p>当前缓冲区: <span id="buffer-size">0</span></p>
                <p>活跃连接: <span id="active-connections">0</span></p>
                <p>平均处理时间: <span id="avg-processing-time">0</span>ms</p>
            </div>
            
            <div class="performance" id="performance">
                <h4>⚡ 性能指标</h4>
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
                    
                    // 计算消息速率
                    const now = Date.now();
                    const timeDiff = (now - lastStatsTime) / 1000;
                    if (timeDiff > 0) {
                        const rate = messageCount / timeDiff;
                        wsRate.textContent = rate.toFixed(2);
                        
                        // 系统状态判断
                        if (rate > 50) {
                            systemStatus.textContent = '高负载';
                            systemStatus.style.color = '#e74c3c';
                        } else if (rate > 10) {
                            systemStatus.textContent = '中等负载';
                            systemStatus.style.color = '#f39c12';
                        } else {
                            systemStatus.textContent = '正常';
                            systemStatus.style.color = '#27ae60';
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
        "news": news_buffer[-50:],  # 返回最新50条
        "statistics": news_processor.get_statistics()
    }

@app.get("/api/stats")
async def get_statistics():
    """获取统计信息API"""
    return news_processor.get_statistics()

async def main():
    """主函数"""
    print("🔥 启动压力测试版实时技术新闻聚合器...")
    print("📡 正在启动高频新闻生成器...")
    
    # 启动高频新闻流生成任务
    asyncio.create_task(generate_high_freq_news_stream(
        news_per_second=1000,  # 每秒1000条新闻
        duration=30            # 持续30秒
    ))
    
    print("🌐 启动FastAPI服务器...")
    print("📱 访问 http://localhost:8000 查看压力测试界面")
    print("📊 访问 http://localhost:8000/api/news 获取新闻API")
    print("📈 访问 http://localhost:8000/api/stats 获取统计API")
    
    # 启动FastAPI服务器
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    import time
    asyncio.run(main())
