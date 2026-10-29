# DualMova: Empirical Audit of Rejected and Edge-Case Paragraphs

## Executive Summary

In processing the full literary corpus from `knihi.com` (5,059 verified historical documents), DualMova extracted **347,717 total paragraphs and strophes**.
While **314,423 segments** were certified into pristine normative registers (**215,365 Narkamaŭka** and **99,058 Classical Taraškievica**), **33,290 segments (9.57%)** were routed to the rejection pool (`rejected.jsonl`).

To ensure total transparency, reproducibility, and forensic traceability for linguistic audits, this document catalogs **30 real-world paragraph examples for each of the 7 rejection categories** (total: 210 concrete excerpts), complete with author, work title, character count, and router classification metrics.

### Rejection Category Frequency Distribution

| Category Code | Paragraph Count | Percentage of Rejects | Description |
| :--- | :---: | :---: | :--- |
| `REJECT_LOW_CONFIDENCE_AMBIGUOUS` | **15,601** | 46.86% | Segments where subtle or weak markers were detected, but the Bayesian posterior probability P(norm) fell below the strict classification threshold (P < 0 |
| `REJECT_RUSSIAN_CHARS` | **15,374** | 46.18% | Segments containing non-Belarusian Cyrillic graphemes (such as Russian и, щ, ъ, or Ы after velars) |
| `REJECT_NEUTRAL_NO_CONTEXT` | **1,582** | 4.75% | Short or isolated paragraphs where every single word is identical across both Narkamaŭka and Classical Taraškievica (zero soft-sign assimilation opportunities, no non-Slavic loanwords, no pre-stressed proclitics, no iotated geminates), and where document-level prior inheritance (L_doc) was uninitialized or neutral |
| `REJECT_ORTHOGRAPHIC_CHIMERA` | **188** | 0.56% | Text displaying concurrent, conflicting normative features (e |
| `REJECT_TRASIANKA_BELAZAR` | **332** | 1.00% | Corrupted texts featuring rule-breaking morphemes characteristic of Belazar automated machine translation, Russian-Belarusian phonetic pidgin (Trasyanka), or catastrophic encoding replacements |
| `REJECT_OCR_HOMOGLYPH` | **179** | 0.54% | Paragraphs suffering from optical character recognition (OCR) substitution errors, such as Latin c, p, a, o, e, x, i erroneously substituted into Cyrillic word tokens during historical book digitization |
| `REJECT_OCR_USHORT_LOSS` | **34** | 0.10% | Texts where scanning software or typography converted post-vocalic ў into regular Cyrillic у, violating the fundamental phonological invariant of the Belarusian language (§ 11 NKBM-2008 and BKP-2005 § 3) |
| **Total Rejected** | **33,290** | **100.00%** | Full uncurated/noisy segment pool |

### Key Linguistic Discoveries & Router Edge Cases Identified

A rigorous manual and automated examination of these 210 concrete excerpts revealed several critical linguistic phenomena that explain the rejections and inform future router iterations:

1. **The Participle / Native Root Collision Trap (`-ушчы / -ашчы`):**
   - In Cascade 0, the Trasyanka filter penalizes Russian-style active participles (`-ушч-`, `-ашч-` via regex `[а-яёіў]+(?:ушч|юшч|ашч|яшч)(?:ы|ая|ае|ыя|ага|аму|ым|ых)`).
   - *Collateral Damage:* This regex unintentionally flags native Belarusian nouns and adjectives sharing these letter clusters:
     - `пушча` → `пушчы` (*Белавежскія пушчы*, *у пушчы*): occurring in classical works by Francišak Bahuševič, Francysk Skaryna, Arkadź Smolič, Janka Kupala, and Karuś Kahaniec.
     - `гушча` → `гушчы` (*з гушчы сялян* — Janka Niamanski).
     - `пашча` → `пашчы` (*з пашчы льва* — Mialecij Smatrycki).
     - `хрушч` → `хрушчы` (*Сватоўе-хрушчы* — Maksim Bahdanovič).
     - Native adjectives like `прапашчы` (U. Žyłka), `хітрушчы` (S. Błatun).
     - 3rd-person verbs in `-шчае` derived from `-шчаць` (*змяшчае* in Jan Vislicki, *абвяшчае* in Janka Maŭr, *прычашчае* in Jakub Kolas).
   - *Remedy:* The participle regex requires a strict exception whitelist of native root lemmas (`пушч-`, `гушч-`, `пашч-`, `хрушч-`, `змяшч-`, `памяшч-`, `абвяшч-`, `прапашч-`, `хітрушч-`).

2. **Pre-Codification 18th & 19th Century Historical Orthography:**
   - Texts written before modern codification (e.g. Kastuś Kalinoŭski's *«Лісты з-пад шыбеніцы»* 1864, Kajetan Marašeŭski's *«Камедыя»* 1787) feature phonetic dialect spellings such as `толька` instead of modern `толькі`. The router correctly separates these from codified 20th-century standards.

3. **Compound Word Phonetic Merging:**
   - The token `педінстытуце` (J. Vasilionak) was flagged by `(?:ді|ті)` because the compound morpheme boundary (`пед-інстытут`) placed `д` before `і`. Morpheme-aware tokenization resolves this boundary.

4. **Code-Switching and Satirical Dialogue:**
   - Classical authors intentionally employ Russian or Trasyanka dialogue for characterization (e.g. Janka Kupala's satirical Tsarist priest in *«Тутэйшыя»* speaking `В нынешнія врэмена дажэ его прэосвяшчэнство воззавідовало...`, or Jułijana Vitan-Dubiejkaŭskaja citing Russian proverbs in her memoirs). The router's rejection of these segments is **linguistically correct**, safeguarding the clean monolingual corpus.

5. **True Orthographic Chimeras:**
   - Transitional post-1988 texts (e.g. ecclesiastical catecheses and unedited diaspora journals) frequently combine Taraškievica soft signs (`сьвет`, `хрысьціянскай`, `выданьня`) with official Narkamaŭka morphology and toponymy (`Мінск`, unassimilated hard geminates). The Chimera detector cleanly isolates these hybrid registers.

---

## 1. Low Confidence / Ambiguous Alignment (`REJECT_LOW_CONFIDENCE_AMBIGUOUS`)

Segments where subtle or weak markers were detected, but the Bayesian posterior probability P(norm) fell below the strict classification threshold (P < 0.88 or |L| < 1.99), or where contradictory weak markers produced ambiguity. Rather than risking noisy label contamination, the engine conservatively drops these paragraphs.

**Audited Segment Count in Category:** 15,601 segments.
**Representative Real-World Samples:** 30 excerpts cataloged below.

### Sample 01 — Маўр Янка | *Амок*
- **Source Work:** Маўр Янка — *«Амок»*
- **Segment Length:** 243 characters
- **Router Diagnostics:** `confidence`: 0.7154, `effective_log_odds`: 0.9219, `local_score`: 1.8, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_loan_soft_l:1']}

> Застагналі, заплакалі дзеці, паліліся салёныя слёзы на салодкую расліну, а на худзенькіх спінах выступілі рыскі крыві. Зараз жа кінуліся на кроў мухі — «леры», абляпілі раны, але адагнаць іх нельга: трэба працаваць усе мінуты, якія ёсць у дні.

### Sample 02 — Баранавых Сымон | *Боты*
- **Source Work:** Баранавых Сымон — *«Боты»*
- **Segment Length:** 71 characters
- **Router Diagnostics:** `confidence`: 0.6596, `effective_log_odds`: 0.6614, `local_score`: 1.6, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_fem_gen_adj:1']}

> І мой дзядзька... ён мог бы заўсёды датрымаць свой тавар да гэтае цаны.

### Sample 03 — Канчэўскі Ігнат | *Вераснёвае пано*
- **Source Work:** Канчэўскі Ігнат — *«Вераснёвае пано»*
- **Segment Length:** 98 characters
- **Router Diagnostics:** `confidence`: 0.6625, `effective_log_odds`: -0.6746, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> І вада ў Вялейцы, ад зімна сіней і празрысцей,
> Гаманіць з камянём аб працёкшых гадох без устану...

### Sample 04 — Абуховіч Альгерд | *Старшына*
- **Source Work:** Абуховіч Альгерд — *«Старшына»*
- **Segment Length:** 81 characters
- **Router Diagnostics:** `confidence`: 0.7451, `effective_log_odds`: -1.0724, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> упершыню апублікаваны ў Беларускі календар «Нашай нівы» на 1915 г. − Вільня, 1915

### Sample 05 — Скарына Францыск | *З прадмовы да «Кнігі Іова»*
- **Source Work:** Скарына Францыск — *«З прадмовы да «Кнігі Іова»»*
- **Segment Length:** 59 characters
- **Router Diagnostics:** `confidence`: 0.6689, `effective_log_odds`: -0.7031, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> У кнізе Іова
> гаворыцца і пра тых,
> што зневажаюць паніжаных,

### Sample 06 — Пясецкі Сяргей | *Менская трылогія*
- **Source Work:** Пясецкі Сяргей — *«Менская трылогія»*
- **Segment Length:** 75 characters
- **Router Diagnostics:** `confidence`: 0.7415, `effective_log_odds`: -1.0538, `local_score`: 0.2, `nark_evidence`: 1, `taras_evidence`: 1, `chimera_index`: 1.0, `features`: {'nark': ['nark_loan_forms:1'], 'taras': ['tarask_lex_markers:1']}

> Сяргей Пясецкі
> Менская трылогія
> Спампаваць усё
> (
> m4a
> ) 
> 1.Яблычак.00a.Уступ

### Sample 07 — Васілёнак Яўген | *Адзіночная камера*
- **Source Work:** Васілёнак Яўген — *«Адзіночная камера»*
- **Segment Length:** 175 characters
- **Router Diagnostics:** `confidence`: 0.6596, `effective_log_odds`: 0.6614, `local_score`: 1.6, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_fem_gen_adj:1']}

> Павел як сам не свой ішоў на кухню, у знямозе апускаўся на табурэтку і так сядзеў да самае раніцы. Жонка не турбавала яго, бо аднаго разу ён быў шалёна накрычаў на яе за гэта.

### Sample 08 — Гурло Алесь | *«Абнімаецца вецер з бярозай...»*
- **Source Work:** Гурло Алесь — *««Абнімаецца вецер з бярозай...»»*
- **Segment Length:** 56 characters
- **Router Diagnostics:** `confidence`: 0.6689, `effective_log_odds`: -0.7031, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> І ўцірае з вачэй яе слёзы,
> Яны капаюць срэбрам на ганак.

### Sample 09 — Каліноўскі Кастусь | *Мужыцкая праўда, №1*
- **Source Work:** Каліноўскі Кастусь — *«Мужыцкая праўда, №1»*
- **Segment Length:** 283 characters
- **Router Diagnostics:** `confidence`: 0.6187, `effective_log_odds`: -0.4841, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Маскалі, чыноўнікі і многа паноў будуць перапыняць пісьмо наша да вас, но найдуцца людзі і з мужыкоў разумнейшыя, і з панскага роду, і з местачковых, што хочуць вашай свабоды, вашага шчасця,— яны то вам самі гэта пісьмо даваці будуць, каб вы зналі, хто ваш прыяцель, а хто ваш вораг.

### Sample 10 — Жаўрук Алесь | *«Ружа»*
- **Source Work:** Жаўрук Алесь — *««Ружа»»*
- **Segment Length:** 64 characters
- **Router Diagnostics:** `confidence`: 0.7471, `effective_log_odds`: -1.0832, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> А ці міг, ці век - не знаў ніхто там,
> Колькі моўчкі праляжалі мы

### Sample 11 — Корбан Уладзімір | *Малпін жарт*
- **Source Work:** Корбан Уладзімір — *«Малпін жарт»*
- **Segment Length:** 61 characters
- **Router Diagnostics:** `confidence`: 0.7169, `effective_log_odds`: -0.929, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Пасля начной адказнае работы
> Трэзор і Мурза спалі каля плота.

### Sample 12 — Краўцоў Макар | *Паварот да Горадна*
- **Source Work:** Краўцоў Макар — *«Паварот да Горадна»*
- **Segment Length:** 73 characters
- **Router Diagnostics:** `confidence`: 0.7491, `effective_log_odds`: -1.0937, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Ізноў я тут. Цябе вітаю,
> Мой родны Горадзен стары!
> Ізноў па вуліцах лятаю

### Sample 13 — Рак Сымон | *Гутарка аб беларускай мове*
- **Source Work:** Рак Сымон — *«Гутарка аб беларускай мове»*
- **Segment Length:** 242 characters
- **Router Diagnostics:** `confidence`: 0.5894, `effective_log_odds`: 0.3616, `local_score`: -0.2, `nark_evidence`: 1, `taras_evidence`: 1, `chimera_index`: 1.0, `features`: {'nark': ['nark_lex_markers:1'], 'taras': ['tarask_nia_biaz:1']}

> — На што-ж гэта?
> — Во мова наша — мужыцкая. На службе намучыўся я цераз яе, пакуль перавучыўся на расійскую. Цяпер так сама ня мала клопату набярэшся, як давядзецца, часамі, мець дзела ў судзе ці з якім начальствам На што ўжо — почта, а і там

### Sample 14 — Галубок Уладзіслаў | *Абразок*
- **Source Work:** Галубок Уладзіслаў — *«Абразок»*
- **Segment Length:** 62 characters
- **Router Diagnostics:** `confidence`: 0.763, `effective_log_odds`: -1.1693, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Наста і валіць проста да яго.
> — Чаго, рыбачка? — пытае кнігар.

### Sample 15 — Мікуліч Барыс | *Развітанне*
- **Source Work:** Мікуліч Барыс — *«Развітанне»*
- **Segment Length:** 208 characters
- **Router Diagnostics:** `confidence`: 0.6596, `effective_log_odds`: 0.6614, `local_score`: 1.6, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_fem_gen_adj:1']}

> Яму адказвае шыракаплечы шырокабароды пасажыр, вылушчваючы лыжачкай рэшткі з яечнае шкарлупкі. Прычмоквае, заядае булачкай, намазанай маслам. Жуюць, прычмокваюць, глытаюць, аблізваюцца, смокчуць усе ў вагоне.

### Sample 16 — Лучына Янка | *Паляўнічыя акварэлькі з Палесся*
- **Source Work:** Лучына Янка — *«Паляўнічыя акварэлькі з Палесся»*
- **Segment Length:** 566 characters
- **Router Diagnostics:** `confidence`: 0.5308, `effective_log_odds`: -0.1235, `local_score`: 0.9, `nark_evidence`: 1, `taras_evidence`: 1, `chimera_index`: 1.0, `features`: {'nark': ['nark_nie_biez_stressed:1'], 'taras': ['tarask_palatal_cluster:1']}

> Папуску даўшы паляўнічай раз ахвоце,
> Страляў калісь чачотак, вераб'ёў на плоце.
> Стары пабачыў Грышка, йшоў кудысь сабе,
> Сярдзіта плюнуў ды сказаў быў у журбе:
> «Панічу! эх, панічу! пахвалы не мецьмеш,
> Хоць стрэліш трапна й пташку, што ўпадзе, прыкмеціш.
> Набою шкода - раз, другое ж - без віны
> За што ж іх, дробных, бедных, біць, калі яны
> Завеяй, маразамі туляцца пад стрэхі?
> Дапраўды, грэх вялікі з гэтакай уцехі.
> Хіба ў лясох звяроў няма, панічу мой?
> Няхай бы волю там ахвоце даў сваёй.
> Забіць лася, ваўка, хоць шарака не тое,
> Што на чачотак, вераб'ёў псаваць набоі.

### Sample 17 — Нёманскі Янка | *Абмылка*
- **Source Work:** Нёманскі Янка — *«Абмылка»*
- **Segment Length:** 404 characters
- **Router Diagnostics:** `confidence`: 0.6596, `effective_log_odds`: 0.6614, `local_score`: 1.6, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_fem_gen_adj:1']}

> Прыйшоўшы раз на службу, доўгі час згадзя пасля тае канферэнцыі, Пятрусь знайшоў на стале нераскрыты канверт. Разарваўшы яго, ён выняў лісток добрае паперы. Старажоўская сямігодка запрашала яго на нейкі там вучнёўскі вечар. На другім баку была прыпіска: «Вы павінны быць безумоўна. Зося». Так і падпісала «Зося», а не Яніцкая. Што гэта азначае «павінны быць»? Загад, ці што? Адкуль гэтае права загадваць?

### Sample 18 — Сваяк Казімір | *Загляне сонца...*
- **Source Work:** Сваяк Казімір — *«Загляне сонца...»*
- **Segment Length:** 56 characters
- **Router Diagnostics:** `confidence`: 0.7645, `effective_log_odds`: -1.1778, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Загляне сонца ў наша ваконца,
> Хатку асвеціць праменьмі -

### Sample 19 — Лёсік Язэп | *Нёман*
- **Source Work:** Лёсік Язэп — *«Нёман»*
- **Segment Length:** 265 characters
- **Router Diagnostics:** `confidence`: 0.6596, `effective_log_odds`: 0.6614, `local_score`: 1.6, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_fem_gen_adj:1']}

> А штотыдня, у чацвер, у погоду й нягоду, узімку і ўлетку, варочае нетры Нямніска скарбовы рыбак. Закінуўшы волак і пабраўшы вяроўкі на плечы, ухаюць, пнуцца рыбакі-небаракі, стогнуць, ірвуцца з апошняе сілы, каб заможнае панства ў замку мела свежую рыбу да стала...

### Sample 20 — Маракоў Валеры | *«І зноў прыйшоў, і зноў пабачыў родны край...»*
- **Source Work:** Маракоў Валеры — *««І зноў прыйшоў, і зноў пабачыў родны край...»»*
- **Segment Length:** 149 characters
- **Router Diagnostics:** `confidence`: 0.7471, `effective_log_odds`: -1.0832, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> І зноў прыйшоў, і зноў пабачыў родны край,
> І сэрца... сэрца так запаланела.
> І зноў лясы агнём зялёным тут гараць,
> І зноў я свежы стаў і стаў я смелы.

### Sample 21 — Купала Янка | *Прымакі*
- **Source Work:** Купала Янка — *«Прымакі»*
- **Segment Length:** 88 characters
- **Router Diagnostics:** `confidence`: 0.6596, `effective_log_odds`: 0.6614, `local_score`: 1.6, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_fem_gen_adj:1']}

> Даміцэля. На табе! на табе! (Тыцкае хвігі.)
> Паланея (таксама) . На! на! А што? — смачна?

### Sample 22 — Чачот Ян | *Да мілых мужычкоў*
- **Source Work:** Чачот Ян — *«Да мілых мужычкоў»*
- **Segment Length:** 59 characters
- **Router Diagnostics:** `confidence`: 0.7169, `effective_log_odds`: -0.929, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Ды і я вам памагу
> Песеньку спяваці,
> Ды і я ж між вамі ўзрос

### Sample 23 — Улас Стары | *Абяцадла*
- **Source Work:** Улас Стары — *«Абяцадла»*
- **Segment Length:** 56 characters
- **Router Diagnostics:** `confidence`: 0.6625, `effective_log_odds`: -0.6746, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Цар - ў пачоце быў калісьці,
> Дуб - зімою ёсць без лісця,

### Sample 24 — Нікановіч Мікола | *На мяжы загонаў*
- **Source Work:** Нікановіч Мікола — *«На мяжы загонаў»*
- **Segment Length:** 229 characters
- **Router Diagnostics:** `confidence`: 0.6596, `effective_log_odds`: 0.6614, `local_score`: 1.6, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_fem_gen_adj:1']}

> Мо гэта яшчэ і таму, што заўтра, калі ападзе раса, мы будзем звозіць снапы са свайго палетка, дзе побач разаслаліся, як скінуць вокам, абшары жыта жыдоўскае камуны, і па гэтых абшарах заўтра, пад жняярку, будзе вязаць снапы Саня.

### Sample 25 — Жуковіч Васіль | *Мы бачылі Парыжскую вясну*
- **Source Work:** Жуковіч Васіль — *«Мы бачылі Парыжскую вясну»*
- **Segment Length:** 158 characters
- **Router Diagnostics:** `confidence`: 0.6689, `effective_log_odds`: 0.7031, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Васіль Жуковіч
> Мы бачылі Парыжскую вясну
> Спампаваць
> Крыніца: https://belarusachka.sch223.minskedu.gov.by/audyezapisy/praekt-tacciany-matafonavai-galasy-paetau

### Sample 26 — Багушэвіч Францішак | *Палясоўшчык*
- **Source Work:** Багушэвіч Францішак — *«Палясоўшчык»*
- **Segment Length:** 225 characters
- **Router Diagnostics:** `confidence`: 0.7675, `effective_log_odds`: -1.1943, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Ноч цёмная, мне дахаты трэба ісці праз сваю пушчу, праз оступ; дарогі ніякай няма, ідзеш логам, пасля градой, а там ізноў оступ; праз ручаёк доўгая старая елка, можа ўжо гадоў сто ляжыць вываратня, і па ёй пераходзім, бывала.

### Sample 27 — Зарэцкі Міхась | *42 дакументы*
- **Source Work:** Зарэцкі Міхась — *«42 дакументы»*
- **Segment Length:** 134 characters
- **Router Diagnostics:** `confidence`: 0.6596, `effective_log_odds`: 0.6614, `local_score`: 1.6, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_fem_gen_adj:1']}

> Сябра рэўкома Зянькевіч.
> 27 чэрвеня 19 г.
> Міламу майму мужу Саўку Ларывонаву Мякушу ад законнае супругі яго Арыны Аксентавай Мякушыхі.

### Sample 28 — Сержпутоўскі Аляксандр | *Дзяўчына*
- **Source Work:** Сержпутоўскі Аляксандр — *«Дзяўчына»*
- **Segment Length:** 255 characters
- **Router Diagnostics:** `confidence`: 0.6623, `effective_log_odds`: 0.6737, `local_score`: 1.6, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_fem_gen_adj:1']}

> Так плакала да прычытала тая дзевачка, а разбойнікі стаялі да слухалі. І мо першы раз закалола ім у сэрцы: мо першы раз пакаяліся яны, што пабілі тых людзей. Выплакалася дзяўчына да быццам акамянела, сядзіць каля халоднае маткі да пазірае, бы непрытомная.

### Sample 29 — Дудо Пятро | *Чортаў тузін*
- **Source Work:** Дудо Пятро — *«Чортаў тузін»*
- **Segment Length:** 152 characters
- **Router Diagnostics:** `confidence`: 0.7154, `effective_log_odds`: 0.9219, `local_score`: 1.8, `nark_evidence`: 0, `taras_evidence`: 1, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': ['tarask_loan_soft_l:1']}

> Ніна Адамаўна. Пастараюся для яе. Гэта не такая ўжо цяжкая праблема — вырашу... А цяпер, дарагая мая Лукер'я Іванаўна, ёсць у мяне да вас важная справа.

### Sample 30 — Кляшторны Тодар | *Восень*
- **Source Work:** Кляшторны Тодар — *«Восень»*
- **Segment Length:** 124 characters
- **Router Diagnostics:** `confidence`: 0.7491, `effective_log_odds`: -1.0937, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Слаўны вечар... Пагода ліпнёвая,
> А у садзе красуецца верасень...
> Колькі яблыкаў восень ружовая,
> Залацістая восень развесіла.

---

## 2. Russian Script Intrusion (`REJECT_RUSSIAN_CHARS`)

Segments containing non-Belarusian Cyrillic graphemes (such as Russian и, щ, ъ, or Ы after velars). In literary portals like knihi.com, these predominantly represent Russian editorial forewords, scholarly footnotes, historical Russian archival documents, or publisher colophons.

**Audited Segment Count in Category:** 15,374 segments.
**Representative Real-World Samples:** 30 excerpts cataloged below.

### Sample 01 — Раманаў Еўдакім | *Сборник памятников народного творчества в Северо-Западном крае*
- **Source Work:** Раманаў Еўдакім — *«Сборник памятников народного творчества в Северо-Западном крае»*
- **Segment Length:** 78 characters
- **Router Diagnostics:** `ru_chars`: 2

> Еўдакім Раманаў
> Сборник памятников народного творчества в Северо-Западном крае

### Sample 02 — Нікіфароўскі Мікалай | *Нечистики. Свод простонародных в Витебской Белоруссии сказаний о нечистой силе*
- **Source Work:** Нікіфароўскі Мікалай — *«Нечистики. Свод простонародных в Витебской Белоруссии сказаний о нечистой силе»*
- **Segment Length:** 120 characters
- **Router Diagnostics:** `ru_chars`: 9

> Мікалай Нікіфароўскі
> Нечистики. Свод простонародных в Витебской Белоруссии сказаний о нечистой силе
> Спампаваць
>  (81 МіБ)

### Sample 03 — Колас Якуб | *На ростанях*
- **Source Work:** Колас Якуб — *«На ростанях»*
- **Segment Length:** 91 characters
- **Router Diagnostics:** `ru_chars`: 3

> Ах, попалась, пташка, стой,
> Не уйдешь из сети!
> Не расстанемся с тобой
> Ни за что на свете! —

### Sample 04 — Езавітаў Кастусь | *Белоруссы и поляки : документы и факты из истории оккупации Белоруссии поляками в 1918 и 1919 годах*
- **Source Work:** Езавітаў Кастусь — *«Белоруссы и поляки : документы и факты из истории оккупации Белоруссии поляками в 1918 и 1919 годах»*
- **Segment Length:** 137 characters
- **Router Diagnostics:** `ru_chars`: 13

> Кастусь Езавітаў
> Белоруссы и поляки : документы и факты из истории оккупации Белоруссии поляками в 1918 и 1919 годах
> Спампаваць
>  (40 МіБ)

### Sample 05 — Малевіч Казімір | *От Сезанна до Суперматизма*
- **Source Work:** Малевіч Казімір — *«От Сезанна до Суперматизма»*
- **Segment Length:** 65 characters
- **Router Diagnostics:** `ru_chars`: 1

> Казімір Малевіч
> От Сезанна до Суперматизма
> Спампаваць
>  (2201 КіБ)

### Sample 06 — Сікорскі І. | *Реликвіи Іосафата Кунцевича*
- **Source Work:** Сікорскі І. — *«Реликвіи Іосафата Кунцевича»*
- **Segment Length:** 74 characters
- **Router Diagnostics:** `ru_chars`: 4

> Артыкул з "Журнала Министерства народного просвещения" (Декабрь 1870, СПб)

### Sample 07 — Чарот Міхась | *Молодняк*
- **Source Work:** Чарот Міхась — *«Молодняк»*
- **Segment Length:** 59 characters
- **Router Diagnostics:** `ru_chars`: 1

> Тут намедни буря выла нам,
> Ветер лязгал, как голодный волк,

### Sample 08 — Галубок Уладзіслаў | *Апошняе спатканне*
- **Source Work:** Галубок Уладзіслаў — *«Апошняе спатканне»*
- **Segment Length:** 219 characters
- **Router Diagnostics:** `ru_chars`: 14

> Чыноўнік (чытае). По указу Е. И. В. Магилевский окр. суд за убийство государственных лиц студенты: Аркадий Дзивны, Пав. Волчанский, Иван Гребенек и неоткрывший своего прозвища осуждены на смертную казнь через повешение.

### Sample 09 — Смоліч Аркадзь | *Географія Беларусі*
- **Source Work:** Смоліч Аркадзь — *«Географія Беларусі»*
- **Segment Length:** 286 characters
- **Router Diagnostics:** `ru_chars`: 1

> Урэшце на паўдні дзе-ня-дзе сеюць цукровыя бураки, з якіх робяць цукар. Гэтыя буракі аднак могуць расьці так сама блізка што і па ўсёй Беларусі на лепшых глыбокіх грунтох. Даўней у нас былі і свае цукраварні напр. у Пінскім павеце у двары Парэччы ды пазакрываліся дзеля розных прычынаў.

### Sample 10 — Гурын Міхаіл | *Кузнечное ремесло Полоцкой земли. IX-XIII вв.*
- **Source Work:** Гурын Міхаіл — *«Кузнечное ремесло Полоцкой земли. IX-XIII вв.»*
- **Segment Length:** 79 characters
- **Router Diagnostics:** `ru_chars`: 1

> Міхаіл Гурын
> Кузнечное ремесло Полоцкой земли. IX-XIII вв.
> Спампаваць
>  (16 МіБ)

### Sample 11 — Уварава Графіня | *Труды Девятого Археологического съезда в Вильне 1893.Том 1*
- **Source Work:** Уварава Графіня — *«Труды Девятого Археологического съезда в Вильне 1893.Том 1»*
- **Segment Length:** 111 characters
- **Router Diagnostics:** `ru_chars`: 3

> Графіня Уварава
> , 
> С.С. Слуцкі
> Труды Девятого Археологического съезда в Вильне 1893.Том 1
> Спампаваць
>  (219 МіБ)

### Sample 12 — Платун А. | *Итоги культурного строительства в БССР за 10 лет*
- **Source Work:** Платун А. — *«Итоги культурного строительства в БССР за 10 лет»*
- **Segment Length:** 79 characters
- **Router Diagnostics:** `ru_chars`: 3

> А. Платун
> Итоги культурного строительства в БССР за 10 лет
> Спампаваць
>  (14 МіБ)

### Sample 13 — Гартны Цішка | *Сокі цаліны*
- **Source Work:** Гартны Цішка — *«Сокі цаліны»*
- **Segment Length:** 278 characters
- **Router Diagnostics:** `ru_chars`: 1

> — Лепі менш пра гэта думай...
> Яны не заўважылі, як па суседству з імі, праз вуліцу, згуртавалася зборня моладзі, і паўночная пара напоўнілася заводзінамі розных абрыўкаў песень. Сярод апошніх можна было чуваць бадзёрыя напевы «Варшавянкі» і цягучыя, сумныя рэчытатывы «Девушки».

### Sample 14 — Насовіч Іван | *Дополненіе къ бѣлорусскому словарю*
- **Source Work:** Насовіч Іван — *«Дополненіе къ бѣлорусскому словарю»*
- **Segment Length:** 67 characters
- **Router Diagnostics:** `ru_chars`: 1

> Іван Насовіч
> Дополненіе къ бѣлорусскому словарю
> Спампаваць
>  (6 МіБ)

### Sample 15 — Вісліцкі Ян | *Пруская вайна*
- **Source Work:** Вісліцкі Ян — *«Пруская вайна»*
- **Segment Length:** 513 characters
- **Router Diagnostics:** `ru_chars`: 1

> 4 Нашыя продкі звычайна тых ворагаў гетамі звалі – Недастаткова ясна, чаму паэт лічыць, што ў старажытнасці прусаў называлі гетамі. Так, напрыклад, Мацей Мяхоўскі ў сваім творы "Tractatus de duabus Sarmatiis" ("Трактат пра дзве Сарматыі"; Кракаў, 1521) піша, што геты насялялі калісьці землі Еўрапейскай Сарматыі – тэрыторыі паміж Танаісам (Донам) і Віслай [гл.: Подосинов 1995, 437 ]. З гэтага пункту гледжання лагічней было б меркаваць, што геты жылі пераважна на тэрыторыі сучасных Украіны, Беларусі і Польшчы.

### Sample 16 — Каганец Карусь | *Яшчэ некалькі слоў пра перажыткі паганства ў беларусаў*
- **Source Work:** Каганец Карусь — *«Яшчэ некалькі слоў пра перажыткі паганства ў беларусаў»*
- **Segment Length:** 498 characters
- **Router Diagnostics:** `ru_chars`: 1

> Пан Сліжань няхай мне выбачае, што я, прачытаўшы ў № 88 «Северо-Западного края» яго «Два слова о пережитках поганства у белорусов», асмелюся яму трохі папярэчыць. Пан Сліжань піша, што ў беларусаў астаткі паганства неяк няясны, туманныя; што ў расіян і маларусаў яны шмат жывейшыя. А я скажу, што ў ніводнага народа хрысціянскага не захавалася так многа, так жывых і ясных слядоў паганства. Беларус хоч хрысціянін і набожны, а між тым ён напалавіну паганец, бо спаўняе верна ўсе абрады паганскія...

### Sample 17 — Таўбін Юлі | *Сирано де Бержерак*
- **Source Work:** Таўбін Юлі — *«Сирано де Бержерак»*
- **Segment Length:** 84 characters
- **Router Diagnostics:** `ru_chars`: 5

> С разбитою лютней идет поэт
> Сирано де Бержерак.
> Жизнь незаметно, как призрак прошла,

### Sample 18 — Шэйн Павал | *Белорусские народные песни, с относящимися к ним обрядами, обычиями и суевериями, с приложением объяснительного словаря и грамматических примечаний*
- **Source Work:** Шэйн Павал — *«Белорусские народные песни, с относящимися к ним обрядами, обычиями и суевериями, с приложением объяснительного словаря и грамматических примечаний»*
- **Segment Length:** 179 characters
- **Router Diagnostics:** `ru_chars`: 21

> Павал Шэйн
> Белорусские народные песни, с относящимися к ним обрядами, обычиями и суевериями, с приложением объяснительного словаря и грамматических примечаний
> Спампаваць
>  (18 МіБ)

### Sample 19 — Берында Памва | *Лексикон славеноросский. Имен толъкование*
- **Source Work:** Берында Памва — *«Лексикон славеноросский. Имен толъкование»*
- **Segment Length:** 119 characters
- **Router Diagnostics:** `ru_chars`: 13

> Месца і год выдання: З типографии общежителнаго монастыра Кутеинскаго тщанием тояжде обители иноков типом издася, 1653.

### Sample 20 — Бяссонаў Пётар | *Белорусские песни, с подробными объяснениями их творчества и языка, с очерками народного обряда,*
- **Source Work:** Бяссонаў Пётар — *«Белорусские песни, с подробными объяснениями их творчества и языка, с очерками народного обряда,»*
- **Segment Length:** 132 characters
- **Router Diagnostics:** `ru_chars`: 9

> Пётар Бяссонаў
> Белорусские песни, с подробными объяснениями их творчества и языка, с очерками народного обряда,
> Спампаваць
>  (15 МіБ)

### Sample 21 — Скарына Францыск | *Прадмова да ўсёй Бібліі*
- **Source Work:** Скарына Францыск — *«Прадмова да ўсёй Бібліі»*
- **Segment Length:** 341 characters
- **Router Diagnostics:** `ru_chars`: 27

> Библиа – греческим языком, по рускии сказуется – книги, тако убо святый Матфей починаеть Христово благовествование: «Библос генезеос Исусу Христу» (Мц. 1. 1), то ест по рускии – «Книга родства Исуса Христова». А можете тым именем называти вси книги Ветхаго и Новаго закону для достойности его, понеже БИБЛИЯ зуполная все то в собе замыкаеть.

### Sample 22 — Карскі Яўхім | *Белорусы. I. Введение в изучение языка и народной словесности*
- **Source Work:** Карскі Яўхім — *«Белорусы. I. Введение в изучение языка и народной словесности»*
- **Segment Length:** 95 characters
- **Router Diagnostics:** `ru_chars`: 5

> Яўхім Карскі
> Белорусы. I. Введение в изучение языка и народной словесности
> Спампаваць
>  (63 МіБ)

### Sample 23 — Сержпутоўскі Аляксандр | *Грамматический очерк белорусского наречия деревни Чудин Слуцкого уезда Минской губернии*
- **Source Work:** Сержпутоўскі Аляксандр — *«Грамматический очерк белорусского наречия деревни Чудин Слуцкого уезда Минской губернии»*
- **Segment Length:** 110 characters
- **Router Diagnostics:** `ru_chars`: 8

> Аляксандр Сержпутоўскі
> Грамматический очерк белорусского наречия деревни Чудин Слуцкого уезда Минской губернии

### Sample 24 — Маракоў Валеры | *Беларуси*
- **Source Work:** Маракоў Валеры — *«Беларуси»*
- **Segment Length:** 62 characters
- **Router Diagnostics:** `ru_chars`: 3

> I
> Ты запела вновь вольную песню, Отчизна,
> Словно кто из недоли

### Sample 25 — Ядвігін Ш. | *Лісты з дарогі*
- **Source Work:** Ядвігін Ш. — *«Лісты з дарогі»*
- **Segment Length:** 169 characters
- **Router Diagnostics:** `ru_chars`: 2

> Рудоміна. Перарэзваючы Ашмянскі тракт, якраз выпала мне ісці каля памятніка палкоўніку расейскаму Дзееву. На памятніку напісана: «На семь месте покоится прахь полковника

### Sample 26 — Лукомскі В. | *Нацыянальнасьць і родапаходжаньне Івана Фёдарава, першадрукара ў Маскве*
- **Source Work:** Лукомскі В. — *«Нацыянальнасьць і родапаходжаньне Івана Фёдарава, першадрукара ў Маскве»*
- **Segment Length:** 880 characters
- **Router Diagnostics:** `ru_chars`: 5

> Зазвычай біёграфы Івана Фёдарава, спасылаючыся на тое, што ён сам называў сябе «Москвитином», па аналёгіі зь Пётрам Цімафеевічам «Мсьціслаўцам» з Амсьціслава (у Літве) ды іншымі падобнымі выпадкамі , схільныя прыпісаць месца яго нараджэньня Маскве і гэтым абмежаваць усе далейшыя пошукі, выпускаючы з-пад увагі, што сваё маскоўскае найменьне Іван Фёдараў ставіць толькі ў спалучэньні з паказаньнем на сваю маскоўскую друкарскую дзейнасьць («друкарь москвитин», «печатник з Москвы»), што, адпавядаючы рэчаіснасьці, не дае права на выснову пра ягоную радзіму. Праўда, у літаратуры ёсьць глухія паказань

### Sample 27 — Александровіч Андрэй | *Сутарэньне*
- **Source Work:** Александровіч Андрэй — *«Сутарэньне»*
- **Segment Length:** 118 characters
- **Router Diagnostics:** `ru_chars`: 5

> Дзе-ні-дзе расклесны афішы кіно-фільмаў: "Два чорных гроба или окровавленный кинжал", "Будущее", "Коварство и любовь".

### Sample 28 — Косіч Марыя | *Литвины-Бѣлорусы Черниговской губерніи, бытъ и пѣсни*
- **Source Work:** Косіч Марыя — *«Литвины-Бѣлорусы Черниговской губерніи, бытъ и пѣсни»*
- **Segment Length:** 85 characters
- **Router Diagnostics:** `ru_chars`: 7

> Марыя Косіч
> Литвины-Бѣлорусы Черниговской губерніи, бытъ и пѣсни
> Спампаваць
>  (29 МіБ)

### Sample 29 — Крапівін Сяргей | *Минский ГУМ. История и современность*
- **Source Work:** Крапівін Сяргей — *«Минский ГУМ. История и современность»*
- **Segment Length:** 88 characters
- **Router Diagnostics:** `ru_chars`: 5

> Сяргей Крапівін
> , 
> Ілля Куркоў
> Минский ГУМ. История и современность
> Спампаваць
>  (41 МіБ)

### Sample 30 — Крачкоўскі Юльян | *Быт западно-русского селянина*
- **Source Work:** Крачкоўскі Юльян — *«Быт западно-русского селянина»*
- **Segment Length:** 413 characters
- **Router Diagnostics:** `ru_chars`: 26

> Западнорусскими селянами автор называл белорусов. В работе две нумерованные главы (статьи). Первая из них посвящена свадьбе и включает записи свадебных песен. Вторая глава включает материалы по календарной обрядности, хозяйству, пище и даже крестьянскому времяисчислению. В конце этой главы приведены исторические предания, легенды, былички, рассказы о колдунах. В главе также приведены образцы календарных песен.

---

## 3. Orthographically Invariant / Isolated Segments (`REJECT_NEUTRAL_NO_CONTEXT`)

Short or isolated paragraphs where every single word is identical across both Narkamaŭka and Classical Taraškievica (zero soft-sign assimilation opportunities, no non-Slavic loanwords, no pre-stressed proclitics, no iotated geminates), and where document-level prior inheritance (L_doc) was uninitialized or neutral.

**Audited Segment Count in Category:** 1,582 segments.
**Representative Real-World Samples:** 30 excerpts cataloged below.

### Sample 01 — Чарнышэвіч Аркадзь | *Выбраныя творы ў двух тамах, т. 1*
- **Source Work:** Чарнышэвіч Аркадзь — *«Выбраныя творы ў двух тамах, т. 1»*
- **Segment Length:** 74 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Аркадзь Чарнышэвіч
> Выбраныя творы ў двух тамах, т. 1
> Спампаваць
>  (195 МіБ)

### Sample 02 — Глебка Пятро | *Збор твораў у трох тамах, т. 1*
- **Source Work:** Глебка Пятро — *«Збор твораў у трох тамах, т. 1»*
- **Segment Length:** 64 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Пятро Глебка
> Збор твораў у трох тамах, т. 1
> Спампаваць
>  (84 МіБ)

### Sample 03 — Герасімчык Васіль | *Канстанцін Каліноўскі: асоба і легенда*
- **Source Work:** Герасімчык Васіль — *«Канстанцін Каліноўскі: асоба і легенда»*
- **Segment Length:** 76 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Васіль Герасімчык
> Канстанцін Каліноўскі: асоба і легенда
> Спампаваць
>  (5 МіБ)

### Sample 04 — Гарун Алесь | *«[Праблудзіў] я па сцепу два тыдні...»*
- **Source Work:** Гарун Алесь — *««[Праблудзіў] я па сцепу два тыдні...»»*
- **Segment Length:** 80 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> [Праблудзіў] я па сцепу два тыдні з лішком,—
> Мне здаецца,— пятнаццаць дзянёчкаў,

### Sample 05 — Гаўрылаў Леанід | *Цішыня*
- **Source Work:** Гаўрылаў Леанід — *«Цішыня»*
- **Segment Length:** 52 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Цішыня над полем і над лесам,
> І на хаты пала цішыня.

### Sample 06 — Власаў В. | *Падручнік па справаводзтву ў папраўча-працоўных установах БССР. Частка I. Апэрацыйнае справаводзтва*
- **Source Work:** Власаў В. — *«Падручнік па справаводзтву ў папраўча-працоўных установах БССР. Частка I. Апэрацыйнае справаводзтва»*
- **Segment Length:** 130 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> В. Власаў
> Падручнік па справаводзтву ў папраўча-працоўных установах БССР. Частка I. Апэрацыйнае справаводзтва
> Спампаваць
>  (15 МіБ)

### Sample 07 — Колас Якуб | *"Год за годам уцякае..."*
- **Source Work:** Колас Якуб — *«"Год за годам уцякае..."»*
- **Segment Length:** 88 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Год за годам уцякае,
> Часам смутна стане мне,
> Што вясенька маладая
> Мігатнулась, як у сне;

### Sample 08 — Красінскі М. | *Дзелавод: узоры офіцыяльных папер, слоўнік тэхнічна-канцэлярскіх выразаў і іншыя, патрэбныя ў дзелаводзтве веды*
- **Source Work:** Красінскі М. — *«Дзелавод: узоры офіцыяльных папер, слоўнік тэхнічна-канцэлярскіх выразаў і іншыя, патрэбныя ў дзелаводзтве веды»*
- **Segment Length:** 145 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> М. Красінскі
> Дзелавод: узоры офіцыяльных папер, слоўнік тэхнічна-канцэлярскіх выразаў і іншыя, патрэбныя ў дзелаводзтве веды
> Спампаваць
>  (35 МіБ)

### Sample 09 — Ядвігін Ш. | *Чаму?*
- **Source Work:** Ядвігін Ш. — *«Чаму?»*
- **Segment Length:** 122 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Як рыбка — прытная; як зорка — ясная; як раса — чыстая; як котачка — дурэла; як галубка — варкавала; як матылёк — пырхала.

### Sample 10 — Якубовіч Леанід | *«О Беларусь! Старонка дарагая...»*
- **Source Work:** Якубовіч Леанід — *««О Беларусь! Старонка дарагая...»»*
- **Segment Length:** 65 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> О Беларусь! Старонка дарагая,
> Мне без цябе — як дрэву без вады...

### Sample 11 — Гладкі Язэп | *Краёвы слоўнік Лагойшчыны*
- **Source Work:** Гладкі Язэп — *«Краёвы слоўнік Лагойшчыны»*
- **Segment Length:** 132 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Краёвы слоўнік Лагойшчыны, выдадзены ў Нью-Ёрку ў 1970 годзе - добрая лексыкаграфічная крыніца па мове цэнтральных рэгіёнаў Беларусі

### Sample 12 — Бухарын Мікалай | *Шлях да соцыялізму і рабоча-сялянскі саюз*
- **Source Work:** Бухарын Мікалай — *«Шлях да соцыялізму і рабоча-сялянскі саюз»*
- **Segment Length:** 78 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Мікалай Бухарын
> Шлях да соцыялізму і рабоча-сялянскі саюз
> Спампаваць
>  (16 МіБ)

### Sample 13 — Дудар Алесь | *Стары лясун*
- **Source Work:** Дудар Алесь — *«Стары лясун»*
- **Segment Length:** 96 characters
- **Router Diagnostics:** `confidence`: 0.5049, `effective_log_odds`: 0.0197, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Нават русалак пакрыўдзіў кон
> Для вадзяных турбін…
> Сэрца кроіць сякераў звон:
> Падаюць хвоі, дубы…

### Sample 14 — Смаленец Алесь | *На старой дзялянцы*
- **Source Work:** Смаленец Алесь — *«На старой дзялянцы»*
- **Segment Length:** 74 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Куды ні глянь - гарматаў, мінаў шмат,
> Акопы, рэйкі ды пячураў лісіх брамы,

### Sample 15 — Маўр Янка | *У краіне райскай птушкі*
- **Source Work:** Маўр Янка — *«У краіне райскай птушкі»*
- **Segment Length:** 64 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Янка Маўр
> У краіне райскай птушкі
> Спампаваць усё
> (
> mp3
> ) 
> 01.mp3

### Sample 16 — Лаўрэш Леанід | *Шпацыры па старой Лідзе*
- **Source Work:** Лаўрэш Леанід — *«Шпацыры па старой Лідзе»*
- **Segment Length:** 77 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Леанід Лаўрэш
> Шпацыры па старой Лідзе
> Спампаваць
>  (26 МіБ)
> Крыніца: pawet.net

### Sample 17 — Пічэта Уладзімір | *Белоруссия и Литва XV-XVI вв.*
- **Source Work:** Пічэта Уладзімір — *«Белоруссия и Литва XV-XVI вв.»*
- **Segment Length:** 67 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Зборнік артыкулаў, прысвечаны гісторыі Беларусі і Літвы 15-16 стст.

### Sample 18 — Аляхновіч Францішак | *Сцэнічныя творы: Дзядзька Якуб, Міхалка, На вёсцы, Пярэстая Красуля*
- **Source Work:** Аляхновіч Францішак — *«Сцэнічныя творы: Дзядзька Якуб, Міхалка, На вёсцы, Пярэстая Красуля»*
- **Segment Length:** 171 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> У зборніку змешчаны творы беларускіх драматургаў - Францішка Аляхновіча (Дзядзька Якуб, На вёсцы), А. Чужыніна (Пярэстая красуля), Далецкіх (Міхалка, пераклад з польскай).

### Sample 19 — Каганец Карусь | *"Ой, у полі вецер вее..."*
- **Source Work:** Каганец Карусь — *«"Ой, у полі вецер вее..."»*
- **Segment Length:** 67 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Ой, у полі вецер вее,
> Маё сэрца чагось млее.
> Паняволі аж прыстанеш,

### Sample 20 — Сыракомля Уладзіслаў | *Доля*
- **Source Work:** Сыракомля Уладзіслаў — *«Доля»*
- **Segment Length:** 69 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> З польскай — У. Сыракомлі
> Ные сэрца без патолі,
> Нудна льюцца слёзы...

### Sample 21 — Багдановіч Максім | *Трыялет ("Калісь глядзеў на сонца я...")*
- **Source Work:** Багдановіч Максім — *«Трыялет ("Калісь глядзеў на сонца я...")»*
- **Segment Length:** 51 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Калісь глядзеў на сонца я,
> Мне сонца асляпіла вочы.

### Sample 22 — Фурман Іван | *Віцебск у гравюрах С. Юдовіна*
- **Source Work:** Фурман Іван — *«Віцебск у гравюрах С. Юдовіна»*
- **Segment Length:** 62 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Іван Фурман
> Віцебск у гравюрах С. Юдовіна
> Спампаваць
>  (38 МіБ)

### Sample 23 — Варонка Язэп | *Беларускі рух ад 1917 да 1920 году*
- **Source Work:** Варонка Язэп — *«Беларускі рух ад 1917 да 1920 году»*
- **Segment Length:** 88 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Язэп Варонка
> Беларускі рух ад 1917 да 1920 году
> Спампаваць
>  (16 МіБ)
> Крыніца: leb.nlr.ru

### Sample 24 — Музыка Арцём | *Прыгоды Панаса і Тараса*
- **Source Work:** Музыка Арцём — *«Прыгоды Панаса і Тараса»*
- **Segment Length:** 56 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Арцём Музыка
> Прыгоды Панаса і Тараса
> Спампаваць
>  (7 МіБ)

### Sample 25 — Дварчанін Ігнат | *Францішак Скарына як культурны дзеяч і гуманіст на беларускай ніве*
- **Source Work:** Дварчанін Ігнат — *«Францішак Скарына як культурны дзеяч і гуманіст на беларускай ніве»*
- **Segment Length:** 103 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Ігнат Дварчанін
> Францішак Скарына як культурны дзеяч і гуманіст на беларускай ніве
> Спампаваць
>  (47 МіБ)

### Sample 26 — Сурначоў Мікола | *У стоптаным жыце*
- **Source Work:** Сурначоў Мікола — *«У стоптаным жыце»*
- **Segment Length:** 65 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Ніколі не ехаць
> Хлапцу маладому
> Да блізкага гаю,
> Да роднага дому.

### Sample 27 — Кіржніц Абрам | *Яўрэйскі пэрыодычны друк у С.С.С.Р. (1917-1927)*
- **Source Work:** Кіржніц Абрам — *«Яўрэйскі пэрыодычны друк у С.С.С.Р. (1917-1927)»*
- **Segment Length:** 82 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Абрам Кіржніц
> Яўрэйскі пэрыодычны друк у С.С.С.Р. (1917-1927)
> Спампаваць
>  (16 МіБ)

### Sample 28 — Жылка Уладзімір | *"Месячыку-месяц..."*
- **Source Work:** Жылка Уладзімір — *«"Месячыку-месяц..."»*
- **Segment Length:** 56 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Месячыку-месяц,
> Срэбранькія рожкі!
> З-за хмарынкі, месяц,

### Sample 29 — Беларуская Народная Творчасць | *Беларуская "Народная Біблія" у сучасных запісах*
- **Source Work:** Беларуская Народная Творчасць — *«Беларуская "Народная Біблія" у сучасных запісах»*
- **Segment Length:** 68 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Беларуская "Народная Біблія" у сучасных запісах
> Спампаваць
>  (63 МіБ)

### Sample 30 — Пушча Язэп | *«Выстрыгалі з фотакартак...»*
- **Source Work:** Пушча Язэп — *««Выстрыгалі з фотакартак...»»*
- **Segment Length:** 53 characters
- **Router Diagnostics:** `confidence`: 0.5, `effective_log_odds`: 0.0, `local_score`: 0, `nark_evidence`: 0, `taras_evidence`: 0, `chimera_index`: 0.0, `features`: {'nark': [], 'taras': []}

> Ні ў нядзелю, ні ў чацвер.
> Праўда, быў такі калісьці,

---

## 4. Mixed Orthographic Chimeras (`REJECT_ORTHOGRAPHIC_CHIMERA`)

Text displaying concurrent, conflicting normative features (e.g. Classical assimilation soft signs alongside official unassimilated hard geminates, or official Greek loan forms alongside Classical soft European L). Such texts are characteristic of 1990s uncodified transitional writing or inconsistent proofreading.

**Audited Segment Count in Category:** 188 segments.
**Representative Real-World Samples:** 30 excerpts cataloged below.

### Sample 01 — Гартны Цішка | *Сокі цаліны*
- **Source Work:** Гартны Цішка — *«Сокі цаліны»*
- **Segment Length:** 1952 characters
- **Router Diagnostics:** `chimera_index`: 0.21052631578947367, `features`: {'nark': ['nark_hard_long:15', 'nark_unmarked_assimilation:4'], 'taras': ['tarask_fem_gen_adj:4']}

> Месяц прамінуў, як дзень: азіраючыся назад, Рыгор падводзіў вынікі гэтаму часу свайго адпачынку. Ён памятаў, з якім узнятым настроем варочаўся з заводскае канторы на кватэру з адпускным пасведчаннем. Многа розных думак перабегла ў яго галаве, шмат невыразных чаканняў займала яго праз усю дарогу. Рыгор маляваў сабе мястэчка водлуг ранейшых сваіх уражанняў і перажыванняў. Здалёк, будучы ў горадзе ў зусім інакшых абставінах, ён заўважаў, як гэтыя абставіны выціскалі з яго ранейшыя настроі і сувязь з местачковымі ўмовамі жыцця, з яго вузкім колам інтарэсаў, з абмежаванымі магчымасцямі ў справе рэв

### Sample 02 — Гурскі Ільля | *Перад бурай*
- **Source Work:** Гурскі Ільля — *«Перад бурай»*
- **Segment Length:** 335 characters
- **Router Diagnostics:** `chimera_index`: 0.5, `features`: {'nark': ['nark_hard_long:3', 'nark_loan_forms:1'], 'taras': ['tarask_lex_markers:2']}

> Амаль усю ноч прагаварыў Уладзімір Ільіч з Сярго, абмяркоўваючы пытанні рэвалюцыі ў Расеі, план заваёвы бальшавікамі ўлады, перспектывы развіцця сацыялістычнай дзяржавы. Уладзімір Ільіч марыў: у сваім багатым уяўленні ён бачыў ужо народы Расеі свабоднымі, краіну індустрыяльнай і каапераванай, з шырокай сеткай магутных электрастанцый.

### Sample 03 — Бядуля Зьмітрок | *Язэп Крушынскі. Кніга I*
- **Source Work:** Бядуля Зьмітрок — *«Язэп Крушынскі. Кніга I»*
- **Segment Length:** 509 characters
- **Router Diagnostics:** `chimera_index`: 0.2857142857142857, `features`: {'nark': ['nark_loan_forms:2'], 'taras': ['tarask_palatal_cluster:5', 'tarask_soft_long:1', 'tarask_lex_markers:1']}

> - - - - - - - -
> Позна ўвечары Крушынскі з агрономам прыехалі ў Менск. Заехалі да старшага Крушынскага, былога доктара і цяперашняга «пролетарскага песьняра», які піша вершы пад псэўдонімам Антон Цярэшка. Ён ужо другі тыдзень сьвяткуе свой двухгадовы літаратурны юбілей. Дзень-у-дзень у яго поўна гасьцей. Дзень-у-дзень ладзіцца ў яго кватэры ўрачыстае сьвяткаваньне двухгадовай мастацкай творчасьці. У працягу двух год ён выпусьціў два зборнікі поэзіі, па шаснаццаць балонак кожны, па восем радкоў на балонцы.

### Sample 04 — Колас Якуб | *На ростанях*
- **Source Work:** Колас Якуб — *«На ростанях»*
- **Segment Length:** 512 characters
- **Router Diagnostics:** `chimera_index`: 1.0, `features`: {'nark': ['nark_unmarked_assimilation:2'], 'taras': ['tarask_fem_gen_adj:2']}

> Баранкевіч спаткаў суседа-настаўніка прыветна і павёў яго ў чыстую палавіну дома, дзе ён звычайна прымаў гасцей. Пакой быў прасторны, чысты, акуратна выбелены. Каля аднае сцяны стаяла канапа і вялікі просты стол каля яе, засланы белым настольнікам. На невялічкім століку недалёка ад канапы стаяла скрыначка, музычны струмант, якую падлоўчы і пускаў у работу, каб забавіць гасцей. Апроч яшчэ аднае канапкі каля другой сцяны і некалькіх простых крэслаў, у пакоі гэтым больш не было нічога, і ён выглядаў пуставата.

### Sample 05 — Фурман Іван | *Крашаніна. Матар'ялы да гісторыі яе ў Віцебшчыне*
- **Source Work:** Фурман Іван — *«Крашаніна. Матар'ялы да гісторыі яе ў Віцебшчыне»*
- **Segment Length:** 1213 characters
- **Router Diagnostics:** `chimera_index`: 0.21052631578947367, `features`: {'nark': ['nark_lex_markers:4'], 'taras': ['tarask_palatal_cluster:10', 'tarask_prefix_soft_sign:1', 'tarask_soft_long:5', 'tarask_fem_gen_adj:3']}

> Пакуль можна зацьвярджаць толькі тое, што малюнак Віцебскае крашаніны па сваёй форме і зьместу розьніцца ад малюнка расійскай крашаніны("набойкі"). Калі ў малюнку расійскай "набойкі" пераважваюць важкія формы расьліннага і жывёліннага сьвету, формы пернікавых дошчак, дык малюнак Віцебскае крашаніны мае лёгкую, дробную форму геомэтрычнага і расьліннага орнамэнту. Калі часамі на Віцебшчыне й працавалі саматужнікі выхадцы з Маскоўшчыны, дык ўсё-ж пераважнага значэньня на ўтварэньне малюнка крашаніны яны не маглі мець, дзякуючы таму, што ўрэшце малюнак залежыў ад густу заказчыка-беларуса. Маючы на

### Sample 06 — Луцкевіч Антон | *Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.*
- **Source Work:** Луцкевіч Антон — *«Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.»*
- **Segment Length:** 436 characters
- **Router Diagnostics:** `chimera_index`: 0.6666666666666666, `features`: {'nark': ['nark_unmarked_assimilation:4'], 'taras': ['tarask_palatal_cluster:2', 'tarask_soft_long:1', 'tarask_fem_gen_adj:1', 'tarask_lex_markers:2']}

> Пачатковая нямецкая окупація 1915 году раздзяліла Беларусь на дзьве часьці, і пад той час, як заходная часць дзяліла добрую і благую долю з Літвой, усходняя Беларусь далей аставалася пад уласьцю Расейскае Імпері. У межах апошняе апынулася переважываючая часць Беларускай зямлі з насяленьнем каля 8 мільенау душ. Да яе належалі: часць Віленскай губ., безмала уся Менская; Вітэбская, Магілеуская, часць Смаленскай і Чарнігаускай губэрній.

### Sample 07 — Сматрыцкі Мялецій | *Трэнас*
- **Source Work:** Сматрыцкі Мялецій — *«Трэнас»*
- **Segment Length:** 1961 characters
- **Router Diagnostics:** `chimera_index`: 0.2222222222222222, `features`: {'nark': ['nark_hard_long:1', 'nark_unmarked_assimilation:6', 'nark_prefix_apostrophe:1', 'nark_nie_biez_stressed:1'], 'taras': ['tarask_palatal_cluster:1', 'tarask_fem_gen_adj:1']}

> Гора мне, даверанай нядбайным работнікам! Гора мне, ненажэрным ласунам аддадзенай у апеку! Бяда вам, што прадаеце, і вам, што купляеце дар Духа святога — серабро ваша будзе вам на згубу. Не хочаце ведаць праўды — не хочаце бачыць і няпраўды. Не хочаце разумець, адкуль тыя, што вам даюць, набываюць, з якога промыслу багацеюць. Малако дояць з авечак, воўну стрыгуць, скуру лупяць і прадаюць, самі іх мясам кормяцца, кроўю ўпіваюцца, а вам з шчодрасці таго мяса і звыш меры нявіннае крыві ўдзяляюць. О, брыдкастаўнікі, а не настаўнікі, гасільнікі, а не свяцільнікі, імпастыры (ілгуны. — У. К.), а не п

### Sample 08 — Каганец Карусь | *Вітаўка*
- **Source Work:** Каганец Карусь — *«Вітаўка»*
- **Segment Length:** 739 characters
- **Router Diagnostics:** `chimera_index`: 0.4, `features`: {'nark': ['nark_hard_long:4', 'nark_unmarked_assimilation:1'], 'taras': ['tarask_fem_gen_adj:2']}

> І ўпаў наш баярын у вялікі грэх, так што зямля нават здрыганулася. І аступіўся той узгорак, на каторым двор стаяў, і рынуліся мураваныя палацы і пахавалі пад сабою грэшнага баярына. Дачка ж таго баярына зышла дзесь у далёкі манастыр і там веку даканала. Чэлядзь па свету разышлася, а двор той штораз болей і болей стаў у балота пагрузаць і аднае ночы саўсім затануў. Толькі на тым мейсцы, дзе цэрква стаяла, людзі распяцце знайшлі. Потым паставілі на тым мейсцы цэркаў дзераўляную і тое распяцце ў ёй паставілі. І праславілася тое распяцце цудамі рознымі, і ўсякі год на Уздзвіжанне збіраецца там шма

### Sample 09 — Рак Сымон | *Гутарка аб беларускай мове*
- **Source Work:** Рак Сымон — *«Гутарка аб беларускай мове»*
- **Segment Length:** 322 characters
- **Router Diagnostics:** `chimera_index`: 0.6, `features`: {'nark': ['nark_lex_markers:3'], 'taras': ['tarask_soft_long:1', 'tarask_nia_biaz:2', 'tarask_loan_hard_sibilant:2']}

> каб усе іх разумелі, каб ім ня трэба было вучыцца мовы таго народу, сярод якога яны жывуць. Навет большай частцы расійскіх пісьменьнікаў ці выдаўцом расійскіх кніжак ды газэт выгадней, каб усе гаварылі расійскай мовай, каб іх кніжкі і газэты купляліся ды расходзіліся ня толькі паміж маскоўцамі, а і паміж іншымі народамі.

### Sample 10 — Мрый Андрэй | *І вечная табе любоў,  мой родны край*
- **Source Work:** Мрый Андрэй — *«І вечная табе любоў,  мой родны край»*
- **Segment Length:** 417 characters
- **Router Diagnostics:** `chimera_index`: 0.6666666666666666, `features`: {'nark': ['nark_hard_long:1', 'nark_nie_biez_stressed:1'], 'taras': ['tarask_lex_markers:3']}

> З беларускіх гарадоў на выстаўцы досыць поўна ілюстраваны Менск, часткова Барысаў, Ворша, Магілёў. Іншыя гарады і нават Віцебск не экспанаваны. Гэта тлумачыцца тым, што выставачны Камітэт адбіраў толькі навейшыя фатаграфіі і зарысоўкі, свядома адкідаючы старыя, адбітыя ў друку. Сучасны Менск адлюстраваны фатаграфіямі Сербава, якія даюць уяўленне аб Менску, як вялікім і шматлюдным горадзе, што не зусім справядліва.

### Sample 11 — Жылка Уладзімір | *Першы крок*
- **Source Work:** Жылка Уладзімір — *«Першы крок»*
- **Segment Length:** 772 characters
- **Router Diagnostics:** `chimera_index`: 0.3333333333333333, `features`: {'nark': ['nark_hard_long:3', 'nark_unmarked_assimilation:1', 'nark_prefix_apostrophe:2'], 'taras': ['tarask_fem_gen_adj:2']}

> Беларускі рух у Латвіі — малады. Гэтую восень аслаўляла беларускае тамтэйшае грамадзянства толькі пятыя ўгодкі свае арганізаванае нацыянальнае працы. Толькі пяць гадоў — але за гэты час дасягнута значных поспехаў у кірунку сацыяльнага і нацыянальнага ўсведамлення, у кірунку арганізацыйным і на полі асветным і культурным. З'яўленне дваццаці новых і маладых паэтыцкіх сілаў, якія выступаюць у «Першым Кроку» — ужо адзін з вынікаў праробленае нацыянальнае працы. З'явішча прыемнае і пацяшаючае, тым болей што латвійскі куток беларускага Наддзвіння адрэзаны ад жывога беларускага цела, адгароджаны мяжо

### Sample 12 — Гарун Алесь | *Два каханні*
- **Source Work:** Гарун Алесь — *«Два каханні»*
- **Segment Length:** 78 characters
- **Router Diagnostics:** `chimera_index`: 1.0, `features`: {'nark': ['nark_hard_long:2'], 'taras': ['tarask_palatal_cluster:2']}

> І сядзяць і шэпчуць да зары-сьвітання,
> Былі вішні у садзе сьведкі мілавання...

### Sample 13 — Гарэцкі Максім | *Антон*
- **Source Work:** Гарэцкі Максім — *«Антон»*
- **Segment Length:** 444 characters
- **Router Diagnostics:** `chimera_index`: 1.0, `features`: {'nark': ['nark_hard_long:2', 'nark_nie_biez_stressed:1'], 'taras': ['tarask_palatal_cluster:2', 'tarask_nia_biaz:1']}

> І на дварэ, на сьвентары народу не мала, аж мітусіцца усё пад старымі ліпінамі, і ў звонніцы бабуляк стаіць і сядзіць даволі, і на звонніцу хлопчыкаў-галузаў панабівалося, і ў цэркву аж дабіцца ня можна. Направа мужчыпны найбольш... Каля сьценак старые, сівые, каля клірасу і пасярод-сярэдніх гадоў бацькі, а ў праходзі хлопцы — прыбраліся, у новых пінжаках, у жупанах, у ботах, у прыгожых кашулях, а "сьвецкіе" ў чорным і дай- жа пры манішках.

### Sample 14 — Родзевіч Леапольд | *Як у казцы*
- **Source Work:** Родзевіч Леапольд — *«Як у казцы»*
- **Segment Length:** 1988 characters
- **Router Diagnostics:** `chimera_index`: 1.0, `features`: {'nark': ['nark_unmarked_assimilation:1', 'nark_prefix_apostrophe:1'], 'taras': ['tarask_lex_markers:2']}

> - Да душы, звар'яцеў чалавек. - Ну дык слухайце, пачну па парадку. Заладзіў я ўсе свае справы, дамоў ехаць яшчэ рана, а дзецца няма куды, дай, думаю, зайду ў царкву, - даўно ўжо там бываў. Стаў сабе тамака ў куточку, паглядаю ўбакі, і ўспомнілася мне, як я тут калісь шлюб браў са сваёй бабай, а там далей і паплылі розныя грэшныя думкі. Ажно гляджу я, што гэта народ без часу выходзіць з царквы, валам верне. Пажар, думаю сабе. Рушыў і я, ды прыслухоўваюся да гутаркі, чую, кажуць, Чарвякоў гаворыць да народу на рынку. Тут я, браткі, локцямі раз-раз, шамятнуўся туды-сюды і шась на рынак. А там ужо

### Sample 15 — Вольны Анатоль | *Два*
- **Source Work:** Вольны Анатоль — *«Два»*
- **Segment Length:** 629 characters
- **Router Diagnostics:** `chimera_index`: 0.5, `features`: {'nark': ['nark_lex_markers:2'], 'taras': ['tarask_palatal_cluster:2', 'tarask_soft_long:1', 'tarask_nia_biaz:1']}

> Вось ужо і коміны — люлькі вялізныя — закурылі ў паветра круцёлкамі дыму. А ясакары са сну ўсё яшчэ церабілі свае зялёныя галовы і з леньню пацягваліся. Толькі вераб'і з надзвычайна паважным відам, нібы камісары ў абдзёртых кожкуртах, пачалі выходзіць на працу. У хатцы на канцы валасной вёскі жыла невялікая сям'я паштовага чыноўніка, сям'я з трох чалавек: старога чыноўніка, яго жонкі і дачкі Настулі. Стары чыноўнік, увесь свой век ня згібаўшы карка ад працы, дрэнна разьбіраўся ў тым, што навокал яго дзеецца. Ён бачыў толькі адно, што "палякі" нападаюць на "Расію" і быў дужа рад, што іх пачалі

### Sample 16 — Кляшторны Тодар | *Ліст у Сібір*
- **Source Work:** Кляшторны Тодар — *«Ліст у Сібір»*
- **Segment Length:** 774 characters
- **Router Diagnostics:** `chimera_index`: 0.4, `features`: {'nark': ['nark_hard_long:3', 'nark_unmarked_assimilation:2'], 'taras': ['tarask_lex_markers:2']}

> Засыпан Менск халоднымі снягамі,
> Пад палазамі гойсае зіма...
> Астрыжан клён асеннімі сярпамі -
> Лістоў няма...
> А помніш ростань,
> Помніш, дарагая,
> Як дагарала восеньская медзь,
> Так і душа ў шуканнях дагарае,
> Каб не гарэць...
> Тады плылі,
> Плылі на поўдзень гусі,
> Будзіў лясы
> Асенні свіст і гуд...
> А ты мяняла поле Беларусі
> На дальнюю тайгу...
> Цяпер зіма скрыпіць пад палазамі,
> Заледзянела дарагая шыр...
> І часта, часта
> Думаю начамі
> Я пра Сібір.
> За тою хмураю,
> Таемнаю тайгою,
> Шукае золата
> І ненец і тунгус...
> Здружыўся з лыжамі
> І цёплаю дахою
> Там беларус.
> Хачу да слёз расквечанай вясною
> Паездзіць там
> І ў

### Sample 17 — Смоліч Аркадзь | *Географія Беларусі*
- **Source Work:** Смоліч Аркадзь — *«Географія Беларусі»*
- **Segment Length:** 978 characters
- **Router Diagnostics:** `chimera_index`: 0.4, `features`: {'nark': ['nark_unmarked_assimilation:1', 'nark_lex_markers:1'], 'taras': ['tarask_palatal_cluster:2', 'tarask_soft_long:3']}

> Прыпяць мае вялікія прытокі — з правага боку — Стоход, Стыр, Горынь, Уборць і Славечну, а з левага — Ясельду, Цну, Лань, Морач і Птыч. Гэтыя ўсе рэкі маюць асабліва важнае значэньне дзеля таго, што толькі па іх жыхары Палесься могуць мець зносіны з светам, бо іншых ніякіх дарог там няма. З прытокаў Прыпяці — па Стохаду, Стыру, Горыні, Ясельдзе ходзяць параходы, па шмат якіх іншых ходзяць непаравыя судны. Па самай-жа Прыпяці параходы ходзяць да Пінску. Вялікай перашкодай параходзтву ёсьць плыткія месцы, карчы, калоды, якіх шмат у гэтай палескай рацэ; затое парагоў няма. Важнейшыя прыстані: Пінс

### Sample 18 — Васілёнак Яўген | *Самае важнае адкрыццё*
- **Source Work:** Васілёнак Яўген — *«Самае важнае адкрыццё»*
- **Segment Length:** 992 characters
- **Router Diagnostics:** `chimera_index`: 0.5, `features`: {'nark': ['nark_hard_long:2', 'nark_nie_biez_stressed:1', 'nark_lex_markers:1'], 'taras': ['tarask_loan_soft_l:2']}

> У гасцініцы было цёпла, нумар Ігнатоўскаму трапіўся добры, утульны, і ісці нікуды не хацелася. Ігнатоўскі надумаў пачытаць апошнюю кніжку «Нового мира». Але, уладжваючыся з часопісам у мяккім ёмкім крэсле, ён раптам успомніў, што збіраўся пазваніць інжынеру Сцяпану Максімавічу Карпілаву. З Карпілавым ён не быў знаёмы, нават не бачыў яго ніколі, але чуў пра яго як пра выдатнага спецыяліста якраз у той галіне, у якой працаваў і сам. Незадоўга да свайго ад'езду з Масквы прафесар вычытаў у адным навуковым выданні, што інжынеру Карпілаву ўдалося вынайсці надзвычай арыгінальную рэч — першы ў гісторы

### Sample 19 — Нёманскі Янка | *Драпежнікі*
- **Source Work:** Нёманскі Янка — *«Драпежнікі»*
- **Segment Length:** 1533 characters
- **Router Diagnostics:** `chimera_index`: 0.2222222222222222, `features`: {'nark': ['nark_hard_long:7', 'nark_unmarked_assimilation:1', 'nark_lex_markers:1'], 'taras': ['tarask_loan_soft_l:1', 'tarask_fem_gen_adj:1']}

> Нязмерна шырокія сенажаці і неаглядныя лясы мінскіх уладанняў князя забяспечвалі яму шырокае жыццё. Беларускі селянін, надрываўшы сябе на працы ў князёўскім лесе або на сенажаці, польскі хлоп пад Кракавам у маёнтках жонкі князя, гнучы з вясны да восені спіну над бурачнымі палямі, не заўсёды дагадваліся, што яны вышукваюць у зямлі золата, якое збіралася ў рэчкі і цякло ў Парыж ці Вену. Асабліва шмат сродкаў траціў князь Зыгмунт на дапамогу розным патрыятычным аб'яднанням, ці то гэта былі студэнцкія, ці эмігранцкія, або проста з няведаўшых за што ўзяцца ў жыцці людзей. Кожная такая або проста гр

### Sample 20 — Беларуская Народная Творчасць | *Гісторыя катэхізму ў Беларусі. Кароткі агляд для беларускіх грэка-каталікоў*
- **Source Work:** Беларуская Народная Творчасць — *«Гісторыя катэхізму ў Беларусі. Кароткі агляд для беларускіх грэка-каталікоў»*
- **Segment Length:** 551 characters
- **Router Diagnostics:** `chimera_index`: 0.4, `features`: {'nark': ['nark_hard_long:1', 'nark_lex_markers:1'], 'taras': ['tarask_palatal_cluster:2', 'tarask_soft_long:2', 'tarask_lex_markers:1']}

> Новы этап гісторыі катэхізму ў Беларусі распачаўся ў 1988 г., калі ў Рыме быў выдадзены новы беларускамоўны катэхізм [Кароткі катэхізм хрысьціянскай навукі. Рым, 1988]. З 1989 г. ён вольна распаўсюджваецца ў Беларусі. У 1990 г. да выданьня катэхізму далучылася й адраджаючаяся Грэка-Каталіцкая Царква ў Беларусі. Напачатку ў часопісе «Унія» [Унія, №1, Менск, 1990 г.], а потым у малітоўніках ды асобнымі выданьнямі [Катэхізм айца Пётры, Мінск, 1991] пабачыла сьвет некалькі Грэка-Каталіцкіх варыянтаў катэхізмаў. Сення гэтая праца працягваеца надалей.

### Sample 21 — Чорны Кузьма | *Вялікая і малая тэма*
- **Source Work:** Чорны Кузьма — *«Вялікая і малая тэма»*
- **Segment Length:** 267 characters
- **Router Diagnostics:** `chimera_index`: 0.6666666666666666, `features`: {'nark': ['nark_hard_long:3'], 'taras': ['tarask_fem_gen_adj:2']}

> У гэтакім стане быў разварот вялікае тэмы ў аўтара праз малы час пасля таго, як малая тэма рэалізавалася ў апавяданне. Але неўзабаве аўтар знайшоў яшчэ такое «дапаўненне» да сваіх замыслаў, якое пачало прэтэндаваць на заняцце галоўнае, цэнтральнае лініі ва ўсёй тэме.

### Sample 22 — Дудар Алесь | *Скрыжалі*
- **Source Work:** Дудар Алесь — *«Скрыжалі»*
- **Segment Length:** 234 characters
- **Router Diagnostics:** `chimera_index`: 0.6666666666666666, `features`: {'nark': ['nark_nie_biez_stressed:2'], 'taras': ['tarask_palatal_cluster:2', 'tarask_nia_biaz:1']}

> 2.
> І праз вецер заходні, і праз вецер і слоту
> Пахне днём і вясною.
> Не магу і ня здамся… Будзе ў песьнях яснота,
> Будзе сонца са мною.
> Заімжыць пазалотай лёгкакрылая песьня
> І не будзе самотна, і не будзе мне цесна –
> Пахне днём і вясною.

### Sample 23 — Калюга Лукаш | *Пустадомкі*
- **Source Work:** Калюга Лукаш — *«Пустадомкі»*
- **Segment Length:** 316 characters
- **Router Diagnostics:** `chimera_index`: 1.0, `features`: {'nark': ['nark_unmarked_assimilation:2'], 'taras': ['tarask_fem_gen_adj:1', 'tarask_lex_markers:1']}

> — Калі? — ды: — Адкуль? Ці надоўга?
> Ажно быў ён з Любаю знаём. Паводле таго, як рад быў Арсень, дазнаўшыся, што яна ў Менску стала жыве, і сляпы споздрыў бы, што не пойдзе больш ён на пераезд сустракаць вячорныя цягнікі. Пасля гэтае стрэчы адпала ўсякая патрэба марна сляпіць вочы, узіраючыся ў тыя мігатлівыя вокны.

### Sample 24 — Аляхновіч Францішак | *У капцюрох ГПУ*
- **Source Work:** Аляхновіч Францішак — *«У капцюрох ГПУ»*
- **Segment Length:** 473 characters
- **Router Diagnostics:** `chimera_index`: 0.6666666666666666, `features`: {'nark': ['nark_loan_forms:2'], 'taras': ['tarask_palatal_cluster:2', 'tarask_soft_long:1']}

> А голад з кажным годам дакучаў усё больш і больш. Калі ў першыя гады маёй бытнасьці на Салоўках нас кармілі сачэўкай, грачанай кашай, бульбай, а часам на мясе варылі зупу, дык пасьля бульбу бачылі мы вельмі рэдка, аб гароху, грэчцы, сачэўцы даўно забыліся, а засталася адно толькі салоная рыба -тараны, якую давалі нам і на сьнеданьне, і на абед. 3 гэнае рыбы варылі поліўку, крыху запраўленую прасянымі крупамі або салонымі зялёнымі памідорамі (!), вельмі рэдка - бульбай.

### Sample 25 — Цьвікевіч Аляксандар | *«Западно-руссизм». Нарысы з гісторыі грамадзкай мысьлі на Беларусі ў XIX і пачатку XX в.*
- **Source Work:** Цьвікевіч Аляксандар — *««Западно-руссизм». Нарысы з гісторыі грамадзкай мысьлі на Беларусі ў XIX і пачатку XX в.»*
- **Segment Length:** 381 characters
- **Router Diagnostics:** `chimera_index`: 0.42857142857142855, `features`: {'nark': ['nark_hard_long:1', 'nark_loan_forms:1', 'nark_lex_markers:1'], 'taras': ['tarask_palatal_cluster:5', 'tarask_soft_long:2']}

> Увазе чытачоў прапануецца глыбокае дасьледаванне Аляксандра Цьвікевіча (1888-1937), выдатнага навукоўца, былога старшыні ўрада БНР, пра ідэалогію і практыку русіфікатарства на Беларусі ў часы Расійскай імперыі. Адразу пасьля друкаваньня, у 1929 годзе, трохтысячны наклад кнігі быў зьнішчаны. Да сёньняшняга дня захаваліся адзінкавыя паасобнікі зь ліку тых, што пасьпеў узяць аўтар.

### Sample 26 — Скарына Францыск | *З прадмовы да «Псалтыра»*
- **Source Work:** Скарына Францыск — *«З прадмовы да «Псалтыра»»*
- **Segment Length:** 407 characters
- **Router Diagnostics:** `chimera_index`: 1.0, `features`: {'nark': ['nark_hard_long:1', 'nark_unmarked_assimilation:2'], 'taras': ['tarask_fem_gen_adj:3']}

> Ведаючы такія пажыткі ад гэтае кнігі, я, Францішак, Скарынін сын з Полацка, у лекарскіх навуках доктар, загадаў «Псалтыр» ціснуці рускімі словамі славянскае мовы. Найперш - для ўшанавання і хвалы Бога ў Тройцы адзінага і Прачыстай маці яго Марыі, і ўсіх нябесных чыноў, і святых божых. А таксама — для карысці паспалітага люду. І асабліва з тае прычыны, што мяне літасцівы Бог з гэтае мовы на свет пусціў...

### Sample 27 — Купала Янка | *Раскіданае гняздо*
- **Source Work:** Купала Янка — *«Раскіданае гняздо»*
- **Segment Length:** 725 characters
- **Router Diagnostics:** `chimera_index`: 0.5, `features`: {'nark': ['nark_hard_long:2', 'nark_unmarked_assimilation:1', 'nark_nie_biez_stressed:1'], 'taras': ['tarask_fem_gen_adj:2']}

> Лявон (з сілай) . Не трэба! Не йдзі! Годзе ўжо бацька твой спіны нагнуўся і парогаў наабіваў. Я сам вінен і за ўсіх вас адвет панясу перад людзьмі і перад Богам. Трэ было мне ў сваім часе выехаць з гэтае хаты і не чакаць, пакуль аж прыйдуць выкідаць. А цяпер... сам сабе яму выкапаў сваймі рукамі! (Пасля некаторае паўзы.) Так, так, сам сабе яму глыбокую выкапаў... Без часу прыходзіцца ў яе лезці. Згіненне якоесь прыступае і душыць мяне з усіх старой... У вачах цёмна робіцца... думкі туманяцца... штосьці горла сціскае, дыхнуць не дае. Тара нейкая навалілася на плечы і цісне мяне, як каменнем уся

### Sample 28 — Баранавых Сымон | *Калі ўзыходзіла сонца*
- **Source Work:** Баранавых Сымон — *«Калі ўзыходзіла сонца»*
- **Segment Length:** 434 characters
- **Router Diagnostics:** `chimera_index`: 1.0, `features`: {'nark': ['nark_prefix_apostrophe:1', 'nark_nie_biez_stressed:1'], 'taras': ['tarask_loan_soft_l:2']}

> Косціку было ўсё роўна. Але праз хвіліну ён ускрыкнуў і працёр кулакамі мокры твар. Недзе ў ноздрах і аж да горла (здаецца, праз усю галаву) пякло пякучым агнём. З вачэй жмуткамі сыпаліся іскры. Пачаў чхаць, і ў роце — салёная вада. Жандар наліў Косціку ў нос спрынцоўкай салёнага рошчыну. Да поўдня не мог апамятацца ад пякучага болю. Соль раз'ядала мяккі храсток ноздраў, шчакатала горла. Вось чаму так палохаўся жандарскага голасу.

### Sample 29 — Маўр Янка | *Палескія рабінзоны*
- **Source Work:** Маўр Янка — *«Палескія рабінзоны»*
- **Segment Length:** 306 characters
- **Router Diagnostics:** `chimera_index`: 1.0, `features`: {'nark': ['nark_unmarked_assimilation:2'], 'taras': ['tarask_lex_markers:2']}

> - Не бойся, яна ў нас вельмі рэдкая. Звычайна расце ў Крыме, вакол Чорнага мора ды ў Паўднёвай Эўропе і нікому там не перашкаджае. Яе нават спецыяльна садзяць у садзе, бо яна раней за ўсіх цвіце. Яна цвіце нават раней, як распусціць сваё лісце. Кажуць, што яе паўтараста год назад завезлі ў Эўропу з Кітая.

### Sample 30 — Баршчэўскі Ян | *Драўляны Дзядок і кабета Інсекта*
- **Source Work:** Баршчэўскі Ян — *«Драўляны Дзядок і кабета Інсекта»*
- **Segment Length:** 1136 characters
- **Router Diagnostics:** `chimera_index`: 1.0, `features`: {'nark': ['nark_unmarked_assimilation:1', 'nark_prefix_apostrophe:1'], 'taras': ['tarask_fem_gen_adj:2']}

> Цяпер раскажу, якім чынам пасля доўгае і дзіўнае вандроўкі гэты Драўляны Дзядок трапіў нарэшце да мяне. Ведаеш добра нашу Беларусь, дарагі госцю, пры любых няўродах адзін толькі лён найчасцей можа задаволіць нашы патрэбы, калі Пан Бог бласлаўляе наша поле. У пазамінулым годзе было ў мяне шмат гэтага тавару, у нас яго набываюць купцы, а пасля, сабраўшыся з цэлае Беларусі, вязуць Дзвіною на караблях у Рыгу. Дык я з гэтым інтэрасам прыехаў да купца, каб збыць яму свой тавар. У яго пабачыў вялікі беспарадак, ягоная жонка Яўхімія ад вялікага пярэпалаху і гневу ледзь дом не растрасла, наракаючы на с

---

## 5. Dialectal Trasyanka & Machine Translation Artifacts (`REJECT_TRASIANKA_BELAZAR`)

Corrupted texts featuring rule-breaking morphemes characteristic of Belazar automated machine translation, Russian-Belarusian phonetic pidgin (Trasyanka), or catastrophic encoding replacements.

**Audited Segment Count in Category:** 332 segments.
**Representative Real-World Samples:** 30 excerpts cataloged below.

### Sample 01 — Вісліцкі Ян | *Пруская вайна*
- **Source Work:** Вісліцкі Ян — *«Пруская вайна»*
- **Segment Length:** 86 characters
- **Router Diagnostics:** `hits`: ['змяшчае']

> Першая кніга за тэмаю следам малітву змяшчае
> Панне Марыі, пасля блізкія польскай зямлі

### Sample 02 — Багушэвіч Францішак | *Праўда*
- **Source Work:** Багушэвіч Францішак — *«Праўда»*
- **Segment Length:** 66 characters
- **Router Diagnostics:** `hits`: ['пушчы']

> Злую нашу долю на сухія пушчы.
> Адвярні на камень ці на бездарожжа,

### Sample 03 — Вітан-Дубейкаўская Юліяна | *Мае ўспаміны*
- **Source Work:** Вітан-Дубейкаўская Юліяна — *«Мае ўспаміны»*
- **Segment Length:** 232 characters
- **Router Diagnostics:** `hits`: ['сказывается', 'делается']

> Я толькі засьмяялася й адказала: «Скоро сказка сказывается, да не скоро дело делается». Аднак я пастанавіла пры нагодзе высьвятліць гэнае пытаньне. Пэўнага дня, зараз жа пасьля абеду прыйшоў Іван і я бачыла, што ён быў здэнэрваваны.

### Sample 04 — Цётка | *Мои думы*
- **Source Work:** Цётка — *«Мои думы»*
- **Segment Length:** 55 characters
- **Router Diagnostics:** `hits`: ['Умчаться']

> Хотела б быть я речкой быстрой,
> Умчаться в край родной.

### Sample 05 — Купала Янка | *Тутэйшыя*
- **Source Work:** Купала Янка — *«Тутэйшыя»*
- **Segment Length:** 78 characters
- **Router Diagnostics:** `hits`: ['дажэ']

> ПОП. В нынешнія врэмена дажэ его прэосвяшчэнство воззавідовало бы сіім блюдам.

### Sample 06 — Краўчанка Усевалад | *Вясна на Палессі*
- **Source Work:** Краўчанка Усевалад — *«Вясна на Палессі»*
- **Segment Length:** 486 characters
- **Router Diagnostics:** `hits`: ['пушчы', 'пушчы']

> Якраз такой прыгожай была пушча і ў дзень, выбраны Грабком для палявання, і, памалу ідучы ўзлессем, Мікола не столькі аддаваў увагі таму, дзеля чаго сюды прыехаў, колькі любаваўся строгай прыгажосцю пушчы, убранай у снегавое адзенне. Ціха рыпеў пад нагамі снег, недзе далёка, па той бок бярозавага гаю, што прымыкаў да пушчы, чуваць было яхканне ганчакоў. Хутка Мікола адбіўся ад сяброў. Ён ішоў адзін і, быццам ап'янёны свежасцю марознага дня, памалу забыўся, аддаўся ва ўладу думак...

### Sample 07 — Нёманскі Янка | *Партызан*
- **Source Work:** Нёманскі Янка — *«Партызан»*
- **Segment Length:** 87 characters
- **Router Diagnostics:** `hits`: ['гушчы']

> Раптам з гушчы сялян рашучымі крокамі выйшаў хлопец гадоў дваццаці і стаў перад ганкам.

### Sample 08 — Галубок Уладзіслаў | *Белая зброя*
- **Source Work:** Галубок Уладзіслаў — *«Белая зброя»*
- **Segment Length:** 70 characters
- **Router Diagnostics:** `hits`: ['очэнь']

> Ганс. Дзела очэнь нехорошые. Зараз прышліце мне мадэльшчыка. (Пайшлі.)

### Sample 09 — Баранавых Сымон | *Начныя цені*
- **Source Work:** Баранавых Сымон — *«Начныя цені»*
- **Segment Length:** 103 characters
- **Router Diagnostics:** `hits`: ['настаяшчаму']

> — Па-настаяшчаму, дык ты сама вінавата,— казаў Пархвен,— непатрэбна было разводзіць цэлую дзежку цеста.

### Sample 10 — Скарына Францыск | *З прадмовы да «Кнігі Юдзіф»*
- **Source Work:** Скарына Францыск — *«З прадмовы да «Кнігі Юдзіф»»*
- **Segment Length:** 65 characters
- **Router Diagnostics:** `hits`: ['пушчы']

> Як звяры,
> што блукаюць у пушчы,
> ад нараджэння
> ведаюць сховы свае,

### Sample 11 — Каліноўскі Кастусь | *Пісьмы з-пад шыбеніцы*
- **Source Work:** Каліноўскі Кастусь — *«Пісьмы з-пад шыбеніцы»*
- **Segment Length:** 1812 characters
- **Router Diagnostics:** `hits`: ['толька', 'толька']

> Пагляньма ж цяпер, што ён зараз пачаў рабіці, гэты дабрадзей мужыцкі, як сам цяпер кажа: найперш, каб не магло вырабляціся сумленне народнае, пакасаваў маскаль усе сходкі людзей выбарных, усе школы нашы, а так, абабраўшы з сумлення да і з розуму, а завёўшы ў нас свой парадак маскоўскі, пазволіў кожнаму дужшаму глуміцца над бедным як толька хоча. Паноў заўсім увольніў ад усякіх ценжараў, даў ім права завадзіць паншчыну маскоўскую, а яна то не тры дай не шэсць дзён з хаты, но 6 дзён з душы рабочай. Мужыку не толька што не даў ніякага права, но яшчэ адабраў і тое права, якое ён меў ад ронду польс

### Sample 12 — Марашэўскі Каятан | *Камедыя*
- **Source Work:** Марашэўскі Каятан — *«Камедыя»*
- **Segment Length:** 1087 characters
- **Router Diagnostics:** `hits`: ['толька', 'толька']

> Селянін . Аж змарыўся, бегучы. Аддыхацца яшчэ не магу. А ліха знаець, можа, ужо і запазніўся... Сапраўды, здаецца, што ўжо спазніўся. Чы не быў ужо тут д'ябал? Да яшчэ, здаецца, што яшчэ рана. Не мусіў яшчэ ён прыходзіць, бо мне здаецца, што ён аба мне лепей мусіць помніць цяпер, бо і яму а рэч ідзець. А толька кажуць людзі, калі ўдаецца раз і другі, так трэцяга ўжо не спадзявацца. І ён казаў, трэці і астатні раз пазволіў мне маўчаць. Вот тут мне альбо прайграць прыйдзецца. Аднак прайграць не спадзяваюся, бо як два разы я прайграў, так і ўму набраўся. Не, не! Не выйграеш – трэці раз за мной, п

### Sample 13 — Колас Якуб | *На ростанях*
- **Source Work:** Колас Якуб — *«На ростанях»*
- **Segment Length:** 81 characters
- **Router Diagnostics:** `hits`: ['прычашчае']

> Айцец Мадэст прычашчае яго. Дзед бярэ кусочак прасфары, кладзе ў рот і хоча ісці.

### Sample 14 — Дунін-Марцінкевіч Вінцэнт | *Вечарніцы*
- **Source Work:** Дунін-Марцінкевіч Вінцэнт — *«Вечарніцы»*
- **Segment Length:** 69 characters
- **Router Diagnostics:** `hits`: ['блісцяшчы']

> Дзве цацкі блісцяшчы, як сонца лучы.
> Бяруць цацкі госці, усякі пытае,

### Sample 15 — Гартны Цішка | *Будаванне*
- **Source Work:** Гартны Цішка — *«Будаванне»*
- **Segment Length:** 56 characters
- **Router Diagnostics:** `hits`: ['пушчы']

> То не вецер у пушчы гудзе,
> То не хвалі на моры бушуюць —

### Sample 16 — Смоліч Аркадзь | *Географія Беларусі*
- **Source Work:** Смоліч Аркадзь — *«Географія Беларусі»*
- **Segment Length:** 844 characters
- **Router Diagnostics:** `hits`: ['пушчы', 'пушчы', 'пушчы', 'пушчы']

> Дуброва у Новаградчыне.
> Да апошніх часоў на захадзе Беларусі было некалькі вялізных кавалкаў яшчэ не чапанага лесу, гэта пушчы. Спаміж іх ёсьць вядомая на ўвесь сьвет Белавежская пуща. Пушча гэтая займае балей за 100 000 дзесяцін прастору у Пружанскім павеце і часткаю ў суседніх. Спаміж пародаў лесу найбалей у пушчы хвоі, елкі і дубу. Есьць і шмат іншых пародаў. Дрэва ў пушчы трапляецца надта добрае і вялікае. Пушча гэтая захавалася, дзякуючы асаблівай апецы каралёў і цароў, якія пераховавалі яе для свайго паляваньня. Апроч Белавежскае — ёсьць яшчэ пушчы Горадзенская — на поўначы ад Горадня, Н

### Sample 17 — Таўбін Юлі | *Сирано де Бержерак*
- **Source Work:** Таўбін Юлі — *«Сирано де Бержерак»*
- **Segment Length:** 57 characters
- **Router Diagnostics:** `hits`: ['расплывается']

> Туман расплывается над землей,
> Солнце ткет огненный шнур,

### Sample 18 — Лучына Янка | *Паляўнічыя акварэлькі з Палесся*
- **Source Work:** Лучына Янка — *«Паляўнічыя акварэлькі з Палесся»*
- **Segment Length:** 406 characters
- **Router Diagnostics:** `hits`: ['пушчы', 'пушчы']

> «Шатана ці русалак бачыў ты хіба?» -
> «Фу!.. цьфу!.. Панічу! ну навошта пахвальба?
> Нібыта не баіцца сілы пан нячыстай?!.
> Мо тут шатан сядзіць на хвоі дзе камлістай!
> Нячысціка ды клікаць?!. У імя Айца!..
> Мы ў пушчы, а не ў хаце свячанай!.. Жыцця
> Яе не перадаць... гм!.. кніжкі пан чытае
> І верыць, што бязлюдны лес душы не мае?
> Прабач. Дык слухайма, лавем жа кожны гук,
> Ад пушчы пан не спадзяецца гэткіх штук.

### Sample 19 — Гарун Алесь | *«[Праблудзіў] я па сцепу два тыдні...»*
- **Source Work:** Гарун Алесь — *««[Праблудзіў] я па сцепу два тыдні...»»*
- **Segment Length:** 72 characters
- **Router Diagnostics:** `hits`: ['Ходім']

> Той,— куды і адкуль,— распытаўся як трэ:
> «Ходім, кажа, до нас ночуваты».

### Sample 20 — Калюга Лукаш | *Тахвілін швагер*
- **Source Work:** Калюга Лукаш — *«Тахвілін швагер»*
- **Segment Length:** 168 characters
- **Router Diagnostics:** `hits`: ['нясушчыя', 'нясушчыя']

> — Надта ж яны,— кажа,— нясушчыя.
> — Ды чорт іх бяры, што яны ў цябе нясушчыя. Я табе кажу, каб не было ў мяне на гаспадарцы гэтага балота. І каб не было! Гіну я праз іх!

### Sample 21 — Каганец Карусь | *"Лясы, бары і дубровы..."*
- **Source Work:** Каганец Карусь — *«"Лясы, бары і дубровы..."»*
- **Segment Length:** 69 characters
- **Router Diagnostics:** `hits`: ['пушчы']

> Лясы, бары і дубровы —
> Краса нашай бо краіны!
> Гаі, пушчы, кнеі, лугі,

### Sample 22 — Пушча Язэп | *Вершы*
- **Source Work:** Пушча Язэп — *«Вершы»*
- **Segment Length:** 68 characters
- **Router Diagnostics:** `hits`: ['пушчы']

> Дома на мякіне,
> Без вады і солі
> Дажылі б да волі.
> Хлопцы, каля пушчы

### Sample 23 — Чарнышэвіч Аркадзь | *Світанне*
- **Source Work:** Чарнышэвіч Аркадзь — *«Світанне»*
- **Segment Length:** 106 characters
- **Router Diagnostics:** `hits`: ['пушчы']

> Лясы непралазныя! Бязмежныя ды бяскрайнія пушчы! Сколькі сцежак-дарог працяла навылет вашы глыбокія нетры!

### Sample 24 — Маўр Янка | *ТВТ*
- **Source Work:** Маўр Янка — *«ТВТ»*
- **Segment Length:** 80 characters
- **Router Diagnostics:** `hits`: ['абвяшчае']

> Таварыства ваяўнічых тэхнікаў абвяшчае барацьбу за незалежнасць ад хатніх рэчаў.

### Sample 25 — Жылка Уладзімір | *"Каму жыццё — атруты келіх..."*
- **Source Work:** Жылка Уладзімір — *«"Каму жыццё — атруты келіх..."»*
- **Segment Length:** 76 characters
- **Router Diagnostics:** `hits`: ['прапашчы']

> Якога мела за абразу
> Ў дзявочых думках цалаваць.
> Цяпер і ён такі ж прапашчы,

### Sample 26 — Гурскі Ільля | *На берагах Прыпяці*
- **Source Work:** Гурскі Ільля — *«На берагах Прыпяці»*
- **Segment Length:** 1961 characters
- **Router Diagnostics:** `hits`: ['пушчы', 'пушчы']

> Паляшанскія дзяўчаты, якія падышлі да Гарбачэні, калі ён спыніўся каля будовы, запрасілі яго зайсці пачаставацца хлебным квасам, пагаманіць. Але Гарбачэня не хацеў бавіцца, яму яшчэ заставалася ісці да свае вёскі добрых кіламетраў пятнаццаць, калі не болей. Падзякаваўшы дзяўчатам за запрашэнне, ён развітаўся з паляшанамі і пайшоў. Скончыліся паляшанскія палеткі, і Гарбачэня зноў апынуўся ў густым цяністым лесе. Панура маўчаў велічны бор, пахла гніллю. У пушчы трапляліся невялікія прагаліны, месцамі лес быў дашчэнту спляжаны, пракладзены новыя дарогі, якіх перад вайною не было,— гэта сяляне тра

### Sample 27 — Чорны Кузьма | *Радасць жанчыны*
- **Source Work:** Чорны Кузьма — *«Радасць жанчыны»*
- **Segment Length:** 237 characters
- **Router Diagnostics:** `hits`: ['настаяшчае', 'настаяшчае']

> «Вось пражыву я гэты дзень, а там будзе другі, лепшы. Вось зраблю я гэтую працу, а там будзе другая, любімая. Усё тое, што сягоння, - не настаяшчае, яно часовае, і яго трэба абы-як перажыць для таго, каб спаткаць тое лепшае, настаяшчае».

### Sample 28 — Сматрыцкі Мялецій | *Трэнас*
- **Source Work:** Сматрыцкі Мялецій — *«Трэнас»*
- **Segment Length:** 1945 characters
- **Router Diagnostics:** `hits`: ['пашчы', 'пашчы']

> Слухайце жалобную аповесць маю ўсе народы, прыслухайцеся ўсе, хто жыве на зямлі! Сыны і дочкі мае, якіх я нарадзіла і выхавала, пакінулі мяне і пайшлі за тою, якая імі не пакутвала, каб удосталь насыціцца яе тлустасцю! Святары мае аслеплі, пастыры мае, не жадаючы ведаць, што размова ідзе пра душу, знямелі, старцы мае падурэлі, юнакі мае здзічэлі, дочкі мае кінуліся ў распусту, і ўсе з адзіным намерам, выракшыся Бога і яго праўды, згаварыліся супраць маёй душы. Разінулі свае пашчы і, свішчучы, скрыгочуць на мяне сваімі зубамі, гавораць: «Вось ужо і прыйшоў той дзень, якога мы чакалі, пойдзем і

### Sample 29 — Багдановіч Максім | *Мушка-зелянушка й Камарык-насаты тварык*
- **Source Work:** Багдановіч Максім — *«Мушка-зелянушка й Камарык-насаты тварык»*
- **Segment Length:** 77 characters
- **Router Diagnostics:** `hits`: ['хрушчы']

> Прыляцела мушка да хаты, —
> Аж у яе камарык насаты.
> Сватоўе-хрушчы усьсядаюць,

### Sample 30 — Беларуская Народная Творчасць | *Акафіст прыпадобнае маці нашае Ефрасіньні Полацкае*
- **Source Work:** Беларуская Народная Творчасць — *«Акафіст прыпадобнае маці нашае Ефрасіньні Полацкае»*
- **Segment Length:** 98 characters
- **Router Diagnostics:** `hits`: ['крочашчая']

> Радуйся, у дабрыні сумленьне моцнае трымаючая;
> Радуйся, ад юнацтва крочашчая па шляху дабрачэсьця.

---

## 6. OCR Homoglyph Contamination (`REJECT_OCR_HOMOGLYPH`)

Paragraphs suffering from optical character recognition (OCR) substitution errors, such as Latin c, p, a, o, e, x, i erroneously substituted into Cyrillic word tokens during historical book digitization.

**Audited Segment Count in Category:** 179 segments.
**Representative Real-World Samples:** 30 excerpts cataloged below.

### Sample 01 — Лукомскі В. | *Нацыянальнасьць і родапаходжаньне Івана Фёдарава, першадрукара ў Маскве*
- **Source Work:** Лукомскі В. — *«Нацыянальнасьць і родапаходжаньне Івана Фёдарава, першадрукара ў Маскве»*
- **Segment Length:** 662 characters
- **Router Diagnostics:** `count`: 2

> Такі ключ - той герб, які Іван Фёдараў зьмяшчаў на выданьнях львоўскага ды астроскага пэрыядаў сваёй друкарскай дзейнасьці - упершыню на «Апостале» 1574 г., уключыўшы яго ў складаную кампазыцыюі акантавай галіны, зьлева ад якой знаходзіцца герб горада Львова, а справа ў гербавым картушы «загадкавы» знак у выглядзе выгнутай паласы (накшталт літары S у адваротны бок) з навершам стралы ўверсе, аточаны літарамі: І-ОY-A-N. Пазьней гэты ж гербавы шчыток з адрозьненьнямі толькі ў дэталях (з бакоў фігураў гербу літары І ды ОY, а сам шчыток трымае рука) двойчы зьяўляецца на астроскіх выданьнях: «Новага

### Sample 02 — Лёсік Язэп | *Некаторыя ўвагі да беларускае літаратурнае мовы*
- **Source Work:** Лёсік Язэп — *«Некаторыя ўвагі да беларускае літаратурнае мовы»*
- **Segment Length:** 329 characters
- **Router Diagnostics:** `count`: 1

> Ёсьць яшчэ шмат зваротаў з ускоснымі склонамі на выражэньне часу (бач. VІ. Прыназоўнікі). Часовыя звароты належаць да тых моўных фактаў, дзе тонкасьці граматычныя пераходзяць у тонкасьці стылістычныя (Пакажэце мне такую кветку, што расьце зімой і ў летку), дзеля гэтага трудна правілам разьмежаваць, калі каторы зварот ужываецца.

### Sample 03 — Аляхновіч Францішак | *Беларускі тэатр*
- **Source Work:** Аляхновіч Францішак — *«Беларускі тэатр»*
- **Segment Length:** 354 characters
- **Router Diagnostics:** `count`: 1

> У другой палове XVIII стал. паяўляецца "Коmedya" ксяндза Каетана Морашэўскага, напісаная ў стылю старой школьнай драмы з дзеячымі асобамі ніжэйшага стану, як Селянін, Жыд, Чорт, Пакутнік і др., у якой Сялянін кажа пабеларуску. Таксама пабеларуску напісаны й рэплікі Жыда, але з некаторымі сьмяхотнымі перакручаньнямі дзеля захаваньня жыдоўскага прононсу.

### Sample 04 — Купала Янка | *Барысаў*
- **Source Work:** Купала Янка — *«Барысаў»*
- **Segment Length:** 50 characters
- **Router Diagnostics:** `count`: 1

> Хітры вораг за мяжою
> Набівае стрэльбы.
> 6/VIІ-34 г.

### Sample 05 — Бядуля Зьмітрок | *Вера, паншчына і воля ў беларускіх народных песьнях і казках*
- **Source Work:** Бядуля Зьмітрок — *«Вера, паншчына і воля ў беларускіх народных песьнях і казках»*
- **Segment Length:** 376 characters
- **Router Diagnostics:** `count`: 2

> Паны ў большасьці бывалі злосныя — «dо trzeciego nіе mów». Сяляне ня ведалі, як прыступіцца да іх: чуць што скажа селянін непаводлуг панскага гумору, — і няшчаснага пасылаюць на стайню, дзе яго кормяць бярозавай, або сырматовай кашай — сыплюць бізуноў, колькі лезе. Такія паны наганялі страх ня толькі на сялян, але й на болей прывілегаваную службу — на войтаў, лёкаяў і г. д.

### Sample 06 — Колас Якуб | *Методыка роднай мовы*
- **Source Work:** Колас Якуб — *«Методыка роднай мовы»*
- **Segment Length:** 62 characters
- **Router Diagnostics:** `count`: 1

> 1/XІ 1925 г.							Аўтар
> г. Мінск
> Методыка – частка дыдактыкі.

### Sample 07 — Маўр Янка | *Сын вады*
- **Source Work:** Маўр Янка — *«Сын вады»*
- **Segment Length:** 309 characters
- **Router Diagnostics:** `count`: 2

> Чым далей ад'язджалі ад акіяна, тым большыя і ніжэйшыя былі астравы. Пачала з'яўляцца трава, дрэвы. Там, далей, на ўсходзе, ёсць і лясы, і лугі, але жыве там моцнае ваяўнічае племя «oна». Гэтыя «oна» — дужы, злы народ; яны здаўна ўжо выпхнулі мірных фуіджы на бясплодныя заходнія скалы і не пускаюць іх назад.

### Sample 08 — Жылка Уладзімір | *Выбраныя творы*
- **Source Work:** Жылка Уладзімір — *«Выбраныя творы»*
- **Segment Length:** 237 characters
- **Router Diagnostics:** `count`: 1

> Уладзімір Жылка
> Выбраныя творы
> Спампаваць
>  (52 МіБ)
> Крыніца: Жылка, У.А. Выбраныя творы / Уладзімір Жылка; [Уклад.,прадм.і камент.М.Скоблы]. - Мн. : Бел.кнігазбор, 1998.- 358,VIIІ с. - ( Беларускі кнігазбор ; Сер.1.Мастацкая літаратура).

### Sample 09 — Чорны Кузьма | *Беларускае мастацтва ў часе Вялікай Айчыннай  вайны*
- **Source Work:** Чорны Кузьма — *«Беларускае мастацтва ў часе Вялікай Айчыннай  вайны»*
- **Segment Length:** 398 characters
- **Router Diagnostics:** `count`: 1

> Пачатак гэтай пары належыць да першых год рэвалюцыі. За гады Савецкай улады ў Беларусі стварылася і атрымала высокае прызнанне шырока за межамі рэспублікі беларуская опера, беларуская філармонія. Была створана і выхоўвала дзеячаў беларускай музыкі Беларуская кансерваторыя. Музычны геній беларускага народа атрымаў @ltзакр.@gt, выйшаў на прасторы вялікіх сваіх магчымасцей і выявіўся з новай сілай.

### Sample 10 — Вісліцкі Ян | *Пруская вайна*
- **Source Work:** Вісліцкі Ян — *«Пруская вайна»*
- **Segment Length:** 716 characters
- **Router Diagnostics:** `count`: 1

> 8 Кракаў высока шануе адвечныя творы Платона – З гэтых слоў можна зрабіць слушную выснову, што дыялогі Платона і яго філасофія былі ў ліку тых дысцыплін, якія вывучаліся ў Кракаўскім універсітэце ў канцы ХV – пачатку ХVІ ст. Б. Кручкевіч прыгадвае той факт, што каля 1440 г. у Фларэнцыі Козіма Медзічы заснаваў славутую платонаўскую Акадэмію. Тым не менш менавіта прафесары Ягелонскага універсітэта аднымі з першых пачалі карыстацца лацінскімі перакладамі твораў Платона. Б. Кручкевіч абвяргае меркаванне аднаго з даследчыкаў "Прускай вайны", які сцвярджаў, што з вышэйпрыведзеных слоў вынікае факт і

### Sample 11 — Гарэцкі Максім | *Віленскія камунары*
- **Source Work:** Гарэцкі Максім — *«Віленскія камунары»*
- **Segment Length:** 65 characters
- **Router Diagnostics:** `count`: 1

> Трупы забралі ў морг пры шпіталі.
> Vае vісtіs.
> (Гора пераможаным.)

### Sample 12 — Ажэшка Эліза | *Нізіны*
- **Source Work:** Ажэшка Эліза — *«Нізіны»*
- **Segment Length:** 254 characters
- **Router Diagnostics:** `count`: 1

> На беларускай мове аповесць друкуецца ўпершыню. Згодна з першапачатковай задумай, мела называцца «Танная невялічкая кніжка для люду» і пісалася для часопіса «Кraj», дзе і з'явілася ў 1884 г. (No.33—40). Першае выданне асобнай кніжкай выйшла ў 1885 годзе.

### Sample 13 — Нёманскі Янка | *Драпежнікі*
- **Source Work:** Нёманскі Янка — *«Драпежнікі»*
- **Segment Length:** 120 characters
- **Router Diagnostics:** `count`: 1

> — Апранута яна не соmme il faut 1 .
> — Мусіць, нейкая бедная з яго далёкіх сваякоў. Гэтых сваякоў у Ляскоўскіх так многа.

### Sample 14 — Дунін-Марцінкевіч Вінцэнт | *Пінская шляхта*
- **Source Work:** Дунін-Марцінкевіч Вінцэнт — *«Пінская шляхта»*
- **Segment Length:** 308 characters
- **Router Diagnostics:** `count`: 1

> Раманс
> Найяснейшая карона!
> Трудна мне без Грышкі жыці.
> Hiяка земска прэпона
> Не ў сілах нас разлучыці!
> Сэрца маё – яго менне,
> Яго любоў – мая сіла.
> Без яго мне смерць – спасенне,
> Без яго мне свет – магіла.
> Няхай бацькі лаюць, мучаць,
> Hi з кім другім не зручуся.
> Калі з ім мяне разлучаць,
> Я ў Прыпяці ўтаплюся.

### Sample 15 — Грамыка Міхайла | *Лісты*
- **Source Work:** Грамыка Міхайла — *«Лісты»*
- **Segment Length:** 167 characters
- **Router Diagnostics:** `count`: 1

> Бывайце здаровы!
> Дзед Міхайла.
> 31/VІІ-65 г.
> Пасылаю ў поўнае тваё скарыстанне аўтабіяграфію. Такую ж, перапісаўшы чарніламі, перашлю ў Саюз разам з іншымі матэрыяламі.

### Sample 16 — Смоліч Аркадзь | *Географія Беларусі*
- **Source Work:** Смоліч Аркадзь — *«Географія Беларусі»*
- **Segment Length:** 307 characters
- **Router Diagnostics:** `count`: 1

> Шмат ведамасьцяў аб асобных мясьцінах Беларусі можна знайсьці у ўсякіх слоўніках географічных і энцыклапэдычных (асабліва варт увагі вялікі расейскі слоўнік Бракгаўза-Эфрона) і ў іншых справачных выданьнях, прыкл. Przewodnik po Litwie i Bałej Rusi, H. Роўбы, Przewodnik po Wilnie — таго ж A. Kipкора і г. д.

### Sample 17 — Баршчэўскі Ян | *Драўляны Дзядок і кабета Інсекта*
- **Source Work:** Баршчэўскі Ян — *«Драўляны Дзядок і кабета Інсекта»*
- **Segment Length:** 151 characters
- **Router Diagnostics:** `count`: 2

> 1. Klauber svulpsіt - Клаўбер напісаў па замове (ці Клаўбер пісаў па жаданню) ад лац. абрэвіятуры s(і) vul(tіs) (scrі)psіt (ці s(і) vul(t) (scrі)psіt).

### Sample 18 — Мрый Андрэй | *Працоўны дзень савецкага лекара*
- **Source Work:** Мрый Андрэй — *«Працоўны дзень савецкага лекара»*
- **Segment Length:** 357 characters
- **Router Diagnostics:** `count`: 2

> — Казала я яму — кінь ты, якая табе карысць! Нашто табе гэты камітэт, нашто табе вазекацца з чужымі грашмі! Праўду людзі кажуць — не gадзівіце: лепш біць свае вошы, чымся лічыць чужыя грошы!.. Во ён павёз здаваць грамадзянскія грошы, а нейкія зладзеі падсцераглі, грошы забралі, а самаuj крыху зусім не забілі! Ой, гора мне, у дварэ цяпер усё пойдзе прахам!

### Sample 19 — Вольны Анатоль | *Два*
- **Source Work:** Вольны Анатоль — *«Два»*
- **Segment Length:** 398 characters
- **Router Diagnostics:** `count`: 1

> І пяро зноў заскрыпела:
> ..За гэта зараз з камандзірам IV баявога вучастку і яго гасьцямі вып'ю за тваё здароўе. Але-ж сяброўства-сяброўствам, а суд — па форме. Як пабачу цябе, дык абавязкова заб'ю. Бо ты варт гэтага. А газэты ты гэта дарэмна паведаміў, што я забіты. Ты не сярдуй на гэтага камандзіра ІV-га вучастку. Ён ня дурней за цябе. Спадзяюся, што з табою таксама пабачымся. А пакуль — бывай!

### Sample 20 — Галубок Уладзіслаў | *Пан Сурынта*
- **Source Work:** Галубок Уладзіслаў — *«Пан Сурынта»*
- **Segment Length:** 123 characters
- **Router Diagnostics:** `count`: 1

> ІІ казак. Паквіталіся!
> ІV казак. Добра паквіталіся: ён галаву пагладзіў, а ты яго так-такі напалам!.. Зухавы з цябе баец!..

### Sample 21 — Беларуская Народная Творчасць | *Наша традыцыя. Да пытаньня абрадавасьці Вуніяцкай Царквы Кіеўскай мітраполіі*
- **Source Work:** Беларуская Народная Творчасць — *«Наша традыцыя. Да пытаньня абрадавасьці Вуніяцкай Царквы Кіеўскай мітраполіі»*
- **Segment Length:** 585 characters
- **Router Diagnostics:** `count`: 1

> Разглядаючы рукапісныя славянскія службоўнікі Антонія Рымляніна (+1147) і Варлаама Хутынскага (+1192), што паходзяць з ХІІ ст., бачым іх разнастайнасьць. Падобная зьява сустракаецца і ў больш пазьнейшых сьпісах ХІІІ ды ХIV ст. Асноўныя разнастайнасьці былі ў такіх важкіх часьцінах як: праскамідыя, Вялікі Ўваход і чын Сьвятога Прычасьця. Характэрна, што падобная разнаабрадавасьць існуе ня толькі ў славянскіх, але і ў грэцкіх сьпісах бізантыйскага абраду[46, ст.947-959]. Такім чынам, тэзіс аб адзінай аўтэнтычнай бізантыйскай абрадавасьці часоў Кіеўскай Русі не вытрымлівае крытыкі.

### Sample 22 — Баранавых Сымон | *Начныя цені*
- **Source Work:** Баранавых Сымон — *«Начныя цені»*
- **Segment Length:** 66 characters
- **Router Diagnostics:** `count`: 1

> ...Як абарваная струна, брынчэла шкло.
> в. Рудкова, 9—18.VІ.1928 г.

### Sample 23 — Пушча Язэп | *Вершы*
- **Source Work:** Пушча Язэп — *«Вершы»*
- **Segment Length:** 59 characters
- **Router Diagnostics:** `count`: 1

> Як мы былі ў калгасе
> «Камунізмa нівы».
> Шумяць бярозы, клёны

### Sample 24 — Лукомскі В. | *Нацыянальнасьць і родапаходжаньне Івана Фёдарава, першадрукара ў Маскве*
- **Source Work:** Лукомскі В. — *«Нацыянальнасьць і родапаходжаньне Івана Фёдарава, першадрукара ў Маскве»*
- **Segment Length:** 484 characters
- **Router Diagnostics:** `count`: 1

> Зьвесткі пра беларускі род Рагаза сягаюць ХV ст. Паводле зьвестак гістарычна-генэалягічнай літаратуры , можна меркаваць, што расьсяліўся ён на вярхоўях Дняпра, маючы ва ўладаньнях землі ў Амсьціслаўскім ды Менскім ваяводзтвах Вялікага Княства Літоўскага. Сярод прадстаўнікоў гэтага роду былі два кіеўскія мітрапаліты: Місаіл (з 1474 да 1477 г.) ды вядомы прыхільнік царкоўнай вуніі Міхаіл (з 1589 да 1579 г.), які да таго (ад 1579) быў архімандрытам Вазьнясенскага манастыра ў Менску.

### Sample 25 — Аляхновіч Францішак | *Беларускі тэатр*
- **Source Work:** Аляхновіч Францішак — *«Беларускі тэатр»*
- **Segment Length:** 108 characters
- **Router Diagnostics:** `count`: 2

> 4 "Z chłopa król", komedia dworska, od Ріоtга Вагукі napisana і nа dworze Іm. Раnа А. L. wyprawiona. (1637).

### Sample 26 — Бядуля Зьмітрок | *Язэп Крушынскі. Кніга II*
- **Source Work:** Бядуля Зьмітрок — *«Язэп Крушынскі. Кніга II»*
- **Segment Length:** 76 characters
- **Router Diagnostics:** `count`: 1

> 25 сакавіка 1918 г.
> —	Вось бачыце, як добра выйшла, — cказаў Раман Скірмунт.

### Sample 27 — Колас Якуб | *Казкі жыцця*
- **Source Work:** Колас Якуб — *«Казкі жыцця»*
- **Segment Length:** 63 characters
- **Router Diagnostics:** `count`: 1

> Якуб Колас
> Казкі жыцця
> Спампаваць усё
> (
> mp3
> ) 
> Штo яны cтpaцілі

### Sample 28 — Маўр Янка | *Сын вады*
- **Source Work:** Маўр Янка — *«Сын вады»*
- **Segment Length:** 255 characters
- **Router Diagnostics:** `count`: 1

> Доўга ён пасоўваўся, як цень, пакуль убачыў прасвет, праз які ўжо было відаць вогнішча і постаці людзей. Потым лёг на зямлю і пачаў паўзці. Праз некалькі мінут ён ужо мог разгледзець чатырох мужчын, якія сядзелі ля вогнішча на беразе ручая. Гэта былі oна.

### Sample 29 — Чорны Кузьма | *Беларускае мастацтва ў часе Вялікай Айчыннай вайны*
- **Source Work:** Чорны Кузьма — *«Беларускае мастацтва ў часе Вялікай Айчыннай вайны»*
- **Segment Length:** 479 characters
- **Router Diagnostics:** `count`: 1

> Яшчэ ў даўнія часы было сказана: мастацтва — душа народа. Беларускае народнае мастацтва заўсёды здзіўляе яго знаўцаў — вялікай сваёй глыбінёй і шчырасцю. Беларуская народная песня, якая праз стагоддзі нараджалася, бытавала і развівалася ў самых глыбокіх народных нетрах, і ў народным быту была часта як першапачатковы прымітыў, мела ў сабе такія найвялікшыя магчымасці і патэнцыі, на аснове якіх з вялікай сілай і за вельмі кароткі час @ltнрз@gt вышэйшыя формы беларускай музыкі.

### Sample 30 — Вісліцкі Ян | *Пруская вайна*
- **Source Work:** Вісліцкі Ян — *«Пруская вайна»*
- **Segment Length:** 307 characters
- **Router Diagnostics:** `count`: 1

> 12 Б. Кручкевіч лічыць, што, хутчэй за ўсё, 438 – 441-ы радкі складзены паэтам на падставе нейкага народнага падання, бо імя таго чалавека, які забіў Ульрыка фон Юнгінгена, магістра крыжакоў, і пазбавіў яго зброі, невядомаe, і можна сумнявацца ў тым, ці было яно вядома самому паэту [гл.: Pauli 1887, 200 ].

---

## 7. Loss of Short-U Ў / Broken Vocalic Alternation (`REJECT_OCR_USHORT_LOSS`)

Texts where scanning software or typography converted post-vocalic ў into regular Cyrillic у, violating the fundamental phonological invariant of the Belarusian language (§ 11 NKBM-2008 and BKP-2005 § 3).

**Audited Segment Count in Category:** 34 segments.
**Representative Real-World Samples:** 30 excerpts cataloged below.

### Sample 01 — Мурашка Рыгор | *Прыгранічны манастыр*
- **Source Work:** Мурашка Рыгор — *«Прыгранічны манастыр»*
- **Segment Length:** 428 characters
- **Router Diagnostics:** `broken`: 1

> Сціплы археолаг імгненна паказаў, што валодае не толькі «старасвецкім шыкам», а і кулакамі: трыма прыёмамі японскай барацьбы «джыу-джыцу», пачаўшы з выкручвання рукі, ён скончыў усю карпатню і паклаў асабіста спартсменскім ударам кулака ў карак. З хуткасцю механізма ён выцяг з кішэні (у археолага заўсёды знойдзецца ў кішэні падобнае што на выпадак) вяровачку і зусім не па-археолагаўску ў паўхвіліны скруціў непрытомнаму рукі.

### Sample 02 — Колас Якуб | *Методыка роднай мовы*
- **Source Work:** Колас Якуб — *«Методыка роднай мовы»*
- **Segment Length:** 877 characters
- **Router Diagnostics:** `broken`: 1

> Наступны момант работы – расклад слоў на гукі. Для раскладу спачатку лепей браць аднаскладовыя словы з галоснага і зычнага гука: ах, ох, ух. Каб дзеці лягчэй маглі выдзеліць патрэбны гук, настаўнік, вымаўляючы слова, расцягвае гэты гук – ууу-х! Вучні вымаўляюць наўперад усё слова, таксама расцягваючы той ці іншы гук. Потым вымаўляюць асобна першы гук і другі. Каб адрозненне і парадак гукаў цвярдзей усвоіліся вучнямі, настаўнік кажа вучням сказаць першы гук, а сам вымаўляе другі і наадварот – сам пачынае, а дзеці канчаюць. Калі дзеці напрактыкуюцца больш-менш свабодна выдзяляць гукі, можна пера

### Sample 03 — Бядуля Зьмітрок | *У дрымучых лясах*
- **Source Work:** Бядуля Зьмітрок — *«У дрымучых лясах»*
- **Segment Length:** 205 characters
- **Router Diagnostics:** `broken`: 1

> - Гу-у-уу! - і адскочыў за высокі корч-вываратню.
> Пан Міхайла ўсхапіўся ні жывы ні мёртвы. Працёр лапай спалоханыя вочы. Узняўся на ногі. Прайшоў, як п'яны, некалькі крокаў, паваліўся і ўткнуў морду ў мох.

### Sample 04 — Смоліч Аркадзь | *Географія Беларусі*
- **Source Work:** Смоліч Аркадзь — *«Географія Беларусі»*
- **Segment Length:** 380 characters
- **Router Diagnostics:** `broken`: 1

> Рака Каспля выцякае з досіць значнага возера Касплінскага, якое ляжыць на паўдні павету, недалёка ад Дняпра. Лічаць, што як раз тут знаходзіўся галоўны волак на вадзяным шляху з Варагаў да Грэкаў, бо апошні мусіў ісьці з Дняпра на Касплінскае возера, далей па р. Касплі, перасякау Дзьвіну і падымаўся ўверх па р. Усьвяту да новага волака, перайшоўшы цераз які трапляў у р. Ловаць.

### Sample 05 — Купала Янка | *Раскіданае гняздо*
- **Source Work:** Купала Янка — *«Раскіданае гняздо»*
- **Segment Length:** 775 characters
- **Router Diagnostics:** `broken`: 1

> Сымон (едучы). З'ем, чаму не з'ем? Ад самага рання нічога ў губе не меу. А работы шмат было: сам мусіў яму выкапаць — ніхто не хацеў памагчы, бо, ка-жуць, для вісельніка страшна дол капаць. Ну, няхай !м будзе страшна. Але я ведаю — не страх тут быў прычы-най, а тое, што мы не маем чым заплаціць і чым пачаставаць, не маем за што даць ім гарэлкі, накарміць салам... Не хацелі, і не трэба! Без іх сядзем за жалобным сталом. Ха-ха-ха! Няма чаго сказаць — багаты стол: бульба І вада, вада і бульба!.. Памінкі па родным бацьку, па гаспадару з гаспадароў! Памінкі на раскіда-най хаце, на здратаваных пасев

### Sample 06 — Луцкевіч Антон | *Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.*
- **Source Work:** Луцкевіч Антон — *«Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.»*
- **Segment Length:** 723 characters
- **Router Diagnostics:** `broken`: 5

> Палякі, жывучы у больш значным чысле у захадняй Беларусі, у усходніх губэрнях становяць зусім малы працэнт. У Вітэбскай і Менскай губэрнях палякоу ня больш 2,5% а у Магілеускай толькі 0,9%. Яшчэ меншы працэнт палякоу у Смаленшчыне і Чарнігаушчыне. Да этаго трэба дадаць, што у заходняй Беларусі польскі элемэнт — гэта бадай выключна вялікшая зямельная буржуазія, каторая праз свае соцыальнае становішчэ стаіць вельмі далека ад баларускіх народных масс, ад каторых яна рэзка аддзелена такжэ і рэлігіей: тут беларусы перэважна праваслауные. Толькі у часе вайны у заходнюю Беларусь панаехало много паляк

### Sample 07 — Чорны Кузьма | *Люба Лук'янская*
- **Source Work:** Чорны Кузьма — *«Люба Лук'янская»*
- **Segment Length:** 470 characters
- **Router Diagnostics:** `broken`: 1

> Ён уставіўся вачыма ў шчыт, дзе сапраўды праз акенца вылазіла нейкая вопратка. Каўнер і рукаў матляліся на ветры. Стафанковіч можа хвілін дзесяць не зводзіў вачэй з гэтага каўняра і рукава, моршчыў лоб, прыжмурваў вочы, і постаць яго трымалася ў дзіўнай позе. Ён не брау на ўвагу нікога і нічога, стаяў, шырока растапырыўшы свае дугаватыя ногі, вельмі нейк удала, проста-такі па-ваяцку, трымаючы тонкае сваё тулава, ссунуўшы набакір блінаватую шапку з раменным казырком.

### Sample 08 — Краўчанка Усевалад | *У вагоне*
- **Source Work:** Краўчанка Усевалад — *«У вагоне»*
- **Segment Length:** 1667 characters
- **Router Diagnostics:** `broken`: 6

> — Астатняе расказала нам сама Надзея, калі прыехала дамоў,— але якая прыехала... Тое, што давялося ёй вынесці на паслугах у нямецкай пані, можна параўнаць толькі з пеклам, калі ёсць яно на свеце, а сама фрау Эльза, гаспадыня Надзеі, была жывым увасабленнем ведзьмы. Столькі злосці і атруты магло быць толькі ў чалавека, смяротна пакрыўджанага лёсам. Фрау Эльза была ў крыўдзе на жыццё за тое, што яе муж, які два гады выкручваўся ад мабілізацыі, у пачатку вайны з Расіяй адразу ж быў узяты ў армію і накіраваны на Усходні фронт. Яна з-за гэтага ледзь не ашалела, але яна не мела на кім вымяшчаць сваю

### Sample 09 — Беларуская Народная Творчасць | *Новы Запавет*
- **Source Work:** Беларуская Народная Творчасць — *«Новы Запавет»*
- **Segment Length:** 167 characters
- **Router Diagnostics:** `broken`: 1

> 20 тайна сямёх зорак, што бачыў ты ў правіцы Маёй, ды се́м сьве́тачаў залатых: се́м зорак — Ангелы сямёх цэркваў, а се́м сьве́тачаў, што ты бачыў, ёсьць се́м цэрквау́.

### Sample 10 — Аляхновіч Францішак | *У капцюрох ГПУ*
- **Source Work:** Аляхновіч Францішак — *«У капцюрох ГПУ»*
- **Segment Length:** 339 characters
- **Router Diagnostics:** `broken`: 1

> Пазьней месца расстрэлау было зьменена.
> Дык-жа тут блізка была "женрота". Улада, мусіць, прызнала, што жанкам ня гожа прыглядацца да расстрэлаў, і перанесьлі экзэкуцыі ў дызэнфэкцыйную камару - у межах крамлёўскіх муроў. У лёхах камары ня было чуваць стрэлаў, да таго-ж туды было блізка ад ізалятара - колькі дзесяткаў мэтраў цераз плошчу.

### Sample 11 — Ядвігін Ш. | *Лісты з дарогі*
- **Source Work:** Ядвігін Ш. — *«Лісты з дарогі»*
- **Segment Length:** 900 characters
- **Router Diagnostics:** `broken`: 1

> Каля самых Бакшт круціцца Бярэзіна; на ёй, недалёка валаснога праўлення, ляжыць на самай вадзе плывучы мост; казна бярэ арэнду за права лавіць рыбу ў гэтай рэчцы, ну дык і мост сама ўсё маніцца будаваць ужо пяты год. І я, стоячы над гэтым мастом, доўга думаў: разувацца чы не? Але, узяўшы на адвагу, пусціўся ў сваіх хадаках; праўда, вады паўнюсенька ў іх набрау Выбраўся на бераг; тут жа пачынаецца і Заберазь. Вёска таксама не малая — больш вярсты цягнецца; вуліца шырокая, хаты нішто а што найважнейшае, перад кожнай хатай пасаджаны дрэвы: ліпы, клёны, бярозы і іншыя; і глядзець прыемна, і ад паж

### Sample 12 — Колас Якуб | *Методыка роднай мовы (другое выданне)*
- **Source Work:** Колас Якуб — *«Методыка роднай мовы (другое выданне)»*
- **Segment Length:** 822 characters
- **Router Diagnostics:** `broken`: 1

> Наступны момант работы – расклад слоў на гукі. Для раскладу спачатку лепей браць аднаскладовыя словы з галоснага і зычнага гука: ах, ох, ух. Каб дзеці лягчэй маглі выдзеліць патрэбны гук, настаўнік, вымаўляючы слова, расцягвае гэты гук – ууу-х! Вучні вымаўляюць наўперад усё слова, таксама расцягваючы той ці іншы гук. Потым вымаўляюць асобна першы гук і другі. Каб адрозненне і парадак гукаў цвярдзей усвоіліся вучнямі, настаўнік кажа вучням сказаць першы гук, а сам вымаўляе другі і наадварот – сам пачынае, а дзеці канчаюць. Калі дзеці напрактыкуюцца больш-менш свабодна выдзяляць гукі, можна пера

### Sample 13 — Купала Янка | *Раскіданае гняздо*
- **Source Work:** Купала Янка — *«Раскіданае гняздо»*
- **Segment Length:** 329 characters
- **Router Diagnostics:** `broken`: 2

> Сымон . Так, так, Зоська, твая дачушка, а мая сястрычка родная ў двор да паніча бегае, уся аколіца аб гэтым як у бубен б'е. Я ўсё не верыў, пакуль сам не пераканаўся: заўчора ўсю ноч там прападала. Я відзеў, але маўчау, бо яшчэ тата быу не пахаваны, не хацеў пры нябожчыку аб гэтым новым нашым няшчасці казаць і калатню падымаць.

### Sample 14 — Луцкевіч Антон | *Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.*
- **Source Work:** Луцкевіч Антон — *«Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.»*
- **Segment Length:** 1960 characters
- **Router Diagnostics:** `broken`: 7

> Закраталося і праваслаунае духавенство, цэнтрам катораго аказалася Масква: тут папалі блізка усе вывезеные з Гродзеншчыны і Віленшчыны сьвяшчэнікі. На адбыушымся тамака у летку 1917 года зьездзі было каля 800 праваслауных сьвяшчэнікау- беларусау, вынесшых рэзалюціі у беларускім нацыональным духу. Між праваслауным духовенствам выдзеляюцца імены протоерэя Кульчыцкаго (у Менску), сьв. Усакоускаго, прот. Корчынскаго, сьв.Рэпніна і інш. Ячшэ да вайны і рэвалюцыіі між прафэсурай вышейшых і сярэдніх школ звертаюць на сябе увагу: праф. Б. Эпімах-Шыпілло, вядомы беларускі філелег праф. Е. Карскі, праф.

### Sample 15 — Беларуская Народная Творчасць | *Сьвятая Біблія. Новы Запавет*
- **Source Work:** Беларуская Народная Творчасць — *«Сьвятая Біблія. Новы Запавет»*
- **Segment Length:** 216 characters
- **Router Diagnostics:** `broken`: 1

> Ціт (Тытус) быу грэкам, паганцам, з паганскіх бацькоў. Пэўне быў навернены самым Апосталам, бо ён заве яго сваім сынам. Ціт быў таварышам сьв. Паўла ў многіх яго падарожжах, пачынаючы ад сабора Апосталаў у Ерузаліме.

### Sample 16 — Купала Янка | *Раскіданае гняздо*
- **Source Work:** Купала Янка — *«Раскіданае гняздо»*
- **Segment Length:** 268 characters
- **Router Diagnostics:** `broken`: 1

> Старац . Ведаю! Важны чалавек быу — гаспадар-ны і справядлівы быў. Колькі раз я ні заходзіў, заўсёды вока на мяне добрае меў. Вечнае яму спачыванне, і няхай зямелька для яго лёганькай будзе, а Бог найвы-шэйшы пляму з яго душачкі здыме, што налажыў сам на яе з роспачы.

### Sample 17 — Луцкевіч Антон | *Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.*
- **Source Work:** Луцкевіч Антон — *«Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.»*
- **Segment Length:** 989 characters
- **Router Diagnostics:** `broken`: 10

> Завяршэньне беларускае палітычнае работы становіць Усебеларускі Зьезд у Менску ад 18 да 30 сьнежня 1917 г. н. с., каторы, як вядома, быу разогнаны большэвікамі. Зьезд складауся с 1167 выбарных дэпутатау ад валасьцей, паветовых і губэрскіх самаупраленьняу і мест беларускіх (нават Смаленск прыслау 10 дэпутатоу) с правам пастанауляючаго голасу і с 705 дэпутатоу з голасам дарадчым і меу характэр Беларускай Констытуанты. Зьезд гэты пастановіу прыступіць да організаціі Беларускай Народнай Рэспублікі, прауда, згодне з духам мамэнту і рэальнымі варункамі, яшчэ у фэдэраціі з Расеей, але і гэта пастанов

### Sample 18 — Беларуская Народная Творчасць | *Сьвятая Бібля: Кнігі Старога і Новага Закону*
- **Source Work:** Беларуская Народная Творчасць — *«Сьвятая Бібля: Кнігі Старога і Новага Закону»*
- **Segment Length:** 127 characters
- **Router Diagnostics:** `broken`: 2

> 18 І жыў Фалек трыццаць год, і нарадзіў Рэу. 19 І жыў Фалек, па нараджэньню Рэу, дзьвесьце дзевяць год, і радзіў сыноў і дачкі.

### Sample 19 — Купала Янка | *Раскіданае гняздо*
- **Source Work:** Купала Янка — *«Раскіданае гняздо»*
- **Segment Length:** 1403 characters
- **Router Diagnostics:** `broken`: 1

> Зоська (перастаушы круціцца) . А! Як відненька! А я думала, што ўжо ночка наступіла і мне трэба к майму саколіку збірацца. (Разглядаючы.) Чаго ж я, дурная, длякаюся? Гэта ж ён тут! Тут мой каралевіч ненаглядны! (Паказваючы на дзерава, на каторым абраз вісіць.) Во дзе ён! Во! Адзін, як сіротка, стаіць і чакае, пакуль я, яго зорка нябесная, к яму не падыду. Ужо іду, ужо іду, мае сонейка мілае! (Падыходзіць і абымае дзерава, прытуляючы твар свой к яму.) Выбачай, саколік, што так позна прыйшла я к табе сягоння! Вялікую дарогу мусіла перабыць. Гадзіны на мяне сыкалі, ваўкі вылі, начніцы і совы пужа

### Sample 20 — Луцкевіч Антон | *Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.*
- **Source Work:** Луцкевіч Антон — *«Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.»*
- **Segment Length:** 407 characters
- **Router Diagnostics:** `broken`: 5

> Усебеларускі Зьезд, а асабліва яга разгон, меу страшэньне вялікую вагу і яшчэ дзеля аднае прычыны. Ужо раней беларускіе нацыональные дамаганьня сустрэчаліся с сурьёзнымі прашкодамі са стараны большэвікоу, каторые у іх бачылі буржуазнасьць і контррэволюціонізм. Разгон Зьезду, як самае найгрубейшае пасяганьне на вярхоуные правы Беларускаго Народу на яго зямлі, давеу разрыу беларусау з большэвікам да канца.

### Sample 21 — Беларуская Народная Творчасць | *Сьвятая Бібля: Кнігі Старога і Новага Закону*
- **Source Work:** Беларуская Народная Творчасць — *«Сьвятая Бібля: Кнігі Старога і Новага Закону»*
- **Segment Length:** 130 characters
- **Router Diagnostics:** `broken`: 2

> 20 І жыў Рэу трыццаць два гады, і нарадзіў Сэруґа. 21 І жыў Рэу, па нараджэньню Сэруґа, дзьвесьце сем год, і радзіў сыноў і дачкі.

### Sample 22 — Луцкевіч Антон | *Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.*
- **Source Work:** Луцкевіч Антон — *«Усходняя Беларусь. Статыстычные і гістарычные матэрыялы.»*
- **Segment Length:** 1102 characters
- **Router Diagnostics:** `broken`: 5

> Аднак, ані Рада Б. Н. Р., ані Народны Сэкрэтарыят немцамі не былі развязаны і далей выпоунялі свае функціі у тых межах, у якіх гэта была магчымо. А у першы чарод, яны заняліся справай прауна-дзержаунаго палажэньня Беларусі. Тутъ узнялася вострая коллізія між беларусамі і організацыямі большэвіцкімі, трэба адзначыць, зложэнымі с прэдстаунікау чужых нацый. Пад той час, як беларусы (а такжэ частка жыдоу) цьверда стаялі за поуную гасударственую незалежнасць Беларусі і разрыу дзержауных звязей з Расеей, большэвіцкіе элемэнты дабіваліся прызнаньня фэдэралізму з Расеей. На заседаньні Рады Беларускае

### Sample 23 — Беларуская Народная Творчасць | *Сьвятая Бібля: Кнігі Старога і Новага Закону*
- **Source Work:** Беларуская Народная Творчасць — *«Сьвятая Бібля: Кнігі Старога і Новага Закону»*
- **Segment Length:** 688 characters
- **Router Diagnostics:** `broken`: 1

> 21 І маліу́ Ісак СПАДАРА праз жонку сваю, бо яна была́ бясплодная; і даўся ўмаліць СПАДАР, і зачала́ Рэвека, жонка ягоная. 22 І штырхаліся сыны ў нутру ейным, і яна сказала: "Калі так, дык чаму я такая?" І пайшла папытацца ў СПАДАРА. 23 І сказаў СПАДАР ёй: "Два народы ў жываце тваім, і два люды з нутра твайго разлучацца; і адзін люд стане дужшым за другі, і старшы будзе служыць малодшаму". 24 І споўніліся дні ейныя радзіць: і вось, блізьняты ў жываце ейным. 25 І вышаў першы, чырвоны, увесь, як адзежа, касматы; і назвалі імя ягонае: Ісаў. 26 Потым вышаў брат ягоны, і рука ягоная дзяржала пяту І

### Sample 24 — Беларуская Народная Творчасць | *Сьвятая Бібля: Кнігі Старога і Новага Закону*
- **Source Work:** Беларуская Народная Творчасць — *«Сьвятая Бібля: Кнігі Старога і Новага Закону»*
- **Segment Length:** 227 characters
- **Router Diagnostics:** `broken`: 1

> 11 І сказау Валак Валааму: "Што ты імне робіш? Я ўзяў цябе праклясьці варагоў маіх, а ты, вось, дабраславенствам дабраславіш ?" 12 І адказаў ён, і сказаў: "Ці ня тое, што ўложа СПАДАР у вусны мае, ці ня тое маю рупіцца казаць?"

### Sample 25 — Беларуская Народная Творчасць | *Сьвятая Бібля: Кнігі Старога і Новага Закону*
- **Source Work:** Беларуская Народная Творчасць — *«Сьвятая Бібля: Кнігі Старога і Новага Закону»*
- **Segment Length:** 405 characters
- **Router Diagnostics:** `broken`: 1

> 28 І расказаў празь іх Масей Елеазару сьвятару а Ігошуу Нунянку а галавам айцоў пакаленьняў сыноў Ізраелявых; 29 І сказаў Масей ім: "Калі пярэйдуць сынове Ґадовы а сынове Рувінавы з вамі за Ёрдан, кажны збройна на вайну перад СПАДАРОМ, і паддана будзе вам зямля, то аддайце ім зямлю Ґілеад у дзяржаньне. 30 Калі ж ня пойдуць яны збройна з вамі, то яны адзяржаць дзяржаву разам із вамі ў зямлі Канаанскай".

### Sample 26 — Беларуская Народная Творчасць | *Сьвятая Бібля: Кнігі Старога і Новага Закону*
- **Source Work:** Беларуская Народная Творчасць — *«Сьвятая Бібля: Кнігі Старога і Новага Закону»*
- **Segment Length:** 793 characters
- **Router Diagnostics:** `broken`: 1

> 23 "І малі́ўся я СПАДАРУ таго часу, кажучы: 24 ,Спадару СПАДАРУ, Ты пачаў паказаваць слузе Свайму вялікасьць Сваю й моцную руку́ Сваю; бо які Бог ё на нябёсах і на зямлі, каторы дзеяў бы подле ўчынкаў Тваіх і моцы Твае? 25 Дай імне перайсьці й абачыць тую добрую зямлю, што за Ёрданом, і тую пазорную гару а Лібан'. 26 Але СПАДАР гневаўся на мяне за вас, і не паслухаў мяне, і сказаў СПАДАР імне: ,Досыць табе, не кажы Імне болей праз гэта. 27 Узыйдзі на верх Пісґі, і ўзьнімі вочы свае на захад а на поўнач а на паўдня а на ўсход, і паглядзі ачыма сваімі; бо ты не пярэйдзеш гэтага Ёрдану. 28 І раск

### Sample 27 — Беларуская Народная Творчасць | *Сьвятая Бібля: Кнігі Старога і Новага Закону*
- **Source Work:** Беларуская Народная Творчасць — *«Сьвятая Бібля: Кнігі Старога і Новага Закону»*
- **Segment Length:** 1466 characters
- **Router Diagnostics:** `broken`: 1

> 10 Малайчыну жонку хто знойдзе? бо шмат большая за пэрлы цана яе. 11 Пэўнае да яе сэрца мужа ейнага, і прыбытку ня будзе нястачы. 12 Робе дабро яму, а ня ліха, усі дні жыцьця свайго. 13 Шукае воўны а лёну і ахвотна робе рукамі сваімі. 14 Яна, як караблі купецкія, зда́леку дастаўляе емя свае. 15 І ўстаець яшчэ ночы, і раздаець ежу хатнім сваім, і належнае служэбкам сваім. 16 Яна падумала праз поле й прыдбала яго; з пладоў рук сваіх яна садзе вінішча. 17 Папяразуе сілаю сьцёгны свае й мацуе рукі свае. 18 Цеме, што тавар ейны добры; ня гасьне ночы сьветач ейны. 19 Выцягуе рукі свае да прасьніцы й

### Sample 28 — Беларуская Народная Творчасць | *Чатыры Эванэліі і Апостальскія Дзеі*
- **Source Work:** Беларуская Народная Творчасць — *«Чатыры Эванэліі і Апостальскія Дзеі»*
- **Segment Length:** 870 characters
- **Router Diagnostics:** `broken`: 1

> 23 У той дзень прыступілі да яго садукеі, каторыя кажуць, што няма ўскрашэньня, і спыталіся ў яго, 24 кажучы: Вучыцель, Майсей сказаў: "Каліб хто памёр, ня маючы сына, то брат ягоны возьме яго жонку і ўскрасіць патомства брату свайму" (Паўл. Пр. 25, 5) . 25 Было-ж у нас сем братоў: першы, ажаніўшыся, памёр і, ня маючы патомства, пакінуў жонку сваю брату свайму. 26 Таксама другі і трэці аж да сёмага. 27 А ўканцы пасьля ўсіх памярла і жонка. 28 Дыу у ўскрашеньні чыёй з сямёх будзе яна жонкай? Бо ўсе мелі яе. 29 А Езус, адказваючы, сказаў ім: Вы мыляецеся, ня ведаючы Пісаньняў ані моцы Божай. 30

### Sample 29 — Беларуская Народная Творчасць | *Святое Евангелле паводле Лукі*
- **Source Work:** Беларуская Народная Творчасць — *«Святое Евангелле паводле Лукі»*
- **Segment Length:** 51 characters
- **Router Diagnostics:** `broken`: 1

> 25 Матафі́еў, Амо́саў, Нау́маў, Еслі́маў, Нагге́еў,

### Sample 30 — Беларуская Народная Творчасць | *Святое Евангелле паводле Лукі*
- **Source Work:** Беларуская Народная Творчасць — *«Святое Евангелле паводле Лукі»*
- **Segment Length:** 50 characters
- **Router Diagnostics:** `broken`: 1

> 26 Маа́фаў, Матафі́еў, Семеі́еў, Іо́сіфаў, Іу́даў,

---
