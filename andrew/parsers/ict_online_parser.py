# parsers/ict_online_parser.py
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from core.logging_config import logger
from typing import Dict

async def parse_ict_online_article(url: str) -> Dict:
    """Парсер статей с ICT-Online.ru"""
    
    logger.info("parsing_ict_online", url=url)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers={
                'User-Agent': 'ArticleSearchAgent/1.0'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Извлекаем заголовок
            title_elem = soup.find('h1') or soup.find('title')
            title = title_elem.text.strip() if title_elem else "Без заголовка"
            
            # Извлекаем содержимое статьи
            content_elem = soup.find('article') or soup.find('div', class_=lambda x: x and 'content' in x)
            content = content_elem.text.strip() if content_elem else ""
            
            # Извлекаем дату
            date_elem = soup.find('time') or soup.find('span', class_=lambda x: x and 'date' in x.lower())
            date_str = date_elem['datetime'] if date_elem and date_elem.get('datetime') else date_elem.text if date_elem else ""
            
            # Парсим дату
            try:
                published_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date().isoformat()
            except:
                published_date = datetime.now().date().isoformat()
            
            # Извлекаем автора
            author_elem = soup.find('a', class_=lambda x: x and 'author' in x.lower()) or soup.find('span', class_=lambda x: x and 'author' in x.lower())
            author = author_elem.text.strip() if author_elem else "Редакция ICT-Online"
            
            # Определяем тематику (можно улучшить с помощью ML)
            thematic = "Кибербезопасность" if any(word in title.lower() for word in ['ntlm', 'безопасност', 'атака', 'уязвим']) else "ИТ-инфраструктура"
            
            return {
                "id": f"ict_{hash(url)}",
                "title": title,
                "content": content,
                "url": url,
                "date": published_date,
                "author": author,
                "source": "ICT-Online.ru",
                "thematic": thematic,
                "tags": ["кибербезопасность", "NTLM", "корпоративная инфраструктура"]
            }
            
        except Exception as e:
            logger.error("ict_online_parsing_error", url=url, error=str(e))
            raise