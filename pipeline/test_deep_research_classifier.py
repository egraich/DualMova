"""
DualMova — Discriminative Classifier Test Suite (v3.0 Architecture)
=============================================================================
Automated test suite verifying the phonological decision cascades,
closed morphemic seam grammars, loanword matrices, Empirical Bayes document-prior
inheritance, bidirectional Laplace context field, and certified invariant core.
"""

import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from ortho_router import DualMovaOrthographyClassifier, RouteResult


def run_tests():
    clf = DualMovaOrthographyClassifier()

    test_cases = [
        # 1. Authentic Narkamaŭka (Kuzma Chorny prose)
        ("Танк гэты стаяў узняты на ўзгорак з супрацьлеглага боку. Трэба было ісці праз дзверы з дрыжаннем, збіраць касці сляпых.", "nark"),
        # 2. Authentic Classical Taraškievica (BKP-2005)
        ("Танк гэты стаяў узьняты на ўзгорак. Яны ня ведалі, як знайсьці праўду ў гэтым сьвеце. Гэта вялікае пытаньне новага жыцьця і грамадзкай радасьці.", "tarask"),
        # 3. Valid soft-sign occurrences in Narkamaŭka (Morphological seams)
        ("Вядомы беларускі пісьменнік напісаў новае пісьмо, дзе распавёў пра сваю просьбу і сустрэчу з людзьмі.", "nark"),
        ("Станьце тут, калі ласка, і паглядзіце на гэтае дзіўнае зацьменне сонца.", "nark"),
        # 4. Neutral phrases across both standards (Pre-hard neutralization & etymological stems -> Certified Invariant Core)
        ("Бацька і дзядзька пайшлі на пакос, дзе была добрая касьба.", "invariant"),
        ("У студзеньскі вечар дзеці гулялі на вуліцы і нешта шукалі, бо хтосьці пакінуў там цацку.", "invariant"),
        # 5. Loanword phonetic contrasts (European vocabulary, lateral softening)
        ("План развіцця горада Мінска быў зацверджаны ў новай сістэме.", "nark"),
        ("Плян разьвіцьця гораду Менску быў зацьверджаны ў новай сыстэме.", "tarask"),
        # 6. Noise, Russian script intrusion, Russian phonology, and Trasyanka
        ("Этот текст написан на русском языке и должен быть отброшен.", "rejected"),
        ("Государство должно уважать права каждого человека в нашей стране.", "rejected"),
        ("Мама мыла раму, а папа делал новый деревянный стол в комнате.", "rejected"),
        ("Ён пашол у магазін і сказаў, што толька еслі патаму што робітся работа.", "rejected"),
        ("Мы чакалі аўтобус цэлы час, но ён так і не прыехаў на нашу астаноўку.", "rejected"),
        # 7. Short neutral dialogue (Certified Invariant Core when isolated)
        ("— Добрага ранку, матуля! — сказаў Янка.", "invariant"),
        # 8. Stress-test: 3rd-person verbs on -ае + neuter nouns (must be nark, not falsely tarask)
        ("Сучаснае пакаленне чытае кнігі, вывучае дакументы і шукае праўды.", "nark"),
        # 9. Stress-test: Unmarked assimilation (узбярэжжа vs узьбярэжжа -> nark)
        ("Уздоўж узбярэжжа раскінулася зацішша, ноччу ваенны патруль вёз збожжа і тонны грузу.", "nark"),
        # 10. Stress-test: Classical Taraškievica with intra-word apostrophe and soft geminate
        ("Разглядаецца праблема аб’яднаньня, дзе адбываецца новае вясельле і адчыняюцца дзьверы.", "tarask"),
        # 11. Stress-test: Pre-stressed unstressed 'не' and 'без' in Classical Taraškievica (BKP-2005 Chapter 7)
        ("Яна не магла і не хацела заставацца без вады і без дапамогі, але сьнег засыпаў усе сьцежкі.", "tarask"),
    ]

    print("=== DUALMOVA DISCRIMINATIVE CLASSIFIER TEST SUITE (v3.0) ===\n")
    all_passed = True
    for text, expected in test_cases:
        res = clf.classify(text)
        passed = (res.label == expected)
        if not passed:
            all_passed = False
        mark = "[PASS]" if passed else "[FAIL]"
        conf = res.metrics.get("confidence", 0.0)
        reason = res.metrics.get("reason", "")
        print(f"{mark} Expected: {expected:10} | Obtained: {res.label:10} (conf={conf:.3f})")
        print(f"       Text: {text[:65]}...")
        if reason:
            print(f"       Reason: {reason}")
        if res.metrics.get("features"):
            print(f"       Features: {res.metrics.get('features')}")
        print()

    # Document-Prior Context Inheritance Test:
    print("--- Document-Prior Context Inheritance Verification ---")
    doc_log_odds_nark = -3.5  # Document context: strongly Narkamaŭka
    res_inherited = clf.classify("— Добрага ранку, матуля! — сказаў Янка.", doc_prior_log_odds=doc_log_odds_nark)
    conf = res_inherited.metrics.get("confidence", 0.0)
    print(f"Outcome with document prior: label={res_inherited.label}, tag={res_inherited.text_tagged}, conf={conf:.3f}")
    if res_inherited.label == "nark":
        print("[PASS] Document context successfully inherited for neutral segment!")
    else:
        print("[FAIL] Prior inheritance failure!")
        all_passed = False

    # Code-Switching Citation Protection Test (Conflict-Aware Gated Decay):
    print("\n--- Code-Switching Embedded Citation Protection Test ---")
    doc_log_odds_tarask = +3.8  # Enclosing document is Taraskievica book
    quote_nark = "Дзяржаўныя органы забяспечваюць развіццё і функцыянаванне беларускай мовы ва ўсіх сферах грамадскага жыцця."
    res_quote = clf.classify(quote_nark, doc_prior_log_odds=doc_log_odds_tarask)
    print(f"Citation in Taraskievica context: label={res_quote.label}, conf={res_quote.metrics.get('confidence', 0.0):.3f}, local_score={res_quote.metrics.get('local_score', 0.0)}")
    if res_quote.label == "nark":
        print("[PASS] Code-switching citation successfully preserved despite document prior!")
    else:
        print("[FAIL] Context poisoning: citation misclassified due to prior!")
        all_passed = False

    print(f"\nOVERALL RESULT: {'ALL TESTS PASSED (100%)' if all_passed else 'TEST FAILURE DETECTED'}")
    return all_passed


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
