from inspect_dataset.scanner import ScannerDef
from inspect_dataset.scanners.answer_distribution import answer_distribution
from inspect_dataset.scanners.answer_length import answer_length
from inspect_dataset.scanners.duplicate_questions import duplicate_questions
from inspect_dataset.scanners.encoding_issues import encoding_issues
from inspect_dataset.scanners.forced_choice_leakage import forced_choice_leakage
from inspect_dataset.scanners.inconsistent_format import inconsistent_format
from inspect_dataset.scanners.binary_question_ratio import binary_question_ratio

BUILTIN_SCANNERS: list[ScannerDef] = [
    answer_length,
    duplicate_questions,
    inconsistent_format,
    answer_distribution,
    forced_choice_leakage,
    encoding_issues,
    binary_question_ratio,
]

BUILTIN_SCANNER_NAMES = {s.name: s for s in BUILTIN_SCANNERS}
