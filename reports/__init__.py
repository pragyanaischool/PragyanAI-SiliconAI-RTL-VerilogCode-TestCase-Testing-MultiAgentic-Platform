"""
PragyanAI SiliconAI
Report generation package.
"""

from .report_generator import (
    build_report_data,
    calculate_verification_score,
    generate_report_data,
)

from .markdown_report import (
    create_markdown_report,
    generate_and_save_markdown_report,
)

from .html_report import (
    create_html_report,
    generate_and_save_html_report,
)

__all__ = [
    "build_report_data",
    "calculate_verification_score",
    "generate_report_data",
    "create_markdown_report",
    "generate_and_save_markdown_report",
    "create_html_report",
    "generate_and_save_html_report",
]
