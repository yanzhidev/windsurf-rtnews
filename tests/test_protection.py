import asyncio
import json
import time
import random
import string
from datetime import datetime

class BackpressureTestGenerator:
    """背压测试生成器 - 生成各种异常数据"""
    
    def __init__(self):
        self.normal_count = 0
        self.oversized_count = 0
        self.invalid_json_count = 0
        self.missing_fields_count = 0
        
    def generate_normal_news(self) -> str:
        """生成正常新闻"""
        self.normal_count += 1
        
        news = {
            "id": f"news_{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "source": random.choice(["TechCrunch", "Wired", "Ars Technica"]),
            "title": f"Normal News {self.normal_count}",
            "summary": f"Normal news summary {self.normal_count}",
            "category": random.choice(["AI", "Cloud", "Security"]),
            "company": random.choice(["OpenAI", "Google", "Microsoft"]),
            "impact_score": round(random.uniform(1.0, 10.0), 2),
            "url": f"https://example.com/news/{self.normal_count}"
        }
        
        return json.dumps(news, ensure_ascii=False)
    
    def generate_oversized_news(self, size_mb: int = 2) -> str:
        """生成超大新闻"""
        self.oversized_count += 1
        
        # 创建超大内容
        large_content = ''.join(random.choices(string.ascii_letters + string.digits, k=size_mb * 1024 * 1024))
        
        news = {
            "id": f"oversized_{self.oversized_count}",
            "timestamp": datetime.now().isoformat(),
            "source": "Oversized Source",
            "title": f"Oversized News {self.oversized_count}",
            "summary": f"Oversized summary with large content: {large_content[:100]}...",
            "category": "Oversized",
            "company": "Oversized Corp",
            "impact_score": 10.0,
            "url": f"https://example.com/oversized/{self.oversized_count}",
            "large_content": large_content  # 这个字段会让JSON变得巨大
        }
        
        return json.dumps(news, ensure_ascii=False)
    
    def generate_invalid_json(self) -> str:
        """生成无效JSON"""
        self.invalid_json_count += 1
        
        # 各种无效JSON格式
        invalid_formats = [
            '{"incomplete": json',  # 不完整JSON
            '{"unclosed": "value"',  # 未闭合JSON
            '{"invalid": "quotes"',  # 无效引号
            'not json at all',  # 完全不是JSON
            '{"extra": "comma",}',  # 多余逗号
            '{"nested": {"unclosed": "value"',  # 嵌套未闭合
        ]
        
        return random.choice(invalid_formats)
    
    def generate_missing_fields_news(self) -> str:
        """生成缺少字段的新闻"""
        self.missing_fields_count += 1
        
        # 随机缺少必要字段
        base_news = {
            "id": f"missing_{self.missing_fields_count}",
            "timestamp": datetime.now().isoformat(),
        }
        
        # 随机添加一些字段，但缺少必要的
        if random.random() > 0.5:
            base_news["title"] = f"Missing Fields News {self.missing_fields_count}"
        if random.random() > 0.5:
            base_news["source"] = "Missing Source"
        if random.random() > 0.5:
            base_news["category"] = "Missing Category"
        
        return json.dumps(base_news, ensure_ascii=False)
    
    def generate_malformed_line(self, line_type: str) -> str:
        """生成畸形行"""
        if line_type == "normal":
            return self.generate_normal_news()
        elif line_type == "oversized":
            return self.generate_oversized_news(random.randint(1, 5))
        elif line_type == "invalid_json":
            return self.generate_invalid_json()
        elif line_type == "missing_fields":
            return self.generate_missing_fields_news()
        else:
            return self.generate_normal_news()
    
    def get_stats(self) -> dict:
        """获取生成统计"""
        return {
            "normal_count": self.normal_count,
            "oversized_count": self.oversized_count,
            "invalid_json_count": self.invalid_json_count,
            "missing_fields_count": self.missing_fields_count,
            "total_generated": self.normal_count + self.oversized_count + self.invalid_json_count + self.missing_fields_count
        }

class BackpressureTestStream:
    """背压测试流 - 模拟各种异常情况"""
    
    def __init__(self):
        self.generator = BackpressureTestGenerator()
        self.is_running = False
        
    async def stream_test_data(self, interval: float = 0.1, duration: int = 60):
        """流式发送测试数据"""
        print(f"🧪 开始背压测试流")
        print(f"📊 发送间隔: {interval}秒")
        print(f"⏱️ 测试时长: {duration}秒")
        print("-" * 60)
        
        self.is_running = True
        start_time = time.time()
        
        # 测试序列
        test_sequence = [
            # 阶段1: 正常数据 (10秒)
            ("normal", 10, 0.01),
            
            # 阶段2: 混合异常数据 (20秒)
            ("mixed", 20, 0.05),
            
            # 阶段3: 大量超大数据 (10秒)
            ("oversized_heavy", 10, 0.1),
            
            # 阶段4: 无效JSON数据 (10秒)
            ("invalid_json", 10, 0.02),
            
            # 阶段5: 恢复正常 (10秒)
            ("normal", 10, 0.01),
        ]
        
        try:
            for phase_name, phase_duration, phase_interval in test_sequence:
                if not self.is_running:
                    break
                    
                print(f"🔄 开始阶段: {phase_name} ({phase_duration}秒)")
                phase_start = time.time()
                
                while time.time() - phase_start < phase_duration and self.is_running:
                    if phase_name == "normal":
                        line = self.generator.generate_malformed_line("normal")
                    elif phase_name == "mixed":
                        # 混合各种异常
                        line_type = random.choice(["normal", "normal", "normal", "oversized", "invalid_json", "missing_fields"])
                        line = self.generator.generate_malformed_line(line_type)
                    elif phase_name == "oversized_heavy":
                        line = self.generator.generate_malformed_line("oversized")
                    elif phase_name == "invalid_json":
                        line = self.generator.generate_malformed_line("invalid_json")
                    else:
                        line = self.generator.generate_malformed_line("normal")
                    
                    # 输出行
                    print(line)
                    
                    # 控制发送间隔
                    await asyncio.sleep(phase_interval)
                    
                    # 定期打印统计
                    stats = self.generator.get_stats()
                    if stats['total_generated'] % 50 == 0:
                        print(f"📊 生成统计: 正常{stats['normal_count']}, 超大{stats['oversized_count']}, 无效{stats['invalid_json_count']}, 缺字段{stats['missing_fields_count']}")
                
                print(f"✅ 阶段完成: {phase_name}")
            
        except KeyboardInterrupt:
            print("\n🛑 测试被用户中断")
        finally:
            self.is_running = False
            final_stats = self.generator.get_stats()
            print(f"\n📊 最终生成统计:")
            print(f"  📰 正常新闻: {final_stats['normal_count']}")
            print(f"  📏 超大新闻: {final_stats['oversized_count']}")
            print(f"  ❌ 无效JSON: {final_stats['invalid_json_count']}")
            print(f"  ⚠️ 缺少字段: {final_stats['missing_fields_count']}")
            print(f"  📊 总计生成: {final_stats['total_generated']}")

async def main():
    """主函数"""
    print("🧪 背压保护和内存安全测试工具")
    print("模拟各种异常数据流，测试系统的背压控制和内存保护")
    print()
    
    test_stream = BackpressureTestStream()
    
    try:
        await test_stream.stream_test_data(
            interval=0.01,  # 10ms间隔，高频发送
            duration=60      # 60秒测试
        )
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
