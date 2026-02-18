import json
import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
from collections import deque
import sys
import signal
import psutil
import os

app = FastAPI(title="背压保护版 - 实时技术新闻聚合器", version="1.3.0")

# 存储活跃的WebSocket连接
active_connections: List[WebSocket] = []

# 存储最新的新闻 - 使用deque提高性能
news_buffer = deque(maxlen=1000)

# 性能统计
broadcast_stats = {
    'total_sent': 0,
    'total_errors': 0,
    'start_time': time.time(),
    'memory_protection_triggers': 0,
    'backpressure_events': 0
}

# 背压控制配置
BACKPRESSURE_CONFIG = {
    'max_line_size': 1 * 1024 * 1024,  # 1MB 最大行大小
    'max_memory_usage': 200 * 1024 * 1024,  # 200MB 最大内存使用
    'max_queue_size': 10000,  # 最大队列大小
    'processing_delay_threshold': 0.1,  # 处理延迟阈值(秒)
    'memory_check_interval': 5,  # 内存检查间隔(秒)
    'graceful_shutdown_timeout': 10  # 优雅关闭超时(秒)
}

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
    
    async def should_pause_processing(self) -> tuple[bool, str]:
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
            broadcast_stats['backpressure_events'] += 1
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

class SafeStreamReader:
    """安全的流读取器 - 带背压控制和内存保护"""
    
    def __init__(self, backpressure_controller: BackpressureController):
        self.backpressure_controller = backpressure_controller
        self.lines_processed = 0
        self.bytes_processed = 0
        self.errors_count = 0
        
    async def read_line_safe(self, reader: asyncio.StreamReader) -> Optional[str]:
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
                broadcast_stats['memory_protection_triggers'] += 1
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            "total_processed": self.processed_count,
            "rejected_count": self.rejected_count,
            "categories_distribution": dict(self.categories_count),
            "buffer_size": len(news_buffer),
            "avg_processing_time_ms": round(avg_processing_time * 1000, 2),
            "active_connections": len(active_connections),
            "broadcast_stats": {
                "total_sent": broadcast_stats['total_sent'],
                "total_errors": broadcast_stats['total_errors'],
                "memory_protection_triggers": broadcast_stats['memory_protection_triggers'],
                "backpressure_events": broadcast_stats['backpressure_events'],
                "uptime_seconds": time.time() - broadcast_stats['start_time']
            }
        }

# 全局组件
backpressure_controller = BackpressureController()
news_processor = ProtectedNewsProcessor()

async def safe_broadcast_news(news_item: Dict[str, Any]):
    """安全的新闻广播"""
    if not active_connections:
        return
    
    start_time = time.time()
    
    # 创建并发发送任务
    tasks = []
    for connection in active_connections:
        tasks.append(send_safe(connection, news_item))
    
    # 并发执行所有发送任务
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 统计结果
    errors = sum(1 for result in results if isinstance(result, Exception))
    success_count = len(tasks) - errors
    
    # 更新统计
    broadcast_stats['total_sent'] += success_count
    broadcast_stats['total_errors'] += errors
    
    broadcast_time = time.time() - start_time
    
    # 记录处理时间到背压控制器
    backpressure_controller.processing_times.append(broadcast_time)
    
    # 只在广播时间较长时打印日志
    if broadcast_time > 0.01:  # 超过10ms才打印
        print(f"📡 广播1条新闻到{len(active_connections)}客户端，耗时{broadcast_time:.3f}s，成功{success_count}，失败{errors}")

async def send_safe(websocket: WebSocket, news_item: Dict[str, Any]):
    """安全发送消息"""
    try:
        message = json.dumps(news_item, ensure_ascii=False)
        await websocket.send_text(message)
    except Exception as e:
        return e  # 返回异常用于统计
    return None

async def safe_broadcast_statistics():
    """安全的统计信息广播"""
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

