import asyncio
import json
import time
import random
from datetime import datetime
from typing import Dict, Any

class HighFreqNewsGenerator:
    def __init__(self):
        self.news_sources = [
            "TechCrunch", "Wired", "Ars Technica", "The Verge", 
            "Engadget", "ZDNet", "CNET", " VentureBeat"
        ]
        
        self.tech_companies = [
            "OpenAI", "Google", "Microsoft", "Apple", "Meta", 
            "Tesla", "Amazon", "NVIDIA", "AMD", "Intel"
        ]
        
        self.news_categories = [
            "Artificial Intelligence", "Machine Learning", "Cloud Computing",
            "Cybersecurity", "Mobile Technology", "Web Development",
            "Data Science", "Blockchain", "IoT", "Quantum Computing"
        ]
        
        self.headline_templates = [
            "{company} Announces Revolutionary {category} Breakthrough",
            "New {category} Technology Discovered by {company}",
            "{company} Launches Innovative {category} Platform",
            "Industry Experts: {category} Will Transform Tech Landscape",
            "{company}'s Latest {category} Innovation Sets New Standards"
        ]
        
        self.generated_count = 0
        self.start_time = None

    def generate_news_item(self) -> Dict[str, Any]:
        """生成一条模拟新闻"""
        company = random.choice(self.tech_companies)
        category = random.choice(self.news_categories)
        source = random.choice(self.news_sources)
        headline_template = random.choice(self.headline_templates)
        
        title = headline_template.format(company=company, category=category)
        summary = f"Latest developments in {category} as {company} continues to push boundaries in technology innovation."
        impact_score = random.uniform(1.0, 10.0)
        
        self.generated_count += 1
        
        return {
            "id": f"news_{int(time.time() * 1000)}_{self.generated_count}",
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "title": title,
            "summary": summary,
            "category": category,
            "company": company,
            "impact_score": round(impact_score, 2),
            "url": f"https://example.com/news/{int(time.time())}_{self.generated_count}"
        }

    async def generate_burst(self, news_per_second: int = 1000, duration: int = 10):
        """生成突发高频新闻"""
        print(f"🚀 开始生成高频新闻流: {news_per_second}条/秒，持续{duration}秒")
        self.start_time = time.time()
        
        total_news = 0
        
        for second in range(duration):
            second_start = time.time()
            
            # 生成这一秒的新闻
            batch = []
            for i in range(news_per_second):
                news_item = self.generate_news_item()
                batch.append(news_item)
                total_news += 1
            
            # 输出进度
            elapsed = time.time() - self.start_time
            print(f"⏱️ 第{second+1}秒: 生成{len(batch)}条新闻，总计{total_news}条，耗时{elapsed:.2f}s")
            
            # 控制时间
            second_elapsed = time.time() - second_start
            if second_elapsed < 1.0:
                await asyncio.sleep(1.0 - second_elapsed)
        
        total_time = time.time() - self.start_time
        actual_rate = total_news / total_time
        
        print(f"✅ 生成完成！")
        print(f"📊 总新闻数: {total_news}")
        print(f"⏱️ 总耗时: {total_time:.2f}秒")
        print(f"🚀 实际速率: {actual_rate:.2f}条/秒")
        
        return batch

async def main():
    """测试高频新闻生成"""
    generator = HighFreqNewsGenerator()
    
    print("🔥 高频新闻生成器测试")
    print("测试不同频率下的生成性能")
    print()
    
    # 测试不同频率
    test_cases = [
        (100, 5),   # 100条/秒，5秒
        (500, 5),   # 500条/秒，5秒
        (1000, 3),  # 1000条/秒，3秒
    ]
    
    for rate, duration in test_cases:
        print(f"\n🎯 测试案例: {rate}条/秒 × {duration}秒")
        await generator.generate_burst(rate, duration)
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
