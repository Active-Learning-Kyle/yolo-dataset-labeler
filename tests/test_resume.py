"""Exercise manual review and reload recovery in desktop and touch Chrome."""

from pathlib import Path
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from test_review import solid_png


HTML = Path(__file__).resolve().parents[1] / 'index.html'


def read_recovery(page, **expected):
    page.wait_for_function('''expected => new Promise(resolve => {
      const db = indexedDB.open('yolo-labeler-workspace');
      db.onsuccess = () => {
        const request = db.result.transaction('session').objectStore('session').get('recent');
        request.onsuccess = () => {
          db.result.close();
          const session = request.result;
          const actual = session && {...session, firstClass: session.classes?.[0], drafts: session.drafts.size};
          resolve(actual && Object.entries(expected).every(([key, value]) => actual[key] === value));
        };
      };
      db.onerror = () => resolve(false);
    })''', arg=expected)


def draw(page, touch):
    canvas = page.locator('#canvas')
    canvas.scroll_into_view_if_needed()
    frame = canvas.bounding_box()
    x = frame['x'] + frame['width'] * .2
    y = frame['y'] + frame['height'] * .2
    last_x = frame['x'] + frame['width'] * .6
    last_y = frame['y'] + frame['height'] * .6
    if touch:
        cdp = page.context.new_cdp_session(page)
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': last_x, 'y': last_y}]})
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        cdp.detach()
    else:
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(last_x, last_y, steps=4)
        page.mouse.up()


def run(browser, touch, url=HTML.as_uri()):
    size = {'width': 390, 'height': 844} if touch else {'width': 1280, 'height': 860}
    page = browser.new_page(viewport=size, is_mobile=touch, has_touch=touch, accept_downloads=True)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def press(selector):
        button = page.locator(selector)
        button.tap() if touch else button.click()

    page.goto(url)
    page.locator('#photosInput').set_input_files([
        {'name': name, 'mimeType': 'image/png', 'buffer': solid_png(200, 140)}
        for name in ('a.png', 'b.png')
    ])
    press('#addClassBtn')
    page.locator('#classList input').fill('bolt')
    read_recovery(page, firstClass='bolt')
    page.reload()
    press('#resumeBtn')
    expect(page.locator('#classList input')).to_have_value('bolt')
    press('#saveClassesBtn')
    press('#labelAllBtn')
    expect(page.locator('#frameName')).to_have_text('a.png')
    expect(page.locator('#canvas')).to_be_visible()
    expect(page.locator('#nextBtn')).to_be_disabled()
    if touch:
        expect(page.locator('#imageBrowser')).to_be_visible()
        expect(page.locator('#imageCount')).to_have_text('2')
        expect(page.get_by_role('button', name='Hide images', exact=False)).to_have_count(0)
    draw(page, touch)
    expect(page.locator('#boxList .box-row')).to_have_count(1)
    expect(page.locator('#progressText')).to_contain_text('Reviewed 0')
    expect(page.locator('#nextBtn')).to_be_disabled()
    if touch:
        expect(page.locator('#imageBrowser')).to_be_visible()
    read_recovery(page, current='a.png', drafts=1)
    page.reload()
    press('#resumeBtn')
    expect(page.locator('#frameName')).to_have_text('a.png')
    expect(page.locator('#boxList .box-row')).to_have_count(1)
    expect(page.locator('#saveState')).to_contain_text('Unsaved draft')
    expect(page.locator('#nextBtn')).to_be_disabled()
    if touch:
        expect(page.locator('#imageBrowser')).to_be_visible()
    press('#backSetupBtn')
    expect(page.locator('#finishMessage')).to_have_text('2 photos still need review. Unsaved edits will stay as drafts in this workspace.')
    press('#finishDialog button[value=continue]')
    expect(page.locator('#labeler')).to_be_visible()
    press('#backSetupBtn')
    press('#finishDialog button[value=exit]')
    expect(page.locator('#setup')).to_be_visible()
    expect(page.locator('#trainingZipBtn')).to_be_hidden()
    expect(page.locator('#summaryIssues')).to_contain_text('1 photo has an unsaved draft')
    press('#labelAllBtn')
    expect(page.locator('#boxList .box-row')).to_have_count(1)
    press('#savePhotoBtn')
    expect(page.locator('#progressText')).to_contain_text('Reviewed 1')
    press('#nextBtn')
    expect(page.locator('#frameName')).to_have_text('b.png')
    if touch:
        expect(page.locator('#imageBrowser')).to_be_visible()
        gap = page.evaluate('''() => {
          window.scrollTo(0, document.documentElement.scrollHeight * 2);
          return {
            bottom: innerHeight - document.querySelector('.right-panel').getBoundingClientRect().bottom,
            overscroll: getComputedStyle(document.documentElement).overscrollBehaviorY,
          };
        }''')
        assert 0 <= gap['bottom'] <= 10 and gap['overscroll'] == 'none', gap
    press('#photoOptions summary')
    press('#noObjectBtn')
    expect(page.locator('#progressText')).to_contain_text('Reviewed 1')
    press('#savePhotoBtn')
    expect(page.locator('#progressText')).to_contain_text('Reviewed 2')
    press('#backSetupBtn')
    expect(page.locator('#finishDialog')).to_be_hidden()
    expect(page.locator('#setup')).to_be_visible()
    with page.expect_download() as download:
        press('#trainingZipBtn')
    with ZipFile(download.value.path()) as archive:
        assert archive.testzip() is None
        assert archive.read('classes.txt') == b'bolt\n'
        assert archive.read('labels/a.txt').startswith(b'0 ')
        assert archive.read('labels/b.txt') == b''
    press('#confirmDownload')
    expect(page.locator('#trainingStep a')).to_have_attribute('href', 'https://colab.research.google.com/')
    press('#dismissDownload')
    read_recovery(page, view='setup', drafts=0)
    page.reload()
    press('#resumeBtn')
    expect(page.locator('#trainingZipBtn')).to_be_visible()
    press('#resetBtn')
    expect(page.locator('#landing')).to_be_visible()
    expect(page.locator('#resumeBtn')).to_be_visible()
    page.once('dialog', lambda dialog: dialog.accept())
    press('#forgetResumeBtn')
    expect(page.locator('#resumeBtn')).to_be_hidden()
    assert not errors, errors
    print('PASS', 'touch' if touch else 'desktop', 'save, review, local storage and ZIP round trip')
    page.context.close()


if __name__ == '__main__':
    with sync_playwright() as playwright, playwright.chromium.launch(channel='chrome') as browser:
        run(browser, touch=False)
        run(browser, touch=True)
