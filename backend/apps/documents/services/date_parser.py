"""
Date Parser Service for Spanish Legal Documents

Converts Spanish text dates to Python date objects.
Handles various formats found in Peruvian legal documents.
"""
import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Diccionarios de conversión
MONTHS_ES = {
    'enero': 1, 'ene': 1,
    'febrero': 2, 'feb': 2,
    'marzo': 3, 'mar': 3,
    'abril': 4, 'abr': 4,
    'mayo': 5, 'may': 5,
    'junio': 6, 'jun': 6,
    'julio': 7, 'jul': 7,
    'agosto': 8, 'ago': 8,
    'septiembre': 9, 'setiembre': 9, 'sep': 9, 'set': 9,
    'octubre': 10, 'oct': 10,
    'noviembre': 11, 'nov': 11,
    'diciembre': 12, 'dic': 12
}

NUMBERS_ES = {
    'un': 1, 'uno': 1, 'una': 1, 'primero': 1, 'primer': 1, 'primera': 1,
    'dos': 2,
    'tres': 3,
    'cuatro': 4,
    'cinco': 5,
    'seis': 6,
    'siete': 7,
    'ocho': 8,
    'nueve': 9,
    'diez': 10,
    'once': 11,
    'doce': 12,
    'trece': 13,
    'catorce': 14,
    'quince': 15,
    'dieciséis': 16, 'dieciseis': 16,
    'diecisiete': 17,
    'dieciocho': 18,
    'diecinueve': 19,
    'veinte': 20,
    'veintiuno': 21, 'veintiun': 21, 'veintiuna': 21,
    'veintidós': 22, 'veintidos': 22,
    'veintitrés': 23, 'veintitres': 23,
    'veinticuatro': 24,
    'veinticinco': 25,
    'veintiséis': 26, 'veintiseis': 26,
    'veintisiete': 27,
    'veintiocho': 28,
    'veintinueve': 29,
    'treinta': 30,
    'treinta y uno': 31, 'treinta y un': 31, 'treinta y una': 31
}

# Números compuestos
def parse_compound_number(text: str) -> Optional[int]:
    """Parse compound numbers like 'treinta y uno' or 'veinte y tres'"""
    text = text.strip().lower()
    
    # Directo
    if text in NUMBERS_ES:
        return NUMBERS_ES[text]
    
    # Compuesto: "treinta y uno"
    match = re.search(r'(treinta|veinte)\s*y\s*(un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve)', text)
    if match:
        base = 30 if 'treinta' in match.group(1) else 20
        unit_text = match.group(2)
        unit = NUMBERS_ES.get(unit_text, 0)
        return base + unit
    
    return None


def text_to_number(text: str) -> Optional[int]:
    """Convert Spanish text number to integer (1-31 for days)"""
    text = text.strip().lower()
    
    # Primero intenta directo
    if text in NUMBERS_ES:
        return NUMBERS_ES[text]
    
    # Intenta compuesto
    compound = parse_compound_number(text)
    if compound:
        return compound
    
    # Si es numérico
    if text.isdigit():
        return int(text)
    
    return None


