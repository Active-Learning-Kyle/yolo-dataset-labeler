# YOLO Dataset Labeler

[Open YOLO Dataset Labeler](https://active-learning-kyle.github.io/yolo-dataset-labeler/)

Draw boxes around objects in your photos and export a dataset for YOLO training. Your photos and labels stay in your browser while you work. No account is needed for labeling.

## Add your photos

1. On your computer, create an empty folder called `My Dataset`. Open the labeler in Chrome or Edge.
2. Click **Open dataset folder**, select your folder and allow access if prompted.
3. Click **Create Missing Items**. The labeler creates `images/`, `labels/` and `classes.txt` for you.
4. Copy your training photos into `images/`, then click **Refresh Dataset**. Keep a few fresh photos separate for testing later.

**On a phone?** Tap **Start with my photos** to choose pictures directly. You can skip the folder setup. Use JPG, PNG, WebP or BMP. Convert HEIC or HEIF photos to JPEG or PNG first.

**Already have a dataset or a draft ZIP?** Click **Open a ZIP** and select it.

## Choose your objects and label them

1. Decide what you want to detect. For example, if you want to tell bolts and nuts apart, add `bolt` and `nut` as two classes. Click **Add Class** for each name, then **Save Classes**. Your first class gets ID 0, the next gets ID 1.
2. Click **Start Labeling**. In **Draw**, choose the **New box class**, then drag a tight box around each matching object. You can draw overlapping boxes. Changing this dropdown sets the class for the next box.
3. To adjust an existing box, switch to **Edit** and select it on the image or in the box list. Move it, drag a corner to resize it, or change its class. Use **Undo** to reverse a mistake.
4. Click **Next** to continue. If you checked the whole photo and found none of your objects, click **Confirm no object**. Skipping an untouched photo leaves it unreviewed.

## Save and resume

- **Working in a writable folder:** Look for **Saved to folder** before closing. Open the same folder to resume. If you see **Save failed**, stay on the image, check write access and retry.
- **Working with photos, a ZIP or a read-only folder:** Click **Download draft ZIP** before closing the tab. Next time, choose **Open a ZIP** to resume.

## Export and train

1. Open **Dataset summary** and finish reviewing any remaining images. Click **Download Labeled_data.zip**. The ZIP contains your photos in `images/`, a matching text file for each photo in `labels/`, and your class names in order in `classes.txt`.
2. Find the ZIP in your downloads, then click **I have the ZIP** and **Continue to Training in Colab**.
3. In Colab, open the notebook supplied in Part 5D. In the **Files** panel, upload your `Labeled_data.zip` and leave it zipped. Run the dataset check and confirm the class names match yours before starting training.

[MIT License](LICENSE)
