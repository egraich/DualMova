"""
DualMova — High-Precision Symmetric Orthography Classifier (v3.0 Architecture)
=============================================================================
Architecture built upon the rigorous phonological codifications of the Belarusian language:
- Official Standard (Narkamaŭka / NKBM-2008, Law of the Republic of Belarus № 420-Z) -> <orth_nark>
- Classical Standard (Taraškievica / BKP-2005 Codification) -> <orth_taras>
- Invariant Common Core (Legitimate neutral Belarusian prose) -> <orth_invariant>
- Anomalies / Trasyanka / Russian script & phonological intrusions / Mixed Norms -> REJECT

Theoretical Foundations & Mathematical Pillars (v3.0):
1. Two-Stage Language Identification (Stage 1 LID in Cascade 0):
   Before orthographic norm arbitration, non-Belarusian intrusions are eliminated via
   strict phonological impossibility constraints:
   - Post-alveolar hard clusters: [ж, ч, ш, р] followed by iotated vowels [е, ё, ю, я]
   - Non-affricated dentals: [д, т] followed by [е, ё, ю, я] (absence of dzekanne/tsekanne)
   - Russian adjectival case inflections: -ого / -его
   - High-frequency Russian grammatical particles and conjunctions lacking [и, щ, ъ].
2. Empirical Bayes Directional Prior (Sample-Size Shrinkage):
   Replaces uncalibrated log-odds ratio with directional balance D_doc and shrinkage factor
   R_doc = E_total / (E_total + kappa_doc), eliminating small-sample volatility.
3. Bidirectional Laplace Context Field L_neigh(i):
   Computes local section-level context in O(M) linear time via forward-backward recurrence
   with spatial decay gamma = 0.65, resolving composite documents (prefaces, anthologies).
4. Direction-Dependent (Conflict-Aware) Gating:
   Eliminates the v2.0 beta_base = 0.40 dead zone:
   - Agreement / Neutrality (L_local * L_ctx >= 0): beta_eff = 1.0 (no dilution of context).
   - Code-Switching Conflict (L_local * L_ctx < 0): beta_conflict = 0.35 * exp(-|L_local| / 2.0).
5. Pre-Soft Morphemic Seam Grammar (§ 18 NKBM-2008):
   Soft sign occurrences before soft consonants in Narkamaŭka are strictly restricted
   to 7 closed morphological categories (e.g. людзьмі, хтосьці, сядзьце, пісьменнік,
   цьмяны, студзеньскі, у барацьбе, дзьме, возьме, маленькі).
"""

from __future__ import annotations

import logging
import math
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

log = logging.getLogger(__name__)


# ── Routing Result Data Structure ─────────────────────────────────────────────

