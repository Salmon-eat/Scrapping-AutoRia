import asyncio
import re

import httpx
from lxml import html as lxml_html
from playwright.async_api import async_playwright

from app.models import Car, now_time

BASE_URL = "https://auto.ria.com/uk/auto_bmw_x3_39304592.html"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
}


async def enrich_phone(client: httpx.AsyncClient, car: Car, page_url: str) -> Car:
    car.phone_number = await parce_phone_number(client, page_url)
    return car


async def main():
    async with httpx.AsyncClient(
        headers=HEADERS, timeout=20, follow_redirects=True
    ) as client:
        response = await client.get(BASE_URL)
        tree = lxml_html.fromstring(response.text)

        car = parse_car(tree)
        car = await enrich_phone(client, car, BASE_URL)
        print(
            car.title,
            car.price_usd,
            car.odometer,
            car.username,
            car.phone_number,
            car.image_url,
            car.images_count,
            car.car_number,
            car.car_vin,
            car.datatime_found,
        )


def xp_text(tree, xp: str) -> str:
    parts = tree.xpath(xp)
    return " ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())


def digits_only(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())


def parse_title(tree) -> str:
    return xp_text(
        tree, '//*[@id="sideTitleTitle"]//span[contains(@class, "titleM")]//text()'
    )


def parse_price_usd(tree) -> int:
    raw = xp_text(
        tree, '//*[@id="sidePrice"]//strong[contains(@class, "titleL")]//text()'
    )
    d = digits_only(raw)
    return int(d) if d else 0


def parse_odometer(tree) -> int:
    raw = xp_text(
        tree,
        '//*[@id="basicInfoTableMainInfo0"]//span[contains(@class, "body")]//text()',
    )
    raw_low = raw.lower()
    d = digits_only(raw)
    if not d:
        return 0
    num = int(d)
    return num * 1000 if "тис" in raw_low else num


def parse_username(tree) -> str:
    return xp_text(
        tree, '//*[@id="sellerInfoUserName"]//span[contains(@class, "titleM")]//text()'
    )


def parse_images_count(tree) -> int:
    raw = xp_text(
        tree, '//*[@id="photoSlider"]//span[contains(@class, "medium")]//text()'
    )
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits[1:]) if digits[1:] else 0


def parce_car_number(tree) -> str:
    return xp_text(tree, '//*[@id="badges"]//span[contains(@class, "body")]//text()')


def parce_car_vin(tree) -> str:
    return xp_text(
        tree, '//*[@id="badgesVinGrid"]//span[contains(@class, "badge")]//text()'
    )


def parce_image_url(tree) -> str:
    return xp_text(tree, '(//img[contains(@src,"photosnew/auto/photo")])[1]/@src')


def normalize_ua_phone(s: str) -> str | None:
    digits = re.sub(r"\D+", "", s)
    if not digits:
        return None
    if digits.startswith("0") and len(digits) == 10:
        return "38" + digits
    if digits.startswith("380") and len(digits) == 12:
        return digits
    return digits


async def parce_phone_number(client, page_url) -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await page.wait_for_selector("button.size-large.conversion", timeout=15000)
        await page.click("button.size-large.conversion")
        await page.wait_for_selector("#autoPhonePopUpResponse", timeout=15000)
        link = page.locator('#autoPhonePopUpResponse a[href^="tel:"]').first
        href = await link.get_attribute("href")

        await browser.close()

        if not href:
            return None

        return normalize_ua_phone(href.replace("tel:", ""))


def parse_car(tree) -> Car:
    return Car(
        title=parse_title(tree),
        price_usd=parse_price_usd(tree),
        odometer=parse_odometer(tree),
        username=parse_username(tree),
        phone_number=None,
        image_url=parce_image_url(tree),
        images_count=parse_images_count(tree),
        car_number=parce_car_number(tree),
        car_vin=parce_car_vin(tree),
        datatime_found=now_time(),
    )


if __name__ == "__main__":
    asyncio.run(main())
