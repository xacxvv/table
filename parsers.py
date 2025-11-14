"""Timetable parsing helpers for EduPage HTML exports."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag


DATA_DIR = Path(__file__).resolve().parent / "data"


DAY_ORDER = [
    "Даваа",
    "Мягмар",
    "Лхагва",
    "Пүрэв",
    "Баасан",
    "Бямба",
    "Ням",
]

DAY_ALIASES = {
    "даваа": "Даваа",
    "мон": "Даваа",
    "monday": "Даваа",
    "мягмар": "Мягмар",
    "tue": "Мягмар",
    "monday": "Даваа",
    "tuesday": "Мягмар",
    "лхагва": "Лхагва",
    "wed": "Лхагва",
    "wednesday": "Лхагва",
    "пүрэв": "Пүрэв",
    "thu": "Пүрэв",
    "thur": "Пүрэв",
    "thursday": "Пүрэв",
    "баасан": "Баасан",
    "fri": "Баасан",
    "friday": "Баасан",
    "бямба": "Бямба",
    "sat": "Бямба",
    "saturday": "Бямба",
    "ням": "Ням",
    "sun": "Ням",
    "sunday": "Ням",
}


@dataclass
class CellInfo:
    subject: str
    second_line: str
    third_line: str
    extra_lines: List[str]

    @property
    def teacher(self) -> str:
        return self.second_line

    @property
    def room(self) -> str:
        return self.third_line

    @property
    def class_name(self) -> str:
        return self.second_line


def _load_html(filename: str) -> BeautifulSoup:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Expected data file at {path}")
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _normalize_day_label(label: str) -> Optional[str]:
    cleaned = _normalize_text(label).lower()
    if not cleaned:
        return None
    return DAY_ALIASES.get(cleaned, label.strip())


def _is_period_label(text: str) -> bool:
    return bool(re.search(r"\d", text))


def _expand_table(table: Tag) -> List[List[Tag]]:
    grid: List[List[Tag]] = []
    span_map: Dict[int, Tuple[Tag, int]] = {}
    for tr in table.find_all("tr"):
        row: List[Tag] = []
        col_idx = 0
        while True:
            span_entry = span_map.get(col_idx)
            if span_entry:
                cell, remaining = span_entry
                row.append(cell)
                remaining -= 1
                if remaining == 0:
                    del span_map[col_idx]
                else:
                    span_map[col_idx] = (cell, remaining)
                col_idx += 1
                continue
            break
        for cell in tr.find_all(["td", "th"]):
            while True:
                span_entry = span_map.get(col_idx)
                if span_entry:
                    span_cell, remaining = span_entry
                    row.append(span_cell)
                    remaining -= 1
                    if remaining == 0:
                        del span_map[col_idx]
                    else:
                        span_map[col_idx] = (span_cell, remaining)
                    col_idx += 1
                    continue
                break
            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))
            for _ in range(colspan):
                row.append(cell)
                if rowspan > 1:
                    span_map[col_idx] = (cell, rowspan - 1)
                col_idx += 1
        while True:
            span_entry = span_map.get(col_idx)
            if span_entry:
                span_cell, remaining = span_entry
                row.append(span_cell)
                remaining -= 1
                if remaining == 0:
                    del span_map[col_idx]
                else:
                    span_map[col_idx] = (span_cell, remaining)
                col_idx += 1
                continue
            break
        grid.append(row)
    return grid


def _parse_table_structure(table: Tag) -> Tuple[List[str], List[str], List[List[Tag]]]:
    grid = _expand_table(table)
    if not grid:
        return [], [], []
    header_cells = grid[0]
    body_rows = grid[1:]
    raw_days = [_normalize_text(c.get_text(" ")) for c in header_cells[1:]]
    periods: List[str] = []
    matrix_cells: List[List[Tag]] = []
    for row in body_rows:
        if not row:
            continue
        period_label = _normalize_text(row[0].get_text(" "))
        if period_label:
            digit_match = re.search(r"\d+", period_label)
            if digit_match:
                period_label = digit_match.group()
        if not period_label:
            period_label = str(len(periods) + 1)
        periods.append(period_label)
        matrix_cells.append(row[1:])
    if raw_days and all(_is_period_label(day) for day in raw_days):
        transposed_matrix = list(zip(*matrix_cells))
        new_days = [_normalize_text(period) for period in periods]
        new_periods = raw_days
        matrix_cells = [list(row) for row in transposed_matrix]
        raw_days = new_days
        periods = new_periods
    normalized_days: List[str] = []
    day_indices: List[int] = []
    for idx, label in enumerate(raw_days):
        normalized = _normalize_day_label(label)
        if normalized:
            normalized_days.append(normalized)
            day_indices.append(idx)
    ordered = sorted(
        zip(day_indices, normalized_days),
        key=lambda pair: DAY_ORDER.index(pair[1]) if pair[1] in DAY_ORDER else len(DAY_ORDER) + pair[0],
    )
    if not ordered:
        ordered = list(zip(range(len(raw_days)), raw_days))
    ordered_days = [day for _, day in ordered]
    ordered_matrix: List[List[Tag]] = []
    for row in matrix_cells:
        ordered_row = [row[idx] for idx, _ in ordered if idx < len(row)]
        ordered_matrix.append(ordered_row)
    return ordered_days, periods, ordered_matrix


def _detect_week_from_classes(classes: Iterable[str]) -> Optional[str]:
    for cls in classes:
        lower = cls.lower()
        if "odd" in lower or "week1" in lower or "aweek" in lower:
            return "odd"
        if "even" in lower or "week2" in lower or "bweek" in lower:
            return "even"
    return None


def _parse_entry_lines(lines: List[str]) -> CellInfo:
    subject = lines[0] if lines else ""
    second_line = lines[1] if len(lines) > 1 else ""
    third_line = lines[2] if len(lines) > 2 else ""
    extra = lines[3:] if len(lines) > 3 else []
    return CellInfo(subject=subject, second_line=second_line, third_line=third_line, extra_lines=extra)


def _split_cell_by_week(cell: Tag) -> Dict[str, CellInfo]:
    week_map: Dict[str, CellInfo] = {}
    entry_elements: List[Tuple[Optional[str], Tag]] = []
    direct_children = [child for child in cell.children if isinstance(child, Tag)]
    if direct_children:
        for child in direct_children:
            week = _detect_week_from_classes(child.get("class", []))
            if week is None and child.has_attr("data-week"):
                week_attr = child["data-week"].lower()
                if "odd" in week_attr or week_attr.endswith("1"):
                    week = "odd"
                elif "even" in week_attr or week_attr.endswith("2"):
                    week = "even"
            entry_elements.append((week, child))
    if not entry_elements:
        entry_elements = [(None, cell)]
    odd_entries: List[Tag] = []
    even_entries: List[Tag] = []
    unknown_entries: List[Tag] = []
    for week, element in entry_elements:
        target_list = unknown_entries
        if week == "odd":
            target_list = odd_entries
        elif week == "even":
            target_list = even_entries
        target_list.append(element)
    if not odd_entries and not even_entries and len(unknown_entries) == 2:
        odd_entries.append(unknown_entries[0])
        even_entries.append(unknown_entries[1])
        unknown_entries = []
    if not odd_entries and unknown_entries:
        odd_entries.append(unknown_entries[0])
    if not even_entries and unknown_entries:
        even_entries.append(unknown_entries[-1])
    if odd_entries and not even_entries:
        even_entries = odd_entries
    if even_entries and not odd_entries:
        odd_entries = even_entries
    if odd_entries:
        lines = [_normalize_text(s) for entry in odd_entries for s in entry.stripped_strings]
        week_map["odd"] = _parse_entry_lines(lines)
    if even_entries:
        lines = [_normalize_text(s) for entry in even_entries for s in entry.stripped_strings]
        week_map["even"] = _parse_entry_lines(lines)
    return week_map


def _parse_cell_content(cell: Tag) -> CellInfo:
    lines = [_normalize_text(text) for text in cell.stripped_strings]
    return _parse_entry_lines(lines)


def _extract_tables_after_heading(heading: Tag) -> List[Tag]:
    tables: List[Tag] = []
    current = heading.next_sibling
    while current:
        if isinstance(current, Tag) and current.name in {"h1", "h2", "h3", "h4"}:
            break
        if isinstance(current, Tag) and current.name == "table":
            tables.append(current)
        current = current.next_sibling
    return tables


def _collect_sections(soup: BeautifulSoup) -> Dict[str, List[Tag]]:
    sections: Dict[str, List[Tag]] = {}
    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        title = _normalize_text(heading.get_text(" "))
        if not title:
            continue
        tables = _extract_tables_after_heading(heading)
        if tables:
            sections[title] = tables
    return sections


def _build_week_matrices(
    tables: List[Tag],
    global_days: Optional[List[str]] = None,
) -> Tuple[List[str], List[str], List[List[CellInfo]], List[List[CellInfo]]]:
    days: Optional[List[str]] = None
    periods: Optional[List[str]] = None
    odd_matrix: Optional[List[List[CellInfo]]] = None
    even_matrix: Optional[List[List[CellInfo]]] = None
    if len(tables) >= 2:
        first_days, first_periods, first_cells = _parse_table_structure(tables[0])
        second_days, second_periods, second_cells = _parse_table_structure(tables[1])
        if not global_days:
            days = first_days
        else:
            days = global_days
        periods = first_periods
        odd_matrix = [[_parse_cell_content(cell) for cell in row] for row in first_cells]
        even_matrix = [[_parse_cell_content(cell) for cell in row] for row in second_cells]
        if days != second_days or periods != second_periods:
            days = days or second_days
            periods = periods or second_periods
    elif tables:
        days, periods, cell_grid = _parse_table_structure(tables[0])
        odd_matrix = []
        even_matrix = []
        for row in cell_grid:
            odd_row: List[CellInfo] = []
            even_row: List[CellInfo] = []
            for cell in row:
                week_entries = _split_cell_by_week(cell)
                odd_row.append(week_entries.get("odd", _parse_entry_lines([])))
                even_row.append(week_entries.get("even", week_entries.get("odd", _parse_entry_lines([]))))
            odd_matrix.append(odd_row)
            even_matrix.append(even_row)
    else:
        days = global_days or []
        periods = []
        odd_matrix = []
        even_matrix = []
    return days or [], periods or [], odd_matrix or [], even_matrix or []


def load_classes() -> Dict[str, object]:
    soup = _load_html("Classes.html")
    sections = _collect_sections(soup)
    class_names = sorted(sections)
    school_to_classes: Dict[str, List[str]] = defaultdict(list)
    odd_week: Dict[str, List[List[CellInfo]]] = {}
    even_week: Dict[str, List[List[CellInfo]]] = {}
    days: List[str] = []
    periods: List[str] = []
    for class_name in class_names:
        class_days, class_periods, odd_matrix, even_matrix = _build_week_matrices(sections[class_name], days or None)
        if class_days and not days:
            days = class_days
        if class_periods and not periods:
            periods = class_periods
        odd_week[class_name] = odd_matrix
        even_week[class_name] = even_matrix
        school_code = class_name.split("-", 1)[0]
        school_to_classes[school_code].append(class_name)
    schools = sorted(school_to_classes)
    for school in schools:
        school_to_classes[school].sort()
    return {
        "days": days,
        "periods": periods,
        "odd_week": odd_week,
        "even_week": even_week,
        "class_names": class_names,
        "schools": schools,
        "school_to_classes": dict(school_to_classes),
    }


def load_teachers() -> Dict[str, object]:
    soup = _load_html("Teachers.html")
    sections = _collect_sections(soup)
    teacher_names = sorted(sections)
    odd_week: Dict[str, List[List[CellInfo]]] = {}
    even_week: Dict[str, List[List[CellInfo]]] = {}
    days: List[str] = []
    periods: List[str] = []
    for teacher in teacher_names:
        teacher_days, teacher_periods, odd_matrix, even_matrix = _build_week_matrices(sections[teacher], days or None)
        if teacher_days and not days:
            days = teacher_days
        if teacher_periods and not periods:
            periods = teacher_periods
        odd_week[teacher] = odd_matrix
        even_week[teacher] = even_matrix
    return {
        "days": days,
        "periods": periods,
        "odd_week": odd_week,
        "even_week": even_week,
        "teacher_names": teacher_names,
    }
