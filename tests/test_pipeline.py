import pytest

from tinydesk import pipeline, state
from tinydesk.config import Config


@pytest.fixture
def workspace(tmp_path):
    ws = pipeline.Workspace(tmp_path, Config())
    songs = ws.library / "Artist"
    songs.mkdir(parents=True)
    (songs / "01 - One.m4a").write_bytes(b"one")
    (songs / "02 - Two.m4a").write_bytes(b"two")
    db = state.State(ws.database)
    db.save(
        "vid", "Artist : Tiny Desk", state.OK, artist="Artist", files=["Artist/01 - One.m4a", "Artist/02 - Two.m4a"]
    )
    return ws, db, tmp_path / "music"


def test_delivery_copies_once(workspace):
    ws, db, music = workspace
    music.mkdir()
    assert pipeline.deliver(db.get("vid"), ws, music, db) is True
    assert sorted(p.name for p in music.iterdir()) == ["Artist - 01 - One.m4a", "Artist - 02 - Two.m4a"]
    assert db.get("vid").delivered

    for imported in music.iterdir():  # Music moves files out of the folder after importing them
        imported.unlink()
    assert pipeline.deliver(db.get("vid"), ws, music, db) is False
    assert not list(music.iterdir())


def test_delivered_episodes_cannot_be_cut_again(workspace):
    ws, db, music = workspace
    music.mkdir()
    pipeline.deliver(db.get("vid"), ws, music, db)
    (ws.review).mkdir(parents=True)
    with pytest.raises(pipeline.UserError, match="already delivered"):
        pipeline.approve("vid", ws, db)
    with pytest.raises(pipeline.UserError, match="already delivered"):
        pipeline.apply("vid", ws.root / "times.json", ws, db)
    with pytest.raises(pipeline.UserError, match="already delivered"):
        pipeline.sync_episode("vid", ws, db)
    assert db.get("vid").delivered
