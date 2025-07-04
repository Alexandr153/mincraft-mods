import configparser
import subprocess
import sys


def launch_tlauncher():
    config_path = 'config.ini'
    config = configparser.ConfigParser()
    config.read(config_path)

    tlauncher_path = config.get('paths', 'tlauncher', fallback=None)
    if not tlauncher_path:
        print("Путь к TLauncher не указан в config.ini!")
        return False

    try:
        if tlauncher_path.endswith('.jar'):
            subprocess.run(['java', '-jar', tlauncher_path])
        else:
            subprocess.run(tlauncher_path.split())
        return True
    except Exception as e:
        print(f"Ошибка запуска TLauncher: {e}")
        return False


# Защита от автоматического выполнения при импорте
if __name__ == "__main__":
    launch_tlauncher()
