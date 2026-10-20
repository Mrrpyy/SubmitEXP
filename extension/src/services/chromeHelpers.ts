// small wrappers around chrome extension apis so the react code stays simple
// in a normal browser tab during npm run dev the chrome apis do not exist,
// so each helper checks first and gives back a safe fallback

export const isExtension = typeof chrome !== 'undefined' && !!chrome.runtime?.id;

// url of the tab the user is looking at, needs the activeTab permission
export async function getActiveTabUrl(): Promise<string | null> {
  if (!isExtension) return null;

  try {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });

    return tab?.url ?? null;
  } catch (error) {
    console.error('Failed to get active tab:', error);
    return null;
  }
}

// true when the url is a canvas page, canvas is hosted on instructure
export function isCanvasUrl(url: string | null): boolean {
  if (!url) return false;

  try {
    const parsed = new URL(url);
    const host = parsed.hostname;

    return parsed.protocol === 'https:' &&
      (host === 'instructure.com' ||
       host.endsWith('.instructure.com'));
  } catch {
    return false;
  }
}

// asks the background worker if it is running
export async function pingBackground(): Promise<boolean> {
  if (!isExtension) return false;
  try {
    const reply = await chrome.runtime.sendMessage({ type: 'PING' });
    return reply?.ok === true;
  } catch {
    return false;
  }
}

 // Saves a small value that survives closing the popup
export async function saveValue(
  key: string,
  value: unknown
): Promise<void> {
  if (!isExtension) return;

  try {
    await chrome.storage.local.set({ [key]: value });
  } catch (error) {
    console.error('Failed to save value:', error);
    throw error;
  }
}

// Loads a value saved with saveValue
export async function loadValue<T>(
  key: string
): Promise<T | undefined> {
  if (!isExtension) return undefined;

  try {
    const result = await chrome.storage.local.get(key);
    return result[key] as T | undefined;
  } catch (error) {
    console.error('Failed to load value:', error);
    throw error;
  }
}
