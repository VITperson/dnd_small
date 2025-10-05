#!/usr/bin/env python3
"""
Простое CLI приложение для D&D мастера с использованием OpenAI API
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
import random
import yaml
import re
from dice_system import dice_roller

# Загружаем переменные окружения
load_dotenv()

class DnDMaster:
    def __init__(self):
        """Инициализация D&D мастера"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            print("❌ Ошибка: Не найден OPENAI_API_KEY в переменных окружения")
            print("Создайте файл .env и добавьте туда ваш API ключ:")
            print("OPENAI_API_KEY=your_key_here")
            sys.exit(1)
        
        self.client = OpenAI(api_key=self.api_key)
        self.conversation_history = []
        self.world_bible = None
        self.game_rules = None
        
        # Загружаем правила игры
        self.load_game_rules()
        
        # Инициализируем Библию мира
        self.initialize_world_bible()
        
        # Системный промпт для D&D мастера
        self.system_prompt = f"""Ты опытный мастер D&D. Твоя задача - вести игру, создавать атмосферу и помогать игрокам. 
        Отвечай на русском языке в роли мастера игры. Будь креативным, но справедливым. 
        Если игрок описывает действия своего персонажа, реагируй как мастер и расскажи что происходит.
        Если игрок задает вопросы о правилах или мире, отвечай как знающий мастер.
        
        ПРАВИЛА ИГРЫ:
        - Всегда бросай кости за кадром и сообщай готовые результаты
        - Используй шкалу сложностей: Тривиальная(5), Легкая(10), Средняя(15), Сложная(20), Очень сложная(25), Почти невозможная(30)
        - Для проверок характеристик используй d20 + модификатор характеристики
        - Для атак используй d20 + бонус атаки против Класса Брони (AC)
        - Критический удар на 20, критический промах на 1
        - Длина ответов: 50-200 слов, предпочтительно 100 слов
        
        ВАЖНО: Строго следуй правилам и константам мира из Библии мира:
        {self.world_bible if self.world_bible else "Библия мира не загружена"}
        
        Никогда не нарушай установленные константы мира и следуй заданному тону и стилю."""
    
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
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": world_prompt}],
                max_tokens=2000,
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
    
    def detect_and_roll_dice(self, user_input: str) -> list:
        """Определяет нужны ли броски костей и выполняет их"""
        dice_results = []
        
        # Список ключевых слов для автоматических бросков
        auto_roll_keywords = {
            'атака': ('d20', 0),
            'урон': ('d8', 0),
            'проверка': ('d20', 0),
            'спасбросок': ('d20', 0),
            'инициатива': ('d20', 0),
            'скрытность': ('d20', 0),
            'восприятие': ('d20', 0),
            'магия': ('d20', 0),
            'убеждение': ('d20', 0),
            'запугивание': ('d20', 0),
            'атлетика': ('d20', 0),
            'акробатика': ('d20', 0),
        }
        
        # Проверяем ключевые слова
        for keyword, (dice_type, modifier) in auto_roll_keywords.items():
            if keyword in user_input.lower():
                result = dice_roller.roll_dice(f"{dice_type}+{modifier}")
                dice_results.append(dice_roller.format_roll_result(result))
        
        # Проверяем явные команды бросков
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
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.8
            )
            
            master_response = response.choices[0].message.content
            
            # Добавляем ответ мастера в историю
            self.conversation_history.append({"role": "assistant", "content": master_response})
            
            return master_response
            
        except Exception as e:
            return f"❌ Ошибка при обращении к OpenAI: {str(e)}"
    
    def show_world_bible(self):
        """Показать Библию мира в CLI"""
        if not self.world_bible:
            print("❌ Библия мира не загружена")
            return
            
        print("\n" + "="*60)
        print("📖 БИБЛИЯ МИРА")
        print("="*60)
        print(self.world_bible)
        print("="*60)
        print("Нажмите Enter для продолжения...")
        input()
    
    def run(self):
        """Основной цикл приложения"""
        print("🎲 Добро пожаловать в D&D с AI мастером! 🎲")
        print("Мир уже создан и готов к приключениям!")
        print("Введите ваши действия или вопросы. Для выхода введите 'quit' или 'exit'")
        print("Для просмотра Библии мира введите 'мир' или 'bible'")
        print("-" * 50)
        
        while True:
            try:
                # Получаем ввод от пользователя
                user_input = input("\n👤 Игрок: ").strip()
                
                # Проверяем команды выхода
                if user_input.lower() in ['quit', 'exit', 'выход']:
                    print("\n🎲 Спасибо за игру! До свидания!")
                    break
                
                # Проверяем команду просмотра Библии мира
                if user_input.lower() in ['мир', 'bible', 'библия']:
                    self.show_world_bible()
                    continue
                
                if not user_input:
                    print("Пожалуйста, введите что-то...")
                    continue
                
                # Проверяем и выполняем броски костей
                dice_results = self.detect_and_roll_dice(user_input)
                if dice_results:
                    print("\n🎲 Результаты бросков:")
                    for result in dice_results:
                        print(f"  {result}")
                
                # Получаем ответ от мастера
                print("\n🎭 Мастер думает...")
                master_response = self.get_master_response(user_input)
                
                print(f"\n🎭 Мастер: {master_response}")
                
            except KeyboardInterrupt:
                print("\n\n🎲 Игра прервана. До свидания!")
                break
            except Exception as e:
                print(f"\n❌ Произошла ошибка: {str(e)}")

def main():
    """Точка входа в приложение"""
    master = DnDMaster()
    master.run()

if __name__ == "__main__":
    main()

