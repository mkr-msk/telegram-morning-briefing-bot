import feedparser

RSS_URL = "https://news.yandex.ru/index.rss"

def get_top_news(n=3):
    feed = feedparser.parse(RSS_URL)
    items = feed["items"][:n]
    return "\n\n".join(f"• <b>{i.title}</b>\n{i.link}" for i in items)