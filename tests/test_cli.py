from pathlib import Path

from dataplatform.cli import init


def test_init_creates_files(tmp_path: Path):
    assert init(tmp_path) == 0
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".mcp.json").exists()
    assert (tmp_path / ".claude/agents/job-validator.md").exists()
    assert (tmp_path / ".claude/skills/validar-job/SKILL.md").exists()
    assert (tmp_path / ".claude/commands/validar-job.md").exists()
    assert (tmp_path / ".claude/skills/analyze-job-run/SKILL.md").exists()
    assert (tmp_path / ".claude/skills/analyze-job-run/reference/glue-errors.md").exists()
    assert (tmp_path / ".claude/agents/job-diagnoser.md").exists()
    assert (tmp_path / ".claude/commands/analyze-job-run.md").exists()


def test_list_runs_without_mcp_extra(capsys):
    from dataplatform.cli import list_all

    assert list_all() == 0
    out = capsys.readouterr().out
    assert "data-platform init" in out
    assert "validar-job" in out


def test_init_is_idempotent_and_preserves_edits(tmp_path: Path):
    init(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("meu conteúdo", encoding="utf-8")
    init(tmp_path)  # segunda passada não sobrescreve
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == "meu conteúdo"


def test_init_force_overwrites(tmp_path: Path):
    init(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("x", encoding="utf-8")
    init(tmp_path, force=True)
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") != "x"
