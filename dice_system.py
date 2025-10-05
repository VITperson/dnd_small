#!/usr/bin/env python3
"""
Модуль для работы с бросками костей в D&D
"""

import random
import re
from typing import Dict, List, Tuple, Optional

class DiceRoller:
    """Класс для бросков костей D&D"""
    
    def __init__(self):
        self.dice_types = {
            'd4': 4, 'd6': 6, 'd8': 8, 'd10': 10, 
            'd12': 12, 'd20': 20, 'd100': 100
        }
    
    def roll_dice(self, dice_string: str) -> Dict:
        """
        Бросает кости по строке формата '2d6+3' или 'd20'
        Возвращает словарь с результатами
        """
        try:
            # Парсим строку броска
            count, sides, modifier = self._parse_dice_string(dice_string)
            
            # Бросаем кости
            rolls = [random.randint(1, sides) for _ in range(count)]
            total = sum(rolls) + modifier
            
            return {
                'dice_string': dice_string,
                'count': count,
                'sides': sides,
                'modifier': modifier,
                'rolls': rolls,
                'total': total,
                'is_critical': self._check_critical(rolls, sides),
                'is_fumble': self._check_fumble(rolls, sides)
            }
        except Exception as e:
            return {
                'dice_string': dice_string,
                'error': str(e),
                'total': 0
            }
    
    def _parse_dice_string(self, dice_string: str) -> Tuple[int, int, int]:
        """Парсит строку броска костей"""
        # Убираем пробелы
        dice_string = dice_string.replace(' ', '')
        
        # Проверяем формат d20, d6 и т.д.
        if dice_string.startswith('d'):
            count = 1
            remaining = dice_string[1:]
        else:
            # Ищем количество костей
            match = re.match(r'^(\d+)d', dice_string)
            if not match:
                raise ValueError(f"Неверный формат броска: {dice_string}")
            count = int(match.group(1))
            remaining = dice_string[match.end():]
        
        # Ищем тип кости
        match = re.match(r'^(\d+)', remaining)
        if not match:
            raise ValueError(f"Неверный формат броска: {dice_string}")
        sides = int(match.group(1))
        
        # Проверяем, что это валидный тип кости
        if f'd{sides}' not in self.dice_types:
            raise ValueError(f"Неподдерживаемый тип кости: d{sides}")
        
        # Ищем модификатор
        modifier = 0
        remaining = remaining[match.end():]
        
        if remaining:
            if remaining.startswith('+'):
                modifier = int(remaining[1:])
            elif remaining.startswith('-'):
                modifier = -int(remaining[1:])
            else:
                raise ValueError(f"Неверный формат модификатора: {remaining}")
        
        return count, sides, modifier
    
    def _check_critical(self, rolls: List[int], sides: int) -> bool:
        """Проверяет критический удар (20 на d20)"""
        return sides == 20 and 20 in rolls
    
    def _check_fumble(self, rolls: List[int], sides: int) -> bool:
        """Проверяет критический промах (1 на d20)"""
        return sides == 20 and 1 in rolls
    
    def roll_ability_check(self, ability_modifier: int = 0, advantage: bool = False, disadvantage: bool = False) -> Dict:
        """Бросает проверку характеристики (d20)"""
        if advantage and disadvantage:
            # Преимущество и недостаток отменяют друг друга
            advantage = disadvantage = False
        
        if advantage:
            roll1 = self.roll_dice('d20')
            roll2 = self.roll_dice('d20')
            if roll1['total'] > roll2['total']:
                result = roll1
            else:
                result = roll2
            result['advantage'] = True
        elif disadvantage:
            roll1 = self.roll_dice('d20')
            roll2 = self.roll_dice('d20')
            if roll1['total'] < roll2['total']:
                result = roll1
            else:
                result = roll2
            result['disadvantage'] = True
        else:
            result = self.roll_dice('d20')
        
        # Добавляем модификатор характеристики
        result['total'] += ability_modifier
        result['ability_modifier'] = ability_modifier
        
        return result
    
    def roll_attack(self, attack_bonus: int = 0) -> Dict:
        """Бросает атаку"""
        result = self.roll_dice('d20')
        result['total'] += attack_bonus
        result['attack_bonus'] = attack_bonus
        return result
    
    def roll_damage(self, damage_dice: str, damage_bonus: int = 0) -> Dict:
        """Бросает урон"""
        result = self.roll_dice(damage_dice)
        result['total'] += damage_bonus
        result['damage_bonus'] = damage_bonus
        return result
    
    def roll_initiative(self, dex_modifier: int = 0) -> Dict:
        """Бросает инициативу"""
        result = self.roll_dice('d20')
        result['total'] += dex_modifier
        result['dex_modifier'] = dex_modifier
        return result
    
    def format_roll_result(self, result: Dict) -> str:
        """Форматирует результат броска для отображения"""
        if 'error' in result:
            return f"❌ Ошибка броска: {result['error']}"
        
        dice_str = result['dice_string']
        total = result['total']
        
        # Формируем детали броска
        details = []
        if 'rolls' in result:
            rolls_str = ', '.join(map(str, result['rolls']))
            details.append(f"Бросок: [{rolls_str}]")
        
        if 'modifier' in result and result['modifier'] != 0:
            mod_str = f"+{result['modifier']}" if result['modifier'] > 0 else str(result['modifier'])
            details.append(f"Модификатор: {mod_str}")
        
        if 'ability_modifier' in result and result['ability_modifier'] != 0:
            mod_str = f"+{result['ability_modifier']}" if result['ability_modifier'] > 0 else str(result['ability_modifier'])
            details.append(f"Характеристика: {mod_str}")
        
        if 'attack_bonus' in result and result['attack_bonus'] != 0:
            mod_str = f"+{result['attack_bonus']}" if result['attack_bonus'] > 0 else str(result['attack_bonus'])
            details.append(f"Бонус атаки: {mod_str}")
        
        # Проверяем критические результаты
        if result.get('is_critical'):
            details.append("🎯 КРИТИЧЕСКИЙ УДАР!")
        elif result.get('is_fumble'):
            details.append("💥 КРИТИЧЕСКИЙ ПРОМАХ!")
        
        if result.get('advantage'):
            details.append("✨ Преимущество")
        elif result.get('disadvantage'):
            details.append("⚠️ Недостаток")
        
        details_str = " | ".join(details)
        return f"🎲 {dice_str} = {total} ({details_str})"

# Глобальный экземпляр для использования в приложении
dice_roller = DiceRoller()
