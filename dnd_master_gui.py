#!/usr/bin/env python3
"""
GUI приложение для D&D мастера с использованием OpenAI API
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from dotenv import load_dotenv
from openai import OpenAI
import threading
import random
import yaml
import re
from dice_system import dice_roller

# Загружаем переменные окружения
load_dotenv()

class DnDMasterGUI:
    def __init__(self):
        """Инициализация GUI приложения"""
        self.root = tk.Tk()
        self.root.title("🎲 D&D Master AI")

        # Цветовая палитра и шрифты вдохновлены атмосферой настольного D&D
        self.theme = {
            "bg_dark": "#1b1410",
            "bg_panel": "#241a16",
            "bg_card": "#f7f0d6",
            "bg_input": "#f2e8cf",
            "accent": "#c08429",
            "accent_light": "#e7c46b",
            "accent_muted": "#9c6b30",
            "button_primary": "#7b3f00",
            "button_secondary": "#5b2d10",
            "button_danger": "#7d1f1a",
            "button_text": "#f8efdb",
            "text_light": "#f5e9cf",
            "text_dark": "#2d1b10",
            "text_muted": "#d2b792",
            "dice_highlight": "#3f6e88"
        }
        self.fonts = {
            "title": ("Georgia", 20, "bold"),
            "subtitle": ("Georgia", 12, "bold"),
            "text": ("Georgia", 11),
            "button": ("Georgia", 11, "bold")
        }

        self.configure_theme()
        
        # Проверяем API ключ
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            messagebox.showerror("Ошибка", 
                               "Не найден OPENAI_API_KEY в переменных окружения!\n"
                               "Создайте файл .env и добавьте туда ваш API ключ:\n"
                               "OPENAI_API_KEY=your_key_here")
            sys.exit(1)
        
        self.client = OpenAI(api_key=self.api_key)
        self.conversation_history = []
        self.world_bible = None
        self.game_rules = None
        self.story_arc = None
        self.story_file = "story_arc.md"
        self.session_mode = "new"
        self.story_status_message = ""
        self.last_error_message = ""
        self.models = {
            "world": os.getenv("DND_WORLD_MODEL", "gpt-4o-mini"),
            "story": os.getenv("DND_STORY_MODEL", "gpt-4o-mini"),
            "master": os.getenv("DND_MASTER_MODEL", "gpt-4o-mini"),
        }
        
        # Загружаем правила игры
        self.load_game_rules()
        
        # Инициализируем Библию мира
        self.initialize_world_bible()

        # Инициализируем сюжет приключения
        self.initialize_story_arc()
        
        # Системный промпт для D&D мастера
        self.update_system_prompt()
        
        self.setup_ui()

    def configure_theme(self):
        """Настраивает базовое оформление окна."""
        self.root.geometry("900x800")
        self.root.configure(bg=self.theme["bg_dark"])
        self.root.option_add("*Font", self.fonts["text"])
        self.root.option_add("*Foreground", self.theme["text_light"])
        self.root.option_add("*Background", self.theme["bg_dark"])
    
    def load_game_rules(self):
        """Загружает правила игры из rules.yaml"""
        try:
            with open('rules.yaml', 'r', encoding='utf-8') as f:
                self.game_rules = yaml.safe_load(f)
            print("📋 Правила игры загружены")
        except Exception as e:
            print(f"❌ Ошибка при загрузке правил: {e}")
            self.game_rules = {}
    
    def initialize_world_bible(self):
        """Инициализация или загрузка Библии мира"""
        bible_file = "world_bible.md"
        
        if os.path.exists(bible_file):
            # Загружаем существующую Библию мира
            try:
                with open(bible_file, 'r', encoding='utf-8') as f:
                    self.world_bible = f.read()
                print("📖 Загружена существующая Библия мира")
            except Exception as e:
                print(f"❌ Ошибка при загрузке Библии мира: {e}")
                self.generate_world_bible()
        else:
            # Генерируем новую Библию мира
            print("🌍 Генерируется новая Библия мира...")
            self.generate_world_bible()
    
    def generate_world_bible(self):
        """Генерирует новую Библию мира"""
        try:
            # Случайные элементы для генерации уникального мира
            settings = [
                "Фэнтези с элементами стимпанка",
                "Темное фэнтези с готическими элементами", 
                "Киберпанк с магией",
                "Постапокалиптическое фэнтези",
                "Средневековое фэнтези с политическими интригами",
                "Магический реализм в современном мире",
                "Сказочное фэнтези с элементами хоррора"
            ]
            
            tones = [
                "мрачный и атмосферный",
                "героический и вдохновляющий", 
                "загадочный и мистический",
                "эпический и драматический",
                "интригующий и политический",
                "темный и напряженный",
                "романтичный и приключенческий"
            ]
            
            genres = [
                "приключения с элементами хоррора",
                "политические интриги с магией",
                "исследования древних руин",
                "война между фракциями",
                "мистические расследования",
                "путешествия между мирами",
                "выживание в опасных землях"
            ]
            
            selected_setting = random.choice(settings)
            selected_tone = random.choice(tones)
            selected_genre = random.choice(genres)
            
            world_prompt = f"""Создай подробную Библию мира для D&D кампании в следующем формате:

