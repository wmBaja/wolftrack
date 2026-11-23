from fastapi import APIRouter
from .common import *
from .common import _build_export_filename, _build_sheet_name, _collect_export_rows

router = APIRouter()

@router.get("/api/export_csv")
async def export_csv(request: Request, timezone_name: str = "America/New_York"):
    rows = await _collect_export_rows(request, timezone_name)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["timestamp", "signal_name", "value", "unit"])
    for row in rows:
        writer.writerow([
            row["timestamp"],
            row["signal_name"],
            row["value"],
            row["unit"],
        ])

    csv_content = "\ufeff" + buffer.getvalue()
    headers = {
        "Content-Disposition": f'attachment; filename="{_build_export_filename()}"',
    }
    return StreamingResponse(
        iter([csv_content.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )

@router.get("/api/export_xlsx")
async def export_xlsx(request: Request, timezone_name: str = "America/New_York"):
    rows = await _collect_export_rows(request, timezone_name)
    grouped_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped_rows[str(row["signal_name"])].append(row)

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)
    header_font = Font(bold=True)
    used_sheet_names: set[str] = set()

    for signal_name, signal_rows in grouped_rows.items():
        sheet = workbook.create_sheet(title=_build_sheet_name(signal_name, used_sheet_names))
        sheet.append(["timestamp", "value", "unit"])
        for cell in sheet[1]:
            cell.font = header_font

        for row in signal_rows:
            sheet.append([
                row["timestamp"],
                row["value"],
                row["unit"],
            ])

        for column_cells in sheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = max_length + 2

    if not workbook.sheetnames:
        sheet = workbook.create_sheet(title="Signals")
        sheet.append(["timestamp", "value", "unit"])
        for cell in sheet[1]:
            cell.font = header_font

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    headers = {
        "Content-Disposition": f'attachment; filename="{_build_export_filename().replace(".csv", ".xlsx")}"',
    }
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
