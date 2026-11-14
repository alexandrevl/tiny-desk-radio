from tinydesk.config import Config
from tinydesk.setlist import parse_artist, parse_setlist

CONFIG = Config()

# Excerpts of real descriptions from the channel.
MARINA_SENA = """LORENA CALABRIA || “Aqui, menos é mais.” Foi com essa ideia que Marina Sena concebeu sua apresentação.

Baseado no “Tiny Desk Concerts” criado por NPR
Produzido por Anonymous Content Brazil

setlist

Numa ilha
Por supuesto
Doçura
Coisas naturais
Cabelo

***

músicos
Marina Sena - Voz
"""

TIM_BERNARDES = """Setlist
Nascer, Viver, Morrer
Mistificar
BB (Garupa de Moto Amarela)
Realmente Lindo
Última Vez
Meus 26
Todas as canções foram compostas por Tim Bernardes. 

Banda
Tim Bernardes
"""

DUQUESA = """O set list percorre diferentes facetas da artista. “Dois Mundos” abre como um manifesto íntimo.

***

músicas 

Dois Mundos
Big D!!!!! Pt. 2
Big D!!!!!
Fuso


músicos

Duquesa - voz
"""

GIOVANI_NO_HEADER = """Cantor, compositor e instrumentista.

Setlist da noite foi escolhido com cuidado.
"""


def test_setlist_after_header_with_blank_line():
    assert parse_setlist(MARINA_SENA, CONFIG) == ["Numa ilha", "Por supuesto", "Doçura", "Coisas naturais", "Cabelo"]


def test_setlist_stops_before_credits_sentence():
    assert parse_setlist(TIM_BERNARDES, CONFIG)[-2:] == ["Última Vez", "Meus 26"]
    assert len(parse_setlist(TIM_BERNARDES, CONFIG)) == 6


def test_musicas_header_and_prose_mentioning_set_list():
    assert parse_setlist(DUQUESA, CONFIG) == ["Dois Mundos", "Big D!!!!! Pt. 2", "Big D!!!!!", "Fuso"]


def test_no_setlist():
    assert parse_setlist(GIOVANI_NO_HEADER, CONFIG) == []


def test_artist_from_title():
    assert parse_artist("Marina Sena : Tiny Desk Brasil", CONFIG) == "Marina Sena"
    assert parse_artist("Mateus Fazeno Rock: Tiny Desk Brazil", CONFIG) == "Mateus Fazeno Rock"
    assert parse_artist("Gilberto Gil, Flor e Bento : Tiny Desk Brasil", CONFIG) == "Gilberto Gil, Flor e Bento"
    assert parse_artist("Metá Metá & Negro Leo: Tiny Desk Brasil", CONFIG) == "Metá Metá & Negro Leo"
    assert parse_artist("Tiny Remix: LARINHX and niLL watch Tulipa Ruiz", CONFIG) is None


NPR = """Tyler Childers performs live at the Tiny Desk.

SET LIST
“Nose on the Grindstone”
“In Your Love”
“Jersey Giant”

MUSICIANS
Tyler Childers: vocals
"""


def test_npr_style_setlist_with_quoted_titles():
    assert parse_setlist(NPR, CONFIG) == ["Nose on the Grindstone", "In Your Love", "Jersey Giant"]


def test_custom_setlist_headers():
    config = Config(setlist_headers=("canciones",))
    assert parse_setlist("Canciones:\nUno\nDos\n\nBanda", config) == ["Uno", "Dos"]
    assert parse_setlist("Setlist\nUno", config) == []


def test_artist_from_other_title_styles():
    assert parse_artist("Tyler Childers: Tiny Desk Concert", CONFIG) == "Tyler Childers"
    assert parse_artist("Laura Gibson: NPR Music Tiny Desk Concert", CONFIG) == "Laura Gibson"
    assert parse_artist("Tiny Desk Concert - Mitski", CONFIG) is None
    custom = Config(title_pattern=r"^Tiny Desk Concert\s*-\s*(?P<artist>.+)$")
    assert parse_artist("Tiny Desk Concert - Mitski", custom) == "Mitski"
