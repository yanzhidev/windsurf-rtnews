"""
新闻流生成器模块
"""
import asyncio
import json
import sys
import time
from collections import deque
from src.utils.config import NEWS_CONFIG, BACKPRESSURE_CONFIG


class NewsStreamGenerator:
    """新闻流生成器"""
    
    def __init__(self, backpressure_controller, news_processor, ws_manager, news_buffer):
        self.backpressure_controller = backpressure_controller
        self.news_processor = news_processor
        self.ws_manager = ws_manager
        self.news_buffer = news_buffer
    
    async def generate_protected_news_stream(self):
        """生成受保护的新闻流"""
        try:
            print("📡 启动受保护的新闻生成器...")
            
            # 尝试导入高频新闻生成器
            try:
                from src.generators.high_frequency_news import HighFreqNewsGenerator
                generator = HighFreqNewsGenerator()
            except ImportError:
                print("⚠️ 无法导入 high_freq_news，使用内置生成器")
                generator = self._create_simple_generator()
            
            duration = NEWS_CONFIG['test_duration']
            news_per_second = NEWS_CONFIG['news_per_second']
            
            start_time = time.time()
            total_generated = 0
            stats_counter = 0
            memory_check_counter = 0
            
            while time.time() - start_time < duration:
                second_start = time.time()
                
                # 检查背压状态 - 使用统一的等待逻辑
                if self.backpressure_controller.is_paused:
                    print(f"⏸️ 处理已暂停: {self.backpressure_controller.pause_reason}")
                    await self.backpressure_controller.wait_for_resume()
                
                # 每秒生成指定数量的新闻
                for i in range(news_per_second):
                    # 检查背压
                    if self.backpressure_controller.is_paused:
                        break
                    
                    news_item = generator.generate_news_item()
                    processed_news = self.news_processor.process_news(news_item)
                    
                    if processed_news:
                        # 添加到缓冲区
                        self.news_buffer.append(processed_news)
                        total_generated += 1
                        
                        # 安全的广播
                        await self.ws_manager.broadcast_news(processed_news, self.backpressure_controller)
                        
                        # 定期广播统计信息
                        if processed_news['processing_id'] % NEWS_CONFIG['stats_broadcast_interval'] == 0:
                            stats = self.news_processor.get_statistics(
                                buffer_size=len(self.news_buffer),
                                active_connections=len(self.ws_manager.active_connections),
                                broadcast_stats=self.ws_manager.broadcast_stats
                            )
                            await self.ws_manager.broadcast_statistics(stats)
                            stats_counter += 1
                        
                        # 定期打印进度
                        if processed_news['processing_id'] % NEWS_CONFIG['progress_report_interval'] == 0:
                            elapsed = time.time() - start_time
                            rate = total_generated / elapsed
                            print(f"📰 已生成 {total_generated} 条新闻，速率: {rate:.2f}条/秒，统计广播: {stats_counter} 次")
                
                # 定期检查内存使用
                memory_check_counter += 1
                if memory_check_counter % BACKPRESSURE_CONFIG['memory_check_interval'] == 0:
                    memory_high = await self.backpressure_controller.check_memory_usage()
                    if memory_high:
                        await self.backpressure_controller.pause_processing("内存使用过高")
                        # 强制垃圾回收
                        import gc
                        gc.collect()
                
                # 控制每秒的时间
                second_elapsed = time.time() - second_start
                if second_elapsed < 1.0:
                    await asyncio.sleep(1.0 - second_elapsed)
            
            total_time = time.time() - start_time
            actual_rate = total_generated / total_time
            
            print(f"✅ 受保护新闻生成完成！")
            print(f"📊 总生成: {total_generated} 条")
            print(f"⏱️ 总耗时: {total_time:.2f} 秒")
            print(f"🚀 实际速率: {actual_rate:.2f} 条/秒")
            print(f"📡 统计广播: {stats_counter} 次")
            print(f"🛡️ 拒绝处理: {self.news_processor.rejected_count} 条")
            print(f"⚠️ 内存保护触发: {self.ws_manager.broadcast_stats['memory_protection_triggers']} 次")
            print(f"🛑 背压事件: {self.ws_manager.broadcast_stats['backpressure_events']} 次")
            
        except Exception as e:
            print(f"❌ Error generating news stream: {e}")

    async def safe_read_news_stream(self):
        """安全读取新闻流 - 带背压控制"""
        try:
            print("📡 启动安全新闻流读取器...")
            
            # 启动 mock_stream.py 作为子进程
            process = await asyncio.create_subprocess_exec(
                sys.executable, 'src/generators/mock_news_stream.py',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            from src.core.protected_news_processor import SafeStreamReader
            reader = SafeStreamReader(self.backpressure_controller)
            
            print("📡 安全流读取器已启动")
            
            while True:
                # 安全读取一行
                line = await reader.read_line_safe(process.stdout)
                
                if line is None:
                    # 检查进程是否结束
                    if process.returncode is not None:
                        print(f"📡 新闻流进程结束，退出码: {process.returncode}")
                        break
                    continue
                
                # 处理有效的JSON行
                if line and line.startswith('{'):
                    try:
                        news_item = json.loads(line)
                        processed_news = self.news_processor.process_news(news_item)
                        
                        if processed_news:
                            # 添加到缓冲区
                            self.news_buffer.append(processed_news)
                            
                            # 安全广播
                            await self.ws_manager.broadcast_news(processed_news, self.backpressure_controller)
                            
                            # 定期广播统计信息
                            if processed_news['processing_id'] % 10 == 0:
                                stats = self.news_processor.get_statistics(
                                    buffer_size=len(self.news_buffer),
                                    active_connections=len(self.ws_manager.active_connections),
                                    broadcast_stats=self.ws_manager.broadcast_stats
                                )
                                await self.ws_manager.broadcast_statistics(stats)
                            
                            # 打印进度
                            if processed_news['processing_id'] % 100 == 0:
                                print(f"📰 处理新闻 [{processed_news['processing_id']}] {processed_news['title'][:50]}...")
                                
                    except json.JSONDecodeError:
                        continue
                        
                # 定期打印读取统计
                if reader.lines_processed % 1000 == 0 and reader.lines_processed > 0:
                    stats = reader.get_stats()
                    print(f"📊 读取统计: {stats['lines_processed']} 行, {stats['bytes_processed']} 字节, {stats['errors_count']} 错误")
                    
        except Exception as e:
            print(f"❌ 安全流读取错误: {e}")
        finally:
            # 确保子进程被清理
            if 'process' in locals():
                process.terminate()
                await process.wait()

    def _create_simple_generator(self):
        """创建简单的新闻生成器"""
        import random
        from datetime import datetime
        
        class SimpleGenerator:
            def __init__(self):
                self.news_sources = ["TechCrunch", "Wired", "Ars Technica", "The Verge"]
                self.tech_companies = ["OpenAI", "Google", "Microsoft", "Apple", "Meta"]
                self.news_categories = ["AI", "Cloud", "Security", "Mobile"]
                self.counter = 0
            
            def generate_news_item(self):
                self.counter += 1
                return {
                    "id": f"news_{int(time.time() * 1000)}_{self.counter}",
                    "timestamp": datetime.now().isoformat(),
                    "source": random.choice(self.news_sources),
                    "title": f"Generated News {self.counter}",
                    "summary": f"Generated news summary {self.counter}",
                    "category": random.choice(self.news_categories),
                    "company": random.choice(self.tech_companies),
                    "impact_score": round(random.uniform(1.0, 10.0), 2),
                    "url": f"https://example.com/news/{self.counter}"
                }
        
        return SimpleGenerator()
