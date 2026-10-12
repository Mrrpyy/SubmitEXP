/**
 * Future client-side OCR module.
 *
 * During the OCR backlog task, integrate Tesseract.js here so image data
 * stays in the extension. Return extracted text, not screenshots, to the
 * parsing UI. Do not send raw screenshots to the backend.
 */
export type OCRResult = {
  text: string;
  confidence?: number;
};

// TODO: add actual Tesseract.js implementation once screenshot capture exists.
