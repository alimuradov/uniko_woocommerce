import time
from utils.woocommerce import wcapi
from utils.utils import get_attribute_id_by_name, group_products_by_codtmc, \
    get_field_values, generate_variations, get_stocks_meta, calculate_total_ost, find_min_price, \
    get_unique_field_values, find_max_price,  get_latest_date
from .func import generate_slug, remove_non_digits

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
        {'name': 'Штрихкод', 'slug': 'pa_scancod', "has_archives": True, "type": "select"},
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
    per_page = 700
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

def old_create_products(existing_products, created_products):
    
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


def create_and_update_products(existing_products, created_products, existing_attributes, existing_categories):
    # Группируем массив по коду
    created_products = group_products_by_codtmc(created_products)
    batch_size = 100
    batch_create = []  # Массив для хранения товаров, которые нужно создать
    batch_update = []  # Массив для хранения товаров, которые нужно обновить 

    total_products = len(existing_products)
    total_batches = (total_products + batch_size - 1) // batch_size  # Корректное округление вверх
    created_pills = []


    # Создаем множество SKU для быстрого поиска
    existing_skus = set(existing_product.get("sku", "") for existing_product in existing_products)
    
    # Для начала мы проверяем существующие товары
    # есть ли они в новой партии на обновление остатков, если их там нет,
    # то мы для всех таких товаров обновляем статус остатка на "нет в наличии"
    unstocked_products = []  #Обнуленные товары
    i = 0
    for exist_pill in existing_products:
        i += 1
        sku = exist_pill.get("sku", "")
        sku = remove_non_digits(sku)

        if not sku.isdigit():
            continue

        if int(sku) not in created_products:
            pill = {
                "id": exist_pill.get("id", ""),
                "stock_status": "outofstock",    
            }
            unstocked_products.append(str(sku))
            batch_update.append(pill)            
        
        if len(batch_update) == batch_size:
            # Отправляем текущую порцию на создание и обновление
            current_batch = (i // batch_size) + 1
            data = {"update": batch_update}
            try:
                response = wcapi.post("products/batch", data)
                if response.status_code == 200:
                    print(f"Снято с остатка -  {len(batch_update)} товаров - Batch {current_batch}/{total_batches}")
                else:
                    print(f"Ошибка снятия товаров с остатка - Batch {current_batch}/{total_batches}")
            except Exception as e:
                print(f"Ошибка: {str(e)}")
                time.sleep(20)  # Приостановить выполнение на 30 секунд
            batch_update = []  # Обнуляем текущую порцию для обновления
    
    # Проверяем, остались ли товары в последней порции для  обнуления остатков
    if  batch_update:
        data = {"update": batch_update}
        response = wcapi.post("products/batch", data)
        if response.status_code == 200:
            print(f"Обнулено {len(batch_update)} товаров")
        else:
            print("Ошибка при обнулении товаров")
        batch_update = []  # Обнуляем текущую порцию для обновления    
    else:
        print("Нет новых товаров для обнуления")            


    # Создаем множество SKU для быстрого поиска

    existing_skus = set()
    for existing_product in existing_products:
        sku = existing_product.get("sku", "")
        if sku:
            existing_skus.add(sku)
        else:
            print(f"Внимание: товар без SKU в existing_products: ID={existing_product.get('id')}")

    i = 0
    batch_counter = 0  # Для последовательного вывода батчей, как обсуждалось ранее
    for product in created_products:
        i += 1
        codtmc = str(product)
        current_product = created_products[product]
        
        if codtmc in unstocked_products:
            continue

        if (codtmc not in created_pills) and (codtmc not in existing_skus):
            # Создаем новый товар
            category_id = None

            for category in existing_categories:
                if category.get("name") == current_product[0]['group']:
                    category_id = category.get("id")
                    break

            name = current_product[0]['name']
            ostatok = calculate_total_ost(current_product) 

            pill = {
                "name": name,
                "slug": generate_slug(name),
                "sku": codtmc,
                "type": "simple",
                "categories": [{"id": category_id}] if category_id else [],
                "regular_price": find_max_price(current_product),
                "manage_stock": False,
                "stock_quantity": ostatok,
                "stock_status": "instock" if ostatok > 0 else "outofstock",
                "attributes": [
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Фармгруппа"),
                        "name": "Фармгруппа",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'farmgroup')
                    },
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Группа"),
                        "name": "Группа",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'group')
                    },
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Производитель"),
                        "name": "Производитель",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'factory')
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "МНН"),
                        "name": "МНН",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'mnn')
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Бренд"),
                        "name": "Бренд",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'brand')
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Срок годности"),
                        "name": "Срок годности",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_latest_date(current_product)
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Рецептурный"),
                        "name": "Рецептурный",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": ["Да" if current_product[0]['isrecept'] else "Нет"]
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Количество в упаковке"),
                        "name": "Количество в упаковке",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'delupak')
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "ЖНВЛ"),
                        "name": "ЖНВЛ",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": ["Да" if current_product[0]['islife'] else "Нет"]
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Штрихкод"),
                        "name": "Штрихкод",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_unique_field_values(current_product, 'scancod')
                    },                                                                                                                                                                                                           
                ],
                "meta_data": get_stocks_meta(current_product),
            }
            batch_create.append(pill)
            created_pills.append(codtmc)
        else:
            # Обновляем существующий товар 
            category_id = None

            for category in existing_categories:
                if category.get("name") == current_product[0]['group']:
                    category_id = category.get("id")
                    break

            existing_product = None
            for existing_product in existing_products:
                if existing_product.get("sku", "") == codtmc:
                    break                

            if existing_product is None:
                print(f"Товар с SKU {codtmc} не найден в existing_products, пропускаем обновление")
                continue  # Пропускаем, если товар не найден
            
            name = current_product[0]['name']
            ostatok = calculate_total_ost(current_product) 
                          
            pill = {
                "id": existing_product['id'],
                "name": name,
                "regular_price": find_max_price(created_products[product]),
                "categories": [{"id": category_id}] if category_id else [],
                "manage_stock": False,
                "stock_quantity": ostatok,
                "stock_status": "instock" if ostatok > 0 else "outofstock",
                "attributes": [
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Фармгруппа"),
                        "name": "Фармгруппа",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'farmgroup')
                    },
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Группа"),
                        "name": "Группа",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'group')
                    },
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Производитель"),
                        "name": "Производитель",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'factory')
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "МНН"),
                        "name": "МНН",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'mnn')
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Бренд"),
                        "name": "Бренд",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'brand')
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Срок годности"),
                        "name": "Срок годности",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_latest_date(current_product)
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Рецептурный"),
                        "name": "Рецептурный",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": [current_product[0]['isrecept']]
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Количество в упаковке"),
                        "name": "Количество в упаковке",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'delupak')
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "ЖНВЛ"),
                        "name": "ЖНВЛ",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": [current_product[0]['islife']]
                    }, 
                    {
                        "id": get_attribute_id_by_name(existing_attributes, "Штрихкод"),
                        "name": "Штрихкод",
                        "position": 0,
                        "visible": True,
                        "variation": False,
                        "options": get_field_values(current_product, 'scancod')
                    },                                                                                                                                                                                                           
                ],
                "meta_data": get_stocks_meta(current_product),                
            }
            batch_update.append(pill)

        if len(batch_create) + len(batch_update) == batch_size:
            batch_counter += 1
            data = {"create": batch_create, "update": batch_update}
            try:
                response = wcapi.post("products/batch", data)
                if response.status_code == 200:
                    print(f"Создано {len(batch_create)} товаров и обновлено {len(batch_update)} товаров - Batch {batch_counter}/{total_products // batch_size + 1}")
                else:
                    print(f"Ошибка при создании/обновлении товаров - Batch {batch_counter}/{total_products // batch_size + 1}")
                    print(f"Проблемный батч: create={len(batch_create)}, update={len(batch_update)}")
            except Exception as e:
                print(f"Exception occurred while creating/updating products - Batch {batch_counter}/{total_products // batch_size + 1}: {str(e)}")
                time.sleep(30)
            batch_create = []
            batch_update = []

    # Последний батч
    if batch_create or batch_update:
        batch_counter += 1
        data = {"create": batch_create, "update": batch_update}
        try:
            response = wcapi.post("products/batch", data)
            if response.status_code == 200:
                print(f"Создано {len(batch_create)} товаров и обновлено {len(batch_update)} товаров - Batch {batch_counter}/{total_products // batch_size + 1}")
            else:
                print(f"Ошибка при создании/обновлении товаров - Batch {batch_counter}/{total_products // batch_size + 1}")
                print(f"Проблемный батч: create={len(batch_create)}, update={len(batch_update)}")
        except Exception as e:
            print(f"Exception occurred while creating/updating products - Batch {batch_counter}/{total_products // batch_size + 1}: {str(e)}")
        batch_create = []
        batch_update = []
    else:
        print("Нет новых товаров для создания и обновления")


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
            try:
                create_variations = generate_variations(created_products[int(product['sku'])], existing_attributes)
            except KeyError as e:
                print("Ошибка при создании вариаций товара " + product['name'] + ": " + str(e))
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
        try:
            response = wcapi.post(f"products/{str(product['id'])}/variations/batch", data)
            if response.status_code == 200:
                print("Cозданы характеристики товара " + product['name'])
            else:
                print("Не удалось создать вариацию товара " + product['name'])
        except Exception as e:
            print(f"Ошибка при создании вариаций товара: {str(e)}")
                
