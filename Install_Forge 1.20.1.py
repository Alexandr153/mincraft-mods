import os
import configparser
import subprocess
from progress_bar import download_file_with_progress


def get_downloads_folder():
    # Для macOS и Linux
    downloads = os.path.expanduser('~/Downloads')
    # Для Windows (если нужно сделать кроссплатформенно)
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders') as key:
                downloads = winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
        except Exception:
            downloads = os.path.expanduser('~/Downloads')
    return downloads


def get_or_ask_minecraft_path(config_path):
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
    mc_path = config.get('paths', 'local_minecraft', fallback=None)
    if not mc_path:
        mc_path = input("Укажите путь к папке Minecraft: ").strip()
        if not os.path.isdir(mc_path):
            print("Папка не найдена, проверьте путь!")
            exit(1)
        if 'paths' not in config:
            config['paths'] = {}
        config['paths']['local_minecraft'] = mc_path
        with open(config_path, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    return os.path.expanduser(mc_path)


def install_forge_and_update_config(config_path, mc_version='1.20.1', forge_build='47.2.20'):
    mc_dir = get_or_ask_minecraft_path(config_path)
    mods_dir = os.path.join(mc_dir, 'mods')

    # Путь к инсталлятору Forge — теперь в папке загрузок
    downloads_folder = get_downloads_folder()
    forge_installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version}-{forge_build}/forge-{mc_version}-{forge_build}-installer.jar"
    forge_installer_path = os.path.join(downloads_folder, "forge_installer.jar")
    download_file_with_progress(forge_installer_url, forge_installer_path)
    print("Forge-инсталлятор скачан, теперь запускаем установку...")

    subprocess.run(["java", "-jar", forge_installer_path])

    # Поиск установленной forge-версии
    from minecraft_launcher_lib.utils import get_installed_versions
    all_versions = get_installed_versions(mc_dir)
    installed_forge_id = None
    for ver in all_versions:
        if 'forge' in ver['id'] and mc_version in ver['id']:
            installed_forge_id = ver['id']
            break
    if installed_forge_id is None:
        raise Exception('Не удалось найти установленную forge-версию после установки')

    # Запись пути к mods в конфиг
    config = configparser.ConfigParser()
    config.read(config_path)
    config['paths']['local_mods'] = mods_dir
    with open(config_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

    return installed_forge_id, mc_dir, mods_dir


if __name__ == '__main__':
    path_to_config = '/Users/alexandrmitin/PycharmProjects/LauncherMinecraft/config.ini'
    forge_version_id, minecraft_path, mods_path = install_forge_and_update_config(path_to_config)
    print(f'Forge установлен: {forge_version_id}')
    print(f'Путь к Minecraft: {minecraft_path}')
    print(f'Путь к модам: {mods_path}')
