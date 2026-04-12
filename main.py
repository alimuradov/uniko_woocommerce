import os
import datetime
import requests
from collections import defaultdict
from dbfread import DBF
from utils.utils import ru_to_lat, send_telegram_message
from utils.woocommerce import wcapi
from utils  import api


def get_file_modification_date(file_path):
    try:
        modified_ts = os.path.getmtime(file_path)
        return datetime.datetime.fromtimestamp(modified_ts).date()
    except OSError:
        return None


def get_stocks_seconds_dbf():
    #получаем остатки второй аптечной сети
    
    ## Укажите путь к вашему файлу .dbf
    files_catalog_path = os.getenv("FILES_CATALOG_PATH")
    dbf_file_path = os.path.join(files_catalog_path, 'agasieva.dbf')
    agasieva_file_date = get_file_modification_date(dbf_file_path)
    pills = DBF(dbf_file_path, encoding='cp866')
    #pills = DBF('./ost.dbf', encoding='cp866')
    stocks = []
    #для катлога
    for item in pills:
        goods_row = {
            'name': item['NAMETMC'],  #Наименование товара
            'ost': item['OST'], #Остаток товара
            'price': item['PRICE'], #Цена
            'mnn': item['MNN'].strip(), #Международное непотентованное название
            'slugpodr': ru_to_lat(item['NAMEPODR'].strip()), #Slug аптеки
            'namepodr': item['NAMEPODR'].strip(), #Название аптеки 
            'isrecept': item['ISRECEPT'], #Рецептурный
            'farmgroup': item['FARMGROUP'].strip(), #Фармгруппа
            'measure': item['MEASURE'].strip(), #Единица измерения
            'delupak': item['DELUPAK'], #Количество единиц в упаковке
            'islife': item['ISLIFE'], #ЖНВЛ
            'group': item['GROUP'].strip(), #Группа товара
            'codtmc': item['CODTMC'], #Код товара
            'factory': item['FACTORY'].strip(), #Производитель
            'category': item['CATEGORY'].strip(), #Категория товара
            'datevalid': item['DATEVALID'], #Срок годности
            'brand': item['BRAND'].strip(), #Бренд
            'pricedeli': item['PRICEDELI'], #Цена закупки
            'scancod': item['SCANCOD'].strip() #Штрихкод]
            }
        stocks.append(goods_row)
    
    return stocks, agasieva_file_date

