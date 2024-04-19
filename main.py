import os
import re
import httpx
import asyncio
import telebot
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

class GatewayCheckerBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.session = httpx.AsyncClient(http2=True)
        self.ua = UserAgent()
        self.loop = asyncio.get_event_loop()  # Use a single event loop throughout
        self.initialize_handlers()

    def initialize_handlers(self):
        @self.bot.message_handler(commands=['start', 'cmds'])
        def send_welcome(message):
            commands = (
                "Welcome to Gateway Checker Bot! Here are the commands you can use:\n"
                "/start - Welcome message.\n"
                "/cmds - Command list.\n"
                "/checkurl <URLs> - Check specified URLs for payment gateways.\n"
                "/dork <query> - Perform Google dorking with the provided query.\n"
                "Dev @fizzyy24"
            )
            self.bot.reply_to(message, commands)

        @self.bot.message_handler(commands=['checkurl'])
        def handle_check_url(message):
            self.loop.create_task(self.check_url(message))

    async def check_url(self, message):
        urls = message.text.split()[1:]
        if not urls:
            await self.bot.send_message(message.chat.id, "No URLs provided. Please provide one or more URLs after the /checkurl command.")
            return
        responses = await self.process_urls(urls)
        for response in responses:
            await self.bot.send_message(message.chat.id, response)

    async def process_urls(self, urls):
        corrected_urls = [self.ensure_protocol(url) for url in urls]
        tasks = [self.check_gateway(url) for url in corrected_urls]
        results = await asyncio.gather(*tasks)
        return results

    def ensure_protocol(self, url):
        if not url.startswith(('http://', 'https://')):
            return 'http://' + url
        return url

    async def check_gateway(self, url):
        try:
            headers = {'User-Agent': self.ua.random}
            response = await self.session.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            detected_gateways = self.detect_payment_gateways(soup)
            captcha = '✅ CAPTCHA detected.' if soup.find('script', {'src': re.compile(r'recaptcha/api.js')}) else '✅ No CAPTCHA detected.'
            cloudflare = '🛑 Cloudflare protection detected.' if soup.find('script', {'src': re.compile(r'cdn-cgi/scripts/captcha')}) else '🛑 No Cloudflare protection detected.'
            msg = f'🔒 𝙎𝙄𝙏𝙀 ➜ {url}\n\n'
            if detected_gateways:
                msg += f'𝗗𝗲𝘁𝗲𝗰𝘁𝗲𝗱 𝗚𝗮𝘁𝗲𝘄𝗮𝘆𝘀 : {", ".join(detected_gateways)}\n'
            else:
                msg += 'No payment gateway detected.\n'
            msg += f'{captcha}\n{cloudflare}\n\nDev @fizzyy24'
            return msg
        except httpx.RequestError as e:
            return f"Error accessing {url}: {e}"

    def detect_payment_gateways(self, soup):
        patterns = {
           'stripe': re.compile(r'.*js\.stripe\.com.*|.*stripe.*', re.IGNORECASE),
                            'paypal': re.compile(r'.*paypal.*|.*checkout\.paypal\.com.*|.*paypalobjects.*', re.IGNORECASE),
                            'braintree': re.compile(r'.*braintree.*|.*braintreegateway.*|.*js\.braintreegateway\.com.*', re.IGNORECASE),
                            'worldpay': re.compile(r'.*worldpay.*', re.IGNORECASE),
                            'authnet': re.compile(r'.*authorizenet.*|.*authorize\.net.*', re.IGNORECASE),
                            'recurly': re.compile(r'.*recurly.*', re.IGNORECASE),
                            'shopify': re.compile(r'.*shopify.*', re.IGNORECASE),
                            'square': re.compile(r'.*square.*', re.IGNORECASE),
                            'cybersource': re.compile(r'.*cybersource.*', re.IGNORECASE),
                            'adyen': re.compile(r'.*adyen.*|.*adyen-checkout.*|.*adyen-encrypted-data.*', re.IGNORECASE),
                            '2checkout': re.compile(r'.*2checkout.*', re.IGNORECASE),
                            'authorize.net': re.compile(r'.*authorize\.net.*', re.IGNORECASE),
                            'eway': re.compile(r'.*eway.*', re.IGNORECASE),
                            'bluepay': re.compile(r'.*bluepay.*', re.IGNORECASE),
                            'xendit': re.compile(r'.js\.xendit\.co.*xendit.*', re.IGNORECASE),
                            'hipay': re.compile(r'.*hipay.*', re.IGNORECASE),
                            'chargebee': re.compile(r'.*js\.chargebee\.com.*', re.IGNORECASE),
        }
        found_gateways = []
        for name, regex in patterns.items():
            if soup.find(string=regex) or soup.find('script', {'src': regex}):
                found_gateways.append(name)
        return found_gateways

    async def close(self):
        await self.session.aclose()

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = GatewayCheckerBot(token)
    try:
        bot.bot.polling()
    finally:
        bot.loop.run_until_complete(bot.close())  # Ensure clean closure

if __name__ == "__main__":
    main()
