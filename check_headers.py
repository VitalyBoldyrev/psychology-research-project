"""Проверить заголовки листа Main."""
import gspread
from google.oauth2.service_account import Credentials
import config

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(config.CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(config.SPREADSHEET_ID)

main_sheet = spreadsheet.worksheet('Main')
headers = main_sheet.row_values(1)
print(f'Заголовки ({len(headers)} колонок):')
for i, h in enumerate(headers, 1):
    print(f'  {i}. {h}')

print(f'\nВсе данные:')
records = main_sheet.get_all_records()
for r in records:
    print(r)
