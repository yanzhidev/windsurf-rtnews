import asyncio
import json
import time
import websockets
import statistics
from datetime import datetime
from typing import List, Dict, Any

class WebSocketFixTester:
    def __init__(self, ws_url="ws://localhost:8000/ws"):
        self.ws_url = ws_url
        self.results = {
            'websocket_messages': 0,
            'websocket_errors': 0,
            'message_intervals': [],
            'start_time': None,
            'end_time': None,
            'broadcast_stats': {},
            'performance_samples': []
        }
        
    async def websocket_client(self, client_id: int, duration: int = 30):
        """WebSocket客户端 - 测试修复效果"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print(f"🔌 修复测试客户端 {client_id} 已连接")
                
                start_time = time.time()
                last_message_time = start_time
                message_count = 0
                
                while time.time() - start_time < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        current_time = time.time()
                        
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
                                    
                                    # 记录性能样本
                                    performance_sample = {
                                        'timestamp': current_time,
                                        'total_sent': data['data']['broadcast_stats'].get('total_sent', 0),
                                        'avg_batch_size': data['data']['broadcast_stats'].get('avg_batch_size', 0),
                                        'uptime': data['data']['broadcast_stats'].get('uptime_seconds', 0)
                                    }
                                    self.results['performance_samples'].append(performance_sample)
                                    
                                print(f"📊 客户端 {client_id} 收到统计更新")
                            else:
                                print(f"📰 客户端 {client_id} 收到新闻: {data.get('title', 'Unknown')[:30]}...")
                                
                        except json.JSONDecodeError:
                            print(f"⚠️ 客户端 {client_id} 收到非JSON消息")
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        self.results['websocket_errors'] += 1
                        print(f"❌ WebSocket客户端 {client_id} 错误: {e}")
                        break
                        
                # 输出客户端统计
                elapsed = time.time() - start_time
                rate = message_count / elapsed if elapsed > 0 else 0
                print(f"📊 客户端 {client_id} 完成: {message_count} 消息, {rate:.2f} 消息/秒")
                        
        except Exception as e:
            self.results['websocket_errors'] += 1
            print(f"❌ WebSocket客户端 {client_id} 连接失败: {e}")
    
    async def run_fix_test(self, websocket_clients: int = 3, duration: int = 30):
        """运行WebSocket修复效果测试"""
        print(f"🔧 开始WebSocket修复效果测试")
        print(f"📊 WebSocket客户端: {websocket_clients}")
        print(f"⏱️ 测试时长: {duration}秒")
        print("-" * 60)
        
        self.results['start_time'] = datetime.now()
        
        # 创建任务列表
        tasks = []
        
        # WebSocket客户端任务
        for i in range(websocket_clients):
            tasks.append(asyncio.create_task(self.websocket_client(i, duration)))
        
        # 等待所有任务完成
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            print(f"❌ 修复测试异常: {e}")
        
        self.results['end_time'] = datetime.now()
        
        # 打印测试结果
        self.print_fix_results()
    
    def print_fix_results(self):
        """打印修复测试结果"""
        print("\n" + "="*70)
        print("📊 WebSocket修复效果测试结果")
        print("="*70)
        
        duration = (self.results['end_time'] - self.results['start_time']).total_seconds()
        
        print(f"⏱️ 测试时长: {duration:.2f}秒")
        print(f"🔌 WebSocket消息接收: {self.results['websocket_messages']}")
        print(f"❌ WebSocket错误: {self.results['websocket_errors']}")
        
        # 计算吞吐量
        ws_throughput = self.results['websocket_messages'] / duration if duration > 0 else 0
        
        print(f"📊 WebSocket吞吐量: {ws_throughput:.2f} 消息/秒")
        
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
        
        # 性能趋势分析
        if len(self.results['performance_samples']) > 1:
            print(f"\n📈 性能趋势分析:")
            samples = self.results['performance_samples']
            
            # 计算广播速率趋势
            first_sample = samples[0]
            last_sample = samples[-1]
            
            if last_sample['uptime'] > first_sample['uptime']:
                time_diff = last_sample['uptime'] - first_sample['uptime']
                sent_diff = last_sample['total_sent'] - first_sample['total_sent']
                avg_rate = sent_diff / time_diff
                
                print(f"  📊 平均广播速率: {avg_rate:.2f} 消息/秒")
                print(f"  📦 批量大小趋势: {first_sample['avg_batch_size']:.1f} → {last_sample['avg_batch_size']:.1f}")
        
        # 修复效果分析
        print(f"\n🔍 修复效果分析:")
        
        if ws_throughput > 10:
            print("  ✅ WebSocket吞吐量优秀 - 修复效果显著")
        elif ws_throughput > 5:
            print("  ⚠️ WebSocket吞吐量中等 - 修复有一定效果")
        else:
            print("  ❌ WebSocket吞吐量较低 - 需要进一步优化")
        
        # 与原始版本对比
        print(f"\n🆚 性能对比:")
        print(f"  📊 原始版本WebSocket吞吐量: ~0.33 消息/秒 (每3秒1条)")
        print(f"  📊 修复版本WebSocket吞吐量: {ws_throughput:.2f} 消息/秒")
        
        if ws_throughput > 0.33:
            improvement = ((ws_throughput - 0.33) / 0.33) * 100
            print(f"  🚀 性能提升: {improvement:.1f}%")
        else:
            degradation = ((0.33 - ws_throughput) / 0.33) * 100
            print(f"  ⚠️ 性能下降: {degradation:.1f}%")
        
        # 批量广播效果
        if self.results['broadcast_stats']:
            avg_batch = self.results['broadcast_stats'].get('avg_batch_size', 0)
            if avg_batch > 1:
                print(f"  📦 批量广播效果: 平均批量大小 {avg_batch:.1f} - 优化有效")
            else:
                print(f"  ⚠️ 批量广播效果: 平均批量大小 {avg_batch:.1f} - 可能需要调整")
        
        print("="*70)

async def main():
    """主函数"""
    print("🔧 WebSocket修复效果测试工具")
    print("测试批量广播和并发发送优化")
    print("确保修复版服务器运行在 http://localhost:8000")
    print()
    
    tester = WebSocketFixTester()
    
    try:
        await tester.run_fix_test(
            websocket_clients=3,  # 3个WebSocket客户端
            duration=25           # 25秒测试
        )
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
