from transliterate import translit

def generate_slug(text):
    # Преобразование кириллицы в латиницу
    slug = translit(text, 'ru', reversed=True)
    # Замена символов, не являющихся буквами или цифрами, на "-"
    slug = slug.lower().replace(' ', '-').replace('_', '-').replace('.', '-')
    # Удаление других символов, кроме букв, цифр и "-"
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    # Удаление повторяющихся "-"
    slug = '-'.join(filter(None, slug.split('-')))
    return slug