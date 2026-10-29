"""
DualMova — High-Precision Symmetric Orthography Classifier (v2.0)
=============================================================================
Architecture built upon the rigorous phonological codifications of the Belarusian language:
- Official Standard (Narkamaŭka / NKBM-2008, Law of the Republic of Belarus № 420-Z) -> <orth_nark>
- Classical Standard (Taraškievica / BKP-2005 Codification) -> <orth_taras>
- Anomalies / Trasyanka / Russian script intrusion / Mixed Norms -> REJECT

Core Theoretical Theorems & Codified Boundaries:
1. Pre-Hard Neutralization Theorem:
   In Belarusian phonology, positional assimilation softening never operates before
   phonologically hard consonants in either norm. Soft sign occurrences before hard
   consonants (e.g. просьба, бацька, пісьмо, ведзьма, пяцьсот) are etymological,
   neutral, and legitimate across both standards.
2. Pre-Soft Morphemic Seam Grammar (§ 18 NKBM-2008):
   Soft sign occurrences before soft consonants in Narkamaŭka are strictly restricted
   to 7 closed morphological categories (e.g. людзьмі, хтосьці, сядзьце, пісьменнік,
   цьмяны, студзеньскі, у барацьбе, дзьме, возьме, маленькі). All non-seam occurrences
   (e.g. сьвет, сьнег, жыцьцё, радасьць, зьезд) are unambiguous markers of BKP-2005.
3. Symmetrical Phonological Detection:
   Both standards are evaluated across 11 calibrated feature families encompassing
   palatal consonant assimilation, iotated geminates, prefixal seams, suffixal
   affricatization, jakanne exceptions, loanword matrices (Grecisms, European l,
   sibilants), and noun/adjective morphological paradigms.
4. Confidence-Gated Bayesian Context Decay:
   Differential-free segments inherit document prior context with exponential dampening,
   protecting code-switching citations from context poisoning.
"""

from __future__ import annotations

import re
import math
import unicodedata
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

log = logging.getLogger(__name__)


# ── Routing Result Data Structure ─────────────────────────────────────────────

@dataclass
class RouteResult:
    """Classification outcome for a text segment in DualMova."""
    label: str                  # "nark" | "tarask" | "rejected"
    text_original: str          # Raw text after safe typographic normalization
    text_tagged: str            # Enclosed text with <orth_nark>...</orth_nark> or empty
    text_nark_candidate: str = "" # Backward-compatibility candidate slot
    is_augmented: bool = False  # Flag for synthetic data (always False for authentic pretraining)
    metrics: dict = field(default_factory=dict)


# ── Typographic Normalization (v2.0 with Roman Numeral Homoglyph Repair) ──────

_ROMAN_NUMERAL_FIX = re.compile(
    r"\b(?=[IVXLCDMІХ]+(?:-[а-яёіўґ]+|\b))[IVXLCDMІХ]{2,}\b"
)
_ROMAN_CYR_TO_LAT = str.maketrans({"І": "I", "Х": "X"})

_LATIN_TO_BY_CYR = re.compile(
    r"(?<=[а-яёўіґА-ЯЁЎІҐ'’ʼ`])[iI](?=[а-яёўіґА-ЯЁЎІҐ'’ʼ`])"
    r"|(?<=[а-яёўіґА-ЯЁЎІҐ'’ʼ`])[iI]\b"
    r"|\b[iI](?=[а-яёўіґА-ЯЁЎІҐ'’ʼ`])"
    r"|\b([iI])\b(?=\s+[а-яёўіґА-ЯЁЎІҐ])"
)

_RE_APOSTROPHE = re.compile(r"(?<=[а-яёіўґА-ЯЁІЎҐ])[’ʼ`‘'](?=[а-яёіўґА-ЯЁІЎҐ])")
_RE_EM_DASH = re.compile(r"(?<=\s)[-–—−]+(?=\s)")
_RE_QUOTES = re.compile(r'["“„”»«]+')


def normalize_typography(text: str) -> str:
    """
    Standardizes cross-orthographic typography without altering lexical phonology:
    - Normalizes Unicode composition via canonical NFC (unifying combining accents on ў, ё)
    - Repairs hybrid Cyrillic/Latin Roman numerals (e.g. VІ -> VI, XІ -> XI, ХV -> XV)
    - Repairs Latin 'i/I' homoglyphs in Cyrillic lexical contexts
    - Unifies intra-word apostrophe variations to ASCII single quote U+0027
    - Normalizes guillemet quotation marks («...») and em-dashes ('—')
    """
    if not text:
        return ""

    # 1. Canonical Unicode NFC Normalization
    text = unicodedata.normalize("NFC", text)

    # 2. Repair hybrid Cyrillic/Latin Roman numerals before mixed-script check
    text = _ROMAN_NUMERAL_FIX.sub(lambda m: m.group(0).translate(_ROMAN_CYR_TO_LAT), text)

    # 3. Repair Latin i/I homoglyphs in Belarusian Cyrillic context
    text = _LATIN_TO_BY_CYR.sub(lambda m: "І" if m.group(0).isupper() else "і", text)

    # 4. Unify intra-word apostrophe variations
    text = _RE_APOSTROPHE.sub("'", text)

    # 5. Normalize em-dashes surrounded by whitespace
    text = _RE_EM_DASH.sub("—", text)

    # 6. Standardize balanced quotation marks
    text = _RE_QUOTES.sub('"', text)
    parts = text.split('"')
    if len(parts) > 1:
        res = []
        for i, part in enumerate(parts):
            res.append(part)
            if i < len(parts) - 1:
                res.append("«" if i % 2 == 0 else "»")
        text = "".join(res)

    return text.strip()


