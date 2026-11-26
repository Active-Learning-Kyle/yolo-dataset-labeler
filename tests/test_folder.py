"""Check writable folder setup and read-only folder import and recovery."""
import argparse
import tempfile
import zipfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from test_review import confirm_no_object, solid_png


def check_read_only_folder(browser):
    page = browser.new_page(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    page.add_init_script('window.showDirectoryPicker = undefined')
    page.goto((Path(__file__).resolve().parents[1] / 'index.html').as_uri())
    folder = page.get_by_role('button', name='Open dataset folder', exact=True)
    with tempfile.TemporaryDirectory() as directory:
        with page.expect_file_chooser() as picker:
            folder.click()
        expect(page.locator('#folderFeedback')).to_contain_text('empty folder')
        picker.value.set_files(directory)
        # Some pickers emit an empty change, some emit cancel or no event.
        expect(page.locator('#folderFeedback')).to_contain_text('Start with my photos')
        expect(page.locator('#landing')).to_be_visible()
        page.locator('#folderInput').dispatch_event('cancel')
        expect(page.locator('#folderFeedback')).to_contain_text('No files were received')
        with page.expect_file_chooser() as photos:
            page.get_by_role('button', name='Start with my photos').click()
        png = solid_png(80, 60)
        photos.value.set_files({'name': 'sample.png', 'mimeType': 'image/png', 'buffer': png})
        expect(page.locator('#summaryStats .stat').first).to_have_text('1Images')
        page.locator('#addClassBtn').click()
        page.locator('#classList input').fill('bolt')
        page.locator('#saveClassesBtn').click()
        page.get_by_role('button', name='Start Labeling', exact=True).click()
        confirm_no_object(page)
        page.locator('#backSetupBtn').click()
        with page.expect_download() as archive:
            page.get_by_role('button', name='Download Labeled_data.zip', exact=True).click()
        assert archive.value.suggested_filename == 'Labeled_data.zip'
        with zipfile.ZipFile(archive.value.path()) as dataset:
            assert dataset.read('images/sample.png') == png
            assert dataset.read('labels/sample.txt') == b''
            assert dataset.read('classes.txt') == b'bolt\n'
        page.locator('#confirmDownload').click()

        # Reopen a populated read-only dataset with the same chooser.
        page.reload()
        root = Path(directory)
        (root/'images').mkdir()
        (root/'labels').mkdir()
        (root/'images/sample.png').write_bytes(png)
        (root/'classes.txt').write_text('target\n')
        (root/'labels/sample.txt').write_text('')
        with page.expect_file_chooser() as retry:
            folder.click()
        retry.value.set_files(directory)
        expect(page.locator('#completionCard')).to_contain_text('No-object images: 1')
    page.close()
    print('PASS read-only empty folder, persistent feedback, photo-to-ZIP recovery and prepared-folder import')


def check(browser):
    page = browser.new_page()
    html = Path(__file__).resolve().parents[1] / 'index.html'
    page.route('http://localhost/index.html', lambda route: route.fulfill(
        content_type='text/html; charset=utf-8', body=html.read_bytes()))
    page.goto('http://localhost/index.html')
    page.evaluate('window.showDirectoryPicker = () => navigator.storage.getDirectory()')
    folder = page.get_by_role('button', name='Open dataset folder', exact=True)
    expect(page.locator('.entry-actions button').first).to_have_id('openBtn')
    expect(page.locator('.entry-actions .primary')).to_have_count(1)
    folder.click()
    expect(page.locator('#checklist .missing')).to_have_count(3)
    expect(page.locator('#importLabelsBtn')).to_be_hidden()
    page.get_by_role('button', name='Create Missing Items').click()
    expect(page.locator('#checklist .ok')).to_have_count(3)
    page.evaluate("""async bytes => {
        const root = await navigator.storage.getDirectory();
        const imgs = await root.getDirectoryHandle('images');
        for (const name of ['a.png', 'b.png']) {
            const file = await imgs.getFileHandle(name, {create:true});
            const writer = await file.createWritable();
            await writer.write(new Uint8Array(bytes));
            await writer.close();
        }
    }""", list(solid_png(320, 240)))
    page.get_by_role('button', name='Refresh Dataset').click()
    expect(page.locator('#summaryStats .stat').first).to_have_text('2Images')
    page.locator('#addClassBtn').click()
    page.locator('#classList input').fill('disc')
    page.locator('#saveClassesBtn').click()
    expect(page.locator('#importLabelsBtn')).to_be_visible()
    expect(page.locator('#summaryDraftBtn')).to_be_hidden()
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
    save_exit = page.get_by_role('button', name='Save & exit', exact=True)
    save_exit.click()
    expect(page.locator('#saveState')).to_have_text('Save failed')
    expect(page.locator('#labeler')).to_be_visible()
    expect(save_exit).to_be_focused()
    expect(page.locator('#boxList .box-row')).to_have_count(1)
    page.evaluate('window.rejectWrites = false')
    save_exit.click()
    expect(page.locator('#labeler')).to_be_hidden()
    expect(page.get_by_role('heading', name='3. Review & export')).to_be_focused()
    page.get_by_role('button', name='Label remaining photos (1)').click()
    expect(page.locator('#frameName')).to_have_text('b.png')
    confirm_no_object(page)
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
    print('PASS empty-folder setup, class save, write denial, Save & exit, resume and background label')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', default='chrome')
    args = parser.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=args.channel)
        check(browser)
        check_read_only_folder(browser)
        browser.close()
