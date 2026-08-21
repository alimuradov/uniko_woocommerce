<?php
/**
 * Одноразовая чистка накопленных термов pa_scancod после перевода атрибута
 * "Штрихкод" в кастомный (не таксономийный) - см. wpcli/sync_products.php и
 * utils/wpcli_sync.py. Термы больше не создаются и не используются ни одним
 * товаром - их безопасно удалить целиком.
 *
 * Запуск: wp eval-file wpcli/cleanup_pa_scancod_terms.php --path=<WP_PATH>
 */

$term_ids = get_terms([
    'taxonomy' => 'pa_scancod',
    'fields' => 'ids',
    'hide_empty' => false,
]);

if (is_wp_error($term_ids)) {
    fwrite(STDERR, $term_ids->get_error_message() . "\n");
    exit(1);
}

$total = count($term_ids);
$deleted = 0;
foreach ($term_ids as $term_id) {
    if (wp_delete_term($term_id, 'pa_scancod')) {
        $deleted++;
    }
}

echo "Термов найдено: {$total}, удалено: {$deleted}\n";
