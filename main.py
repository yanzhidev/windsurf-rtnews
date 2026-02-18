"""
实时技术新闻聚合器 - 重构版
"""
import asyncio
import signal
import uvicorn
from fastapi import FastAPI
from collections import deque

# 导入自定义模块
from src.utils.config import APP_CONFIG, NEWS_CONFIG, BACKPRESSURE_CONFIG
from src.core.backpressure_controller import BackpressureController
from src.core.protected_news_processor import ProtectedNewsProcessor
from src.core.websocket_manager import WebSocketManager, WebSocketEndpoint
from src.core.news_stream_generator import NewsStreamGenerator
from src.api.routes import setup_routes


class NewsAggregatorApp:
    """实时新闻聚合应用主类"""
    
    def __init__(self):
        # 创建FastAPI应用
        self.app = FastAPI(
            title=APP_CONFIG['title'],
            version=APP_CONFIG['version']
        )
        
        # 初始化核心组件
        self.backpressure_controller = BackpressureController()
        self.news_processor = ProtectedNewsProcessor()
        self.ws_manager = WebSocketManager()
        self.news_buffer = deque(maxlen=NEWS_CONFIG['buffer_size'])
        
        # 初始化服务组件
        self.ws_endpoint = WebSocketEndpoint(self.ws_manager, self.news_processor)
        self.news_generator = NewsStreamGenerator(
            self.backpressure_controller,
            self.news_processor,
            self.ws_manager,
            self.news_buffer
        )
        
        # 设置路由
        setup_routes(self.app, self.ws_endpoint, self.news_processor, self.news_buffer)
    
    async def start_news_stream(self):
        """启动新闻流生成任务"""
        await self.news_generator.generate_protected_news_stream()
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            print(f"\n🛑 收到信号 {signum}，准备优雅关闭...")
            # 这里可以添加清理逻辑
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """运行应用"""
        print("� 启动实时技术新闻聚合器...")
        print("📡 正在启动新闻流生成器...")
        
        # 设置信号处理器
        self.setup_signal_handlers()
        
        # 启动新闻流生成任务
        asyncio.create_task(self.start_news_stream())
        
        print("🌐 启动FastAPI服务器...")
        print("📱 访问 http://localhost:8000 查看Web界面")
        print("📊 访问 http://localhost:8000/api/news 获取新闻API")
        print("📈 访问 http://localhost:8000/api/stats 获取统计API")
        
        print(f"🛡️ 内存限制: {BACKPRESSURE_CONFIG['max_memory_usage']/1024/1024}MB, "
              f"行大小限制: {BACKPRESSURE_CONFIG['max_line_size']/1024}KB")
        
        # 启动FastAPI服务器
        config = uvicorn.Config(
            self.app,
            host=APP_CONFIG['host'],
            port=APP_CONFIG['port'],
            log_level=APP_CONFIG['log_level']
        )
        server = uvicorn.Server(config)
        await server.serve()


async def main():
    """主函数"""
    app = NewsAggregatorApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
