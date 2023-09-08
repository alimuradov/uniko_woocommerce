from datetime import datetime, timedelta

def ru_to_lat(st):
    if st == 'Аптека №149 (второй отдел)':
        return 'parafarm'
    if st == 'Аптека №149 (Шеболдаева 49в)':
        return 'sheboldaeva'    
    elif st == 'Аптека №149 (ул. Хизроева 8)':
        return 'xizroeva'
    elif st == 'Аптека №149 (Агасиева 26А)':
        return 'agasieva26'            
    elif st == 'Аптека №149 (Агасиева 17А)':
        return 'agasieva17'
    elif st == 'Аптека №149 (Ленина 86)':
        return 'lenina86'
    elif st == 'Аптека №149 (ул. 345 ДСД 17)':
        return '345'
    elif st == 'Аптека №149 (ул. Сальмана 87А)':
        return 'salmana'
    elif st == 'Аптека №149 (г. Даг. Огни)':
        return 'ogni'
    elif st == 'Аптека №149 (ТЦ Глобус)':
        return 'globus'
    elif st == 'Аптека №149 (ул. Пушкина 50)':
        return 'pushkina'
    else:
        return '' 
    

def get_attribute_id_by_name(existing_attributes, attribute_name):
    for attribute in existing_attributes:
        if attribute.get("name") == attribute_name:
            return attribute.get("id")
    return None


def group_products_by_codtmc(products):
    grouped_products = {}
    for product in products:
        codtmc = product['codtmc']
        if codtmc in grouped_products:
            grouped_products[codtmc].append(product)
        else:
            grouped_products[codtmc] = [product]
    return grouped_products


def get_field_values(objects, key):
    field_values = []  # Список для хранения значений поля

    for obj in objects:
        value = obj.get(key)
        if value:
            field_values.append(value)

    return field_values

def get_unique_field_values(objects, key):
    field_values = set()  # Множество для хранения уникальных значений поля

    for obj in objects:
        value = obj.get(key)
        if value:
            field_values.add(value)

    return list(field_values)


def generate_variations(objects, existing_attributes):
    variations = []  # Список для хранения значений поля
    for obj in objects:
        attributes = []
        attribute_filial = {
            "id": get_attribute_id_by_name(existing_attributes, "Филиал"),
            "option": obj['namepodr']
        }
        attributes.append(attribute_filial)

        attribute_price = {
            "id": get_attribute_id_by_name(existing_attributes, "Цена"),
            "option": obj['price']
        }
        attributes.append(attribute_price)

        attribute_ost = {
            "id": get_attribute_id_by_name(existing_attributes, "Остаток"),
            "option": obj['ost']
        }                
        attributes.append(attribute_ost)
        
        variation = {
            "regular_price": obj['price'],
            "price": obj['price'],
            "attributes": attributes

        }
        variations.append(variation)

    return variations


def get_stocks_meta(obj):
    stocks_meta = []
    for item in obj:
        stock_name = item['namepodr']
        stock_ost = item['ost']
        stocks_meta.append({'key': stock_name, 'value': stock_ost})
    return stocks_meta

def calculate_total_ost(obj):
    total_ost = sum(item['ost'] for item in obj)
    if total_ost == 0:
        return 0
    return total_ost


def find_min_price(obj):
    min_price = min(item['price'] for item in obj)
    return min_price

def find_max_price(obj):
    max_price = max(item['price'] for item in obj)
    return max_price



def update_variations(existing_variations, new_stocks):
    updated_variations = []

    for existing_variation in existing_variations:
        # Находим соответствующую партию по атрибутам вариации
        pass


def strtobool (val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))
    

def get_latest_date(objects):
    valid_dates = []  # Список для хранения действительных дат

    for obj in objects:
        date_str = obj.get('datevalid')
        if date_str:
            try:
                date = datetime.strptime(date_str, '%d.%m.%Y')
                valid_dates.append(date)
            except ValueError:
                pass  # Пропустить неверные форматы дат

    if valid_dates:
        latest_date = max(valid_dates)
    else:
        latest_date = datetime.now() + timedelta(days=365 * 3)  # Текущая дата + 3 года

    return latest_date.isoformat()    