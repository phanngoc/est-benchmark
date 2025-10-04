"""
Sun Asterisk Excel Estimation Exporter
======================================

Generates Excel estimation sheets following Sun Asterisk standard format
with bilingual JP/EN headers, role-specific effort breakdown, and formulas.

Author: AI Assistant
Date: 2025-10-04
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

# Import logging
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class SunAsteriskExcelExporter:
    """
    Excel exporter following Sun Asterisk estimation sheet standard.

    Schema: 20 columns with bilingual headers, role × task type breakdown,
    MD per MM configuration, and formula-based calculations.
    """

    # Column definitions (order matters!)
    COLUMNS = [
        "No",                           # 1
        "カテゴリ",                       # 2
        "Sub.No",                       # 3
        "画面・機能 Screen・Feature",     # 4
        "参照資料 Reference Document",   # 5
        "Task",                         # 6
        "Premise",                      # 7
        "Task(JP)",                     # 8
        "想定／前提",                     # 9
        "備考 Remark",                   # 10
        "Backend - Implement",          # 11
        "Backend - FixBug",             # 12
        "Backend - Unit Test",          # 13
        "Frontend - Implement",         # 14
        "Frontend - FixBug",            # 15
        "Frontend - Unit Test",         # 16
        "Responsive - Implement",       # 17
        "QA - Implement",               # 18
        "Total (MD)",                   # 19
        "Note"                          # 20
    ]

    # Column widths
    COLUMN_WIDTHS = {
        "No": 5,
        "カテゴリ": 12,
        "Sub.No": 8,
        "画面・機能 Screen・Feature": 28,
        "参照資料 Reference Document": 28,
        "Task": 16,
        "Premise": 16,
        "Task(JP)": 22,
        "想定／前提": 18,
        "備考 Remark": 22,
        "Backend - Implement": 12,
        "Backend - FixBug": 12,
        "Backend - Unit Test": 12,
        "Frontend - Implement": 12,
        "Frontend - FixBug": 12,
        "Frontend - Unit Test": 12,
        "Responsive - Implement": 12,
        "QA - Implement": 12,
        "Total (MD)": 12,
        "Note": 20
    }

    # Effort column indices (1-based for Excel)
    EFFORT_COLUMNS = [11, 12, 13, 14, 15, 16, 17, 18]  # Backend-Implement through QA-Implement
    TOTAL_COLUMN = 19  # Total (MD)

    def __init__(
        self,
        no: str = "001",
        version: str = "1.0",
        issue_date: Optional[str] = None,
        md_per_mm: int = 20
    ):
        """
        Initialize Sun Asterisk Excel Exporter.

        Args:
            no: Document number (e.g., "001")
            version: Document version (e.g., "1.0")
            issue_date: Issue date (defaults to today)
            md_per_mm: Man-days per man-month (default: 20)
        """
        self.no = no
        self.version = version
        self.issue_date = issue_date or datetime.now().strftime("%Y-%m-%d")
        self.md_per_mm = md_per_mm

    def export(
        self,
        data: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> str:
        """
        Export estimation data to Sun Asterisk Excel format.

        Args:
            data: List of task dictionaries with estimation data
            filename: Output filename (auto-generated if None)

        Returns:
            str: Path to exported Excel file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sunasterisk_estimation_{timestamp}.xlsx"

        filepath = os.path.join(os.getcwd(), filename)

        try:
            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Estimation"

            # Build header
            self._build_header(ws)

            # Build data table
            self._build_data_table(ws, data)

            # Add Total (MM) row
            self._add_total_mm_row(ws, len(data))

            # Apply formatting
            self._apply_formatting(ws, len(data))

            # Freeze panes (header + subheader)
            ws.freeze_panes = "A9"  # Freeze everything above row 9

            # Save workbook
            wb.save(filepath)

            logger.info(f"✅ Sun Asterisk Excel export completed: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"❌ Error exporting Sun Asterisk Excel: {e}")
            raise

    def _build_header(self, ws):
        """Build header section with company info and metadata."""
        # A1:F1 - "ESTIMATION"
        ws.merge_cells("A1:F1")
        ws["A1"] = "ESTIMATION"
        ws["A1"].font = Font(size=16, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

        # H1:J1 - "No: {no}"
        ws.merge_cells("H1:J1")
        ws["H1"] = f"No: {self.no}"
        ws["H1"].alignment = Alignment(horizontal="left", vertical="center")

        # H2:J2 - "Version: {version}"
        ws.merge_cells("H2:J2")
        ws["H2"] = f"Version: {self.version}"
        ws["H2"].alignment = Alignment(horizontal="left", vertical="center")

        # H3:J3 - "Issue Date: {issue_date}"
        ws.merge_cells("H3:J3")
        ws["H3"] = f"Issue Date: {self.issue_date}"
        ws["H3"].alignment = Alignment(horizontal="left", vertical="center")

        # A2:F2 - "SUN ASTERISK VIETNAM CO., LTD"
        ws.merge_cells("A2:F2")
        ws["A2"] = "SUN ASTERISK VIETNAM CO., LTD"
        ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

        # A3:F3 - "ISO/IEC 27001:2013 & ISO 9001:2015"
        ws.merge_cells("A3:F3")
        ws["A3"] = "ISO/IEC 27001:2013 & ISO 9001:2015"
        ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

        # L1 - "MD per MM"
        ws["L1"] = "MD per MM"
        ws["L1"].font = Font(bold=True)
        ws["L1"].alignment = Alignment(horizontal="right", vertical="center")

        # M1 - {md_per_mm}
        ws["M1"] = self.md_per_mm
        ws["M1"].font = Font(bold=True)
        ws["M1"].alignment = Alignment(horizontal="center", vertical="center")

        # Row 5: "Effort（Man-days）" header spanning effort columns
        effort_start = get_column_letter(self.EFFORT_COLUMNS[0])
        effort_end = get_column_letter(self.EFFORT_COLUMNS[-1])
        ws.merge_cells(f"{effort_start}5:{effort_end}5")
        ws[f"{effort_start}5"] = "Effort（Man-days）"
        ws[f"{effort_start}5"].font = Font(bold=True)
        ws[f"{effort_start}5"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"{effort_start}5"].fill = PatternFill(start_color="B4C7E7", end_color="B4C7E7", fill_type="solid")

        # Row 6: Main column headers
        for idx, col_name in enumerate(self.COLUMNS, start=1):
            cell = ws.cell(row=6, column=idx)
            cell.value = col_name
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

            # Set column width
            ws.column_dimensions[get_column_letter(idx)].width = self.COLUMN_WIDTHS.get(col_name, 12)

    def _build_data_table(self, ws, data: List[Dict[str, Any]]):
        """Build data table with task rows."""
        start_row = 7  # Data starts at row 7

        for idx, task in enumerate(data, start=1):
            row = start_row + idx - 1

            # No (auto-increment)
            ws.cell(row=row, column=1).value = idx
            ws.cell(row=row, column=1).alignment = Alignment(horizontal="center", vertical="center")

            # カテゴリ
            ws.cell(row=row, column=2).value = task.get("category", "")
            ws.cell(row=row, column=2).alignment = Alignment(horizontal="left", vertical="center")

            # Sub.No
            ws.cell(row=row, column=3).value = task.get("sub_no", "")
            ws.cell(row=row, column=3).alignment = Alignment(horizontal="center", vertical="center")

            # 画面・機能 Screen・Feature
            ws.cell(row=row, column=4).value = task.get("feature", "")
            ws.cell(row=row, column=4).alignment = Alignment(horizontal="left", vertical="center")

            # 参照資料 Reference Document
            ws.cell(row=row, column=5).value = task.get("reference", "")
            ws.cell(row=row, column=5).alignment = Alignment(horizontal="left", vertical="center")

            # Task
            ws.cell(row=row, column=6).value = task.get("task", "")
            ws.cell(row=row, column=6).alignment = Alignment(horizontal="left", vertical="center")

            # Premise
            ws.cell(row=row, column=7).value = task.get("premise", "")
            ws.cell(row=row, column=7).alignment = Alignment(horizontal="left", vertical="center")

            # Task(JP)
            ws.cell(row=row, column=8).value = task.get("task_jp", "")
            ws.cell(row=row, column=8).alignment = Alignment(horizontal="left", vertical="center")

            # 想定／前提
            ws.cell(row=row, column=9).value = task.get("assumption_jp", "")
            ws.cell(row=row, column=9).alignment = Alignment(horizontal="left", vertical="center")

            # 備考 Remark
            ws.cell(row=row, column=10).value = task.get("remark", "")
            ws.cell(row=row, column=10).alignment = Alignment(horizontal="left", vertical="center")

            # Effort columns
            backend_data = task.get("backend", {})
            frontend_data = task.get("frontend", {})
            responsive_data = task.get("responsive", {})
            qa_data = task.get("qa", {})

            # Backend - Implement
            ws.cell(row=row, column=11).value = backend_data.get("implement", 0) or None
            ws.cell(row=row, column=11).alignment = Alignment(horizontal="center", vertical="center")

            # Backend - FixBug
            ws.cell(row=row, column=12).value = backend_data.get("fixbug", 0) or None
            ws.cell(row=row, column=12).alignment = Alignment(horizontal="center", vertical="center")

            # Backend - Unit Test
            ws.cell(row=row, column=13).value = backend_data.get("unittest", 0) or None
            ws.cell(row=row, column=13).alignment = Alignment(horizontal="center", vertical="center")

            # Frontend - Implement
            ws.cell(row=row, column=14).value = frontend_data.get("implement", 0) or None
            ws.cell(row=row, column=14).alignment = Alignment(horizontal="center", vertical="center")

            # Frontend - FixBug
            ws.cell(row=row, column=15).value = frontend_data.get("fixbug", 0) or None
            ws.cell(row=row, column=15).alignment = Alignment(horizontal="center", vertical="center")

            # Frontend - Unit Test
            ws.cell(row=row, column=16).value = frontend_data.get("unittest", 0) or None
            ws.cell(row=row, column=16).alignment = Alignment(horizontal="center", vertical="center")

            # Responsive - Implement
            ws.cell(row=row, column=17).value = responsive_data.get("implement", 0) or None
            ws.cell(row=row, column=17).alignment = Alignment(horizontal="center", vertical="center")

            # QA - Implement
            ws.cell(row=row, column=18).value = qa_data.get("implement", 0) or None
            ws.cell(row=row, column=18).alignment = Alignment(horizontal="center", vertical="center")

            # Total (MD) - Formula: SUM of effort columns
            effort_start = get_column_letter(self.EFFORT_COLUMNS[0])
            effort_end = get_column_letter(self.EFFORT_COLUMNS[-1])
            total_formula = f"=SUM({effort_start}{row}:{effort_end}{row})"
            ws.cell(row=row, column=19).value = total_formula
            ws.cell(row=row, column=19).alignment = Alignment(horizontal="center", vertical="center")

            # Note
            ws.cell(row=row, column=20).value = task.get("note", "")
            ws.cell(row=row, column=20).alignment = Alignment(horizontal="left", vertical="center")

    def _add_total_mm_row(self, ws, data_count: int):
        """Add Total (MM) summary row with formulas."""
        total_row = 7 + data_count  # Row after last data row

        # Merge cells for "Total (MM)" label
        ws.merge_cells(f"A{total_row}:J{total_row}")
        ws[f"A{total_row}"] = "Total (MM)"
        ws[f"A{total_row}"].font = Font(bold=True)
        ws[f"A{total_row}"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"A{total_row}"].fill = PatternFill(start_color="FFD9B3", end_color="FFD9B3", fill_type="solid")

        # Add MM formulas for each effort column and Total (MD)
        for col_idx in self.EFFORT_COLUMNS + [self.TOTAL_COLUMN]:
            col_letter = get_column_letter(col_idx)

            # Formula: SUM(column) / $M$1
            mm_formula = f"=SUM({col_letter}7:{col_letter}{total_row-1})/$M$1"

            cell = ws.cell(row=total_row, column=col_idx)
            cell.value = mm_formula
            cell.number_format = "0.00"
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill = PatternFill(start_color="FFD9B3", end_color="FFD9B3", fill_type="solid")

    def _apply_formatting(self, ws, data_count: int):
        """Apply borders and final formatting."""
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )

        # Apply borders to header (row 6)
        for col_idx in range(1, len(self.COLUMNS) + 1):
            ws.cell(row=6, column=col_idx).border = thin_border

        # Apply borders to data rows (row 7 to total_row)
        total_row = 7 + data_count
        for row in range(7, total_row + 1):
            for col_idx in range(1, len(self.COLUMNS) + 1):
                ws.cell(row=row, column=col_idx).border = thin_border


def export_sunasterisk_excel(
    data: List[Dict[str, Any]],
    filename: Optional[str] = None,
    no: str = "001",
    version: str = "1.0",
    issue_date: Optional[str] = None,
    md_per_mm: int = 20
) -> str:
    """
    Convenience function to export Sun Asterisk Excel estimation sheet.

    Args:
        data: List of task dictionaries
        filename: Output filename (auto-generated if None)
        no: Document number
        version: Document version
        issue_date: Issue date (defaults to today)
        md_per_mm: Man-days per man-month

    Returns:
        str: Path to exported Excel file
    """
    exporter = SunAsteriskExcelExporter(
        no=no,
        version=version,
        issue_date=issue_date,
        md_per_mm=md_per_mm
    )
    return exporter.export(data, filename)