# БИБЛИЯ МИРА

## СЕТТИНГ
{selected_setting}

## ТОН И СТИЛЬ
Тон кампании: {selected_tone}
Жанровые правила: {selected_genre}

## ВЕЛИКИЕ ТАБУ (что категорически нельзя делать в этом мире)
- [3-4 табу, связанных с магией, религией или социальными нормами]

## СТАРТОВАЯ ЛОКАЦИЯ
- Название и описание места, где начинается приключение
- Ключевые NPC и их роли
- Основные достопримечательности и опасности

## КЛЮЧЕВЫЕ ФРАКЦИИ
- [4-5 основных фракций с их целями, методами и отношениями]

## МИРОВЫЕ КОНСТАНТЫ (никогда не нарушай эти правила!)
1. [Фундаментальный закон мира]
2. [Магическое правило]
3. [Социальная константа]
4. [Природный закон]
5. [Религиозная догма]
6. [Историческая истина]
7. [Космический принцип]

Создай уникальный, интересный мир с четкими правилами и атмосферой. Все должно быть логично связано между собой."""

            response = self.client.chat.completions.create(
                model=self.models["world"],
                messages=[{"role": "user", "content": world_prompt}],
                max_completion_tokens=2000,
                temperature=0.9
            )
            
            self.world_bible = response.choices[0].message.content
            
            # Сохраняем Библию мира в файл
            with open("world_bible.md", 'w', encoding='utf-8') as f:
                f.write(self.world_bible)
            
            print("✅ Библия мира успешно сгенерирована и сохранена")
            
        except Exception as e:
            print(f"❌ Ошибка при генерации Библии мира: {e}")
            self.world_bible = "Ошибка загрузки Библии мира"

    def initialize_story_arc(self):
        """Определяет текущий сюжет: продолжить или начать заново."""
        has_previous_story = os.path.exists(self.story_file)

        if has_previous_story:
            continue_previous = messagebox.askyesno(
                "Режим игры",
                "Продолжить прошлую сессию приключения?\n" \
                "(Да — продолжить, Нет — начать новую историю)"
            )

            if continue_previous:
                self.session_mode = "continue"
                loaded = self.load_story_arc()
                if loaded and self.story_arc and not self.story_arc.startswith("Ошибка"):
                    self.story_status_message = "Продолжаем прошлое приключение. Загляните в 'Сюжет', чтобы освежить план."
                else:
                    self.session_mode = "new"
                    if self.story_arc and not self.story_arc.startswith("Ошибка"):
                        self.story_status_message = "Предыдущий сюжет не найден, создано новое приключение. Ознакомьтесь с 'Сюжетом'."
                    else:
                        detail = f" Причина: {self.last_error_message}" if self.last_error_message else ""
                        self.story_status_message = "Не удалось загрузить прошлый сюжет и создать новый. Попробуйте сгенерировать его вручную через раздел 'Сюжет'." + detail
                return

        # Если нет предыдущей истории или выбран новый старт
        self.session_mode = "new"
        created = self.generate_story_arc()
        if created and self.story_arc and not self.story_arc.startswith("Ошибка"):
            self.story_status_message = "Начинаем новое приключение! Ознакомьтесь с разделом 'Сюжет', чтобы понять направление истории."
        else:
            detail = f" Причина: {self.last_error_message}" if self.last_error_message else ""
            self.story_status_message = "Не удалось сгенерировать сюжет автоматически. Попробуйте снова через меню 'Сюжет'." + detail

    def load_story_arc(self):
        """Загружает сюжет из файла"""
        try:
            with open(self.story_file, 'r', encoding='utf-8') as f:
                self.story_arc = f.read().strip()
            if not self.story_arc:
                raise ValueError("Пустой сюжет")
            print("🗺️ Сюжет кампании загружен")
            self.last_error_message = ""
            self.update_system_prompt()
            return True
        except Exception as e:
            print(f"❌ Ошибка при загрузке сюжета: {e}")
            self.last_error_message = str(e)
            self.story_arc = None
            created = self.generate_story_arc()
            return created

    def generate_story_arc(self) -> bool:
        """Генерирует новый сюжет кампании и сохраняет его.

        Возвращает True при успехе, False при ошибке."""
        try:
            world_context = self.world_bible if self.world_bible else "Мир не определен"
            rules_context = "\n" + yaml.dump(self.game_rules, allow_unicode=True, sort_keys=False) if self.game_rules else ""

            story_prompt = f"""На основе следующей информации создай сюжет для кампании D&D:

