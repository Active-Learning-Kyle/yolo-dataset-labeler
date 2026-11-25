# YOLO Dataset Labeler

A browser-based tool for creating, editing, validating, importing, and exporting object-detection annotations in the standard YOLO bounding-box format.

## Classroom entry point

The current classroom link is Timmy Cheng’s original release. To try the workshop branch, download its `index.html` and open it in a browser.

https://timmy-wccheng.github.io/yolo-dataset-labeler/

## Features

- Draw, move, resize, delete, and reclassify bounding boxes
- Read and write standard YOLO labels using normalized `class_id x_center y_center width height` values
- Manage class names through `classes.txt`
- Validate malformed labels, invalid class IDs, out-of-range boxes, orphan labels, and duplicate image-name stems
- Mark background images by saving an empty label file
- Import images or complete datasets from ZIP files
- Export a completed dataset as `Labeled_data.zip`
- Undo and redo annotation changes
- Search images and filter unlabeled or invalid files
- Support JPG, JPEG, PNG, WebP, and BMP images
- Work without external JavaScript libraries or server-side processing

## Privacy

Selected images and label files are processed locally in the user's browser. This application does not intentionally upload dataset contents to a server.

When the application is opened through GitHub Pages, GitHub still serves the webpage and may process ordinary website-access information according to GitHub's own policies. Dataset files selected in the application are not intentionally sent to GitHub by this project.

## Browser Support

For the best experience, use the latest desktop version of Google Chrome or Microsoft Edge.

| Browser | Folder access | Saving behaviour |
| --- | --- | --- |
| Chrome or Edge on desktop | Direct folder mode when the File System Access API is available | Labels and `classes.txt` can be written back to the selected folder |
| Safari or Firefox on desktop | Compatibility mode | Download a draft ZIP before closing the tab, or the final ZIP when review is complete |

## Dataset Structure

The recommended dataset structure is:

```text
dataset/
├── images/
│   ├── image_001.jpg
│   └── image_002.jpg
├── labels/
│   ├── image_001.txt
│   └── image_002.txt
└── classes.txt
```

Each non-empty label line must contain exactly five fields:

```text
class_id x_center y_center width height
```

Example:

```text
0 0.512500 0.475000 0.225000 0.350000
```

Coordinates and dimensions are normalized to the range from `0` to `1`. An empty label file represents an image containing no target object.

## How to Use

1. Select **Import Images ZIP**. Open the classroom images, a draft ZIP, or a dataset with `images/`, `labels/` and `classes.txt`. Desktop browsers that support writable folder access can also use **Open Dataset Folder**.
2. Review the image count and class order in the dataset summary. Enter the agreed class names and select **Save Classes** before starting. The first class has ID 0.
3. Select **Start Labeling**. Drag a box around the visible part of each target. Select a box to move it or drag a handle to resize it. Expand the box guide for examples.
4. Choose **Confirm no object** only after inspecting the whole image. A missing label means the image still needs review. An empty label records a reviewed background.
5. Return to the dataset summary to download a **draft ZIP** before you leave a ZIP session. Reopen the draft with **Import Images ZIP**. Direct folder mode writes changes back to the selected folder.
6. When review is complete, download **Labeled_data.zip**. The class list, images and labels at the root match the classroom notebook’s input. Keep unseen test images outside this training ZIP.

## Keyboard Shortcuts

- `A` or `Left Arrow`: previous image
- `D` or `Right Arrow`: next image
- `1` to `9`: select a class
- `Delete` or `Backspace`: delete the selected box
- `Ctrl/Cmd + Z`: undo
- `Ctrl/Cmd + Shift + Z`: redo
- `Ctrl/Cmd + S`: save
- `Esc`: cancel the current action or deselect a box

## ZIP Limits

The application applies the following defensive limits:

- Maximum ZIP input size: 1 GiB
- Maximum number of ZIP entries: 50,000
- Maximum uncompressed size per entry: 512 MiB
- Maximum total extracted size: 2 GiB
- Supported compression methods: Store and Deflate
- ZIP filenames must be UTF-8 or ASCII
- Password-protected ZIP files are not supported

Large datasets can still exceed the practical memory limits of a browser before reaching these maximum values. For large projects, divide the dataset into smaller batches and keep backup copies of the original images and labels.

## Important Notes

- Keep a backup before using direct folder mode because the application can write `classes.txt` and files inside `labels/`.
- Class order is locked after label files exist because changing class IDs would change the meaning of existing annotations.
- Images with the same filename stem, such as `sample.jpg` and `sample.png`, are rejected because both would map to `sample.txt`.
- The tool creates YOLO bounding-box annotations. It does not train, evaluate, or run a YOLO model.
- Browser behaviour may change as the File System Access API and related web APIs evolve.

## AI Assistance

This project was developed with assistance from generative AI. The code was reviewed and adapted by the repository owner.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
