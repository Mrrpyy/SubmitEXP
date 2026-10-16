// background worker, chrome starts this when the extension loads
// screenshot capture and backend calls will add listeners here later
chrome.runtime.onInstalled.addListener((details) => {
  console.log('SubmitEXP installed:', details.reason);
});

// the popup sends a PING message to check this worker is running
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'PING') {
    sendResponse({ ok: true, time: Date.now() });
  }
  return false;
});