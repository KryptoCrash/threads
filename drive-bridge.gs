// Threads → Google Drive bridge (Google Apps Script)
// Paste this whole file into a new project at script.google.com, then deploy
// as a web app. Full steps in DRIVE-SYNC-SETUP.md.

const TOKEN = '40a276f8d5df63efbcc92a4cd0817279'; // must match the token you paste into the Threads app
const FILE_NAME = 'threads.json';                 // created in your Drive root on first sync
const FOLDER_ID = '';                             // optional: a Drive folder ID to keep the file in instead

function getFile_() {
  const folder = FOLDER_ID ? DriveApp.getFolderById(FOLDER_ID) : DriveApp.getRootFolder();
  const it = folder.getFilesByName(FILE_NAME);
  if (it.hasNext()) return it.next();
  return folder.createFile(FILE_NAME, '{"version":1,"threads":[],"tombstones":{}}', 'application/json');
}

function doGet(e) {
  if (!e || !e.parameter || e.parameter.token !== TOKEN) return json_({ ok: false, error: 'bad token' });
  const raw = getFile_().getBlob().getDataAsString() || '{"version":1,"threads":[],"tombstones":{}}';
  let data;
  try { data = JSON.parse(raw); } catch (err) { data = { version: 1, threads: [], tombstones: {} }; }
  return json_({ ok: true, data: data });
}

function doPost(e) {
  let body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false, error: 'bad json' }); }
  if (body.token !== TOKEN) return json_({ ok: false, error: 'bad token' });
  if (!body.data || !Array.isArray(body.data.threads)) return json_({ ok: false, error: 'not a threads payload' });
  // Serialize writes so two devices can't interleave mid-write.
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try { getFile_().setContent(JSON.stringify(body.data)); }
  finally { lock.releaseLock(); }
  return json_({ ok: true });
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