@dataclass
class RouteResult:
    """Classification outcome for a text segment in DualMova."""
    label: str                  # "nark" | "tarask" | "invariant" | "rejected"
    text_original: str          # Raw text after safe typographic normalization
    text_tagged: str            # Enclosed text with <orth_nark>, <orth_taras>, <orth_invariant> or empty
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
    Normalizes typography without altering phonological or orthographic information:
    1. Repairs OCR Cyrillic homoglyphs in Roman numerals (e.g. 'ХХІ' -> 'XXI').
    2. Converts OCR Latin 'i/I' inside Cyrillic words to authentic Belarusian 'і/І'.
    3. Normalizes all apostrophe variants (’, ʼ, `, ‘, ') to canonical ASCII apostrophe (').
    4. Normalizes inter-word dashes (hyphen, en-dash, minus) to em-dash (—).
    5. Normalizes paired quotation marks to standard typographic chevrons («...»).
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)

    # 1. Repair OCR Roman numerals
    def _fix_roman(m):
        return m.group(0).translate(_ROMAN_CYR_TO_LAT)
    text = _ROMAN_NUMERAL_FIX.sub(_fix_roman, text)

    # 2. Repair Latin 'i' inside Belarusian Cyrillic words
    def _lat_to_by(m):
        c = m.group(0)
        return "І" if c == "I" else "і"
    text = _LATIN_TO_BY_CYR.sub(_lat_to_by, text)

    # 3. Canonical apostrophe
    text = _RE_APOSTROPHE.sub("'", text)

    # 4. Canonical em-dash between spaces
    text = _RE_EM_DASH.sub("—", text)

    # 5. Canonical typographic chevrons
    parts = _RE_QUOTES.split(text)
    if len(parts) > 1:
        res = []
        for i, p in enumerate(parts):
            res.append(p)
            if i < len(parts) - 1:
                res.append("«" if i % 2 == 0 else "»")
        text = "".join(res)

    return text.strip()


class DualMovaOrthographyClassifier:
    """
    Symmetric discriminative multi-norm classifier for Belarusian textual corpora (v3.0).
    Categorizes input text into Official Standard ('nark'), Classical Standard ('tarask'),
    Invariant Common Core ('invariant'), or anomalies / mixed varieties ('rejected').
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

    # v3.0 Hyperparameters
    DECISION_THRESHOLD: float = 1.25
    MAX_DOC_PRIOR: float = 4.0
    DOC_SHRINKAGE_KAPPA: float = 6.0      # Empirical Bayes pseudo-count for document (~3 strong markers)
    NEIGH_SHRINKAGE_KAPPA: float = 2.5    # Empirical Bayes pseudo-count for local neighborhood
    NEIGH_DECAY_GAMMA: float = 0.65       # Bidirectional Laplace decay parameter per segment step
    NOISE_TOLERANCE_MU: float = 0.15      # Citation noise tolerance inside homogeneous texts
    BETA_CONFLICT: float = 0.35           # Context weight multiplier under code-switching conflict
    TAU_CONFLICT: float = 2.0             # Exponential decay scale for conflict gating

    # Legacy compatibility aliases
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

        # CASCADE 0: STAGE 1 LID, UNICODE HYGIENE & RUSSIAN DETECTOR
        self.re_russian_chars = re.compile(r"[ищъИЩЪ]")
        self.re_word_tokens = re.compile(r"[а-яёіўґА-ЯЁІЎҐ']+(?:-[а-яёіўґА-ЯЁІЎҐ']+)*")
        self.re_mixed_script = re.compile(
            r"\b(?:[а-яёіўґА-ЯЁІЎҐ]+[a-zA-Z]+|[a-zA-Z]+[а-яёіўґА-ЯЁІЎҐ]+)\b"
        )
        self.re_ushort_valid = re.compile(r"[аеёіоуыэюя]ў\b", re.IGNORECASE)
        self.re_ushort_broken = re.compile(
            r"\b(?!(?:шоу|ток-шоу|траур|фауна|сауна|пауза|клоун|страус|баул|аул|караул)\b)"
            r"[а-яёіўґ]*[аеёіоуыэюя]у\b",
            re.IGNORECASE,
        )

        # Stage 1 LID: Russian Phonological and Morphological Detector (catches Russian text without [и, щ, ъ])
        self.re_russian_phonology = re.compile(
            r"\b(?:"
            # 1. Hard post-alveolars [ж, ч, ш, р] with iotated vowels [е, ё, ю, я]
            r"(?!(?:жэле|жэтон|пюрэ|парашут|журы|брошур)[а-яёіўґ']*)'?"
            r"[а-яёіўґ']*[жчшр][еёюя][а-яёіўґ']*|"
            # 2. Non-affricated dentals [д, т] + [е, ё, ю, я] (absence of Belarusian dzekanne/tsekanne)
            r"(?!(?:дэпутат|дэмакр|дэклар|дэтал|дэфект|дэлегат|дэкан|дырэкт|дырэкц|тэле|тэатр|тэор|тэхн|тэмп|тэндэнц|тэрытор|тэмпер|тэкст|тэрмін|матэры|катэг)[а-яёіўґ']*)'?"
            r"[а-яёіўґ']*[дт][еёюя][а-яёіўґ']*|"
            # 3. Russian adjectival case endings -ого / -его
            r"[а-яёіўґ']{2,}(?:ого|его)\b|"
            # 4. Frequent Russian functional words without [и, щ, ъ]
            r"(?:он|она|оно|что|это|этот|эта|вчера|сегодня|после|перед|через|между|около|"
            r"потому|поэтому|также|тоже|только|если|чтобы|когда|всегда|очень|здесь|почему|зачем|сколько)\b"
            r")",
            re.IGNORECASE,
        )

        # Trasyanka detector expanded with colloquial intrusions and non-Belarusian particles
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
            r"(?:толька|еслі|патаму|патом|дажэ|очэнь|кагда|всё|сейчас|астаноўк[а-яёіўґ']*)\b|"
            r"(?!(?:пед|мед|паліт|фіз|хім|буд|гандаль|дзярж|кам|край|між|над|пад|прад|раз|роз|сац|спец|тэх|універ|юрыд)ін[а-яёіўґ']*)"
            r"[а-яёіў]*(?:ді|ті)[а-яёіў]*\b"
            r")|,\s*но\b",
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
            r"|(?:не|мала)?пісьм[еёіюя][а-яёіўґ'’ʼ`]*"
            r"|(?:па|за)?цьм(?:ян|ен|ін|е)[а-яёіўґ'’ʼ`]*"
            r"|васьм[іёю][а-яёіўґ'’ʼ`]*"
            r"|ледзьве"
            r"|разьб(?:яр|лён|е)[а-яёіўґ'’ʼ`]*"
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

        # Prefix/prepositional assimilative soft sign in Taraškievica (зь-, бязь-, празь-, нязь-) before vowels/soft consonants
        self.re_tarask_prefix_soft_sign = re.compile(
            r"(?<![а-яёўіґ'’ʼ`])(?:"
            r"(?:зь|бязь|безь|празь|нязь|разь|адзь|падзь|надзь|усparentsь|уззь|абзь)"
            r"(?=[а-яёўіґ'’ʼ`]{2,})"
            r"|зь\s+(?=[а-яёўіґ'’ʼ`]{2,})"
            r")",
            re.IGNORECASE,
        )

        # Soft elongated geminates in Taraškievica (цьц, зьз, сьс, ньн, льл...)
        self.re_tarask_soft_long = re.compile(
            r"(?<![а-яёўіґ'’ʼ`])[а-яёіўґ'’ʼ`]*(?:"
            r"зьз|сьс|ньн|льл|цьц|дзьдз"
            r")[еёіюя][а-яёўіґ'’ʼ`]*",
            re.IGNORECASE,
        )

        # Hard geminates in Narkamaŭka (цц, зз, сс, нн, лл, дздз before iotated vowels)
        self.re_nark_hard_long = re.compile(
            r"(?<![а-яёўіґ'’ʼ`])[а-яёіўґ'’ʼ`]*(?:"
            r"(?<![зсцнл])цц|(?<![зсцнл])зз|(?<![зсцнл])сс|(?<![зсцнл])нн|(?<![зсцнл])лл|(?<![зсцнл])дздз"
            r")[еёіюя][а-яёўіґ'’ʼ`]*",
            re.IGNORECASE,
        )

        # CASCADE 2: PHONOTACTIC CONSTRAINTS & UNMARKED CONSONANT SEQUENCES
        # Unmarked assimilation in Narkamaŭka (свет, снег, дзверы, песня, змена, свята...)
        self.re_nark_unmarked_assimilation = re.compile(
            r"(?:(?<=^)|(?<=[а-яёўіґ'’ʼ`\s\-]))"
            r"(?:дз|[зсц])"
            r"(?:дз|[бвджзлмнпрстфцчш])"
            r"(?=[еёіюя])",
            re.IGNORECASE,
        )

        # Distinctive prefixes with apostrophe in Narkamaŭka vs soft-sign in Taraškievica (з'езд vs зьезд, без'языкі vs бязьлітасны)
        # Note: prefixes аб-, пад-, ад-, над-, раз- take apostrophe in BOTH standards (BKP-2005 § 10)
        self.re_nark_prefix_apostrophe = re.compile(
            r"(?<![а-яёўіґ'’ʼ`])(?:"
            r"(?:з|без|праз|уз)'[еёіюя][а-яёўіґ'’ʼ`]*"
            r")",
            re.IGNORECASE,
        )

        # Suffixal affricatization (-дз- / -ц- from д / т before soft suffixes)
        self.re_tarask_affricate_assim = re.compile(
            r"(?<![а-яёўіґ'’ʼ`])[а-яёіўґ'’ʼ`]*(?:"
            r"цьбіт|дзьбіт|цьбін|дзьбін|цьвяр|дзьвяр|цьмя|дзьмя"
            r")[а-яёўіґ'’ʼ`]*",
            re.IGNORECASE,
        )
        self.re_nark_affricate_unassimilated = re.compile(
            r"(?:(?<=^)|(?<=[а-яёўіґ'’ʼ`\s\-]))"
            r"(?:тв|дв)"
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
        # Note: 'дэпутат' and 'калектыў' are invariant across both modern standards (BKP-2005 Chapter 2 & NKBM-2008)
        self.re_nark_jakanie_exceptions = re.compile(
            r"(?<![а-яёўіґ'’ʼ`])(?:"
            r"веліч(?:н|ав|эзн|адушн|асвецк|амучан|арос)[а-яёўіґ'’ʼ`]*"
            r"|(?:сем|восем|дзевят)наццац[а-яёўіґ'’ʼ`]*"
            r"|(?:пяць|шэсць|сем|восем)дзесят[а-яёўіґ'’ʼ`]*"
            r"|дзевятнаццат[а-яёўіґ'’ʼ`]*"
            r"|сезон[а-яёўіґ'’ʼ`]*|секунд[а-яёўіґ'’ʼ`]*|медал[яіюёёмўх][а-яёўіґ'’ʼ`]*|медаль\b|метро\b|метрапалітэн[а-яёўіґ'’ʼ`]*"
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
            r")[а-яёіўґ'’ʼ`]*",
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

    def _compute_context_field(
        self, local_scores: List[float]
    ) -> Tuple[float, List[float]]:
        """
        Computes in linear O(M) time:
        1. Global Empirical Bayes document prior L_doc_eb with sample-size shrinkage.
        2. Bidirectional Laplace context field L_ctx[i] for each segment i = 0..M-1.
        """
        m = len(local_scores)
        if m == 0:
            return 0.0, []

        doc_taras_ev = sum(s for s in local_scores if s > 0.0)
        doc_nark_ev = sum(-s for s in local_scores if s < 0.0)
        total_ev = doc_taras_ev + doc_nark_ev

        if total_ev > 0.0:
            direction = (doc_taras_ev - doc_nark_ev) / total_ev
            scaled_dir = max(-1.0, min(1.0, direction / (1.0 - self.NOISE_TOLERANCE_MU)))
            reliability = total_ev / (total_ev + self.DOC_SHRINKAGE_KAPPA)
            l_doc_eb = self.MAX_DOC_PRIOR * reliability * scaled_dir
        else:
            l_doc_eb = 0.0

        # Bidirectional Laplace recurrence O(M) for local sections (prefaces, chapters, quotes)
        gamma = self.NEIGH_DECAY_GAMMA
        fwd_taras, fwd_nark = [0.0] * m, [0.0] * m
        bwd_taras, bwd_nark = [0.0] * m, [0.0] * m

        for i in range(1, m):
            prev_s = local_scores[i - 1]
            t_prev = prev_s if prev_s > 0.0 else 0.0
            n_prev = -prev_s if prev_s < 0.0 else 0.0
            fwd_taras[i] = gamma * (fwd_taras[i - 1] + t_prev)
            fwd_nark[i] = gamma * (fwd_nark[i - 1] + n_prev)

        for i in range(m - 2, -1, -1):
            next_s = local_scores[i + 1]
            t_next = next_s if next_s > 0.0 else 0.0
            n_next = -next_s if next_s < 0.0 else 0.0
            bwd_taras[i] = gamma * (bwd_taras[i + 1] + t_next)
            bwd_nark[i] = gamma * (bwd_nark[i + 1] + n_next)

        l_ctx_list: List[float] = []
        for i in range(m):
            nt = fwd_taras[i] + bwd_taras[i]
            nn = fwd_nark[i] + bwd_nark[i]
            n_ev = nt + nn
            if n_ev > 0.0:
                n_dir = (nt - nn) / n_ev
                n_rel = n_ev / (n_ev + self.NEIGH_SHRINKAGE_KAPPA)
                l_neigh = self.MAX_DOC_PRIOR * n_rel * n_dir
                # Interpolate between local neighborhood field and global document EB prior
                l_ctx = n_rel * l_neigh + (1.0 - n_rel) * l_doc_eb
            else:
                l_ctx = l_doc_eb
            l_ctx_list.append(l_ctx)

        return l_doc_eb, l_ctx_list

    def _combine_local_and_context(self, local_score: float, l_ctx: float) -> float:
        """
        Direction-dependent (Conflict-Aware) aggregation of local score and context:
        - Agreement or Neutrality (local_score == 0 or local_score * l_ctx >= 0):
          context is inherited without artificial attenuation (beta = 1.0).
        - Conflict / Inset Quote (local_score * l_ctx < 0):
          context is exponentially suppressed (beta_conflict = 0.35 * exp(-|local| / 2.0)).
        """
        clipped_ctx = max(-self.MAX_DOC_PRIOR, min(self.MAX_DOC_PRIOR, l_ctx))
        if local_score == 0.0 or (local_score * clipped_ctx >= 0.0):
            return local_score + clipped_ctx
        else:
            beta = self.BETA_CONFLICT * math.exp(-abs(local_score) / self.TAU_CONFLICT)
            return local_score + beta * clipped_ctx

    def compute_doc_prior(self, segments: List[str]) -> float:
        """
        Computes the Empirical Bayes log-odds prior score (L_doc_eb) across an entire document.
        """
        raw_scores = []
        for text in segments:
            norm_text = normalize_typography(text)
            words = self.re_word_tokens.findall(norm_text)
            if len(words) < 4:
                raw_scores.append(0.0)
                continue

            masked_for_palatal = self.re_nark_legal_palatal_seam.sub(" ", norm_text)
            counts = {
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
            s = sum(counts[k] * self.WEIGHTS[k] for k in counts if counts[k] > 0)
            raw_scores.append(s)

        l_doc_eb, _ = self._compute_context_field(raw_scores)
        return l_doc_eb

    def classify(self, text: str, doc_prior_log_odds: float = 0.0) -> RouteResult:
        """
        Classifies an individual text segment with conflict-aware document-prior inheritance.
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

        # 1. Cascade 0: Non-Belarusian characters, Russian Phonology, OCR homoglyphs, broken short-u, Trasyanka
        ru_chars = len(self.re_russian_chars.findall(norm_text))
        cyr_chars = sum(len(w) for w in words)
        if cyr_chars > 0 and (ru_chars / cyr_chars) > 0.002:
            return RouteResult(
                label="rejected",
                text_original=norm_text,
                text_tagged="",
                metrics={"reason": "REJECT_RUSSIAN_CHARS", "ru_chars": ru_chars}
            )

        # Stage 1 LID: Russian Phonological & Morphological Filter
        ru_phonology_hits = self.re_russian_phonology.findall(norm_text)
        if len(ru_phonology_hits) >= 2 or (total_words < 12 and len(ru_phonology_hits) >= 1) or (len(ru_phonology_hits) / max(total_words, 1) >= 0.15):
            return RouteResult(
                label="rejected",
                text_original=norm_text,
                text_tagged="",
                metrics={"reason": "REJECT_RUSSIAN_PHONOLOGY", "hits": ru_phonology_hits[:5]}
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
        if (valid_ushort + broken_ushort) >= 5 and broken_ushort / (valid_ushort + 1.0) > 0.15:
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

        # 2. Extract differential features across all 23 calibrated families
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

        # Contextual Gating for Stylistic Archaic Feminine Genitive Adjective (-ае/-яе) in Narkamaŭka editions
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

        # 4. Local Score Formulation across all 23 features
        local_score = sum(counts[feat] * self.WEIGHTS[feat] for feat in counts if counts[feat] > 0)

        # 5. Direction-Dependent (Conflict-Aware) Context Combination
        final_score = self._combine_local_and_context(local_score, doc_prior_log_odds)
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

        # 6. Decision Routing: Invariant Core vs Rejected vs Certified Norm
        if abs(final_score) < self.DECISION_THRESHOLD:
            if total_ev == 0 and abs(doc_prior_log_odds) < 0.2:
                # Certified Invariant Core: legitimate Belarusian text without differential markers
                return RouteResult(
                    label="invariant",
                    text_original=norm_text,
                    text_tagged=f"<orth_invariant>{norm_text}</orth_invariant>",
                    metrics={**metrics, "reason": "CERTIFIED_INVARIANT_CORE"}
                )
            else:
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
        DualMova v3.0 Single-Pass High-Throughput Document Processor:
        1. Extracts phonological counts and local scores for all segments in a single pass.
        2. Computes Empirical Bayes global document prior and bidirectional Laplace context field.
        3. Applies conflict-aware gating and routes each segment to nark, tarask, invariant, or rejected.
        """
        if not segments:
            return 0.0, []

        parsed = []
        raw_local_scores: List[float] = []

        for text in segments:
            norm_text = normalize_typography(text)
            words = self.re_word_tokens.findall(norm_text)
            total_words = len(words)

            if total_words < 4:
                parsed.append(("too_short", norm_text, total_words, None, 0.0))
                raw_local_scores.append(0.0)
                continue

            ru_chars = len(self.re_russian_chars.findall(norm_text))
            cyr_chars = sum(len(w) for w in words)
            if cyr_chars > 0 and (ru_chars / cyr_chars) > 0.002:
                parsed.append(("ru_chars", norm_text, ru_chars, None, 0.0))
                raw_local_scores.append(0.0)
                continue

            ru_phonology_hits = self.re_russian_phonology.findall(norm_text)
            if len(ru_phonology_hits) >= 2 or (total_words < 12 and len(ru_phonology_hits) >= 1) or (len(ru_phonology_hits) / max(total_words, 1) >= 0.15):
                parsed.append(("ru_phonology", norm_text, ru_phonology_hits, None, 0.0))
                raw_local_scores.append(0.0)
                continue

            mixed_words = self.re_mixed_script.findall(norm_text)
            if len(mixed_words) / total_words > 0.01:
                parsed.append(("mixed_script", norm_text, len(mixed_words), None, 0.0))
                raw_local_scores.append(0.0)
                continue

            valid_ushort = len(self.re_ushort_valid.findall(norm_text))
            broken_ushort = len(self.re_ushort_broken.findall(norm_text))
            if (valid_ushort + broken_ushort) >= 5 and broken_ushort / (valid_ushort + 1.0) > 0.15:
                parsed.append(("broken_ushort", norm_text, broken_ushort, None, 0.0))
                raw_local_scores.append(0.0)
                continue

            trasianka_hits = self.re_trasianka.findall(norm_text)
            if len(trasianka_hits) >= 2 or (total_words < 15 and len(trasianka_hits) >= 1):
                parsed.append(("trasianka", norm_text, trasianka_hits, None, 0.0))
                raw_local_scores.append(0.0)
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

            local_score = sum(counts[feat] * self.WEIGHTS[feat] for feat in counts if counts[feat] > 0)
            parsed.append(("valid", norm_text, total_words, counts, local_score))
            raw_local_scores.append(local_score)

        # Compute EB prior and bidirectional Laplace context field in linear O(M)
        l_doc_eb, l_ctx_list = self._compute_context_field(raw_local_scores)

        results: List[RouteResult] = []
        for item, l_ctx in zip(parsed, l_ctx_list):
            status = item[0]
            norm_text = item[1]
            if status == "too_short":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "too_short", "word_count": item[2]}))
            elif status == "ru_chars":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "REJECT_RUSSIAN_CHARS", "ru_chars": item[2]}))
            elif status == "ru_phonology":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "REJECT_RUSSIAN_PHONOLOGY", "hits": item[2][:5]}))
            elif status == "mixed_script":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "REJECT_OCR_HOMOGLYPH", "count": item[2]}))
            elif status == "broken_ushort":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "REJECT_OCR_USHORT_LOSS", "broken": item[2]}))
            elif status == "trasianka":
                results.append(RouteResult(label="rejected", text_original=norm_text, text_tagged="", metrics={"reason": "REJECT_TRASIANKA_BELAZAR", "hits": item[2]}))
            else:
                counts = dict(item[3])
                local_score = item[4]

                nark_ev = sum(v for k, v in counts.items() if k.startswith("nark_") and v > 0)
                hard_taras_ev = sum(v for k, v in counts.items() if k.startswith("tarask_") and k != "tarask_fem_gen_adj" and v > 0)
                if counts["tarask_fem_gen_adj"] > 0 and hard_taras_ev == 0 and (nark_ev > 0 or l_ctx <= -2.0):
                    counts["tarask_fem_gen_adj"] = 0
                    local_score = sum(counts[feat] * self.WEIGHTS[feat] for feat in counts if counts[feat] > 0)

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

                final_score = self._combine_local_and_context(local_score, l_ctx)
                confidence = 1.0 / (1.0 + math.exp(-abs(final_score)))

                metrics = {
                    "confidence": round(confidence, 4),
                    "effective_log_odds": round(final_score, 4),
                    "local_score": round(local_score, 4),
                    "context_score": round(l_ctx, 4),
                    "doc_prior_eb": round(l_doc_eb, 4),
                    "nark_evidence": nark_ev,
                    "taras_evidence": taras_ev,
                    "chimera_index": round(chimera_index, 4),
                    "features": features,
                }

                if abs(final_score) < self.DECISION_THRESHOLD:
                    if total_ev == 0:
                        results.append(RouteResult(
                            label="invariant",
                            text_original=norm_text,
                            text_tagged=f"<orth_invariant>{norm_text}</orth_invariant>",
                            metrics={**metrics, "reason": "CERTIFIED_INVARIANT_CORE"}
                        ))
                    else:
                        results.append(RouteResult(
                            label="rejected",
                            text_original=norm_text,
                            text_tagged="",
                            metrics={**metrics, "reason": "REJECT_LOW_CONFIDENCE_AMBIGUOUS"}
                        ))
                elif final_score > 0:
                    results.append(RouteResult(
                        label="tarask",
                        text_original=norm_text,
                        text_tagged=f"<orth_taras>{norm_text}</orth_taras>",
                        metrics=metrics,
                    ))
                else:
                    results.append(RouteResult(
                        label="nark",
                        text_original=norm_text,
                        text_tagged=f"<orth_nark>{norm_text}</orth_nark>",
                        metrics=metrics,
                    ))

        return l_doc_eb, results


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
        # Narkamaŭka prose
        ("Танк гэты стаяў узняты на ўзгорак з супрацьлеглага боку. Трэба было ісці праз дзверы з дрыжаннем, збіраць касці сляпых.", "nark"),
        ("Вядомы беларускі пісьменнік напісаў новае пісьмо, дзе распавёў пра сваю просьбу і сустрэчу з людзьмі.", "nark"),
        ("Станьце тут, калі ласка, і паглядзіце на гэтае дзіўнае зацьменне сонца.", "nark"),
        ("Сучаснае пакаленне чытае кнігі, вывучае дакументы і шукае праўды.", "nark"),
        ("План развіцця горада Мінска быў зацверджаны ў новай сістэме.", "nark"),
        ("Арганаўты стоўпіліся на палубе, любаваліся велічным відовішчам... Хвалі неслі «Арго» проста на скалы. На носе карабля стаяў Язон... Язон выпусціў птушку ў праход... Так паўстаюць перад намі героі Элады.", "nark"),
        # Taraškievica prose
        ("Танк гэты стаяў узьняты на ўзгорак. Яны ня ведалі, як знайсьці праўду ў гэтым сьвеце. Гэта вялікае пытаньне новага жыцьця і грамадзкай радасьці.", "tarask"),
        ("Плян разьвіцьця гораду Менску быў зацьверджаны ў новай сыстэме.", "tarask"),
        ("Разглядаецца праблема аб’яднаньня, дзе адбываецца новае вясельле і адчыняюцца дзьверы.", "tarask"),
        ("Яна не магла і не хацела заставацца без вады і без дапамогі, але сьнег засыпаў усе сьцежкі.", "tarask"),
        # Invariant Belarusian text (identified as invariant core when isolated)
        ("Уздоўж узбярэжжа раскінулася зацішша, ноччу ваенны патруль вёз збожжа і тонны грузу.", "nark"),
        ("Хлопчык глядзеў у акно і думаў пра заўтрашні дзень.", "invariant"),
        ("Стары дзед сядзеў на драўлянай лаўцы каля хаты.", "invariant"),
        # Russian intrusions (with and without [и, щ, ъ])
        ("Этот текст написан на русском языке и должен быть отброшен.", "rejected"),
        ("Государство должно уважать права каждого человека в нашей стране.", "rejected"),
        ("Мама мыла раму, а папа делал новый деревянный стол в комнате.", "rejected"),
        # Trasyanka
        ("Ён пашол у магазін і сказаў, што толька еслі патаму што робітся работа.", "rejected"),
        ("Мы чакалі аўтобус цэлы час, но ён так і не прыехаў на нашу астаноўку.", "rejected"),
    ]

    print("=== DUALMOVA v3.0 CLASSIFIER INLINE VERIFICATION ===\n")
    all_ok = True
    for text, exp in test_samples:
        r = router.route(text)
        ok = (r.label == exp)
        if not ok:
            all_ok = False
        status = "[PASS]" if ok else "[FAIL]"
        lo = r.metrics.get("effective_log_odds", 0.0)
        conf = r.metrics.get("confidence", 0.0)
        reaz = r.metrics.get("reason", "")
        extra = f" (reason: {reaz})" if reaz else ""
        print(f"{status} Expected: {exp:10} | Obtained: {r.label:10} (score={lo:+.2f}, conf={conf:.3f}){extra} | {text[:55]}...")

    print(f"\nRESULT: {'ALL VERIFICATION SAMPLES PASSED (100%)!' if all_ok else 'TEST FAILURE DETECTED!'}")
