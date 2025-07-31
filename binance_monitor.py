#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Binance Multi-Pair Trade Monitor
Мониторинг множественных торговых пар на Binance (spot и futures)
"""

import asyncio
import json
import logging
import time
import os
from datetime import datetime
from typing import Dict, Set, List
from collections import defaultdict

import aiohttp
import websockets

# Настройка логирования
def setup_logging():
    """Настройка логирования с параметрами из конфигурации"""
    try:
        from config import LOG_LEVEL, LOG_FILE
        log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    except ImportError:
        log_level = logging.INFO
        LOG_FILE = 'binance_monitor.log'
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class BinanceMultiMonitor:
    def __init__(self, telegram_token: str, min_amount: float = 100000):
        """
        Инициализация монитора для множественных пар
        
        Args:
            telegram_token: Токен Telegram-бота
            min_amount: Минимальная сумма сделки в USD для уведомления
        """
        self.telegram_token = telegram_token
        self.min_amount = min_amount
        self.telegram_url = f"https://api.telegram.org/bot{telegram_token}"
        self.subscribed_users: Set[int] = set()
        self.subscribers_file = "subscribers.json"
        
        # Импортируем конфигурацию
        from config import TRADING_PAIRS, ASSET_EMOJIS, NOTIFICATION_SETTINGS
        self.trading_pairs = TRADING_PAIRS
        self.asset_emojis = ASSET_EMOJIS
        self.notification_settings = NOTIFICATION_SETTINGS
        
        # Статистика по парам
        self.stats = {
            'spot_trades': defaultdict(int),
            'futures_trades': defaultdict(int),
            'notifications_sent': 0,
            'start_time': time.time(),
            'total_trades': 0
        }
        
        # Ограничение уведомлений
        self.notification_timestamps = []
        
        # Загружаем сохраненных подписчиков
        self.load_subscribers()
        
    def load_subscribers(self):
        """Загрузка сохраненных подписчиков из файла"""
        try:
            if os.path.exists(self.subscribers_file):
                with open(self.subscribers_file, 'r') as f:
                    data = json.load(f)
                    self.subscribed_users = set(data.get('subscribers', []))
                    logger.info(f"📥 Загружено {len(self.subscribed_users)} подписчиков из файла")
            else:
                logger.info("📁 Файл подписчиков не найден, создаем новый")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки подписчиков: {e}")
    
    def save_subscribers(self):
        """Сохранение подписчиков в файл"""
        try:
            data = {
                'subscribers': list(self.subscribed_users),
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.subscribed_users)
            }
            with open(self.subscribers_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Сохранено {len(self.subscribed_users)} подписчиков в файл")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения подписчиков: {e}")
    
    def add_subscriber(self, user_id: int):
        """Добавление нового подписчика"""
        if user_id not in self.subscribed_users:
            self.subscribed_users.add(user_id)
            self.save_subscribers()
            logger.info(f"✅ Добавлен новый подписчик: {user_id}")
    
    def get_asset_emoji(self, symbol: str) -> str:
        """Получение эмодзи для актива"""
        # Извлекаем базовый актив из символа (например, BTC из BTCUSDT)
        for asset, emoji in self.asset_emojis.items():
            if asset in symbol.upper():
                return emoji
        return "💱"  # Эмодзи по умолчанию
    
    def can_send_notification(self) -> bool:
        """Проверка лимита уведомлений"""
        current_time = time.time()
        # Удаляем старые записи (старше 1 минуты)
        self.notification_timestamps = [ts for ts in self.notification_timestamps 
                                       if current_time - ts < 60]
        
        max_per_minute = self.notification_settings.get('max_notifications_per_minute', 10)
        return len(self.notification_timestamps) < max_per_minute
    
    async def test_telegram_connection(self):
        """Тестирование подключения к Telegram API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.telegram_url}/getMe") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            bot_info = data['result']
                            logger.info(f"✅ Подключение к Telegram успешно! Бот: @{bot_info['username']}")
                            return True
                    else:
                        logger.error(f"❌ Ошибка подключения к Telegram: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования Telegram: {e}")
            return False
    
    async def get_subscribed_users(self):
        """Получение списка пользователей, подписанных на бота"""
        try:
            # Получаем обновления с большим лимитом
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.telegram_url}/getUpdates?limit=1000&timeout=1") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            new_users = 0
                            for update in data.get('result', []):
                                if 'message' in update:
                                    user_id = update['message']['from']['id']
                                    if user_id not in self.subscribed_users:
                                        self.subscribed_users.add(user_id)
                                        new_users += 1
                            
                            if new_users > 0:
                                self.save_subscribers()
                                logger.info(f"📊 Добавлено {new_users} новых подписчиков")
                            
                            logger.info(f"📊 Всего подписчиков: {len(self.subscribed_users)}")
                            
                            if not self.subscribed_users:
                                logger.warning("⚠️ Подписчиков не найдено! Отправьте сообщение боту в Telegram")
        except Exception as e:
            logger.error(f"Ошибка при получении подписчиков: {e}")
    
    async def update_subscribers_periodically(self):
        """Периодическое обновление списка подписчиков"""
        while True:
            try:
                await asyncio.sleep(300)  # Обновляем каждые 5 минут
                await self.get_subscribed_users()
            except Exception as e:
                logger.error(f"Ошибка периодического обновления подписчиков: {e}")
    
    async def send_telegram_notification(self, message: str):
        """Отправка уведомления всем подписчикам"""
        if not self.subscribed_users:
            logger.warning("⚠️ Нет подписчиков для отправки уведомления")
            return
        
        if not self.can_send_notification():
            logger.warning("⚠️ Превышен лимит уведомлений в минуту")
            return
        
        success_count = 0
        failed_users = []
        
        for user_id in self.subscribed_users:
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        'chat_id': user_id,
                        'text': message,
                        'parse_mode': 'HTML',
                        'disable_web_page_preview': True
                    }
                    async with session.post(f"{self.telegram_url}/sendMessage", json=payload) as response:
                        if response.status == 200:
                            success_count += 1
                        else:
                            response_text = await response.text()
                            if response.status == 403:  # Пользователь заблокировал бота
                                failed_users.append(user_id)
                            logger.warning(f"Ошибка отправки пользователю {user_id}: {response.status}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
        
        # Удаляем заблокировавших пользователей
        if failed_users:
            for user_id in failed_users:
                self.subscribed_users.discard(user_id)
            self.save_subscribers()
            logger.info(f"🗑️ Удалено {len(failed_users)} заблокировавших пользователей")
        
        if success_count > 0:
            self.stats['notifications_sent'] += success_count
            self.notification_timestamps.append(time.time())
            logger.info(f"✅ Уведомление отправлено {success_count} пользователям")
    
    def format_trade_message(self, trade_data: Dict, market_type: str, symbol: str) -> str:
        """Форматирование сообщения о сделке"""
        price = float(trade_data['p'])
        quantity = float(trade_data['q'])
        amount = price * quantity
        timestamp = datetime.fromtimestamp(trade_data['T'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # Определение типа сделки (покупка/продажа)
        is_buyer_maker = trade_data.get('m', False)
        trade_type = "🟢 ПОКУПКА" if not is_buyer_maker else "🔴 ПРОДАЖА"
        
        # Эмодзи для типа рынка и актива
        market_emoji = "💱" if market_type == "SPOT" else "📈"
        asset_emoji = self.get_asset_emoji(symbol)
        
        # Форматирование суммы
        if amount >= 1000000:
            amount_str = f"${amount/1000000:.2f}M"
        elif amount >= 1000:
            amount_str = f"${amount/1000:.1f}K"
        else:
            amount_str = f"${amount:,.0f}"
        
        message = f"""
{market_emoji} <b>{market_type} {symbol.upper()}</b> {asset_emoji}

{trade_type}
💰 Сумма: <b>{amount_str}</b>
💵 Цена: <b>${price:,.4f}</b>
📊 Объём: <b>{quantity:.6f}</b>
⏰ Время: <b>{timestamp}</b>

🔗 <a href="https://www.binance.com/ru/trade/{symbol.upper()}">Открыть Binance</a>
        """.strip()
        
        return message
    
    async def handle_trade(self, message: str, market_type: str, symbol: str):
        """Обработка сделки"""
        try:
            trade_data = json.loads(message)
            price = float(trade_data['p'])
            quantity = float(trade_data['q'])
            amount = price * quantity
            
            # Обновляем статистику
            self.stats['total_trades'] += 1
            if market_type == "SPOT":
                self.stats['spot_trades'][symbol] += 1
            else:
                self.stats['futures_trades'][symbol] += 1
            
            # Проверяем минимальную сумму
            if amount >= self.min_amount:
                formatted_message = self.format_trade_message(trade_data, market_type, symbol)
                await self.send_telegram_notification(formatted_message)
                
        except Exception as e:
            logger.error(f"Ошибка обработки сделки {market_type} {symbol}: {e}")
    
    async def websocket_handler(self, symbol: str, market_type: str):
        """Обработчик WebSocket для одной пары"""
        if market_type == "SPOT":
            ws_url = f"wss://stream.binance.com:9443/ws/{symbol}@trade"
        else:
            ws_url = f"wss://fstream.binance.com/ws/{symbol}@trade"
        
        while True:
            try:
                async with websockets.connect(ws_url) as websocket:
                    logger.info(f"✅ Подключение к {market_type} WebSocket для {symbol.upper()}")
                    
                    async for message in websocket:
                        await self.handle_trade(message, market_type, symbol)
                        
            except Exception as e:
                logger.error(f"Ошибка {market_type} WebSocket для {symbol}: {e}")
                await asyncio.sleep(5)
    
    async def print_stats(self):
        """Вывод статистики"""
        try:
            from config import STATS_INTERVAL
            interval = STATS_INTERVAL
        except ImportError:
            interval = 60
        
        while True:
            await asyncio.sleep(interval)
            runtime = time.time() - self.stats['start_time']
            
            # Подсчет общих сделок
            total_spot = sum(self.stats['spot_trades'].values())
            total_futures = sum(self.stats['futures_trades'].values())
            
            logger.info(f"""
=== 📊 СТАТИСТИКА ===
⏱️ Время работы: {runtime:.0f} сек
💱 Всего SPOT сделок: {total_spot}
📈 Всего FUTURES сделок: {total_futures}
📱 Уведомлений отправлено: {self.stats['notifications_sent']}
👥 Подписчиков: {len(self.subscribed_users)}
💰 Порог суммы: ${self.min_amount:,.0f}
🔄 Мониторинг пар: {len(self.trading_pairs)}
==================
            """)
    
    async def run(self):
        """Запуск монитора"""
        logger.info(f"🚀 Запуск Multi-Pair Binance Monitor (порог: ${self.min_amount:,.0f})")
        logger.info(f"📊 Мониторинг {len(self.trading_pairs)} торговых пар")
        
        # Тестируем подключение к Telegram
        if not await self.test_telegram_connection():
            logger.error("❌ Не удалось подключиться к Telegram. Проверьте токен!")
            return
        
        # Получаем список подписчиков
        await self.get_subscribed_users()
        
        # Создаем задачи для всех пар
        tasks = []
        
        # Добавляем задачи для спота
        if self.notification_settings.get('enable_spot', True):
            for symbol in self.trading_pairs:
                tasks.append(self.websocket_handler(symbol, "SPOT"))
        
        # Добавляем задачи для фьючерсов
        if self.notification_settings.get('enable_futures', True):
            for symbol in self.trading_pairs:
                tasks.append(self.websocket_handler(symbol, "FUTURES"))
        
        # Добавляем задачу статистики
        tasks.append(self.print_stats())
        
        # Добавляем задачу периодического обновления подписчиков
        tasks.append(self.update_subscribers_periodically())
        
        # Запускаем все задачи
        await asyncio.gather(*tasks)

async def main():
    """Главная функция"""
    # Импортируем конфигурацию
    try:
        from config import TELEGRAM_TOKEN, MIN_AMOUNT
    except ImportError:
        logger.error("❌ Файл config.py не найден!")
        return
    
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("❌ Пожалуйста, укажите токен Telegram-бота в config.py")
        return
    
    monitor = BinanceMultiMonitor(TELEGRAM_TOKEN, MIN_AMOUNT)
    
    try:
        await monitor.run()
    except KeyboardInterrupt:
        logger.info("👋 Монитор остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 