async def generate_protected_news_stream():
    """生成受保护的新闻流"""
    try:
        print("📡 启动受保护的新闻生成器...")
        
        from high_freq_news import HighFreqNewsGenerator
        generator = HighFreqNewsGenerator()
        
        duration = 30  # 30秒测试
        news_per_second = 1000  # 每秒1000条
        
        start_time = time.time()
        total_generated = 0
        stats_counter = 0
        memory_check_counter = 0
        
        while time.time() - start_time < duration:
            second_start = time.time()
            
            # 检查背压状态 - 使用统一的等待逻辑
            if backpressure_controller.is_paused:
                print(f"⏸️ 处理已暂停: {backpressure_controller.pause_reason}")
                await backpressure_controller.wait_for_resume()
            
            # 每秒生成指定数量的新闻
            for i in range(news_per_second):
                # 检查背压
                if backpressure_controller.is_paused:
                    break
                
                news_item = generator.generate_news_item()
                processed_news = news_processor.process_news(news_item)
                
                if processed_news:
                    # 添加到缓冲区
                    news_buffer.append(processed_news)
                    total_generated += 1
                    
                    # 安全的广播
                    await safe_broadcast_news(processed_news)
                    
                    # 每100条新闻广播统计信息
                    if processed_news['processing_id'] % 100 == 0:
                        await safe_broadcast_statistics()
                        stats_counter += 1
                    
                    # 每1000条打印一次进度
                    if processed_news['processing_id'] % 1000 == 0:
                        elapsed = time.time() - start_time
                        rate = total_generated / elapsed
                        print(f"📰 已生成 {total_generated} 条新闻，速率: {rate:.2f}条/秒，统计广播: {stats_counter} 次")
            
            # 定期检查内存使用
            memory_check_counter += 1
            if memory_check_counter % BACKPRESSURE_CONFIG['memory_check_interval'] == 0:
                memory_high = await backpressure_controller.check_memory_usage()
                if memory_high:
                    await backpressure_controller.pause_processing("内存使用过高")
                    # 强制垃圾回收
                    import gc
                    gc.collect()
            
            # 控制每秒的时间
            second_elapsed = time.time() - second_start
            if second_elapsed < 1.0:
                await asyncio.sleep(1.0 - second_elapsed)
        
        total_time = time.time() - start_time
        actual_rate = total_generated / total_time
        
        print(f"✅ 受保护新闻生成完成！")
        print(f"📊 总生成: {total_generated} 条")
        print(f"⏱️ 总耗时: {total_time:.2f} 秒")
        print(f"🚀 实际速率: {actual_rate:.2f} 条/秒")
        print(f"📡 统计广播: {stats_counter} 次")
        print(f"🛡️ 拒绝处理: {news_processor.rejected_count} 条")
        print(f"⚠️ 内存保护触发: {broadcast_stats['memory_protection_triggers']} 次")
        print(f"🛑 背压事件: {broadcast_stats['backpressure_events']} 次")
        
    except Exception as e:
        print(f"❌ Error generating news stream: {e}")

async def safe_read_news_stream():
    """安全读取新闻流 - 带背压控制"""
    try:
        print("📡 启动安全新闻流读取器...")
        
        # 启动 mock_stream.py 作为子进程
        process = await asyncio.create_subprocess_exec(
            sys.executable, 'mock_stream.py',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        reader = SafeStreamReader(backpressure_controller)
        
        print("📡 安全流读取器已启动")
        
        while True:
            # 安全读取一行
            line = await reader.read_line_safe(process.stdout)
            
            if line is None:
                # 检查进程是否结束
                if process.returncode is not None:
                    print(f"📡 新闻流进程结束，退出码: {process.returncode}")
                    break
                continue
            
            # 处理有效的JSON行
            if line and line.startswith('{'):
                try:
                    news_item = json.loads(line)
                    processed_news = news_processor.process_news(news_item)
                    
                    if processed_news:
                        # 添加到缓冲区
                        news_buffer.append(processed_news)
                        
                        # 安全广播
                        await safe_broadcast_news(processed_news)
                        
                        # 定期广播统计信息
                        if processed_news['processing_id'] % 10 == 0:
                            await safe_broadcast_statistics()
                        
                        # 打印进度
                        if processed_news['processing_id'] % 100 == 0:
                            print(f"📰 处理新闻 [{processed_news['processing_id']}] {processed_news['title'][:50]}...")
                            
                except json.JSONDecodeError:
                    continue
                    
            # 定期打印读取统计
            if reader.lines_processed % 1000 == 0 and reader.lines_processed > 0:
                stats = reader.get_stats()
                print(f"📊 读取统计: {stats['lines_processed']} 行, {stats['bytes_processed']} 字节, {stats['errors_count']} 错误")
                
    except Exception as e:
        print(f"❌ 安全流读取错误: {e}")
    finally:
        # 确保子进程被清理
        if 'process' in locals():
            process.terminate()
            await process.wait()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点 - 安全版"""
    await websocket.accept()
    active_connections.append(websocket)
    print(f"🔌 新连接，当前连接数: {len(active_connections)}")
    
    try:
        # 发送当前统计信息
        await safe_broadcast_statistics()
        
        # 保持连接
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"🔌 连接断开，当前连接数: {len(active_connections)}")
    except Exception as e:
        print(f"❌ WebSocket错误: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/")
async def get():
    """主页 - 安全版"""
    return HTMLResponse("""
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
    """)

@app.get("/api/news")
async def get_latest_news():
    """获取最新新闻API"""
    return {
        "news": list(news_buffer)[-10:],  # 返回最新10条
        "statistics": news_processor.get_statistics()
    }

@app.get("/api/stats")
async def get_statistics():
    """获取统计信息API"""
    return news_processor.get_statistics()

async def main():
    """主函数"""
    print("🛡️ 启动背压保护版实时技术新闻聚合器...")
    print("📡 正在启动受保护的新闻流生成器...")
    
    # 设置信号处理器
    def signal_handler(signum, frame):
        print(f"\n🛑 收到信号 {signum}，准备优雅关闭...")
        # 这里可以添加清理逻辑
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动新闻流生成任务
    asyncio.create_task(generate_protected_news_stream())
    
    print("🌐 启动FastAPI服务器...")
    print("📱 访问 http://localhost:8000 查看保护版Web界面")
    print("📊 访问 http://localhost:8000/api/news 获取新闻API")
    print("📈 访问 http://localhost:8000/api/stats 获取统计API")
    print("🛡️ 内存限制: 200MB, 行大小限制: 1MB")
    
    # 启动FastAPI服务器
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
