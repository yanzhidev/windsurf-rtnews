import asyncio
import time
import multiprocessing
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import statistics

class GILComparison:
    def __init__(self):
        self.results = {
            'single_thread': {},
            'multi_thread': {},
            'multi_process': {}
        }
    
    def cpu_intensive_task(self, n: int) -> int:
        """CPU密集型任务"""
        total = 0
        for i in range(n):
            total += i * i
        return total
    
    async def async_cpu_task(self, n: int) -> int:
        """异步CPU密集型任务"""
        return self.cpu_intensive_task(n)
    
    def single_thread_test(self, task_count: int = 1000000):
        """单线程测试"""
        print("🧵 单线程测试...")
        start_time = time.time()
        
        for i in range(10):  # 10个任务
            result = self.cpu_intensive_task(task_count)
        
        end_time = time.time()
        duration = end_time - start_time
        
        self.results['single_thread'] = {
            'duration': duration,
            'tasks_per_second': 10 / duration
        }
        
        print(f"  ⏱️ 耗时: {duration:.3f}秒")
        print(f"  🚀 任务速率: {self.results['single_thread']['tasks_per_second']:.2f} 任务/秒")
    
    async def async_single_thread_test(self, task_count: int = 1000000):
        """异步单线程测试"""
        print("🔄 异步单线程测试...")
        start_time = time.time()
        
        tasks = []
        for i in range(10):  # 10个异步任务
            tasks.append(self.async_cpu_task(task_count))
        
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        self.results['async_single_thread'] = {
            'duration': duration,
            'tasks_per_second': 10 / duration
        }
        
        print(f"  ⏱️ 耗时: {duration:.3f}秒")
        print(f"  🚀 任务速率: {self.results['async_single_thread']['tasks_per_second']:.2f} 任务/秒")
    
    def multi_thread_test(self, task_count: int = 1000000):
        """多线程测试"""
        print("🧵 多线程测试...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(10):  # 10个任务
                future = executor.submit(self.cpu_intensive_task, task_count)
                futures.append(future)
            
            # 等待所有任务完成
            for future in futures:
                result = future.result()
        
        end_time = time.time()
        duration = end_time - start_time
        
        self.results['multi_thread'] = {
            'duration': duration,
            'tasks_per_second': 10 / duration
        }
        
        print(f"  ⏱️ 耗时: {duration:.3f}秒")
        print(f"  🚀 任务速率: {self.results['multi_thread']['tasks_per_second']:.2f} 任务/秒")
    
    def multi_process_test(self, task_count: int = 1000000):
        """多进程测试"""
        print("🔧 多进程测试...")
        start_time = time.time()
        
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(10):  # 10个任务
                future = executor.submit(self.cpu_intensive_task, task_count)
                futures.append(future)
            
            # 等待所有任务完成
            for future in futures:
                result = future.result()
        
        end_time = time.time()
        duration = end_time - start_time
        
        self.results['multi_process'] = {
            'duration': duration,
            'tasks_per_second': 10 / duration
        }
        
        print(f"  ⏱️ 耗时: {duration:.3f}秒")
        print(f"  🚀 任务速率: {self.results['multi_process']['tasks_per_second']:.2f} 任务/秒")
    
    def run_comparison(self):
        """运行完整对比测试"""
        print("🔍 GIL影响对比测试")
        print("="*50)
        
        # 运行所有测试
        self.single_thread_test()
        print()
        
        asyncio.run(self.async_single_thread_test())
        print()
        
        self.multi_thread_test()
        print()
        
        self.multi_process_test()
        print()
        
        # 打印对比结果
        self.print_comparison()
    
    def print_comparison(self):
        """打印对比结果"""
        print("📊 GIL影响对比结果")
        print("="*50)
        
        # 创建对比表格
        print(f"{'测试方式':<15} {'耗时(秒)':<10} {'任务/秒':<12} {'相对性能':<10}")
        print("-" * 50)
        
        baseline = self.results['single_thread']['duration']
        
        # 单线程基准
        single = self.results['single_thread']
        relative_perf = (baseline / single['duration']) * 100
        print(f"{'单线程':<15} {single['duration']:<10.3f} {single['tasks_per_second']:<12.2f} {relative_perf:<10.1f}%")
        
        # 异步单线程
        if 'async_single_thread' in self.results:
            async_single = self.results['async_single_thread']
            relative_perf = (baseline / async_single['duration']) * 100
            print(f"{'异步单线程':<15} {async_single['duration']:<10.3f} {async_single['tasks_per_second']:<12.2f} {relative_perf:<10.1f}%")
        
        # 多线程
        multi_thread = self.results['multi_thread']
        relative_perf = (baseline / multi_thread['duration']) * 100
        print(f"{'多线程':<15} {multi_thread['duration']:<10.3f} {multi_thread['tasks_per_second']:<12.2f} {relative_perf:<10.1f}%")
        
        # 多进程
        multi_process = self.results['multi_process']
        relative_perf = (baseline / multi_process['duration']) * 100
        print(f"{'多进程':<15} {multi_process['duration']:<10.3f} {multi_process['tasks_per_second']:<12.2f} {relative_perf:<10.1f}%")
        
        print("\n🔍 分析结论:")
        
        # 分析GIL影响
        thread_improvement = (self.results['single_thread']['duration'] / self.results['multi_thread']['duration'] - 1) * 100
        process_improvement = (self.results['single_thread']['duration'] / self.results['multi_process']['duration'] - 1) * 100
        
        if thread_improvement < 10:
            print(f"⚠️ 多线程性能提升仅 {thread_improvement:.1f}% - GIL限制了CPU密集型任务的并发")
        else:
            print(f"✅ 多线程性能提升 {thread_improvement:.1f}%")
        
        if process_improvement > 50:
            print(f"🚀 多进程性能提升 {process_improvement:.1f}% - 有效绕过GIL限制")
        else:
            print(f"⚠️ 多进程性能提升 {process_improvement:.1f}%")
        
        # 对压力测试的建议
        print(f"\n📋 对压力测试的建议:")
        print(f"1. 🧵 CPU密集型任务(如新闻生成)应使用多进程")
        print(f"2. 🌐 I/O密集型任务(如网络请求)可以使用多线程/异步")
        print(f"3. 🔗 混合工作负载建议进程+线程混合使用")
        
        print("="*50)

def main():
    """主函数"""
    comparison = GILComparison()
    comparison.run_comparison()

if __name__ == "__main__":
    import sys
    if sys.platform.startswith('darwin'):  # macOS
        multiprocessing.set_start_method('spawn', force=True)
    elif sys.platform.startswith('win'):  # Windows
        multiprocessing.set_start_method('spawn', force=True)
    
    main()
