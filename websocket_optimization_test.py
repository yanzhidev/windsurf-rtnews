import asyncio
import json
import time
import websockets
import aiohttp
import statistics
from datetime import datetime
from typing import List, Dict, Any
import threading

class WebSocketOptimizationTester:
    def __init__(self, ws_url="ws://localhost:8000/ws", api_url="http://localhost:8000"):
        self.ws_url = ws_url
        self.api_url = api_url
        self.results = {
            'websocket_messages': 0,
            'websocket_errors': 0,
            'api_calls': 0,
            'api_errors': 0,
            'response_times': [],
            'message_intervals': [],
            'start_time': None,
            'end_time': None,
            'broadcast_stats': {}
        }
        self.lock = threading.Lock()
        
    async def websocket_client(self, client_id: int, duration: int = 30):
        """WebSocket客户端 - 专门测试优化效果"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print(f"🔌 优化测试客户端 {client_id} 已连接")
                
                start_time = time.time()
                last_message_time = start_time
                message_count = 0
                
                while time.time() - start_time < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        current_time = time.time()
                        
                        with self.lock:
                            self.results['websocket_messages'] += 1
                            message_count += 1
                            
                            # 记录消息间隔
                            interval = current_time - last_message_time
                            self.results['message_intervals'].append(interval)
                            last_message_time = current_time
                        
                        # 解析消息类型
                        try:
                            data = json.loads(message)
                            if data.get('type') == 'statistics':
                                # 提取广播统计信息
                                if 'broadcast_stats' in data.get('data', {}):
                                    self.results['broadcast_stats'] = data['data']['broadcast_stats']
                                    print(f"📊 客户端 {client_id} 收到统计更新: 广播总数={data['data']['broadcast_stats'].get('total_sent', 0)}")
                                else:
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
                        
                # 输出客户端统计
                elapsed = time.time() - start_time
                rate = message_count / elapsed if elapsed > 0 else 0
                print(f"📊 客户端 {client_id} 完成: {message_count} 消息, {rate:.2f} 消息/秒")
                        
        except Exception as e:
            with self.lock:
                self.results['websocket_errors'] += 1
            print(f"❌ WebSocket客户端 {client_id} 连接失败: {e}")
    
    async def api_client(self, client_id: int, requests_per_second: int = 5, duration: int = 30):
        """API客户端"""
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < duration and request_count < requests_per_second * duration:
                request_start = time.time()
                
                try:
                    async with session.get(f"{self.api_url}/api/stats") as response:
                        if response.status == 200:
                            data = await response.json()
                            response_time = time.time() - request_start
                            
                            with self.lock:
                                self.results['api_calls'] += 1
                                self.results['response_times'].append(response_time)
                                
                            # 检查优化指标
                            if 'broadcast_stats' in data:
                                stats = data['broadcast_stats']
                                print(f"🌐 API客户端 {client_id} 获取优化指标: 广播总数={stats.get('total_sent', 0)}, 批量大小={stats.get('avg_batch_size', 0):.1f}")
                                
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
    
    async def run_optimization_test(self, websocket_clients: int = 5, api_clients: int = 2, duration: int = 30):
        """运行WebSocket优化测试"""
        print(f"🚀 开始WebSocket优化效果测试")
        print(f"📊 WebSocket客户端: {websocket_clients}")
        print(f"🌐 API客户端: {api_clients}")
        print(f"⏱️ 测试时长: {duration}秒")
        print("-" * 60)
        
        self.results['start_time'] = datetime.now()
        
        # 创建任务列表
        tasks = []
        
        # WebSocket客户端任务
        for i in range(websocket_clients):
            tasks.append(asyncio.create_task(self.websocket_client(i, duration)))
        
        # API客户端任务
        for i in range(api_clients):
            tasks.append(asyncio.create_task(self.api_client(i, 5, duration)))
        
        # 等待所有任务完成
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            print(f"❌ 优化测试异常: {e}")
        
        self.results['end_time'] = datetime.now()
        
        # 打印测试结果
        self.print_optimization_results()
    
    def print_optimization_results(self):
        """打印优化测试结果"""
        print("\n" + "="*70)
        print("📊 WebSocket优化效果测试结果")
        print("="*70)
        
        duration = (self.results['end_time'] - self.results['start_time']).total_seconds()
        
        print(f"⏱️ 测试时长: {duration:.2f}秒")
        print(f"🔌 WebSocket消息接收: {self.results['websocket_messages']}")
        print(f"❌ WebSocket错误: {self.results['websocket_errors']}")
        print(f"🌐 API调用成功: {self.results['api_calls']}")
        print(f"❌ API错误: {self.results['api_errors']}")
        
        # 计算吞吐量
        ws_throughput = self.results['websocket_messages'] / duration if duration > 0 else 0
        api_throughput = self.results['api_calls'] / duration if duration > 0 else 0
        
        print(f"📊 WebSocket吞吐量: {ws_throughput:.2f} 消息/秒")
        print(f"🌐 API吞吐量: {api_throughput:.2f} 请求/秒")
        
        # 消息间隔分析
        if self.results['message_intervals']:
            avg_interval = statistics.mean(self.results['message_intervals'])
            min_interval = min(self.results['message_intervals'])
            max_interval = max(self.results['message_intervals'])
            
            print(f"\n📈 消息间隔分析:")
            print(f"  📊 平均间隔: {avg_interval:.3f}秒")
            print(f"  ⬇️ 最小间隔: {min_interval:.3f}秒")
            print(f"  ⬆️ 最大间隔: {max_interval:.3f}秒")
            
            # 计算消息频率
            frequency = 1 / avg_interval if avg_interval > 0 else 0
            print(f"  🚀 消息频率: {frequency:.2f} 消息/秒")
        
        # 广播统计信息
        if self.results['broadcast_stats']:
            stats = self.results['broadcast_stats']
            print(f"\n📡 广播优化统计:")
            print(f"  📊 广播总数: {stats.get('total_sent', 0)}")
            print(f"  ❌ 广播错误: {stats.get('total_errors', 0)}")
            print(f"  📦 平均批量大小: {stats.get('avg_batch_size', 0):.1f}")
            print(f"  ⏱️ 运行时间: {stats.get('uptime_seconds', 0):.1f}秒")
            
            if stats.get('uptime_seconds', 0) > 0:
                broadcast_rate = stats.get('total_sent', 0) / stats.get('uptime_seconds', 1)
                print(f"  🚀 广播速率: {broadcast_rate:.2f} 消息/秒")
        
        # 优化效果分析
        print(f"\n🔍 优化效果分析:")
        
        if ws_throughput > 100:
            print("  ✅ WebSocket吞吐量优秀 - 优化效果显著")
        elif ws_throughput > 50:
            print("  ⚠️ WebSocket吞吐量中等 - 优化有一定效果")
        else:
            print("  ❌ WebSocket吞吐量较低 - 需要进一步优化")
        
        # 与之前版本对比
        print(f"\n🆚 性能对比:")
        print(f"  📊 优化前WebSocket吞吐量: ~32 消息/秒")
        print(f"  📊 优化后WebSocket吞吐量: {ws_throughput:.2f} 消息/秒")
        
        if ws_throughput > 32:
            improvement = ((ws_throughput - 32) / 32) * 100
            print(f"  🚀 性能提升: {improvement:.1f}%")
        else:
            degradation = ((32 - ws_throughput) / 32) * 100
            print(f"  ⚠️ 性能下降: {degradation:.1f}%")
        
        # 批量广播效果
        if self.results['broadcast_stats']:
            avg_batch = self.results['broadcast_stats'].get('avg_batch_size', 0)
            if avg_batch > 5:
                print(f"  📦 批量广播效果: 平均批量大小 {avg_batch:.1f} - 优化有效")
            else:
                print(f"  ⚠️ 批量广播效果: 平均批量大小 {avg_batch:.1f} - 可能需要调整")
        
        print("="*70)

async def main():
    """主函数"""
    print("🚀 WebSocket优化效果测试工具")
    print("测试批量广播和连接管理优化")
    print("确保优化版服务器运行在 http://localhost:8000")
    print()
    
    tester = WebSocketOptimizationTester()
    
    try:
        await tester.run_optimization_test(
            websocket_clients=5,  # 5个WebSocket客户端
            api_clients=2,        # 2个API客户端
            duration=25           # 25秒测试
        )
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