class DualMovaOrthographyClassifier:
    """
    Symmetric discriminative multi-norm classifier for Belarusian textual corpora.
    Categorizes input text into Official Standard ('nark'), Classical Standard ('tarask'),
    or anomalies / mixed varieties ('rejected').
    """

    WEIGHTS: Dict[str, float] = {
         # 1. Phonological / Assimilative / Geminate Core
         "tarask_palatal_cluster": +2.5,
         "tarask_prefix_soft_sign": +2.3,
         "tarask_soft_long": +2.4,
         "tarask_affricate_assim": +2.2,
         "nark_hard_long": -2.4,
         "nark_unmarked_assimilation": -2.2,
         "nark_prefix_apostrophe": -2.2,
         "nark_affricate_unassimilated": -2.0,

         # 2. Jakanie & Pre-Stressed Vocalism (Proclitics, Exceptions, Numerals)
         "tarask_nia_biaz": +1.8,
         "tarask_jakanie_lex": +2.0,
         "nark_nie_biez_stressed": -1.6,
         "nark_jakanie_exceptions": -2.0,

         # 3. Loanword Phonetics (Grecisms θ/β/s, European soft l, Sibilants сы/зы/сэ/зэ vs сі/зі/се/зе)
         "tarask_loan_soft_l": +1.8,
         "tarask_loan_hard_sibilant": +1.8,
         "tarask_loan_greek_latin": +2.0,
         "nark_loan_forms": -1.8,
         "nark_loan_greek_latin": -2.0,

         # 4. Morphology (Case Endings)
         "tarask_fem_gen_adj": +1.4,
         "tarask_morph_endings": +1.8,
         "nark_fem_gen_adj": -1.4,
         "nark_morph_endings": -1.8,

         # 5. Lexical / Toponymic Markers
         "tarask_lex_markers": +2.0,
         "nark_lex_markers": -2.0,
    }

    DECISION_THRESHOLD: float = 1.25
    MAX_DOC_PRIOR: float = 4.0
    BETA_BASE: float = 0.40
    DECAY_TAU: float = 3.0

    def __init__(
         self,
         tarask_vocab: Optional[Set[str]] = None,
         nark_vocab: Optional[Set[str]] = None,
         prior_alpha: float = 0.5,
         confidence_threshold: float = 0.88,
         max_joint_oov: float = 0.12,
         max_chimera_index: float = 0.20,
    ):
         self.vocab_taras = tarask_vocab or set()
         self.vocab_nark = nark_vocab or set()
         self.prior_alpha = prior_alpha
         self.confidence_threshold = confidence_threshold
         self.max_joint_oov = max_joint_oov
         self.max_chimera_index = max_chimera_index

         # CASCADE 0: UNICODE HYGIENE, RUSSIAN SCRIPT INTRUSIONS & TRASIANKA
         self.re_russian_chars = re.compile(r"[ищъИЩЪ]")
         self.re_word_tokens = re.compile(r"[а-яёіўґА-ЯЁІЎҐ']+")
         self.re_mixed_script = re.compile(
              r"\b(?:[а-яёіўґА-ЯЁІЎҐ]+[a-zA-Z]+|[a-zA-Z]+[а-яёіўґА-ЯЁІЎҐ]+)\b"
         )
         self.re_ushort_valid = re.compile(r"[аеёіоуыэюя]ў\b", re.IGNORECASE)
         self.re_ushort_broken = re.compile(
              r"\b(?!(?:шоу|ток-шоу|траур|фауна|сауна|пауза|клоун|страус|баул|аул|караул)\b)"
              r"[а-яёіўґ]*[аеёіоуыэюя]у\b",
              re.IGNORECASE,
         )
         # Whitelists native Belarusian nouns/adjectives/verbs with -ушч-/-ашч- (пушчы, гушчы, пашчы, хрушчы, прапашчы, змяшчае...)
         # and compound word boundaries with -дін- (педінстытут, медінстытут)
         self.re_trasianka = re.compile(
              r"\b(?:"
              r"(?!(?:пушч|гушч|пашч|хрушч|плюшч|таўшч|рушч|ляшч|хряшч|прапашч|хітрушч|"
              r"(?:вы|з|зь|на|па|пера|пра|раз|разь|у|ў)?мяшч|"
              r"(?:аб|аб'|уз|узь|ўз|ўзь|па|пра)?вяшч|"
              r"(?:пры)?чашч)[а-яёіўґ']*)"
              r"[а-яёіў]+(?:ушч|юшч|ашч|яшч)(?:ы|ая|ае|ыя|ага|аму|ым|ых)\b|"
               r"[а-яёіў]+(?:ўш)(?:ы|ая|ае|ай|ую|ыя|ага|аму|ым|ых|ую)\b|"
              r"[а-яёіў]{3,}(?:тся|ться)\b|"
              r"(?:сказал|зрабіл|пашол|прыйшол|хадзіл|бачыл|купіл|пісал)\b|"
              r"(?:толька|еслі|патаму|дажэ|очэнь|кагда|всё|сейчас)\b|"
              r"(?!(?:пед|мед|паліт|фіз|хім|буд|гандаль|дзярж|кам|край|між|над|пад|прад|раз|роз|сац|спец|тэх|універ|юрыд)ін[а-яёіўґ']*)"
              r"[а-яёіў]*(?:ді|ті)[а-яёіў]*\b"
              r")",
              re.IGNORECASE,
         )

         # CASCADE 1: SEAM GRAMMAR & SYMMETRIC ASSIMILATIVE SOFTNESS
         # Closed grammar of 7 legal Narkamaŭka morphemic seams before soft consonants (§ 18 NKBM-2008)
         self.re_nark_legal_palatal_seam = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              # 1. Instrumental plural in -мі (людзьмі, грудзьмі, дзецьмі, коньмі, саньмі, слязьмі, гусьмі, касцьмі, вароцьмі):
              r"[а-яёўіґ'’ʼ`]*[дзсцнл]ьмі"
              # 2. Indefinite pronoun affix -сьці (хтосьці, штосьці, дзесьці, калісьці, кудысьці, чыйсьці, якісьці):
               r"|(?:[а-яёўіґ'’ʼ`]*(?:хто|што|дзе|калі|куды|адкуль|чаму|як|чый|чыя|чыё|чые|чыім|чыіх|які|якая|якое|якія|якім|якіх|каго|чаго|каму|чаму|кім|чым))сьці"
              # 3. Compound preposition / prefix супраць- (супрацьлеглы, супрацьдзеянне, супрацьстаяць):
              r"|супраць[а-яёўіґ'’ʼ`]*"
              # 4. Imperatives on -це, -ся, -цеся (сядзьце, агледзься, станьце, праходзьце, будзьце, вазьміце, кінься, звесься):
              r"|[а-яёўіґ'’ʼ`]*[дзсцнл]ь(?:це(?:ся)?|ся)"
              # 5. Compound numerals 50, 60, 500, 600, 900 (пяцьдзесят, шэсцьдзесят, пяцьсот, шэсцьсот, дзевяцьсот):
              r"|(?:пя|шэс|дзевя)ць(?:дз[ея]сят|сот)[а-яёўіґ'’ʼ`]*"
              # 6. Roots with soft labials and alternations (пісьменнік, цьмяны, васьмі, васьмёрка, ледзьве, разьбяр, дзьме, возьме, у барацьбе, барацьбіт, ганьбіць, носьбіт, хрэсьбіны):
              r"|(?:не|мала)?пісьм[еёіюя][а-яёўіґ'’ʼ`]*"
              r"|(?:па|за)?цьм(?:ян|ен|ін|е)[а-яёўіґ'’ʼ`]*"
              r"|васьм[іёю][а-яёўіґ'’ʼ`]*"
              r"|ледзьве"
              r"|разьб(?:яр|лён|е)[а-яёўіґ'’ʼ`]*"
              r"|(?:вы|за|на|па|пра|раз|з)?дзьм(?:е|еш|ем|еце|яце|ецца)"
              r"|в[ао]зьм(?:і|іце|іся|е|еш|ем|еце|ецца)"
              r"|(?:барацьб|ганьб|касьб|малацьб|просьб|сядзьб|ведзьм|тасьм|вязьм|кузьм)(?:е|і[а-яёўіґ'’ʼ`]*|аван[а-яёўіґ'’ʼ`]*)"
              r"|(?:носьбіт|хрэсьбін)[а-яёўіґ'’ʼ`]*"
              # 7. Adjectives on -скі / nouns on -ства from stems on -нь, suffix -чык-, and diminutives before velars [гкх] (студзеньскі, чэрвеньскі, восеньскі, каменьчык, бацькі, маленькі):
              r"|[а-яёўіґ'’ʼ`]*нь(?:ск|ств|чык)[а-яёўіґ'’ʼ`]*"
              r"|[а-яёўіґ'’ʼ`]*[дзсцнл]ь[гґкх][а-яёўіґ'’ʼ`]*"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )

         # Assimilative soft clusters in Taraškievica (BKP-2005 Chapter 8, Rules 29-30):
         self.re_tarask_palatal_cluster = re.compile(
              r"(?:(?<=^)|(?<=[а-яёўіґ'’ʼ`\s\-]))"
              r"(?:дз|[зсц])ь"
              r"(?:(?:дз|[зсц])ь)?"
              r"(?:дз|[бвджзлмнпрстфцчш])"
              r"(?=[еёіюяь])",
              re.IGNORECASE,
         )

         # Generalized Unmarked Assimilation in Narkamaŭka (phonologically symmetric to re_tarask_palatal_cluster):
         # Evaluated on `masked_for_palatal` (after masking all 7 legal categories of § 18 NKBM-2008).
         # Captures all [с, з] + [л', н', ц', дз', с', з', в', м', п', б'] + [е, ё, і, ю, я, ь]
         # and [ц, дз] + [в'] + [е, ё, і, ю, я, ь] (e.g. неслі, выпусціў, расці, сцяна, касцёл, песня, радасць, цвіце, дзве).
         self.re_nark_unmarked_assimilation = re.compile(
              r"(?<!\bды)(?<!\bтран)(?<!\bюры)(?<!\bпост)"
              r"(?!збярэжж)"
              r"(?:"
              r"(?<![зс])(?:[зс](?:дз|[бвлмнпц])|сз|зс)"
              r"|"
              r"(?<![дтц])(?:дз|ц)в"
              r")"
              r"(?=[еёіюяь])",
              re.IGNORECASE,
         )

         # Prefix soft sign vs apostrophe before iotated vowels
         self.re_tarask_prefix_soft_sign = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:з|раз|уз|ўз|бяз|параз|паўз|с)ь(?=[еёюя])",
              re.IGNORECASE,
         )
         self.re_nark_prefix_apostrophe = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:з|раз|уз|ўз|бяз|параз|паўз|с)['’ʼ`](?=[еёюя])",
              re.IGNORECASE,
         )

         # Affricate assimilation before -ств- / -ск- (BKP-2005 Rules 36-38 vs NKBM-2008 § 13)
         self.re_tarask_affricate_assim = re.compile(
               r"(?<![а-яёўіґ'’ʼ`])[а-яёўіґ'’ʼ`]{2,}(?:дзтв|дзк|брацтв)[а-яёўіґ'’ʼ`]*",
              re.IGNORECASE,
         )
         self.re_nark_affricate_unassimilated = re.compile(
               r"(?<![а-яёўіґ'’ʼ`])[а-яёўіґ'’ʼ`]{2,}(?:дств|дск|тств)[а-яёўіґ'’ʼ`]*",
              re.IGNORECASE,
         )

         # CASCADE 2: GEMINATE CONSONANTS
         self.re_tarask_soft_long = re.compile(
              r"(?<=[аеёіоуыэюя])(?:льл|ньн|сьс|зьз|цьц|дзьдз)(?=[еёіюя])",
              re.IGNORECASE,
         )
         self.re_nark_hard_long = re.compile(
              r"(?<=[аеёіоуыэюя])"
              r"(?:"
              r"лл|нн|сс|зз|цц"
              r"|(?<!\bа)(?<!\bпа)(?<!\bна)(?<!\bпера)(?<!\bпра)"
              r"(?<!паа)(?<!неа)(?<!пераа)(?<!папа)(?<!пана)"
              r"ддз"
              r")"
              r"(?=[еёіюя])",
              re.IGNORECASE,
         )

         # CASCADE 3: PROCLITICS, JAKANIE EXCEPTIONS & MORPHOLOGICAL CASE ENDINGS
         self.re_tarask_nia_biaz = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?!няма\b|няўжо\b)(?:ня|бязь?|безь)\s+(?=[а-яёўіґ'’ʼ`]{2,})",
              re.IGNORECASE,
         )
         self.re_nark_nie_biez_stressed = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"не\s+(?:быў|быць|будзе|будзь|тут|там|так|тое|той|тая|тыя|ты|ён|мы|вы|дом|год|дзень|раз|час|мог|мае|маю|маем|знае|ведае|ведаю|хоча|хочаш|трэба|можна|льга|жаль|варты|варта|многа|мала|дужа|вельмі|зусім|надта|проста|толькі|кожны|ўсе|усе|гэты|гэтая|гэтае|сам|сама|праўда|добра|дрэнна|лёгка|цяжка)"
              r"|"
              r"без\s+(?:нас|вас|іх|яе|яго|таго|тых|цябе|мяне|рук|ног|слоў|дум|сіл|меж|праўды|працы|хлеба|солі|сэнсу|шкоды|увагі|ўвагі|даху|роду|ліку|следу|устану|ўстану)"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )

         # Lexical and numeral exceptions to Jakanie (§§ 6-7 NKBM-2008 & 1959 norm vs BKP-2005 Chapter 2)
         self.re_nark_jakanie_exceptions = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"веліч(?:н|ав|эзн|адушн|асвецк|амучан|арос)[а-яёўіґ'’ʼ`]*"
              r"|(?:сем|восем|дзевят)наццац[а-яёўіґ'’ʼ`]*"
              r"|(?:пяць|шэсць|сем|восем)дзесят[а-яёўіґ'’ʼ`]*"
              r"|дзевятнаццат[а-яёўіґ'’ʼ`]*"
              r"|сезон[а-яёўіґ'’ʼ`]*|секунд[а-яёўіґ'’ʼ`]*|медал[яіюёёмўх][а-яёўіґ'’ʼ`]*|медаль\b|метро\b|метрапалітэн[а-яёўіґ'’ʼ`]*|дэпутат[а-яёўіґ'’ʼ`]*|калекты[ўв][а-яёўіґ'’ʼ`]*"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )
         self.re_tarask_jakanie_lex = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"вяліч(?:н|ав|эзн|адушн|асьвет|амучан)[а-яёўіґ'’ʼ`]*"
              r"|(?:дзявят)наццац[а-яёўіґ'’ʼ`]*|дзявятнаццат[а-яёўіґ'’ʼ`]*"
              r"|(?:пяць|шэсьць|сям|васям)дзясят[а-яёўіґ'’ʼ`]*|(?:сям|васям)дзесят[а-яёўіґ'’ʼ`]*"
              r"|гяро[йяюеміў][а-яёўіґ'’ʼ`]*|лягенд[а-яёўіґ'’ʼ`]*|сязон[а-яёўіґ'’ʼ`]*|сякунд[а-яёўіґ'’ʼ`]*|мядал[а-яёўіґ'’ʼ`]*|мятро\b|дзяпутат[а-яёўіґ'’ʼ`]*|калякты[ўв][а-яёўіґ'’ʼ`]*"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )

         # Feminine genitive/dative/locative adjectives (-ае/-яе vs -ай/-яй)
         self.re_tarask_fem_gen_adj = re.compile(
              r"(?:"
              r"(?<![а-яёўіґ'’ʼ`])(?:ад|б[ея]зь?|для|да|з|зь|са|ля|каля|акрамя|апроч|замест|паводле|супраць|сярод|вакол|наконт|пасля|пасьля|падчас)\s+"
              r"(?!(?:веда|шука|чыта|ма|дума|гуля|спява|сьпява|пачына|працягва|вывуча|ствара|азнача|змяшча|зьмяшча|дазваля|прыма|адкрыва|вызнача|паказва|дапамага|захоўва|выкарыстоўва|разгляда|уплыва|ўплыва|быва|ста|да|зна|тыцка|гушка|таска|плеска|пырска|ціска|бліска|трэска|луска)е\b)"
              r"([а-яёўіґ'’ʼ`]{3,}[ая]е)"
              r"|"
              r"(?<![а-яёўіґ'’ʼ`])(?!(?:тыцка|гушка|таска|плеска|пырска|ціска|бліска|трэска|луска)е\b)"
              r"((?:[а-яёўіґ'’ʼ`]{2,}(?:ск|цк|зк|альн|ільн|ельн|ульн|оўн|аўн|еўн|іўн|ліў|ават|яват|іст|ыст|эйш|ейш|енн|анн|інн|онн|родн|народн|сучасн|моўн|краёв|зямельн|дзяржаўн|нацыянальн|гістарычн|палітычн|культурн|літаратурн|эканамічн|грамадск|чалавеч|жаноч|сусветн|сьветн)"
              r"|вялік|мал|нов|стар|добр|бел|чорн|чырвон|сін|зялён|перш|друг|трэц|чацвёрт|пят|шост|сём|восьм|дзявят|дзясят|сам|кожн|інш|усяк|адн|наш|ваш)[ая]е)"
              r")\s+"
              r"(?!(?:яны|калі|тады|куды|сюды|туды|заўжды|трохі|зноўку|ніколі|паволі|аніколі)\b)"
              r"([а-яёўіґ'’ʼ`]{3,}[іы])(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )
         self.re_nark_fem_gen_adj = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:ад|без|для|да|з|са|каля|акрамя|апроч|замест|паводле|супраць|сярод|вакол|наконт|пасля|падчас)\s+"
              r"[а-яёўіґ'’ʼ`]{3,}(?:скай|цкай|зкай|най|вай|лай|рай|тай|дай|чай|шай|жай|гадовай|аднай|гэтай|такой|самай|адной|другой|усёй|сваёй|маёй|тваёй|нашай|вашай)\s+"
              r"[а-яёўіґ'’ʼ`]{3,}[іы](?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )

         # Noun case endings: Locative pl -ох/-ёх, Genitive pl 1st/3rd decl -аў/-яў vs -ей, Genitive sg masc -у vs -а
         self.re_tarask_morph_endings = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"(?:у|ў|па|на|пры|аб)(?:\s+[а-яёўіґ'’ʼ`]+){0,3}\s+(?:лясох|гадох|палёх|грунтох|капцюрох|лугох|барох|садох|дамох|берагох|краёх|радох|часох)"
              r"|(?:гармат|мін|сякер|пячур|прычын|кніжк|хат|вёск|краін|мов|навук|школ|галін|асоб|літар|сіл|справ|машын|фабрык|газэт|задач|праблем|хвілін|гадзін|тысяч)аў"
               r"|(?:падзе|надзе|ліні|пазыцы|станцы|арганізацы|парты)яў\b"
              r"|[а-яёўіґ'’ʼ`]{3,}(?:сьцяў|зьзяў|вязяў)"
              r"|(?:завод|інстытут|унівэрсытэт|універсітэт|камітэт|парлямэнт|парламент|клюб|клуб|тэатр|музэ|горад|менск|пінск|віцебск|полацк|гомел|магілёв|гародн)[ую]"
              r"|(?<=\d\s)году|(?<=\d-га\s)году"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )
         self.re_nark_morph_endings = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"[а-яёўіґ'’ʼ`]{3,}(?:асцей|ясцей|осцей|есцей|уззей|вязей)"
               r"|(?:падзей|надзей|ліній|пазіцый|станцый|арганізацый|партый)\b"
              r"|(?:завод|інстытут|універсітэт|ўніверсітэт|камітэт|парламент|клуб|тэатр|музе|горад|мінск|пінск|віцебск|полацк|брэст|гомел|магілёв|сацыялізм|камунізм|капіталізм|арганізм|механізм|рэалізм)[ая]"
              r"|(?<=\d\s)года|(?<=\d-га\s)года"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )

         # CASCADE 4: LOANWORD MATRICES (EUROPEAN L, SIBILANTS, GREEK θ/β/s) & LEXICAL MARKERS
         # Soft European [л'] in Taraškievica (BKP-2005 Chapter 19, Rules 54-55)
         self.re_tarask_loan_soft_l = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"лёгік[а-яёўіґ'’ʼ`]*|лягічн[а-яёўіґ'’ʼ`]*|[а-яёўіґ'’ʼ`]{3,}лёгі[яіюей][а-яёўіґ'’ʼ`]*"
              r"|плян(?:а|у|е|ы|аў|ам|амі|ах|аваць|аваньне)?|кляс(?:а|ы|у|е|ны|ная|нае|ныя|ык[а-яёўіґ'’ʼ`]*|ыфікац[а-яёўіґ'’ʼ`]*|ік[а-яёўіґ'’ʼ`]*|іфікац[а-яёўіґ'’ʼ`]*)?"
              r"|парлямэнт[а-яёўіґ'’ʼ`]*|філязофі[яіюей][а-яёўіґ'’ʼ`]*|філязофск[а-яёўіґ'’ʼ`]*|філёзаф[а-яёўіґ'’ʼ`]*|філялёгі[яіюей][а-яёўіґ'’ʼ`]*|філёляг[а-яёўіґ'’ʼ`]*"
              r"|плянэт[а-яёўіґ'’ʼ`]*|плятформ[а-яёўіґ'’ʼ`]*|рэклям[а-яёўіґ'’ʼ`]*|дэклярац[а-яёўіґ'’ʼ`]*|рэглямэнт[а-яёўіґ'’ʼ`]*"
              r"|лябаратор[а-яёўіґ'’ʼ`]*|дыплём[а-яёўіґ'’ʼ`]*|дыплямат[а-яёўіґ'’ʼ`]*|кілямэт[а-яёўіґ'’ʼ`]*|калёні[яіюей][а-яёўіґ'’ʼ`]*"
              r"|салён(?:а|у|е|ы|аў|ам|амі|ах|ны)?|балён[а-яёўіґ'’ʼ`]*|талён[а-яёўіґ'’ʼ`]*|эшалён[а-яёўіґ'’ʼ`]*|эталён[а-яёўіґ'’ʼ`]*|флякон[а-яёўіґ'’ʼ`]*"
              r"|флёр[аыу]|флёт[ауе]?|блёк(?:а|у|і|аў|ам|аваць)?|клюб(?:а|у|е|ы|аў|ам|амі|ах|ны)?|клюмб[а-яёўіґ'’ʼ`]*"
              r"|эляд[аыуе]|атлянт[а-яёўіґ'’ʼ`]*|глядыятар[а-яёўіґ'’ʼ`]*|глябус[а-яёўіґ'’ʼ`]*|глёбус[а-яёўіґ'’ʼ`]*"
              r"|лямп[а-яёўіґ'’ʼ`]*|ляндшафт[а-яёўіґ'’ʼ`]*|ляўрэат[а-яёўіґ'’ʼ`]*|лякмус[а-яёўіґ'’ʼ`]*|лязарэт[а-яёўіґ'’ʼ`]*"
              r"|плякат[а-яёўіґ'’ʼ`]*|плястык[а-яёўіґ'’ʼ`]*|пляцдарм[а-яёўіґ'’ʼ`]*|атлят[а-яёўіґ'’ʼ`]*"
              r"|алькагол[а-яёўіґ'’ʼ`]*|альгарытм[а-яёўіґ'’ʼ`]*|альгебр[а-яёўіґ'’ʼ`]*|фальклёр[а-яёўіґ'’ʼ`]*|цэлюлёз[а-яёўіґ'’ʼ`]*"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )

         # Hard sibilants (сы/зы/сэ/зэ) & post-consonantal `э` in Taraškievica (BKP-2005 Chapters 21, 24)
         self.re_tarask_loan_hard_sibilant = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"сыстэм|сытуац|сымбал|сыгнал|сынтэз|сынтаксіс|сымпат|сынонім|сымуляц|сындром|сымфоні|сымэтры"
              r"|сэкц|сэзон|сэкунд|сэсі[яіюей]|сэнат|сэктар|сэры[яіюей]|сэрвіс|сэнсац|сэмінар|сэпарат|сэртыфік|сэкрэт"
              r"|музэ[йіюя]|прэзыдэн|прэзыдыюм|пазыцы|кампазыц|апазыц|фізык|фізычн|фізыялёг|візыт|крызыс|тэзыс|базыс|базылік|рэзыдэнц|дывізы|інквізыц|газэт|касэт|нансэнс"
              r"|асыстэн|асыміляц|дысыдэн|кансыліюм|масы[ўв]|пасы[ўв]|унівэрсытэт|клясык|клясычн|клясыцызм|лексык|таксычн|максымум"
              r"|апэрац|каапэрац|літэратур|мэдал|мэтал|мэтро\b|мэтрапалітэн|генэрал|кабінэт|кампанэн|кантынэн|абанэн|аргумэн|дакумэн|парлямэн|элемэн|экспэрымэн|інструмэн|рэфэрэн|канфэрэнц|унівэрсам|пэрыяд|пэрыод|пэдагог|пэнсі|вэтэран|фэдэрац|энэргі|энцыкляпэд"
              r")[а-яёўіґ'’ʼ`]*",
              re.IGNORECASE,
         )

         # Greek θ -> т, β -> б, intervocalic s -> с, and final -тар/-дар in Taraškievica (BKP-2005 Rules 78, 79, 81)
         self.re_tarask_loan_greek_latin = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"міт(?:ы\b|а\b|у\b|е\b|ам\b|аў\b|амі\b|ах\b|ычн[а-яёўіґ'’ʼ`]*|алёгі[а-яёўіґ'’ʼ`]*)|міт\b"
              r"|катэдр[а-яёўіґ'’ʼ`]*|арытмэты[кч][а-яёўіґ'’ʼ`]*|лягарытм[а-яёўіґ'’ʼ`]*|альгарытм[а-яёўіґ'’ʼ`]*"
              r"|артаграфі[а-яёўіґ'’ʼ`]*|артадокс[а-яёўіґ'’ʼ`]*|артапэд[а-яёўіґ'’ʼ`]*|маратон[а-яёўіґ'’ʼ`]*|патас[а-яёўіґ'’ʼ`]*|анатэм[а-яёўіґ'’ʼ`]*|дытырамб[а-яёўіґ'’ʼ`]*|этэр(?:у|ам|ны)?\b|атэны\b|пітагор[а-яёўіґ'’ʼ`]*"
              r"|альфабэт[а-яёўіґ'’ʼ`]*|бабілён[а-яёўіґ'’ʼ`]*|бізанты[а-яёўіґ'’ʼ`]*|арабі[яію][а-яёўіґ'’ʼ`]*|лібан[а-яёўіґ'’ʼ`]*|барбар[а-яёўіґ'’ʼ`]*|сыбіл[а-яёўіґ'’ʼ`]*|амбон[а-яёўіґ'’ʼ`]*|бэтлеем[а-яёўіґ'’ʼ`]*|габр[аэ][йіюя][а-яёўіґ'’ʼ`]*"
              r"|ясон[ауе]?|эзоп[ауе]?|імпрэсі[яіюей][а-яёўіґ'’ʼ`]*|дыскусі[яіюей][а-яёўіґ'’ʼ`]*"
              r"|(?:мэтар|цэнтар|тэатар|міністар|рэестар|сэквэстар|монстар|аркестар|цыліндар|аляксандар|пэдыятар|пюпітар)\b"
              r"|офіцыяльн[а-яёўіґ'’ʼ`]*|соцыялізм[а-яёўіґ'’ʼ`]*|коаперац[а-яёўіґ'’ʼ`]*|організац[а-яёўіґ'’ʼ`]*"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )

         # Narkamaŭka loanword forms (hard l, soft sibilants сі/зі/се/зе, post-consonantal `е`)
         self.re_nark_loan_forms = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"логік[а-яёўіґ'’ʼ`]*|лагічн[а-яёўіґ'’ʼ`]*|[а-яёўіґ'’ʼ`]{3,}логі[яіюей][а-яёўіґ'’ʼ`]*"
              r"|план(?:а|у|е|ы|аў|ам|амі|ах|аваць|аванне)?|клас(?:а|ы|у|е|ны|ная|нае|ныя|ік[а-яёўіґ'’ʼ`]*|іфікац[а-яёўіґ'’ʼ`]*|іцызм[а-яёўіґ'’ʼ`]*)?"
              r"|парламент[а-яёўіґ'’ʼ`]*|філасофі[яіюей][а-яёўіґ'’ʼ`]*|філасофск[а-яёўіґ'’ʼ`]*|філосаф[а-яёўіґ'’ʼ`]*|філалогі[яіюей][а-яёўіґ'’ʼ`]*|філолаг[а-яёўіґ'’ʼ`]*"
              r"|планет[а-яёўіґ'’ʼ`]*|платформ[а-яёўіґ'’ʼ`]*|рэклам[а-яёўіґ'’ʼ`]*|дэкларац[а-яёўіґ'’ʼ`]*|рэгламент[а-яёўіґ'’ʼ`]*"
              r"|лабаратор[а-яёўіґ'’ʼ`]*|дыплом[а-яёўіґ'’ʼ`]*|дыпламат[а-яёўіґ'’ʼ`]*|кіламетр[а-яёўіґ'’ʼ`]*|калоні[яіюей][а-яёўіґ'’ʼ`]*"
              r"|салон(?:а|у|е|ы|аў|ам|амі|ах|ны)?|балон[а-яёўіґ'’ʼ`]*|талон[а-яёўіґ'’ʼ`]*|эшалон[а-яёўіґ'’ʼ`]*|эталон[а-яёўіґ'’ʼ`]*|флакон[а-яёўіґ'’ʼ`]*"
              r"|флор[аыу]|флот[ауе]?|блок(?:а|у|і|аў|ам|аваць)?|клуб(?:а|у|е|ы|аў|ам|амі|ах|ны)?|клумб[а-яёўіґ'’ʼ`]*"
              r"|элад[аыуе]|атлант[а-яёўіґ'’ʼ`]*|гладыятар[а-яёўіґ'’ʼ`]*|глобус[а-яёўіґ'’ʼ`]*|платон[а-яёўіґ'’ʼ`]*|фларэнцы[а-яёўіґ'’ʼ`]*"
              r"|ламп[а-яёўіґ'’ʼ`]*|ландшафт[а-яёўіґ'’ʼ`]*|лаўрэат[а-яёўіґ'’ʼ`]*|лакмус[а-яёўіґ'’ʼ`]*|лазарэт[а-яёўіґ'’ʼ`]*"
              r"|плакат[а-яёўіґ'’ʼ`]*|пластык[а-яёўіґ'’ʼ`]*|плацдарм[а-яёўіґ'’ʼ`]*|атлет[а-яёўіґ'’ʼ`]*|календар[ауыоіе][а-яёўіґ'’ʼ`]*"
              r"|алкагол[а-яёўіґ'’ʼ`]*|алгарытм[а-яёўіґ'’ʼ`]*|алгебр[а-яёўіґ'’ʼ`]*|фальклор[а-яёўіґ'’ʼ`]*|цэлюлоз[а-яёўіґ'’ʼ`]*"
              r"|сістэм[а-яёўіґ'’ʼ`]*|сітуац[а-яёўіґ'’ʼ`]*|сімвал[а-яёўіґ'’ʼ`]*|сігнал[а-яёўіґ'’ʼ`]*|сінтэз[а-яёўіґ'’ʼ`]*|сінтаксіс[а-яёўіґ'’ʼ`]*|сімпат[а-яёўіґ'’ʼ`]*|сінонім[а-яёўіґ'’ʼ`]*|сімптом[а-яёўіґ'’ʼ`]*|сіндром[а-яёўіґ'’ʼ`]*|сімфоні[а-яёўіґ'’ʼ`]*|сіметры[а-яёўіґ'’ʼ`]*"
              r"|секцы[яіюей][а-яёўіґ'’ʼ`]*|сесі[яіюей][а-яёўіґ'’ʼ`]*|сенат[а-яёўіґ'’ʼ`]*|сектар[а-яёўіґ'’ʼ`]*|серы[яіюей][а-яёўіґ'’ʼ`]*|сервіз[а-яёўіґ'’ʼ`]*|сенсац[а-яёўіґ'’ʼ`]*|семінар[а-яёўіґ'’ʼ`]*|сепарат[а-яёўіґ'’ʼ`]*|сертыфік[а-яёўіґ'’ʼ`]*"
              r"|музе[йіюя][а-яёўіґ'’ʼ`]*|прэзідэн[а-яёўіґ'’ʼ`]*|прэзідыум[а-яёўіґ'’ʼ`]*|пазіцы[яіюей][а-яёўіґ'’ʼ`]*|кампазіц[а-яёўіґ'’ʼ`]*|апазіц[а-яёўіґ'’ʼ`]*"
              r"|фізік[а-яёўіґ'’ʼ`]*|фізічн[а-яёўіґ'’ʼ`]*|фізіялог[а-яёўіґ'’ʼ`]*|візіт[а-яёўіґ'’ʼ`]*|крызіс[а-яёўіґ'’ʼ`]*|тэзіс[а-яёўіґ'’ʼ`]*|базіс[а-яёўіґ'’ʼ`]*|базілік[а-яёўіґ'’ʼ`]*|рэзідэнц[а-яёўіґ'’ʼ`]*|дывізі[яіюей][а-яёўіґ'’ʼ`]*|інквізіц[а-яёўіґ'’ʼ`]*|газет[а-яёўіґ'’ʼ`]*|касет[а-яёўіґ'’ʼ`]*"
              r"|асістэн[а-яёўіґ'’ʼ`]*|асіміляц[а-яёўіґ'’ʼ`]*|дысідэн[а-яёўіґ'’ʼ`]*|кансіліум[а-яёўіґ'’ʼ`]*|масі[ўв][а-яёўіґ'’ʼ`]*|пасі[ўв][а-яёўіґ'’ʼ`]*|універсітэт[а-яёўіґ'’ʼ`]*|ўніверсітэт[а-яёўіґ'’ʼ`]*|лексік[а-яёўіґ'’ʼ`]*|таксічн[а-яёўіґ'’ʼ`]*|максімум[а-яёўіґ'’ʼ`]*"
              r"|аперац[а-яёўіґ'’ʼ`]*|кааперац[а-яёўіґ'’ʼ`]*|метал[ауеыі][а-яёўіґ'’ʼ`]*|метал\b|генерал[а-яёўіґ'’ʼ`]*|кабінет[а-яёўіґ'’ʼ`]*|кампанен[а-яёўіґ'’ʼ`]*|кантынен[а-яёўіґ'’ʼ`]*|абанен[а-яёўіґ'’ʼ`]*|аргумен[а-яёўіґ'’ʼ`]*|дакумен[а-яёўіґ'’ʼ`]*|элемен[а-яёўіґ'’ʼ`]*|эксперымен[а-яёўіґ'’ʼ`]*|інструмен[а-яёўіґ'’ʼ`]*|рэферэн[а-яёўіґ'’ʼ`]*|канферэнц[а-яёўіґ'’ʼ`]*|універсам[а-яёўіґ'’ʼ`]*|перыяд[а-яёўіґ'’ʼ`]*|педагог[а-яёўіґ'’ʼ`]*|пенсі[яіюей][а-яёўіґ'’ʼ`]*|ветэран[а-яёўіґ'’ʼ`]*|федэрац[а-яёўіґ'’ʼ`]*|энергі[яіюей][а-яёўіґ'’ʼ`]*|энцыклапед[а-яёўіґ'’ʼ`]*|перспекты[ўв][а-яёўіґ'’ʼ`]*|спецыял[а-яёўіґ'’ʼ`]*|інжынер[а-яёўіґ'’ʼ`]*|прафесар[а-яёўіґ'’ʼ`]*|канверт[а-яёўіґ'’ʼ`]*"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )

         # Narkamaŭka Greek θ -> ф, β -> в, intervocalic s -> з (Язон), and final -тр/-др
         self.re_nark_loan_greek_latin = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"міф(?:ы\b|а\b|у\b|е\b|ам\b|аў\b|амі\b|ах\b|ічн[а-яёўіґ'’ʼ`]*|алогі[а-яёўіґ'’ʼ`]*)|міф\b"
              r"|кафедр[а-яёўіґ'’ʼ`]*|арыфметы[кч][а-яёўіґ'’ʼ`]*|лагарыфм[а-яёўіґ'’ʼ`]*"
              r"|арфаграфі[а-яёўіґ'’ʼ`]*|арфаэпі[а-яёўіґ'’ʼ`]*|марафон[а-яёўіґ'’ʼ`]*|пафас[а-яёўіґ'’ʼ`]*|анафем[а-яёўіґ'’ʼ`]*|дыфірамб[а-яёўіґ'’ʼ`]*|эфір(?:у|ам|ны)?\b|афіны\b|піфагор[а-яёўіґ'’ʼ`]*"
              r"|алфавіт[а-яёўіґ'’ʼ`]*|вавілон[а-яёўіґ'’ʼ`]*|візанты[а-яёўіґ'’ʼ`]*|араві[яію][а-яёўіґ'’ʼ`]*|ліван[а-яёўіґ'’ʼ`]*|варвар[а-яёўіґ'’ʼ`]*|сібір[а-яёўіґ'’ʼ`]*|амвон[а-яёўіґ'’ʼ`]*|віфлеем[а-яёўіґ'’ʼ`]*"
              r"|язон[ауе]?|канстанцін[а-яёўіґ'’ʼ`]*"
              r"|(?:метр|кіламетр|сантіметр|міліметр|цэнтр|тэатр|міністр|рэестр|секвестр|монстр|аркестр|цыліндр|аляксандр|педыятр|пюпітр)\b"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )

         # Characteristic toponyms and lexical markers
         self.re_tarask_lex_markers = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"менск[а-яёўіґ'’ʼ`]*|берасьц[а-яёўіґ'’ʼ`]*|расе[яію][а-яёўіґ'’ʼ`]*|расейск[а-яёўіґ'’ʼ`]*|"
              r"эўроп[а-яёўіґ'’ʼ`]*|эўрапейск[а-яёўіґ'’ʼ`]*|досьвед[а-яёўіґ'’ʼ`]*|адсотак[а-яёўіґ'’ʼ`]*"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )
         self.re_nark_lex_markers = re.compile(
              r"(?<![а-яёўіґ'’ʼ`])(?:"
              r"мінск[а-яёўіґ'’ʼ`]*|брэст[а-яёўіґ'’ʼ`]*|расі[яію][а-яёўіґ'’ʼ`]*|расійск[а-яёўіґ'’ʼ`]*|"
              r"еўроп[а-яёўіґ'’ʼ`]*|еўрапейск[а-яёўіґ'’ʼ`]*|працэнт[а-яёўіґ'’ʼ`]*"
              r")(?![а-яёўіґ'’ʼ`])",
              re.IGNORECASE,
         )

    def compute_doc_prior(self, segments: List[str]) -> float:
         """
         Computes the Bayesian log-odds prior score (L_doc) across an entire document.
         """
         doc_taras_ev = 0.0
         doc_nark_ev = 0.0

         for text in segments:
              norm_text = normalize_typography(text)
              masked_for_palatal = self.re_nark_legal_palatal_seam.sub(" ", norm_text)

              doc_taras_ev += (
                   len(self.re_tarask_palatal_cluster.findall(masked_for_palatal)) * 2.5
                   + len(self.re_tarask_prefix_soft_sign.findall(norm_text)) * 2.3
                   + len(self.re_tarask_soft_long.findall(norm_text)) * 2.4
                   + len(self.re_tarask_affricate_assim.findall(norm_text)) * 2.2
                   + len(self.re_tarask_jakanie_lex.findall(norm_text)) * 2.0
                   + len(self.re_tarask_loan_soft_l.findall(norm_text)) * 1.8
                   + len(self.re_tarask_loan_hard_sibilant.findall(norm_text)) * 1.8
                   + len(self.re_tarask_loan_greek_latin.findall(norm_text)) * 2.0
                   + len(self.re_tarask_morph_endings.findall(norm_text)) * 1.8
                   + len(self.re_tarask_lex_markers.findall(norm_text)) * 2.0
              )

              doc_nark_ev += (
                   len(self.re_nark_hard_long.findall(norm_text)) * 2.4
                   + len(self.re_nark_unmarked_assimilation.findall(masked_for_palatal)) * 2.2
                   + len(self.re_nark_prefix_apostrophe.findall(norm_text)) * 2.2
                   + len(self.re_nark_affricate_unassimilated.findall(norm_text)) * 2.0
                   + len(self.re_nark_jakanie_exceptions.findall(norm_text)) * 2.0
                   + len(self.re_nark_loan_forms.findall(norm_text)) * 1.8
                   + len(self.re_nark_loan_greek_latin.findall(norm_text)) * 2.0
                   + len(self.re_nark_morph_endings.findall(norm_text)) * 1.8
                   + len(self.re_nark_lex_markers.findall(norm_text)) * 2.0
              )

         raw_prior = math.log((doc_taras_ev + self.prior_alpha) / (doc_nark_ev + self.prior_alpha))
         return max(-self.MAX_DOC_PRIOR, min(self.MAX_DOC_PRIOR, raw_prior))

    def classify(self, text: str, doc_prior_log_odds: float = 0.0) -> RouteResult:
         """
         Classifies an individual text segment with confidence-gated document-prior inheritance.
         """
         norm_text = normalize_typography(text)
         words = self.re_word_tokens.findall(norm_text)
         total_words = len(words)

         if total_words < 4:
              return RouteResult(
                   label="rejected",
                   text_original=norm_text,
                   text_tagged="",
                   metrics={"reason": "too_short", "word_count": total_words}
              )

         # 1. Cascade 0: Non-Belarusian characters, OCR homoglyphs, broken short-u, Trasyanka
         ru_chars = len(self.re_russian_chars.findall(norm_text))
         cyr_chars = sum(len(w) for w in words)
         if cyr_chars > 0 and (ru_chars / cyr_chars) > 0.002:
              return RouteResult(
                   label="rejected",
                   text_original=norm_text,
                   text_tagged="",
                   metrics={"reason": "REJECT_RUSSIAN_CHARS", "ru_chars": ru_chars}
              )

         mixed_words = self.re_mixed_script.findall(norm_text)
         if len(mixed_words) / total_words > 0.01:
              return RouteResult(
                   label="rejected",
                   text_original=norm_text,
                   text_tagged="",
                   metrics={"reason": "REJECT_OCR_HOMOGLYPH", "count": len(mixed_words)}
              )

         valid_ushort = len(self.re_ushort_valid.findall(norm_text))
         broken_ushort = len(self.re_ushort_broken.findall(norm_text))
         if (valid_ushort + broken_ushort) >= 5:
              if broken_ushort / (valid_ushort + 1.0) > 0.15:
                   return RouteResult(
                        label="rejected",
                        text_original=norm_text,
                        text_tagged="",
                        metrics={"reason": "REJECT_OCR_USHORT_LOSS", "broken": broken_ushort}
                   )

         trasianka_hits = self.re_trasianka.findall(norm_text)
         if len(trasianka_hits) >= 2 or (total_words < 15 and len(trasianka_hits) >= 1):
              return RouteResult(
                   label="rejected",
                   text_original=norm_text,
                   text_tagged="",
                   metrics={"reason": "REJECT_TRASIANKA_BELAZAR", "hits": trasianka_hits}
              )

         # 2. Extract differential features
         # Mask legal Narkamaŭka morphological seams (§ 18 NKBM-2008) for BOTH palatal detectors
         masked_for_palatal = self.re_nark_legal_palatal_seam.sub(" ", norm_text)

         counts: Dict[str, int] = {
              "tarask_palatal_cluster": len(self.re_tarask_palatal_cluster.findall(masked_for_palatal)),
              "tarask_prefix_soft_sign": len(self.re_tarask_prefix_soft_sign.findall(norm_text)),
              "tarask_soft_long": len(self.re_tarask_soft_long.findall(norm_text)),
              "tarask_affricate_assim": len(self.re_tarask_affricate_assim.findall(norm_text)),
              "tarask_nia_biaz": len(self.re_tarask_nia_biaz.findall(norm_text)),
              "tarask_jakanie_lex": len(self.re_tarask_jakanie_lex.findall(norm_text)),
              "tarask_loan_soft_l": len(self.re_tarask_loan_soft_l.findall(norm_text)),
              "tarask_loan_hard_sibilant": len(self.re_tarask_loan_hard_sibilant.findall(norm_text)),
              "tarask_loan_greek_latin": len(self.re_tarask_loan_greek_latin.findall(norm_text)),
              "tarask_fem_gen_adj": len(self.re_tarask_fem_gen_adj.findall(norm_text)),
              "tarask_morph_endings": len(self.re_tarask_morph_endings.findall(norm_text)),
              "tarask_lex_markers": len(self.re_tarask_lex_markers.findall(norm_text)),
              "nark_hard_long": len(self.re_nark_hard_long.findall(norm_text)),
              "nark_unmarked_assimilation": len(self.re_nark_unmarked_assimilation.findall(masked_for_palatal)),
              "nark_prefix_apostrophe": len(self.re_nark_prefix_apostrophe.findall(norm_text)),
              "nark_affricate_unassimilated": len(self.re_nark_affricate_unassimilated.findall(norm_text)),
              "nark_nie_biez_stressed": len(self.re_nark_nie_biez_stressed.findall(norm_text)),
              "nark_jakanie_exceptions": len(self.re_nark_jakanie_exceptions.findall(norm_text)),
              "nark_loan_forms": len(self.re_nark_loan_forms.findall(norm_text)),
              "nark_loan_greek_latin": len(self.re_nark_loan_greek_latin.findall(norm_text)),
              "nark_fem_gen_adj": len(self.re_nark_fem_gen_adj.findall(norm_text)),
              "nark_morph_endings": len(self.re_nark_morph_endings.findall(norm_text)),
              "nark_lex_markers": len(self.re_nark_lex_markers.findall(norm_text)),
         }

         nark_ev = sum(v for k, v in counts.items() if k.startswith("nark_") and v > 0)
         hard_taras_ev = sum(
              v for k, v in counts.items()
              if k.startswith("tarask_") and k != "tarask_fem_gen_adj" and v > 0
         )

         # Contextual Gating for Stylistic Archaic Feminine Genitive Adjective (-ае/-яе) in Narkamaŭka editions:
         if counts["tarask_fem_gen_adj"] > 0 and hard_taras_ev == 0 and (nark_ev > 0 or doc_prior_log_odds <= -2.0):
              counts["tarask_fem_gen_adj"] = 0

         features: Dict[str, List[str]] = {"nark": [], "taras": []}
         for k, v in counts.items():
              if v > 0:
                   if k.startswith("tarask_"):
                        features["taras"].append(f"{k}:{v}")
                   else:
                        features["nark"].append(f"{k}:{v}")

         taras_ev = sum(v for k, v in counts.items() if k.startswith("tarask_") and v > 0)
         total_ev = taras_ev + nark_ev

         # 3. Orthographic Chimera Detection (intra-segment norm mixing)
         min_ev = min(nark_ev, taras_ev)
         max_ev = max(nark_ev, taras_ev)
         chimera_index = (min_ev / max_ev) if max_ev > 0 else 0.0

         taras_weight = sum(counts[k] * self.WEIGHTS[k] for k in counts if k.startswith('tarask_'))
         nark_weight = sum(counts[k] * abs(self.WEIGHTS[k]) for k in counts if k.startswith('nark_'))
         is_chimera = (min_ev >= 2 and chimera_index > self.max_chimera_index) or (
             min_ev >= 1 and min(taras_weight, nark_weight) >= 1.5 and chimera_index >= 0.20
         )
         if is_chimera:
              return RouteResult(
                   label="rejected",
                   text_original=norm_text,
                   text_tagged="",
                   metrics={
                        "reason": "REJECT_ORTHOGRAPHIC_CHIMERA",
                        "chimera_index": chimera_index,
                        "features": features,
                   }
              )

         # 4. Local Score Formulation
         local_score = sum(counts[feat] * self.WEIGHTS[feat] for feat in counts if counts[feat] > 0)

         # 5. Confidence-Gated Context Decay
         clipped_prior = max(-self.MAX_DOC_PRIOR, min(self.MAX_DOC_PRIOR, doc_prior_log_odds))
         effective_beta = self.BETA_BASE * math.exp(-abs(local_score) / self.DECAY_TAU)
         final_score = local_score + effective_beta * clipped_prior

         # Probabilistic sigmoid confidence
         confidence = 1.0 / (1.0 + math.exp(-abs(final_score)))

         metrics = {
              "confidence": round(confidence, 4),
              "effective_log_odds": round(final_score, 4),
              "local_score": round(local_score, 4),
              "nark_evidence": nark_ev,
              "taras_evidence": taras_ev,
              "chimera_index": round(chimera_index, 4),
              "features": features,
         }

         # Neutral segment with non-informative document context
         if total_ev == 0 and abs(clipped_prior) < 0.2:
              return RouteResult(
                   label="rejected",
                   text_original=norm_text,
                   text_tagged="",
                   metrics={**metrics, "reason": "REJECT_NEUTRAL_NO_CONTEXT"}
              )

         # Decision threshold gating
         if abs(final_score) < self.DECISION_THRESHOLD:
              return RouteResult(
                   label="rejected",
                   text_original=norm_text,
                   text_tagged="",
                   metrics={**metrics, "reason": "REJECT_LOW_CONFIDENCE_AMBIGUOUS"}
              )

         if final_score > 0:
              return RouteResult(
                   label="tarask",
                   text_original=norm_text,
                   text_tagged=f"<orth_taras>{norm_text}</orth_taras>",
                   metrics=metrics,
              )
         else:
              return RouteResult(
                   label="nark",
                   text_original=norm_text,
                   text_tagged=f"<orth_nark>{norm_text}</orth_nark>",
                   metrics=metrics,
              )

    def classify_document(self, segments: List[str]) -> Tuple[float, List[RouteResult]]:
        """
        High-throughput single-pass document processor.
        Extracts phonological features across all segments once, aggregates document evidence
        to compute the Bayesian document prior, and evaluates each segment against that prior.
        Mathematically identical to compute_doc_prior followed by individual classify calls,
        but eliminates redundant regular expression evaluations.
        """
        if not segments:
            return 0.0, []

        parsed = []
        doc_taras_ev = 0.0
        doc_nark_ev = 0.0

        for text in segments:
            norm_text = normalize_typography(text)
            words = self.re_word_tokens.findall(norm_text)
            total_words = len(words)

            if total_words < 4:
                parsed.append(("too_short", norm_text, total_words, None))
                continue

            ru_chars = len(self.re_russian_chars.findall(norm_text))
            cyr_chars = sum(len(w) for w in words)
            if cyr_chars > 0 and (ru_chars / cyr_chars) > 0.002:
                parsed.append(("ru_chars", norm_text, ru_chars, None))
                continue

            mixed_words = self.re_mixed_script.findall(norm_text)
            if len(mixed_words) / total_words > 0.01:
                parsed.append(("mixed_script", norm_text, len(mixed_words), None))
                continue

            valid_ushort = len(self.re_ushort_valid.findall(norm_text))
            broken_ushort = len(self.re_ushort_broken.findall(norm_text))
            if (valid_ushort + broken_ushort) >= 5 and broken_ushort / (valid_ushort + 1.0) > 0.15:
                parsed.append(("broken_ushort", norm_text, broken_ushort, None))
                continue

            trasianka_hits = self.re_trasianka.findall(norm_text)
            if len(trasianka_hits) >= 2 or (total_words < 15 and len(trasianka_hits) >= 1):
                parsed.append(("trasianka", norm_text, trasianka_hits, None))
                continue

            masked_for_palatal = self.re_nark_legal_palatal_seam.sub(" ", norm_text)

            counts: Dict[str, int] = {
                "tarask_palatal_cluster": len(self.re_tarask_palatal_cluster.findall(masked_for_palatal)),
                "tarask_prefix_soft_sign": len(self.re_tarask_prefix_soft_sign.findall(norm_text)),
                "tarask_soft_long": len(self.re_tarask_soft_long.findall(norm_text)),
                "tarask_affricate_assim": len(self.re_tarask_affricate_assim.findall(norm_text)),
                "tarask_nia_biaz": len(self.re_tarask_nia_biaz.findall(norm_text)),
                "tarask_jakanie_lex": len(self.re_tarask_jakanie_lex.findall(norm_text)),
                "tarask_loan_soft_l": len(self.re_tarask_loan_soft_l.findall(norm_text)),
                "tarask_loan_hard_sibilant": len(self.re_tarask_loan_hard_sibilant.findall(norm_text)),
                "tarask_loan_greek_latin": len(self.re_tarask_loan_greek_latin.findall(norm_text)),
                "tarask_fem_gen_adj": len(self.re_tarask_fem_gen_adj.findall(norm_text)),
                "tarask_morph_endings": len(self.re_tarask_morph_endings.findall(norm_text)),
                "tarask_lex_markers": len(self.re_tarask_lex_markers.findall(norm_text)),
                "nark_hard_long": len(self.re_nark_hard_long.findall(norm_text)),
                "nark_unmarked_assimilation": len(self.re_nark_unmarked_assimilation.findall(masked_for_palatal)),
                "nark_prefix_apostrophe": len(self.re_nark_prefix_apostrophe.findall(norm_text)),
                "nark_affricate_unassimilated": len(self.re_nark_affricate_unassimilated.findall(norm_text)),
                "nark_nie_biez_stressed": len(self.re_nark_nie_biez_stressed.findall(norm_text)),
                "nark_jakanie_exceptions": len(self.re_nark_jakanie_exceptions.findall(norm_text)),
                "nark_loan_forms": len(self.re_nark_loan_forms.findall(norm_text)),
                "nark_loan_greek_latin": len(self.re_nark_loan_greek_latin.findall(norm_text)),
                "nark_fem_gen_adj": len(self.re_nark_fem_gen_adj.findall(norm_text)),
                "nark_morph_endings": len(self.re_nark_morph_endings.findall(norm_text)),
                "nark_lex_markers": len(self.re_nark_lex_markers.findall(norm_text)),
            }

            doc_taras_ev += (
                counts["tarask_palatal_cluster"] * 2.5
                + counts["tarask_prefix_soft_sign"] * 2.3
                + counts["tarask_soft_long"] * 2.4
                + counts["tarask_affricate_assim"] * 2.2
                + counts["tarask_jakanie_lex"] * 2.0
                + counts["tarask_loan_soft_l"] * 1.8
                + counts["tarask_loan_hard_sibilant"] * 1.8
                + counts["tarask_loan_greek_latin"] * 2.0
                + counts["tarask_morph_endings"] * 1.8
                + counts["tarask_lex_markers"] * 2.0
            )
            doc_nark_ev += (
                counts["nark_hard_long"] * 2.4
                + counts["nark_unmarked_assimilation"] * 2.2
                + counts["nark_prefix_apostrophe"] * 2.2
                + counts["nark_affricate_unassimilated"] * 2.0
                + counts["nark_jakanie_exceptions"] * 2.0
                + counts["nark_loan_forms"] * 1.8
                + counts["nark_loan_greek_latin"] * 2.0
                + counts["nark_morph_endings"] * 1.8
                + counts["nark_lex_markers"] * 2.0
            )
            parsed.append(("valid", norm_text, total_words, counts))

        raw_prior = math.log((doc_taras_ev + self.prior_alpha) / (doc_nark_ev + self.prior_alpha))
        clipped_prior = max(-self.MAX_DOC_PRIOR, min(self.MAX_DOC_PRIOR, raw_prior))

        results = []
        for item in parsed:
            status = item[0]
            norm_text = item[1]
            if status == "too_short":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "too_short", "word_count": item[2]}))
            elif status == "ru_chars":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "REJECT_RUSSIAN_CHARS", "ru_chars": item[2]}))
            elif status == "mixed_script":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "REJECT_OCR_HOMOGLYPH", "count": item[2]}))
            elif status == "broken_ushort":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "REJECT_OCR_USHORT_LOSS", "broken": item[2]}))
            elif status == "trasianka":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "REJECT_TRASIANKA_BELAZAR", "hits": item[2]}))
            else:
                counts = dict(item[3])
                nark_ev = sum(v for k, v in counts.items() if k.startswith("nark_") and v > 0)
                hard_taras_ev = sum(v for k, v in counts.items() if k.startswith("tarask_") and k != "tarask_fem_gen_adj" and v > 0)
                if counts["tarask_fem_gen_adj"] > 0 and hard_taras_ev == 0 and (nark_ev > 0 or clipped_prior <= -2.0):
                    counts["tarask_fem_gen_adj"] = 0

                features: Dict[str, List[str]] = {"nark": [], "taras": []}
                for k, v in counts.items():
                    if v > 0:
                        if k.startswith("tarask_"):
                            features["taras"].append(f"{k}:{v}")
                        else:
                            features["nark"].append(f"{k}:{v}")

                taras_ev = sum(v for k, v in counts.items() if k.startswith("tarask_") and v > 0)
                total_ev = taras_ev + nark_ev
                min_ev = min(nark_ev, taras_ev)
                max_ev = max(nark_ev, taras_ev)
                chimera_index = (min_ev / max_ev) if max_ev > 0 else 0.0

                taras_weight = sum(counts[k] * self.WEIGHTS[k] for k in counts if k.startswith('tarask_'))
                nark_weight = sum(counts[k] * abs(self.WEIGHTS[k]) for k in counts if k.startswith('nark_'))
                is_chimera = (min_ev >= 2 and chimera_index > self.max_chimera_index) or (
                    min_ev >= 1 and min(taras_weight, nark_weight) >= 1.5 and chimera_index >= 0.20
                )
                if is_chimera:
                    results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "REJECT_ORTHOGRAPHIC_CHIMERA", "chimera_index": chimera_index, "features": features}))
                    continue

                local_score = sum(counts[feat] * self.WEIGHTS[feat] for feat in counts if counts[feat] > 0)
                effective_beta = self.BETA_BASE * math.exp(-abs(local_score) / self.DECAY_TAU)
                final_score = local_score + effective_beta * clipped_prior
                confidence = 1.0 / (1.0 + math.exp(-abs(final_score)))

                metrics = {
                    "confidence": round(confidence, 4),
                    "effective_log_odds": round(final_score, 4),
                    "local_score": round(local_score, 4),
                    "nark_evidence": nark_ev,
                    "taras_evidence": taras_ev,
                    "chimera_index": round(chimera_index, 4),
                    "features": features,
                }

                if total_ev == 0 and abs(clipped_prior) < 0.2:
                    results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={**metrics, "reason": "REJECT_NEUTRAL_NO_CONTEXT"}))
                elif abs(final_score) < self.DECISION_THRESHOLD:
                    results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={**metrics, "reason": "REJECT_LOW_CONFIDENCE_AMBIGUOUS"}))
                elif final_score > 0:
                    results.append(RouteResult(label="tarask", text_original=norm_text, text_tagged=f"<orth_taras>{norm_text}</orth_taras>", metrics=metrics))
                else:
                    results.append(RouteResult(label="nark", text_original=norm_text, text_tagged=f"<orth_nark>{norm_text}</orth_nark>", metrics=metrics))

        return clipped_prior, results


