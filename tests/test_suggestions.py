"""Check that model suggestions remain provisional until reviewed."""
import argparse
from pathlib import Path
import zipfile

from playwright.sync_api import expect, sync_playwright

from test_review import confirm_no_object, solid_png


def stub_point_worker(page):
    page.route('http://localhost/click-box-worker.js', lambda route: route.fulfill(
        content_type='text/javascript', body="""
        onmessage = ({data}) => setTimeout(() => postMessage({type: 'done', proposals: [
          {x:.25, y:.25, w:data.selection ? .15 : .5, h:.25},
          {x:.25, y:.25, w:data.selection ? .25 : .35, h:.25}
        ]}), 200);
        """))


def run(browser):
    page = browser.new_page()
    site = 'http://localhost/index.html'
    html = Path(__file__).resolve().parents[1] / 'index.html'
    page.route(site, lambda route: route.fulfill(content_type='text/html; charset=utf-8', body=html.read_bytes()))
    page.route('http://localhost/suggest-boxes-worker.js', lambda route: route.fulfill(
        content_type='text/javascript',
        body="""onmessage = ({data}) => {
          postMessage({type:'analyzing'});
          const boxes = data.photo.name === 'a.png'
            ? [{classId:0, x:12, y:14, w:30, h:32, score:0.62}] : [];
          setTimeout(() => postMessage({type:'done', boxes}), 150);
        };""",
    ))
    stub_point_worker(page)
    errors, worker_loads = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: worker_loads.append(request.url) if request.url.endswith('suggest-boxes-worker.js') else None)
    page.goto(site)
    expect(page.locator('#landing')).not_to_contain_text('Vietnam AI Workshop')
    page.locator('#photosInput').set_input_files([
        {'name': name, 'mimeType': 'image/png', 'buffer': solid_png(100, 80)}
        for name in ('a.png', 'b.png')
    ])
    for index, name in enumerate(('bolt', 'hex_nut')):
        page.locator('#addClassBtn').click()
        page.locator('#classList input').nth(index).fill(name)
    page.locator('#saveClassesBtn').click()
    page.get_by_role('button', name='Start Labeling', exact=True).click()

    suggest = page.locator('.draw-tools').get_by_role('button', name='Suggest boxes', exact=True)
    review = page.locator('#suggestReview')
    row = page.locator('#boxList .box-row')
    expect(suggest).to_be_visible()
    assert not worker_loads, worker_loads
    suggest.click()
    page.locator('#cancelSuggestions').click()
    expect(page.locator('#suggestStatus')).to_contain_text('Suggestions canceled')
    expect(suggest).to_be_enabled()
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    suggest.click()
    expect(review).to_be_visible()
    expect(row).to_contain_text('AI 0.62')
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    page.locator('#nextBtn').click()
    expect(page.locator('#frameName')).to_have_text('a.png')
    page.keyboard.press('Control+s')
    expect(page.locator('#downloadDialog')).to_be_hidden()
    page.get_by_role('button', name='Click to box', exact=True).click()
    page.locator('#canvas').click(position={'x': 115, 'y': 90})
    page.get_by_role('button', name='Apply box', exact=True).click()
    expect(row).to_have_count(2)
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    page.locator('#discardSuggestions').click()
    expect(row).to_have_count(0)
    expect(page.locator('#saveState')).to_have_text('Not reviewed')

    suggest.click()
    expect(review).to_be_visible()
    picker = row.get_by_role('combobox', name='Class for box 1')
    expect(picker).to_have_value('0')
    picker.select_option('1')
    expect(picker).to_have_value('1')
    expect(picker).to_be_focused()
    expect(page.locator('#editClassField')).to_be_hidden()
    expect(row).not_to_contain_text('AI')
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    page.locator('#saveSuggestions').click()
    expect(page.locator('#imageList .current')).to_contain_text('Labeled')
    expect(suggest).to_be_disabled()
    page.locator('#undoBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    expect(row).to_have_count(0)
    page.locator('#redoBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('Labeled')
    expect(row).to_contain_text('hex_nut')

    page.locator('#nextBtn').click()
    expect(page.locator('#frameName')).to_have_text('b.png')
    suggest.click()
    expect(page.locator('#suggestStatus')).to_contain_text('No suggestions found')
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    confirm_no_object(page)
    expect(page.locator('#imageList .current')).to_contain_text('No Object')
    page.locator('#backSetupBtn').click()
    with page.expect_download() as exported:
        page.get_by_role('button', name='Download Labeled_data.zip', exact=True).click()
    with zipfile.ZipFile(exported.value.path()) as dataset:
        assert dataset.read('labels/a.txt').split()[0] == b'1'
        assert len(dataset.read('labels/a.txt').split()) == 5
        assert dataset.read('labels/b.txt') == b''
        assert dataset.read('classes.txt') == b'bolt\nhex_nut\n'
    assert not errors, errors
    page.close()
    print('PASS suggestions on the regular workbench, lazy load, class edit, discard, save, undo and export')


def point_preview(browser):
    page = browser.new_page(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    html = Path(__file__).resolve().parents[1] / 'index.html'
    page.route('http://localhost/index.html', lambda route: route.fulfill(
        content_type='text/html', body=html.read_bytes()))
    stub_point_worker(page)
    page.goto('http://localhost/index.html')
    page.locator('#photosInput').set_input_files(
        {'name': 'part.png', 'mimeType': 'image/png', 'buffer': solid_png(320, 240)})
    page.locator('#addClassBtn').tap()
    page.locator('#classList input').fill('bolt')
    page.locator('#saveClassesBtn').tap()
    page.get_by_role('button', name='Start Labeling').tap()
    page.get_by_role('button', name='Click to box', exact=True).tap()
    canvas = page.locator('#canvas')
    rows = page.locator('#boxList .box-row')
    canvas.tap(position={'x': 110, 'y': 80})
    apply_box = page.get_by_role('button', name='Apply box', exact=True)
    expect(apply_box).to_be_visible()
    expect(rows).to_have_count(0)
    page.get_by_role('button', name='Save & exit').tap()
    expect(page.locator('#labeler')).to_be_visible()
    page.get_by_role('button', name='Try another preview').tap()
    expect(page.locator('#pointStatus')).to_contain_text('Preview 2 of 2')
    apply_box.tap()
    expect(rows).to_have_count(1)
    rows.first.get_by_role('button').first.tap()
    page.get_by_role('button', name='Tighten selected box').tap()
    canvas.tap(position={'x': 110, 'y': 80})
    apply_box.tap()
    expect(rows).to_have_count(1)
    page.get_by_role('button', name='Save & exit').tap()
    with page.expect_download() as exported:
        page.get_by_role('button', name='Download Labeled_data.zip', exact=True).tap()
    with zipfile.ZipFile(exported.value.path()) as dataset:
        assert dataset.read('labels/part.txt').split() == [
            b'0', b'0.325000', b'0.375000', b'0.150000', b'0.250000']
    page.close()
    print('PASS point preview, alternate preview, manual apply, refine and ZIP on emulated touch')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', default='chrome')
    with sync_playwright() as playwright, playwright.chromium.launch(channel=parser.parse_args().channel) as browser:
        run(browser)
        point_preview(browser)