def create_products(created_products, existing_attributes, existing_categories):
    """
    Создает новые товары поштучно в WooCommerce.
    """
    created_products = group_products_by_codtmc(created_products)
    existing_skus = set()  # Множество SKU для проверки существующих товаров
    created_pills = []     # Список созданных товаров

    # Формируем множество SKU существующих товаров
    for existing_product in existing_products:
        sku = existing_product.get("sku", "")
        if sku:
            existing_skus.add(sku)
        else:
            print(f"Внимание: товар без SKU в existing_products: ID={existing_product.get('id')}")

    total_products = len(created_products)
    for i, product in enumerate(created_products, 1):
        codtmc = str(product)
        current_product = created_products[product]

        if codtmc in existing_skus or codtmc in created_pills:
            continue  # Пропускаем, если товар уже существует или был создан

        # Находим ID категории
        category_id = None
        for category in existing_categories:
            if category.get("name") == current_product[0]['group']:
                category_id = category.get("id")
                break

        name = current_product[0]['name']
        ostatok = calculaFte_total_ost(current_product)

        # Формируем данные для нового товара
        pill = {
            "name": name,
            "slug": generate_slug(name),
            "sku": codtmc,
            "type": "simple",
            "categories": [{"id": category_id}] if category_id else [],
            "regular_price": find_max_price(current_product),
            "manage_stock": False,
            "stock_quantity": ostatok,
            "stock_status": "instock" if ostatok > 0 else "outofstock",
            "attributes": [
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Фармгруппа"),
                    "name": "Фармгруппа",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'farmgroup')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Группа"),
                    "name": "Группа",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'group')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Производитель"),
                    "name": "Производитель",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'factory')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "МНН"),
                    "name": "МНН",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'mnn')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Бренд"),
                    "name": "Бренд",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'brand')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Срок годности"),
                    "name": "Срок годности",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_latest_date(current_product)
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Рецептурный"),
                    "name": "Рецептурный",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Да" if current_product[0]['isrecept'] else "Нет"]
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Количество в упаковке"),
                    "name": "Количество в упаковке",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'delupak')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "ЖНВЛ"),
                    "name": "ЖНВЛ",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Да" if current_product[0]['islife'] else "Нет"]
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Штрихкод"),
                    "name": "Штрихкод",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_unique_field_values(current_product, 'scancod')
                },
            ],
            "meta_data": get_stocks_meta(current_product),
        }

        # Создаем товар поштучно
        try:
            response = wcapi.post("products", pill)
            if response.status_code == 201:
                print(f"Создан товар {codtmc} ({i}/{total_products})")
                created_pills.append(codtmc)
            else:
                print(f"Ошибка при создании товара {codtmc}: {response.json()}")
        except Exception as e:
            print(f"Ошибка при создании товара {codtmc}: {str(e)}")
            time.sleep(20)  # Пауза при ошибке

    print(f"Создание завершено. Создано {len(created_pills)} новых товаров.")
    return created_pills

