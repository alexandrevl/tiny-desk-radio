from tinydesk.lyrics import Phrase, normalize, order_by_lyrics
from tinydesk.segmentation import Span

SPANS = [Span(0, 100), Span(110, 200), Span(210, 300)]


def phrases(*sung: tuple[float, str]) -> list[Phrase]:
    return [Phrase(at, at + 3, text) for at, text in sung]


def test_normalize_ignores_case_accents_and_punctuation():
    assert normalize("Doçura, é MINHA cura!") == "docura e minha cura"


def test_setlist_order_stands_when_titles_are_sung_in_place():
    titles = ["Numa ilha", "Por supuesto", "Doçura"]
    heard = phrases((20, "Descalça numa ilha"), (150, "por supuesto que não"), (250, "essa doçura é minha cura"))
    assert order_by_lyrics(titles, SPANS, heard) == (titles, [])


def test_setlist_order_stands_when_nothing_is_heard():
    titles = ["Numa ilha", "Por supuesto", "Doçura"]
    assert order_by_lyrics(titles, SPANS, phrases((20, "la la la"))) == (titles, [])


def test_titles_follow_the_lyrics_when_played_in_another_order():
    titles = ["Demônio Colorido", "Retratos e Canções", "Olhos Coloridos"]
    heard = phrases(
        (20, "meus olhos coloridos me fazem refletir"), (150, "meu demônio colorido"), (250, "retratos e canções")
    )
    assert order_by_lyrics(titles, SPANS, heard) == (
        ["Olhos Coloridos", "Demônio Colorido", "Retratos e Canções"],
        [],
    )


def test_a_title_moved_without_being_heard_is_reported():
    titles = ["Sozinho", "Demônio Colorido", "Olhos Coloridos"]
    heard = phrases((20, "meu demônio colorido"), (150, "olhos coloridos"))
    ordered, unverified = order_by_lyrics(titles, SPANS, heard)
    assert ordered == ["Demônio Colorido", "Olhos Coloridos", "Sozinho"]
    assert unverified == ["Sozinho"]
