"""Expérience 2 : le modèle de cloches retrouve des faits connus avant toute recherche."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiences" / "exp2_erin"))
import run as R  # noqa: E402


def _course(alterne):
    tete, sorte, n = tuple(range(7)), 0, 0
    while True:
        _, d = R.six(tete, sorte)
        tete = R.appliquer(d, R.P7)
        n += 1
        if alterne:
            sorte = 1 - sorte
        if tete == tuple(range(7)) and sorte == 0:
            return n * 6


def test_courses_normales_connues():
    assert _course(True) == 84      # Stedman Triples
    assert _course(False) == 42     # Erin Triples


def test_structure_de_knuth():
    _, noeuds = R.graphe("erin")
    blocs = {rs for rs, _ in noeuds.values()}
    assert len(noeuds) == 2520 and len(blocs) == 840


def test_verification_refuse_une_course_seule():
    assert not R.verifier("erin", [0] * 7)
    assert not R.verifier("stedman", [0] * 14)
