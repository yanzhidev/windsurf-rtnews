"""
WebSocket压力测试
"""
import asyncio
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
import websockets
from concurrent.futures import ThreadPoolExecutor

from stress_test_framework import StressTestFramework, TestResult
from stress_test_config import STRESS_CONFIG


class WebSocketStressTester:
    """WebSocket压力测试器"""
    
    def __init__(self, framework: StressTestFramework):
        self.framework = framework
        self.logger = logging.getLogger("websocket_stress_test")
        self.active_connections = []
        self.connection_stats = {
            'total_connections': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'total_messages': 0,
            'connection_errors': []
        }
    
    async def single_websocket_client(self, client_id: int, duration: int, 
                                    message_interval: float = 0.1) -> Dict[str, Any]:
        """单个WebSocket客户端"""
        connection_start = time.time()
        stats = {
            'client_id': client_id,
            'connection_time': 0,
            'messages_received': 0,
            'total_bytes_received': 0,
            'errors': [],
            'connected': False,
            'connection_duration': 0
        }
        
        try:
            # 记录连接开始时间
            connect_start = time.time()
            
            async with websockets.connect(
                self.framework.config.ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                connect_time = time.time() - connect_start
                stats['connection_time'] = connect_time
                stats['connected'] = True
                
                self.logger.debug(f"客户端 {client_id} 连接成功，耗时 {connect_time:.3f}s")
                
                # 监听消息
                while time.time() - connection_start < duration:
                    try:
                        # 设置接收超时
                        message = await asyncio.wait_for(
                            websocket.recv(), timeout=1.0
                        )
                        
                        # 统计消息
                        stats['messages_received'] += 1
                        stats['total_bytes_received'] += len(message.encode('utf-8'))
                        
                        # 验证消息格式
                        try:
                            message_data = json.loads(message)
                            if not isinstance(message_data, dict):
                                stats['errors'].append(f"客户端 {client_id}: 收到非JSON对象消息")
                        except json.JSONDecodeError:
                            stats['errors'].append(f"客户端 {client_id}: 收到无效JSON消息")
                        
                        self.logger.debug(f"客户端 {client_id} 收到消息 #{stats['messages_received']}")
                        
                    except asyncio.TimeoutError:
                        # 超时是正常的，继续监听
                        continue
                    except websockets.exceptions.ConnectionClosed as e:
                        stats['errors'].append(f"客户端 {client_id}: 连接意外关闭 - {e}")
                        break
                    except Exception as e:
                        stats['errors'].append(f"客户端 {client_id}: 接收消息错误 - {e}")
                        break
                    
                    await asyncio.sleep(message_interval)
                
                stats['connection_duration'] = time.time() - connection_start
                
        except websockets.exceptions.InvalidURI:
            stats['errors'].append(f"客户端 {client_id}: 无效的WebSocket URI")
        except websockets.exceptions.ConnectionClosed:
            stats['errors'].append(f"客户端 {client_id}: 连接被拒绝或关闭")
        except Exception as e:
            stats['errors'].append(f"客户端 {client_id}: 连接失败 - {e}")
        
        return stats
    
    async def concurrent_websocket_test(self, num_clients: int, duration: int, 
                                     message_interval: float = 0.1) -> TestResult:
        """并发WebSocket连接测试"""
        self.logger.info(f"开始并发WebSocket测试: {num_clients}个客户端，持续{duration}秒")
        
        start_time = time.time()
        
        # 启动系统监控
        monitor_task = asyncio.create_task(
            self.framework.monitor_system_resources(duration)
        )
        
        # 创建客户端任务
        client_tasks = []
        for i in range(num_clients):
            task = asyncio.create_task(
                self.single_websocket_client(i, duration, message_interval)
            )
            client_tasks.append(task)
        
        # 等待所有客户端完成
        client_stats = await asyncio.gather(*client_tasks, return_exceptions=True)
        
        # 等待系统监控完成
        await monitor_task
        
        # 统计结果
        successful_connections = len([s for s in client_stats if s.get('connected', False)])
        failed_connections = num_clients - successful_connections
        total_messages = sum(s.get('messages_received', 0) for s in client_stats)
        total_bytes = sum(s.get('total_bytes_received', 0) for s in client_stats)
        
        # 收集所有错误
        all_errors = []
        for stats in client_stats:
            if isinstance(stats, dict):
                all_errors.extend(stats.get('errors', []))
            elif isinstance(stats, Exception):
                all_errors.append(f"客户端异常: {str(stats)}")
        
        # 更新连接统计
        self.connection_stats.update({
            'total_connections': num_clients,
            'successful_connections': successful_connections,
            'failed_connections': failed_connections,
            'total_messages': total_messages,
            'total_bytes_received': total_bytes,
            'connection_errors': all_errors
        })
        
        # 计算测试结果
        end_time = time.time()
        test_duration = end_time - start_time
        
        # 创建模拟指标用于结果计算
        mock_metrics = []
        for stats in client_stats:
            if isinstance(stats, dict) and stats.get('connected', False):
                # 为每个成功连接创建指标
                metrics = await self.framework.collect_system_metrics()
                metrics.response_time = stats.get('connection_time', 0)
                metrics.success = True
                mock_metrics.append(metrics)
        
        result = self.framework._calculate_test_result(
            f"websocket_concurrent_{num_clients}_clients",
            start_time=datetime.fromtimestamp(start_time),
            end_time=datetime.fromtimestamp(end_time),
            metrics=mock_metrics
        )
        
        # 添加WebSocket特定的统计信息
        result.total_requests = num_clients  # 连接数
        result.successful_requests = successful_connections
        result.failed_requests = failed_connections
        result.errors.extend(all_errors[:10])
        
        return result
    
    async def websocket_message_throughput_test(self, num_clients: int = 10, 
                                              duration: int = 60) -> TestResult:
        """WebSocket消息吞吐量测试"""
        self.logger.info(f"开始WebSocket消息吞吐量测试: {num_clients}个客户端，持续{duration}秒")
        
        start_time = time.time()
        message_stats = []
        
        # 启动系统监控
        monitor_task = asyncio.create_task(
            self.framework.monitor_system_resources(duration)
        )
        
        async def message_counter_client(client_id: int):
            """消息计数客户端"""
            messages = []
            connection_start = time.time()
            
            try:
                async with websockets.connect(self.framework.config.ws_url) as websocket:
                    while time.time() - connection_start < duration:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            message_time = time.time()
                            messages.append({
                                'client_id': client_id,
                                'timestamp': message_time,
                                'size': len(message.encode('utf-8'))
                            })
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            self.logger.error(f"客户端 {client_id} 错误: {e}")
                            break
            except Exception as e:
                self.logger.error(f"客户端 {client_id} 连接失败: {e}")
            
            return messages
        
        # 启动所有客户端
        client_tasks = [message_counter_client(i) for i in range(num_clients)]
        client_messages = await asyncio.gather(*client_tasks, return_exceptions=True)
        
        # 等待系统监控完成
        await monitor_task
        
        # 统计消息
        all_messages = []
        for messages in client_messages:
            if isinstance(messages, list):
                all_messages.extend(messages)
        
        total_messages = len(all_messages)
        messages_per_second = total_messages / duration if duration > 0 else 0
        
        # 按时间排序并计算消息间隔
        all_messages.sort(key=lambda x: x['timestamp'])
        message_intervals = []
        for i in range(1, len(all_messages)):
            interval = all_messages[i]['timestamp'] - all_messages[i-1]['timestamp']
            message_intervals.append(interval)
        
        # 计算统计信息
        avg_interval = sum(message_intervals) / len(message_intervals) if message_intervals else 0
        max_interval = max(message_intervals) if message_intervals else 0
        min_interval = min(message_intervals) if message_intervals else 0
        
        self.logger.info(f"消息吞吐量测试完成:")
        self.logger.info(f"  总消息数: {total_messages}")
        self.logger.info(f"  每秒消息数: {messages_per_second:.2f}")
        self.logger.info(f"  平均消息间隔: {avg_interval:.3f}s")
        self.logger.info(f"  最大消息间隔: {max_interval:.3f}s")
        self.logger.info(f"  最小消息间隔: {min_interval:.3f}s")
        
        # 创建测试结果
        end_time = time.time()
        mock_metrics = [await self.framework.collect_system_metrics() for _ in range(total_messages)]
        
        result = self.framework._calculate_test_result(
            "websocket_message_throughput",
            start_time=datetime.fromtimestamp(start_time),
            end_time=datetime.fromtimestamp(end_time),
            metrics=mock_metrics
        )
        
        result.total_requests = total_messages
        result.successful_requests = total_messages
        result.requests_per_second = messages_per_second
        
        return result
    
    async def run_all_websocket_tests(self):
        """运行所有WebSocket压力测试"""
        self.logger.info("开始运行所有WebSocket压力测试")
        
        results = []
        
        # 测试场景配置
        test_scenarios = [
            {"clients": 10, "duration": 30, "name": "light_load"},
            {"clients": 50, "duration": 60, "name": "medium_load"},
            {"clients": 100, "duration": 120, "name": "heavy_load"},
        ]
        
        for scenario in test_scenarios:
            self.logger.info(f"执行测试场景: {scenario['name']}")
            
            # 并发连接测试
            result1 = await self.concurrent_websocket_test(
                num_clients=scenario['clients'],
                duration=scenario['duration']
            )
            result1.test_name = f"websocket_concurrent_{scenario['name']}"
            results.append(result1)
            self.framework.save_test_report(result1)
            
            # 等待一段时间让系统恢复
            await asyncio.sleep(5)
            
            # 消息吞吐量测试
            result2 = await self.websocket_message_throughput_test(
                num_clients=min(scenario['clients'], 20),  # 限制客户端数量
                duration=scenario['duration']
            )
            result2.test_name = f"websocket_throughput_{scenario['name']}"
            results.append(result2)
            self.framework.save_test_report(result2)
            
            # 等待系统恢复
            await asyncio.sleep(10)
        
        return results


async def main():
    """主函数"""
    framework = StressTestFramework()
    tester = WebSocketStressTester(framework)
    
    try:
        results = await tester.run_all_websocket_tests()
        
        print(f"\nWebSocket压力测试完成，共执行 {len(results)} 个测试")
        print("详细报告已保存到 test_reports 目录")
        
    except Exception as e:
        logging.error(f"WebSocket压力测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
