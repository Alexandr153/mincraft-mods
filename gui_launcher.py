import hashlib

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import configparser
import os
import threading
import subprocess
import sys
from pathlib import Path
from datetime import datetime

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from mcstatus import JavaServer
import json


class MinecraftLauncher:
    def __init__(self):
        # Настройка CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Создание главного окна
        self.root = ctk.CTk()
        self.root.title("Minecraft Mod Launcher")
        self.root.geometry("1200x925")
        self.root.resizable(True, True)

        self.theme_var = tk.StringVar(value="dark")

        # Путь к конфигурации
        self.config_path = Path(__file__).parent / "config.ini"
        self.config = configparser.ConfigParser()
        self.update_status_path = Path(__file__).parent / "mods_to_update.json"

        # Переменные для путей
        self.minecraft_path = tk.StringVar()
        self.tlauncher_path = tk.StringVar()
        self.mods_path = tk.StringVar()

        # Состояние модов
        self.mods_need_update = None
        self.outdated_mods = []
        self.check_performed = False

        # Переменные для темы и сервера
        self.current_theme = "dark"
        self.server_status = "🔄 Проверка..."
        self.server_address = "ip-213-152-43-29.joinserver.xyz:25577"
        self.server_name = "Our World"
        self.check_server_running = False

        # Прочие переменные
        self.path_info_text = None
        self.theme_icon = None
        self.theme_switch = None
        self.server_status_label = None
        self.mod_status_frame = None
        self.mods_list = None
        self.mods_info_label = None
        self.launch_btn = None
        self.mod_status_label = None
        self.check_btn = None
        self.status_label = None
        self.settings_btn = None
        self.log_text = None
        self.minecraft_settings_entry = None
        self.filter_info = None
        self.filter_success = None
        self.filter_warning = None
        self.filter_error = None
        self.tlauncher_settings_entry = None

        # Инициализация
        self.load_config()
        self.create_widgets()
        self.check_mod_status()

    def load_config(self):
        """Загрузка конфигурации из файла"""
        if self.config_path.exists():
            self.config.read(self.config_path)

            # Загрузка путей
            self.minecraft_path.set(
                self.config.get('paths', 'local_minecraft', fallback='')
            )
            self.tlauncher_path.set(
                self.config.get('paths', 'tlauncher', fallback='')
            )
            self.mods_path.set(
                self.config.get('paths', 'local_mods', fallback='')
            )

    def save_config(self):
        """Сохранение конфигурации в файл"""
        if 'paths' not in self.config:
            self.config['paths'] = {}

        self.config['paths']['local_minecraft'] = self.minecraft_path.get()
        self.config['paths']['tlauncher'] = self.tlauncher_path.get()
        self.config['paths']['local_mods'] = self.mods_path.get()

        with open(self.config_path, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def set_text_readonly(self, textbox, text):
        """Обновление текста в readonly textbox"""
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("1.0", text)
        textbox.configure(state="disabled")

    def create_widgets(self):
        """Создание интерфейса"""

        # Верхняя панель с заголовком и переключателем темы
        top_frame = ctk.CTkFrame(self.root, height=60)
        top_frame.pack(fill="x", padx=20, pady=(10, 0))
        top_frame.pack_propagate(False)

        # Заголовок слева внутри top_frame
        title_label = ctk.CTkLabel(
            top_frame,
            text="Minecraft Mod Launcher",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=15)

        # Переключатель темы (справа)
        theme_frame = ctk.CTkFrame(top_frame)
        theme_frame.pack(side="right", padx=20, pady=15)

        # Создаем отдельный лейбл для иконки
        self.theme_icon = ctk.CTkLabel(
            theme_frame,
            text="🌙",  # Начальная иконка
            font=ctk.CTkFont(size=20)
        )
        self.theme_icon.pack(side="left", padx=5)

        self.theme_switch = ctk.CTkSwitch(
            theme_frame,
            text="Тёмная тема",
            command=self.toggle_theme,
            variable=self.theme_var,
            onvalue="dark",
            offvalue="light"
        )
        self.theme_switch.pack(side="left", padx=10)

        # ГЛАВНЫЙ КОНТЕЙНЕР - разделен на три части
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(pady=10, padx=20, fill="both", expand=True)

        # === ЛЕВАЯ ПАНЕЛЬ: Информация о путях ===
        left_frame = ctk.CTkFrame(main_container, width=300)
        left_frame.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left_frame.pack_propagate(False)

        info_title = ctk.CTkLabel(
            left_frame,
            text="Конфигурация",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        info_title.pack(pady=10)

        # Статус сервера (внизу левой панели)
        server_frame = ctk.CTkFrame(left_frame)
        server_frame.pack(side="bottom", pady=10, padx=10, fill="x")

        server_title = ctk.CTkLabel(
            server_frame,
            text=f"Сервер: {self.server_name}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        server_title.pack(pady=5)

        self.server_status_label = ctk.CTkLabel(
            server_frame,
            text=self.server_status,
            font=ctk.CTkFont(size=12)
        )
        self.server_status_label.pack(pady=5)

        # Показываем адрес сервера (только для информации)
        server_addr_label = ctk.CTkLabel(
            server_frame,
            text=self.server_address,
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        server_addr_label.pack(pady=2)

        # Кнопка для ручной проверки
        check_server_btn = ctk.CTkButton(
            server_frame,
            text="🔄 Проверить сервер",
            command=self.manual_check_server,
            height=30
        )
        check_server_btn.pack(pady=5, fill="x", padx=10)

        # Запуск автоматической проверки сервера
        self.start_server_monitoring()

        # Информация о текущих путях
        self.path_info_text = ctk.CTkTextbox(left_frame, height=200)
        self.path_info_text.configure(state="disabled")
        self.path_info_text.pack(pady=5, padx=10, fill="x")
        self.update_path_info()

        # Кнопка настроек
        self.settings_btn = ctk.CTkButton(
            left_frame,
            text="⚙️ Настройки путей",
            command=self.show_settings,
            fg_color="orange" if not self.all_paths_configured() else None,
            hover_color="darkorange" if not self.all_paths_configured() else None
        )
        self.settings_btn.pack(pady=10, padx=10, fill="x")

        # Статус модов
        self.mod_status_frame = ctk.CTkFrame(left_frame)
        self.mod_status_frame.pack(pady=10, padx=10, fill="x")

        mod_status_title = ctk.CTkLabel(
            self.mod_status_frame,
            text="Статус модов",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        mod_status_title.pack(pady=5)

        self.mod_status_label = ctk.CTkLabel(
            self.mod_status_frame,
            text="🔄 Проверка не выполнена",
            font=ctk.CTkFont(size=12)
        )
        self.mod_status_label.pack(pady=5)

        # Кнопки управления
        buttons_frame = ctk.CTkFrame(left_frame)
        buttons_frame.pack(pady=10, padx=10, fill="x")

        self.check_btn = ctk.CTkButton(
            buttons_frame,
            text="🔍 Проверить обновления",
            font=ctk.CTkFont(size=12),
            height=40,
            command=self.check_updates
        )
        self.check_btn.pack(pady=5, fill="x")

        self.update_btn = ctk.CTkButton(
            buttons_frame,
            text="⬇️ Обновить моды",
            font=ctk.CTkFont(size=12),
            height=40,
            command=self.update_mods,
            state="disabled"
        )
        self.update_btn.pack(pady=5, fill="x")

        self.launch_btn = ctk.CTkButton(
            buttons_frame,
            text="🎮 Запустить игру",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            fg_color="green",
            hover_color="darkgreen",
            command=self.launch_minecraft
        )
        self.launch_btn.pack(pady=10, fill="x")

        # === ЦЕНТРАЛЬНАЯ ПАНЕЛЬ: ЛОГ КОНСОЛЬ ===
        center_frame = ctk.CTkFrame(main_container)
        center_frame.pack(side="left", fill="both", expand=True, padx=5, pady=10)

        log_title = ctk.CTkLabel(
            center_frame,
            text="🗒️ Логи операций",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        log_title.pack(pady=10)

        # Лог область - ЦЕНТРАЛЬНАЯ И БОЛЬШАЯ
        self.log_text = ctk.CTkTextbox(
            center_frame,
            height=500,  # Увеличена высота
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.log_text.pack(pady=5, padx=15, fill="both", expand=True)

        self.setup_log_context_menu()
        self.setup_hotkeys()

        # Кнопка очистки логов
        clear_log_btn = ctk.CTkButton(
            center_frame,
            text="🗑️ Очистить логи",
            command=self.clear_logs,
            fg_color="gray",
            hover_color="darkgray",
            height=30
        )
        clear_log_btn.pack(pady=5)

        # === ПРАВАЯ ПАНЕЛЬ: Детали модов ===
        right_frame = ctk.CTkFrame(main_container, width=280)
        right_frame.pack(side="right", fill="y", padx=(5, 10), pady=10)
        right_frame.pack_propagate(False)

        mods_title = ctk.CTkLabel(
            right_frame,
            text="Моды для обновления",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        mods_title.pack(pady=10)

        self.mods_list = ctk.CTkTextbox(right_frame, height=300)
        self.mods_list.pack(pady=5, padx=10, fill="both", expand=True)
        self.update_mods_list()

        # === УЛУЧШЕННЫЕ ВОДЯНЫЕ ЗНАКИ ===
        watermark_frame = ctk.CTkFrame(self.root, fg_color="transparent", height=25)
        watermark_frame.pack(side="bottom", fill="x", pady=(0, 5))
        watermark_frame.pack_propagate(False)

        # Левый водяной знак с иконкой
        left_watermark = ctk.CTkLabel(
            watermark_frame,
            text="Clouse1",
            font=ctk.CTkFont(size=10, weight="normal"),
            text_color=("gray60", "gray40"),
            fg_color="transparent"
        )
        left_watermark.pack(side="left", padx=15, pady=2)

        # Правый водяной знак с иконкой версии
        right_watermark = ctk.CTkLabel(
            watermark_frame,
            text="Version Alpha 1.0",
            font=ctk.CTkFont(size=10, weight="normal"),
            text_color=("gray60", "gray40"),
            fg_color="transparent"
        )
        right_watermark.pack(side="right", padx=15, pady=2)

        # Статус бар
        self.status_label = ctk.CTkLabel(
            self.root,
            text="Требуется проверка",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="bottom", pady=0)

        # Инициализация логов
        self.log_info("🚀 Лаунчер запущен")
        if not self.all_paths_configured():
            self.log_warning("⚠️ Необходимо настроить пути в настройках")

    def setup_hotkeys(self):
        """Настройка горячих клавиш для логов"""
        self.root.bind('<Control-s>', lambda e: self.save_logs_to_file())
        self.root.bind('<Control-f>', lambda e: self.search_in_logs())
        self.root.bind('<Control-l>', lambda e: self.clear_logs_with_confirmation())

    def check_mod_status(self):
        """Проверка состояния модов ТОЛЬКО при запуске лаунчера"""
        # ПРИНУДИТЕЛЬНО сбрасываем статус при каждом запуске
        self.reset_mod_status()

        # Не читаем старый файл - всегда требуем новую проверку при запуске
        self.log_warning("🔴 При запуске требуется проверка актуальности модов")
        self.log_info("💡 Нажмите 'Проверить обновления' для продолжения")

    def reset_mod_status(self):
        """Сброс статуса модов к состоянию 'требуется проверка'"""
        self.mods_need_update = None
        self.outdated_mods = []
        self.check_performed = False
        self.update_btn.configure(state="disabled")
        self.update_mod_status_display()
        self.update_mods_list()
        self.log_warning("🔴 Требуется проверка модов перед запуском игры")

    def update_mod_status_display(self):
        """Обновление отображения статуса модов"""
        if self.mods_need_update is None or not self.check_performed:
            # Статус "не проверено" - кнопка активна, но с предупреждением
            self.mod_status_label.configure(
                text="🔄 Требуется проверка модов",
                text_color="red"
            )
            # КНОПКА ВСЕГДА АКТИВНА
            self.launch_btn.configure(
                text="🎮 Запустить игру",
                state="normal",
                fg_color="green",
                hover_color="darkgreen"
            )
        elif self.mods_need_update:
            count = len(self.outdated_mods)
            self.mod_status_label.configure(
                text=f"⚠️ {count} мод(ов) требуют обновления",
                text_color="orange"
            )
            # КНОПКА ВСЕГДА АКТИВНА
            self.launch_btn.configure(
                text="🎮 Запустить игру",
                state="normal",
                fg_color="green",
                hover_color="darkgreen"
            )
        else:
            self.mod_status_label.configure(
                text="✅ Все моды актуальны",
                text_color="green"
            )
            # КНОПКА АКТИВНА
            self.launch_btn.configure(
                text="🎮 Запустить игру",
                state="normal",
                fg_color="green",
                hover_color="darkgreen"
            )

    def update_mods_list(self):
        """Обновление списка модов с размерами файлов"""
        if self.outdated_mods:
            text = "Моды требующие обновления:\n\n"
            total_size = 0
            for i, mod in enumerate(self.outdated_mods, 1):
                mod_name = mod.get('name', 'Неизвестный мод')
                mod_size = mod.get('size', 0)
                total_size += mod_size
                formatted_size = self.format_file_size(mod_size)
                text += f"{i}. {mod_name} ({formatted_size})\n"

            text += f"\nОбщий размер: {self.format_file_size(total_size)}"
        else:
            text = "Все моды актуальны 😊\n\nЛибо проверка еще не выполнена."

        self.set_text_readonly(self.mods_list, text)

    def log_info(self, message):
        """Информационное сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] ℹ️ {message}\n"

        # Временно разрешаем редактирование
        self.log_text.configure(state="normal")
        self.log_text.insert("end", formatted_message)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")  # Возвращаем readonly
        self.root.update()

    def log_success(self, message):
        """Сообщение об успехе в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] ✅ {message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", formatted_message)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.root.update()

    def log_warning(self, message):
        """Предупреждение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] ⚠️ {message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", formatted_message)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.root.update()

    def log_error(self, message):
        """Ошибка в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] ❌ {message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", formatted_message)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.root.update()

    def clear_logs(self):
        """Очистка логов"""
        self.log_text.configure(state="normal")  # Разрешаем изменение
        self.log_text.delete("1.0", "end")  # Очищаем всё
        self.log_text.configure(state="disabled")  # Запрещаем изменение пользователю
        self.log_info("Логи очищены")  # Добавляем служебную запись

    def all_paths_configured(self):
        """Проверка, что все ОБЯЗАТЕЛЬНЫЕ пути настроены"""
        # Теперь проверяем папку Minecraft
        return (self.minecraft_path.get() and
                os.path.exists(self.minecraft_path.get()) and
                os.path.isdir(self.minecraft_path.get()))  # Добавляем проверку на папку

    def update_path_info(self):
        """Обновление информации о путях"""
        minecraft_status = "✅" if (self.minecraft_path.get() and
                                   os.path.exists(self.minecraft_path.get()) and
                                   os.path.isdir(self.minecraft_path.get())) else "❌"
        tlauncher_status = "✅" if self.tlauncher_path.get() and os.path.exists(self.tlauncher_path.get()) else "⚪"
        mods_status = "✅" if self.mods_path.get() and os.path.exists(self.mods_path.get()) else "❌"

        info = f"""{minecraft_status} Папка Minecraft (обязательно):
    {self.minecraft_path.get()[:40] + '...' if len(self.minecraft_path.get()) > 40 else self.minecraft_path.get() or 'Не настроена'}

    {tlauncher_status} TLauncher (опционально):
    {self.tlauncher_path.get()[:40] + '...' if len(self.tlauncher_path.get()) > 40 else self.tlauncher_path.get() or 'Не указан'}

    {mods_status} Моды:
    {self.mods_path.get()[:40] + '...' if len(self.mods_path.get()) > 40 else self.mods_path.get() or 'Не настроен'}"""

        self.set_text_readonly(self.path_info_text, info)

    def show_settings(self):
        """Окно настроек"""
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("Настройки путей")
        settings_window.geometry("600x600")
        settings_window.transient(self.root)
        settings_window.grab_set()

        # Заголовок
        title = ctk.CTkLabel(
            settings_window,
            text="Настройки путей",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=20)

        # Основной фрейм
        main_frame = ctk.CTkFrame(settings_window)
        main_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Путь к папке Minecraft (ОБЯЗАТЕЛЬНЫЙ)
        minecraft_label = ctk.CTkLabel(
            main_frame,
            text="Путь к папке Minecraft: *",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        minecraft_label.pack(anchor="w", padx=20, pady=(20, 5))

        minecraft_hint = ctk.CTkLabel(
            main_frame,
            text="Папка с установленным Minecraft (содержит launcher_profiles.json)",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        minecraft_hint.pack(anchor="w", padx=20, pady=(0, 5))

        minecraft_frame = ctk.CTkFrame(main_frame)
        minecraft_frame.pack(padx=20, pady=5, fill="x")

        self.minecraft_settings_entry = ctk.CTkEntry(
            minecraft_frame,
            placeholder_text="Выберите папку Minecraft..."
        )
        self.minecraft_settings_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.minecraft_settings_entry.insert(0, self.minecraft_path.get())

        minecraft_browse_btn = ctk.CTkButton(
            minecraft_frame,
            text="📁",
            width=50,
            command=lambda: self.browse_minecraft_folder(self.minecraft_settings_entry)
        )
        minecraft_browse_btn.pack(side="right", padx=10, pady=10)

        # Путь к TLauncher (ОПЦИОНАЛЬНЫЙ)
        tlauncher_label = ctk.CTkLabel(
            main_frame,
            text="Путь к TLauncher (опционально):",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        tlauncher_label.pack(anchor="w", padx=20, pady=(20, 5))

        tlauncher_hint = ctk.CTkLabel(
            main_frame,
            text="Если не указан, игра запустится напрямую",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        tlauncher_hint.pack(anchor="w", padx=20, pady=(0, 5))

        tlauncher_frame = ctk.CTkFrame(main_frame)
        tlauncher_frame.pack(padx=20, pady=5, fill="x")

        self.tlauncher_settings_entry = ctk.CTkEntry(
            tlauncher_frame,
            placeholder_text="Выберите TLauncher (необязательно)..."
        )
        self.tlauncher_settings_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.tlauncher_settings_entry.insert(0, self.tlauncher_path.get())

        tlauncher_browse_btn = ctk.CTkButton(
            tlauncher_frame,
            text="📁",
            width=50,
            command=lambda: self.browse_minecraft_file(self.tlauncher_settings_entry)
        )
        tlauncher_browse_btn.pack(side="right", padx=10, pady=10)

        # Путь к модам (автоматический)
        mods_label = ctk.CTkLabel(
            main_frame,
            text="Путь к модам (автоматический):",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        mods_label.pack(anchor="w", padx=20, pady=(20, 5))

        self.mods_info_label = ctk.CTkLabel(
            main_frame,
            text=self.mods_path.get() or "Будет определён автоматически",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.mods_info_label.pack(anchor="w", padx=20, pady=5)

        # Кнопки
        buttons_frame = ctk.CTkFrame(settings_window)
        buttons_frame.pack(pady=20, fill="x")

        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Отмена",
            command=settings_window.destroy,
            fg_color="gray",
            hover_color="darkgray"
        )
        cancel_btn.pack(side="left", padx=20, pady=10)

        save_settings_btn = ctk.CTkButton(
            buttons_frame,
            text="💾 Сохранить настройки",
            command=lambda: self.save_settings_config(settings_window),
            fg_color="green",
            hover_color="darkgreen"
        )
        save_settings_btn.pack(side="right", padx=20, pady=10)

    def save_settings_config(self, window):
        """Сохранение настроек из окна настроек"""
        minecraft_path = self.minecraft_settings_entry.get().strip()
        tlauncher_path = self.tlauncher_settings_entry.get().strip()

        # Проверяем только обязательные поля
        if not minecraft_path:
            messagebox.showerror("Ошибка", "Пожалуйста, укажите папку Minecraft!")
            self.settings_btn.configure(fg_color="orange", hover_color="darkorange")
            return

        if not os.path.exists(minecraft_path):
            messagebox.showerror("Ошибка", f"Папка Minecraft не найдена: {minecraft_path}")
            self.settings_btn.configure(fg_color="orange", hover_color="darkorange")
            return

        if not os.path.isdir(minecraft_path):
            messagebox.showerror("Ошибка", f"Указанный путь не является папкой: {minecraft_path}")
            self.settings_btn.configure(fg_color="orange", hover_color="darkorange")
            return

        # TLauncher проверяем только если указан
        if tlauncher_path and not os.path.exists(tlauncher_path):
            messagebox.showerror("Ошибка", f"TLauncher не найден: {tlauncher_path}")
            return

        # Автоматическое определение пути к модам на основе папки Minecraft
        mods_path = os.path.join(minecraft_path, "mods")
        os.makedirs(mods_path, exist_ok=True)

        # Сохранение путей
        self.minecraft_path.set(minecraft_path)
        self.tlauncher_path.set(tlauncher_path)  # Может быть пустым
        self.mods_path.set(mods_path)

        self.save_config()
        self.update_path_info()
        self.settings_btn.configure(fg_color="#1f6aa5", hover_color="#144870")

        window.destroy()
        self.log_success("Настройки обновлены успешно!")

        if tlauncher_path:
            messagebox.showinfo("Успех", "Настройки сохранены!\nБудет использоваться TLauncher для запуска.")
        else:
            messagebox.showinfo("Успех", "Настройки сохранены!\nИгра будет запускаться из указанной папки.")

    def browse_minecraft_folder(self, entry_widget):
        """Выбор папки Minecraft"""
        folder = filedialog.askdirectory(
            title="Выберите папку Minecraft",
            initialdir=os.path.expanduser("~")
        )
        if folder:
            # Проверяем, что это действительно папка Minecraft
            if self.validate_minecraft_folder(folder):
                entry_widget.delete(0, "end")
                entry_widget.insert(0, folder)
            else:
                # Предлагаем создать папку .minecraft или выбрать другую
                result = messagebox.askyesno(
                    "Папка Minecraft не найдена",
                    f"В папке {folder} не найдены файлы Minecraft.\n\n"
                    "Это может быть:\n"
                    "• Неправильная папка\n"
                    "• Новая установка без профилей\n\n"
                    "Использовать эту папку как папку Minecraft?",
                    icon="question"
                )
                if result:
                    entry_widget.delete(0, "end")
                    entry_widget.insert(0, folder)

    def validate_minecraft_folder(self, folder_path):
        """Проверка, что папка содержит файлы Minecraft"""
        if not os.path.exists(folder_path):
            return False

        # Проверяем наличие характерных файлов/папок Minecraft
        minecraft_indicators = [
            "launcher_profiles.json",  # Профили лаунчера
            "versions",  # Папка с версиями
            "libraries",  # Библиотеки
            "assets",  # Ресурсы
            "mods"  # Папка модов (может отсутствовать)
        ]

        # Достаточно найти хотя бы один индикатор
        for indicator in minecraft_indicators:
            if os.path.exists(os.path.join(folder_path, indicator)):
                return True

        return False

    def browse_folder(self, entry_widget, title):
        """Выбор папки"""
        folder = filedialog.askdirectory(title=title)
        if folder:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, folder)

    def browse_file(self, entry_widget, title, filetypes):
        """Выбор файла"""
        file = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if file:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, file)

    def update_status(self, text):
        """Обновление статуса"""
        self.status_label.configure(text=text)
        self.root.update()

    def validate_paths(self):
        """Проверка корректности путей"""
        if not self.all_paths_configured():
            result = messagebox.askyesno(
                "Настройка путей",
                "Папка Minecraft не настроена.\nОткрыть настройки сейчас?",
                icon="question"
            )
            if result:
                self.show_settings()
            return False
        return True

    def update_progress(self, progress):
        """Обновляет прогресс-бар на progress процентов (0-100)"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set(progress / 100.0)

    def check_updates(self):
        """Проверка обновлений модов"""
        if not self.all_paths_configured():
            self.log_error("Не настроены пути к файлам. Откройте настройки.")
            return

        self.log_info("Начинаю проверку обновлений модов...")
        self.update_status("Проверка обновлений...")
        self.check_btn.configure(state="disabled")

        def check_thread():
            try:
                # === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (перенесены из update.py) ===

                def get_file_hash(filepath):
                    """Вычисление SHA256 хэша файла"""
                    h = hashlib.sha256()
                    with open(filepath, 'rb') as file_obj:
                        while True:
                            chunk = file_obj.read(65536)
                            if not chunk:
                                break
                            h.update(chunk)
                    return h.hexdigest()

                def download_file(url, dest_path):
                    """Скачивание файла с логированием в GUI"""
                    self.root.after(0, lambda: self.log_info(f"→ Скачиваю {os.path.basename(dest_path)}..."))
                    response = requests.get(url, stream=True)
                    response.raise_for_status()
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, 'wb') as file_out:
                        for chunk in response.iter_content(chunk_size=65536):
                            if chunk:
                                file_out.write(chunk)
                    self.root.after(0, lambda: self.log_info(f"→ {os.path.basename(dest_path)} скачан."))

                def get_remote_size(head_url):
                    """Получение размера файла по URL"""
                    try:
                        response = requests.head(head_url, allow_redirects=True, timeout=10)
                        return int(response.headers.get('content-length', 0))
                    except Exception:
                        return 0

                # === КОНСТАНТЫ И ПЕРЕМЕННЫЕ ===
                REPO = 'Alexandr153/mincraft-mods'
                TAG = 'latest'
                LOCAL_MODS = self.mods_path.get()  # Используем путь из GUI
                MODLIST_URL = f'https://github.com/{REPO}/releases/download/{TAG}/modlist.txt'
                LOCAL_MODLIST = os.path.join(LOCAL_MODS, 'modlist.txt')
                TO_UPDATE_PATH = Path(__file__).parent / 'mods_to_update.json'

                # === ОСНОВНАЯ ЛОГИКА ПРОВЕРКИ ОБНОВЛЕНИЙ ===

                # 1. Скачиваем modlist.txt
                os.makedirs(LOCAL_MODS, exist_ok=True)
                self.root.after(0, lambda: self.log_info('Скачиваю modlist.txt...'))
                download_file(MODLIST_URL, LOCAL_MODLIST)
                self.root.after(0, lambda: self.log_info('modlist.txt скачан.'))

                # 2. Проверяем какие моды надо обновить
                self.root.after(0, lambda: self.log_info("Проверяю актуальность модов..."))
                mods_info = []

                with open(LOCAL_MODLIST, 'r', encoding='utf-8') as modlist_file:
                    for modlist_line in modlist_file:
                        parts = modlist_line.strip().split()
                        if len(parts) < 3:
                            continue
                        mod_name, remote_hash, mod_url = parts
                        local_mod_path = os.path.join(LOCAL_MODS, mod_name)
                        mods_info.append((mod_name, remote_hash, mod_url, local_mod_path))

                # 3. Параллельно считаем хэши локальных файлов
                def check_mod_hash(mod_tuple):
                    mod_name, remote_hash, mod_url, local_mod_path = mod_tuple
                    if os.path.exists(local_mod_path):
                        local_hash = get_file_hash(local_mod_path)
                    else:
                        local_hash = None
                    return mod_name, remote_hash, mod_url, local_mod_path, local_hash

                with ThreadPoolExecutor(max_workers=8) as hash_executor:
                    hash_results = []
                    total_mods = len(mods_info)
                    completed = 0

                    futures = [hash_executor.submit(check_mod_hash, mod_info) for mod_info in mods_info]
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            hash_results.append(result)
                            completed += 1
                            progress = int((completed / total_mods) * 50)  # 50% для проверки хэшей
                            self.root.after(0, lambda p=progress: self.update_progress(p))
                        except Exception as e:
                            self.root.after(0, lambda err=str(e): self.log_error(f"Ошибка при проверке хэша: {err}"))

                # 4. Получаем размеры для модов, требующих обновления
                mods_to_update = []
                total_bytes = 0

                def get_mod_size_for_update(mod_with_hash):
                    mod_name, remote_hash, mod_url, local_mod_path, local_hash = mod_with_hash
                    if local_hash != remote_hash:
                        mod_size = get_remote_size(mod_url)
                        return mod_name, mod_url, local_mod_path, mod_size
                    else:
                        self.root.after(0, lambda name=mod_name: self.log_info(f"→ {name}: актуален."))
                        return None

                with ThreadPoolExecutor(max_workers=8) as size_executor:
                    size_futures = [size_executor.submit(get_mod_size_for_update, hash_result) for hash_result in
                                    hash_results]
                    completed_size = 0

                    for future in as_completed(size_futures):
                        try:
                            mod_update_info = future.result()
                            if mod_update_info:
                                upd_name, upd_url, upd_path, upd_size = mod_update_info
                                mods_to_update.append({
                                    'name': upd_name,
                                    'url': upd_url,
                                    'path': upd_path,
                                    'size': upd_size
                                })
                                total_bytes += upd_size
                                self.root.after(0,
                                                lambda name=upd_name: self.log_info(f"→ {name}: требуется обновление."))

                            completed_size += 1
                            progress = 50 + int((completed_size / len(hash_results)) * 50)  # 50-100% для размеров
                            self.root.after(0, lambda p=progress: self.update_progress(p))
                        except Exception as e:
                            self.root.after(0,
                                            lambda err=str(e): self.log_error(f"Ошибка при получении размера: {err}"))

                # 5. Сохраняем список на обновление
                with open(TO_UPDATE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(mods_to_update, f, ensure_ascii=False, indent=2)

                # 6. Выводим результаты
                self.root.after(0, lambda: self.log_info(
                    f"Проверка завершена. Модов для обновления: {len(mods_to_update)}"))

                if mods_to_update:
                    self.root.after(0, lambda: self.log_info("Доступны для обновления:"))
                    for mod in mods_to_update:
                        self.root.after(0, lambda name=mod['name']: self.log_info(f"  - {name}"))
                else:
                    self.root.after(0, lambda: self.log_info("Все моды актуальны."))

                # Завершение проверки
                self.root.after(0, lambda: self.on_check_complete())

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.on_check_error(err))

        threading.Thread(target=check_thread, daemon=True).start()

    def on_check_complete(self):
        """Завершение проверки обновлений"""
        self.log_success("Проверка обновлений завершена")
        self.update_status("Проверка завершена")
        self.check_btn.configure(state="normal")

        # Устанавливаем флаг выполненной проверки
        self.check_performed = True

        # ИСПРАВЛЕНО: Загружаем статус модов напрямую из файла
        self.load_mods_status_from_file()

        if self.mods_need_update:
            self.update_btn.configure(state="normal")
            self.log_warning(f"Найдено {len(self.outdated_mods)} мод(ов) для обновления")
        else:
            self.update_btn.configure(state="disabled")
            self.log_success("Все моды актуальны! Можно запускать игру.")

    def load_mods_status_from_file(self):
        """Загрузка статуса модов из JSON файла (только после проверки)"""
        if self.update_status_path.exists():
            try:
                with open(self.update_status_path, 'r', encoding='utf-8') as f:
                    mods_to_update = json.load(f)
                    self.outdated_mods = mods_to_update
                    self.mods_need_update = len(mods_to_update) > 0

                    # Активируем кнопку обновления если есть моды для обновления
                    if self.mods_need_update:
                        self.update_btn.configure(state="normal")
                    else:
                        self.update_btn.configure(state="disabled")

                    self.update_mod_status_display()
                    self.update_mods_list()
                    self.log_info("Статус модов обновлен после проверки")
            except Exception as e:
                self.log_error(f"Ошибка чтения статуса модов: {e}")
                self.reset_mod_status()
        else:
            # Если файл не создался - значит все моды актуальны
            self.mods_need_update = False
            self.outdated_mods = []
            self.update_mod_status_display()
            self.update_mods_list()
            self.log_success("Все моды актуальны!")

    def on_check_error(self, error):
        """Ошибка при проверке"""
        self.log_error(f"Ошибка при проверке: {error}")
        self.update_status("Ошибка проверки")
        self.check_btn.configure(state="normal")

    def update_mods(self):
        """Обновление модов"""
        if not self.validate_paths():
            return

        self.log_info("Начинаю обновление модов...")
        self.update_status("Обновление модов...")
        self.update_btn.configure(state="disabled")

        # Показ простого прогресс-бара
        progress_window = self.show_progress("Обновление модов...")

        def update_thread():
            try:
                subprocess.run([sys.executable, "update.py", "update"],
                               cwd=Path(__file__).parent, check=True)
                self.root.after(0, lambda: self.on_update_complete(progress_window))
            except subprocess.CalledProcessError as e:
                self.root.after(0, lambda: self.on_update_error(str(e), progress_window))

        threading.Thread(target=update_thread, daemon=True).start()

    def on_update_complete(self, progress_window):
        """Завершение обновления"""
        progress_window.destroy()
        self.log_success("Моды успешно обновлены!")
        self.update_status("Обновление завершено")
        self.update_btn.configure(state="disabled")  # Отключаем кнопку после обновления

        # Очищаем список модов для обновления
        self.mods_need_update = False
        self.outdated_mods = []
        self.update_mod_status_display()
        self.update_mods_list()

        # Удаляем файл с модами для обновления
        if self.update_status_path.exists():
            self.update_status_path.unlink()

    def format_file_size(self, size_bytes):
        """Форматирование размера файла в читаемый вид"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def on_update_error(self, error, progress_window):
        """Ошибка при обновлении"""
        progress_window.destroy()
        self.log_error(f"Ошибка при обновлении: {error}")
        self.update_status("Ошибка обновления")
        self.update_btn.configure(state="normal")

    def show_progress(self, title):
        """Показ окна прогресса"""
        progress_window = ctk.CTkToplevel(self.root)
        progress_window.title(title)
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()

        label = ctk.CTkLabel(progress_window, text=title, font=ctk.CTkFont(size=14))
        label.pack(pady=20)

        progress = ctk.CTkProgressBar(progress_window, mode="indeterminate")
        progress.pack(pady=20, padx=40, fill="x")
        progress.start()

        return progress_window

    def launch_minecraft(self):
        """Запуск Minecraft через TLauncher"""
        if not self.validate_paths():
            return

        # Проверка состояния модов с предупреждениями
        if self.mods_need_update is None or not self.check_performed:
            result = messagebox.askyesno(
                "Проверка модов не выполнена",
                "Проверка модов не проводилась.\n\n"
                "Рекомендуется проверить актуальность модов перед запуском игры.\n\n"
                "Запустить игру без проверки?",
                icon="warning"
            )
            if not result:
                self.log_info("💡 Запуск отменен. Выполните проверку модов.")
                return
            else:
                self.log_warning("⚠️ Запуск игры без проверки модов")

        elif self.mods_need_update:
            result = messagebox.askyesno(
                "Моды требуют обновления",
                f"Найдено {len(self.outdated_mods)} устаревших мод(ов).\n\n"
                "Рекомендуется обновить моды перед запуском игры.\n\n"
                "Запустить игру с устаревшими модами?",
                icon="warning"
            )
            if not result:
                self.log_info("💡 Запуск отменен. Обновите моды.")
                return
            else:
                self.log_warning("⚠️ Запуск игры с устаревшими модами")
        else:
            self.log_info("✅ Все моды актуальны. Запускаю игру...")

            # Определяем способ запуска
            minecraft_folder = self.minecraft_path.get()
            tlauncher_path = self.tlauncher_path.get()

            try:
                if tlauncher_path and os.path.exists(tlauncher_path):
                    # Запуск через TLauncher
                    self.update_status("Запуск TLauncher...")
                    self.log_info("🚀 Запускаю игру через TLauncher...")

                    import runner
                    success = runner.launch_tlauncher()

                    if success:
                        self.log_success("✅ TLauncher запущен успешно")
                        self.update_status("TLauncher запущен")
                    else:
                        self.log_error("❌ Ошибка запуска TLauncher")
                        self.update_status("Ошибка запуска")
                else:
                    # Запуск стандартного лаунчера из папки Minecraft
                    self.update_status("Запуск Minecraft Launcher...")
                    self.log_info("🚀 Запускаю стандартный лаунчер...")

                    # Ищем лаунчер в папке Minecraft
                    launcher_paths = self.find_minecraft_launcher(minecraft_folder)

                    if launcher_paths:
                        launcher_path = launcher_paths[0]  # Берем первый найденный
                        self.log_info(f"Найден лаунчер: {os.path.basename(launcher_path)}")

                        if sys.platform == "win32":
                            subprocess.Popen([launcher_path], cwd=minecraft_folder)
                        elif sys.platform == "darwin":  # macOS
                            if launcher_path.endswith('.app'):
                                subprocess.Popen(['open', launcher_path])
                            else:
                                subprocess.Popen(['java', '-jar', launcher_path], cwd=minecraft_folder)
                        else:  # Linux
                            subprocess.Popen(['java', '-jar', launcher_path], cwd=minecraft_folder)

                        self.log_success("✅ Minecraft Launcher запущен успешно")
                        self.update_status("Minecraft Launcher запущен")
                    else:
                        # Пытаемся запустить через команду minecraft (если установлен глобально)
                        self.log_warning("Лаунчер не найден в папке, пытаюсь запустить minecraft...")
                        try:
                            subprocess.Popen(['minecraft-launcher'], cwd=minecraft_folder)
                            self.log_success("✅ Minecraft запущен через системную команду")
                        except FileNotFoundError:
                            self.log_error("❌ Не найден способ запуска Minecraft из указанной папки")
                            messagebox.showerror(
                                "Ошибка запуска",
                                "Не удалось найти лаунчер Minecraft в указанной папке.\n\n"
                                "Убедитесь, что:\n"
                                "• Указана правильная папка Minecraft\n"
                                "• В папке есть исполняемые файлы лаунчера\n"
                                "• Или используйте TLauncher для запуска"
                            )

            except Exception as e:
                self.log_error(f"❌ Ошибка запуска: {e}")
                self.update_status("Ошибка запуска")

    def find_minecraft_launcher(self, minecraft_folder):
        """Поиск исполняемых файлов лаунчера в папке Minecraft"""
        launcher_files = []

        # Возможные имена лаунчеров
        launcher_names = [
            "MinecraftLauncher.exe",
            "Minecraft.exe",
            "launcher.exe",
            "minecraft-launcher.exe",
            "Minecraft Launcher.app",
            "launcher.jar",
            "minecraft.jar"
        ]

        # Ищем в основной папке
        for launcher_name in launcher_names:
            launcher_path = os.path.join(minecraft_folder, launcher_name)
            if os.path.exists(launcher_path):
                launcher_files.append(launcher_path)

        # Ищем в подпапках (особенно для Windows)
        for root, dirs, files in os.walk(minecraft_folder):
            # Ограничиваем глубину поиска
            if root.count(os.sep) - minecraft_folder.count(os.sep) > 2:
                continue

            for file in files:
                if file.lower() in [name.lower() for name in launcher_names]:
                    launcher_files.append(os.path.join(root, file))

        return launcher_files

    def toggle_theme(self):
        """Переключение темы с обновлением иконки"""
        if self.theme_var.get() == "dark":
            ctk.set_appearance_mode("dark")
            self.current_theme = "dark"
            self.theme_icon.configure(text="🌙")  # Луна для темной темы
            self.log_info("🌙 Переключено на тёмную тему")
        else:
            ctk.set_appearance_mode("light")
            self.current_theme = "light"
            self.theme_icon.configure(text="☀️")  # Солнце для светлой темы
            self.log_info("🌞 Переключено на светлую тему")

    def start_server_monitoring(self):
        """Запуск мониторинга сервера"""
        self.check_server_running = True
        self.check_server_status()

    def stop_server_monitoring(self):
        """Остановка мониторинга сервера"""
        self.check_server_running = False

    def setup_log_context_menu(self):
        """Настройка контекстного меню для логов"""
        self.context_menu = tk.Menu(self.root, tearoff=0)

        # Основные действия
        self.context_menu.add_command(
            label="📋 Копировать все",
            command=self.copy_all_logs,
            accelerator="Ctrl+A, Ctrl+C"
        )
        self.context_menu.add_command(
            label="📂 Копировать выделенное",
            command=self.copy_selected_logs
        )

        self.context_menu.add_separator()

        # Сохранение
        self.context_menu.add_command(
            label="💾 Сохранить в файл",
            command=self.save_logs_to_file,
            accelerator="Ctrl+S"
        )
        self.context_menu.add_command(
            label="📤 Экспорт с фильтром",
            command=self.export_filtered_logs
        )

        self.context_menu.add_separator()

        # Управление логами
        self.context_menu.add_command(
            label="🔍 Найти в логах",
            command=self.search_in_logs,
            accelerator="Ctrl+F"
        )
        self.context_menu.add_command(
            label="🗑️ Очистить логи",
            command=self.clear_logs_with_confirmation,
            accelerator="Ctrl+L"
        )

        self.context_menu.add_separator()

        # Дополнительные опции
        self.context_menu.add_command(
            label="📊 Статистика логов",
            command=self.show_log_statistics
        )

        def show_context_menu(event):
            try:
                # Определяем, есть ли выделенный текст
                try:
                    selection = self.log_text.selection_get()
                    has_selection = bool(selection)
                except tk.TclError:
                    has_selection = False

                # Активируем/деактивируем пункты меню в зависимости от контекста
                if has_selection:
                    self.context_menu.entryconfig("📂 Копировать выделенное", state="normal")
                else:
                    self.context_menu.entryconfig("📂 Копировать выделенное", state="disabled")

                # Показываем меню
                self.context_menu.tk_popup(event.x_root, event.y_root)
            except Exception as e:
                print(f"Ошибка контекстного меню: {e}")
            finally:
                self.context_menu.grab_release()

        # Привязываем контекстное меню
        self.log_text.bind("<Button-3>", show_context_menu)  # Правая кнопка мыши
        self.log_text.bind("<Control-Button-1>", show_context_menu)  # Ctrl+ЛКМ для macOS

    def copy_selected_logs(self):
        """Копирование выделенного текста логов"""
        try:
            selected_text = self.log_text.selection_get()
            if selected_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
                lines_count = len(selected_text.splitlines())
                self.log_info(f"📋 Скопировано {lines_count} строк выделенного текста")
            else:
                messagebox.showinfo("Информация", "Нет выделенного текста для копирования")
        except tk.TclError:
            messagebox.showinfo("Информация", "Нет выделенного текста для копирования")
        except Exception as e:
            self.log_error(f"Ошибка копирования выделенного: {e}")

    def export_filtered_logs(self):
        """Экспорт логов с возможностью фильтрации"""
        filter_window = ctk.CTkToplevel(self.root)
        filter_window.title("Экспорт логов с фильтром")
        filter_window.geometry("400x300")
        filter_window.transient(self.root)
        filter_window.grab_set()

        # Заголовок
        title_label = ctk.CTkLabel(
            filter_window,
            text="Экспорт логов с фильтром",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=10)

        # Фильтры
        filter_frame = ctk.CTkFrame(filter_window)
        filter_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Тип сообщений
        ctk.CTkLabel(filter_frame, text="Тип сообщений:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10,
                                                                                                pady=5)

        self.filter_info = tk.BooleanVar(value=True)
        self.filter_success = tk.BooleanVar(value=True)
        self.filter_warning = tk.BooleanVar(value=True)
        self.filter_error = tk.BooleanVar(value=True)

        ctk.CTkCheckBox(filter_frame, text="ℹ️ Информация", variable=self.filter_info).pack(anchor="w", padx=20)
        ctk.CTkCheckBox(filter_frame, text="✅ Успех", variable=self.filter_success).pack(anchor="w", padx=20)
        ctk.CTkCheckBox(filter_frame, text="⚠️ Предупреждения", variable=self.filter_warning).pack(anchor="w", padx=20)
        ctk.CTkCheckBox(filter_frame, text="❌ Ошибки", variable=self.filter_error).pack(anchor="w", padx=20)

        # Поиск по ключевому слову
        ctk.CTkLabel(filter_frame, text="Фильтр по ключевому слову:", font=ctk.CTkFont(weight="bold")).pack(anchor="w",
                                                                                                            padx=10,
                                                                                                            pady=(
                                                                                                                10, 5))
        self.keyword_entry = ctk.CTkEntry(filter_frame, placeholder_text="Введите ключевое слово...")
        self.keyword_entry.pack(anchor="w", padx=20, pady=5, fill="x")

        # Кнопки
        buttons_frame = ctk.CTkFrame(filter_window)
        buttons_frame.pack(pady=10, fill="x")

        ctk.CTkButton(
            buttons_frame,
            text="Отмена",
            command=filter_window.destroy,
            fg_color="gray"
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            buttons_frame,
            text="💾 Экспортировать",
            command=lambda: self.apply_filter_and_export(filter_window),
            fg_color="green"
        ).pack(side="right", padx=20)

    def apply_filter_and_export(self, filter_window):
        """Применение фильтра и экспорт логов"""
        log_content = self.log_text.get("1.0", "end-1c")
        lines = log_content.splitlines()

        filtered_lines = []
        keyword = self.keyword_entry.get().lower()

        for line in lines:
            # Фильтр по типу сообщений
            if ("ℹ️" in line and not self.filter_info.get()) or \
                    ("✅" in line and not self.filter_success.get()) or \
                    ("⚠️" in line and not self.filter_warning.get()) or \
                    ("❌" in line and not self.filter_error.get()):
                continue

            # Фильтр по ключевому слову
            if keyword and keyword not in line.lower():
                continue

            filtered_lines.append(line)

        if not filtered_lines:
            messagebox.showinfo("Информация", "Нет логов, соответствующих фильтру")
            return

        # Сохранение отфильтрованных логов
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"filtered_logs_{timestamp}.txt"

        file_path = filedialog.asksaveasfilename(
            title="Сохранить отфильтрованные логи",
            defaultextension=".txt",
            initialfile=default_filename,
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(filtered_lines))
                filter_window.destroy()
                self.log_info(f"📁 Отфильтрованные логи сохранены: {os.path.basename(file_path)}")
                messagebox.showinfo("Успех", f"Сохранено {len(filtered_lines)} строк логов")
            except Exception as e:
                self.log_error(f"Ошибка сохранения: {e}")

    def search_in_logs(self):
        """Поиск текста в логах"""
        search_window = ctk.CTkToplevel(self.root)
        search_window.title("Поиск в логах")
        search_window.geometry("200")
        search_window.transient(self.root)

        ctk.CTkLabel(search_window, text="Поиск в логах", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        search_frame = ctk.CTkFrame(search_window)
        search_frame.pack(pady=10, padx=20, fill="x")

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Введите текст для поиска...")
        self.search_entry.pack(pady=10, padx=10, fill="x")

        buttons_frame = ctk.CTkFrame(search_window)
        buttons_frame.pack(pady=10, fill="x")

        ctk.CTkButton(buttons_frame, text="Найти", command=lambda: self.perform_search(search_window)).pack(
            side="right", padx=20)
        ctk.CTkButton(buttons_frame, text="Отмена", command=search_window.destroy, fg_color="gray").pack(side="left",
                                                                                                         padx=20)

    def perform_search(self, search_window):
        """Выполнение поиска в логах"""
        search_text = self.search_entry.get().strip()
        if not search_text:
            return

        log_content = self.log_text.get("1.0", "end")

        # Удаляем предыдущие выделения
        self.log_text.tag_remove("search", "1.0", "end")

        # Поиск всех вхождений
        start = "1.0"
        matches = 0

        while True:
            pos = self.log_text.search(search_text, start, "end", nocase=True)
            if not pos:
                break

            end_pos = f"{pos}+{len(search_text)}c"
            self.log_text.tag_add("search", pos, end_pos)
            matches += 1
            start = end_pos

        # Настройка стиля выделения
        self.log_text.tag_config("search", background="yellow", foreground="black")

        search_window.destroy()

        if matches > 0:
            self.log_info(f"🔍 Найдено {matches} вхождений '{search_text}'")
            # Прокручиваем к первому найденному
            first_match = self.log_text.tag_ranges("search")
            if first_match:
                self.log_text.see(first_match[0])
        else:
            messagebox.showinfo("Поиск", f"Текст '{search_text}' не найден в логах")

    def show_log_statistics(self):
        """Показ статистики логов"""
        log_content = self.log_text.get("1.0", "end-1c")
        lines = log_content.splitlines()

        # Подсчет статистики
        total_lines = len(lines)
        info_count = sum(1 for line in lines if "ℹ️" in line)
        success_count = sum(1 for line in lines if "✅" in line)
        warning_count = sum(1 for line in lines if "⚠️" in line)
        error_count = sum(1 for line in lines if "❌" in line)

        # Окно статистики
        stats_window = ctk.CTkToplevel(self.root)
        stats_window.title("Статистика логов")
        stats_window.geometry("350x400")
        stats_window.transient(self.root)

        ctk.CTkLabel(stats_window, text="📊 Статистика логов", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)

        stats_frame = ctk.CTkFrame(stats_window)
        stats_frame.pack(pady=10, padx=20, fill="both", expand=True)

        stats_text = f"""
    📝 Всего строк: {total_lines}

    📊 По типам сообщений:
    ℹ️  Информационные: {info_count}
    ✅ Успешные: {success_count}
    ⚠️  Предупреждения: {warning_count}
    ❌ Ошибки: {error_count}

    📈 Процентное соотношение:
    ℹ️  {(info_count / total_lines * 100):.1f}% информационных
    ✅ {(success_count / total_lines * 100):.1f}% успешных
    ⚠️  {(warning_count / total_lines * 100):.1f}% предупреждений
    ❌ {(error_count / total_lines * 100):.1f}% ошибок
    """

        stats_label = ctk.CTkLabel(stats_frame, text=stats_text, font=ctk.CTkFont(size=12), justify="left")
        stats_label.pack(pady=20, padx=20)

        ctk.CTkButton(stats_window, text="Закрыть", command=stats_window.destroy).pack(pady=10)

    def clear_logs_with_confirmation(self):
        """Очистка логов с подтверждением и возможностью сохранения"""
        log_content = self.log_text.get("1.0", "end-1c")
        if not log_content.strip():
            messagebox.showinfo("Информация", "Логи уже пусты")
            return

        result = messagebox.askyesnocancel(
            "Очистка логов",
            "Очистить все логи?\n\n"
            "Да - Очистить без сохранения\n"
            "Нет - Сохранить и очистить\n"
            "Отмена - Не очищать",
            icon="question"
        )

        if result is None:  # Отмена
            return
        elif result is False:  # Сохранить и очистить
            self.save_logs_to_file()

        # Очищаем логи
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.log_info("🗑️ Логи очищены")

    def save_logs_to_file(self):
        """Сохранение логов в файл"""
        log_content = self.log_text.get("1.0", "end-1c")
        if not log_content.strip():
            messagebox.showinfo("Информация", "Логи пусты, нечего сохранять.")
            return

        # Создаем папку для логов
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)

        # Генерируем имя файла с текущей датой и временем
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"launcher_log_{timestamp}.txt"

        # Диалог сохранения файла
        file_path = filedialog.asksaveasfilename(
            title="Сохранить логи",
            defaultextension=".txt",
            initialfile=default_filename,
            filetypes=[
                ("Текстовые файлы", "*.txt"),
                ("Все файлы", "*.*")
            ]
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.log_info(f"📁 Логи сохранены в файл: {os.path.basename(file_path)}")
                messagebox.showinfo("Успех", f"Логи успешно сохранены в:\n{file_path}")
            except Exception as e:
                self.log_error(f"Ошибка сохранения логов: {e}")
                messagebox.showerror("Ошибка", f"Не удалось сохранить логи:\n{e}")

    def copy_all_logs(self):
        """Копирование всех логов в буфер обмена"""
        log_content = self.log_text.get("1.0", "end-1c")
        if not log_content.strip():
            messagebox.showinfo("Информация", "Логи пусты, нечего копировать.")
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(log_content)
            self.log_info("📋 Логи скопированы в буфер обмена")

            # Показываем количество скопированных строк
            lines_count = len(log_content.splitlines())
            messagebox.showinfo("Копирование", f"Скопировано {lines_count} строк логов в буфер обмена")
        except Exception as e:
            self.log_error(f"Ошибка копирования: {e}")
            messagebox.showerror("Ошибка", f"Не удалось скопировать логи:\n{e}")

    def check_server_status(self):
        """Проверка статуса сервера"""
        if not self.check_server_running:
            return

        def check_thread():
            try:
                # Используем фиксированный адрес
                server = JavaServer.lookup(self.server_address)
                status = server.status()

                # Обновляем статус в главном потоке
                status_text = f"✅ Онлайн: {status.players.online}/{status.players.max}"
                self.root.after(0, lambda: self.update_server_status(status_text, "green"))

            except Exception:
                error_text = "❌ Сервер недоступен"
                self.root.after(0, lambda: self.update_server_status(error_text, "red"))

        # Запускаем проверку в отдельном потоке
        threading.Thread(target=check_thread, daemon=True).start()

        # Планируем следующую проверку через 30 секунд
        if self.check_server_running:
            self.root.after(30000, self.check_server_status)

    def manual_check_server(self):
        """Ручная проверка сервера"""
        self.log_info(f"🔄 Проверяю статус сервера {self.server_name}...")
        self.server_status_label.configure(text="🔄 Проверка...", text_color="orange")

        def check_thread():
            try:
                server = JavaServer.lookup(self.server_address)
                status = server.status()
                latency = server.ping()

                status_text = f"✅ Онлайн: {status.players.online}/{status.players.max} (пинг: {latency:.0f}ms)"
                self.root.after(0, lambda: self.update_server_status(status_text, "green"))
                self.root.after(0, lambda: self.log_success(
                    f"Сервер {self.server_name} онлайн. Игроков: {status.players.online}/{status.players.max}"))

            except Exception as e:
                error_text = "❌ Сервер недоступен"
                self.root.after(0, lambda: self.update_server_status(error_text, "red"))
                self.root.after(0, lambda: self.log_error(
                    f"Не удалось подключиться к серверу {self.server_name}: {str(e)}"))

        threading.Thread(target=check_thread, daemon=True).start()

    def update_server_status(self, status_text, color):
        """Обновление отображения статуса сервера"""
        self.server_status = status_text
        self.server_status_label.configure(text=status_text, text_color=color)

    def run(self):
        """Запуск приложения"""
        try:
            self.root.mainloop()
        finally:
            # Останавливаем мониторинг при закрытии
            self.stop_server_monitoring()


if __name__ == "__main__":
    try:
        import customtkinter
    except ImportError:
        print("Устанавливаю CustomTkinter...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
        import customtkinter

    # Запуск лаунчера
    launcher = MinecraftLauncher()
    launcher.run()
