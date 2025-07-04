import configparser
import os
import hashlib
import requests
import sys
import json
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

config = configparser.ConfigParser()
config.read('/Users/alexandrmitin/PycharmProjects/LauncherMinecraft/config.ini')

REPO = 'Alexandr153/mincraft-mods'
TAG = 'latest'
LOCAL_MODS = os.path.expanduser(
    config.get('paths', 'local_mods', fallback='~/.minecraft/mods/')
)

MODLIST_URL = f'https://github.com/{REPO}/releases/download/{TAG}/modlist.txt'
LOCAL_MODLIST = os.path.join(LOCAL_MODS, 'modlist.txt')
# ИСПРАВЛЕНО: файл должен быть в папке лаунчера, а не в папке модов
TO_UPDATE_PATH = Path(__file__).parent / 'mods_to_update.json'


def get_file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as file_obj:
        while True:
            chunk = file_obj.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def download_file(url, dest_path, pbar=None):
    print(f"  → Скачиваю {os.path.basename(dest_path)} ...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, 'wb') as file_out:
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                file_out.write(chunk)
                if pbar:
                    pbar.update(len(chunk))
    print(f"  → {os.path.basename(dest_path)} скачан.")


def get_remote_size(head_url):
    try:
        response = requests.head(head_url, allow_redirects=True, timeout=10)
        return int(response.headers.get('content-length', 0))
    except Exception:
        return 0


def check_updates():
    # 1. Скачиваем modlist.txt
    os.makedirs(LOCAL_MODS, exist_ok=True)
    print('Скачиваем modlist.txt...')
    download_file(MODLIST_URL, LOCAL_MODLIST)
    print('modlist.txt скачан.\n')

    # 2. Проверяем какие моды надо обновить (ускорено)
    print("Проверяю актуальность модов (ускорено)...")
    mods_info = []
    with open(LOCAL_MODLIST, 'r', encoding='utf-8') as modlist_file:
        for modlist_line in modlist_file:
            parts = modlist_line.strip().split()
            if len(parts) < 3:
                continue
            mod_name, remote_hash, mod_url = parts
            local_mod_path = os.path.join(LOCAL_MODS, mod_name)
            mods_info.append((mod_name, remote_hash, mod_url, local_mod_path))

    # Параллельно считаем хэши локальных файлов
    def check_mod_hash(mod_tuple):
        mod_name, remote_hash, mod_url, local_mod_path = mod_tuple
        if os.path.exists(local_mod_path):
            local_hash = get_file_hash(local_mod_path)
        else:
            local_hash = None
        return mod_name, remote_hash, mod_url, local_mod_path, local_hash

    with ThreadPoolExecutor(max_workers=8) as hash_executor:
        hash_results = list(
            tqdm(hash_executor.map(check_mod_hash, mods_info), total=len(mods_info), desc="Проверка файлов"))

    # Параллельно получаем размеры только для тех, что требуют обновления
    mods_to_update = []
    total_bytes = 0

    def get_mod_size_for_update(mod_with_hash):
        mod_name, remote_hash, mod_url, local_mod_path, local_hash = mod_with_hash
        if local_hash != remote_hash:
            mod_size = get_remote_size(mod_url)
            return mod_name, mod_url, local_mod_path, mod_size
        else:
            print(f"  → {mod_name}: актуален.")
            return None

    with ThreadPoolExecutor(max_workers=8) as size_executor:
        size_results = list(tqdm(size_executor.map(get_mod_size_for_update, hash_results), total=len(hash_results),
                                 desc="Получение размеров"))

    for mod_update_info in size_results:
        if mod_update_info:
            upd_name, upd_url, upd_path, upd_size = mod_update_info
            mods_to_update.append({
                'name': upd_name,
                'url': upd_url,
                'path': upd_path,
                'size': upd_size
            })
            total_bytes += upd_size
            print(f"  → {upd_name}: требуется обновление или скачивание.")

    # Сохраняем список на обновление
    with open(TO_UPDATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(mods_to_update, f, ensure_ascii=False, indent=2)

    print(f"\nПроверка завершена. Модов для обновления: {len(mods_to_update)}")
    print(f"Результаты сохранены в: {TO_UPDATE_PATH}")

    if mods_to_update:
        print("Для обновления доступны моды:")
        for mod in mods_to_update:
            print(f"  - {mod['name']}")
    else:
        print("Все моды актуальны.")


def do_update():
    # Загружаем список модов для обновления
    if not os.path.exists(TO_UPDATE_PATH):
        print("Нет информации о модах для обновления. Сначала выполните проверку!")
        return

    with open(TO_UPDATE_PATH, 'r', encoding='utf-8') as f:
        mods_to_update = json.load(f)

    total_bytes = sum(mod['size'] for mod in mods_to_update)
    if not mods_to_update:
        print("Нет модов для обновления.")
        return

    print(f'Скачиваем/обновляем {len(mods_to_update)} мод(ов)...')
    with tqdm(total=total_bytes, unit='B', unit_scale=True, desc='Общий прогресс') as progress_bar:
        with ThreadPoolExecutor(max_workers=4) as download_executor:
            futures = [
                download_executor.submit(download_file, mod['url'], mod['path'], progress_bar)
                for mod in mods_to_update
            ]  # ИСПРАВЛЕНО: добавлена закрывающая скобка

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f'Ошибка при скачивании: {e}')

    print('\nВсе моды обновлены.')
    # После успешного обновления можно удалить файл
    if os.path.exists(TO_UPDATE_PATH):
        os.remove(TO_UPDATE_PATH)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python update.py [check|update]")
        sys.exit(1)
    if sys.argv[1] == "check":
        check_updates()
    elif sys.argv[1] == "update":
        do_update()
    else:
        print("Неизвестная команда. Используйте check или update.")
