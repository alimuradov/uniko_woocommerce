import os
import json
import tempfile
import time

import paramiko
from dotenv import load_dotenv

from utils.utils import (
    group_products_by_codtmc,
    calculate_total_ost,
    find_max_price,
    get_stocks_meta,
    get_field_values,
    get_unique_field_values,
    get_latest_date,
)
from utils.func import generate_slug

load_dotenv()

SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = int(os.getenv("SSH_PORT", "22"))
SSH_USER = os.getenv("SSH_USER")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
WP_PATH = os.getenv("WP_PATH")
WP_CLI_BIN = os.getenv("WP_CLI_BIN", "wp")
WP_SYNC_SCRIPT_PATH = os.getenv("WP_SYNC_SCRIPT_PATH")
REMOTE_TMP_DIR = os.getenv("REMOTE_TMP_DIR", "/tmp")


def build_products_payload(stocks):
    """Собирает JSON-совместимый payload для wpcli/sync_products.php.
    Использует те же хелперы, что и REST-путь (utils/api.py), но не делает
    сетевых вызовов сама - только форма данных.
    """
    grouped = group_products_by_codtmc(stocks)
    payload = []
    for codtmc, group in grouped.items():
        ostatok = calculate_total_ost(group)
        payload.append({
            "sku": str(codtmc),
            "name": group[0]['name'],
            "slug": generate_slug(group[0]['name']),
            "regular_price": str(find_max_price(group)),
            "stock_quantity": ostatok,
            "stock_status": "instock" if ostatok > 0 else "outofstock",
            "category_name": group[0]['group'],
            # Таксономийные (select) атрибуты - термы общие на весь каталог,
            # годится только для значений с малым числом вариантов.
            "attributes": {
                "pa_farmgroup": get_field_values(group, 'farmgroup'),
                "pa_group": get_field_values(group, 'group'),
                "pa_factory": get_field_values(group, 'factory'),
                "pa_mnn": get_field_values(group, 'mnn'),
                "pa_brand": get_field_values(group, 'brand'),
                "pa_isrecept": ["Да" if group[0]['isrecept'] else "Нет"],
                "pa_delupak": get_field_values(group, 'delupak'),
                "pa_islife": ["Да" if group[0]['islife'] else "Нет"],
            },
            # Кастомные (не таксономийные) атрибуты - значение хранится прямо в
            # товаре, term'ы не создаются. "Срок годности" почти уникальна для
            # каждой партии, "Штрихкод" почти уникален на партию - как таксономия
            # они раздули pa_datevalid до 2.77 млн термов (и по тому же паттерну
            # pa_scancod до ~30 000) и положили bootstrap WordPress/WooCommerce.
            # Не повторять.
            "custom_attributes": {
                "Срок годности": get_latest_date(group),
                "Штрихкод": get_unique_field_values(group, 'scancod'),
            },
            "meta_data": {item['key']: item['value'] for item in get_stocks_meta(group)},
        })
    return payload


def _connect():
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {"hostname": SSH_HOST, "port": SSH_PORT, "username": SSH_USER}
    if SSH_KEY_PATH:
        connect_kwargs["key_filename"] = SSH_KEY_PATH
    else:
        connect_kwargs["password"] = SSH_PASSWORD
    ssh.connect(**connect_kwargs, timeout=30, banner_timeout=30, auth_timeout=30)
    # Без keepalive молча умершее соединение (VPN/NAT) не замечается никогда,
    # и stdout.read() ниже висит вечно - скрипт не завершается.
    ssh.get_transport().set_keepalive(30)
    return ssh


def _upload_and_run(local_path):
    """Одна попытка: подключиться, залить payload, выполнить sync_products.php."""
    ssh = _connect()
    try:
        remote_path = f"{REMOTE_TMP_DIR.rstrip('/')}/uniko_sync_{int(time.time())}.json"
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)

        command = (
            f"{WP_CLI_BIN} eval-file {WP_SYNC_SCRIPT_PATH} {remote_path} "
            f"--path={WP_PATH} --allow-root"
        )
        # timeout - на каждое чтение: скрипт печатает прогресс каждые 200
        # товаров, 30 минут тишины = соединение мертво, падаем в ретрай.
        _, stdout, stderr = ssh.exec_command(command, timeout=1800)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()

        if out:
            print(out)
        if err:
            print("STDERR:", err)

        if exit_status != 0:
            raise RuntimeError(f"wp eval-file завершился с кодом {exit_status}. stderr: {err}")

        summary_line = None
        for line in reversed(out.strip().splitlines()):
            line = line.strip()
            if line.startswith("{"):
                summary_line = line
                break
        if not summary_line:
            raise RuntimeError(f"Не удалось найти JSON-сводку в выводе скрипта. stdout: {out}")

        summary = json.loads(summary_line)

        try:
            sftp.remove(remote_path)
        except Exception:
            pass

        return summary
    finally:
        ssh.close()


def sync_products_via_wpcli(stocks):
    """Синк товаров напрямую на сервере через WP-CLI/WooCommerce CRUD вместо
    REST-батчей. Отдельная точка входа от utils.api.create_and_update_products -
    ничего в utils/api.py не меняется, main.py выбирает один из двух вызовов.
    """
    payload = build_products_payload(stocks)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        local_path = f.name

    try:
        last_error = None
        # Ретрай покрывает весь цикл подключение+заливка+выполнение, а не
        # только подключение - разрыв SSH-сессии может случиться и посреди
        # заливки payload (напр. "Corrupted MAC on input"), а не только при
        # установке соединения.
        for attempt in range(2):
            try:
                return _upload_and_run(local_path)
            except Exception as e:
                last_error = e
                print(f"Попытка синка {attempt + 1}/2 не удалась: {e}")
                time.sleep(10)
        raise RuntimeError(f"Синк через WP-CLI не удался за 2 попытки: {last_error}")
    finally:
        try:
            os.unlink(local_path)
        except OSError:
            pass
