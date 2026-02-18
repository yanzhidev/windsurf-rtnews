import json
import asyncio
import subprocess
import sys
from typing import Dict, Any
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="实时技术新闻聚合器", version="1.0.0")

# 存储活跃的WebSocket连接
active_connections: list[WebSocket] = []

# 存储最新的新闻
news_buffer: list[Dict[str, Any]] = []
MAX_BUFFER_SIZE = 50

class NewsProcessor:
    def __init__(self):
        self.processed_count = 0
        self.categories_count = {}
        
    def process_news(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """处理新闻数据"""
        self.processed_count += 1
        
        # 统计分类
        category = news_item.get('category', 'Unknown')
        self.categories_count[category] = self.categories_count.get(category, 0) + 1
        
        # 添加处理时间戳
        news_item['processed_at'] = datetime.now().isoformat()
        news_item['processing_id'] = self.processed_count
        
        return news_item
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return {
            "total_processed": self.processed_count,
            "categories_distribution": self.categories_count,
            "buffer_size": len(news_buffer)
        }

# 全局新闻处理器
news_processor = NewsProcessor()

async def generate_news_stream():
    """直接生成新闻流"""
    try:
        print("📡 News generator started")
        
        # 导入 MockNewsStream
        from mock_stream import MockNewsStream
        stream = MockNewsStream()
        
        while True:
            # 生成新闻
            news_item = stream.generate_news_item()
            processed_news = news_processor.process_news(news_item)
            
            # 添加到缓冲区
            news_buffer.append(processed_news)
            if len(news_buffer) > MAX_BUFFER_SIZE:
                news_buffer.pop(0)
            
            # 打印到控制台
            print(f"📰 [{processed_news['processing_id']}] {processed_news['title']}")
            print(f"   来源: {processed_news['source']} | 分类: {processed_news['category']}")
            print(f"   影响力: {processed_news['impact_score']}/10")
            print("-" * 60)
            
            # 广播给所有WebSocket客户端
            await broadcast_news(processed_news)
            
            # 广播更新的统计信息
            await broadcast_statistics()
            
            # 等待3秒
            await asyncio.sleep(3)
            
    except Exception as e:
        print(f"❌ Error generating news stream: {e}")

async def broadcast_news(news_item: Dict[str, Any]):
    """向所有连接的客户端广播新闻"""
    if active_connections:
        disconnected_clients = []
        for connection in active_connections:
            try:
                await connection.send_text(json.dumps(news_item, ensure_ascii=False))
            except:
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
            except:
                disconnected_clients.append(connection)
        
        # 移除断开的连接
        for client in disconnected_clients:
            active_connections.remove(client)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点"""
    await websocket.accept()
    active_connections.append(websocket)
    
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

@app.get("/")
async def get():
    """主页"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>实时技术新闻聚合器</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .news-item { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .news-title { font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 8px; }
            .news-meta { color: #7f8c8d; font-size: 14px; margin-bottom: 8px; }
            .news-summary { color: #34495e; line-height: 1.5; }
            .stats { background: #3498db; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .impact-high { border-left: 4px solid #e74c3c; }
            .impact-medium { border-left: 4px solid #f39c12; }
            .impact-low { border-left: 4px solid #27ae60; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 实时技术新闻聚合器</h1>
                <p>实时接收和展示最新的技术新闻</p>
            </div>
            
            <div class="stats" id="stats">
                <h3>📊 统计信息</h3>
                <p>总处理新闻数: <span id="total-count">0</span></p>
                <p>当前缓冲区: <span id="buffer-size">0</span></p>
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
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'statistics') {
                    totalCount.textContent = data.data.total_processed;
                    bufferSize.textContent = data.data.buffer_size;
                } else {
                    // 添加新闻到页面
                    const newsDiv = document.createElement('div');
                    newsDiv.className = 'news-item';
                    
                    // 根据影响力设置样式
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
                        <div class="news-summary">${data.summary}</div>
                    `;
                    
                    // 插入到顶部
                    newsContainer.insertBefore(newsDiv, newsContainer.firstChild);
                    
                    // 限制显示数量
                    while (newsContainer.children.length > 20) {
                        newsContainer.removeChild(newsContainer.lastChild);
                    }
                }
            };
            
            ws.onopen = function() {
                console.log('WebSocket连接已建立');
            };
            
            ws.onclose = function() {
                console.log('WebSocket连接已关闭');
            };
        </script>
    </body>
    </html>
    """)

@app.get("/api/news")
async def get_latest_news():
    """获取最新新闻API"""
    return {
        "news": news_buffer[-10:],  # 返回最新10条
        "statistics": news_processor.get_statistics()
    }

@app.get("/api/stats")
async def get_statistics():
    """获取统计信息API"""
    return news_processor.get_statistics()

async def main():
    """主函数"""
    print("🚀 启动实时技术新闻聚合器...")
    print("📡 正在启动新闻流生成器...")
    
    # 启动新闻流生成任务
    asyncio.create_task(generate_news_stream())
    
    print("🌐 启动FastAPI服务器...")
    print("📱 访问 http://localhost:8000 查看Web界面")
    print("📊 访问 http://localhost:8000/api/news 获取新闻API")
    print("📈 访问 http://localhost:8000/api/stats 获取统计API")
    
    # 启动FastAPI服务器
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
