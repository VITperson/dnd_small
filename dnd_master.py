#!/usr/bin/env python3
"""
Простое CLI приложение для D&D мастера с использованием OpenAI API
"""

import json
import os
import sys
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI
import random
import yaml
import re
from dice_system import dice_roller
from party_builder import PartyBuilder, PartyMember, PartyValidationError


CANDIDATE_LIBRARY: List[Dict[str, object]] = [
    {
        "id": "shadow",
        "pitch": "shadow - скрытный разведчик, терпеливый наблюдатель",
        "style_focus": ["stealth", "exploration"],
        "tone_bias": ["neutral", "chaotic"],
        "member": {
            "id": "pc_shadow",
            "name": "Тенар",
            "role": "Разведчик",
            "concept": "тихий ловчий",
            "stats": {"str": 0, "dex": 3, "int": 1, "wit": 2, "charm": 0},
            "traits": ["скрытный", "терпеливый"],
            "loadout": ["кинжал", "теневой плащ"],
            "hp": 10,
            "tags": ["stealth", "scout"],
        },
    },
    {
        "id": "warden",
        "pitch": "warden - внимательный следопыт, преданный защитник",
        "style_focus": ["exploration", "combat"],
        "tone_bias": ["lawful", "neutral"],
        "member": {
            "id": "pc_warden",
            "name": "Эллин",
            "role": "Следопыт",
            "concept": "сторож границ",
            "stats": {"str": 1, "dex": 2, "int": 0, "wit": 2, "charm": 0},
            "traits": ["наблюдательный", "верный"],
            "loadout": ["лук", "набор следопыта"],
            "hp": 12,
            "tags": ["explorer", "guardian"],
        },
    },
    {
        "id": "silver",
        "pitch": "silver - утонченный дипломат, чуткий эмпат",
        "style_focus": ["social"],
        "tone_bias": ["lawful", "neutral"],
        "member": {
            "id": "pc_silver",
            "name": "Марис",
            "role": "Дипломат",
            "concept": "тонкий переговорщик",
            "stats": {"str": -1, "dex": 1, "int": 2, "wit": 1, "charm": 3},
            "traits": ["харизматичный", "внимательный"],
            "loadout": ["шпага", "плащ посредника"],
            "hp": 9,
            "tags": ["face", "support"],
        },
    },
    {
        "id": "ember",
        "pitch": "ember - решительный дуэлянт, пламенный маг",
        "style_focus": ["combat"],
        "tone_bias": ["chaotic", "neutral"],
        "member": {
            "id": "pc_ember",
            "name": "Айрин",
            "role": "Боевой маг",
            "concept": "стихийный боец",
            "stats": {"str": 1, "dex": 1, "int": 2, "wit": 0, "charm": 0},
            "traits": ["пламенный", "решительный"],
            "loadout": ["клинок", "огненный фокус"],
            "hp": 11,
            "tags": ["combat", "caster"],
        },
    },
    {
        "id": "sage",
        "pitch": "sage - любознательный ученый, вдумчивый стратег",
        "style_focus": ["exploration", "social"],
        "tone_bias": ["lawful", "neutral"],
        "member": {
            "id": "pc_sage",
            "name": "Калем",
            "role": "Знаток",
            "concept": "искатель знаний",
            "stats": {"str": -1, "dex": 1, "int": 3, "wit": 2, "charm": 0},
            "traits": ["рассудительный", "вдумчивый"],
            "loadout": ["том знаний", "компас"],
            "hp": 9,
            "tags": ["lore", "planner"],
        },
    },
    {
        "id": "lotus",
        "pitch": "lotus - спокойный целитель, мудрый наставник",
        "style_focus": ["social", "exploration"],
        "tone_bias": ["lawful", "neutral"],
        "member": {
            "id": "pc_lotus",
            "name": "Сайя",
            "role": "Целитель",
            "concept": "миротворец",
            "stats": {"str": 0, "dex": 0, "int": 2, "wit": 1, "charm": 2},
            "traits": ["сочувствующий", "сдержанный"],
            "loadout": ["посох", "лечебные травы"],
            "hp": 10,
            "tags": ["healer", "support"],
        },
    },
    {
        "id": "hammer",
        "pitch": "hammer - стойкий воин, прямолинейный защитник",
        "style_focus": ["combat"],
        "tone_bias": ["lawful", "neutral"],
        "member": {
            "id": "pc_hammer",
            "name": "Бранн",
            "role": "Воин",
            "concept": "щит группы",
            "stats": {"str": 3, "dex": 0, "int": 0, "wit": 1, "charm": -1},
            "traits": ["несгибаемый", "прямой"],
            "loadout": ["боевой молот", "щит"],
            "hp": 14,
            "tags": ["tank", "frontline"],
        },
    },
]

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
        self.party_state_file = "party_state.json"
        self.party_state = self.load_party_state()
        
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

    def load_party_state(self) -> Dict[str, object] | None:
        """Load stored party state if it exists."""
        if os.path.exists(self.party_state_file):
            try:
                with open(self.party_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as error:
                print(f"❌ Не удалось загрузить сохраненную партию: {error}")
        return None

    def save_party_state(self, payload: Dict[str, object]) -> None:
        """Persist the created party state to disk."""
        try:
            with open(self.party_state_file, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as error:
            print(f"❌ Не удалось сохранить партию: {error}")

    @property
    def party_initialized(self) -> bool:
        flags = (
            self.party_state
            and self.party_state.get("state_delta", {})
            .get("flags", {})
            .get("set", [])
        )
        return bool(flags and "party_initialized" in flags)

    def ensure_party_initialized(self) -> None:
        """Guide the user through party creation if no party exists."""
        if self.party_initialized:
            print("Партия уже инициализирована.")
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
            self.save_party_state(payload)

    def _run_party_creation_flow(self) -> Dict[str, object]:
        print("Перед стартом соберем стартовую партию.")

        style = self._prompt_option(
            "Выбери стиль игры (stealth/combat/social/exploration): ",
            ["stealth", "combat", "social", "exploration"],
        )
        tone = self._prompt_option(
            "Выбери моральный тон (lawful/neutral/chaotic): ",
            ["lawful", "neutral", "chaotic"],
        )
        taboo = input("Есть ли табу или нежелательные темы? ").strip()

        tags = self._build_preference_tags(style, tone, taboo)
        candidates = self._select_candidates(style, tone, tags)

        print("\nПредлагаю кандидатов, выбери от одного до трех (id через пробел):")
        for candidate in candidates:
            print(candidate["pitch"])

        chosen_ids = self._prompt_candidate_selection([c["id"] for c in candidates])

        builder = PartyBuilder(party_tags=tags[:3])
        for candidate in candidates:
            if candidate["id"] in chosen_ids:
                member = PartyMember(**candidate["member"])  # type: ignore[arg-type]
                builder.add_member(member)

        payload = builder.build_payload()

        json_text = json.dumps(payload, ensure_ascii=False, indent=2)
        print(json_text)
        for line in payload["party_compact"]:
            print(line)

        return payload

    def _prompt_option(self, prompt: str, options: List[str]) -> str:
        options_lower = [opt.lower() for opt in options]
        while True:
            answer = input(prompt).strip().lower()
            if answer in options_lower:
                return answer
            print(f"Введите одно из: {', '.join(options_lower)}")

    def _prompt_candidate_selection(self, valid_ids: List[str]) -> List[str]:
        valid = set(valid_ids)
        while True:
            raw = input("Ваш выбор: ").strip().lower()
            choices = [part for part in re.split(r'[\s,;]+', raw) if part]
            unique = []
            for item in choices:
                if item not in unique:
                    unique.append(item)
            if 1 <= len(unique) <= 3 and all(choice in valid for choice in unique):
                return unique
            print("Нужно выбрать от одного до трех кандидатов из списка.")

    def _build_preference_tags(self, style: str, tone: str, taboo: str) -> List[str]:
        tags: List[str] = [style.lower(), f"tone_{tone.lower()}"]
        taboo_tags = self._taboo_to_tags(taboo)
        for tag in taboo_tags:
            if tag not in tags:
                tags.append(tag)
            if len(tags) == 5:
                break
        while len(tags) < 3:
            tags.append("focus_team")
        return tags[:5]

    def _taboo_to_tags(self, taboo: str) -> List[str]:
        if not taboo:
            return ["no_topics"]
        chunks = re.split(r'[,;\/\\\s]+', taboo.lower())
        tags: List[str] = []
        for chunk in chunks:
            slug = self._slugify_tag(chunk)
            if slug and slug not in tags:
                tags.append(f"no_{slug}")
            if len(tags) >= 3:
                break
        return tags or ["no_topics"]

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

    def _select_candidates(self, style: str, tone: str, tags: List[str]) -> List[Dict[str, object]]:
        scored: List[tuple[int, Dict[str, object]]] = []
        for candidate in CANDIDATE_LIBRARY:
            score = 0
            if style in candidate.get("style_focus", []):
                score += 3
            if tone in candidate.get("tone_bias", []):
                score += 2
            member_tags = candidate.get("member", {}).get("tags", [])  # type: ignore[union-attr]
            if any(tag in member_tags for tag in tags):
                score += 1
            scored.append((score, candidate))

        scored.sort(key=lambda item: (-item[0], item[1]["id"]))
        return [item[1] for item in scored[:5]]

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

