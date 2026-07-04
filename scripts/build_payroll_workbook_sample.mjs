import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.resolve("outputs", "arc_payroll_artifacts");
await fs.mkdir(outputDir, { recursive: true });

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Payroll Summary");
const timesheets = workbook.worksheets.add("Timesheets");
const adjustments = workbook.worksheets.add("Adjustments");
const exceptions = workbook.worksheets.add("Exceptions");

const palette = {
  ink: "#17221B",
  green: "#2F5D3A",
  greenSoft: "#E8F1EA",
  gold: "#D9A441",
  goldSoft: "#FBF4E3",
  line: "#D8E0DA",
  paper: "#FFFFFF",
  muted: "#66736A",
  danger: "#9B2C2C",
  dangerSoft: "#FCE8E8",
};

function titleBand(sheet, title, subtitle, endColumn) {
  sheet.getRange(`A1:${endColumn}1`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A2:${endColumn}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A1:${endColumn}1`).format = {
    fill: palette.green,
    font: { bold: true, color: "#FFFFFF", size: 20 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${endColumn}2`).format = {
    fill: palette.greenSoft,
    font: { color: palette.green, italic: true, size: 10 },
    verticalAlignment: "center",
  };
  sheet.getRange("A1").format.rowHeight = 36;
  sheet.getRange("A2").format.rowHeight = 26;
  sheet.showGridLines = false;
}

function styleHeader(range) {
  range.format = {
    fill: palette.ink,
    font: { bold: true, color: "#FFFFFF", size: 10 },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: palette.ink },
  };
  range.format.rowHeight = 28;
}

function styleBody(range) {
  range.format = {
    font: { color: palette.ink, size: 10 },
    borders: {
      insideHorizontal: { style: "thin", color: palette.line },
      bottom: { style: "thin", color: palette.line },
    },
    verticalAlignment: "center",
  };
}

titleBand(
  summary,
  "Best Buds Payroll Review",
  "SAMPLE • Operator-ready workbook • Period: June 16–30, 2026 • America/New_York",
  "J",
);
summary.getRange("A4:B5").values = [["Review status", "Ready for owner review"], ["Employees", 3]];
summary.getRange("D4:E5").values = [["Recorded hours", null], ["Exceptions", null]];
summary.getRange("E4").formulas = [["=SUM(E9:E11)"]];
summary.getRange("E5").formulas = [["=SUM(J9:J11)"]];
summary.getRange("G4:H5").values = [["Gross estimate", null], ["Net estimate", null]];
summary.getRange("H4").formulas = [["=SUM(G9:G11)"]];
summary.getRange("H5").formulas = [["=SUM(I9:I11)"]];
for (const address of ["A4:B5", "D4:E5", "G4:H5"]) {
  summary.getRange(address).format = {
    fill: palette.greenSoft,
    font: { color: palette.ink, size: 11 },
    borders: { preset: "outside", style: "thin", color: palette.line },
  };
}
summary.getRange("A4:A5").format.font = { bold: true, color: palette.green };
summary.getRange("D4:D5").format.font = { bold: true, color: palette.green };
summary.getRange("G4:G5").format.font = { bold: true, color: palette.green };
summary.getRange("H4:H5").format.numberFormat = "$#,##0.00";
summary.getRange("A7:J7").merge();
summary.getRange("A7").values = [["Employee totals"]];
summary.getRange("A7:J7").format = {
  fill: palette.goldSoft,
  font: { bold: true, color: palette.ink, size: 12 },
};
summary.getRange("A8:J11").values = [
  ["Employee", "Employee ID", "Regular", "Overtime", "Total Hours", "Hourly Rate", "Gross Estimate", "Tax Estimate", "Net Estimate", "Exceptions"],
  ["Avery Collins", "emp_101", null, null, null, 22.5, null, 86.4, null, 0],
  ["Jordan Reed", "emp_104", null, null, null, 19.75, null, 67.68, null, 0],
  ["Morgan Lee", "emp_112", null, null, null, 24.0, null, 36.0, null, 1],
];
summary.getRange("C9").formulas = [['=SUMIF(Timesheets!$B$5:$B$200,B9,Timesheets!$G$5:$G$200)']];
summary.getRange("C9:C11").fillDown();
summary.getRange("D9").formulas = [['=SUMIF(Timesheets!$B$5:$B$200,B9,Timesheets!$H$5:$H$200)']];
summary.getRange("D9:D11").fillDown();
summary.getRange("E9").formulas = [["=C9+D9"]];
summary.getRange("E9:E11").fillDown();
summary.getRange("G9").formulas = [["=E9*F9"]];
summary.getRange("G9:G11").fillDown();
summary.getRange("I9").formulas = [["=MAX(G9-H9,0)"]];
summary.getRange("I9:I11").fillDown();
styleHeader(summary.getRange("A8:J8"));
styleBody(summary.getRange("A9:J11"));
summary.getRange("C9:G11").format.numberFormat = "0.00";
summary.getRange("F9:I11").format.numberFormat = "$#,##0.00";
summary.getRange("A13:J13").merge();
summary.getRange("A13").values = [["Estimates only. Review exceptions and approved adjustments before payroll submission."]];
summary.getRange("A13:J13").format = {
  fill: palette.goldSoft,
  font: { bold: true, color: "#6B4D12", size: 10 },
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: "#E7C875" },
};
summary.getRange("A13").format.rowHeight = 38;
summary.freezePanes.freezeRows(8);
summary.getRange("A:J").format.columnWidth = 14;
summary.getRange("A:A").format.columnWidth = 22;
summary.getRange("B:B").format.columnWidth = 14;
summary.getRange("J:J").format.columnWidth = 14;

