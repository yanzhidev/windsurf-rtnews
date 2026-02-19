"""
压力测试框架
"""
import asyncio
import time
import json
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import psutil
import aiohttp
import websockets
from concurrent.futures import ThreadPoolExecutor

from stress_test_config import STRESS_CONFIG


@dataclass
class TestMetrics:
    """测试指标数据类"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    response_time: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    peak_cpu_percent: float
    peak_memory_percent: float
    avg_cpu_percent: float
    avg_memory_percent: float
    errors: List[str]


class StressTestFramework:
    """压力测试框架"""
    
    def __init__(self, config: STRESS_CONFIG.__class__ = STRESS_CONFIG):
        self.config = config
        self.metrics: List[TestMetrics] = []
        self.logger = self._setup_logger()
        self.process = psutil.Process()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("stress_test")
        logger.setLevel(logging.INFO if self.config.enable_detailed_logging else logging.WARNING)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def collect_system_metrics(self) -> TestMetrics:
        """收集系统指标"""
        cpu_percent = self.process.cpu_percent()
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        return TestMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_info.rss / 1024 / 1024
        )
    
    async def monitor_system_resources(self, duration: float, interval: float = 1.0):
        """监控系统资源"""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            metrics = await self.collect_system_metrics()
            self.metrics.append(metrics)
            await asyncio.sleep(interval)
    
    async def make_api_request(self, session: aiohttp.ClientSession, endpoint: str) -> TestMetrics:
        """发起API请求"""
        start_time = time.time()
        success = True
        error_message = None
        
        try:
            async with session.get(f"{self.config.base_url}{endpoint}") as response:
                if response.status != 200:
                    success = False
                    error_message = f"HTTP {response.status}"
                await response.text()
        except Exception as e:
            success = False
            error_message = str(e)
        
        response_time = time.time() - start_time
        
        # 获取当前系统指标
        system_metrics = await self.collect_system_metrics()
        system_metrics.response_time = response_time
        system_metrics.success = success
        system_metrics.error_message = error_message
        
        return system_metrics
    
    async def run_api_stress_test(self, endpoint: str = "/api/news", 
                                 concurrent_requests: int = None,
                                 duration: int = None) -> TestResult:
        """运行API压力测试"""
        concurrent_requests = concurrent_requests or self.config.api_concurrent_requests
        duration = duration or self.config.api_duration
        
        self.logger.info(f"开始API压力测试: {endpoint}")
        self.logger.info(f"并发请求数: {concurrent_requests}, 持续时间: {duration}秒")
        
        start_time = datetime.now()
        request_metrics = []
        
        # 启动系统监控
        monitor_task = asyncio.create_task(
            self.monitor_system_resources(duration)
        )
        
        # 创建HTTP会话
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            async def request_worker():
                """请求工作器"""
                while time.time() - (start_time.timestamp() + duration) < 0:
                    # 创建并发请求
                    batch_tasks = []
                    for _ in range(concurrent_requests):
                        batch_tasks.append(self.make_api_request(session, endpoint))
                    
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    request_metrics.extend([r for r in batch_results if isinstance(r, TestMetrics)])
                    
                    await asyncio.sleep(self.config.api_request_interval)
            
            # 启动请求工作器
            await request_worker()
        
        # 等待监控完成
        await monitor_task
        
        end_time = datetime.now()
        
        # 计算测试结果
        return self._calculate_test_result("api_stress_test", start_time, end_time, request_metrics)
    
    async def run_websocket_stress_test(self, clients: int = None, duration: int = None) -> TestResult:
        """运行WebSocket压力测试"""
        clients = clients or self.config.websocket_clients
        duration = duration or self.config.websocket_duration
        
        self.logger.info(f"开始WebSocket压力测试")
        self.logger.info(f"客户端数量: {clients}, 持续时间: {duration}秒")
        
        start_time = datetime.now()
        connection_metrics = []
        
        # 启动系统监控
        monitor_task = asyncio.create_task(
            self.monitor_system_resources(duration)
        )
        
        async def websocket_client(client_id: int):
            """WebSocket客户端"""
            connection_start = time.time()
            success = True
            error_message = None
            
            try:
                async with websockets.connect(self.config.ws_url) as websocket:
                    messages_received = 0
                    
                    while time.time() - connection_start < duration:
                        try:
                            message = await asyncio.wait_for(
                                websocket.recv(), timeout=1.0
                            )
                            messages_received += 1
                            
                            # 记录消息接收指标
                            metrics = await self.collect_system_metrics()
                            metrics.success = True
                            connection_metrics.append(metrics)
                            
                        except asyncio.TimeoutError:
                            # 超时是正常的，继续
                            pass
                        except Exception as e:
                            error_message = f"Client {client_id}: {str(e)}"
                            break
                        
                        await asyncio.sleep(self.config.websocket_message_interval)
                        
            except Exception as e:
                success = False
                error_message = f"Client {client_id} connection failed: {str(e)}"
            
            # 记录连接结果
            metrics = await self.collect_system_metrics()
            metrics.success = success
            metrics.error_message = error_message
            connection_metrics.append(metrics)
        
        # 启动所有WebSocket客户端
        client_tasks = [websocket_client(i) for i in range(clients)]
        await asyncio.gather(*client_tasks, return_exceptions=True)
        
        # 等待监控完成
        await monitor_task
        
        end_time = datetime.now()
        
        # 计算测试结果
        return self._calculate_test_result("websocket_stress_test", start_time, end_time, connection_metrics)
    
    async def run_memory_stress_test(self, duration: int = None) -> TestResult:
        """运行内存压力测试"""
        duration = duration or self.config.memory_test_duration
        
        self.logger.info(f"开始内存压力测试，持续时间: {duration}秒")
        
        start_time = datetime.now()
        memory_metrics = []
        
        # 启动系统监控
        monitor_task = asyncio.create_task(
            self.monitor_system_resources(duration, self.config.memory_check_interval)
        )
        
        # 模拟内存压力 - 创建大量临时数据
        async def memory_pressure_generator():
            """内存压力生成器"""
            data_chunks = []
            
            for i in range(int(duration / 0.1)):  # 每0.1秒一次
                # 创建临时数据块
                chunk = [0] * 10000  # 约40KB
                data_chunks.append(chunk)
                
                # 定期清理数据以模拟真实场景
                if len(data_chunks) > 100:
                    data_chunks = data_chunks[-50:]
                
                await asyncio.sleep(0.1)
        
        # 启动内存压力生成器
        await memory_pressure_generator()
        
        # 等待监控完成
        await monitor_task
        
        end_time = datetime.now()
        
        # 计算测试结果
        return self._calculate_test_result("memory_stress_test", start_time, end_time, self.metrics)
    
    def _calculate_test_result(self, test_name: str, start_time: datetime, 
                              end_time: datetime, metrics: List[TestMetrics]) -> TestResult:
        """计算测试结果"""
        duration = (end_time - start_time).total_seconds()
        
        # 过滤有效的响应时间指标
        response_times = [m.response_time for m in metrics if m.response_time is not None]
        successful_requests = len([m for m in metrics if m.success])
        failed_requests = len(metrics) - successful_requests
        
        # 计算响应时间统计
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            sorted_times = sorted(response_times)
            p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
            p99_response_time = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
        
        # 计算系统资源统计
        cpu_values = [m.cpu_percent for m in self.metrics]
        memory_values = [m.memory_percent for m in self.metrics]
        
        peak_cpu = max(cpu_values) if cpu_values else 0
        peak_memory = max(memory_values) if memory_values else 0
        avg_cpu = statistics.mean(cpu_values) if cpu_values else 0
        avg_memory = statistics.mean(memory_values) if memory_values else 0
        
        # 收集错误信息
        errors = [m.error_message for m in metrics if m.error_message]
        
        # 计算每秒请求数
        requests_per_second = successful_requests / duration if duration > 0 else 0
        
        return TestResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            total_requests=len(metrics),
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            peak_cpu_percent=peak_cpu,
            peak_memory_percent=peak_memory,
            avg_cpu_percent=avg_cpu,
            avg_memory_percent=avg_memory,
            errors=errors[:10]  # 只保留前10个错误
        )
    
    def save_test_report(self, result: TestResult):
        """保存测试报告"""
        report_file = f"{self.config.report_output_dir}/{result.test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 转换为可序列化的格式
        report_data = asdict(result)
        report_data['start_time'] = result.start_time.isoformat()
        report_data['end_time'] = result.end_time.isoformat()
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"测试报告已保存到: {report_file}")
        
        # 打印摘要
        self._print_test_summary(result)
    
    def _print_test_summary(self, result: TestResult):
        """打印测试摘要"""
        print(f"\n{'='*60}")
        print(f"测试名称: {result.test_name}")
        print(f"测试时长: {result.duration:.2f}秒")
        print(f"总请求数: {result.total_requests}")
        print(f"成功请求数: {result.successful_requests}")
        print(f"失败请求数: {result.failed_requests}")
        print(f"成功率: {(result.successful_requests/result.total_requests*100):.2f}%")
        print(f"每秒请求数: {result.requests_per_second:.2f}")
        print(f"平均响应时间: {result.avg_response_time*1000:.2f}ms")
        print(f"P95响应时间: {result.p95_response_time*1000:.2f}ms")
        print(f"P99响应时间: {result.p99_response_time*1000:.2f}ms")
        print(f"峰值CPU使用率: {result.peak_cpu_percent:.2f}%")
        print(f"峰值内存使用率: {result.peak_memory_percent:.2f}%")
        print(f"平均CPU使用率: {result.avg_cpu_percent:.2f}%")
        print(f"平均内存使用率: {result.avg_memory_percent:.2f}%")
        
        if result.errors:
            print(f"\n主要错误:")
            for error in result.errors[:5]:
                print(f"  - {error}")
        
        print(f"{'='*60}\n")
