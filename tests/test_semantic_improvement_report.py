from scripts.generate_semantic_improvement_report import build_report


MODEL_BACKSTORY = (
    "Orin Nightbloom is a Half-Orc Bard whose gifts were sharpened in the halls of Sunstone Mage College.\n\n"
    "The death of Orin Nightbloom's Mother left him with grief and the truth of a curse that only worsens "
    "when ignored.\n\n"
    "Now Orin turns music into defiance, determined to break the curse and stop a younger relative from "
    "repeating the family's worst choice."
)


def test_semantic_report_formats_three_version_score_table():
    report = build_report(rewrite_client=lambda messages: MODEL_BACKSTORY)
    table_lines = [
        line
        for line in report.splitlines()
        if line.startswith("| ")
        and (
            "Candidate" in line
            or "Graph rewrite" in line
            or "Existing generated section" in line
            or "Original section" in line
            or "---" in line
        )
    ]

    assert "Source context similarity compares each candidate" in report
    assert any("Graph rewrite" in line for line in table_lines)
    assert any("Existing generated section" in line for line in table_lines)
    assert any("Original section" in line for line in table_lines)
    assert len({len(line) for line in table_lines}) == 1