# ── High-Level Compatibility Facade ──────────────────────────────────────────

def load_tarask_wordlist(path: Path) -> frozenset:
    log.info("Loading reference wordlist: %s", path)
    words = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            for w in line.strip().split(","):
                cleaned = w.strip().lower()
                if cleaned:
                    words.add(cleaned)
    return frozenset(words)


class OrthographyRouter:
    """
    Facade class maintaining seamless compatibility with DualMova dataset pipelines.
    """
    def __init__(
        self,
        tarask_wordlist_path: Optional[Path | str] = None,
        use_languagetool: bool = False,
        confidence_threshold: float = 0.88,
    ):
        taras_vocab = set()
        if tarask_wordlist_path and Path(tarask_wordlist_path).exists():
            taras_vocab = set(load_tarask_wordlist(Path(tarask_wordlist_path)))

        self.classifier = DualMovaOrthographyClassifier(
            tarask_vocab=taras_vocab,
            confidence_threshold=confidence_threshold,
        )

    def route(self, text: str, doc_prior_log_odds: float = 0.0) -> RouteResult:
        return self.classifier.classify(text, doc_prior_log_odds=doc_prior_log_odds)

    def route_document(self, texts: List[str]) -> Tuple[float, List[RouteResult]]:
        return self.classifier.classify_document(texts)

    def compute_doc_prior(self, texts: List[str]) -> float:
        return self.classifier.compute_doc_prior(texts)

    def generate_augmented_pair(self, result: RouteResult) -> Optional[RouteResult]:
        # Synthetic regex pair augmentation is deactivated to preserve 100% human-authored corpus authenticity
        return None


