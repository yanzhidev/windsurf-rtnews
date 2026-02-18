import asyncio
import json
import time
import websockets
import aiohttp
import statistics
import multiprocessing
import threading
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import queue
import sys

class MultiProcessStressTester:
    def __init__(self, ws_url="ws://localhost:8000/ws", api_url="http://localhost:8000"):
        self.ws_url = ws_url
        self.api_url = api_url
        self.results = multiprocessing.Manager().dict({
            'websocket_messages': 0,
            'websocket_errors': 0,
            'api_calls': 0,
            'api_errors': 0,
            'response_times': multiprocessing.Manager().list(),
            'start_time': None,
            'end_time': None,
            'process_results': multiprocessing.Manager().dict()
        })
        
    def websocket_worker(self, worker_id: int, duration: int, result_queue: multiprocessing.Queue):
        """独立的WebSocket工作进程"""
        try:
            async def websocket_client():
                try:
                    async with websockets.connect(self.ws_url) as websocket:
                        print(f"🔌 WebSocket工作进程 {worker_id} 已连接")
                        
                        start_time = time.time()
                        local_messages = 0
                        local_errors = 0
                        
                        while time.time() - start_time < duration:
                            try:
                                message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                                local_messages += 1
                                
                                # 解析消息类型
                                try:
                                    data = json.loads(message)
                                    if data.get('type') == 'statistics':
                                        pass  # 统计消息不打印
                                    else:
                                        print(f"📰 进程 {worker_id} 收到新闻: {data.get('title', 'Unknown')[:30]}...")
                                        
                                except json.JSONDecodeError:
                                    local_errors += 1
                                    
                            except asyncio.TimeoutError:
                                continue
                            except Exception as e:
                                local_errors += 1
                                print(f"❌ WebSocket进程 {worker_id} 错误: {e}")
                                break
                        
                        # 返回结果到主进程
                        result_queue.put({
                            'worker_id': worker_id,
                            'type': 'websocket',
                            'messages': local_messages,
                            'errors': local_errors
                        })
                        
                except Exception as e:
                    print(f"❌ WebSocket进程 {worker_id} 连接失败: {e}")
                    result_queue.put({
                        'worker_id': worker_id,
                        'type': 'websocket',
                        'messages': 0,
                        'errors': 1
                    })
            
            # 运行异步客户端
            asyncio.run(websocket_client())
            
        except Exception as e:
            print(f"❌ WebSocket工作进程 {worker_id} 异常: {e}")
    
    def api_worker(self, worker_id: int, requests_per_second: int, duration: int, result_queue: multiprocessing.Queue):
        """独立的API工作进程"""
        try:
            async def api_client():
                async with aiohttp.ClientSession() as session:
                    start_time = time.time()
                    request_count = 0
                    local_calls = 0
                    local_errors = 0
                    local_response_times = []
                    
                    while time.time() - start_time < duration and request_count < requests_per_second * duration:
                        request_start = time.time()
                        
                        try:
                            async with session.get(f"{self.api_url}/api/news") as response:
                                if response.status == 200:
                                    await response.json()
                                    response_time = time.time() - request_start
                                    
                                    local_calls += 1
                                    local_response_times.append(response_time)
                                    
                                    print(f"🌐 API进程 {worker_id} 请求成功，响应时间: {response_time:.3f}s")
                                else:
                                    local_errors += 1
                                    print(f"❌ API进程 {worker_id} HTTP错误: {response.status}")
                                    
                        except Exception as e:
                            local_errors += 1
                            print(f"❌ API进程 {worker_id} 请求失败: {e}")
                        
                        request_count += 1
                        await asyncio.sleep(1.0 / requests_per_second)
                    
                    # 返回结果到主进程
                    result_queue.put({
                        'worker_id': worker_id,
                        'type': 'api',
                        'calls': local_calls,
                        'errors': local_errors,
                        'response_times': local_response_times
                    })
            
            asyncio.run(api_client())
            
        except Exception as e:
            print(f"❌ API工作进程 {worker_id} 异常: {e}")
    
    def news_generator_worker(self, news_per_second: int, duration: int, result_queue: multiprocessing.Queue):
        """独立的新闻生成工作进程"""
        try:
            from high_freq_news import HighFreqNewsGenerator
            generator = HighFreqNewsGenerator()
            
            print(f"🚀 新闻生成进程启动: {news_per_second}条/秒，持续{duration}秒")
            
            start_time = time.time()
            total_generated = 0
            
            while time.time() - start_time < duration:
                second_start = time.time()
                
                # 每秒生成指定数量的新闻
                for i in range(news_per_second):
                    news_item = generator.generate_news_item()
                    total_generated += 1
                
                # 控制每秒的时间
                second_elapsed = time.time() - second_start
                if second_elapsed < 1.0:
                    time.sleep(1.0 - second_elapsed)
                
                # 每1000条打印一次进度
                if total_generated % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = total_generated / elapsed
                    print(f"📰 生成进程已生成 {total_generated} 条新闻，速率: {rate:.2f}条/秒")
            
            total_time = time.time() - start_time
            actual_rate = total_generated / total_time
            
            print(f"✅ 新闻生成完成！总计: {total_generated} 条，实际速率: {actual_rate:.2f} 条/秒")
            
            # 返回结果到主进程
            result_queue.put({
                'worker_id': 0,
                'type': 'news_generator',
                'total_generated': total_generated,
                'actual_rate': actual_rate,
                'total_time': total_time
            })
            
        except Exception as e:
            print(f"❌ 新闻生成进程异常: {e}")
    
    def run_multi_process_stress_test(self, websocket_clients: int = 5, api_clients: int = 3, 
                                   news_per_second: int = 1000, duration: int = 30):
        """运行多进程压力测试"""
        print(f"🔥 开始多进程压力测试 (解决GIL问题)")
        print(f"📊 WebSocket工作进程: {websocket_clients}")
        print(f"🌐 API工作进程: {api_clients}")
        print(f"📰 新闻生成进程: 1个 ({news_per_second}条/秒)")
        print(f"⏱️ 测试时长: {duration}秒")
        print(f"🔧 总工作进程数: {websocket_clients + api_clients + 1}个")
        print("-" * 60)
        
        self.results['start_time'] = datetime.now()
        
        # 创建结果队列
        result_queue = multiprocessing.Queue()
        
        # 创建进程池
        processes = []
        
        # 启动WebSocket工作进程
        for i in range(websocket_clients):
            p = multiprocessing.Process(
                target=self.websocket_worker,
                args=(i, duration, result_queue)
            )
            p.start()
            processes.append(p)
            print(f"🚀 启动WebSocket工作进程 {i}")
        
        # 启动API工作进程
        for i in range(api_clients):
            p = multiprocessing.Process(
                target=self.api_worker,
                args=(i, 10, duration, result_queue)
            )
            p.start()
            processes.append(p)
            print(f"🚀 启动API工作进程 {i}")
        
        # 启动新闻生成工作进程
        p = multiprocessing.Process(
            target=self.news_generator_worker,
            args=(news_per_second, duration, result_queue)
        )
        p.start()
        processes.append(p)
        print(f"🚀 启动新闻生成工作进程")
        
        print(f"\n⏳ 所有工作进程已启动，等待测试完成...")
        
        # 收集结果
        collected_results = {
            'websocket': {'messages': 0, 'errors': 0, 'processes': []},
            'api': {'calls': 0, 'errors': 0, 'response_times': [], 'processes': []},
            'news_generator': {'total_generated': 0, 'actual_rate': 0}
        }
        
        # 等待所有进程完成并收集结果
        for _ in range(len(processes)):
            try:
                result = result_queue.get(timeout=duration + 10)  # 额外10秒超时
                result_type = result['type']
                
                if result_type == 'websocket':
                    collected_results['websocket']['messages'] += result['messages']
                    collected_results['websocket']['errors'] += result['errors']
                    collected_results['websocket']['processes'].append(result)
                    
                elif result_type == 'api':
                    collected_results['api']['calls'] += result['calls']
                    collected_results['api']['errors'] += result['errors']
                    collected_results['api']['response_times'].extend(result['response_times'])
                    collected_results['api']['processes'].append(result)
                    
                elif result_type == 'news_generator':
                    collected_results['news_generator']['total_generated'] = result['total_generated']
                    collected_results['news_generator']['actual_rate'] = result['actual_rate']
                    
            except queue.Empty:
                print("⚠️ 等待工作进程结果超时")
                break
        
        # 等待所有进程结束
        for p in processes:
            p.join(timeout=5)
            if p.is_alive():
                print(f"⚠️ 强制终止进程 {p.pid}")
                p.terminate()
                p.join()
        
        self.results['end_time'] = datetime.now()
        
        # 更新结果
        self.results['websocket_messages'] = collected_results['websocket']['messages']
        self.results['websocket_errors'] = collected_results['websocket']['errors']
        self.results['api_calls'] = collected_results['api']['calls']
        self.results['api_errors'] = collected_results['api']['errors']
        self.results['response_times'] = collected_results['api']['response_times']
        self.results['process_results'] = collected_results
        
        # 打印测试结果
        self.print_multi_process_results(collected_results)
    
    def print_multi_process_results(self, collected_results):
        """打印多进程测试结果"""
        print("\n" + "="*70)
        print("📊 多进程压力测试结果")
        print("="*70)
        
        duration = (self.results['end_time'] - self.results['start_time']).total_seconds()
        
        print(f"⏱️ 测试时长: {duration:.2f}秒")
        print(f"🔧 使用工作进程数: {len(collected_results['websocket']['processes']) + len(collected_results['api']['processes']) + 1}个")
        
        print(f"\n📌 WebSocket进程结果:")
        for proc in collected_results['websocket']['processes']:
            print(f"  进程 {proc['worker_id']}: {proc['messages']} 消息, {proc['errors']} 错误")
        print(f"  📊 WebSocket总计: {collected_results['websocket']['messages']} 消息, {collected_results['websocket']['errors']} 错误")
        
        print(f"\n📌 API进程结果:")
        for proc in collected_results['api']['processes']:
            avg_time = sum(proc['response_times']) / len(proc['response_times']) if proc['response_times'] else 0
            print(f"  进程 {proc['worker_id']}: {proc['calls']} 调用, {proc['errors']} 错误, 平均响应: {avg_time:.3f}s")
        print(f"  📊 API总计: {collected_results['api']['calls']} 调用, {collected_results['api']['errors']} 错误")
        
        print(f"\n📌 新闻生成进程结果:")
        print(f"  📊 总生成: {collected_results['news_generator']['total_generated']} 条")
        print(f"  🚀 实际速率: {collected_results['news_generator']['actual_rate']:.2f} 条/秒")
        
        if collected_results['api']['response_times']:
            avg_response_time = statistics.mean(collected_results['api']['response_times'])
            max_response_time = max(collected_results['api']['response_times'])
            min_response_time = min(collected_results['api']['response_times'])
            
            print(f"\n📈 API响应时间统计:")
            print(f"  📊 平均响应时间: {avg_response_time:.3f}秒")
            print(f"  ⬆️ 最大响应时间: {max_response_time:.3f}秒")
            print(f"  ⬇️ 最小响应时间: {min_response_time:.3f}秒")
        
        # 计算吞吐量
        ws_throughput = collected_results['websocket']['messages'] / duration if duration > 0 else 0
        api_throughput = collected_results['api']['calls'] / duration if duration > 0 else 0
        
        print(f"\n🚀 吞吐量统计:")
        print(f"  📊 WebSocket吞吐量: {ws_throughput:.2f} 消息/秒")
        print(f"  🌐 API吞吐量: {api_throughput:.2f} 请求/秒")
        
        # 性能分析
        print(f"\n🔍 多进程性能分析:")
        if ws_throughput > 100:
            print("  ✅ WebSocket吞吐量优秀 (多进程有效)")
        elif ws_throughput > 50:
            print("  ⚠️ WebSocket吞吐量中等")
        else:
            print("  ❌ WebSocket吞吐量较低")
            
        if avg_response_time < 0.01:
            print("  ✅ API响应时间优秀")
        elif avg_response_time < 0.05:
            print("  ⚠️ API响应时间中等")
        else:
            print("  ❌ API响应时间较慢")
        
        print(f"\n🆚 GIL对比分析:")
        print(f"  📊 多进程WebSocket吞吐量: {ws_throughput:.2f} 消息/秒")
        print(f"  📊 单进程WebSocket吞吐量: ~32 消息/秒 (之前测试)")
        if ws_throughput > 32:
            improvement = ((ws_throughput - 32) / 32) * 100
            print(f"  🚀 性能提升: {improvement:.1f}%")
        
        print("="*70)

async def main():
    """主函数"""
    print("🔥 多进程 FastAPI 压力测试工具")
    print("解决GIL问题的真正并发压力测试")
    print("确保服务器运行在 http://localhost:8000")
    print()
    
    tester = MultiProcessStressTester()
    
    try:
        tester.run_multi_process_stress_test(
            websocket_clients=5,     # 5个WebSocket工作进程
            api_clients=3,           # 3个API工作进程
            news_per_second=1000,     # 1000条/秒新闻生成
            duration=20               # 20秒测试
        )
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    # 设置多进程启动方法
    if sys.platform.startswith('darwin'):  # macOS
        multiprocessing.set_start_method('spawn', force=True)
    elif sys.platform.startswith('win'):  # Windows
        multiprocessing.set_start_method('spawn', force=True)
    
    asyncio.run(main())
