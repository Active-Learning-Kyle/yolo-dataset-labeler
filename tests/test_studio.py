"""Exercise local file drops, thumbnail navigation, and original-image review."""
import argparse
import base64
import io
import zipfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from test_review import solid_png


def drop(page, files):
    payload = [(name, base64.b64encode(data).decode()) for name, data in files]
    page.locator('#dropZone').evaluate("""(zone, entries) => {
        const transfer = new DataTransfer();
        for (const [name, encoded] of entries) {
            const bytes = Uint8Array.from(atob(encoded), c => c.charCodeAt(0));
            transfer.items.add(new File([bytes], name));
        }
        for (const type of ['dragover', 'drop']) {
            zone.dispatchEvent(new DragEvent(type, {dataTransfer:transfer, bubbles:true, cancelable:true}));
        }
    }""", payload)


def run(browser):
    page = browser.new_page(viewport={'width': 1024, 'height': 820})
    errors = []
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.goto((Path(__file__).resolve().parents[1] / 'index.html').as_uri())
    labels = page.locator('.kit-photo .photo-box b')
    names = ['Hex head', 'Socket cap', 'Thumb screw', 'Wing screw', 'Eye screw', 'Set screw',
             'Self-drilling', 'Slotted flat', 'Wood screw', 'Shoulder screw', 'Pan head', 'Round head']
    expect(labels).to_have_text(names)
    expect(page.locator('#photoKey li')).to_have_text(names)
    for width in (320, 390, 600, 820, 1024, 1440):
        page.set_viewport_size({'width': width, 'height': 850})
        page.locator('.kit-photo').scroll_into_view_if_needed()
        if page.locator('.kit-photo').bounding_box()['width'] <= 480:
            expect(page.locator('#photoKey')).to_be_visible()
            expect(labels.first.locator('span')).to_be_hidden()
        else:
            expect(page.locator('#photoKey')).to_be_hidden()
            expect(labels.first.locator('span')).to_be_visible()
        assert labels.evaluate_all("""labels => {
            const photo = labels[0].closest('.kit-photo').getBoundingClientRect();
            const tags = labels.map(label => label.getBoundingClientRect());
            return tags.every((a, i) => a.width > 0 && a.left >= photo.left && a.right <= photo.right
                && a.top >= photo.top && a.bottom <= photo.bottom
                && tags.slice(i + 1).every(b => a.right <= b.left || b.right <= a.left
                    || a.bottom <= b.top || b.bottom <= a.top));
        }""")
        covered = labels.evaluate_all("""labels => labels.filter(label => {
            const r = label.getBoundingClientRect();
            const y = r.top + r.height / 2;
            return [r.left + 1, r.left + r.width / 2, r.right - 1].some(x =>
                !label.contains(document.elementFromPoint(x, y)));
        }).map(label => label.textContent)""")
        assert not covered, f'Cover labels obscured at {width}px: {covered}'
    page.set_viewport_size({'width': 1024, 'height': 820})
    photo = solid_png(200, 170)
    frames = io.BytesIO()
    with zipfile.ZipFile(frames, 'w') as archive:
        archive.writestr('classes.txt', 'bolt\nhex_nut\n')
        for i in range(20):
            archive.writestr(f'images/kit-{i:02}.png', photo)
        archive.writestr('labels/kit-00.txt', '1 0.5 0.5 0.4 0.3\n')
    dataset = ('kit.zip', frames.getvalue())
    drop(page, [dataset, ('loose.png', photo)])
    expect(page.get_by_role('alert')).to_contain_text('Drop one dataset ZIP')
    expect(page.locator('#landing')).to_be_visible()
    drop(page, [('a.png', photo), ('b.png', photo)])
    expect(page.locator('#summaryStats .stat').first).to_have_text('2Images')
    page.reload()
    drop(page, [dataset])
    page.get_by_role('button', name='Review all photos', exact=True).click()
    first = page.locator('#imageList .image-item').first
    expect(first.locator('img')).to_have_js_property('complete', True)
    page.wait_for_function('document.querySelector("#imageList img").naturalWidth > 0')
    canvas = page.locator('#canvas')
    annotated = canvas.evaluate('c => c.toDataURL()')
    page.locator('#toggleBoxes').click()
    expect(page.get_by_role('button', name='Show boxes')).to_be_visible()
    assert canvas.evaluate('c => c.toDataURL()') != annotated
    rect = canvas.bounding_box()
    page.mouse.move(rect['x'] + 15, rect['y'] + 15)
    page.mouse.down()
    page.mouse.move(rect['x'] + 75, rect['y'] + 75)
    page.mouse.up()
    page.locator('#toggleBoxes').click()
    assert canvas.evaluate('c => c.toDataURL()') == annotated
    expect(page.locator('#boxList .box-row')).to_have_count(1)
    # Select by search, then navigate through a longer strip with the keyboard.
    page.locator('#imageSearch').fill('kit-17')
    page.locator('#imageList .image-item').click()
    page.locator('#imageSearch').fill('')
    page.locator('#nextBtn').focus()
    page.keyboard.press('d')
    expect(page.locator('#frameName')).to_have_text('kit-18.png')
    page.wait_for_function("""() => {
        const list = document.querySelector('#imageList');
        const current = list.querySelector('.current');
        return list.scrollLeft > 0 && current.querySelector('img').naturalWidth > 0
            && current.getBoundingClientRect().right <= list.getBoundingClientRect().right + 1;
    }""")
    page.set_viewport_size({'width': 390, 'height': 844})
    expect(page.locator('#imageBrowser')).to_be_hidden()
    expect(page.locator('#browseImages')).to_contain_text('19 / 20')
    page.locator('#browseImages').click()
    expect(page.locator('#imageList .current')).to_be_in_viewport()
    assert not errors, errors
    page.close()
    print('PASS mixed-drop rejection, photo and ZIP drops, real thumbnails, keyboard filmstrip navigation, mobile drawer, box visibility')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', default='chrome')
    args = parser.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=args.channel)
        run(browser)
        browser.close()
