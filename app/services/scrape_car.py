import asyncio
import re

import httpx
from playwright.async_api import TimeoutError as PWTimeout
from playwright.async_api import async_playwright

from app.models import Car, now_time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
}


async def enrich_phone(client: httpx.AsyncClient, car: Car, page_url: str) -> Car:
    phone = await parce_phone_number(
        client, page_url, nav_timeout=30000, phone_timeout=10000
    )
    if phone is None:
        await asyncio.sleep(1.0)
        phone = await parce_phone_number(
            client, page_url, nav_timeout=45000, phone_timeout=20000
        )

    car.phone_number = phone
    return car


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


async def parce_phone_number(
    client,
    page_url: str,
    nav_timeout: int = 30000,
    phone_timeout: int = 10000,
) -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(
                page_url, wait_until="domcontentloaded", timeout=nav_timeout
            )

            button = page.locator("button.size-large.conversion").first
            if await button.count() == 0:
                return None

            await button.scroll_into_view_if_needed()
            await button.click(timeout=5000)

            phone_link = page.locator('#autoPhonePopUpResponse a[href^="tel:"]').first
            await phone_link.wait_for(timeout=phone_timeout)

            href = await phone_link.get_attribute("href")
            if not href:
                return None

            return normalize_ua_phone(href.replace("tel:", ""))

        except PWTimeout as e:
            return None
        except Exception as e:
            return None
        finally:
            await browser.close()


def parse_car(tree) -> Car:
    return Car(
        url=None,
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
