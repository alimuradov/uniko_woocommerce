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

def generate_variations(objects, existing_attributes):
    variations = []  # Список для хранения значений поля
    attributes = []

    i=0
    for obj in objects:
        i += 1
        attribute_filial = {
            "id": get_attribute_id_by_name(existing_attributes, "Филиал"),
            "option": obj['namepodr']
        }

        attribute_price = {
            "id": get_attribute_id_by_name(existing_attributes, "Цена"),
            "option": obj['price']
        }

        attribute_ost = {
            "id": get_attribute_id_by_name(existing_attributes, "Остаток"),
            "option": obj['ost']
        }                
        attributes.append(attribute_filial)
        attributes.append(attribute_price)
        attributes.append(attribute_ost)
        
        variation = {
            "regular_price": obj['price'],
            "price": obj['price'],
            "attributes": attributes

        }
        variations.append(variation)

    return variations

