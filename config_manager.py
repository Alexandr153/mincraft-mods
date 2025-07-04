import configparser
import os
from pathlib import Path


class ConfigManager:
    def __init__(self, config_path="config.ini"):
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        self.load()

    def load(self):
        """Загрузка конфигурации"""
        if self.config_path.exists():
            self.config.read(self.config_path, encoding='utf-8')

    def save(self):
        """Сохранение конфигурации"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)

    def get(self, section, key, fallback=None):
        """Получение значения"""
        return self.config.get(section, key, fallback=fallback)

    def set(self, section, key, value):
        """Установка значения"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = str(value)
