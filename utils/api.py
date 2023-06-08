import time
from utils.woocommerce import wcapi
from utils.utils import get_attribute_id_by_name, group_products_by_codtmc, \
    get_field_values, generate_variations
from .func import generate_slug

def create_new_categories(existing_categories, all_categories):
    # Создание списка новых категорий, отсутствующих в существующих категориях
    existing_categories = [ item['name'].strip() for item in existing_categories]
    new_categories = [category for category in all_categories if category not in existing_categories]

    # Подготовка данных для создания новых категорий
    data = {
        "create": [{"name": category, "slug": generate_slug(category)} for category in new_categories]
    }

    # Отправка запроса на создание новых категорий
    if len(data['create']) > 0:
        response = wcapi.post("products/categories/batch", data)
        # Проверка статуса ответа
        if response.status_code == 200 and  (len(response.json()['create']) == len(data['create'])):
            print("Новые категории успешно созданы.")
        else:
            print("Ошибка при создании новых категорий")        
    else:
        print("Нет новых категорий")
    



def create_new_attributes(existing_attributes):
    # Создание списка новых атрибутов, отсутствующих в существующих атрибутах
    all_attributes = [
        {'name': 'Фармгруппа', 'slug': 'pa_farmgroup', "has_archives": True, "type": "select"},
        {'name': 'Группа', 'slug': 'pa_group', "has_archives": True, "type": "select"},
        {'name': 'МНН', 'slug': 'pa_mnn', "has_archives": True, "type": "select"},
        {'name': 'Производитель', 'slug': 'pa_factory', "has_archives": True, "type": "select"},
        {'name': 'Категория', 'slug': 'pa_category', "has_archives": True, "type": "select"},
        {'name': 'Филиал', 'slug': 'pa_namepodr', "has_archives": True, "type": "select"},
        {'name': 'Бренд', 'slug': 'pa_brand', "has_archives": True, "type": "select"},
        {'name': 'Срок годности', 'slug': 'pa_datevalid', "has_archives": False},
        {'name': 'Код товара', 'slug': 'pa_codtmc', "has_archives": False},
        {'name': 'Рецептурный', 'slug': 'pa_isrecept', "has_archives": False},
        {'name': 'Количество в упаковке', 'slug': 'pa_delupak', "has_archives": False},
        {'name': 'Единица измерения', 'slug': 'pa_measure', "has_archives": False},
        {'name': 'ЖНВЛ', 'slug': 'pa_islife', "has_archives": False},
        {'name': 'Штрихкод', 'slug': 'pa_scancod, "has_archives": True, "type": "select"'},
        {'name': 'Цена', 'slug': 'pa_price', "has_archives": False},
        {'name': 'Остаток', 'slug': 'pa_stock', "has_archives": False}
    ]
    new_attributes = [attr for attr in all_attributes if attr['name'] not in [existing['name'] for existing in existing_attributes]]

    # Подготовка данных для создания новых атрибутов
    data = {
        "create": new_attributes
    }

    # Отправка запроса на создание новых атрибутов
    if len(data['create']) > 0:
        response = wcapi.post("products/attributes/batch", data)
        # Проверка статуса ответа
        if response.status_code == 200 and  (len(response.json()['create']) == len(data['create'])):
            print("Новые атрибуты успешно созданы.")
        else:
            print("Ошибка при создании новых атрибутов")        
    else:
        print("Нет новых атрибутов")


def get_attribute_terms(attribute):
    per_page = 100
    page = 1
    all_attributes = []

    while True:
        response = wcapi.get(f"products/attributes/{attribute['id']}/terms", params={"per_page": per_page, "page": page})
        
        # Проверка статуса ответа
        if response.status_code == 200:
            existing_attributes = response.json()
            all_attributes.extend(existing_attributes)
            
            # Если получены все элементы, выход из цикла
            if len(existing_attributes) < per_page:
                print("Все значения  атрибута " + attribute['name'] + " созданы")
                break
            
            # Увеличение номера страницы для следующего запроса
            page += 1
        else:
            print("Ошибка при получении значений атрибута " + attribute['name'])
            break

    return all_attributes


def create_attribute_terms(attribute, existing_terms, created_terms_value):
    batch_size = 100
    total_terms = len(created_terms_value)
    created_terms = []

    for i in range(0, total_terms, batch_size):
        batch = created_terms_value[i:i+batch_size]
        terms_to_create = []

        for term in batch:
            if not any(existing_term.get("name") == term for existing_term in existing_terms):
                if term:
                    terms_to_create.append({"name": term})

        if not terms_to_create:
            continue  # Пропускаем пустую порцию значений атрибута

        data = {"create": terms_to_create}

        response = wcapi.post(f"products/attributes/{attribute['id']}/terms/batch", data)

        if response.status_code == 200:
            created_terms.extend(response.json().get("create", []))
        else:
            print("Ошибка при создании значений атрибутов")
            break

    return created_terms



def get_all_products():
    all_products = []
    page = 1
    per_page = 900
    total_pages = 1
    
    while page <= total_pages:
        response = wcapi.get("products", params={"page": page, "per_page": per_page})
        
        if response.status_code == 200:
            products = response.json()
            all_products.extend(products)
            
            # Получение общего количества страниц
            total_pages = int(response.headers.get("X-WP-TotalPages"))
            
            # Увеличение номера страницы для следующего запроса
            print("Получено " + str(page * per_page) + " товаров")
            page += 1
        else:
            print("Ошибка при получении товаров")
            break
    print("Всего получено "  + str(len(all_products)) + " товаров")
    return all_products

