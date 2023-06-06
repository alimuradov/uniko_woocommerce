import datetime
from dbfread import DBF
from utils.utils import ru_to_lat
from utils.woocommerce import wcapi
from utils  import api


def get_stocks_from_dbf():
    ## Укажите путь к вашему файлу .dbf
    # pills = DBF('D:/dev/site/backend/dbf/ost.dbf', encoding='cp866')
    pills = DBF('./ost.dbf', encoding='cp866')
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
    
    # Получение всех уникальных значений поля "Фармгруппа"
    farmgroups = set(item['farmgroup'] for item in stocks)
    farmgroups_list = list(farmgroups)


    # Получение всех уникальных значений поля "группа"
    groups = set(item['group'] for item in stocks)
    groups_list = list(groups)

    # Получение всех уникальных значений справочника МНН
    mnn = set(item['mnn'] for item in stocks)
    mnn_list = list(mnn)
    
    # Получение всех уникальных значений единиц измерения
    measure = set(item['measure'] for item in stocks)
    measure_list = list(measure)

    # Получение всех уникальных значений справочника Проиозводители
    factory = set(item['factory'] for item in stocks)
    factory_list = list(factory)

    # Получение всех уникальных значений справочника Категории товаров
    category = set(item['category'] for item in stocks)
    category_list = list(category)
    
    # Получение всех уникальных значений справочника Категории товаров
    brand = set(item['brand'] for item in stocks)
    brand_list = list(brand) 

    # Получение всех уникальных значений справочника Филиалы
    filial = set(item['namepodr'] for item in stocks)
    filial_list = list(filial) 

    # Получение всех уникальных значений справочника товары, фильруем по артикулу
    codtmc = set(item['codtmc'] for item in stocks)
    codtmc_list = list(codtmc)  
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
        'filials': filial_list,
    }


# Получаем текущую дату и время в момент запуска скрипта
start_time = datetime.datetime.now()
print("Скрипт начал выполнение:", start_time)

result = get_stocks_from_dbf()
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

#Создаем товары
api.create_products(existing_products, result['stocks'])

#Снова  получаем существующие товары
existing_products = api.get_all_products()

#Далее обходим все товары  и обновлям для них вариации.
api.create_variations(existing_products, result['stocks'])

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