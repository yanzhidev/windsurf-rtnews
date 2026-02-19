"""
压力测试主运行器
"""
import asyncio
import argparse
import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any

from stress_test_framework import StressTestFramework, TestResult
from stress_test_config import STRESS_CONFIG
from test_stress_websocket import WebSocketStressTester
from test_stress_api import APIStressTester
from test_stress_memory import MemoryStressTester


class StressTestRunner:
    """压力测试运行器"""
    
    def __init__(self):
        self.framework = StressTestFramework()
        self.logger = self._setup_logger()
        
        # 初始化测试器
        self.websocket_tester = WebSocketStressTester(self.framework)
        self.api_tester = APIStressTester(self.framework)
        self.memory_tester = MemoryStressTester(self.framework)
        
        # 测试结果汇总
        self.all_results: List[TestResult] = []
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("stress_test_runner")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # 文件处理器
            log_file = f"{STRESS_CONFIG.report_output_dir}/stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    async def run_websocket_tests(self, scenarios: List[str] = None) -> List[TestResult]:
        """运行WebSocket压力测试"""
        self.logger.info("开始WebSocket压力测试")
        
        if scenarios is None:
            scenarios = ["light_load", "medium_load"]
        
        results = []
        
        for scenario in scenarios:
            if scenario in STRESS_CONFIG.test_scenarios:
                config = STRESS_CONFIG.test_scenarios[scenario]
                self.logger.info(f"执行WebSocket测试场景: {scenario}")
                
                try:
                    result = await self.websocket_tester.concurrent_websocket_test(
                        num_clients=config['websocket_clients'],
                        duration=config['duration']
                    )
                    result.test_name = f"websocket_{scenario}"
                    results.append(result)
                    self.framework.save_test_report(result)
                    
                    # 等待系统恢复
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    self.logger.error(f"WebSocket测试场景 {scenario} 失败: {e}")
        
        return results
    
    async def run_api_tests(self, scenarios: List[str] = None) -> List[TestResult]:
        """运行API压力测试"""
        self.logger.info("开始API压力测试")
        
        if scenarios is None:
            scenarios = ["light_load", "medium_load"]
        
        results = []
        
        for scenario in scenarios:
            if scenario in STRESS_CONFIG.test_scenarios:
                config = STRESS_CONFIG.test_scenarios[scenario]
                self.logger.info(f"执行API测试场景: {scenario}")
                
                try:
                    # 测试主要API端点
                    result = await self.framework.run_api_stress_test(
                        endpoint="/api/news",
                        concurrent_requests=config['api_concurrent_requests'],
                        duration=config['duration']
                    )
                    result.test_name = f"api_news_{scenario}"
                    results.append(result)
                    self.framework.save_test_report(result)
                    
                    # 等待系统恢复
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    self.logger.error(f"API测试场景 {scenario} 失败: {e}")
        
        return results
    
    async def run_memory_tests(self) -> List[TestResult]:
        """运行内存压力测试"""
        self.logger.info("开始内存压力测试")
        
        try:
            results = await self.memory_tester.run_all_memory_tests()
            return results
        except Exception as e:
            self.logger.error(f"内存压力测试失败: {e}")
            return []
    
    async def run_full_stress_test_suite(self) -> List[TestResult]:
        """运行完整的压力测试套件"""
        self.logger.info("开始运行完整压力测试套件")
        start_time = datetime.now()
        
        all_results = []
        
        try:
            # 1. WebSocket测试
            self.logger.info("=" * 60)
            self.logger.info("1/3 执行WebSocket压力测试")
            self.logger.info("=" * 60)
            
            websocket_results = await self.run_websocket_tests()
            all_results.extend(websocket_results)
            
            # 等待系统恢复
            self.logger.info("等待系统恢复...")
            await asyncio.sleep(30)
            
            # 2. API测试
            self.logger.info("=" * 60)
            self.logger.info("2/3 执行API压力测试")
            self.logger.info("=" * 60)
            
            api_results = await self.run_api_tests()
            all_results.extend(api_results)
            
            # 等待系统恢复
            self.logger.info("等待系统恢复...")
            await asyncio.sleep(30)
            
            # 3. 内存测试
            self.logger.info("=" * 60)
            self.logger.info("3/3 执行内存压力测试")
            self.logger.info("=" * 60)
            
            memory_results = await self.run_memory_tests()
            all_results.extend(memory_results)
            
        except Exception as e:
            self.logger.error(f"压力测试套件执行失败: {e}")
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # 生成综合报告
        self.generate_summary_report(all_results, total_duration)
        
        return all_results
    
    async def run_quick_stress_test(self) -> List[TestResult]:
        """运行快速压力测试"""
        self.logger.info("开始运行快速压力测试")
        
        results = []
        
        try:
            # 快速WebSocket测试
            result1 = await self.websocket_tester.concurrent_websocket_test(
                num_clients=10,
                duration=30
            )
            result1.test_name = "quick_websocket_test"
            results.append(result1)
            self.framework.save_test_report(result1)
            
            # 等待系统恢复
            await asyncio.sleep(10)
            
            # 快速API测试
            result2 = await self.framework.run_api_stress_test(
                endpoint="/api/news",
                concurrent_requests=10,
                duration=30
            )
            result2.test_name = "quick_api_test"
            results.append(result2)
            self.framework.save_test_report(result2)
            
            # 等待系统恢复
            await asyncio.sleep(10)
            
            # 快速内存测试
            result3 = await self.memory_tester.memory_allocation_test(
                max_memory_mb=100,
                chunk_size_mb=5,
                duration=30
            )
            result3.test_name = "quick_memory_test"
            results.append(result3)
            self.framework.save_test_report(result3)
            
        except Exception as e:
            self.logger.error(f"快速压力测试失败: {e}")
        
        # 生成快速报告
        total_test_duration = sum(r.duration for r in results) if results else 0.0
        self.generate_summary_report(results, total_test_duration)
        
        return results
    
    def generate_summary_report(self, results: List[TestResult], total_duration: float):
        """生成综合报告"""
        self.logger.info("=" * 80)
        self.logger.info("压力测试综合报告")
        self.logger.info("=" * 80)
        
        self.logger.info(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"总测试时长: {total_duration:.2f}秒")
        self.logger.info(f"执行测试数量: {len(results)}")
        
        # 按测试类型分组
        websocket_tests = [r for r in results if 'websocket' in r.test_name.lower()]
        api_tests = [r for r in results if 'api' in r.test_name.lower()]
        memory_tests = [r for r in results if 'memory' in r.test_name.lower()]
        
        # WebSocket测试统计
        if websocket_tests:
            self.logger.info(f"\nWebSocket测试 ({len(websocket_tests)}个):")
            for test in websocket_tests:
                self.logger.info(f"  {test.test_name}: "
                               f"成功率 {(test.successful_requests/test.total_requests*100):.1f}%, "
                               f"平均响应时间 {test.avg_response_time*1000:.1f}ms")
        
        # API测试统计
        if api_tests:
            self.logger.info(f"\nAPI测试 ({len(api_tests)}个):")
            for test in api_tests:
                self.logger.info(f"  {test.test_name}: "
                               f"成功率 {(test.successful_requests/test.total_requests*100):.1f}%, "
                               f"RPS {test.requests_per_second:.1f}")
        
        # 内存测试统计
        if memory_tests:
            self.logger.info(f"\n内存测试 ({len(memory_tests)}个):")
            for test in memory_tests:
                self.logger.info(f"  {test.test_name}: "
                               f"峰值内存 {test.peak_memory_percent:.1f}%, "
                               f"峰值CPU {test.peak_cpu_percent:.1f}%")
        
        # 系统资源峰值
        all_peak_cpu = max(r.peak_cpu_percent for r in results) if results else 0
        all_peak_memory = max(r.peak_memory_percent for r in results) if results else 0
        
        self.logger.info(f"\n系统资源峰值:")
        self.logger.info(f"  CPU使用率峰值: {all_peak_cpu:.1f}%")
        self.logger.info(f"  内存使用率峰值: {all_peak_memory:.1f}%")
        
        # 错误统计
        all_errors = []
        for result in results:
            all_errors.extend(result.errors)
        
        if all_errors:
            self.logger.info(f"\n主要错误 (前10个):")
            for i, error in enumerate(all_errors[:10]):
                self.logger.info(f"  {i+1}. {error}")
        
        # 保存综合报告
        summary_data = {
            'test_time': datetime.now().isoformat(),
            'total_duration': total_duration,
            'total_tests': len(results),
            'websocket_tests': len(websocket_tests),
            'api_tests': len(api_tests),
            'memory_tests': len(memory_tests),
            'peak_cpu_percent': all_peak_cpu,
            'peak_memory_percent': all_peak_memory,
            'test_results': [
                {
                    'name': r.test_name,
                    'duration': r.duration,
                    'success_rate': r.successful_requests / r.total_requests * 100 if r.total_requests > 0 else 0,
                    'avg_response_time': r.avg_response_time,
                    'requests_per_second': r.requests_per_second,
                    'peak_cpu': r.peak_cpu_percent,
                    'peak_memory': r.peak_memory_percent
                }
                for r in results
            ],
            'top_errors': all_errors[:20]
        }
        
        summary_file = f"{STRESS_CONFIG.report_output_dir}/stress_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"\n综合报告已保存到: {summary_file}")
        self.logger.info("=" * 80)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="压力测试运行器")
    parser.add_argument("--type", choices=["full", "quick", "websocket", "api", "memory"],
                       default="quick", help="测试类型")
    parser.add_argument("--scenarios", nargs="+", help="测试场景")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    runner = StressTestRunner()
    
    try:
        if args.type == "full":
            results = await runner.run_full_stress_test_suite()
        elif args.type == "quick":
            results = await runner.run_quick_stress_test()
        elif args.type == "websocket":
            results = await runner.run_websocket_tests(args.scenarios)
        elif args.type == "api":
            results = await runner.run_api_tests(args.scenarios)
        elif args.type == "memory":
            results = await runner.run_memory_tests()
        
        print(f"\n压力测试完成！共执行 {len(results)} 个测试")
        print(f"详细报告请查看 {STRESS_CONFIG.report_output_dir} 目录")
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n压力测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
