from taskrail.markdown import parse_sections, split_row


def test_split_row_honours_escaped_pipes():
    assert split_row("| a | b \\| c | d |") == ["a", "b | c", "d"]


def test_split_row_rejects_non_table_lines():
    assert split_row("plain text") is None


def test_tables_inside_fences_are_ignored():
    text = "## E01 — X\n\n```\n| ✓ | ID |\n|---|---|\n| ⬜ | T001 |\n```\n"
    sections = parse_sections(text)
    assert sections[-1].tables == []


def test_table_without_separator_is_malformed():
    sections = parse_sections("## E01 — X\n| ✓ | ID |\n| ⬜ | T001 |\n")
    assert sections[-1].malformed_tables == [2]