titleBand(
  timesheets,
  "Timesheet Detail",
  "Human-readable session detail used by the Payroll Summary sheet",
  "L",
);
timesheets.getRange("A4:L9").values = [
  ["Work Date", "Employee ID", "Employee", "Clock In", "Clock Out", "Break Minutes", "Regular Hours", "Overtime Hours", "Total Hours", "Hourly Rate", "Gross Estimate", "Notes"],
  ["Jun 16, 2026", "emp_101", "Avery Collins", "Jun 16, 2026 8:55 AM", "Jun 16, 2026 5:20 PM", 30, 7.92, 0, 7.92, 22.5, 178.2, ""],
  ["Jun 17, 2026", "emp_101", "Avery Collins", "Jun 17, 2026 9:02 AM", "Jun 17, 2026 5:05 PM", 30, 7.55, 0, 7.55, 22.5, 169.88, ""],
  ["Jun 16, 2026", "emp_104", "Jordan Reed", "Jun 16, 2026 10:00 AM", "Jun 16, 2026 6:15 PM", 30, 7.75, 0, 7.75, 19.75, 153.06, ""],
  ["Jun 17, 2026", "emp_104", "Jordan Reed", "Jun 17, 2026 10:05 AM", "Jun 17, 2026 6:00 PM", 30, 7.42, 0, 7.42, 19.75, 146.55, "Approved +0.25 hour adjustment included"],
  ["Jun 18, 2026", "emp_112", "Morgan Lee", "Jun 18, 2026 9:10 AM", "OPEN", 0, 6.0, 0, 6.0, 24.0, 144.0, "OPEN SESSION — owner review required"],
];
styleHeader(timesheets.getRange("A4:L4"));
styleBody(timesheets.getRange("A5:L9"));
timesheets.getRange("F5:I9").format.numberFormat = "0.00";
timesheets.getRange("J5:K9").format.numberFormat = "$#,##0.00";
timesheets.getRange("A5:L9").format.rowHeight = 24;
timesheets.getRange("L9").format = {
  fill: palette.dangerSoft,
  font: { bold: true, color: palette.danger },
};
timesheets.tables.add("A4:L9", true, "PayrollTimesheets");
timesheets.freezePanes.freezeRows(4);
timesheets.getRange("A:L").format.columnWidth = 14;
timesheets.getRange("C:C").format.columnWidth = 21;
timesheets.getRange("D:E").format.columnWidth = 22;
timesheets.getRange("L:L").format.columnWidth = 38;

titleBand(
  adjustments,
  "Approved Adjustments",
  "Owner-entered changes are separated from recorded punch events",
  "F",
);
adjustments.getRange("A4:F5").values = [
  ["Work Date", "Employee ID", "Employee", "Hours", "Reason", "Recorded At"],
  ["Jun 17, 2026", "emp_104", "Jordan Reed", 0.25, "Approved missed setup time", "Jun 18, 2026 10:20 AM"],
];
styleHeader(adjustments.getRange("A4:F4"));
styleBody(adjustments.getRange("A5:F5"));
adjustments.getRange("D5:D5").format.numberFormat = "0.00";
adjustments.tables.add("A4:F5", true, "PayrollAdjustments");
adjustments.freezePanes.freezeRows(4);
adjustments.getRange("A:F").format.columnWidth = 18;
adjustments.getRange("C:C").format.columnWidth = 22;
adjustments.getRange("E:E").format.columnWidth = 36;
adjustments.getRange("F:F").format.columnWidth = 23;

titleBand(
  exceptions,
  "Review Exceptions",
  "Resolve or acknowledge these items before using the workbook for payroll",
  "F",
);
exceptions.getRange("A4:F5").values = [
  ["Priority", "Employee", "Employee ID", "Exception", "Recommended Action", "Status"],
  ["High", "Morgan Lee", "emp_112", "Open clock session", "Confirm the clock-out time in Operator Control.", "Needs Review"],
];
styleHeader(exceptions.getRange("A4:F4"));
styleBody(exceptions.getRange("A5:F5"));
exceptions.getRange("A5:F5").format.fill = palette.dangerSoft;
exceptions.getRange("A5:A5").format.font = { bold: true, color: palette.danger };
exceptions.getRange("F5:F5").format.font = { bold: true, color: palette.danger };
exceptions.tables.add("A4:F5", true, "PayrollExceptions");
exceptions.freezePanes.freezeRows(4);
exceptions.getRange("A:F").format.columnWidth = 18;
exceptions.getRange("B:B").format.columnWidth = 22;
exceptions.getRange("D:E").format.columnWidth = 38;

const workbookPath = path.join(outputDir, "bbtc_payroll_workbook_sample_v0.9.0.xlsx");
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(workbookPath);

for (const sheetName of ["Payroll Summary", "Timesheets", "Adjustments", "Exceptions"]) {
  const rendered = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  const fileName = `${sheetName.toLowerCase().replaceAll(" ", "_")}.png`;
  await fs.writeFile(path.join(outputDir, fileName), new Uint8Array(await rendered.arrayBuffer()));
}

const inspection = await workbook.inspect({
  kind: "workbook,sheet,table,formula",
  maxChars: 10000,
  tableMaxRows: 8,
  tableMaxCols: 12,
  options: { maxResults: 100 },
});
await fs.writeFile(
  path.join(outputDir, "workbook_inspection.json"),
  JSON.stringify(inspection, null, 2),
  "utf8",
);

console.log(workbookPath);
