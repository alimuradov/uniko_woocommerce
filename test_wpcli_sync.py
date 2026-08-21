"""
Ad-hoc ручной скрипт для проверки utils/wpcli_sync.py (по образцу test_create.py) -
шлёт 1-2 захардкоженных тестовых товара через WP-CLI/WooCommerce CRUD на
реальный/staging-сайт, настроенный в .env. НЕ юнит-тест.

Запуск дважды подряд должен: 1) создать товар, 2) обновить тот же товар по SKU
(не задублировать). Смотрите итоговую JSON-сводку в выводе.
"""

from utils.wpcli_sync import sync_products_via_wpcli

test_stocks = [
    {
        'name': 'ТЕСТ Аденопросин 29мг №10 свечи рект.',
        'ost': 4,
        'price': '1550.00',
        'mnn': '',
        'namepodr': 'Аптека №149 (г. Даг. Огни)',
        'isrecept': False,
        'farmgroup': 'Противогеморроидальные',
        'measure': 'шт',
        'delupak': 10,
        'islife': False,
        'group': 'ЛС (препараты)',
        'codtmc': 999001,
        'factory': 'Биотехнос',
        'category': '',
        'datevalid': '05.07.2026',
        'brand': '',
        'pricedeli': '1000.00',
        'scancod': '5944700301058',
    },
    {
        'name': 'ТЕСТ Аденопросин 29мг №10 свечи рект.',
        'ost': 2,
        'price': '1550.00',
        'mnn': '',
        'namepodr': 'Аптека №149 (Агасиева 17А)',
        'isrecept': False,
        'farmgroup': 'Противогеморроидальные',
        'measure': 'шт',
        'delupak': 10,
        'islife': False,
        'group': 'ЛС (препараты)',
        'codtmc': 999001,
        'factory': 'Биотехнос',
        'category': '',
        'datevalid': '05.07.2026',
        'brand': '',
        'pricedeli': '1000.00',
        'scancod': '5944700301058',
    },
]

result = sync_products_via_wpcli(test_stocks)
print("Сводка:", result)
