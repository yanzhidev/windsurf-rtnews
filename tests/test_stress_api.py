"""
API端点压力测试
"""
import asyncio
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import aiohttp
from dataclasses import dataclass

from stress_test_framework import StressTestFramework, TestResult
from stress_test_config import STRESS_CONFIG


@dataclass
class APIEndpoint:
    """API端点定义"""
    path: str
    method: str = "GET"
    expected_status: int = 200
    timeout: float = 10.0
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None


class APIStressTester:
    """API压力测试器"""
    
    def __init__(self, framework: StressTestFramework):
        self.framework = framework
        self.logger = logging.getLogger("api_stress_test")
        
        # 定义测试端点
        self.endpoints = {
            "news": APIEndpoint("/api/news"),
            "stats": APIEndpoint("/api/stats"),
            "health": APIEndpoint("/health", expected_status=404),  # 可能不存在
            "root": APIEndpoint("/"),
        }
    
    async def single_api_request(self, session: aiohttp.ClientSession, 
                               endpoint: APIEndpoint) -> Dict[str, Any]:
        """单个API请求"""
        start_time = time.time()
        result = {
            'endpoint': endpoint.path,
            'method': endpoint.method,
            'status_code': None,
            'response_time': 0,
            'success': False,
            'error': None,
            'response_size': 0,
            'content_type': None
        }
        
        try:
            # 构建请求参数
            request_kwargs = {
                'timeout': aiohttp.ClientTimeout(total=endpoint.timeout),
                'headers': endpoint.headers or {}
            }
            
            if endpoint.method.upper() == 'GET':
                request_kwargs['params'] = endpoint.params or {}
            elif endpoint.method.upper() == 'POST':
                request_kwargs['json'] = endpoint.params or {}
            
            # 发起请求
            async with session.request(
                endpoint.method,
                f"{self.framework.config.base_url}{endpoint.path}",
                **request_kwargs
            ) as response:
                result['status_code'] = response.status
                result['content_type'] = response.headers.get('content-type', '')
                
                # 读取响应内容
                content = await response.read()
                result['response_size'] = len(content)
                
                # 检查状态码
                if response.status == endpoint.expected_status:
                    result['success'] = True
                else:
                    result['error'] = f"Unexpected status code: {response.status}"
                
                # 尝试解析JSON
                if 'application/json' in result['content_type']:
                    try:
                        json.loads(content.decode('utf-8'))
                    except json.JSONDecodeError:
                        result['error'] = "Invalid JSON response"
                
        except asyncio.TimeoutError:
            result['error'] = f"Request timeout after {endpoint.timeout}s"
        except aiohttp.ClientError as e:
            result['error'] = f"Client error: {str(e)}"
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
        
        result['response_time'] = time.time() - start_time
        return result
    
    async def concurrent_api_test(self, endpoint_name: str, 
                                concurrent_requests: int = None,
                                duration: int = None) -> TestResult:
        """并发API测试"""
        endpoint = self.endpoints.get(endpoint_name)
        if not endpoint:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")
        
        concurrent_requests = concurrent_requests or self.framework.config.api_concurrent_requests
        duration = duration or self.framework.config.api_duration
        
        self.logger.info(f"开始API并发测试: {endpoint.path}")
        self.logger.info(f"并发数: {concurrent_requests}, 持续时间: {duration}秒")
        
        start_time = time.time()
        request_results = []
        
        # 启动系统监控
        monitor_task = asyncio.create_task(
            self.framework.monitor_system_resources(duration)
        )
        
        # 创建HTTP会话
        connector = aiohttp.TCPConnector(
            limit=concurrent_requests * 2,  # 连接池大小
            limit_per_host=concurrent_requests,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=endpoint.timeout)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async def request_worker():
                """请求工作器"""
                while time.time() - (start_time + duration) < 0:
                    # 创建并发请求批次
                    batch_tasks = []
                    for _ in range(concurrent_requests):
                        task = asyncio.create_task(
                            self.single_api_request(session, endpoint)
                        )
                        batch_tasks.append(task)
                    
                    # 等待批次完成
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # 处理结果
                    for result in batch_results:
                        if isinstance(result, dict):
                            request_results.append(result)
                        elif isinstance(result, Exception):
                            request_results.append({
                                'endpoint': endpoint.path,
                                'method': endpoint.method,
                                'status_code': None,
                                'response_time': 0,
                                'success': False,
                                'error': f"Request exception: {str(result)}",
                                'response_size': 0,
                                'content_type': None
                            })
                    
                    # 请求间隔
                    await asyncio.sleep(self.framework.config.api_request_interval)
            
            # 启动请求工作器
            await request_worker()
        
        # 等待系统监控完成
        await monitor_task
        
        # 计算测试结果
        end_time = time.time()
        return self._calculate_api_test_result(
            f"api_concurrent_{endpoint_name}",
            datetime.fromtimestamp(start_time),
            datetime.fromtimestamp(end_time),
            request_results
        )
    
    async def api_load_ramp_test(self, endpoint_name: str,
                               max_concurrent: int = 50,
                               ramp_duration: int = 60,
                               steady_duration: int = 60) -> TestResult:
        """API负载递增测试"""
        endpoint = self.endpoints.get(endpoint_name)
        if not endpoint:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")
        
        self.logger.info(f"开始API负载递增测试: {endpoint.path}")
        self.logger.info(f"最大并发数: {max_concurrent}, 递增时间: {ramp_duration}s, 稳定时间: {steady_duration}s")
        
        total_duration = ramp_duration + steady_duration
        start_time = time.time()
        request_results = []
        
        # 启动系统监控
        monitor_task = asyncio.create_task(
            self.framework.monitor_system_resources(total_duration)
        )
        
        connector = aiohttp.TCPConnector(limit=max_concurrent * 2, limit_per_host=max_concurrent)
        timeout = aiohttp.ClientTimeout(total=endpoint.timeout)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async def ramp_worker():
                """递增负载工作器"""
                elapsed = 0
                
                while elapsed < total_duration:
                    # 计算当前并发数
                    if elapsed < ramp_duration:
                        # 递增阶段
                        current_concurrent = int(max_concurrent * (elapsed / ramp_duration))
                    else:
                        # 稳定阶段
                        current_concurrent = max_concurrent
                    
                    if current_concurrent > 0:
                        # 发起请求
                        tasks = []
                        for _ in range(current_concurrent):
                            task = asyncio.create_task(
                                self.single_api_request(session, endpoint)
                            )
                            tasks.append(task)
                        
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        for result in results:
                            if isinstance(result, dict):
                                request_results.append(result)
                            elif isinstance(result, Exception):
                                request_results.append({
                                    'endpoint': endpoint.path,
                                    'method': endpoint.method,
                                    'status_code': None,
                                    'response_time': 0,
                                    'success': False,
                                    'error': f"Request exception: {str(result)}",
                                    'response_size': 0,
                                    'content_type': None
                                })
                    
                    # 等待下一个周期
                    await asyncio.sleep(1.0)
                    elapsed = time.time() - start_time
            
            await ramp_worker()
        
        # 等待系统监控完成
        await monitor_task
        
        # 计算测试结果
        end_time = time.time()
        return self._calculate_api_test_result(
            f"api_ramp_{endpoint_name}",
            datetime.fromtimestamp(start_time),
            datetime.fromtimestamp(end_time),
            request_results
        )
    
    async def api_endurance_test(self, endpoint_name: str,
                               concurrent_requests: int = 10,
                               duration: int = 300) -> TestResult:
        """API耐久性测试"""
        endpoint = self.endpoints.get(endpoint_name)
        if not endpoint:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")
        
        self.logger.info(f"开始API耐久性测试: {endpoint.path}")
        self.logger.info(f"并发数: {concurrent_requests}, 持续时间: {duration}秒")
        
        start_time = time.time()
        request_results = []
        
        # 启动系统监控
        monitor_task = asyncio.create_task(
            self.framework.monitor_system_resources(duration)
        )
        
        connector = aiohttp.TCPConnector(limit=concurrent_requests * 2, limit_per_host=concurrent_requests)
        timeout = aiohttp.ClientTimeout(total=endpoint.timeout)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async def endurance_worker():
                """耐久性测试工作器"""
                while time.time() - (start_time + duration) < 0:
                    # 发起请求
                    tasks = []
                    for _ in range(concurrent_requests):
                        task = asyncio.create_task(
                            self.single_api_request(session, endpoint)
                        )
                        tasks.append(task)
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, dict):
                            request_results.append(result)
                        elif isinstance(result, Exception):
                            request_results.append({
                                'endpoint': endpoint.path,
                                'method': endpoint.method,
                                'status_code': None,
                                'response_time': 0,
                                'success': False,
                                'error': f"Request exception: {str(result)}",
                                'response_size': 0,
                                'content_type': None
                            })
                    
                    # 请求间隔
                    await asyncio.sleep(self.framework.config.api_request_interval)
            
            await endurance_worker()
        
        # 等待系统监控完成
        await monitor_task
        
        # 计算测试结果
        end_time = time.time()
        return self._calculate_api_test_result(
            f"api_endurance_{endpoint_name}",
            datetime.fromtimestamp(start_time),
            datetime.fromtimestamp(end_time),
            request_results
        )
    
    def _calculate_api_test_result(self, test_name: str, start_time: datetime, 
                                  end_time: datetime, request_results: List[Dict]) -> TestResult:
        """计算API测试结果"""
        duration = end_time - start_time
        
        # 统计请求结果
        successful_requests = len([r for r in request_results if r['success']])
        failed_requests = len(request_results) - successful_requests
        
        # 响应时间统计
        response_times = [r['response_time'] for r in request_results if r['response_time'] > 0]
        
        if response_times:
            import statistics
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            sorted_times = sorted(response_times)
            p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
            p99_response_time = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
        
        # 系统资源统计
        cpu_values = [m.cpu_percent for m in self.framework.metrics]
        memory_values = [m.memory_percent for m in self.framework.metrics]
        
        peak_cpu = max(cpu_values) if cpu_values else 0
        peak_memory = max(memory_values) if memory_values else 0
        avg_cpu = statistics.mean(cpu_values) if cpu_values else 0
        avg_memory = statistics.mean(memory_values) if memory_values else 0
        
        # 收集错误信息
        errors = [r['error'] for r in request_results if r.get('error')]
        error_counts = {}
        for error in errors:
            error_counts[error] = error_counts.get(error, 0) + 1
        
        # 按频率排序错误
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        top_errors = [f"{error} ({count}次)" for error, count in sorted_errors[:10]]
        
        # 计算每秒请求数
        requests_per_second = len(request_results) / duration if duration > 0 else 0
        
        return TestResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            total_requests=len(request_results),
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
            errors=top_errors
        )
    
    async def run_all_api_tests(self):
        """运行所有API压力测试"""
        self.logger.info("开始运行所有API压力测试")
        
        results = []
        
        # 测试每个端点
        for endpoint_name in self.endpoints.keys():
            self.logger.info(f"测试端点: {endpoint_name}")
            
            try:
                # 并发测试
                result1 = await self.concurrent_api_test(
                    endpoint_name=endpoint_name,
                    concurrent_requests=20,
                    duration=30
                )
                result1.test_name = f"api_concurrent_{endpoint_name}"
                results.append(result1)
                self.framework.save_test_report(result1)
                
                # 等待系统恢复
                await asyncio.sleep(5)
                
                # 负载递增测试
                result2 = await self.api_load_ramp_test(
                    endpoint_name=endpoint_name,
                    max_concurrent=30,
                    ramp_duration=30,
                    steady_duration=30
                )
                result2.test_name = f"api_ramp_{endpoint_name}"
                results.append(result2)
                self.framework.save_test_report(result2)
                
                # 等待系统恢复
                await asyncio.sleep(10)
                
            except Exception as e:
                self.logger.error(f"端点 {endpoint_name} 测试失败: {e}")
                continue
        
        return results


async def main():
    """主函数"""
    framework = StressTestFramework()
    tester = APIStressTester(framework)
    
    try:
        results = await tester.run_all_api_tests()
        
        print(f"\nAPI压力测试完成，共执行 {len(results)} 个测试")
        print("详细报告已保存到 test_reports 目录")
        
    except Exception as e:
        logging.error(f"API压力测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
