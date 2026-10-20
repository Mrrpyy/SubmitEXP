import { createWorker } from 'tesseract.js';

export type OCRResult = {
  text: string;
  confidence?: number;
};

// chrome extensions cant load code from the internet so we load it in. They live in extension/public/tesserasact 
const base = `${window.location.origin}/tesseract`;

let workerPromise: ReturnType<typeof createWorker> | null = null;

function getWorker() {
  if (!workerPromise) {
    workerPromise = createWorker('eng', 1, {
      workerPath: `${base}/worker.min.js`,
      corePath: `${base}/tesseract-core-simd-lstm.wasm.js`,
      langPath: base,
      workerBlobURL: false, 
      cacheMethod: 'none',
    });
  }
  return workerPromise;
}

// Reads text from a screenshot, we decided to not send the ss to the backend. The image never leaves the browser.
export async function recognizeScreenshot(image: Blob | string): Promise<OCRResult> {
  const worker = await getWorker();
  const { data } = await worker.recognize(image);
  return { text: data.text, confidence: data.confidence };
}