#!/usr/bin/env python3
"""
Простое CLI приложение для D&D мастера с использованием OpenAI API
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from dotenv import load_dotenv
from openai import OpenAI
import random
import yaml
import re
from dice_system import dice_roller
from party_builder import PartyBuilder, PartyMember, PartyValidationError

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
        self.party_state_path = Path(__file__).resolve().parent / "party_state.json"
        self.party_state_file = str(self.party_state_path)
        self.party_store = self.load_party_state()
        self.current_scenario: Optional[str] = None
        self.party_state: Optional[Dict[str, object]] = None
        
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

    def load_party_state(self) -> Dict[str, object]:
        """Load stored parties for all scenarios, migrating old format if needed."""
        default_store: Dict[str, object] = {"scenarios": {}}
        if self.party_state_path.exists():
            try:
                with open(self.party_state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict) and "scenarios" in data:
                    scenarios = data.get("scenarios", {})
                    if isinstance(scenarios, dict):
                        return {"scenarios": scenarios}
                if isinstance(data, dict) and "party" in data:
                    return {"scenarios": {"default": data}}
            except Exception as error:
                print(f"❌ Не удалось загрузить сохраненную партию: {error}")
        else:
            try:
                with open(self.party_state_file, 'w', encoding='utf-8') as f:
                    json.dump(default_store, f, ensure_ascii=False, indent=2)
            except Exception as error:
                print(f"❌ Не удалось создать файл хранения партий: {error}")
        return default_store

    def save_party_state(self) -> None:
        """Persist all stored scenario parties to disk."""
        try:
            with open(self.party_state_file, 'w', encoding='utf-8') as f:
                json.dump(self.party_store, f, ensure_ascii=False, indent=2)
        except Exception as error:
            print(f"❌ Не удалось сохранить партию: {error}")

    @property
    def party_initialized(self) -> bool:
        if not isinstance(self.party_state, dict):
            return False
        flags = (
            self.party_state.get("state_delta", {})
            .get("flags", {})
            .get("set", [])
        )
        return bool(flags and "party_initialized" in flags)

    def has_saved_party_members(self) -> bool:
        scenarios = self.party_store.get("scenarios", {})
        if not isinstance(scenarios, dict):
            return False
        for payload in scenarios.values():
            if not isinstance(payload, dict):
                continue
            flags = (
                payload.get("state_delta", {})
                .get("flags", {})
                .get("set", [])
            )
            if isinstance(flags, list) and "party_initialized" in flags:
                return True
        return False

    def ensure_party_initialized(self) -> None:
        """Guide the user through party creation if no party exists."""
        self._ensure_scenario_selected()
        if self.party_initialized:
            print("Партия уже инициализирована для выбранного сценария.")
            return

        try:
            payload = self._run_party_creation_flow()
        except KeyboardInterrupt:
            print("\nСоздание партии прервано пользователем.")
            sys.exit(0)
        except PartyValidationError as error:
            print(f"❌ Ошибка валидации партии: {error}")
            sys.exit(1)

        if payload:
            self.party_state = payload
            scenarios = self.party_store.setdefault("scenarios", {})
            if self.current_scenario:
                scenarios[self.current_scenario] = payload
            self.save_party_state()
            print("\nПартия готова. Ведущий может начинать первую сцену.")

    def _run_party_creation_flow(self) -> Dict[str, object]:
        scenario_label = self.current_scenario or "новый сценарий"
        print(f"Создаем стартовую команду для сценария: {scenario_label}")

        party_size = self._prompt_party_size()
        builder = PartyBuilder()
        existing_ids: Set[str] = set()

        for index in range(1, party_size + 1):
            print(f"\nПерсонаж {index} из {party_size}:")
            member = self._collect_member_data(index, existing_ids)
            builder.add_member(member)
            existing_ids.add(member.id)

        coin = self._prompt_optional_int(
            "Сколько монет у партии? (по умолчанию 0): ",
            minimum=0,
            default=0,
        )
        rations = self._prompt_optional_int(
            "Сколько пайков у партии? (по умолчанию 0): ",
            minimum=0,
            default=0,
        )
        party_tags = self._prompt_party_tags()

        builder.coin = coin
        builder.rations = rations
        builder.party_tags = party_tags

        payload = builder.build_payload()

        json_text = json.dumps(payload, ensure_ascii=False, indent=2)
        print(json_text)
        for line in payload["party_compact"]:
            print(line)

        return payload

    def _ensure_scenario_selected(self) -> None:
        if self.current_scenario:
            return

        scenarios = self.party_store.get("scenarios", {})
        scenario_names = list(scenarios.keys())
        if scenario_names:
            print("\nДоступные сценарии:")
            for idx, name in enumerate(scenario_names, start=1):
                print(f"  {idx}. {name}")

        prompt = (
            "Введите название сценария или номер из списка: "
            if scenario_names
            else "Введите название нового сценария: "
        )

        while True:
            choice = input(prompt).strip()
            if not choice:
                print("Название сценария не может быть пустым.")
                continue

            if scenario_names and choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(scenario_names):
                    self.current_scenario = scenario_names[index - 1]
                    break
                print("Укажите корректный номер из списка.")
                continue

            self.current_scenario = choice
            break

        if self.current_scenario in scenarios:
            stored = scenarios[self.current_scenario]
            if isinstance(stored, dict):
                self.party_state = stored

    def _prompt_party_size(self) -> int:
        while True:
            raw = input("Сколько персонажей будет в этом сценарии? (1-3): ").strip()
            if not raw:
                print("Нужно ввести число от 1 до 3.")
                continue
            if raw.isdigit():
                value = int(raw)
                if 1 <= value <= 3:
                    return value
            print("Количество персонажей должно быть от 1 до 3.")

    def _collect_member_data(self, index: int, existing_ids: Set[str]) -> PartyMember:
        name = self._prompt_non_empty("Имя персонажа: ")
        role = self._prompt_non_empty("Роль персонажа: ")
        concept = self._prompt_non_empty("Коротко о концепте: ")

        stats: Dict[str, int] = {}
        stat_order = [
            ("str", "Сила"),
            ("dex", "Ловкость"),
            ("int", "Интеллект"),
            ("wit", "Сообразительность"),
            ("charm", "Обаяние"),
        ]
        for key, label in stat_order:
            stats[key] = self._prompt_int(
                f"{label} ({-1} до {3}): ",
                minimum=-1,
                maximum=3,
            )

        hp = self._prompt_int("HP (8-14): ", minimum=8, maximum=14)

        traits = self._prompt_fixed_list(
            "Укажи две черты характера (через запятую): ",
            expected_count=2,
        )
        loadout = self._prompt_fixed_list(
            "Укажи два предмета стартового снаряжения (через запятую): ",
            expected_count=2,
        )
        tags = self._prompt_tags(
            "Укажи 1-2 тега персонажа (через запятую): ",
            minimum=1,
            maximum=2,
        )

        member_id = self._generate_member_id(name, existing_ids, index)

        return PartyMember(
            id=member_id,
            name=name,
            role=role,
            concept=concept,
            stats=stats,
            traits=traits,
            loadout=loadout,
            hp=hp,
            tags=tags,
        )

    def _prompt_non_empty(self, prompt: str) -> str:
        while True:
            value = input(prompt).strip()
            if value:
                return value
            print("Поле не может быть пустым.")

    def _prompt_int(
        self,
        prompt: str,
        *,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
    ) -> int:
        while True:
            raw = input(prompt).strip()
            try:
                value = int(raw)
            except ValueError:
                print("Введите целое число.")
                continue
            if minimum is not None and value < minimum:
                print(f"Число не может быть меньше {minimum}.")
                continue
            if maximum is not None and value > maximum:
                print(f"Число не может быть больше {maximum}.")
                continue
            return value

    def _prompt_optional_int(
        self,
        prompt: str,
        *,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
        default: int = 0,
    ) -> int:
        while True:
            raw = input(prompt).strip()
            if not raw:
                return default
            try:
                value = int(raw)
            except ValueError:
                print("Введите целое число или оставьте строку пустой.")
                continue
            if minimum is not None and value < minimum:
                print(f"Число не может быть меньше {minimum}.")
                continue
            if maximum is not None and value > maximum:
                print(f"Число не может быть больше {maximum}.")
                continue
            return value

    def _prompt_fixed_list(self, prompt: str, *, expected_count: int) -> List[str]:
        while True:
            raw = input(prompt).strip()
            items = [item.strip() for item in re.split(r'[;,/]+', raw) if item.strip()]
            if len(items) == expected_count:
                return items
            print(f"Нужно указать ровно {expected_count} элемента(ов).")

    def _prompt_tags(
        self,
        prompt: str,
        *,
        minimum: int,
        maximum: int,
    ) -> List[str]:
        while True:
            raw = input(prompt).strip()
            items = [item.strip() for item in re.split(r'[;,]+', raw) if item.strip()]
            if minimum <= len(items) <= maximum:
                return items
            print(f"Нужно указать от {minimum} до {maximum} тегов.")

    def _prompt_party_tags(self) -> List[str]:
        prompt = (
            "Опиши стиль партии тегами (до 3, через запятую, по умолчанию adventure): "
        )
        while True:
            raw = input(prompt).strip()
            if not raw:
                return ["adventure"]
            tags = [item.strip() for item in re.split(r'[;,]+', raw) if item.strip()]
            if 1 <= len(tags) <= 3:
                return tags
            print("Можно указать от 1 до 3 тегов.")

    def _generate_member_id(
        self,
        name: str,
        existing_ids: Set[str],
        index: int,
    ) -> str:
        base = self._slugify_tag(name) or f"pc_{index}"
        candidate = f"pc_{base}" if not base.startswith("pc_") else base
        suffix = 1
        final_id = candidate
        while final_id in existing_ids:
            suffix += 1
            final_id = f"{candidate}_{suffix}"
        return final_id

    def _slugify_tag(self, text: str) -> str:
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
            'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        result = []
        for char in text.lower():
            if char in translit_map:
                result.append(translit_map[char])
            elif char.isalnum() and char.isascii():
                result.append(char)
        slug = ''.join(result)
        slug = re.sub(r'[^a-z0-9]+', '', slug)
        return slug

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

        if self.has_saved_party_members():
            print("Обнаружены сохраненные персонажи в party_state.json.")

        self.ensure_party_initialized()

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

