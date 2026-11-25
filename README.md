# YOLO Dataset Labeler

A browser-based tool for creating, editing, validating, importing, and exporting object-detection annotations in the standard YOLO bounding-box format.

## Classroom entry point

For the Vietnam AI Workshop, [open the classroom labeler](https://active-learning-kyle.github.io/yolo-dataset-labeler/).

This workshop edition is based on [Timmy Cheng’s original YOLO Dataset Labeler](https://timmy-wccheng.github.io/yolo-dataset-labeler/).

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

1. For the classroom exercise, create an empty folder on your computer. In desktop Chrome or Edge, select **Open dataset folder**, choose that folder, and allow write access. Select **Create Missing Items** to create `images/`, `labels/` and `classes.txt`. Copy your workshop photos into `images/` using your file manager, then select **Refresh Dataset**.
2. Review the image count. Choose **Add Class** for each assigned class, enter the names in the required order, then select **Save Classes**. The first class has ID 0.
3. Select **Start Labeling**. Choose **New box class** and use **Draw** to box each visible target, even inside another box. For example, in an assembly kit inspection, draw a separate box around each bolt and hex nut. To adjust an existing box, choose **Edit** and select it on the canvas or in the box list. Drag the box or a corner, or use **Change selected box class**. Choose **Hide boxes** to inspect the original photo. Use the thumbnail strip to jump between images. On phones, tap **Images** to open it.
4. Choose **Confirm no object** only after inspecting the whole image. A missing label means the image still needs review. An empty label records a reviewed background.
5. Select **Next** to advance. Skipping an untouched image keeps it unreviewed. In direct folder mode, the labeler saves edits to the selected folder. Open that folder again to resume. In a photo, ZIP or imported-folder session, use **Download draft ZIP** before closing the tab and **Open a ZIP** to resume.
6. When review is complete, download **Labeled_data.zip**. The labeler packages the images, matching label files and class list. Check your Downloads folder before selecting **I have the ZIP**.
7. **Continue to Training in Colab** opens the Colab home page. Sign in there, upload the notebook supplied by your instructor, then upload your own ZIP to session storage. Match the class names and order required by that notebook. Keep unseen test images outside the training ZIP.

If you already have a workshop pack or a saved draft, select **Open a ZIP**. To use individual photos without preparing a folder, select **Start with my photos**. You can also drop photos or one ZIP onto the cover. When direct folder writing is unavailable, opening a prepared folder imports a copy into the tab. Download a draft ZIP before closing a tab that holds your edits.

For phone photos, choose JPG/JPEG, PNG, WebP or BMP. Convert HEIC/HEIF before importing. The ZIP writer re-encodes JPEGs with EXIF rotation or reflection in their displayed orientation so their labels align in readers that ignore metadata. Original photos on your device are preserved.

## Keyboard Shortcuts

- `A` or `Left Arrow`: previous image
- `D` or `Right Arrow`: next image
- `B` / `V`: draw / edit
- `1` to `9`: choose the class for the next box
- `Delete` or `Backspace`: delete the selected box
- `Ctrl/Cmd + Z`: undo
- `Ctrl/Cmd + Shift + Z`: redo
- `Ctrl/Cmd + S`: download a draft ZIP
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
- Loose photos and unlabeled ZIP images with colliding stems receive unique names inside the dataset. Direct folders and ambiguous image–label pairs must be fixed before labeling. When collecting files outside the labeler, give each one a unique stem before copying it into a shared folder, such as `target-001.webp` and `target-002.webp`. Keep the extension and keep paired labels with their images.
- The tool creates YOLO bounding-box annotations. It does not train, evaluate, or run a YOLO model.
- Browser behaviour may change as the File System Access API and related web APIs evolve.

## AI Assistance

This project was developed with assistance from generative AI. The code was reviewed and adapted by the repository owner.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
