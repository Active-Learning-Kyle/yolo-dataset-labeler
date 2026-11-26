import { AutoProcessor, env, RawImage, SamModel } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1/dist/transformers.min.js';

const modelId = 'Xenova/slimsam-77-uniform';
const revision = '5850ab45f587c112167512ffef949107115e26a0';
env.allowLocalModels = false;
env.backends.onnx.wasm.numThreads = 1;

let model;
let processor;
let currentImage;
let embeddings;

async function loadImage(photo) {
  const bitmap = await createImageBitmap(photo);
  try {
    const scale = Math.min(1, 1024 / Math.max(bitmap.width, bitmap.height));
    const canvas = new OffscreenCanvas(
      Math.max(1, Math.round(bitmap.width * scale)), Math.max(1, Math.round(bitmap.height * scale)));
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return RawImage.fromCanvas(canvas);
  } finally {
    bitmap.close();
  }
}

// Keep the mask component the student clicked so stray pixels cannot enlarge its box.
function componentBounds(mask, width, height, x, y) {
  const start = y * width + x;
  if (!mask[start]) return null;
  const queue = new Uint32Array(mask.length);
  let read = 0, end = 1;
  let left = x, right = x, top = y, bottom = y;
  queue[0] = start;
  mask[start] = 0;
  const add = index => {
    if (!mask[index]) return;
    mask[index] = 0;
    queue[end++] = index;
  };
  while (read < end) {
    const index = queue[read++];
    const col = index % width;
    const row = Math.floor(index / width);
    left = Math.min(left, col);
    right = Math.max(right, col);
    top = Math.min(top, row);
    bottom = Math.max(bottom, row);
    if (col > 0) add(index - 1);
    if (col + 1 < width) add(index + 1);
    if (row > 0) add(index - width);
    if (row + 1 < height) add(index + width);
  }
  const w = right + 1 - left, h = bottom + 1 - top;
  if (end < 9 || w < 3 || h < 3 || end > width * height * 0.85) return null;
  return {x: left / width, y: top / height, w: w / width, h: h / height};
}

function insideSelection(box, selection) {
  const w = Math.max(0, Math.min(selection.x + selection.w, box.x + box.w) - Math.max(selection.x, box.x));
  const h = Math.max(0, Math.min(selection.y + selection.h, box.y + box.h) - Math.max(selection.y, box.y));
  return w * h >= box.w * box.h * 0.85 && box.w * box.h < selection.w * selection.h;
}

self.onmessage = async ({data: {photo, point, selection}}) => {
  try {
    if (!model || !processor) {
      postMessage({type: 'loading'});
      [processor, model] = await Promise.all([
        AutoProcessor.from_pretrained(modelId, {revision}),
        SamModel.from_pretrained(modelId, {revision, dtype: 'q8', device: 'wasm'}),
      ]);
    }
    postMessage({type: 'analyzing'});
    if (photo) {
      currentImage = await loadImage(photo);
      embeddings = null;
    }
    const {width, height} = currentImage;
    const x = Math.min(width - 1, Math.floor(point.x * width));
    const y = Math.min(height - 1, Math.floor(point.y * height));
    const inputs = await processor(currentImage, {input_points: [[[x, y]]]});
    embeddings ??= await model.get_image_embeddings(inputs);
    const {pred_masks, iou_scores} = await model({...inputs, ...embeddings});
    const [masks] = await processor.post_process_masks(pred_masks, inputs.original_sizes, inputs.reshaped_input_sizes);
    const scores = Array.from(iou_scores.data);
    const indices = scores.map((_, index) => index).sort((a, b) => scores[b] - scores[a]);
    const pixels = width * height;
    const proposed = [];
    for (const index of indices) {
      const mask = masks.data.subarray(index * pixels, (index + 1) * pixels);
      const bounds = componentBounds(mask, width, height, x, y);
      if (!bounds || (selection && !insideSelection(bounds, selection))) continue;
      if (proposed.some(box => ['x', 'y', 'w', 'h'].every(key => Math.abs(box[key] - bounds[key]) < 0.01))) continue;
      proposed.push(bounds);
    }
    postMessage({type: 'done', proposals: proposed});
  } catch (error) {
    console.error('Click to box:', error);
    currentImage = embeddings = null;
    postMessage({type: 'error'});
  }
};
