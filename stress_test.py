import asyncio
import json
import time
import websockets
import aiohttp
import statistics
from datetime import datetime
from typing import List, Dict, Any
import concurrent.futures
import threading

class StressTester:
    def __init__(self, ws_url="ws://localhost:8000/ws", api_url="http://localhost:8000"):
        self.ws_url = ws_url
        self.api_url = api_url
        self.results = {
            'websocket_messages': 0,
            'websocket_errors': 0,
            'api_calls': 0,
            'api_errors': 0,
            'response_times': [],
            'start_time': None,
            'end_time': None
        }
        self.lock = threading.Lock()
        
    async def websocket_client(self, client_id: int, duration: int = 30):
        """WebSocket客户端模拟"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print(f"🔌 WebSocket客户端 {client_id} 已连接")
                
                start_time = time.time()
                while time.time() - start_time < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        
                        with self.lock:
                            self.results['websocket_messages'] += 1
                            
                        # 解析消息类型
                        try:
                            data = json.loads(message)
                            if data.get('type') == 'statistics':
                                print(f"📊 客户端 {client_id} 收到统计更新")
                            else:
                                print(f"📰 客户端 {client_id} 收到新闻: {data.get('title', 'Unknown')[:30]}...")
                                
                        except json.JSONDecodeError:
                            print(f"⚠️ 客户端 {client_id} 收到非JSON消息")
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        with self.lock:
                            self.results['websocket_errors'] += 1
                        print(f"❌ WebSocket客户端 {client_id} 错误: {e}")
                        break
                        
        except Exception as e:
            with self.lock:
                self.results['websocket_errors'] += 1
            print(f"❌ WebSocket客户端 {client_id} 连接失败: {e}")
    
    async def api_client(self, client_id: int, requests_per_second: int = 10, duration: int = 30):
        """API客户端模拟"""
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < duration and request_count < requests_per_second * duration:
                request_start = time.time()
                
                try:
                    async with session.get(f"{self.api_url}/api/news") as response:
                        if response.status == 200:
                            data = await response.json()
                            response_time = time.time() - request_start
                            
                            with self.lock:
                                self.results['api_calls'] += 1
                                self.results['response_times'].append(response_time)
                                
                            print(f"🌐 API客户端 {client_id} 请求成功，响应时间: {response_time:.3f}s")
                        else:
                            with self.lock:
                                self.results['api_errors'] += 1
                            print(f"❌ API客户端 {client_id} HTTP错误: {response.status}")
                            
                except Exception as e:
                    with self.lock:
                        self.results['api_errors'] += 1
                    print(f"❌ API客户端 {client_id} 请求失败: {e}")
                
                request_count += 1
                await asyncio.sleep(1.0 / requests_per_second)
    
    async def generate_high_frequency_news(self, duration: int = 30):
        """生成高频新闻数据流"""
        print(f"🚀 开始生成高频新闻数据流 ({duration}秒)")
        
        # 导入新闻生成器
        from mock_stream import MockNewsStream
        stream = MockNewsStream()
        
        start_time = time.time()
        news_count = 0
        
        while time.time() - start_time < duration:
            # 每秒生成1000条新闻
            batch_start = time.time()
            
            for i in range(1000):
                news_item = stream.generate_news_item()
                news_count += 1
                
                # 每100条打印一次进度
                if news_count % 100 == 0:
                    print(f"📰 已生成 {news_count} 条新闻")
            
            # 控制每秒的批次
            batch_time = time.time() - batch_start
            if batch_time < 1.0:
                await asyncio.sleep(1.0 - batch_time)
        
        print(f"✅ 总共生成了 {news_count} 条新闻")
        return news_count
    
    async def run_stress_test(self, websocket_clients: int = 5, api_clients: int = 3, duration: int = 30):
        """运行压力测试"""
        print(f"🔥 开始压力测试")
        print(f"📊 WebSocket客户端: {websocket_clients}")
        print(f"🌐 API客户端: {api_clients}")
        print(f"⏱️ 测试时长: {duration}秒")
        print("-" * 50)
        
        self.results['start_time'] = datetime.now()
        
        # 创建任务列表
        tasks = []
        
        # WebSocket客户端任务
        for i in range(websocket_clients):
            tasks.append(asyncio.create_task(self.websocket_client(i, duration)))
        
        # API客户端任务
        for i in range(api_clients):
            tasks.append(asyncio.create_task(self.api_client(i, 10, duration)))
        
        # 高频新闻生成任务
        tasks.append(asyncio.create_task(self.generate_high_frequency_news(duration)))
        
        # 等待所有任务完成
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            print(f"❌ 压力测试异常: {e}")
        
        self.results['end_time'] = datetime.now()
        
        # 打印测试结果
        self.print_results()
    
    def print_results(self):
        """打印测试结果"""
        print("\n" + "="*60)
        print("📊 压力测试结果")
        print("="*60)
        
        duration = (self.results['end_time'] - self.results['start_time']).total_seconds()
        
        print(f"⏱️ 测试时长: {duration:.2f}秒")
        print(f"🔌 WebSocket消息接收: {self.results['websocket_messages']}")
        print(f"❌ WebSocket错误: {self.results['websocket_errors']}")
        print(f"🌐 API调用成功: {self.results['api_calls']}")
        print(f"❌ API错误: {self.results['api_errors']}")
        
        if self.results['response_times']:
            avg_response_time = statistics.mean(self.results['response_times'])
            max_response_time = max(self.results['response_times'])
            min_response_time = min(self.results['response_times'])
            
            print(f"📈 API平均响应时间: {avg_response_time:.3f}秒")
            print(f"⬆️ API最大响应时间: {max_response_time:.3f}秒")
            print(f"⬇️ API最小响应时间: {min_response_time:.3f}秒")
        
        # 计算吞吐量
        ws_throughput = self.results['websocket_messages'] / duration if duration > 0 else 0
        api_throughput = self.results['api_calls'] / duration if duration > 0 else 0
        
        print(f"📊 WebSocket吞吐量: {ws_throughput:.2f} 消息/秒")
        print(f"🌐 API吞吐量: {api_throughput:.2f} 请求/秒")
        
        # 性能分析
        print("\n🔍 性能分析:")
        if avg_response_time > 1.0:
            print("⚠️ API响应时间较长，可能存在性能瓶颈")
        if self.results['websocket_errors'] > 0:
            print("⚠️ WebSocket存在错误，可能连接不稳定")
        if ws_throughput < 100:
            print("⚠️ WebSocket吞吐量较低，可能存在阻塞")
        
        print("="*60)

async def main():
    """主函数"""
    print("🔥 FastAPI 压力测试工具")
    print("确保服务器运行在 http://localhost:8000")
    print()
    
    tester = StressTester()
    
    try:
        await tester.run_stress_test(
            websocket_clients=3,  # 3个WebSocket客户端
            api_clients=2,        # 2个API客户端
            duration=20           # 20秒测试
        )
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
