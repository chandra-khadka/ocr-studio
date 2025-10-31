import logging
import re
from typing import List

from backend.config import logger


class LanguageDetector:
    """
    A language detection system that provides balanced detection across multiple languages
    using an enhanced statistical approach.
    """

    def __init__(self):
        """Initialize the language detector with statistical language models"""
        logger.info("Initializing language detector with statistical models")

        # Initialize language indicators dictionary for statistical detection
        self._init_language_indicators()
        # Set thresholds for language detection confidence
        self.single_lang_confidence = 65  # Minimum score to consider a language detected
        self.secondary_lang_threshold = 0.75  # Secondary language must be at least this fraction of primary score

    def _init_language_indicators(self):
        """Initialize language indicators for statistical detection with historical markers"""
        # Define indicators for all supported languages with equal detail level
        # Each language has:
        # - Distinctive characters
        # - Common words (including historical forms)
        # - N-grams (character sequences)
        # - Historical markers specific to older forms of the language
        self.language_indicators = {
            "English": {
                "chars": [],  # English uses basic Latin alphabet without special chars
                "words": ['the', 'and', 'of', 'to', 'in', 'a', 'is', 'that', 'for', 'it',
                          'with', 'as', 'be', 'on', 'by', 'at', 'this', 'have', 'from', 'or',
                          'an', 'but', 'not', 'what', 'all', 'were', 'when', 'we', 'there', 'can',
                          'would', 'who', 'you', 'been', 'one', 'their', 'has', 'more', 'if', 'no'],
                "ngrams": ['th', 'he', 'in', 'er', 'an', 're', 'on', 'at', 'en', 'nd', 'ti', 'es', 'or',
                           'ing', 'tion', 'the', 'and', 'tha', 'ent', 'ion'],
                "historical": {
                    "chars": ['þ', 'ȝ', 'æ', 'ſ'],  # Thorn, yogh, ash, long s
                    "words": ['thou', 'thee', 'thy', 'thine', 'hath', 'doth', 'ere', 'whilom', 'betwixt',
                              'ye', 'art', 'wast', 'dost', 'hast', 'shalt', 'mayst', 'verily'],
                    "patterns": ['eth$', '^y[^a-z]', 'ck$', 'aught', 'ought']  # -eth endings, y- prefixes
                }
            },
            "French": {
                "chars": ['é', 'è', 'ê', 'à', 'ç', 'ù', 'â', 'î', 'ô', 'û', 'ë', 'ï', 'ü'],
                "words": ['le', 'la', 'les', 'et', 'en', 'de', 'du', 'des', 'un', 'une', 'ce', 'cette',
                          'ces', 'dans', 'par', 'pour', 'sur', 'qui', 'que', 'quoi', 'où', 'quand', 'comment',
                          'est', 'sont', 'ont', 'nous', 'vous', 'ils', 'elles', 'avec', 'sans', 'mais', 'ou'],
                "ngrams": ['es', 'le', 'de', 'en', 'on', 'nt', 'qu', 'ai', 'an', 'ou', 'ur', 're', 'me',
                           'les', 'ent', 'que', 'des', 'ons', 'ant', 'ion'],
                "historical": {
                    "chars": ['ſ', 'æ', 'œ'],  # Long s and ligatures
                    "words": ['aultre', 'avecq', 'icelluy', 'oncques', 'moult', 'estre', 'mesme', 'ceste',
                              'ledict', 'celuy', 'ceulx', 'aulcun', 'ainſi', 'touſiours', 'eſtre',
                              'eſt', 'meſme', 'felon', 'auec', 'iufques', 'chofe', 'fcience'],
                    "patterns": ['oi[ts]$', 'oi[re]$', 'f[^aeiou]', 'ff', 'ſ', 'auoit', 'eſtoit',
                                 'ſi', 'ſur', 'ſa', 'cy', 'ayant', 'oy', 'uſ', 'auſ']
                },
            },
            "German": {
                "chars": ['ä', 'ö', 'ü', 'ß'],
                "words": ['der', 'die', 'das', 'und', 'in', 'zu', 'den', 'ein', 'eine', 'mit', 'ist', 'von',
                          'des', 'sich', 'auf', 'für', 'als', 'auch', 'werden', 'bei', 'durch', 'aus', 'sind',
                          'nicht', 'nur', 'wurde', 'wie', 'wenn', 'aber', 'noch', 'nach', 'so', 'sein', 'über'],
                "ngrams": ['en', 'er', 'ch', 'de', 'ei', 'in', 'te', 'nd', 'ie', 'ge', 'un', 'sch', 'ich',
                           'den', 'die', 'und', 'der', 'ein', 'ung', 'cht'],
                "historical": {
                    "chars": ['ſ', 'ů', 'ė', 'ÿ'],
                    "words": ['vnnd', 'vnnd', 'vnter', 'vnd', 'seyn', 'thun', 'auff', 'auß', 'deß', 'diß'],
                    "patterns": ['^v[nd]', 'th', 'vnter', 'ſch']
                }
            },
            "Spanish": {
                "chars": ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'ü', '¿', '¡'],
                "words": ['el', 'la', 'los', 'las', 'de', 'en', 'y', 'a', 'que', 'por', 'un', 'una', 'no',
                          'es', 'con', 'para', 'su', 'al', 'se', 'del', 'como', 'más', 'pero', 'lo', 'mi',
                          'si', 'ya', 'todo', 'esta', 'cuando', 'hay', 'muy', 'bien', 'sin', 'así'],
                "ngrams": ['de', 'en', 'os', 'es', 'la', 'ar', 'el', 'er', 'ra', 'as', 'an', 'do', 'or',
                           'que', 'nte', 'los', 'ado', 'con', 'ent', 'ien'],
                "historical": {
                    "chars": ['ſ', 'ç', 'ñ'],
                    "words": ['facer', 'fijo', 'fermoso', 'agora', 'asaz', 'aver', 'caſa', 'deſde', 'eſte',
                              'eſta', 'eſto', 'deſto', 'deſta', 'eſſo', 'muger', 'dixo', 'fazer'],
                    "patterns": ['^f[aei]', 'ſſ', 'ſc', '^deſ', 'xo$', 'xe$']
                },
            },
            "Italian": {
                "chars": ['à', 'è', 'é', 'ì', 'í', 'ò', 'ó', 'ù', 'ú'],
                "words": ['il', 'la', 'i', 'le', 'e', 'di', 'a', 'in', 'che', 'non', 'per', 'con', 'un',
                          'una', 'del', 'della', 'è', 'sono', 'da', 'si', 'come', 'anche', 'più', 'ma', 'ci',
                          'se', 'ha', 'mi', 'lo', 'ti', 'al', 'tu', 'questo', 'questi'],
                "ngrams": ['di', 'la', 'er', 'to', 're', 'co', 'de', 'in', 'ra', 'on', 'li', 'no', 'ri',
                           'che', 'ent', 'con', 'per', 'ion', 'ato', 'lla']
            },
            "Portuguese": {
                "chars": ['á', 'â', 'ã', 'à', 'é', 'ê', 'í', 'ó', 'ô', 'õ', 'ú', 'ç'],
                "words": ['o', 'a', 'os', 'as', 'de', 'em', 'e', 'do', 'da', 'dos', 'das', 'no', 'na',
                          'para', 'que', 'um', 'uma', 'por', 'com', 'se', 'não', 'mais', 'como', 'mas',
                          'você', 'eu', 'este', 'isso', 'ele', 'seu', 'sua', 'ou', 'já', 'me'],
                "ngrams": ['de', 'os', 'em', 'ar', 'es', 'ra', 'do', 'da', 'en', 'co', 'nt', 'ad', 'to',
                           'que', 'nto', 'ent', 'com', 'ção', 'ado', 'ment']
            },
            "Dutch": {
                "chars": ['ë', 'ï', 'ö', 'ü', 'é', 'è', 'ê', 'ç', 'á', 'à', 'ä', 'ó', 'ô', 'ú', 'ù', 'û', 'ij'],
                "words": ['de', 'het', 'een', 'en', 'van', 'in', 'is', 'dat', 'op', 'te', 'zijn', 'met',
                          'voor', 'niet', 'aan', 'er', 'die', 'maar', 'dan', 'ik', 'je', 'hij', 'zij', 'we',
                          'kunnen', 'wordt', 'nog', 'door', 'over', 'als', 'uit', 'bij', 'om', 'ook'],
                "ngrams": ['en', 'de', 'er', 'ee', 'ge', 'an', 'aa', 'in', 'te', 'et', 'ng', 'ee', 'or',
                           'van', 'het', 'een', 'ing', 'ver', 'den', 'sch']
            },
            "Russian": {
                # Russian (Cyrillic alphabet) characters
                "chars": ['а', 'б', 'в', 'г', 'д', 'е', 'ё', 'ж', 'з', 'и', 'й', 'к', 'л', 'м', 'н', 'о', 'п',
                          'р', 'с', 'т', 'у', 'ф', 'х', 'ц', 'ч', 'ш', 'щ', 'ъ', 'ы', 'ь', 'э', 'ю', 'я'],
                "words": ['и', 'в', 'не', 'на', 'что', 'я', 'с', 'а', 'то', 'он', 'как', 'этот', 'по',
                          'но', 'из', 'к', 'у', 'за', 'вы', 'все', 'так', 'же', 'от', 'для', 'о', 'его',
                          'мы', 'было', 'она', 'бы', 'мне', 'еще', 'есть', 'быть', 'был'],
                "ngrams": ['о', 'е', 'а', 'н', 'и', 'т', 'р', 'с', 'в', 'л', 'к', 'м', 'д',
                           'ст', 'но', 'то', 'ни', 'на', 'по', 'ет']
            },
            "Chinese": {
                "chars": ['的', '是', '不', '了', '在', '和', '有', '我', '们', '人', '这', '上', '中',
                          '个', '大', '来', '到', '国', '时', '要', '地', '出', '会', '可', '也', '就',
                          '年', '生', '对', '能', '自', '那', '都', '得', '说', '过', '子', '家', '后', '多'],
                # Chinese doesn't have "words" in the same way as alphabetic languages
                "words": ['的', '是', '不', '了', '在', '和', '有', '我', '们', '人', '这', '上', '中',
                          '个', '大', '来', '到', '国', '时', '要', '地', '出', '会', '可', '也', '就'],
                "ngrams": ['的', '是', '不', '了', '在', '我', '有', '和', '人', '这', '中', '大', '来', '上',
                           '国', '个', '到', '说', '们', '为']
            },
            "Japanese": {
                # A mix of hiragana, katakana, and common kanji
                "chars": ['あ', 'い', 'う', 'え', 'お', 'か', 'き', 'く', 'け', 'こ', 'さ', 'し', 'す', 'せ', 'そ',
                          'ア', 'イ', 'ウ', 'エ', 'オ', 'カ', 'キ', 'ク', 'ケ', 'コ', 'サ', 'シ', 'ス', 'セ', 'ソ',
                          '日', '本', '人', '大', '小', '中', '山', '川', '田', '子', '女', '男', '月', '火', '水'],
                "words": ['は', 'を', 'に', 'の', 'が', 'で', 'へ', 'から', 'より', 'まで', 'だ', 'です', 'した',
                          'ます', 'ません', 'です', 'これ', 'それ', 'あれ', 'この', 'その', 'あの', 'わたし'],
                "ngrams": ['の', 'は', 'た', 'が', 'を', 'に', 'て', 'で', 'と', 'し', 'か', 'ま', 'こ', 'い',
                           'する', 'いる', 'れる', 'なる', 'れて', 'した']
            },
            "Korean": {
                "chars": ['가', '나', '다', '라', '마', '바', '사', '아', '자', '차', '카', '타', '파', '하',
                          '그', '는', '을', '이', '에', '에서', '로', '으로', '와', '과', '또는', '하지만'],
                "words": ['이', '그', '저', '나', '너', '우리', '그들', '이것', '그것', '저것', '은', '는',
                          '이', '가', '을', '를', '에', '에서', '으로', '로', '와', '과', '의', '하다', '되다'],
                "ngrams": ['이', '다', '는', '에', '하', '고', '지', '서', '의', '가', '을', '로', '을', '으',
                           '니다', '습니', '하는', '이다', '에서', '하고']
            },
            "Arabic": {
                "chars": ['ا', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'س', 'ش', 'ص', 'ض',
                          'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي', 'ء', 'ة', 'ى'],
                "words": ['في', 'من', 'على', 'إلى', 'هذا', 'هذه', 'ذلك', 'تلك', 'هو', 'هي', 'هم', 'أنا',
                          'أنت', 'نحن', 'كان', 'كانت', 'يكون', 'لا', 'لم', 'ما', 'أن', 'و', 'أو', 'ثم', 'بعد'],
                "ngrams": ['ال', 'ان', 'في', 'من', 'ون', 'ين', 'ات', 'ار', 'ور', 'ما', 'لا', 'ها', 'ان',
                           'الم', 'لان', 'علا', 'الح', 'الس', 'الع', 'الت']
            },
            "Hindi": {
                "chars": ['अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ए', 'ऐ', 'ओ', 'औ', 'क', 'ख', 'ग', 'घ', 'ङ',
                          'च', 'छ', 'ज', 'झ', 'ञ', 'ट', 'ठ', 'ड', 'ढ', 'ण', 'त', 'थ', 'द', 'ध', 'न',
                          'प', 'फ', 'ब', 'भ', 'म', 'य', 'र', 'ल', 'व', 'श', 'ष', 'स', 'ह', 'ा', 'ि', 'ी',
                          'ु', 'ू', 'े', 'ै', 'ो', 'ौ', '्', 'ं', 'ः', "टे"],
                "words": ['और', 'का', 'के', 'की', 'एक', 'में', 'है', 'यह', 'हैं', 'से', 'को', 'पर', 'इस',
                          'हो', 'गया', 'कर', 'मैं', 'या', 'हुआ', 'था', 'वह', 'अपने', 'सकता', 'ने', 'बहुत'],
                "ngrams": ['का', 'के', 'की', 'है', 'ने', 'से', 'मे', 'को', 'पर', 'हा', 'रा', 'ता', 'या',
                           'ार', 'ान', 'कार', 'राज', 'ारा', 'जाए', 'ेजा']
            },
            "Latin": {
                "chars": [],  # Latin uses basic Latin alphabet
                "words": ['et', 'in', 'ad', 'est', 'sunt', 'non', 'cum', 'sed', 'qui', 'quod', 'ut', 'si',
                          'nec', 'ex', 'per', 'quam', 'pro', 'iam', 'hoc', 'aut', 'esse', 'enim', 'de',
                          'atque', 'ac', 'ante', 'post', 'sub', 'ab'],
                "ngrams": ['us', 'is', 'um', 'er', 'it', 'nt', 'am', 'em', 're', 'at', 'ti', 'es', 'ur',
                           'tur', 'que', 'ere', 'ent', 'ius', 'rum', 'tus']
            },
            "Greek": {
                "chars": ['α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'π',
                          'ρ', 'σ', 'ς', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω', 'ά', 'έ', 'ή', 'ί', 'ό', 'ύ', 'ώ'],
                "words": ['και', 'του', 'της', 'των', 'στο', 'στη', 'με', 'από', 'για', 'είναι', 'να',
                          'ότι', 'δεν', 'στον', 'μια', 'που', 'ένα', 'έχει', 'θα', 'το', 'ο', 'η', 'τον'],
                "ngrams": ['αι', 'τα', 'ου', 'τη', 'οι', 'το', 'ης', 'αν', 'ος', 'ον', 'ις', 'ει', 'ερ',
                           'και', 'την', 'τον', 'ους', 'νου', 'εντ', 'μεν']
            }
        }

    def detect_languages(self, text: str, filename: str = None, current_languages: List[str] = None) -> List[str]:
        """
        Detect languages in text using an enhanced statistical approach
        
        Args:
            text: Text to analyze
            filename: Optional filename to provide additional context
            current_languages: Optional list of languages already detected
            
        Returns:
            List of detected languages
        """
        if not text or len(text.strip()) < 10:
            return current_languages if current_languages else ["English"]

        # If we already have detected languages, use them
        if current_languages and len(current_languages) > 0:
            logger.info(f"Using already detected languages: {current_languages}")
            return current_languages

        # Use enhanced statistical detection
        detected_languages = self._detect_statistically(text, filename)
        logger.info(f"Statistical language detection results: {detected_languages}")
        return detected_languages

    def _detect_statistically(self, text: str, filename: str = None) -> List[str]:
        """
        Detect languages using enhanced statistical analysis with historical language indicators
        
        Args:
            text: Text to analyze
            filename: Optional filename for additional context
            
        Returns:
            List of detected languages
        """
        logger = logging.getLogger("language_detector")

        # Normalize text to lowercase for consistent analysis
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)  # Extract words

        # Score each language based on characters, words, n-grams, and historical markers
        language_scores = {}
        historical_bonus = {}

        # PHASE 1: Special character analysis
        # Count special characters for each language
        special_char_counts = {}
        total_special_chars = 0

        for language, indicators in self.language_indicators.items():
            chars = indicators["chars"]
            count = 0
            for char in chars:
                if char in text_lower:
                    count += text_lower.count(char)
            special_char_counts[language] = count
            total_special_chars += count

        # Normalize character scores (0-30 points)
        for language, count in special_char_counts.items():
            if total_special_chars > 0:
                # Scale score to 0-30 range (reduced from 35 to make room for historical)
                normalized_score = (count / total_special_chars) * 30
                language_scores[language] = normalized_score
            else:
                language_scores[language] = 0

        # PHASE 2: Word analysis (0-30 points)
        # Count common words for each language
        for language, indicators in self.language_indicators.items():
            word_list = indicators["words"]
            word_matches = sum(1 for word in words if word in word_list)

            # Normalize word score based on text length and word list size
            word_score_factor = min(1.0, word_matches / (len(words) * 0.1))  # Max 1.0 if 10% match
            language_scores[language] = language_scores.get(language, 0) + (word_score_factor * 30)

        # PHASE 3: N-gram analysis (0-20 points)
        for language, indicators in self.language_indicators.items():
            ngram_list = indicators["ngrams"]
            ngram_matches = 0

            # Count ngram occurrences
            for ngram in ngram_list:
                ngram_matches += text_lower.count(ngram)

            # Normalize ngram score based on text length
            if len(text_lower) > 0:
                ngram_score_factor = min(1.0, ngram_matches / (len(text_lower) * 0.05))  # Max 1.0 if 5% match
                language_scores[language] = language_scores.get(language, 0) + (ngram_score_factor * 20)

        # PHASE 4: Historical language markers (0-20 points)
        for language, indicators in self.language_indicators.items():
            if "historical" in indicators:
                historical_indicators = indicators["historical"]
                historical_score = 0

                # Check for historical chars
                if "chars" in historical_indicators:
                    for char in historical_indicators["chars"]:
                        if char in text_lower:
                            historical_score += text_lower.count(char) * 0.5

                # Check for historical words
                if "words" in historical_indicators:
                    hist_words = historical_indicators["words"]
                    hist_word_matches = sum(1 for word in words if word in hist_words)
                    if hist_word_matches > 0:
                        # Historical words are strong indicators
                        historical_score += min(10, hist_word_matches * 2)

                # Check for historical patterns
                if "patterns" in historical_indicators:
                    for pattern in historical_indicators["patterns"]:
                        matches = len(re.findall(pattern, text_lower))
                        if matches > 0:
                            historical_score += min(5, matches * 0.5)

                # Cap historical score at 20 points
                historical_score = min(20, historical_score)
                historical_bonus[language] = historical_score

                # Apply historical bonus
                language_scores[language] += historical_score

                # Apply language-specific exclusivity multiplier if present
                if "exclusivity" in indicators:
                    exclusivity = indicators["exclusivity"]
                    language_scores[language] *= exclusivity
                    logger.info(f"Applied exclusivity multiplier {exclusivity} to {language}")

        # Print historical bonus for debugging
        for language, bonus in historical_bonus.items():
            if bonus > 0:
                logger.info(f"Historical language bonus for {language}: {bonus} points")

        # Final language selection with more stringent criteria
        # Get languages with scores above threshold
        threshold = self.single_lang_confidence  # Higher minimum score
        candidates = [(lang, score) for lang, score in language_scores.items() if score >= threshold]
        candidates.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Language candidates: {candidates}")

        # If we have candidate languages, return top 1-2 with higher threshold for secondary
        if candidates:
            # Always take top language
            result = [candidates[0][0]]

            # Add second language only if it's significantly strong compared to primary
            # and doesn't have a historical/exclusivity conflict
            if len(candidates) > 1:
                primary_lang = candidates[0][0]
                secondary_lang = candidates[1][0]
                primary_score = candidates[0][1]
                secondary_score = candidates[1][1]

                # Only add secondary if it meets threshold and doesn't conflict
                ratio = secondary_score / primary_score

                # Check for French and Spanish conflict (historical French often gets misidentified)
                historical_conflict = False
                if (primary_lang == "French" and secondary_lang == "Spanish" and
                        historical_bonus.get("French", 0) > 5):
                    historical_conflict = True
                    logger.info("Historical French markers detected, suppressing Spanish detection")

                if ratio >= self.secondary_lang_threshold and not historical_conflict:
                    result.append(secondary_lang)
                    logger.info(f"Added secondary language {secondary_lang} (score ratio: {ratio:.2f})")
                else:
                    logger.info(f"Rejected secondary language {secondary_lang} (score ratio: {ratio:.2f})")

            return result
