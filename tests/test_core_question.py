"""Schema-3.0 question model: validation, conversion and round-tripping."""

from __future__ import annotations

import pytest

from npee_math_papers.core.errors import ValidationError
from npee_math_papers.core.question import (
    CHOICE_LABELS,
    Question,
    convert_v2_question,
    has_schema_v3,
    validate_questions,
)

from tests.conftest import make_choice_question, make_fill_question


def test_valid_choice_question_round_trips() -> None:
    raw = make_choice_question(3)
    [question] = validate_questions([raw], "q")
    assert question.number == 3
    assert question.section == "choice"
    assert [choice.label for choice in question.choices] == list(CHOICE_LABELS)
    # ``to_dict`` drops empty ``figures`` arrays (the storage normalization), so
    # a second validation of the emitted dict must produce an identical dict.
    assert validate_questions([question.to_dict()], "q")[0].to_dict() == question.to_dict()


def test_fill_question_has_no_choices() -> None:
    [question] = validate_questions([make_fill_question()], "q")
    assert question.section == "fill"
    assert question.choices == ()


def test_questions_are_sorted_by_number() -> None:
    questions = validate_questions([make_fill_question(11), make_choice_question(1)], "q")
    assert [item.number for item in questions] == [1, 11]


def test_duplicate_numbers_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_questions([make_choice_question(1), make_choice_question(1)], "q")


def test_choice_requires_exactly_four_options() -> None:
    raw = make_choice_question(1)
    raw["choices"] = raw["choices"][:3]
    with pytest.raises(ValidationError):
        validate_questions([raw], "q")


def test_choice_labels_must_be_in_order() -> None:
    raw = make_choice_question(1)
    raw["choices"][0], raw["choices"][1] = raw["choices"][1], raw["choices"][0]
    with pytest.raises(ValidationError):
        validate_questions([raw], "q")


def test_non_choice_must_not_carry_choices() -> None:
    raw = make_fill_question()
    raw["choices"] = make_choice_question(1)["choices"]
    with pytest.raises(ValidationError):
        validate_questions([raw], "q")


def test_empty_stem_rejected() -> None:
    raw = make_fill_question()
    raw["stem"] = {"text": "  ", "figures": []}
    with pytest.raises(ValidationError):
        validate_questions([raw], "q")


def test_block_math_rejected() -> None:
    raw = make_fill_question()
    raw["stem"]["text"] = "求 $$x$$ 的值。"
    with pytest.raises(ValidationError):
        validate_questions([raw], "q")


def test_a_mis_sized_fraction_still_ingests() -> None:
    """Legacy records must stay loadable.

    The store re-validates on read, so a hard rejection here would make 233
    existing papers unreadable. The size mismatch is normalised at render time and
    reported by the audit instead.
    """

    raw = make_fill_question()
    raw["stem"]["text"] = r"$\frac{1}{2}$"
    [question] = validate_questions([raw], "q")
    assert question.stem.text == r"$\frac{1}{2}$"


def test_unknown_field_rejected() -> None:
    raw = make_choice_question(1)
    raw["extra"] = 1
    with pytest.raises(ValidationError):
        validate_questions([raw], "q")


def test_has_schema_v3_detects_block_shape() -> None:
    assert has_schema_v3(make_choice_question(1))
    assert not has_schema_v3({"number": 1, "section": "fill", "points": 5, "latex": "$x$"})


def test_convert_v2_lifts_stem_and_subparts() -> None:
    converted = convert_v2_question(
        {
            "number": 19,
            "section": "solution",
            "points": 12,
            "latex": "证明 $x>0$。",
            "subparts": [{"latex": "（I）…"}, {"latex": "（II）…"}],
        }
    )
    assert converted["stem"]["text"] == "证明 $x>0$。"
    assert [part["text"] for part in converted["subparts"]] == ["（I）…", "（II）…"]


def test_convert_v2_lifts_graphic_choice_into_figure() -> None:
    converted = convert_v2_question(
        {
            "number": 1,
            "section": "choice",
            "points": 5,
            "latex": "选出正确图形：",
            "choices": [
                "$\\begin{tikzpicture}\\draw (0,0)--(1,1);\\end{tikzpicture}$",
                "文本选项",
                "另一个选项",
                "第四个选项",
            ],
        }
    )
    first = converted["choices"][0]
    assert first["text"] == ""
    assert first["figures"][0]["kind"] == "tikz"


def test_question_summary_counts_figures() -> None:
    question = Question.from_dict(make_choice_question(1), "q")
    summary = question.to_summary()
    assert summary["number"] == 1
    assert summary["figure_count"] == 0
    assert summary["has_choices"] is True