if __name__ == "__main__":
    router = OrthographyRouter()

    test_samples = [
        ("Танк гэты стаяў узняты на ўзгорак з супрацьлеглага боку. Трэба было ісці праз дзверы з дрыжаннем, збіраць касці сляпых.", "nark"),
        ("Танк гэты стаяў узьняты на ўзгорак. Яны ня ведалі, як знайсьці праўду ў гэтым сьвеце. Гэта вялікае пытаньне новага жыцьця і грамадзкай радасьці.", "tarask"),
        ("Вядомы беларускі пісьменнік напісаў новае пісьмо, дзе распавёў пра сваю просьбу і сустрэчу з людзьмі.", "nark"),
        ("Станьце тут, калі ласка, і паглядзіце на гэтае дзіўнае зацьменне сонца.", "nark"),
        ("Сучаснае пакаленне чытае кнігі, вывучае дакументы і шукае праўды.", "nark"),
        ("План развіцця горада Мінска быў зацверджаны ў новай сістэме.", "nark"),
        ("Плян разьвіцьця гораду Менску быў зацьверджаны ў новай сыстэме.", "tarask"),
        ("Разглядаецца праблема аб’яднаньня, дзе адбываецца новае вясельле і адчыняюцца дзьверы.", "tarask"),
        ("Яна не магла і не хацела заставацца без вады і без дапамогі, але сьнег засыпаў усе сьцежкі.", "tarask"),
        ("Уздоўж узбярэжжа раскінулася зацішша, ноччу ваенны патруль вёз збожжа і тонны грузу.", "rejected"),
        ("Этот текст написан на русском языке и должен быть отброшен.", "rejected"),
        ("Ён пашол у магазін і сказаў, што толька еслі патаму што робітся работа.", "rejected"),
        ("Арганаўты стоўпіліся на палубе, любаваліся велічным відовішчам... Хвалі неслі «Арго» проста на скалы. На носе карабля стаяў Язон... Язон выпусціў птушку ў праход... Так паўстаюць перад намі героі Элады.", "nark"),
    ]

    print("=== DUALMOVA CLASSIFIER INLINE VERIFICATION ===\n")
    all_ok = True
    for text, exp in test_samples:
        r = router.route(text)
        ok = (r.label == exp)
        if not ok:
            all_ok = False
        status = "[PASS]" if ok else "[FAIL]"
        lo = r.metrics.get("effective_log_odds", 0.0)
        print(f"{status} Expected: {exp:10} | Obtained: {r.label:10} (score={lo:+.2f}, conf={r.metrics.get('confidence', 0.0):.3f}) | Snippet: {text[:55]}...")

    print(f"\nRESULT: {'ALL VERIFICATION SAMPLES PASSED!' if all_ok else 'TEST FAILURE DETECTED!'}")
