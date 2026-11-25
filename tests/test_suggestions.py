"""Check that model suggestions remain provisional until reviewed."""
import argparse
from pathlib import Path
import zipfile

from playwright.sync_api import expect, sync_playwright

from test_review import solid_png


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
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(site)
    page.locator('#photosInput').set_input_files([
        {'name': name, 'mimeType': 'image/png', 'buffer': solid_png(100, 80)}
        for name in ('a.png', 'b.png')
    ])
    for index, name in enumerate(('bolt', 'hex_nut')):
        page.locator('#addClassBtn').click()
        page.locator('#classList input').nth(index).fill(name)
    page.locator('#saveClassesBtn').click()
    page.get_by_role('button', name='Start Labeling', exact=True).click()

    suggest = page.locator('#suggestBoxes')
    review = page.locator('#suggestReview')
    row = page.locator('#boxList .box-row')
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
    page.locator('#discardSuggestions').click()
    expect(row).to_have_count(0)
    expect(page.locator('#saveState')).to_have_text('Not reviewed')

    suggest.click()
    expect(review).to_be_visible()
    row.get_by_role('button').first.click()
    page.locator('#editClass').select_option('1')
    expect(row).to_contain_text('hex_nut')
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
    page.locator('#noObjectBtn').click()
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
    print('PASS provisional suggestions, discard, edit class, save, undo, empty result and YOLO export')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', default='chrome')
    with sync_playwright() as playwright, playwright.chromium.launch(channel=parser.parse_args().channel) as browser:
        run(browser)
