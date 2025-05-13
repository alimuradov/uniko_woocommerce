import json
from utils.woocommerce import wcapi

def check_product_exists(sku):
    """Проверяет, существует ли товар с указанным SKU."""
    response = wcapi.get(f"products/?sku={sku}")
    if response.status_code == 200 and response.json():
        return True  # Товар существует
    return False  # Товар не существует

# Формируем данные для батчевого создания двух товаров
data = {
    "create": [
        {
            "name": "Аденопросин 29мг №10 свечи рект.",
            "slug": "adenoprosin-29mg-10-svechi-rekt",
            "sku": "86031",
            "type": "simple",
            "regular_price": "1550.00",
            "manage_stock": True,
            "stock_quantity": "8",
            "stock_status": "instock",
            "categories": [
                {"id": 30}
            ],
            "attributes": [
                {
                    "id": 1,
                    "name": "Фармгруппа",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Противогеморроидальные"]
                },
                {
                    "id": 2,
                    "name": "Группа",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["ЛС (препараты)"]
                },
                {
                    "id": 4,
                    "name": "Производитель",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Биотехнос"]
                },
                {
                    "id": 3,
                    "name": "МНН",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": []
                },
                {
                    "id": 6,
                    "name": "Бренд",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": []
                },
                {
                    "id": 7,
                    "name": "Срок годности",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["2026-07-05"]
                },
                {
                    "id": 9,
                    "name": "Рецептурный",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Нет"]
                },
                {
                    "id": 10,
                    "name": "Количество в упаковке",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["1"]
                },
                {
                    "id": 12,
                    "name": "ЖНВЛ",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Нет"]
                },
                {
                    "id": 15,
                    "name": "Штрихкод",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["5944700301058"]
                }
            ],
            "meta_data": [
                {"key": "Аптека №149 (г. Даг. Огни)", "value": "4.0"},
                {"key": "Аптека №149 (Агасиева 17А)", "value": "4.0"}
            ]
        },
        {
            "name": "Аденурик 120мг №28 таб.",
            "slug": "adenurik-120mg-28-tab",
            "sku": "86032",
            "type": "simple",
            "regular_price": "4174.00",
            "manage_stock": True,
            "stock_quantity": "6",
            "stock_status": "instock",
            "categories": [
                {"id": 30}
            ],
            "attributes": [
                {
                    "id": 1,
                    "name": "Фармгруппа",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Гиперурикемия"]
                },
                {
                    "id": 2,
                    "name": "Группа",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["ЛС (препараты)"]
                },
                {
                    "id": 4,
                    "name": "Производитель",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Berlin-Chemie"]
                },
                {
                    "id": 3,
                    "name": "МНН",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Фебуксостат"]
                },
                {
                    "id": 6,
                    "name": "Бренд",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": []
                },
                {
                    "id": 7,
                    "name": "Срок годности",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["2025-09-30"]
                },
                {
                    "id": 9,
                    "name": "Рецептурный",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Нет"]
                },
                {
                    "id": 10,
                    "name": "Количество в упаковке",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["1"]
                },
                {
                    "id": 12,
                    "name": "ЖНВЛ",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Нет"]
                },
                {
                    "id": 15,
                    "name": "Штрихкод",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["4013054022108"]
                }
            ],
            "meta_data": [
                {"key": "Аптека №149 (ул. 345 ДСД 17)", "value": "3.0"},
                {"key": "Аптека №149 (Агасиева 17А)", "value": "3.0"}
            ]
        }
    ]
}


# Отправка батчевого запроса
response = wcapi.post("products/batch", data)

# Проверка ответа
if response.status_code == 200:
    print("Товары успешно созданы:", response.json())
else:
    print("Ошибка при создании товаров:", response.json())