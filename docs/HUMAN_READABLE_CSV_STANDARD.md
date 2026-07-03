# Human-Readable CSV Standard

Employee CSV exports use readable headers, localized date/time text, two-decimal
hours, and currency strings. They preserve the raw JSONL ledger separately.

Required employee headers:

`Employee Name, Employee ID, Date, Clock In, Clock Out, Break Minutes, Total Hours,
Hourly Rate, Gross Pay Estimate, Tax Withheld Estimate, Net Pay Estimate, Notes`

CSV files use UTF-8 with BOM for spreadsheet compatibility. Pay and tax values are
estimates, not payroll or tax compliance outputs.
