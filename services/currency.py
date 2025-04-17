import aiohttp
import xml.etree.ElementTree as ET
from datetime import date, timedelta

async def get_usd_change():
    today = date.today()
    yesterday = today - timedelta(days=1)
    async with aiohttp.ClientSession() as s:
        r1 = await s.get(f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={today:%d/%m/%Y}")
        r2 = await s.get(f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={yesterday:%d/%m/%Y}")
    tree1 = ET.fromstring(await r1.text())
    tree2 = ET.fromstring(await r2.text())
    def parse(tree):
        return float(tree.find(".//Valute[CharCode='USD']/Value").text.replace(',', '.'))
    val1, val2 = parse(tree1), parse(tree2)
    diff = val1 - val2
    sign = "+" if diff >=0 else "-"
    return f"USD/RUB: {val1:.2f} ({sign}{abs(diff):.2f})"