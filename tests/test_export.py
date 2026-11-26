"""Drive a local classroom round trip with 24 original illustrated frames.

Requires Pillow and Playwright. --output saves UI screenshots and the actual ZIP.
"""
import argparse
import io
import random
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import expect, sync_playwright

from test_review import confirm_no_object


def tabletop(index):
    width, height = (540, 720) if index == 2 else (720, 540)
    image = Image.new("RGB", (width, height), "#e3d6c2")
    draw = ImageDraw.Draw(image)
    rng = random.Random(index)
    for y in range(height):
        light = round(12 * (1 - y / height) + rng.uniform(-2, 2))
        draw.line((0, y, width, y), fill=(220+light, 204+light, 181+light))
    # Gridded cutting mat, ruler and paper discs. All artwork is generated locally.
    draw.rounded_rectangle((28, 32, width-28, height-50), 10, fill="#b5c7c0")
    for x in range(40, width-28, 18):
        draw.line((x, 39, x, height-57), fill="#c8d6cf")
    for y in range(40, height-53, 18):
        draw.line((35, y, width-35, y), fill="#c8d6cf")
    draw.rounded_rectangle((51, height-124, width//2, height-84), 4, fill="#e9c783")
    for j, x in enumerate(range(62, width//2-4, 6)):
        draw.line((x, height-122, x, height-(108 if j%5 == 0 else 115)), fill="#785a36")
    draw.ellipse((width-161, 63, width-69, 155), fill="#bd7552")
    boxes = []
    if index <= 21:
        x, y = 96+rng.randrange(96), 110+rng.randrange(40)
        boxes.append((x, y, x+144, y+144))
        if index == 1:
            boxes.append((x+122, y+90, x+232, y+200))
    for x, y, right, bottom in boxes:
        draw.ellipse((x+4, y+6, right+4, bottom+6), fill="#85968e")
        draw.ellipse((x, y, right, bottom), fill="#2869b5", outline="#244e7a", width=2)
    encoded = io.BytesIO()
    if index == 2:
        exif = Image.Exif()
        exif[274] = 6
        image.transpose(Image.Transpose.ROTATE_90).save(encoded, "JPEG", quality=95, exif=exif)
    else:
        image.save(encoded, "JPEG", quality=95)
    return encoded.getvalue(), [(x/width, y/height, r/width, b/height) for x,y,r,b in boxes]


def run(browser, output):
    site = (Path(__file__).resolve().parents[1] / "index.html").as_uri()
    page = browser.new_page(viewport={"width":1440, "height":900}, accept_downloads=True)
    network = []
    errors = []
    page.on("request", lambda req: network.append(req.url) if req.url.startswith(("http:", "https:")) else None)
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.goto(site)
    frames = [tabletop(i) for i in range(1, 25)]
    def photo(i):
        return {"name": f"table-{i:02}.jpg", "mimeType": "image/jpeg", "buffer": frames[i-1][0]}
    page.locator("#photosInput").set_input_files([photo(i) for i in range(1,25)])
    page.locator("#addClassBtn").click()
    page.locator("#classList input").fill("blue_disc")
    page.locator("#saveClassesBtn").click()
    page.get_by_role("button", name="Start Labeling", exact=True).click()
    canvas = page.locator("#canvas")
    for i, (_, boxes) in enumerate(frames, 1):
        expect(page.locator("#frameName")).to_have_text(f"table-{i:02}.jpg")
        expect(page.locator("#labeler")).not_to_have_attribute("inert", "")
        canvas.scroll_into_view_if_needed()
        rect = canvas.bounding_box()
        for x,y,right,bottom in boxes:
            page.mouse.move(rect["x"]+rect["width"]*x, rect["y"]+rect["height"]*y)
            page.mouse.down()
            page.mouse.move(rect["x"]+rect["width"]*right, rect["y"]+rect["height"]*bottom, steps=3)
            page.mouse.up()
        if not boxes:
            confirm_no_object(page)
        else:
            page.locator('#savePhotoBtn').click()
        if i in (1,2):
            expect(page.locator("#saveState")).to_contain_text("Saved")
            if i == 1:
                page.screenshot(path=output/"desktop.png")
                page.set_viewport_size({"width":820, "height":1024})
                page.screenshot(path=output/"tablet.png")
            else:
                page.set_viewport_size({"width":390, "height":844})
                expect(page.locator("#imageBrowser")).to_be_visible()
                page.screenshot(path=output/"phone-portrait.png")
            page.set_viewport_size({"width":1440, "height":900})
        if i < 24:
            page.locator("#nextBtn").click()
    page.locator("#backSetupBtn").click()
    expect(page.locator("#completionCard")).to_contain_text("No-object images: 3")
    with page.expect_download() as pending:
        page.get_by_role("button", name="Download Labeled_data.zip", exact=True).click()
    assert pending.value.suggested_filename == "Labeled_data.zip"
    dest = output / pending.value.suggested_filename
    pending.value.save_as(dest)
    page.locator("#confirmDownload").click()
    expect(page.locator("#trainingStep")).to_be_visible()
    page.screenshot(path=output/"training.png")
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None and len(z.namelist()) == 49
        assert z.read("classes.txt") == b"blue_disc\n"
        for i, (original, boxes) in enumerate(frames, 1):
            data = z.read(f"images/table-{i:02}.jpg")
            if i == 2:
                img = Image.open(io.BytesIO(data))
                assert img.size == (540,720) and img.getexif().get(274,1) == 1
                x,y,r,b = boxes[0]
                red,green,blue = img.getpixel((int((x+r)*270),int((y+b)*360)))
                assert blue > green > red
            else:
                assert data == original
            lines = z.read(f"labels/table-{i:02}.txt").decode().splitlines()
            assert len(lines) == len(boxes)
            for line, (x,y,r,b) in zip(lines, boxes):
                cls, *values = line.split()
                assert cls == "0"
                assert max(abs(float(a)-v) for a,v in zip(values, ((x+r)/2,(y+b)/2,r-x,b-y))) < .007
    page.reload()
    page.locator("#zipImagesInput").set_input_files(dest)
    expect(page.locator("#completionCard")).to_contain_text("Images with boxes: 21")
    assert not network and not errors, (network, errors)
    page.close()
    print("PASS 24 frames, 22 boxes, 3 backgrounds, EXIF portrait, ZIP bytes and coordinates, reopen, zero HTTP requests", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", default="chrome")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        out = args.output or Path(tmp)
        out.mkdir(parents=True, exist_ok=True)
        browser = pw.chromium.launch(channel=args.channel)
        run(browser, out)
        browser.close()