def get_stocks_from_dbf():
    ## Укажите путь к вашему файлу .dbf
    files_catalog_path = os.getenv("FILES_CATALOG_PATH")
    dbf_file_path = os.path.join(files_catalog_path, 'ost.dbf')
    ost_file_date = get_file_modification_date(dbf_file_path)
    pills = DBF(dbf_file_path, encoding='cp866')

    stocks = []

    # Список филиалов
    filial_list = set()

    #получаем остатки  аптечной сети Панация
    stocks_panaceya, agasieva_file_date = get_stocks_seconds_dbf()

    # Создаем словарь для быстрого поиска по scancod
    panaceya_by_scancod = defaultdict(list)

    # Множество для отслеживания комбинаций scancod + namepodr только для stocks_panaceya
    added_panaceya_combinations = set()
    
    for stock in stocks_panaceya:
        scancod = stock['scancod'].strip()
        panaceya_by_scancod[scancod].append(stock)    


    # Обрабатываем первую сеть (ost.dbf)
    for item in pills:
        goods_row = {
            'name': item['NAMETMC'],  #Наименование товара
            'ost': item['OST'], #Остаток товара
            'price': item['PRICE'], #Цена
            'mnn': item['MNN'].strip(), #Международное непотентованное название
            'slugpodr': ru_to_lat(item['NAMEPODR'].strip()), #Slug аптеки
            'namepodr': item['NAMEPODR'].strip(), #Название аптеки 
            'isrecept': item['ISRECEPT'], #Рецептурный
            'farmgroup': item['FARMGROUP'].strip(), #Фармгруппа
            'measure': item['MEASURE'].strip(), #Единица измерения
            'delupak': item['DELUPAK'], #Количество единиц в упаковке
            'islife': item['ISLIFE'], #ЖНВЛ
            'group': item['GROUP'].strip(), #Группа товара
            'codtmc': item['CODTMC'], #Код товара
            'factory': item['FACTORY'].strip(), #Производитель
            'category': item['CATEGORY'].strip(), #Категория товара
            'datevalid': item['DATEVALID'], #Срок годности
            'brand': item['BRAND'].strip(), #Бренд
            'pricedeli': item['PRICEDELI'], #Цена закупки
            'scancod': item['SCANCOD'].strip() #Штрихкод]
            }
        stocks.append(goods_row)
        filial_list.add(item['NAMEPODR'].strip())


        # Находим совпадения по scancod
        scancod = item['SCANCOD'].strip()
        if scancod in panaceya_by_scancod:
            for stock in panaceya_by_scancod[scancod]:
                namepodr_raw = stock['namepodr'].strip()
                
                # Определяем название филиала
                name_farmaci = ''
                if namepodr_raw == 'Агасиева 17а':
                    name_farmaci = 'Аптека №149 (Агасиева 17А)'
                elif namepodr_raw == 'ПФ (второй отдел)':
                    name_farmaci = 'Аптека №149 (второй отдел)'
                elif namepodr_raw == 'г. Огни ул. Революции 52б':
                    name_farmaci = 'Аптека №149 (Даг. Огни ул. Революции 52б)'
                
                if not name_farmaci:
                    continue
                
                # Проверяем дубликаты
                combination = (scancod, name_farmaci)
                if combination in added_panaceya_combinations:
                    continue
                
                # Создаем новую запись
                new_goods_row = goods_row.copy()
                new_goods_row['ost'] = stock['ost']
                new_goods_row['namepodr'] = name_farmaci
                new_goods_row['slugpodr'] = ru_to_lat(namepodr_raw)
                
                # Добавляем запись
                stocks.append(new_goods_row)
                print(f"Добавлена запись: scancod={new_goods_row['scancod']}, namepodr={new_goods_row['namepodr']}, ost={new_goods_row['ost']}")
                added_panaceya_combinations.add(combination)
                filial_list.add(name_farmaci) 
    
    # Получаем уникальные значения
    farmgroups_list = list(set(item['farmgroup'] for item in stocks))
    groups_list = list(set(item['group'] for item in stocks))
    mnn_list = list(set(item['mnn'] for item in stocks))
    measure_list = list(set(item['measure'] for item in stocks))
    factory_list = list(set(item['factory'] for item in stocks))
    category_list = list(set(item['category'] for item in stocks))
    brand_list = list(set(item['brand'] for item in stocks))
    codtmc_list = list(set(item['codtmc'] for item in stocks))
    
    print('Товаров в выгрузке ' + str(len(codtmc_list)))
    print('Партий в выгрузке ' + str(len(stocks)))              

    return {
        'mnns': mnn_list,
        'brands': brand_list,
        'categorys': category_list,
        'factorys': factory_list,
        'measures': measure_list,
        'stocks': stocks,
        'farmgroups': farmgroups_list,
        'groups': groups_list,
        'filials': list(filial_list),
        'file_dates': {
            'ost.dbf': ost_file_date,
            'agasieva.dbf': agasieva_file_date,
        },
    }


# Получаем текущую дату и время в момент запуска скрипта
start_time = datetime.datetime.now()
print("Скрипт начал выполнение:", start_time)

result = get_stocks_from_dbf()

print("Завершена подготовка данных для импорта:",  datetime.datetime.now())

#Получаем все категории товаров на сайте
existing_categories = wcapi.get("products/categories", params={"per_page": 100}).json()

#Получаем все атрубуты товаров на сайте
existing_attributes = wcapi.get("products/attributes", params={"per_page": 100}).json()

#создаем категории если их нет
api.create_new_categories(existing_categories, result['groups'])

#Создаем обязательные аттрибуты для импорта данных
api.create_new_attributes(existing_attributes)

