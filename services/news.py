# services/news.py
import feedparser
import logging
import aiohttp

# Надёжный публичный RSS РБК
RSS_URL = "http://tass.ru/rss/v2.xml?sections=MjU%3D"

async def get_top_news(n: int = 3) -> str:
    """
    Асинхронно берёт топ N новостей из RSS РБК через aiohttp.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(RSS_URL, headers={"User-Agent":"Mozilla/5.0"}, timeout=10) as resp:
                data = await resp.text()
        feed = feedparser.parse(data)
        entries = getattr(feed, 'entries', [])[:n]
        if not entries:
            return "Не удалось получить новости."

        lines = []
        for entry in entries:
            title = entry.get('title', 'Нет заголовка') if isinstance(entry, dict) else getattr(entry, 'title', 'Нет заголовка')
            link  = entry.get('link', '')               if isinstance(entry, dict) else getattr(entry, 'link', '')
            lines.append(f"• <b>{title}</b>\n{link}")
        return "\n\n".join(lines)

    except Exception:
        logging.exception("Ошибка получения новостей RSS")
        return "Ошибка при получении новостей."