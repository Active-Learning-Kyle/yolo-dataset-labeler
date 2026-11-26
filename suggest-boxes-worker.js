import { env, pipeline, RawImage } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1/dist/transformers.min.js';

const model = 'Xenova/owlvit-base-patch32';
const revision = 'b75f4e52949639c3bb0b96546ea4149482f6e7ef';
env.allowLocalModels = false;
env.backends.onnx.wasm.numThreads = 1;

let detector;

async function loadDetector() {
  if (detector) return detector;
  detector = await pipeline('zero-shot-object-detection', model, {
    revision,
    dtype: 'q8',
    device: 'wasm',
    progress_callback: event => {
      if (event.status === 'progress' && event.file.endsWith('.onnx') && Number.isFinite(event.progress)) {
        postMessage({ type: 'download', percent: Math.round(event.progress) });
      }
    },
  });
  return detector;
}

function overlap(a, b) {
  const width = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x));
  const height = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
  const shared = width * height;
  return shared / (a.w * a.h + b.w * b.h - shared);
}

function suggestions(detections, prompts, width, height) {
  const clip = (value, limit) => Math.max(0, Math.min(limit, value * limit));
  const boxes = [];
  for (const { label, score, box } of detections) {
    const classId = prompts.indexOf(label);
    if (classId < 0 || !Number.isFinite(score)) continue;
    const x = clip(box.xmin, width);
    const y = clip(box.ymin, height);
    const w = clip(box.xmax, width) - x;
    const h = clip(box.ymax, height) - y;
    if (!Number.isFinite(w) || !Number.isFinite(h) || w < 3 || h < 3) continue;
    const next = { classId, score, x, y, w, h };
    if (boxes.some(existing => overlap(existing, next) >= (existing.classId === classId ? 0.5 : 0.8))) continue;
    boxes.push(next);
    if (boxes.length === 25) break;
  }
  return boxes;
}

self.onmessage = async ({ data: { photo, classes, width, height } }) => {
  try {
    const findObjects = await loadDetector();
    postMessage({ type: 'analyzing' });
    const bitmap = await createImageBitmap(photo);
    let image;
    try {
      const scale = Math.min(1, 960 / Math.max(bitmap.width, bitmap.height));
      const canvas = new OffscreenCanvas(Math.round(bitmap.width * scale), Math.round(bitmap.height * scale));
      canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      image = RawImage.fromCanvas(canvas);
    } finally {
      bitmap.close();
    }
    const prompts = classes.map(name => 'a close-up photo of a ' + name.toLowerCase().replace(/[_-]/g, ' ').replace(/\s+/g, ' ').trim());
    if (new Set(prompts).size !== prompts.length) {
      postMessage({ type: 'error', message: 'Use more distinct class names before requesting suggestions.' });
      return;
    }
    const detections = await findObjects(image, prompts, { threshold: 0.1, percentage: true, top_k: 100 });
    postMessage({ type: 'done', boxes: suggestions(detections, prompts, width, height) });
  } catch (error) {
    console.error('Suggest boxes:', error);
    postMessage({ type: 'error', message: 'Suggestions could not run. Try again or keep labeling by hand.' });
  }
};