class SpanishDateParser:
    """Parser for Spanish text dates in legal documents"""
    
    # Patrones de fecha
    DATE_PATTERNS = [
        # Formato con números directos: "10 de noviembre de 2023"
        r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
        
        # Formato con números y "del": "10 del noviembre del 2023"
        r'(\d{1,2})\s+de\s+(\w+)\s+del\s+(\d{4})',
        
        # "ocho de enero del año dos mil veinticinco"
        # "primero de abril del dos mil veinticinco"
        r'(\w+(?:\s+y\s+\w+)?)\s+de\s+(\w+)\s+del?\s+(?:año\s+)?(\w+\s+mil\s+\w+(?:\s+y\s+\w+)?)',
        
        # "veintisiete de diciembre de dos mil veinticuatro"
        r'(\w+(?:\s+y\s+\w+)?)\s+de\s+(\w+)\s+de\s+(\w+\s+mil\s+\w+(?:\s+y\s+\w+)?)',
        
        # "dos mil veinticinco, septiembre dos"
        r'(\w+\s+mil\s+\w+(?:\s+y\s+\w+)?),\s*(\w+)\s+(\w+)',
        
        # "dos de junio del dos mil veinticinco"
        r'(\w+)\s+de\s+(\w+)\s+del?\s+(\w+\s+mil\s+\w+(?:\s+y\s+\w+)?)',
        
        # Formato numérico: "08/01/2025" o "08-01-2025"
        r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})',
        
        # "2025-01-08" (ISO)
        r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
    ]
    
    def parse(self, text: str) -> Optional[datetime]:
        """
        Parse Spanish date text to datetime object.
        
        Args:
            text: Date text in Spanish
            
        Returns:
            datetime object or None if parsing fails
        """
        if not text:
            return None
        
        text = text.strip().lower()
        text = text.replace('.-', '').replace('.', '').replace('-', ' ')
        
        logger.debug(f"Attempting to parse date: {text}")
        
        # Intenta cada patrón
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result = self._parse_match(match, pattern)
                    if result:
                        logger.info(f"Successfully parsed date: {text} -> {result.date()}")
                        return result
                except Exception as e:
                    logger.debug(f"Failed to parse match with pattern {pattern}: {e}")
                    continue
        
        logger.warning(f"Could not parse date: {text}")
        return None
    
    def _parse_match(self, match, pattern: str) -> Optional[datetime]:
        """Parse a regex match into a datetime"""
        groups = match.groups()
        
        # Formato numérico DD/MM/YYYY
        if r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})' in pattern:
            day = int(groups[0])
            month = int(groups[1])
            year = int(groups[2])
            return datetime(year, month, day)
        
        # Formato ISO YYYY-MM-DD
        if r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})' in pattern:
            year = int(groups[0])
            month = int(groups[1])
            day = int(groups[2])
            return datetime(year, month, day)
        
        # Formato con números directos: "10 de noviembre de 2023"
        # Pattern: r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
        # Pattern: r'(\d{1,2})\s+de\s+(\w+)\s+del\s+(\d{4})'
        if groups[0].isdigit() and groups[2].isdigit() and len(groups[2]) == 4:
            day = int(groups[0])
            month_text = groups[1]
            year = int(groups[2])
            
            # Parsear mes
            month = MONTHS_ES.get(month_text.strip().lower())
            if not month:
                return None
            
            return datetime(year, month, day)
        
        # Formato "dos mil veinticinco, septiembre dos"
        if 'mil' in groups[0]:
            year_text = groups[0]
            month_text = groups[1]
            day_text = groups[2]
        else:
            # Formato normal: día de mes del año
            day_text = groups[0]
            month_text = groups[1]
            year_text = groups[2]
        
        # Parsear día
        day = text_to_number(day_text)
        if not day or day < 1 or day > 31:
            return None
        
        # Parsear mes
        month = MONTHS_ES.get(month_text.strip())
        if not month:
            return None
        
        # Parsear año
        year = self._parse_year(year_text)
        if not year:
            return None
        
        return datetime(year, month, day)
    
    def _parse_year(self, year_text: str) -> Optional[int]:
        """Parse year from Spanish text"""
        year_text = year_text.strip().lower()
        
        # Si es numérico directo
        if year_text.isdigit():
            return int(year_text)
        
        # Parsear "dos mil veinticinco"
        # Patrón: (dos|un) mil (número)
        match = re.search(r'(dos|un)\s+mil\s+(\w+(?:\s+y\s+\w+)?)', year_text)
        if not match:
            return None
        
        millennium = 2000 if match.group(1) == 'dos' else 1000
        remainder_text = match.group(2).strip()
        
        # Parsear el resto
        remainder = text_to_number(remainder_text)
        if remainder is None:
            # Intenta con números más complejos
            remainder = self._parse_complex_year_remainder(remainder_text)
        
        if remainder is None:
            return None
        
        return millennium + remainder
    
    def _parse_complex_year_remainder(self, text: str) -> Optional[int]:
        """Parse complex year remainders like 'veinte y cuatro' -> 24"""
        # Ya cubierto por parse_compound_number
        return parse_compound_number(text)


# Instancia global
date_parser = SpanishDateParser()
