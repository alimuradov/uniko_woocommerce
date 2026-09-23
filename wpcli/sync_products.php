<?php
/**
 * Синхронизация товаров WooCommerce напрямую через WooCommerce CRUD -
 * замена REST-батчей (products/batch), которые падают по таймауту на
 * большом объёме.
 *
 * Запуск: wp eval-file wpcli/sync_products.php <payload.json> --path=<WP_PATH>
 * $args[0] - путь к JSON-файлу с товарами (собирает utils/wpcli_sync.py).
 *
 * Единственные raw-SQL запросы в этом файле - SELECT (поиск существующих
 * товаров по SKU и категории по имени). Все записи идут через
 * WC_Product/WC_Product_Attribute CRUD, никаких INSERT/UPDATE напрямую в БД.
 */

global $wpdb;

if (empty($args[0]) || !file_exists($args[0])) {
    fwrite(STDERR, "Не передан путь к JSON с товарами\n");
    exit(1);
}

$payload = json_decode(file_get_contents($args[0]), true);
if (!is_array($payload)) {
    fwrite(STDERR, "Невалидный JSON в payload\n");
    exit(1);
}

function uniko_resolve_category_id($group_name) {
    global $wpdb;
    $group_name = trim((string) $group_name);
    if ($group_name === '') {
        return null;
    }
    $term_id = $wpdb->get_var($wpdb->prepare(
        "SELECT t.term_id FROM {$wpdb->terms} t
         INNER JOIN {$wpdb->term_taxonomy} tt ON t.term_id = tt.term_id
         WHERE tt.taxonomy = 'product_cat' AND LOWER(TRIM(t.name)) = LOWER(%s)
         LIMIT 1",
        $group_name
    ));
    return $term_id ? (int) $term_id : null;
}

function uniko_resolve_term_ids($taxonomy, $names) {
    $ids = [];
    foreach ((array) $names as $name) {
        $name = trim((string) $name);
        if ($name === '') {
            continue;
        }
        $term = get_term_by('name', $name, $taxonomy);
        if (!$term) {
            $result = wp_insert_term($name, $taxonomy);
            if (is_wp_error($result)) {
                $term = get_term_by('name', $name, $taxonomy);
                if (!$term) {
                    continue;
                }
                $ids[] = (int) $term->term_id;
                continue;
            }
            $ids[] = (int) $result['term_id'];
        } else {
            $ids[] = (int) $term->term_id;
        }
    }
    return $ids;
}

// Шаг 1: дешёвый lookup существующих товаров (read-only, через готовую
// индексную таблицу WooCommerce, без выгрузки полных объектов товаров)
$existing = [];
$rows = $wpdb->get_results(
    // JOIN с posts отсекает осиротевшие строки lookup (товар удалён, строка
    // осталась) - иначе такой SKU считается существующим и не создаётся заново
    "SELECT l.product_id, l.sku, l.stock_status FROM {$wpdb->prefix}wc_product_meta_lookup l
     INNER JOIN {$wpdb->posts} p ON p.ID = l.product_id",
    ARRAY_A
);
foreach ($rows as $row) {
    $sku = preg_replace('/\D/', '', (string) $row['sku']);
    if ($sku === '') {
        continue;
    }
    $existing[$sku] = [
        'id' => (int) $row['product_id'],
        'stock_status' => $row['stock_status'],
    ];
}

$payload_skus = [];
foreach ($payload as $row) {
    $payload_skus[(string) $row['sku']] = true;
}

$created = 0;
$updated = 0;
$outofstock = 0;
$errors = 0;
$error_skus = [];

// Шаг 2: снимаем с остатка товары, которых нет в новой партии
foreach ($existing as $sku => $info) {
    if (isset($payload_skus[$sku]) || $info['stock_status'] === 'outofstock') {
        continue;
    }
    try {
        $product = wc_get_product($info['id']);
        if (!$product) {
            continue;
        }
        $product->set_stock_status('outofstock');
        // Товар пропал из выгрузки целиком - у него больше нет ни одного
        // поставляющего филиала, поэтому чистим весь накопленный остаток по
        // филиалам (см. тот же диф ниже, в ветке обновления).
        foreach ($product->get_meta_data() as $meta) {
            $product->delete_meta_data($meta->key);
        }
        $product->save();
        $outofstock++;
    } catch (\Throwable $e) {
        $errors++;
        $error_skus[] = $sku;
        fwrite(STDERR, "outofstock error sku={$sku}: {$e->getMessage()}\n");
    }
}

