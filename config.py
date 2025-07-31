#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация для Binance Monitor Bot02
Мониторинг множественных торговых пар
"""

# Telegram Bot Token
TELEGRAM_TOKEN = "8313822061:AAGCMm6MvOT8zAU30bYqO-eCp9X1m-2ocso"

# Минимальная сумма сделки для уведомления (в USD)
MIN_AMOUNT = 1000000

# Настройки логирования
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "binance_monitor.log"

# Настройки WebSocket
RECONNECT_DELAY = 5  # секунды между попытками переподключения
STATS_INTERVAL = 60  # интервал вывода статистики в секундах

# Торговые пары для мониторинга
TRADING_PAIRS = [
    'bchusdt',
    'btcusdt', 
    'ethusdt',
    'bnbusdt',
    'dydxusdt',
    'solusdt',
    'suiusdt',
    'dogeusdt',
    'xrpusdt',
    'dotusdt',
    'tiausdt',
    'xtzusdt',
    'notusdt',
    'cfxusdt',
    'nearusdt',
    'epicusdt',
    'funusdt'
]

# Настройки уведомлений
NOTIFICATION_SETTINGS = {
    'enable_spot': True,      # Включить мониторинг спота
    'enable_futures': True,   # Включить мониторинг фьючерсов
    'include_link': True,     # Включить ссылку на Binance в сообщениях
    'emoji_enabled': True,    # Включить эмодзи в сообщениях
    'max_notifications_per_minute': 10  # Максимум уведомлений в минуту
}

# Эмодзи для разных типов активов
ASSET_EMOJIS = {
    'BCH': '🪙',
    'BTC': '₿',
    'ETH': 'Ξ',
    'BNB': '🟡',
    'DYDX': '📊',
    'SOL': '☀️',
    'SUI': '💎',
    'DOGE': '🐕',
    'XRP': '💎',
    'DOT': '🔗',
    'TIA': '🌟',
    'XTZ': '🌿',
    'NOT': '📝',
    'CFX': '🌊',
    'NEAR': '🌐',
    'EPIC': '🎮',
    'FUN': '🎯'
} 