def create_products(existing_products, created_products):
    #Группируем массив по коду
    created_products = group_products_by_codtmc(created_products)
    
    batch_size = 100
    total_products = len(created_products)
    created_pills = []

    #Снова получаем все категории далее они нам понадобятся при создании товаров
    existing_categories = wcapi.get("products/categories", params={"per_page": 100}).json()  

    #Получаем все атрубуты товаров на сайте
    existing_attributes = wcapi.get("products/attributes", params={"per_page": 100}).json()

    batch = []  # Массив для хранения текущей порции товаров
    i = 0
    for product in created_products:
        i= i+1
        codtmc = str(product)
        if (codtmc not in created_pills) and  (codtmc not in [existing_product.get("sku", "") for existing_product in existing_products]):
            # Находим соответствующую категорию из existing_categories
            category_id = None

            for category in existing_categories:
                if category.get("name") == created_products[product][0]['group']:
                    category_id = category.get("id")
                    break   
            name = created_products[product][0]['name']
            pill = {
                "name": name,
                "slug": generate_slug(name),
                "sku": codtmc,
                "type": "variable",
                "categories": [{"id": category_id}] if category_id else [],
                "attributes": [
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Филиал"),
                        "name": "Филиал",
                        "position": 0,
                        "visible": False,
                        "variation": True,
                        "options": get_field_values(created_products[product], 'namepodr')
                    },
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Цена"),
                        "name": "Цена",
                        "position": 0,
                        "visible": False,
                        "variation": True,
                        "options": get_field_values(created_products[product], 'price')
                    },
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Остаток"),
                        "name": "Остаток",
                        "position": 0,
                        "visible": False,
                        "variation": True,
                        "options": get_field_values(created_products[product], 'ost')
                    },                        
                ],
                # "variations": generate_variations(created_products[product], existing_attributes),
                "meta_data": [
                    {'key': 'mnn', 'value': created_products[product][0]['mnn']},
                    {'key': 'isrecept', 'value': created_products[product][0]['isrecept']},
                    {'key': 'farmgroup', 'value': created_products[product][0]['farmgroup']},
                    {'key': 'measure', 'value': created_products[product][0]['measure']},
                    {'key': 'delupak', 'value': created_products[product][0]['delupak']},
                    {'key': 'islife', 'value': created_products[product][0]['islife']},
                    {'key': 'group', 'value': created_products[product][0]['group']},
                    {'key': 'factory', 'value': created_products[product][0]['factory']},
                    {'key': 'category', 'value': created_products[product][0]['category']},
                    {'key': 'datevalid', 'value': created_products[product][0]['datevalid']},
                    {'key': 'brand', 'value': created_products[product][0]['brand']},
                    {'key': 'scancod', 'value': created_products[product][0]['scancod']},
                ],
            }
            #ДОбавляем создаваемый товар в порцию    
            batch.append(pill)
            #ДОбавляем текущий товар в массив созданных товаров
            created_pills.append(codtmc)

        if len(batch) == batch_size:
            # Отправляем текущую порцию на создание
            data = {"create": batch}
            try:
                response = wcapi.post("products/batch", data)
                if response.status_code == 200:
                    print(f"Создано {len(batch)} товаров - Batch {i//batch_size+1}/{total_products//batch_size+1}")
                else:
                    print(f"Ошибка при создании товаров - Batch {i//batch_size+1}/{total_products//batch_size+1}")
            except Exception as e:
                print(f"Exception occurred while creating products - Batch {i//batch_size+1}/{total_products//batch_size+1}: {str(e)}")
                time.sleep(30)  # Приостановить выполнение на 60 секунд
            batch = []  # Обнуляем текущую порцию

    # Проверяем, остались ли товары в последней порции
    if batch:
        data = {"create": batch}
        response = wcapi.post("products/batch", data)
        if response.status_code == 200:
            print(f"Создано {len(batch)} товаров")
        else:
            print("Ошибка при создании товаров")
    else:
        print("Нет новых товаров в порции")             



def create_variations(existing_products, created_products):
    #Группируем массив по коду
    created_products = group_products_by_codtmc(created_products)

    #Получаем все атрубуты товаров на сайте
    existing_attributes = wcapi.get("products/attributes", params={"per_page": 100}).json()

    #Обходим все товары
    for product in existing_products:
        #Сначала получаем текущие вариации
        response = wcapi.get(f"products/{str(product['id'])}/variations")
        delete_variations =[]
        create_variations = []
        if response.status_code == 200:
            response = response.json()
        else:
            print("Ошибка при получении информации о товаре " + product['name'])
            break 
        #Если характеристик нет то создаем их
        if len(response) == 0:
            create_variations = generate_variations(created_products[int(product['sku'])], existing_attributes)
        elif len(response) > 0: #Если же вариации есть то удаляем их
            for item in response:
                delete_variations.append(item['id'])
            try:
                # И создаем по новой
                create_variations = generate_variations(created_products[int(product['sku'])], existing_attributes)
            except KeyError as e:
                print("Ошибка при создании вариаций товара " + product['name'] + ": " + str(e))

        data = {
            "create": create_variations,
            "delete": delete_variations,
        }        

        response = wcapi.post(f"products/{str(product['id'])}/variations/batch", data)
        if response.status_code == 200:
            print("Cозданы характеристики товара " + product['name'])
        else:
            print("Ошибка при создании вариаций товара " + product['name'])
            break 