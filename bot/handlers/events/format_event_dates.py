import datetime

MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

def format_event_dates(start_date, end_date):
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    today = datetime.date.today()
    if start_date == end_date:
        if start_date.year == today.year:
            return f"{start_date.day} {MONTHS_RU[start_date.month]}"
        else:
            return f"{start_date.day} {MONTHS_RU[start_date.month]} {start_date.year}"
    if start_date.year == end_date.year == today.year:
        if start_date.month == end_date.month:
            return f"{start_date.day}–{end_date.day} {MONTHS_RU[start_date.month]}"
        else:
            return f"{start_date.day} {MONTHS_RU[start_date.month]} – {end_date.day} {MONTHS_RU[end_date.month]}"
    else:
        left = f"{start_date.day} {MONTHS_RU[start_date.month]}"
        if start_date.year != end_date.year:
            left += f" {start_date.year}"
        right = f"{end_date.day} {MONTHS_RU[end_date.month]} {end_date.year}"
        return f"{left} – {right}"
