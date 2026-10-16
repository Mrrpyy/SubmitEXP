import { useEffect, useState } from 'react';
import {
  getActiveTabUrl,
  isCanvasUrl,
  isExtension,
  loadValue,
  pingBackground,
  saveValue,
} from './services/chromeHelpers';

export default function App() {
  const [onCanvas, setOnCanvas] = useState(false);
  const [backgroundOk, setBackgroundOk] = useState(false);
  const [timesOpened, setTimesOpened] = useState(0);

  // runs once every time the popup opens
  useEffect(() => {
    async function setup() {
      const url = await getActiveTabUrl();
      setOnCanvas(isCanvasUrl(url));
      setBackgroundOk(await pingBackground());

      // proves storage works, this number keeps going up after the popup closes
      const count = ((await loadValue<number>('timesOpened')) ?? 0) + 1;
      await saveValue('timesOpened', count);
      setTimesOpened(count);
    }
    setup().catch((error) => {
      console.error('Popup setup failed:', error);
    });
  }, []);

  return (
    <main className="shell">
      <div className="tag">SPRINT 1</div>
      <h1>Submit<span>EXP</span></h1>
      <p className="motto">Finish early. Level up.</p>

      <section className="panel">
        <h2>Status</h2>
        <ul className="status">
          <li>Running as extension: {isExtension ? 'yes' : 'no (dev preview)'}</li>
          <li>Background worker: {backgroundOk ? 'running' : 'not found'}</li>
          <li>Current tab is Canvas: {onCanvas ? 'yes' : 'no'}</li>
          <li>Popup opened: {timesOpened} times</li>
        </ul>
        <button disabled={!onCanvas} title={onCanvas ? '' : 'Open a Canvas page first'}>
          Check Submission
        </button>
      </section>

      <small>Screenshot capture comes in a later item.</small>
    </main>
  );
}
