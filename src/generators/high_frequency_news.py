"""
高频新闻生成器
"""
import random
import time
from datetime import datetime


class HighFreqNewsGenerator:
    """高频新闻生成器 - 用于压力测试"""
    
    def __init__(self):
        self.news_sources = [
            "TechCrunch", "Wired", "Ars Technica", "The Verge", 
            "Engadget", "ZDNet", "CNET", "VentureBeat", "The Register",
            "MIT Technology Review", "IEEE Spectrum", "New Scientist"
        ]
        
        self.tech_companies = [
            "OpenAI", "Google", "Microsoft", "Apple", "Meta", 
            "Tesla", "Amazon", "NVIDIA", "AMD", "Intel",
            "Samsung", "Sony", "Oracle", "Salesforce", "Adobe"
        ]
        
        self.news_categories = [
            "Artificial Intelligence", "Machine Learning", "Cloud Computing",
            "Cybersecurity", "Mobile Technology", "Blockchain", "IoT", 
            "5G Networks", "Quantum Computing", "Robotics", "AR/VR",
            "Autonomous Vehicles", "Green Tech", "Data Science", "DevOps"
        ]
        
        self.templates = [
            "{company} Launches Revolutionary {category} Solution",
            "Breaking: {company} Announces Major {category} Breakthrough",
            "{company} Unveils Next-Generation {category} Platform",
            "Industry Update: {company} Leads {category} Innovation",
            "{company} Sets New Standard in {category} Technology",
            "Analysis: How {company} is Transforming {category}",
            "{company} Reports Record {category} Performance",
            "Exclusive: {company}'s Secret {category} Project Revealed",
            "{company} Partners with Industry Leaders for {category} Initiative",
            "Market Impact: {company}'s {category} Strategy Reshapes Industry"
        ]
        
        self.counter = 0
    
    def generate_news_item(self):
        """生成新闻项"""
        self.counter += 1
        
        company = random.choice(self.tech_companies)
        category = random.choice(self.news_categories)
        source = random.choice(self.news_sources)
        template = random.choice(self.templates)
        
        news_item = {
            "id": f"news_{int(time.time() * 1000)}_{self.counter}",
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "title": template.format(company=company, category=category),
            "summary": f"In-depth analysis of {company}'s latest developments in {category}. This story covers the technical implications, market impact, and future prospects. Story #{self.counter}",
            "category": category,
            "company": company,
            "impact_score": round(random.uniform(1.0, 10.0), 2),
            "url": f"https://{source.lower().replace(' ', '')}.com/news/{self.counter}",
            "author": f"Tech Reporter {self.counter % 10 + 1}",
            "word_count": random.randint(200, 1500),
            "reading_time": random.randint(1, 10)
        }
        
        return news_item