Мир:
{world_context}

Правила или особенности кампании:
{rules_context}

Требования к сюжету:
- Дай яркое название кампании и краткий синопсис (3-4 предложения).
- Распиши сюжет минимум на 3 акта с ключевыми событиями, конфликтами и ожидаемым исходом каждого акта.
- Добавь 3-4 ключевых NPC или фракции, чьи цели двигают сюжет вперед.
- Обозначь 3 сюжетных крючка для игроков и 3 возможные развилки/варианта развития.
- Укажи финальную цель кампании и условия ее достижения.
- Пиши компактно, структурировано с подзаголовками и списками.
- Помни, что мастер обязан направлять игроков к кульминациям, сохраняя интригу и атмосферу.
"""

            response = self.client.chat.completions.create(
                model=self.models["story"],
                messages=[{"role": "user", "content": story_prompt}],
                max_completion_tokens=1500,
                temperature=0.85
            )

            self.story_arc = response.choices[0].message.content.strip()

            with open(self.story_file, 'w', encoding='utf-8') as f:
                f.write(self.story_arc)

            print("✅ Сюжет кампании обновлен и сохранен")

            self.last_error_message = ""
            return True

        except Exception as e:
            print(f"❌ Ошибка при генерации сюжета: {e}")
            self.last_error_message = str(e)
            self.story_arc = "Ошибка загрузки сюжета"
            return False

        finally:
            # После любого обновления сюжета пересобираем системный промпт
            self.update_system_prompt()

    def update_system_prompt(self):
        """Обновляет системный промпт(OpenAI) с учетом текущего мира и сюжета"""
        world_context = self.world_bible if self.world_bible else "Библия мира не загружена"
        story_arc_context = self.story_arc if self.story_arc else "Сюжет текущей сессии не загружен"

        self.system_prompt = f"""Ты опытный мастер D&D. Твоя задача - вести игру, создавать атмосферу и помогать игрокам.
        Отвечай на русском языке в роли мастера игры. Будь креативным, но справедливым.
        Если игрок описывает действия своего персонажа, реагируй как мастер и расскажи что происходит.
        Если игрок задает вопросы о правилах или мире, отвечай как знающий мастер.
        Ты обязан строго следовать сюжету текущей сессии и мягко направлять игроков к его ключевым событиям, сохраняя свободу выбора.

        ПРАВИЛА ИГРЫ:
        - Всегда бросай кости за кадром и сообщай готовые результаты
        - Используй шкалу сложностей: Тривиальная(5), Легкая(10), Средняя(15), Сложная(20), Очень сложная(25), Почти невозможная(30)
        - Для проверок характеристик используй d20 + модификатор характеристики
        - Для атак используй d20 + бонус атаки против Класса Брони (AC)
        - Критический удар на 20, критический промах на 1
        - Длина ответов: 50-200 слов, предпочтительно 100 слов

        ВАЖНО: Строго следуй правилам и константам мира из Библии мира:
        {world_context}

        ТЕКУЩИЙ СЮЖЕТ КАМПАНИИ (следуй ему без отклонений, направляй игроков к кульминациям и финалу):
        {story_arc_context}

        Никогда не нарушай установленные константы мира и следуй заданному тону и стилю."""

    def detect_and_roll_dice(self, user_input: str) -> str:
        """Определяет нужны ли броски костей и выполняет их"""
        dice_results = []
        
        # Список ключевых слов для автоматических бросков
        auto_roll_keywords = {
            'атака': ('d20', 0),  # Базовая атака
            'урон': ('d8', 0),    # Базовый урон меча
            'проверка': ('d20', 0),  # Проверка характеристики
            'спасбросок': ('d20', 0),  # Спасбросок
            'инициатива': ('d20', 0),  # Инициатива
            'скрытность': ('d20', 0),  # Проверка скрытности
            'восприятие': ('d20', 0),  # Проверка восприятия
            'магия': ('d20', 0),  # Проверка магии
            'убеждение': ('d20', 0),  # Проверка убеждения
            'запугивание': ('d20', 0),  # Проверка запугивания
            'атлетика': ('d20', 0),  # Проверка атлетики
            'акробатика': ('d20', 0),  # Проверка акробатики
        }
        
        # Проверяем, есть ли в тексте ключевые слова для бросков
        for keyword, (dice_type, modifier) in auto_roll_keywords.items():
            if keyword in user_input.lower():
                result = dice_roller.roll_dice(f"{dice_type}+{modifier}")
                dice_results.append(dice_roller.format_roll_result(result))
        
        # Проверяем явные команды бросков (например "бросаю d20", "кидаю кости")
        dice_patterns = [
            r'бросаю?\s+(d\d+)',
            r'кидаю?\s+(d\d+)',
            r'бросок\s+(d\d+)',
            r'(\d*d\d+\+?\d*)',
        ]
        
        for pattern in dice_patterns:
            matches = re.findall(pattern, user_input.lower())
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                result = dice_roller.roll_dice(match)
                dice_results.append(dice_roller.format_roll_result(result))
        
        return dice_results
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        colors = self.theme
        fonts = self.fonts

        # Заголовок
        title_frame = tk.Frame(
            self.root,
            bg=colors["bg_dark"],
            pady=10
        )
        title_frame.pack(fill='x', padx=20, pady=(10, 0))

        title_label = tk.Label(
            title_frame,
            text="🎲 Добро пожаловать в D&D с AI мастером! 🎲",
            font=fonts["title"],
            bg=colors["bg_dark"],
            fg=colors["accent_light"]
        )
        title_label.pack()

        subtitle_label = tk.Label(
            title_frame,
            text="Приготовьтесь к приключению: описывайте действия, а мастер поведает, что скрывают тени мира.",
            font=fonts["text"],
            bg=colors["bg_dark"],
            fg=colors["text_muted"]
        )
        subtitle_label.pack()

        # Область истории чата
        chat_frame = tk.Frame(
            self.root,
            bg=colors["bg_panel"],
            highlightbackground=colors["accent_muted"],
            highlightthickness=1,
            bd=0,
            padx=10,
            pady=10
        )
        chat_frame.pack(fill='both', expand=True, padx=20, pady=15)

        chat_label = tk.Label(
            chat_frame,
            text="История приключения:",
            font=fonts["subtitle"],
            bg=colors["bg_panel"],
            fg=colors["accent_light"]
        )
        chat_label.pack(anchor='w', padx=5, pady=(0, 4))

        # Текстовое поле с прокруткой для истории
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=fonts["text"],
            bg=colors["bg_card"],
            fg=colors["text_dark"],
            state='disabled',
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            insertbackground=colors["text_dark"],
            selectbackground=colors["accent"],
            selectforeground=colors["text_dark"],
            padx=10,
            pady=10
        )
        try:
            self.chat_display.config(disabledbackground=colors["bg_card"], disabledforeground=colors["text_dark"])
        except tk.TclError:
            pass
        self.chat_display.pack(fill='both', expand=True, padx=5, pady=5)
        self.chat_display.tag_configure("speaker_master", foreground=colors["accent"], font=fonts["button"])
        self.chat_display.tag_configure("speaker_player", foreground=colors["button_primary"], font=fonts["button"])
        self.chat_display.tag_configure("speaker_dice", foreground=colors["dice_highlight"], font=fonts["button"])
        self.chat_display.tag_configure("speaker_other", foreground=colors["text_dark"], font=fonts["button"])
        self.chat_display.tag_configure("message_body", foreground=colors["text_dark"], font=fonts["text"])

        # Область ввода
        input_frame = tk.Frame(
            self.root,
            bg=colors["bg_panel"],
            highlightbackground=colors["accent_muted"],
            highlightthickness=1,
            bd=0,
            padx=10,
            pady=10
        )
        input_frame.pack(fill='x', padx=20, pady=(0, 20))

        input_label = tk.Label(
            input_frame,
            text="Ваше действие:",
            font=fonts["subtitle"],
            bg=colors["bg_panel"],
            fg=colors["accent_light"]
        )
        input_label.pack(anchor='w', padx=5, pady=(0, 6))

        # Поле ввода и кнопки
        button_frame = tk.Frame(
            input_frame,
            bg=colors["bg_panel"]
        )
        button_frame.pack(fill='x', padx=5, pady=5)

        self.input_text = tk.Text(
            button_frame,
            height=3,
            wrap=tk.WORD,
            font=fonts["text"],
            bg=colors["bg_input"],
            fg=colors["text_dark"],
            insertbackground=colors["text_dark"],
            relief='flat',
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=colors["accent_muted"],
            highlightcolor=colors["accent"],
            padx=8,
            pady=6
        )
        self.input_text.pack(side='left', fill='both', expand=True, padx=(0, 5))

        # Кнопки
        buttons_frame = tk.Frame(button_frame, bg=colors["bg_panel"])
        buttons_frame.pack(side='right', fill='y')

        self.send_button = tk.Button(
            buttons_frame,
            text="Отправить",
            command=self.send_message,
            font=fonts["button"],
            bg=colors["button_primary"],
            fg=colors["button_text"],
            activebackground=colors["accent"],
            activeforeground=colors["text_dark"],
            relief='flat',
            bd=0,
            width=12,
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"]
        )
        self.send_button.pack(pady=2)

        self.world_button = tk.Button(
            buttons_frame,
            text="Мир",
            command=self.show_world_bible,
            font=fonts["button"],
            bg=colors["button_secondary"],
            fg=colors["button_text"],
            activebackground=colors["accent"],
            activeforeground=colors["text_dark"],
            relief='flat',
            bd=0,
            width=12,
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"]
        )
        self.world_button.pack(pady=2)

        self.story_button = tk.Button(
            buttons_frame,
            text="Сюжет",
            command=self.show_story_arc,
            font=fonts["button"],
            bg=colors["accent_light"],
            fg=colors["text_dark"],
            activebackground=colors["accent"],
            activeforeground=colors["text_dark"],
            relief='flat',
            bd=0,
            width=12,
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"]
        )
        self.story_button.pack(pady=2)

        self.dice_button = tk.Button(
            buttons_frame,
            text="Кости",
            command=self.show_dice_roller,
            font=fonts["button"],
            bg=colors["accent"],
            fg=colors["text_dark"],
            activebackground=colors["accent_light"],
            activeforeground=colors["text_dark"],
            relief='flat',
            bd=0,
            width=12,
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"]
        )
        self.dice_button.pack(pady=2)

        self.exit_button = tk.Button(
            buttons_frame,
            text="Выход",
            command=self.exit_app,
            font=fonts["button"],
            bg=colors["button_danger"],
            fg=colors["button_text"],
            activebackground="#a42822",
            activeforeground=colors["button_text"],
            relief='flat',
            bd=0,
            width=12,
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"]
        )
        self.exit_button.pack(pady=2)
        
        # Привязываем Enter для отправки сообщения
        self.input_text.bind('<Control-Return>', lambda e: self.send_message())
        
        # Приветственное сообщение
        welcome_message = (
            "Добро пожаловать в мир D&D! Я ваш мастер игры. Мир уже создан и готов к приключениям. "
            "Нажмите кнопку 'Мир', чтобы изучить Библию мира, и 'Сюжет' — чтобы увидеть план кампании. "
        )
        if self.story_status_message:
            welcome_message += self.story_status_message
        self.add_to_chat("🎭 Мастер", welcome_message)
        
    def add_to_chat(self, sender, message):
        """Добавить сообщение в чат"""
        if "Мастер" in sender:
            speaker_tag = "speaker_master"
        elif "Игрок" in sender:
            speaker_tag = "speaker_player"
        elif "Бросок" in sender:
            speaker_tag = "speaker_dice"
        else:
            speaker_tag = "speaker_other"

        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"{sender}: ", speaker_tag)
        self.chat_display.insert(tk.END, f"{message}\n\n", "message_body")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
        
    def send_message(self):
        """Отправить сообщение мастеру"""
        user_input = self.input_text.get("1.0", tk.END).strip()
        
        if not user_input:
            return
            
        # Очищаем поле ввода
        self.input_text.delete("1.0", tk.END)
        
        # Добавляем сообщение игрока в чат
        self.add_to_chat("👤 Игрок", user_input)
        
        # Проверяем и выполняем броски костей
        dice_results = self.detect_and_roll_dice(user_input)
        if dice_results:
            for result in dice_results:
                self.add_to_chat("🎲 Бросок", result)
        
        # Отключаем кнопку отправки во время обработки
        self.send_button.config(state='disabled', text="Думает...")
        
        # Запускаем обработку в отдельном потоке
        thread = threading.Thread(target=self.process_message, args=(user_input,))
        thread.daemon = True
        thread.start()
        
    def process_message(self, user_input):
        """Обработать сообщение в отдельном потоке"""
        try:
            master_response = self.get_master_response(user_input)
            
            # Обновляем UI в главном потоке
            self.root.after(0, self.display_master_response, master_response)
            
        except Exception as e:
            error_msg = f"❌ Ошибка при обращении к OpenAI: {str(e)}"
            self.root.after(0, self.display_master_response, error_msg)
            
    def display_master_response(self, response):
        """Отобразить ответ мастера"""
        self.add_to_chat("🎭 Мастер", response)
        
        # Включаем кнопку отправки обратно
        self.send_button.config(state='normal', text="Отправить")
        
    def get_master_response(self, user_input):
        """Получить ответ от мастера через OpenAI API"""
        try:
            # Добавляем пользовательский ввод в историю
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Формируем сообщения для API
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.conversation_history[-10:])  # Ограничиваем историю последними 10 сообщениями
            
            # Отправляем запрос к OpenAI
            response = self.client.chat.completions.create(
                model=self.models["master"],
                messages=messages,
                max_completion_tokens=500,
                temperature=0.8
            )
            
            master_response = response.choices[0].message.content
            
            # Добавляем ответ мастера в историю
            self.conversation_history.append({"role": "assistant", "content": master_response})
            
            return master_response
            
        except Exception as e:
            return f"❌ Ошибка при обращении к OpenAI: {str(e)}"
    
    def show_world_bible(self):
        """Показать Библию мира в отдельном окне"""
        if not self.world_bible:
            messagebox.showwarning("Предупреждение", "Библия мира не загружена")
            return
            
        colors = self.theme
        fonts = self.fonts

        bible_window = tk.Toplevel(self.root)
        bible_window.title("📖 Библия мира")
        bible_window.geometry("900x700")
        bible_window.minsize(700, 500)
        bible_window.configure(bg=colors["bg_dark"])

        container = tk.Frame(
            bible_window,
            bg=colors["bg_panel"],
            highlightbackground=colors["accent_muted"],
            highlightthickness=1,
            bd=0,
            padx=15,
            pady=15
        )
        container.pack(fill='both', expand=True, padx=20, pady=20)

        title_label = tk.Label(
            container,
            text="📖 Библия мира",
            font=fonts["title"],
            bg=colors["bg_panel"],
            fg=colors["accent_light"]
        )
        title_label.pack(pady=(0, 12))

        bible_text = scrolledtext.ScrolledText(
            container,
            wrap=tk.WORD,
            width=100,
            height=35,
            font=fonts["text"],
            bg=colors["bg_card"],
            fg=colors["text_dark"],
            state='disabled',
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            insertbackground=colors["text_dark"],
            selectbackground=colors["accent"],
            selectforeground=colors["text_dark"],
            padx=12,
            pady=12
        )
        try:
            bible_text.config(disabledbackground=colors["bg_card"], disabledforeground=colors["text_dark"])
        except tk.TclError:
            pass
        bible_text.pack(fill='both', expand=True, padx=5, pady=5)

        bible_text.config(state='normal')
        bible_text.insert(tk.END, self.world_bible)
        bible_text.config(state='disabled')

        close_button = tk.Button(
            container,
            text="Закрыть",
            command=bible_window.destroy,
            font=fonts["button"],
            bg=colors["button_danger"],
            fg=colors["button_text"],
            activebackground="#a42822",
            activeforeground=colors["button_text"],
            relief='flat',
            bd=0,
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"],
            padx=14,
            pady=6
        )
        close_button.pack(pady=10)

    def show_story_arc(self):
        """Показывает текущий сюжет кампании и позволяет обновить его"""
        colors = self.theme
        fonts = self.fonts

        story_window = tk.Toplevel(self.root)
        story_window.title("🗺️ Сюжет кампании")
        story_window.geometry("800x600")
        story_window.minsize(600, 450)
        story_window.configure(bg=colors["bg_dark"])

        container = tk.Frame(
            story_window,
            bg=colors["bg_panel"],
            highlightbackground=colors["accent_muted"],
            highlightthickness=1,
            bd=0,
            padx=15,
            pady=15
        )
        container.pack(fill='both', expand=True, padx=20, pady=20)

        title_label = tk.Label(
            container,
            text="🗺️ План кампании",
            font=fonts["title"],
            bg=colors["bg_panel"],
            fg=colors["accent_light"]
        )
        title_label.pack(pady=(0, 12))

        story_text = scrolledtext.ScrolledText(
            container,
            wrap=tk.WORD,
            width=90,
            height=30,
            font=fonts["text"],
            bg=colors["bg_card"],
            fg=colors["text_dark"],
            state='normal',
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            insertbackground=colors["text_dark"],
            selectbackground=colors["accent"],
            selectforeground=colors["text_dark"],
            padx=12,
            pady=12
        )
        story_text.pack(fill='both', expand=True, padx=5, pady=5)

        if self.story_arc and not self.story_arc.startswith("Ошибка"):
            story_content = self.story_arc
            story_state = 'disabled'
        else:
            story_content = "Сюжет не загружен. Используйте кнопку ниже, чтобы сгенерировать новый."
            story_state = 'normal'

        story_text.insert(tk.END, story_content)
        story_text.config(state=story_state)
        try:
            story_text.config(disabledbackground=colors["bg_card"], disabledforeground=colors["text_dark"])
        except tk.TclError:
            pass

        buttons_bar = tk.Frame(container, bg=colors["bg_panel"])
        buttons_bar.pack(fill='x', pady=(12, 0))

        def regenerate_story():
            if not messagebox.askyesno(
                "Новый сюжет",
                "Сгенерировать новый сюжет кампании? Текущий план будет перезаписан."
            ):
                return

            created = self.generate_story_arc()
            if created and self.story_arc and not self.story_arc.startswith("Ошибка"):
                story_text.config(state='normal')
                story_text.delete("1.0", tk.END)
                story_text.insert(tk.END, self.story_arc)
                story_text.config(state='disabled')
                messagebox.showinfo("Сюжет обновлен", "Создан новый сюжет кампании. Ведущий будет следовать ему.")
                self.session_mode = "new"
                self.story_status_message = "Сюжет обновлен. Ознакомьтесь с разделом 'Сюжет', чтобы увидеть новые детали."
                self.add_to_chat("🎭 Мастер", "Сюжет кампании только что обновился. Следуем новому плану приключения!")
            else:
                story_text.config(state='normal')
                story_text.delete("1.0", tk.END)
                failure_text = "Не удалось создать сюжет. Повторите попытку позже."
                if self.last_error_message:
                    failure_text += f"\n\nПричина: {self.last_error_message}"
                story_text.insert(tk.END, failure_text)
                story_text.config(state='disabled')
                message = "Не удалось создать сюжет. Проверьте подключение к сети или попробуйте позже."
                if self.last_error_message:
                    message += f"\n\nПодробности: {self.last_error_message}"
                messagebox.showerror("Ошибка", message)
                self.story_status_message = "Сюжет недоступен. Повторите генерацию через раздел 'Сюжет'."
                self.add_to_chat("🎭 Мастер", "Не удалось обновить сюжет кампании. Попробуйте снова или проверьте соединение.")

        regenerate_button = tk.Button(
            buttons_bar,
            text="Сгенерировать новый сюжет",
            command=regenerate_story,
            font=fonts["button"],
            bg=colors["button_primary"],
            fg=colors["button_text"],
            activebackground=colors["accent"],
            activeforeground=colors["text_dark"],
            relief='flat',
            bd=0,
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"],
            padx=12,
            pady=6
        )
        regenerate_button.pack(side='left')

        close_button = tk.Button(
            buttons_bar,
            text="Закрыть",
            command=story_window.destroy,
            font=fonts["button"],
            bg=colors["button_danger"],
            fg=colors["button_text"],
            activebackground="#a42822",
            activeforeground=colors["button_text"],
            relief='flat',
            bd=0,
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"],
            padx=12,
            pady=6
        )
        close_button.pack(side='right')

    def show_dice_roller(self):
        """Показать окно броска костей"""
        colors = self.theme
        fonts = self.fonts

        dice_window = tk.Toplevel(self.root)
        dice_window.title("🎲 Бросок костей")
        dice_window.geometry("500x400")
        dice_window.minsize(420, 360)
        dice_window.configure(bg=colors["bg_dark"])

        container = tk.Frame(
            dice_window,
            bg=colors["bg_panel"],
            highlightbackground=colors["accent_muted"],
            highlightthickness=1,
            bd=0,
            padx=15,
            pady=15
        )
        container.pack(fill='both', expand=True, padx=20, pady=20)

        title_label = tk.Label(
            container,
            text="🎲 Бросок костей",
            font=fonts["title"],
            bg=colors["bg_panel"],
            fg=colors["accent_light"]
        )
        title_label.pack(pady=(0, 12))

        input_frame = tk.Frame(container, bg=colors["bg_panel"])
        input_frame.pack(fill='x', padx=5, pady=10)

        tk.Label(
            input_frame,
            text="Введите бросок (например: d20, 2d6+3):",
            font=fonts["text"],
            bg=colors["bg_panel"],
            fg=colors["accent_light"]
        ).pack(anchor='w')

        dice_input = tk.Entry(
            input_frame,
            font=fonts["text"],
            width=20,
            bg=colors["bg_input"],
            fg=colors["text_dark"],
            insertbackground=colors["text_dark"],
            relief='flat',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"],
            highlightcolor=colors["accent"]
        )
        dice_input.pack(side='left', padx=(0, 10), pady=(6, 0))

        roll_button = tk.Button(
            input_frame,
            text="Бросить",
            command=lambda: self.roll_dice_from_input(dice_input, result_text),
            font=fonts["button"],
            bg=colors["button_primary"],
            fg=colors["button_text"],
            activebackground=colors["accent"],
            activeforeground=colors["text_dark"],
            relief='flat',
            bd=0,
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"],
            padx=12,
            pady=4
        )
        roll_button.pack(side='left', pady=(6, 0))

        quick_frame = tk.Frame(container, bg=colors["bg_panel"])
        quick_frame.pack(fill='x', padx=5, pady=5)

        tk.Label(
            quick_frame,
            text="Быстрые броски:",
            font=fonts["text"],
            bg=colors["bg_panel"],
            fg=colors["accent_light"]
        ).pack(anchor='w')

        quick_buttons_frame = tk.Frame(quick_frame, bg=colors["bg_panel"])
        quick_buttons_frame.pack(fill='x', pady=5)

        quick_dice = ['d20', 'd12', 'd10', 'd8', 'd6', 'd4']
        for dice in quick_dice:
            btn = tk.Button(
                quick_buttons_frame,
                text=dice,
                command=lambda d=dice: self.quick_roll(d, result_text),
                font=fonts["text"],
                bg=colors["accent"],
                fg=colors["text_dark"],
                activebackground=colors["accent_light"],
                activeforeground=colors["text_dark"],
                relief='flat',
                bd=0,
                width=6,
                cursor='hand2',
                highlightthickness=1,
                highlightbackground=colors["accent_muted"]
            )
            btn.pack(side='left', padx=3, pady=2)

        result_text = scrolledtext.ScrolledText(
            container,
            wrap=tk.WORD,
            width=50,
            height=15,
            font=fonts["text"],
            bg=colors["bg_card"],
            fg=colors["text_dark"],
            state='disabled',
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            insertbackground=colors["text_dark"],
            selectbackground=colors["accent"],
            selectforeground=colors["text_dark"],
            padx=10,
            pady=10
        )
        try:
            result_text.config(disabledbackground=colors["bg_card"], disabledforeground=colors["text_dark"])
        except tk.TclError:
            pass
        result_text.pack(fill='both', expand=True, padx=5, pady=10)

        close_button = tk.Button(
            container,
            text="Закрыть",
            command=dice_window.destroy,
            font=fonts["button"],
            bg=colors["button_danger"],
            fg=colors["button_text"],
            activebackground="#a42822",
            activeforeground=colors["button_text"],
            relief='flat',
            bd=0,
            cursor='hand2',
            highlightthickness=1,
            highlightbackground=colors["accent_muted"],
            padx=14,
            pady=6
        )
        close_button.pack(pady=10)
    
    def roll_dice_from_input(self, input_widget, result_widget):
        """Бросить кости из поля ввода"""
        dice_string = input_widget.get().strip()
        if not dice_string:
            return
        
        result = dice_roller.roll_dice(dice_string)
        formatted_result = dice_roller.format_roll_result(result)
        
        result_widget.config(state='normal')
        result_widget.insert(tk.END, f"{formatted_result}\n")
        result_widget.config(state='disabled')
        result_widget.see(tk.END)
        
        # Добавляем результат в основной чат
        self.add_to_chat("🎲 Бросок", formatted_result)
    
    def quick_roll(self, dice_string, result_widget):
        """Быстрый бросок костей"""
        result = dice_roller.roll_dice(dice_string)
        formatted_result = dice_roller.format_roll_result(result)
        
        result_widget.config(state='normal')
        result_widget.insert(tk.END, f"{formatted_result}\n")
        result_widget.config(state='disabled')
        result_widget.see(tk.END)
        
        # Добавляем результат в основной чат
        self.add_to_chat("🎲 Бросок", formatted_result)
    
    def exit_app(self):
        """Выход из приложения"""
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти из игры?"):
            self.root.quit()
            self.root.destroy()
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

def main():
    """Точка входа в приложение"""
    try:
        app = DnDMasterGUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Произошла ошибка при запуске приложения: {str(e)}")

if __name__ == "__main__":
    main()
