import requests
from bs4 import BeautifulSoup
import re
import os
import time
from urllib.parse import urljoin
from typing import List, Dict, Optional
import json


class HabrArticleParser:
    def __init__(self, target_tags: List[str], max_articles_per_tag: int = 5):
        self.base_url = "https://habr.com"
        self.target_tags = target_tags
        self.max_articles_per_tag = max_articles_per_tag
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        os.makedirs("habr_articles", exist_ok=True)
    
    def get_articles_by_tag(self, tag: str) -> List[str]:
        """Поиск статей по тегу"""
        articles_urls = []
        
        print(f"\n🔍 Поиск статей по тегу: {tag}")
        
        try:
            # Преобразуем тег для URL
            tag_formatted = tag.lower().replace(' ', '_').replace('-', '_')
            
            # Для популярных тегов используем хабы
            hub_mapping = {
                'python': 'python',
                'искусственный интеллект': 'machine_learning',
                'javascript': 'javascript',
                'машинное обучение': 'machine_learning',
                'ai': 'artificial_intelligence',
            }
            
            hub_name = hub_mapping.get(tag.lower(), tag_formatted)
            url = f"{self.base_url}/ru/hub/{hub_name}/"
            
            print(f"  Используем URL: {url}")
            
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем статьи
            article_elements = soup.find_all('article', class_='tm-articles-list__item')
            
            if not article_elements:
                article_elements = soup.find_all('h2', class_='tm-title')
            
            for i, article in enumerate(article_elements[:self.max_articles_per_tag]):
                if len(articles_urls) >= self.max_articles_per_tag:
                    break
                
                # Ищем ссылку
                link_element = None
                if hasattr(article, 'find'):
                    link_element = article.find('a', class_='tm-title__link')
                
                if not link_element and hasattr(article, 'parent'):
                    link_element = article.parent.find('a')
                
                if link_element and link_element.get('href'):
                    href = link_element['href']
                    if '/articles/' in href or '/post/' in href:
                        full_url = urljoin(self.base_url, href)
                        full_url = full_url.split('?')[0]
                        
                        if full_url not in articles_urls:
                            articles_urls.append(full_url)
                            print(f"  ✅ Найдена статья {i+1}")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ Ошибка при поиске: {e}")
        
        print(f"📊 Найдено статей: {len(articles_urls)}")
        return articles_urls
    
    def extract_article_text(self, soup: BeautifulSoup) -> str:
        """Извлечение текста статьи"""
        try:
            # Ищем основной контент
            article_body = soup.find('div', id='post-content-body')
            
            if not article_body:
                article_body = soup.find('div', class_='tm-article-body')
            
            if not article_body:
                article_body = soup.find('article')
            
            if not article_body:
                return "Текст статьи не найден"
            
            # Удаляем комментарии и рекламу
            for element in article_body.find_all(class_=lambda x: x and any(
                word in x.lower() for word in ['comment', 'discuss', 'recommended', 'adv', 'ad']
            )):
                element.decompose()
            
            # Получаем текст
            text = article_body.get_text(separator='\n', strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            return text
            
        except Exception as e:
            print(f"  ❌ Ошибка извлечения текста: {e}")
            return "Ошибка при извлечении текста"
    
    def parse_article(self, url: str) -> Optional[Dict]:
        """Парсинг статьи с правильным поиском тегов"""
        print(f"\n📖 Парсинг: {url}")
        
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Автор
            author = "Неизвестный автор"
            author_elem = soup.find('a', class_='tm-user-info__username')
            if author_elem:
                author = author_elem.text.strip().split('·')[0].strip()
            
            print(f"  👤 Автор: {author}")
            
            # 2. Заголовок
            title = "Без названия"
            title_elem = soup.find('h1', class_='tm-title')
            if title_elem:
                title = title_elem.find('span').text.strip() if title_elem.find('span') else title_elem.text.strip()
            
            print(f"  📝 Заголовок: {title[:80]}...")
            
            # 3. ТЕГИ - ИСПРАВЛЕННЫЙ ПОИСК
            tags = []
            
            # Способ 1: Основной контейнер тегов на Хабре
            tags_container = soup.find('div', class_='tm-publication-hubs')
            
            # Способ 2: Альтернативный поиск
            if not tags_container:
                tags_container = soup.find('div', class_='tm-article-presenter__meta-list')
            
            # Способ 3: Поиск всех ссылок с классом hub-link
            if not tags_container:
                hub_links = soup.find_all('a', class_='tm-hubs-list__link')
                tags = [link.text.strip() for link in hub_links if link.text.strip()]
            
            # Способ 4: Поиск в meta-тегах
            if not tags:
                meta_tags = soup.find_all('meta', {'name': 'keywords'})
                if meta_tags:
                    keywords = meta_tags[0].get('content', '')
                    tags = [k.strip() for k in keywords.split(',') if k.strip()]
            
            # Обрабатываем найденный контейнер
            if tags_container and not tags:
                # Ищем теги внутри контейнера
                tag_links = tags_container.find_all('a')
                for link in tag_links:
                    tag_text = link.text.strip()
                    if tag_text and tag_text not in ['...', '']:
                        tags.append(tag_text)
            
            print(f"  🏷️  Найдено тегов: {len(tags)}")
            if tags:
                print(f"  🏷️  Теги: {', '.join(tags[:5])}")
            
            # 4. Текст статьи
            content = self.extract_article_text(soup)
            print(f"  📄 Длина текста: {len(content)} символов")
            
            return {
                'author': author,
                'url': url,
                'title': title,
                'tags': tags,
                'content': content
            }
            
        except Exception as e:
            print(f"  ❌ Ошибка парсинга: {e}")
            return None
    
    def save_article_to_txt(self, article_data: Dict, tag: str, index: int):
        """Сохранение статьи"""
        try:
            safe_title = re.sub(r'[^\w\s-]', '', article_data['title'])
            safe_title = re.sub(r'[-\s]+', '_', safe_title)[:50]
            
            filename = f"habr_articles/{tag}_{index:03d}_{safe_title}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{article_data['author']}\n")
                f.write(f"{article_data['url']}\n")
                f.write(f"{article_data['title']}\n")
                
                # ТЕГИ - всегда записываем, даже если пустые
                tags_str = ', '.join(article_data['tags']) if article_data['tags'] else 'Нет тегов'
                f.write(f"{tags_str}\n\n")
                
                f.write(article_data['content'])
            
            print(f"  💾 Сохранено: {filename}")
            print(f"  📝 Теги в файле: {tags_str}")
            return True
            
        except Exception as e:
            print(f"  ❌ Ошибка сохранения: {e}")
            return False
    
    def run(self):
        """Запуск парсера"""
        print("=" * 60)
        print("ПАРСЕР HABR С ИСПРАВЛЕННЫМИ ТЕГАМИ")
        print("=" * 60)
        
        for tag in self.target_tags:
            print(f"\n{'='*60}")
            print(f"ТЕГ: {tag.upper()}")
            print(f"{'='*60}")
            
            articles = self.get_articles_by_tag(tag)
            
            for i, url in enumerate(articles, 1):
                print(f"\n--- Статья {i}/{len(articles)} ---")
                article_data = self.parse_article(url)
                
                if article_data:
                    self.save_article_to_txt(article_data, tag, i)
                
                time.sleep(1)
        
        print(f"\n{'='*60}")
        print("ГОТОВО! Проверьте файлы в папке habr_articles/")
        print(f"{'='*60}")