echo "Снято с остатка: {$outofstock}\n";

// Шаг 3: создаём/обновляем товары. Каждый товар - независимая save(), одна
// ошибка не прерывает и не портит обработку остальных.
$processed = 0;
$total = count($payload);

foreach ($payload as $row) {
    $processed++;
    $sku = (string) $row['sku'];

    try {
        $is_new = !isset($existing[$sku]);
        $product = $is_new ? new WC_Product_Simple() : wc_get_product($existing[$sku]['id']);
        if (!$product) {
            throw new \Exception('не удалось загрузить товар');
        }

        $product->set_name($row['name']);
        $product->set_regular_price((string) $row['regular_price']);
        $product->set_manage_stock(false);
        $product->set_stock_quantity($row['stock_quantity']);
        $product->set_stock_status($row['stock_status']);

        // slug/sku выставляем только при создании - ресинк не должен
        // переписывать вручную отредактированный slug (как и в REST-пути)
        if ($is_new) {
            $product->set_slug($row['slug']);
            $product->set_sku($sku);
        }

        $category_id = uniko_resolve_category_id($row['category_name'] ?? '');
        $product->set_category_ids($category_id ? [$category_id] : []);

        $attributes = [];
        foreach ((array) ($row['attributes'] ?? []) as $taxonomy => $names) {
            $term_ids = uniko_resolve_term_ids($taxonomy, $names);
            $attribute = new WC_Product_Attribute();
            $attribute->set_id(wc_attribute_taxonomy_id_by_name($taxonomy));
            $attribute->set_name($taxonomy);
            $attribute->set_options($term_ids);
            $attribute->set_position(0);
            $attribute->set_visible(true);
            $attribute->set_variation(false);
            $attributes[] = $attribute;
        }
        // Кастомные (не таксономийные) атрибуты - значение хранится прямо в
        // товаре, никаких термов/wp_insert_term. Обязательно для значений,
        // почти уникальных на партию (напр. "Срок годности", "Штрихкод") -
        // иначе термы накапливаются без ограничения (см. инцидент с
        // pa_datevalid/pa_scancod). Значение может быть скаляром (одна дата)
        // или массивом (несколько штрихкодов на товар) - принимаем оба вида.
        foreach ((array) ($row['custom_attributes'] ?? []) as $name => $value) {
            $values = is_array($value) ? $value : [$value];
            $values = array_values(array_filter(array_map(
                static function ($v) { return trim((string) $v); },
                $values
            ), static function ($v) { return $v !== ''; }));
            if (empty($values)) {
                continue;
            }
            $attribute = new WC_Product_Attribute();
            $attribute->set_id(0);
            $attribute->set_name($name);
            $attribute->set_options($values);
            $attribute->set_position(0);
            $attribute->set_visible(true);
            $attribute->set_variation(false);
            $attributes[] = $attribute;
        }
        $product->set_attributes($attributes);

        // Мета-ключи остатка по филиалам должны точно отражать текущую
        // выгрузку: если товар обновляется, а не создаётся заново, чистим
        // ключи филиалов, которых нет в текущем импорте для этого SKU -
        // иначе устаревшие филиалы копятся в meta_data бесконечно.
        if (!$is_new) {
            $incoming_keys = array_map('strval', array_keys((array) ($row['meta_data'] ?? [])));
            foreach ($product->get_meta_data() as $meta) {
                if (!in_array((string) $meta->key, $incoming_keys, true)) {
                    $product->delete_meta_data($meta->key);
                }
            }
        }

        foreach ((array) ($row['meta_data'] ?? []) as $key => $value) {
            $product->update_meta_data($key, $value);
        }

        $product->save();
        $is_new ? $created++ : $updated++;
    } catch (\Throwable $e) {
        $errors++;
        $error_skus[] = $sku;
        fwrite(STDERR, "product error sku={$sku}: {$e->getMessage()}\n");
    }

    if ($processed % 200 === 0) {
        echo "Обработано {$processed}/{$total}\n";
    }
}

echo "Готово. Создано: {$created}, обновлено: {$updated}, снято с остатка: {$outofstock}, ошибок: {$errors}\n";

// Последняя строка stdout - JSON-сводка, её парсит utils/wpcli_sync.py
echo json_encode([
    'created' => $created,
    'updated' => $updated,
    'outofstock' => $outofstock,
    'errors' => $errors,
    'error_skus' => array_slice($error_skus, 0, 50),
]) . "\n";
