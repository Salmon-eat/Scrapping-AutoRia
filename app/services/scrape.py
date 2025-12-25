import asyncio
import json
from http import client

import httpx
from lxml import html as lxml_html

from app.models import Car

BASE_URL = "https://auto.ria.com/uk/auto_bmw_x3_39304592.html"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
}


async def main():
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        response = await client.get(BASE_URL)
        car = parse_car(response.text)
        print(
            car.title,
            car.price_usd,
            car.odometer,
            car.username,
            car.image_url,
            car.images_count,
            car.car_number,
            car.car_vin,
        )


def xp_text(tree, xp: str) -> str:
    parts = tree.xpath(xp)
    return " ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())


def digits_only(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())


def parse_title(tree) -> str:
    return xp_text(
        tree,
        '//*[@id="sideTitleTitle"]//span[contains(@class, "titleM")]//text()'
    )


def parse_price_usd(tree) -> int:
    raw = xp_text(
        tree,
        '//*[@id="sidePrice"]//strong[contains(@class, "titleL")]//text()'
    )
    d = digits_only(raw)
    return int(d) if d else 0


def parse_odometer(tree) -> int:
    raw = xp_text(
        tree,
        '//*[@id="basicInfoTableMainInfo0"]//span[contains(@class, "body")]//text()'
    )
    raw_low = raw.lower()
    d = digits_only(raw)
    if not d:
        return 0
    num = int(d)
    return num * 1000 if "тис" in raw_low else num


def parse_username(tree) -> str:
    return xp_text(
        tree,
        '//*[@id="sellerInfoUserName"]//span[contains(@class, "titleM")]//text()'
    )

def parse_images_count(tree) -> int:
    raw = xp_text(
        tree,
        '//*[@id="photoSlider"]//span[contains(@class, "medium")]//text()'
    )
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits[1:]) if digits[1:] else 0

def parce_car_number(tree) -> str:
    return xp_text(
        tree,
        '//*[@id="badges"]//span[contains(@class, "body")]//text()'

    )

def parce_car_vin(tree) -> str:
    return xp_text(
        tree,
        '//*[@id="badgesVinGrid"]//span[contains(@class, "badge")]//text()'
    )

def parce_image_url(tree) -> str:
    return xp_text(
        tree,
        '(//img[contains(@src,"photosnew/auto/photo")])[1]/@src'

    )

def parse_car(page) -> Car:
    tree = lxml_html.fromstring(page)
    return Car(
        title=parse_title(tree),
        price_usd=parse_price_usd(tree),
        odometer=parse_odometer(tree),
        username=parse_username(tree),
        image_url=parce_image_url(tree),
        images_count=parse_images_count(tree),
        car_number=parce_car_number(tree),
        car_vin=parce_car_vin(tree)
    )


if __name__ == "__main__":
    asyncio.run(main())