def update_products(existing_products, created_products, existing_attributes, existing_categories):
    """
    Обновляет остатки и данные существующих товаров в WooCommerce батчами.
    """
    created_products = group_products_by_codtmc(created_products)
    batch_size = 100
    batch_update = []
    unstocked_products = []

    total_products = len(existing_products)
    total_batches = (total_products + batch_size - 1) // batch_size

    # Обнуление остатков для товаров, отсутствующих в новой партии
    for i, exist_pill in enumerate(existing_products, 1):
        sku = exist_pill.get("sku", "")
        sku = remove_non_digits(sku)

        if not sku.isdigit():
            continue

        if int(sku) not in created_products:
            pill = {
                "id": exist_pill.get("id", ""),
                "stock_status": "outofstock",
            }
            unstocked_products.append(str(sku))
            batch_update.append(pill)

        if len(batch_update) == batch_size:
            current_batch = (i // batch_size) + 1
            data = {"update": batch_update}
            try:
                response = wcapi.post("products/batch", data)
                if response.status_code == 200:
                    print(f"Снято с остатка - {len(batch_update)} товаров - Batch {current_batch}/{total_batches}")
                else:
                    print(f"Ошибка снятия товаров с остатка - Batch {current_batch}/{total_batches}")
            except Exception as e:
                print(f"Ошибка: {str(e)}")
                time.sleep(20)
            batch_update = []

    if batch_update:
        data = {"update": batch_update}
        try:
            response = wcapi.post("products/batch", data)
            if response.status_code == 200:
                print(f"Обнулено {len(batch_update)} товаров")
            else:
                print("Ошибка при обнулении товаров")
        except Exception as e:
            print(f"Ошибка: {str(e)}")
        batch_update = []
    else:
        print("Нет товаров для обнуления")

    # Обновление существующих товаров
    batch_counter = 0
    for i, product in enumerate(created_products, 1):
        codtmc = str(product)
        current_product = created_products[product]

        if codtmc in unstocked_products:
            continue

        # Находим существующий товар
        existing_product = None
        for ep in existing_products:
            if ep.get("sku", "") == codtmc:
                existing_product = ep
                break

        if existing_product is None:
            print(f"Товар с SKU {codtmc} не найден в existing_products, пропускаем обновление")
            continue

        # Находим ID категории
        category_id = None
        for category in existing_categories:
            if category.get("name") == current_product[0]['group']:
                category_id = category.get("id")
                break

        name = current_product[0]['name']
        ostatok = calculate_total_ost(current_product)

        # Формируем данные для обновления
        pill = {
            "id": existing_product['id'],
            "name": name,
            "regular_price": find_max_price(current_product),
            "categories": [{"id": category_id}] if category_id else [],
            "manage_stock": False,
            "stock_quantity": ostatok,
            "stock_status": "instock" if ostatok > 0 else "outofstock",
            "attributes": [
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Фармгруппа"),
                    "name": "Фармгруппа",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'farmgroup')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Группа"),
                    "name": "Группа",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'group')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Производитель"),
                    "name": "Производитель",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'factory')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "МНН"),
                    "name": "МНН",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'mnn')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Бренд"),
                    "name": "Бренд",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'brand')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Срок годности"),
                    "name": "Срок годности",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_latest_date(current_product)
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Рецептурный"),
                    "name": "Рецептурный",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Да" if current_product[0]['isrecept'] else "Нет"]
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Количество в упаковке"),
                    "name": "Количество в упаковке",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_field_values(current_product, 'delupak')
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "ЖНВЛ"),
                    "name": "ЖНВЛ",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": ["Да" if current_product[0]['islife'] else "Нет"]
                },
                {
                    "id": get_attribute_id_by_name(existing_attributes, "Штрихкод"),
                    "name": "Штрихкод",
                    "position": 0,
                    "visible": True,
                    "variation": False,
                    "options": get_unique_field_values(current_product, 'scancod')
                },
            ],
            "meta_data": get_stocks_meta(current_product),
        }
        batch_update.append(pill)

        if len(batch_update) == batch_size:
            batch_counter += 1
            data = {"update": batch_update}
            try:
                response = wcapi.post("products/batch", data)
                if response.status_code == 200:
                    print(f"Обновлено {len(batch_update)} товаров - Batch {batch_counter}/{total_products // batch_size + 1}")
                else:
                    print(f"Ошибка при обновлении товаров - Batch {batch_counter}/{total_products // batch_size + 1}")
            except Exception as e:
                print(f"Ошибка при обновлении: {str(e)}")
                time.sleep(20)
            batch_update = []

    # Последний батч обновления
    if batch_update:
        batch_counter += 1
        data = {"update": batch_update}
        try:
            response = wcapi.post("products/batch", data)
            if response.status_code == 200:
                print(f"Обновлено {len(batch_update)} товаров - Batch {batch_counter}/{total_products // batch_size + 1}")
            else:
                print(f"Ошибка при обновлении товаров - Batch {batch_counter}/{total_products // batch_size + 1}")
        except Exception as e:
            print(f"Ошибка при обновлении: {str(e)}")
    else:
        print("Нет товаров для обновления")