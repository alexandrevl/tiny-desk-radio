# Tiny Desk Radio

[English](README.md) | **Português (pt-BR)**

O `tinydesk` transforma um canal ou playlist de Tiny Desk do YouTube em **um arquivo M4A etiquetado por
música** e entrega tudo ao Apple Music, para você ouvir todos os artistas em modo aleatório, como uma rádio.

Já vem configurado para o canal [Tiny Desk Brasil](https://www.youtube.com/channel/UCFV9qv5deOsJ_AF7k_t4h3A)
e funciona com qualquer outro canal ou playlist que publique shows completos com a lista de músicas na
descrição (Tiny Desk Concerts da NPR Music, de outros países etc.).

> **Aviso.** Ferramenta de uso pessoal. Você é responsável por cumprir os Termos de Serviço do YouTube e a
> lei de direitos autorais do seu país. Veja [Aviso legal](#aviso-legal).

## Recursos

- **Um arquivo por música, sem recodificar**: as faixas são cortadas do áudio AAC do YouTube com
  `ffmpeg -c copy`. Aplausos e falas entre as músicas ficam de fora.
- **Descobre as músicas sozinho**: a lista vem da descrição do vídeo; os limites vêm dos capítulos do
  YouTube quando existem, ou de análise de áudio (energia de graves, volume, tonalidade e o detector de
  música do [YAMNet](https://www.tensorflow.org/hub/tutorials/yamnet)).
- **Conferência pela letra**: um modelo Whisper local escuta o show e confirma qual música é qual, porque
  a descrição nem sempre segue a ordem em que as músicas foram tocadas.
- **Fila de revisão**: quando a detecção não fecha, nada é entregue. O episódio vai para a revisão com um
  relatório, uma proposta de corte e a transcrição do que se fala entre as músicas.
- **Tags completas**: título, artista, artista do álbum, álbum, gênero, ano, número da faixa e capa.
- **Incremental**: o `sync` só processa vídeos novos; o estado fica num SQLite local.
- **Fonte configurável**: flag, variável de ambiente ou `tinydesk.toml`.
- Tudo roda na sua máquina; sem contas e sem chaves de API.

## Requisitos

| O quê | Para quê | Plataforma |
| --- | --- | --- |
| Python 3.12 e [uv](https://docs.astral.sh/uv/) | tudo | qualquer |
| [`ffmpeg`](https://ffmpeg.org) no `PATH` | cortar e decodificar | qualquer |
| [`mlx-whisper`](https://github.com/ml-explore/mlx-examples/tree/main/whisper) | conferência pela letra e transcrições da revisão | **somente macOS com Apple Silicon** |
| Apple Music | pasta de entrega | macOS |

O que é específico do macOS: o `mlx-whisper` (instalado só em macOS/arm64, por marcador de ambiente) e a
pasta de adição automática do Apple Music. O resto (listagem, download, análise de áudio, corte, tags,
testes) é Python puro e roda também no Linux, mas o `sync` ainda depende da transcrição; portanto uma
execução completa só é suportada em Macs com Apple Silicon. Nos demais sistemas dá para usar
`sync --dry-run`, os testes e a biblioteca. Um backend de transcrição plugável está no
[roteiro](#roteiro).

## Instalação

```sh
brew install ffmpeg            # macOS; em outros sistemas, use o seu gerenciador de pacotes
git clone https://github.com/alexandrevl/tiny-desk-radio.git
cd tiny-desk-radio
uv sync
```

Na primeira execução real são baixados dois modelos: YAMNet (4 MB) e Whisper large-v3-turbo (cerca de
1,6 GB, do Hugging Face). Cada show em cache ocupa cerca de 20 MB em `data/audio`, o que acelera novas
execuções.

## Início rápido

```sh
uv run tinydesk sync --dry-run               # mostra quais vídeos a fonte encontra; não baixa nada
uv run tinydesk sync --limit 1 --no-deliver  # processa um episódio para ./library, sem tocar no Music
uv run tinydesk list                         # situação de cada episódio
uv run tinydesk sync                         # catálogo inteiro; entrega os episódios `ok` ao Music
```

As músicas ficam em `./library/<Artista>/<NN> - <Título>.m4a`. Os episódios no estado `ok` também são
copiados, uma única vez, para a pasta de adição automática do Music
(`~/Music/Music/Media.localized/Automatically Add to Music.localized`).

### Outro canal ou playlist (Tiny Desk Concerts da NPR)

```sh
uv run tinydesk sync --dry-run \
  --source "https://www.youtube.com/playlist?list=PL1B627337ED6F55F0" \
  --include "tiny desk" --exclude "contest|behind the scenes" --language en
```

Ou deixe num `tinydesk.toml` no diretório onde você roda o comando (veja [`examples/`](examples)):

```toml
source = "https://www.youtube.com/playlist?list=PL1B627337ED6F55F0"
include = "tiny desk"
exclude = "contest|behind the scenes"
language = "en"
```

Para qualquer canal você precisa de três coisas: a URL do canal ou da playlist, uma regex `include` que
case apenas com os títulos dos shows completos e, se os títulos não forem no formato
`Artista: Tiny Desk ...`, um `title_pattern` que extraia o artista. Use `sync --dry-run` para conferir o
filtro antes de baixar qualquer coisa. A URL raiz de um canal (`https://www.youtube.com/@nome`) é lida
como a aba Vídeos.

## Referência de comandos

| Comando | O que faz |
| --- | --- |
| `tinydesk sync` | Processa os episódios da fonte que ainda não estão no banco de estado e entrega os `ok`. |
| `tinydesk sync --limit N` | Processa no máximo `N` episódios novos. |
| `tinydesk sync --video ID` | (Re)processa um vídeo. |
| `tinydesk sync --no-deliver` | Só monta o `./library`. |
| `tinydesk sync --dry-run` | Lista os vídeos encontrados e a situação deles; não baixa nada. |
| `tinydesk list` | Tabela de todos os episódios: estado, músicas na lista, detectadas, entregue, motivo. |
| `tinydesk approve ID` | Aceita o corte proposto de um episódio em `review` e o entrega. |
| `tinydesk apply ID times.json` | Corta um episódio em `review` onde você indicar e o entrega. |

`sync`, `approve` e `apply` aceitam todas as flags de configuração abaixo e `--no-deliver`.

Estados: `ok` (cortado, etiquetado, na biblioteca), `review` (precisa de uma pessoa, veja abaixo),
`skipped` (sem lista de músicas ou artista não identificado no título).

## Configuração

Precedência: **flag > variável de ambiente > `tinydesk.toml` > padrão**. O TOML é lido do diretório atual
ou de `--config ARQUIVO`. Chaves desconhecidas dão erro.

| Configuração (chave TOML) | Flag | Ambiente | Padrão |
| --- | --- | --- | --- |
| `source` | `--source` | `TINYDESK_SOURCE` | o canal Tiny Desk Brasil |
| `include` | `--include` | `TINYDESK_INCLUDE` | `tiny desk (brasil\|brazil)` |
| `exclude` | `--exclude` | `TINYDESK_EXCLUDE` | `premiere\|tiny ?talks` |
| `title_pattern` | `--title-pattern` | `TINYDESK_TITLE_PATTERN` | `^(?P<artist>.+?)\s*:\s*(?:npr music )?tiny desk\b` |
| `language` | `--language` | `TINYDESK_LANGUAGE` | `pt` |
| `setlist_headers` | `--setlist-headers a,b` | `TINYDESK_SETLIST_HEADERS` | `setlist, set list, tracklist, track list, playlist, músicas, musicas, repertório, repertorio` |
| `album` | `--album` | `TINYDESK_ALBUM` | `Tiny Desk Radio` |
| `genre` | `--genre` | `TINYDESK_GENRE` | `Tiny Desk` |
| `cookies_from_browser` | `--cookies-from-browser` | `TINYDESK_COOKIES_FROM_BROWSER` | nenhum; use `chrome` se o YouTube pedir para confirmar que você não é um robô |
| `library` | `--library` | `TINYDESK_LIBRARY` | `library` |
| `music_dir` | `--music-dir` | `TINYDESK_MUSIC_DIR` | pasta de adição automática do Music |

Observações:

- `include`, `exclude` e `title_pattern` são expressões regulares sem distinção de maiúsculas.
  `title_pattern` precisa ter um grupo nomeado `(?P<artist>...)`.
- `language` é o código de idioma da letra para o Whisper (`pt`, `en`, `es`...).
- A lista de músicas é o bloco de linhas depois de uma linha de cabeçalho (a linha inteira deve ser uma das
  palavras de `setlist_headers`), um título por linha, até a primeira linha em branco. Aspas em volta dos
  títulos são removidas.
- O banco de estado (`data/state.db`) usa o id do vídeo como chave, então dá para trocar de fonte à
  vontade: episódios já processados são pulados, de qualquer fonte. Mudar os filtros não reavalia episódios
  já registrados; use `sync --video ID` para eles.

## Como um episódio é dividido

1. **Lista de músicas.** Os títulos sob o cabeçalho da descrição (episódios sem lista são pulados).
2. **Limites.** Capítulos do YouTube, se o vídeo tiver. Senão, cada 0,25 s de áudio recebe uma nota de
   "música" a partir de quatro sinais independentes que caem durante aplausos e falas: energia de graves,
   volume, tonalidade espectral e a probabilidade de música do YAMNet. Sabendo que são exatamente *N*
   músicas, a ferramenta escolhe os *N* trechos disjuntos de maior nota total e depois alarga as bordas
   por passagens silenciosas que o YAMNet ainda reconhece como música.
3. **Títulos.** Associados na ordem da lista, a menos que o Whisper ouça um título sendo cantado em outra
   música; nesse caso os títulos seguem a letra.
4. **Corte e tags.** `ffmpeg -c copy`, depois tags e capa (a miniatura do vídeo) com o mutagen.

### Fila de revisão

Um episódio vai para `review` (nada é entregue) quando:

- menos músicas são separadas por aplausos ou fala do que a lista indica (músicas seguidas);
- uma faixa fica com menos de 90 s ou mais de 10 min;
- a letra sugere ordem diferente da lista, mas um dos títulos movidos não pode ser confirmado;
- a lista e os capítulos discordam.

O arquivo `data/review/<video_id>.json` traz então os problemas, o corte proposto (`proposed`, tempos em
segundos) e a transcrição do que se fala entre as músicas propostas. Depois:

```sh
uv run tinydesk approve <video_id>            # a proposta está certa
uv run tinydesk apply <video_id> times.json   # corrija: [{"title": "...", "start": 7.7, "end": 150.0}, ...]
```

Um episódio já entregue não pode ser cortado de novo (isso colocaria músicas duplicadas no Music); o
comando avisa e não faz nada.

## Playlist inteligente no Music

Toda música tem álbum **Tiny Desk Radio** (ou o seu `album`) e gênero **Tiny Desk**. No Music:
*Arquivo ▸ Novo ▸ Playlist Inteligente…*, defina **Álbum** **é** `Tiny Desk Radio`, mantenha
*Atualização em tempo real* ligada, dê um nome e use o modo aleatório. Os episódios novos entram sozinhos
assim que o `tinydesk sync` os entrega.

## Solução de problemas

- **`ffmpeg: command not found`**: instale o ffmpeg e garanta que está no `PATH`.
- **Avisos do yt-dlp sobre desafio de JavaScript**: normalmente inofensivos. Se os downloads falharem,
  atualize o yt-dlp (`uv lock --upgrade-package yt-dlp && uv sync`); instalar o `deno` pode ajudar.
- **`transcription needs mlx-whisper`**: o `sync` completo exige macOS com Apple Silicon.
- **`Music auto-add folder not found`**: defina `music_dir` / `--music-dir` ou use `--no-deliver`.
- **As músicas não aparecem no Music**: o Music importa da pasta de adição automática enquanto está
  aberto. O que ele não consegue importar vai para uma pasta "Not Added" ao lado da pasta de adição.
- **Episódio em `review` ou títulos fora de ordem**: veja o relatório em `data/review/`.
- **Recomeçar um episódio**: `sync --video ID` (impossível depois de entregue).

## Limitações

- O áudio é o que o YouTube serve: AAC a cerca de 128-160 kbps. Não há recodificação, então a qualidade é
  a da fonte; não é sem perdas.
- A análise de áudio é heurística. Músicas emendadas, apresentações faladas sobre a música e intros muito
  baixas podem ser cortadas com um a três segundos de diferença, ou ser fundidas. A fila de revisão pega
  muitos casos, não todos: confira o que entregar. As faixas não têm fade.
- As listas são lidas de texto livre; descrições fora do formato "cabeçalho e um título por linha" são
  puladas.
- O Whisper pode ouvir a letra errado; ele só serve de conferência e para as transcrições da revisão.
- Execuções completas exigem Apple Silicon hoje (veja Requisitos).

## Roteiro

Mantenedores e contribuições são muito bem-vindos; veja [CONTRIBUTING.md](CONTRIBUTING.md).

- Backend de transcrição plugável (`faster-whisper` ou `whisper.cpp`) para rodar no Linux e no Intel.
- Modo `--no-lyrics`, só com análise de áudio.
- Dividir melhor músicas emendadas sem aplauso (repetições de letra, mudanças de acordes).
- Fades curtos opcionais nos pontos de corte.
- Outros destinos (pastas simples, nomes para Plex/Jellyfin, pastas de importação de outros players).
- Publicação no PyPI e no Homebrew.

Boas primeiras issues:

1. Criar um perfil pronto em `examples/` para outro canal de Tiny Desk, validado com `--dry-run`.
2. Incluir mais palavras de cabeçalho e exemplos reais de descrição em `tests/test_setlist.py`.
3. Um comando `tinydesk review` que mostre os relatórios de revisão de forma legível.
4. Um comando `tinydesk forget ID` que reinicie um episódio no banco de estado.
5. Traduzir o README para outro idioma.

## Desenvolvimento

```sh
uv sync
uv run pytest
uv run ruff check
uv run ruff format --check
```

Os testes não precisam de rede nem de Whisper. Mais detalhes em [CONTRIBUTING.md](CONTRIBUTING.md). As
mudanças estão no [CHANGELOG.md](CHANGELOG.md).

## Suporte

Dúvidas e ideias: abra uma Discussion ou issue no GitHub. Bugs: use o modelo de bug. Música cortada no
lugar errado: use o modelo "Wrong split" e anexe o JSON de revisão. Falhas de segurança: veja
[SECURITY.md](SECURITY.md).

## Aviso legal

- Este projeto é uma **ferramenta de uso pessoal**. Ele baixa áudio do YouTube **na sua máquina**, para
  você. **Você** é responsável por cumprir os [Termos de Serviço do YouTube](https://www.youtube.com/t/terms)
  e a lei de direitos autorais do seu país. Certifique-se de ter o direito de baixar e guardar o conteúdo
  que processar.
- **Este repositório não distribui nenhum conteúdo.** Ele contém apenas código-fonte. Áudio baixado,
  transcrições, o banco de estado e a biblioteca gerada ficam em `data/` e `library/`, ignorados pelo git;
  não os publique nem compartilhe.
- Este projeto **não é afiliado, endossado nem patrocinado** pela NPR, pelo Tiny Desk, pela Anonymous
  Content, pelo YouTube, pelo Google ou pela Apple. Todas as marcas e nomes pertencem aos seus
  respectivos donos.
- O software é fornecido "como está", sem garantias. Veja a [LICENSE](LICENSE) (MIT).

Componentes de terceiros: [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense),
[mutagen](https://github.com/quodlibet/mutagen) (GPL-2.0-ou-posterior; usado como biblioteca),
[mlx-whisper](https://github.com/ml-explore/mlx-examples) e modelos Whisper da OpenAI (MIT),
[YAMNet](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet) (Apache-2.0, modelo
baixado na primeira execução), [ai-edge-litert](https://pypi.org/project/ai-edge-litert/) (Apache-2.0),
[NumPy](https://numpy.org) (BSD-3-Clause).

## Licença

[MIT](LICENSE) © 2026 Alexandre Lima