def test_tags_on_example():
    """Тестовая функция для проверки поиска тегов на конкретной статье"""
    test_url = "https://habr.com/ru/companies/nix/articles/342904/"
    
    print("🔍 Тестируем поиск тегов на примере статьи...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(test_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("\n1. Поиск по class='tm-publication-hubs':")
    hubs = soup.find_all('div', class_='tm-publication-hubs')
    print(f"   Найдено элементов: {len(hubs)}")
    for i, hub in enumerate(hubs[:3]):
        print(f"   Элемент {i+1}: {hub}")
        if hub.find('a'):
            print(f"   Теги внутри: {[a.text.strip() for a in hub.find_all('a')]}")
    
    print("\n2. Поиск по class='tm-article-presenter__meta-list':")
    meta_list = soup.find_all('div', class_='tm-article-presenter__meta-list')
    print(f"   Найдено: {len(meta_list)}")
    
    print("\n3. Поиск всех элементов с 'hub' в классе:")
    all_hub_elements = soup.find_all(class_=lambda x: x and 'hub' in x.lower())
    print(f"   Найдено: {len(all_hub_elements)}")
    for elem in all_hub_elements[:5]:
        print(f"   Класс: {elem.get('class')}, Текст: {elem.text[:50]}...")
    
    print("\n4. Поиск всех ссылок с тегами:")
    all_links = soup.find_all('a')
    tag_links = []
    for link in all_links:
        href = link.get('href', '')
        text = link.text.strip()
        if '/hub/' in href and text:
            tag_links.append((text, href))
    
    print(f"   Найдено ссылок на хабы: {len(tag_links)}")
    for text, href in tag_links[:10]:
        print(f"   Тег: '{text}', Ссылка: {href}")


def main():
    # Сначала протестируйте
    #test_tags_on_example()
    
    # Затем запустите парсер
    target_tags = ['Python', 'Искусственный интеллект', 'JavaScript']
    parser = HabrArticleParser(target_tags, max_articles_per_tag=20)
    parser.run()


if __name__ == "__main__":
    main()