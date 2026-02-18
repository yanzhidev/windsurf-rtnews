"""
API路由模块
"""
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from src.core.websocket_manager import WebSocketEndpoint
from src.utils.config import APP_CONFIG


def create_html_page() -> str:
    """创建HTML页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>背压保护版 - 实时技术新闻聚合器</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #9b59b6; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .news-item { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .news-title { font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 8px; }
            .news-meta { color: #7f8c8d; font-size: 14px; margin-bottom: 8px; }
            .stats { background: #9b59b6; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .protection { background: #e74c3c; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }
            .backpressure { background: #f39c12; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }
            .impact-high { border-left: 4px solid #e74c3c; }
            .impact-medium { border-left: 4px solid #f39c12; }
            .impact-low { border-left: 4px solid #27ae60; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛡️ 背压保护版 - 实时技术新闻聚合器</h1>
                <p>内存保护 + 背压控制 + 安全流读取</p>
            </div>
            
            <div class="stats" id="stats">
                <h3>📊 实时统计信息</h3>
                <p>总处理新闻数: <span id="total-count">0</span></p>
                <p>拒绝处理数: <span id="rejected-count">0</span></p>
                <p>当前缓冲区: <span id="buffer-size">0</span></p>
                <p>活跃连接: <span id="active-connections">0</span></p>
                <p>平均处理时间: <span id="avg-processing-time">0</span>ms</p>
            </div>
            
            <div class="protection" id="protection">
                <h4>🛡️ 内存保护</h4>
                <p>内存保护触发: <span id="memory-triggers">0</span> 次</p>
                <p>广播错误: <span id="broadcast-errors">0</span></p>
            </div>
            
            <div class="backpressure" id="backpressure">
                <h4>🛑 背压控制</h4>
                <p>背压事件: <span id="backpressure-events">0</span> 次</p>
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
            const rejectedCount = document.getElementById('rejected-count');
            const bufferSize = document.getElementById('buffer-size');
            const activeConnections = document.getElementById('active-connections');
            const avgProcessingTime = document.getElementById('avg-processing-time');
            const systemStatus = document.getElementById('system-status');
            
            // 保护指标
            const memoryTriggers = document.getElementById('memory-triggers');
            const broadcastErrors = document.getElementById('broadcast-errors');
            const backpressureEvents = document.getElementById('backpressure-events');
            
            let messageCount = 0;
            let lastStatsTime = Date.now();
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                messageCount++;
                
                if (data.type === 'statistics') {
                    totalCount.textContent = data.data.total_processed;
                    rejectedCount.textContent = data.data.rejected_count;
                    bufferSize.textContent = data.data.buffer_size;
                    activeConnections.textContent = data.data.active_connections;
                    avgProcessingTime.textContent = data.data.avg_processing_time_ms;
                    
                    // 更新保护指标
                    if (data.data.broadcast_stats) {
                        memoryTriggers.textContent = data.data.broadcast_stats.memory_protection_triggers;
                        broadcastErrors.textContent = data.data.broadcast_stats.total_errors;
                        backpressureEvents.textContent = data.data.broadcast_stats.backpressure_events;
                    }
                    
                    // 计算消息速率
                    const now = Date.now();
                    const timeDiff = (now - lastStatsTime) / 1000;
                    if (timeDiff > 0) {
                        const rate = messageCount / timeDiff;
                        
                        // 系统状态判断
                        if (data.data.broadcast_stats.backpressure_events > 0) {
                            systemStatus.textContent = '背压激活';
                            systemStatus.style.color = '#e74c3c';
                        } else if (data.data.broadcast_stats.memory_protection_triggers > 0) {
                            systemStatus.textContent = '内存保护';
                            systemStatus.style.color = '#f39c12';
                        } else if (rate > 50) {
                            systemStatus.textContent = '高性能';
                            systemStatus.style.color = '#27ae60';
                        } else {
                            systemStatus.textContent = '正常';
                            systemStatus.style.color = '#3498db';
                        }
                    }
                    
                    messageCount = 0;
                    lastStatsTime = now;
                } else {
                    // 添加新闻到页面（限制显示数量）
                    if (newsContainer.children.length > 20) {
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
    """


def setup_routes(app: FastAPI, ws_endpoint: WebSocketEndpoint, news_processor, news_buffer):
    """设置API路由"""
    
    @app.get("/")
    async def get():
        """主页 - 安全版"""
        return HTMLResponse(create_html_page())

    @app.get("/api/news")
    async def get_latest_news():
        """获取最新新闻API"""
        return {
            "news": list(news_buffer)[-10:],  # 返回最新10条
            "statistics": news_processor.get_statistics(
                buffer_size=len(news_buffer),
                active_connections=0,  # 将在调用时传入
                broadcast_stats={}  # 将在调用时传入
            )
        }

    @app.get("/api/stats")
    async def get_statistics():
        """获取统计信息API"""
        return news_processor.get_statistics(
            buffer_size=len(news_buffer),
            active_connections=0,  # 将在调用时传入
            broadcast_stats={}  # 将在调用时传入
        )

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket端点 - 安全版"""
        await ws_endpoint.handle_websocket(websocket)
