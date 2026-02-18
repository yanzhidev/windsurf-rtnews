import json
import time
import random
from datetime import datetime
from typing import Dict, Any

class MockNewsStream:
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

    def generate_news_item(self) -> Dict[str, Any]:
        """生成一条模拟新闻"""
        company = random.choice(self.tech_companies)
        category = random.choice(self.news_categories)
        source = random.choice(self.news_sources)
        headline_template = random.choice(self.headline_templates)
        
        # 生成标题
        title = headline_template.format(company=company, category=category)
        
        # 生成内容摘要
        summary = f"Latest developments in {category} as {company} continues to push boundaries in technology innovation."
        
        # 生成随机影响分数
        impact_score = random.uniform(1.0, 10.0)
        
        return {
            "id": f"news_{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "title": title,
            "summary": summary,
            "category": category,
            "company": company,
            "impact_score": round(impact_score, 2),
            "url": f"https://example.com/news/{int(time.time())}"
        }

    def stream_news(self, interval: int = 3):
        """持续生成新闻流"""
        print("🚀 Starting mock news stream...")
        print(f"📰 Generating news every {interval} seconds")
        print("-" * 50)
        
        try:
            while True:
                news_item = self.generate_news_item()
                
                # 输出 JSON 格式的新闻（单行）
                print(json.dumps(news_item, ensure_ascii=False))
                print("-" * 50)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 News stream stopped by user")

if __name__ == "__main__":
    stream = MockNewsStream()
    stream.stream_news()
