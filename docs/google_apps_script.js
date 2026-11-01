/**
 * Google Apps Script Web App for ScholarScope
 * 
 * Paste this into Extensions > Apps Script in your Google Sheet:
 * 1. Set SECRET to match APPS_SCRIPT_SECRET in your .env
 * 2. Click Deploy > New deployment (or Manage deployments)
 * 3. Type: Web app
 * 4. Execute as: "Me"
 * 5. Who has access: "Anyone"   <-- CRITICAL: Must be "Anyone" so Python can POST/GET with secret
 * 6. Copy the Web App URL and set APPS_SCRIPT_URL in your .env
 */

const SCRIPT_SECRET = "DakshGhandat";

function doGet(e) {
  try {
    const secret = e.parameter.secret;
    if (secret !== SCRIPT_SECRET) {
      return ContentService.createTextOutput(JSON.stringify({ ok: false, error: "Unauthorized secret" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    const tabName = e.parameter.tab || "Results";
    const limit = parseInt(e.parameter.limit || "10", 10);
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName(tabName);

    if (!sheet) {
      return ContentService.createTextOutput(JSON.stringify({ ok: true, rows: [] }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    const values = sheet.getDataRange().getValues();
    // Return all data rows (or last `limit` rows)
    const rows = values.length > limit ? values.slice(values.length - limit) : values;

    return ContentService.createTextOutput(JSON.stringify({ ok: true, rows: rows }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  try {
    const contents = e.postData.contents;
    const data = JSON.parse(contents);

    if (data.secret !== SCRIPT_SECRET) {
      return ContentService.createTextOutput(JSON.stringify({ ok: false, error: "Unauthorized secret" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    const tabName = data.tab || "Results";
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(tabName);

    if (!sheet) {
      sheet = ss.insertSheet(tabName);
      // Insert default headers
      if (tabName === "Results" || tabName === "Tests") {
        sheet.appendRow([
          "Timestamp", "Topic", "Prompt Version", "Scope", "Resources",
          "Sources", "Outcomes", "Total", "Verdict", "Validation", "Notes"
        ]);
      }
    }

    sheet.appendRow(data.row);
    const newRowNum = sheet.getLastRow();

    return ContentService.createTextOutput(JSON.stringify({ ok: true, row: newRowNum }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

