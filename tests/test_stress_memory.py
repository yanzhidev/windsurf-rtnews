"""
内存和系统资源压力测试
"""
import asyncio
import time
import gc
import logging
import psutil
import threading
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from stress_test_framework import StressTestFramework, TestResult
from stress_test_config import STRESS_CONFIG


@dataclass
class MemorySnapshot:
    """内存快照"""
    timestamp: float
    rss_mb: float  # 物理内存
    vms_mb: float  # 虚拟内存
    percent: float  # 内存使用百分比
    available_mb: float  # 可用内存
    cpu_percent: float  # CPU使用率
    thread_count: int  # 线程数
    fd_count: int  # 文件描述符数


class MemoryStressTester:
    """内存压力测试器"""
    
    def __init__(self, framework: StressTestFramework):
        self.framework = framework
        self.logger = logging.getLogger("memory_stress_test")
        self.process = psutil.Process()
        self.memory_snapshots: List[MemorySnapshot] = []
        
    def take_memory_snapshot(self) -> MemorySnapshot:
        """获取内存快照"""
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        # 获取系统内存信息
        system_memory = psutil.virtual_memory()
        
        try:
            thread_count = self.process.num_threads()
        except (psutil.NoSuchProcess, AttributeError):
            thread_count = 0
        
        try:
            fd_count = self.process.num_fds()
        except (AttributeError, psutil.AccessDenied):
            fd_count = 0
        
        return MemorySnapshot(
            timestamp=time.time(),
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=memory_percent,
            available_mb=system_memory.available / 1024 / 1024,
            cpu_percent=self.process.cpu_percent(),
            thread_count=thread_count,
            fd_count=fd_count
        )
    
    async def monitor_memory_usage(self, duration: float, interval: float = 1.0):
        """监控内存使用情况"""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            snapshot = self.take_memory_snapshot()
            self.memory_snapshots.append(snapshot)
            await asyncio.sleep(interval)
    
    def allocate_memory_chunks(self, chunk_size_mb: int, num_chunks: int) -> List[bytes]:
        """分配内存块"""
        chunks = []
        chunk_size_bytes = chunk_size_mb * 1024 * 1024
        
        for i in range(num_chunks):
            # 分配内存块
            chunk = b'x' * chunk_size_bytes
            chunks.append(chunk)
            
            if i % 10 == 0:
                self.logger.debug(f"已分配 {i+1}/{num_chunks} 个内存块，每个 {chunk_size_mb}MB")
        
        return chunks
    
    def cpu_intensive_task(self, duration: float):
        """CPU密集型任务"""
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # 执行一些计算密集型操作
            result = sum(i * i for i in range(10000))
            _ = result  # 避免编译器优化
    
    async def memory_allocation_test(self, max_memory_mb: int = 500, 
                                  chunk_size_mb: int = 10,
                                  duration: int = 120) -> TestResult:
        """内存分配测试"""
        self.logger.info(f"开始内存分配测试")
        self.logger.info(f"最大内存: {max_memory_mb}MB, 块大小: {chunk_size_mb}MB, 持续时间: {duration}秒")
        
        start_time = time.time()
        memory_chunks = []
        
        # 启动内存监控
        monitor_task = asyncio.create_task(
            self.monitor_memory_usage(duration, 0.5)
        )
        
        try:
            # 逐步分配内存
            allocated_mb = 0
            while allocated_mb < max_memory_mb and time.time() - start_time < duration:
                chunks_to_allocate = min(
                    (max_memory_mb - allocated_mb) // chunk_size_mb,
                    10  # 每次最多分配10个块
                )
                
                if chunks_to_allocate > 0:
                    new_chunks = self.allocate_memory_chunks(chunk_size_mb, chunks_to_allocate)
                    memory_chunks.extend(new_chunks)
                    allocated_mb += len(new_chunks) * chunk_size_mb
                    
                    self.logger.info(f"已分配内存: {allocated_mb}MB")
                
                # 等待一段时间
                await asyncio.sleep(2)
                
                # 检查系统内存使用率
                current_snapshot = self.take_memory_snapshot()
                if current_snapshot.percent > 90:
                    self.logger.warning(f"内存使用率过高: {current_snapshot.percent:.1f}%")
                    break
        
        except MemoryError:
            self.logger.error("内存分配失败，可能达到系统限制")
        except Exception as e:
            self.logger.error(f"内存分配测试异常: {e}")
        
        # 等待监控完成
        await monitor_task
        
        # 清理内存
        memory_chunks.clear()
        gc.collect()
        
        end_time = time.time()
        
        # 计算测试结果
        return self._calculate_memory_test_result(
            "memory_allocation_test",
            datetime.fromtimestamp(start_time),
            datetime.fromtimestamp(end_time)
        )
    
    async def memory_leak_simulation_test(self, duration: int = 180) -> TestResult:
        """内存泄漏模拟测试"""
        self.logger.info(f"开始内存泄漏模拟测试，持续时间: {duration}秒")
        
        start_time = time.time()
        leak_objects = []
        
        # 启动内存监控
        monitor_task = asyncio.create_task(
            self.monitor_memory_usage(duration, 1.0)
        )
        
        try:
            # 模拟内存泄漏
            while time.time() - start_time < duration:
                # 创建一些对象但不释放
                for i in range(100):
                    leak_objects.append({
                        'data': 'x' * 1000,  # 1KB数据
                        'timestamp': time.time(),
                        'id': i
                    })
                
                # 偶尔创建更大的对象
                if int(time.time()) % 10 == 0:
                    leak_objects.append({
                        'large_data': 'y' * 10000,  # 10KB数据
                        'timestamp': time.time(),
                        'type': 'large'
                    })
                
                await asyncio.sleep(1)
                
                # 定期报告内存使用情况
                if int(time.time()) % 30 == 0:
                    snapshot = self.take_memory_snapshot()
                    self.logger.info(f"当前内存使用: {snapshot.rss_mb:.1f}MB ({snapshot.percent:.1f}%)")
        
        except Exception as e:
            self.logger.error(f"内存泄漏测试异常: {e}")
        
        # 等待监控完成
        await monitor_task
        
        # 清理部分内存（模拟修复泄漏）
        leak_objects = leak_objects[-len(leak_objects)//2:]  # 保留一半
        gc.collect()
        
        end_time = time.time()
        
        # 计算测试结果
        return self._calculate_memory_test_result(
            "memory_leak_simulation",
            datetime.fromtimestamp(start_time),
            datetime.fromtimestamp(end_time)
        )
    
    async def cpu_memory_combined_test(self, cpu_workers: int = 4,
                                     memory_load_mb: int = 200,
                                     duration: int = 120) -> TestResult:
        """CPU和内存组合压力测试"""
        self.logger.info(f"开始CPU和内存组合压力测试")
        self.logger.info(f"CPU工作线程: {cpu_workers}, 内存负载: {memory_load_mb}MB, 持续时间: {duration}秒")
        
        start_time = time.time()
        
        # 启动内存监控
        monitor_task = asyncio.create_task(
            self.monitor_memory_usage(duration, 0.5)
        )
        
        # 分配内存
        memory_chunks = self.allocate_memory_chunks(10, memory_load_mb // 10)
        
        try:
            # 启动CPU密集型任务
            with ThreadPoolExecutor(max_workers=cpu_workers) as executor:
                futures = []
                
                for i in range(cpu_workers):
                    future = executor.submit(self.cpu_intensive_task, duration)
                    futures.append(future)
                
                # 等待所有CPU任务完成
                for future in futures:
                    future.result()
        
        except Exception as e:
            self.logger.error(f"CPU内存组合测试异常: {e}")
        
        # 等待监控完成
        await monitor_task
        
        # 清理内存
        memory_chunks.clear()
        gc.collect()
        
        end_time = time.time()
        
        # 计算测试结果
        return self._calculate_memory_test_result(
            "cpu_memory_combined_test",
            datetime.fromtimestamp(start_time),
            datetime.fromtimestamp(end_time)
        )
    
    async def garbage_collection_stress_test(self, duration: int = 120) -> TestResult:
        """垃圾回收压力测试"""
        self.logger.info(f"开始垃圾回收压力测试，持续时间: {duration}秒")
        
        start_time = time.time()
        
        # 启动内存监控
        monitor_task = asyncio.create_task(
            self.monitor_memory_usage(duration, 1.0)
        )
        
        try:
            # 创建大量临时对象
            for cycle in range(int(duration / 5)):  # 每5秒一个周期
                self.logger.debug(f"垃圾回收测试周期 {cycle + 1}")
                
                # 创建大量临时对象
                temp_objects = []
                for i in range(1000):
                    temp_objects.append({
                        'id': i,
                        'data': list(range(1000)),  # 创建列表
                        'nested': {
                            'deep': {'deeper': {'value': i * 2}}
                        }
                    })
                
                # 创建一些大对象
                large_objects = []
                for i in range(10):
                    large_objects.append(b'z' * 100000)  # 100KB
                
                # 强制垃圾回收
                gc.collect()
                
                # 清理引用
                temp_objects.clear()
                large_objects.clear()
                
                await asyncio.sleep(5)
        
        except Exception as e:
            self.logger.error(f"垃圾回收测试异常: {e}")
        
        # 等待监控完成
        await monitor_task
        
        end_time = time.time()
        
        # 计算测试结果
        return self._calculate_memory_test_result(
            "garbage_collection_stress_test",
            datetime.fromtimestamp(start_time),
            datetime.fromtimestamp(end_time)
        )
    
    def _calculate_memory_test_result(self, test_name: str, start_time: datetime, 
                                    end_time: datetime) -> TestResult:
        """计算内存测试结果"""
        duration = end_time - start_time
        
        if not self.memory_snapshots:
            # 如果没有快照，创建一个默认结果
            return TestResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time=0,
                min_response_time=0,
                max_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                requests_per_second=0,
                peak_cpu_percent=0,
                peak_memory_percent=0,
                avg_cpu_percent=0,
                avg_memory_percent=0,
                errors=[]
            )
        
        # 计算内存统计
        rss_values = [s.rss_mb for s in self.memory_snapshots]
        memory_percent_values = [s.percent for s in self.memory_snapshots]
        cpu_values = [s.cpu_percent for s in self.memory_snapshots]
        
        peak_memory_mb = max(rss_values) if rss_values else 0
        avg_memory_mb = sum(rss_values) / len(rss_values) if rss_values else 0
        peak_memory_percent = max(memory_percent_values) if memory_percent_values else 0
        avg_memory_percent = sum(memory_percent_values) / len(memory_percent_values) if memory_percent_values else 0
        peak_cpu = max(cpu_values) if cpu_values else 0
        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        
        # 计算内存增长率
        if len(rss_values) >= 2:
            memory_growth_rate = (rss_values[-1] - rss_values[0]) / duration
        else:
            memory_growth_rate = 0
        
        # 创建模拟指标
        mock_metrics = []
        for snapshot in self.memory_snapshots:
            metrics = self.framework.collect_system_metrics()
            metrics.cpu_percent = snapshot.cpu_percent
            metrics.memory_percent = snapshot.percent
            mock_metrics.append(metrics)
        
        result = self.framework._calculate_test_result(
            test_name,
            start_time,
            end_time,
            mock_metrics
        )
        
        # 添加内存特定的统计信息
        result.errors.append(f"峰值内存使用: {peak_memory_mb:.1f}MB")
        result.errors.append(f"平均内存使用: {avg_memory_mb:.1f}MB")
        result.errors.append(f"内存增长率: {memory_growth_rate:.2f}MB/s")
        
        return result
    
    async def run_all_memory_tests(self):
        """运行所有内存压力测试"""
        self.logger.info("开始运行所有内存压力测试")
        
        results = []
        
        # 内存分配测试
        self.logger.info("执行内存分配测试...")
        result1 = await self.memory_allocation_test(
            max_memory_mb=300,
            chunk_size_mb=10,
            duration=60
        )
        results.append(result1)
        self.framework.save_test_report(result1)
        
        # 等待系统恢复
        await asyncio.sleep(10)
        
        # 内存泄漏模拟测试
        self.logger.info("执行内存泄漏模拟测试...")
        result2 = await self.memory_leak_simulation_test(duration=90)
        results.append(result2)
        self.framework.save_test_report(result2)
        
        # 等待系统恢复
        await asyncio.sleep(10)
        
        # CPU和内存组合测试
        self.logger.info("执行CPU和内存组合测试...")
        result3 = await self.cpu_memory_combined_test(
            cpu_workers=2,
            memory_load_mb=150,
            duration=60
        )
        results.append(result3)
        self.framework.save_test_report(result3)
        
        # 等待系统恢复
        await asyncio.sleep(10)
        
        # 垃圾回收压力测试
        self.logger.info("执行垃圾回收压力测试...")
        result4 = await self.garbage_collection_stress_test(duration=60)
        results.append(result4)
        self.framework.save_test_report(result4)
        
        return results


async def main():
    """主函数"""
    framework = StressTestFramework()
    tester = MemoryStressTester(framework)
    
    try:
        results = await tester.run_all_memory_tests()
        
        print(f"\n内存压力测试完成，共执行 {len(results)} 个测试")
        print("详细报告已保存到 test_reports 目录")
        
    except Exception as e:
        logging.error(f"内存压力测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