#Обходим все атрибуты и для каждого атрибута получаем его значения
for attribute in existing_attributes:
    #Для каждого атрибута получаем его существующие значения
    if attribute['name'] == 'Бренд':
        created_terms = result['brands']
        existing_attribute_terms = api.get_attribute_terms(attribute)
        api.create_attribute_terms(attribute, existing_attribute_terms, created_terms)
    if attribute['name'] == 'Фармгруппа':
        created_terms = result['farmgroups']
        existing_attribute_terms = api.get_attribute_terms(attribute)
        api.create_attribute_terms(attribute, existing_attribute_terms, created_terms)
    if attribute['name'] == 'Группа':
        created_terms = result['groups']
        existing_attribute_terms = api.get_attribute_terms(attribute)
        api.create_attribute_terms(attribute, existing_attribute_terms, created_terms)
    if attribute['name'] == 'МНН':
        created_terms = result['mnns']
        existing_attribute_terms = api.get_attribute_terms(attribute)
        api.create_attribute_terms(attribute, existing_attribute_terms, created_terms)
    if attribute['name'] == 'Единица измерения':
        created_terms = result['measures']
        existing_attribute_terms = api.get_attribute_terms(attribute)
        api.create_attribute_terms(attribute, existing_attribute_terms, created_terms)
    if attribute['name'] == 'Производитель':
        created_terms = result['factorys']
        existing_attribute_terms = api.get_attribute_terms(attribute)
        api.create_attribute_terms(attribute, existing_attribute_terms, created_terms)
    if attribute['name'] == 'Категория':
        created_terms = result['categorys']
        existing_attribute_terms = api.get_attribute_terms(attribute)
        api.create_attribute_terms(attribute, existing_attribute_terms, created_terms) 
    if attribute['name'] == 'Филиал':
        created_terms = result['filials']
        existing_attribute_terms = api.get_attribute_terms(attribute)
        api.create_attribute_terms(attribute, existing_attribute_terms, created_terms) 

#Получаем существующие товары
existing_products = api.get_all_products()

# #Создаем товары
api.create_and_update_products(existing_products, result['stocks'], existing_attributes, existing_categories)



# Получаем время окончания выполнения скрипта
end_time = datetime.datetime.now()
print("Скрипт завершил выполнение:", end_time)

# Вычисляем общее время выполнения
execution_time = end_time - start_time

# Выводим общее время выполнения
print("Общее время выполнения скрипта:", execution_time)

# Вычисляем затраченное время в часах и минутах
hours = execution_time.seconds // 3600
minutes = (execution_time.seconds % 3600) // 60

# Выводим затраченное время в часах и минутах
print("Затраченное время в часах и минутах:", hours, "ч", minutes, "мин")

# Форматируем сообщение о затраченном времени
time_info = f"Затраченное время в часах и минутах: {int(hours)} ч {int(minutes)} мин"

# Формируем информацию об актуальности файлов
today = datetime.date.today()
file_dates = result.get('file_dates', {})
file_labels = {
    'ost.dbf': 'Остатки ИП Магомедова Ш.А',
    'agasieva.dbf': 'Остатки ООО Панацея',
}
file_status_lines = []
for filename, file_date in file_dates.items():
    label = file_labels.get(filename, filename)
    if not file_date:
        file_status_lines.append(f"{label}: дата не определена")
    elif file_date != today:
        file_status_lines.append(f"Внимание: {label} датирован {file_date}")
    else:
        file_status_lines.append(f"{label} актуальны на: {file_date}")

# Итоговое сообщение
message_lines = [
    "Каталог сайта обновлен.",
    time_info,
] + file_status_lines
message = "\n".join(message_lines)

#отправляем сообщение в телеграмм
# send_telegram_message(message)
url = "https://n9n.alimuradov.ru/webhook/fc931587-9fed-4f36-86ff-bf53322860ac"
response = requests.post(url, json={"text": message}, timeout=30)
print("\nОтвет с заголовками:", response.json())
