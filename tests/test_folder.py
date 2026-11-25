"""Check the direct-write path in an isolated browser-managed directory."""
import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from test_review import solid_png


def check(browser):
    page = browser.new_page()
    html = Path(__file__).resolve().parents[1] / 'index.html'
    page.route('http://localhost/index.html', lambda route: route.fulfill(
        content_type='text/html; charset=utf-8', body=html.read_bytes()))
    page.goto('http://localhost/index.html')
    page.evaluate("""async bytes => {
        const root = await navigator.storage.getDirectory();
        async function write(dir, name, data) {
            const file = await dir.getFileHandle(name, {create:true});
            const writer = await file.createWritable();
            await writer.write(data);
            await writer.close();
        }
        const imgs = await root.getDirectoryHandle('images', {create:true});
        await root.getDirectoryHandle('labels', {create:true});
        await write(root, 'classes.txt', 'disc');
        for (const name of ['a.png', 'b.png']) await write(imgs, name, new Uint8Array(bytes));
        window.showDirectoryPicker = async () => root;
    }""", list(solid_png(320, 240)))
    page.locator('#openBtn').click()
    page.get_by_role('button', name='Start Labeling', exact=True).click()
    page.evaluate("""() => {
        const proto = FileSystemFileHandle.prototype;
        const create = proto.createWritable;
        proto.createWritable = function (...args) {
            if (window.rejectWrites) return Promise.reject(new Error('Write denied in test'));
            return create.apply(this, args);
        };
        window.rejectWrites = true;
    }""")
    canvas = page.locator('#canvas')
    canvas.scroll_into_view_if_needed()
    rect = canvas.bounding_box()
    page.mouse.move(rect['x'] + 30, rect['y'] + 30)
    page.mouse.down()
    page.mouse.move(rect['x'] + 130, rect['y'] + 160)
    page.mouse.up()
    page.locator('#nextBtn').click()
    expect(page.locator('#saveState')).to_have_text('Save failed')
    expect(page.locator('#frameName')).to_have_text('a.png')
    page.evaluate('window.rejectWrites = false')
    page.locator('#nextBtn').click()
    expect(page.locator('#frameName')).to_have_text('b.png')
    page.locator('#noObjectBtn').click()
    expect(page.locator('#saveState')).to_have_text('Saved to folder')
    labels = page.evaluate("""async () => {
        const dir = await (await navigator.storage.getDirectory()).getDirectoryHandle('labels');
        const labels = {};
        for await (const [name, handle] of dir.entries()) labels[name] = await (await handle.getFile()).text();
        return labels;
    }""")
    assert labels['b.txt'] == '' and labels['a.txt'].split()[0] == '0'
    assert len(labels['a.txt'].split()) == 5
    page.close()
    print('PASS direct write denial, navigation held, retry to original file, empty background label')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', default='chrome')
    args = parser.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=args.channel)
        check(browser)
        browser.close()
