"""Check workbench photo additions, removal, and restoration."""

import io
import zipfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from test_review import confirm_no_object, dismiss_box_guide, solid_png


HTML = Path(__file__).resolve().parents[1] / 'index.html'
PHOTO = solid_png(200, 140)


def upload(page, names):
    with page.expect_file_chooser() as chooser:
        page.locator('#imageList').get_by_role('button', name='Add photos', exact=True).click()
    chooser.value.set_files([{'name': name, 'mimeType': 'image/png', 'buffer': PHOTO}
                             for name in names])


def remove(page, name, touch=False):
    button = page.get_by_role('button', name=f'Remove {name} from dataset', exact=True)
    if touch:
        expect(button).to_have_css('opacity', '1')
        button.tap()
    else:
        button.locator('..').hover()
        expect(button).to_have_css('opacity', '1')
        button.click()


def export(page, selector):
    with page.expect_download() as pending:
        page.locator(selector).click()
    with zipfile.ZipFile(pending.value.path()) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    page.locator('#dismissDownload').click()
    return files


def memory_workbench(browser):
    page = browser.new_page(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    page.goto(HTML.as_uri())
    original = io.BytesIO()
    with zipfile.ZipFile(original, 'w') as archive:
        archive.writestr('classes.txt', 'bolt\nhex_nut\n')
        archive.writestr('images/kit.png', PHOTO)
        archive.writestr('labels/kit.txt', '1 0.5 0.5 0.4 0.4\n')
    page.locator('#zipImagesInput').set_input_files(
        {'name': 'test.zip', 'mimeType': 'application/zip', 'buffer': original.getvalue()})
    class_rows = page.locator('#classList .class-row')
    page.locator('#addClassBtn').tap()
    page.locator('#saveClassesBtn').tap()
    expect(page.locator('#classError')).to_contain_text('Class names cannot be blank.')
    for index in (0, 1):
        expect(class_rows.nth(index).get_by_role('button', name='Delete')).to_be_disabled()
    draft_delete = class_rows.nth(2).get_by_role('button', name='Delete')
    expect(draft_delete).to_be_enabled()
    draft_delete.tap()
    expect(class_rows).to_have_count(2)
    expect(page.locator('#classError')).to_be_empty()
    page.locator('#addClassBtn').tap()
    class_rows.nth(2).locator('input').fill('washer')
    page.locator('#saveClassesBtn').tap()
    spare = class_rows.nth(2).get_by_role('button', name='Delete')
    expect(spare).to_be_enabled()
    spare.tap()
    page.locator('#saveClassesBtn').tap()
    page.locator('#labelAllBtn').click()
    dismiss_box_guide(page, touch=True)
    expect(page.locator('#boxList .box-row')).to_have_count(1)
    expect(page.locator('#imageBrowser')).to_be_visible()
    remove(page, 'kit.png', touch=True)
    expect(page.locator('#progressText')).to_contain_text('No photos')
    expect(page.locator('#imageList button').last).to_have_text('+Add photos')
    page.get_by_role('button', name='Back to dataset').tap()
    expect(page.locator('#reviewExportTitle')).to_be_focused()
    expect(page.locator('#summaryStats .stat').first).to_have_text('0Images')
    expect(class_rows.nth(1).get_by_role('button', name='Delete')).to_be_disabled()
    page.locator('#setupUndoRemove').tap()
    expect(page.locator('#summaryStats .stat').first).to_have_text('1Images')
    page.locator('#labelAllBtn').tap()
    expect(page.locator('#boxList .box-row')).to_contain_text('1: hex_nut')
    canvas = page.locator('#canvas')
    canvas.scroll_into_view_if_needed()
    frame = canvas.bounding_box()
    mouse = page.mouse
    mouse.move(frame['x'] + frame['width'] * .15, frame['y'] + frame['height'] * .15)
    mouse.down()
    mouse.move(frame['x'] + frame['width'] * .65, frame['y'] + frame['height'] * .65, steps=4)
    mouse.up()
    expect(page.locator('#boxList .box-row')).to_have_count(2)
    upload(page, ['a.png', 'kit.png'])
    expect(page.locator('#imageList .image-name')).to_have_text(['kit.png', 'a.png', 'kit_imported_2.png'])
    expect(page.locator('#imageList button').last).to_have_text('+Add photos')
    expect(page.locator('#frameName')).to_have_text('kit.png')
    expect(page.locator('#boxList .box-row')).to_have_count(2)
    expect(page.locator('#progressText')).to_contain_text('Reviewed 0 · Remaining 3')
    remove(page, 'kit.png', touch=True)
    expect(page.locator('#frameName')).to_have_text('a.png')
    expect(page.locator('#undoRemovePhoto')).to_be_visible()
    draft = export(page, '#draftBtn')
    assert set(draft) == {'classes.txt', 'images/a.png', 'images/kit_imported_2.png'}
    for name in ('a.png', 'kit_imported_2.png'):
        page.get_by_role('button', name=f'{name} Unlabeled').click()
        confirm_no_object(page)
    page.locator('#backSetupBtn').click()
    training = export(page, '#trainingZipBtn')
    assert set(training) == {*draft, 'labels/a.txt', 'labels/kit_imported_2.txt'}
    assert training['classes.txt'] == b'bolt\nhex_nut\n'
    page.close()


def writable_workbench(browser):
    page = browser.new_page(viewport={'width': 1360, 'height': 860})
    page.route('http://localhost/index.html', lambda route: route.fulfill(
        content_type='text/html; charset=utf-8', body=HTML.read_bytes()))
    page.goto('http://localhost/index.html')
    page.evaluate("""async bytes => {
        const root = await navigator.storage.getDirectory();
        window.showDirectoryPicker = async () => root;
        async function write(dir, name, data) {
            const handle = await dir.getFileHandle(name, {create: true});
            const stream = await handle.createWritable();
            await stream.write(data);
            await stream.close();
        }
        await write(root, 'classes.txt', 'bolt\\n');
        await write(await root.getDirectoryHandle('images', {create: true}), 'm.png', new Uint8Array(bytes));
        await write(await root.getDirectoryHandle('labels', {create: true}), 'm.txt', '');
    }""", list(PHOTO))
    page.locator('#openBtn').click()
    page.locator('#addClassBtn').click()
    appended_class = page.locator('#classList .class-row').last
    appended_class.locator('input').fill('hex_nut')
    expect(appended_class.get_by_role('button', name='Delete')).to_be_enabled()
    page.locator('#saveClassesBtn').click()
    expect(page.locator('#classList button').filter(has_text='Delete').first).to_be_enabled()
    page.locator('#labelAllBtn').click()
    dismiss_box_guide(page)
    expect(page.locator('#frameName')).to_have_text('m.png')
    page.evaluate("""() => {
        const original = FileSystemFileHandle.prototype.createWritable;
        window.rejectPhoto = true;
        FileSystemFileHandle.prototype.createWritable = function (...options) {
            if (window.rejectPhoto && this.name === 'a.png') throw new Error('Write denied in test');
            return original.apply(this, options);
        };
    }""")
    upload(page, ['a.png'])
    expect(page.get_by_role('alert')).to_contain_text('Write denied in test')
    expect(page.locator('#imageList .image-name')).to_have_text(['m.png'])
    page.evaluate('window.rejectPhoto = false')
    upload(page, ['a.png'])
    expect(page.locator('#imageList .image-name')).to_have_text(['m.png', 'a.png'])
    original = page.get_by_role('button', name='Remove m.png from dataset')
    page.locator('#frameName').hover()
    expect(original).to_have_css('opacity', '0')
    original.focus()
    expect(original).to_have_css('opacity', '1')
    remove(page, 'm.png')
    expect(page.locator('#frameName')).to_have_text('a.png')
    assert page.evaluate("""async () => {
        const root = await navigator.storage.getDirectory();
        const images = await root.getDirectoryHandle('images');
        const labels = await root.getDirectoryHandle('labels');
        return (await (await images.getFileHandle('a.png')).getFile()).size > 0 &&
               (await (await images.getFileHandle('m.png')).getFile()).size > 0 &&
               (await (await labels.getFileHandle('m.txt')).getFile()).size === 0;
    }""")
    draft = export(page, '#draftBtn')
    assert set(draft) == {'classes.txt', 'images/a.png'}
    page.locator('#undoRemovePhoto').click()
    expect(page.locator('#imageList .image-name')).to_have_text(['m.png', 'a.png'])
    expect(page.locator('#imageList .image-item').first).to_contain_text('No Object')
    page.close()


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome')
        memory_workbench(browser)
        writable_workbench(browser)
        browser.close()
    print('PASS draft class deletion, saved class ID protection, photo management and ZIP contents')
