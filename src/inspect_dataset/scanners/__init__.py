from inspect_dataset.scanner import ScannerDef
from inspect_dataset.scanners.answer_distribution import answer_distribution
from inspect_dataset.scanners.answer_length import answer_length
from inspect_dataset.scanners.duplicate_questions import duplicate_questions
from inspect_dataset.scanners.inconsistent_format import inconsistent_format

BUILTIN_SCANNERS: list[ScannerDef] = [
    answer_length,
    duplicate_questions,
    inconsistent_format,
    answer_distribution,
]

BUILTIN_SCANNER_NAMES = {s.name: s for s in BUILTIN_SCANNERS}
