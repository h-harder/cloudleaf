"""Single-user cloud browser. No website passwords or URLs are logged."""
import asyncio
import hmac
import io
import ipaddress
import os
import socket
from contextlib import asynccontextmanager
from urllib.parse import urlsplit, quote
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response, HTMLResponse
from pydantic import BaseModel, Field
from PIL import Image
from playwright.async_api import async_playwright, Error as BrowserError

TOKEN = os.environ.get('BROWSER_TOKEN', '')
lock = asyncio.Lock()
pw = browser = context = page = None

async def public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        return False
    try:
        if parsed.port not in (None, 80, 443):
            return False
        addresses = await asyncio.get_running_loop().getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)
    except (ValueError, OSError):
        return False

async def filter_request(route):
    url = route.request.url
    if route.request.resource_type in ('media', 'websocket'):
        await route.abort()
    elif url.startswith('data:') or await public_url(url):
        await route.continue_()
    else:
        await route.abort()

async def close_session():
    global context, page
    if context:
        await context.close()
    context = page = None

async def get_page(width, height):
    global pw, browser, context, page
    if not browser or not browser.is_connected():
        if pw:
            await pw.stop()
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(args=['--disable-dev-shm-usage', '--disable-gpu'], headless=True)
        context = page = None
    if not page or page.is_closed():
        await close_session()
        context = await browser.new_context(viewport={'width': width, 'height': height},
            device_scale_factor=1, service_workers='block', accept_downloads=False, reduced_motion='reduce')
        await context.route('**/*', filter_request)
        page = await context.new_page()
        page.set_default_timeout(12000)
        # Keep only one tab. Popup-dependent sites are unsupported in this version.
        async def close_popup(popup):
            if popup != page:
                await popup.close()
        context.on('page', close_popup)
        page.on('dialog', lambda dialog: dialog.dismiss())
        await page.set_content('<html><body style="font:28px sans-serif;padding:40px">CloudLeaf<br><br>Use the address field in the toolbar to start browsing.</body></html>')
    elif page.viewport_size != {'width': width, 'height': height}:
        await page.set_viewport_size({'width': width, 'height': height})
    return page

@asynccontextmanager
async def lifespan(app):
    if len(TOKEN) < 24:
        raise RuntimeError('Set BROWSER_TOKEN to a random secret of at least 24 characters.')
    yield
    await close_session()
    if browser:
        await browser.close()
    if pw:
        await pw.stop()

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

class Command(BaseModel):
    action: Literal['view', 'goto', 'click', 'scroll', 'back', 'forward', 'reload', 'type', 'key', 'close'] = 'view'
    width: int = Field(800, ge=300, le=2000)
    height: int = Field(1000, ge=300, le=2400)
    url: str = Field('', max_length=2048)
    x: int = Field(0, ge=0, le=2000)
    y: int = Field(0, ge=0, le=2400)
    dy: int = Field(0, ge=-2400, le=2400)
    text: str = Field('', max_length=4000)
    key: Literal['Enter', 'Backspace', 'Tab', 'Escape'] = 'Enter'

@app.get('/', response_class=HTMLResponse)
async def home():
    return '<h1>CloudLeaf server is awake</h1><p>Connect with the KOReader plugin using this HTTPS address and your secret token.</p>'

@app.get('/health')
async def health():
    return {'ok': True}

@app.post('/frame')
async def frame(command: Command, authorization: str = Header('')):
    if not TOKEN or not hmac.compare_digest(authorization, 'Bearer ' + TOKEN):
        raise HTTPException(401, 'Incorrect browser token')
    if lock.locked():
        raise HTTPException(429, 'Browser busy; try again')
    async with lock:
        try:
            async with asyncio.timeout(35):
                if command.action == 'close':
                    await close_session()
                    return Response(status_code=204)
                p = await get_page(command.width, command.height)
                if command.action == 'goto':
                    if not await public_url(command.url):
                        raise HTTPException(400, 'Use a public HTTP/HTTPS website')
                    await p.goto(command.url, wait_until='domcontentloaded', timeout=20000)
                elif command.action == 'click':
                    if command.x >= command.width or command.y >= command.height:
                        raise HTTPException(400, 'Tap outside viewport')
                    await p.mouse.click(command.x, command.y)
                elif command.action == 'scroll':
                    await p.mouse.wheel(0, command.dy)
                elif command.action == 'back':
                    await p.go_back(wait_until='domcontentloaded')
                elif command.action == 'forward':
                    await p.go_forward(wait_until='domcontentloaded')
                elif command.action == 'reload':
                    await p.reload(wait_until='domcontentloaded')
                elif command.action == 'type':
                    await p.keyboard.insert_text(command.text)
                elif command.action == 'key':
                    await p.keyboard.press(command.key)
                await asyncio.sleep(0.3)
                png = await p.screenshot(type='png', animations='disabled', timeout=10000)
                # 8-bit grayscale: inexpensive to decode on e-ink and smaller to transmit.
                image = Image.open(io.BytesIO(png)).convert('L')
                out = io.BytesIO()
                image.save(out, format='PNG')
                return Response(out.getvalue(), media_type='image/png', headers={'Cache-Control': 'no-store', 'X-CloudLeaf-URL': quote(p.url if p.url.startswith(('http://','https://')) else '', safe='')})
        except HTTPException:
            raise
        except (BrowserError, TimeoutError):
            raise HTTPException(503, 'Browser timed out or ran out of memory. Retry Refresh; reopen if necessary.')
