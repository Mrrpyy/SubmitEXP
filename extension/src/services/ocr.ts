
import { createWorker } from 'tesseract.js';

export type OCRResult = {
  text: string;
  confidence?: number;
};

// Load Tesseract locally inside the extension.
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
    }).catch((error) => {
      workerPromise = null;
      throw error;
    });
  }
  return workerPromise;
}
// Enlarge screenshots to improve small text reading
async function enhanceScreenshot(
  image: Blob | string
): Promise<string> {
  const objectUrl =
    image instanceof Blob
      ? URL.createObjectURL(image)
      : null;
  const source = objectUrl ?? (image as string);

  try {
    const img = new Image();

    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () =>
        reject(new Error('Failed to load screenshot'));
      img.src = source;
    });

    const scale = Math.max(
      1,
      Math.min(
        2,
        3840 / Math.max(img.naturalWidth, img.naturalHeight)
      )
    );
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('Canvas processing unavailable');
    }
// White background for OCR.
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
// Smoothly enlarge text.
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';

    ctx.drawImage(
      img,
      0,
      0,
      canvas.width,
      canvas.height
    );
    return canvas.toDataURL('image/png');
  } finally {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
    }
  }
}

// Read screenshot locally without uploading it.
export async function recognizeScreenshot(
  image: Blob | string
): Promise<OCRResult> {
  const enhancedImage = await enhanceScreenshot(image);

  const worker = await getWorker();
  const { data } = await worker.recognize(enhancedImage);

  return {
    text: data.text,
    confidence: data.confidence,
  };
}
