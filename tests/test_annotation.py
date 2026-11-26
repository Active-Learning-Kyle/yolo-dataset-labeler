"""Regression checks for overlapping classes, focus, history, and phone photo imports."""
import argparse
import io
import zipfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from test_review import confirm_no_object, solid_png


def check_session(browser, site, width, height, touch):
    context = browser.new_context(viewport={'width': width, 'height': height}, has_touch=touch, is_mobile=touch)
    page = context.new_page()
    page.set_default_timeout(8000)
    notebook = 'example_notebook_id'
    fragment = {320: '#notebook=' + notebook, 390: '#notebook=https://example.org'}.get(width, '')
    page.goto(site + fragment)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    cdp = context.new_cdp_session(page) if touch and browser.browser_type.name == 'chromium' else None
    canvas = page.locator('#canvas')
    rows = page.locator('#boxList .box-row')

    def click(selector):
        control = page.locator(selector)
        control.tap() if touch else control.click()

    def drag(start, finish):
        canvas.scroll_into_view_if_needed()
        rect = canvas.bounding_box()
        def point(pair):
            return {'x': rect['x'] + rect['width'] * pair[0], 'y': rect['y'] + rect['height'] * pair[1]}
        first, last = point(start), point(finish)
        if cdp:
            cdp.send('Input.dispatchTouchEvent', {'type':'touchStart', 'touchPoints':[first]})
            cdp.send('Input.dispatchTouchEvent', {'type':'touchMove', 'touchPoints':[last]})
            cdp.send('Input.dispatchTouchEvent', {'type':'touchEnd', 'touchPoints':[]})
        else:
            page.mouse.move(**first)
            page.mouse.down()
            page.mouse.move(**last, steps=4)
            page.mouse.up()

    def read_zip(action):
        with page.expect_download() as pending:
            action()
        with zipfile.ZipFile(pending.value.path()) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    first = {'name':'OIP.png', 'mimeType':'image/png', 'buffer':solid_png(400,300)}
    second = {**first, 'buffer':solid_png(320,240)}
    page.locator('#photosInput').set_input_files(first)
    expect(page.locator('#datasetName')).to_contain_text('Selected photos')
    click('#addClassBtn')
    page.locator('#classList input').nth(0).fill('disc')
    click('#addClassBtn')
    page.locator('#classList input').nth(1).fill('plate')
    click('#saveClassesBtn')
    expect(page.locator('#classSelect option')).to_have_count(2)
    page.locator('#photosInput').set_input_files(second)
    expect(page.get_by_text('1 photo(s) added. 1 renamed to keep both copies.')).to_be_visible()
    page.get_by_role('button',name='Start Labeling',exact=True).click()
    expect(page.locator('#frameName')).to_have_text('OIP.png')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    if width < 761:
        expect(page.locator('#imageBrowser')).to_be_hidden()
        click('#browseImages')
        expect(page.locator('#imageBrowser')).to_be_visible()
        click('#browseImages')
        assert canvas.bounding_box()['width'] > width * .83

    drag((.10,.10),(.80,.80))
    expect(rows).to_have_count(1)
    page.locator('#classSelect').select_option('1')
    expect(rows.nth(0)).to_contain_text('0: disc')
    drag((.3,.3),(.55,.55))
    expect(rows).to_have_count(2)
    expect(rows.nth(1)).to_contain_text('1: plate')
    # Canvas pixels, not just the list, must update on the first undo.
    before = canvas.evaluate('c=>c.toDataURL()')
    page.locator('#classSelect').focus()
    page.keyboard.press('Control+z')
    expect(rows).to_have_count(1)
    assert canvas.evaluate('c=>c.toDataURL()') != before
    click('#redoBtn')
    expect(rows).to_have_count(2)
    click('#editTool')
    drag((.42,.42),(.42,.42))
    click('#undoBtn')
    expect(rows).to_have_count(1)
    click('#redoBtn')
    rows.nth(1).get_by_role('button').first.click()
    page.locator('#editClass').select_option('0')
    expect(rows.nth(1)).to_contain_text('0: disc')
    expect(page.locator('#classSelect')).to_have_value('1')
    click('#undoBtn')
    expect(rows.nth(1)).to_contain_text('1: plate')
    rows.nth(1).get_by_role('button').first.click()
    drag((.42,.42),(.51,.50))
    drag((.64,.63),(.71,.71))
    draft = read_zip(lambda: click('#draftBtn'))
    expect(page.locator('#trainingStep')).to_be_hidden()
    click('#dismissDownload')
    # Dismissing the download prompt must retain the unsaved-session warning.
    assert page.evaluate("""() => {
        const event = new Event('beforeunload', {cancelable:true});
        return !window.dispatchEvent(event);
    }""")
    lines = draft['labels/OIP.txt'].decode().splitlines()
    assert [line.split()[0] for line in lines] == ['0','1']
    assert float(lines[1].split()[3]) > .28
    assert 'labels/OIP_imported_2.txt' not in draft
    assert draft['images/OIP.png'] == first['buffer']
    assert draft['images/OIP_imported_2.png'] == second['buffer']
    draft_bytes = io.BytesIO()
    with zipfile.ZipFile(draft_bytes, 'w') as archive:
        for name, data in draft.items():
            archive.writestr(name, data)
    restored = context.new_page()
    restored.goto(site)
    restored.locator('#zipImagesInput').set_input_files({
        'name':'Labeler-draft.zip', 'mimeType':'application/zip', 'buffer':draft_bytes.getvalue()})
    restored.get_by_role('button', name='Review all photos', exact=True).click()
    expect(restored.locator('#boxList .box-row')).to_have_count(2)
    restored.locator('#nextBtn').click()
    expect(restored.locator('#saveState')).to_have_text('Not reviewed')
    restored.close()

    click('#nextBtn')
    expect(page.locator('#frameName')).to_have_text('OIP_imported_2.png')
    expect(page.locator('#undoBtn')).to_be_disabled()
    click('#prevBtn')
    expect(page.locator('#undoBtn')).to_be_enabled()
    click('#undoBtn')
    click('#redoBtn')
    click('#nextBtn')
    confirm_no_object(page)
    click('#backSetupBtn')
    expect(page.get_by_role('heading', name='3. Review & export')).to_be_in_viewport()
    complete = read_zip(lambda: page.get_by_role('button',name='Download Labeled_data.zip',exact=True).click())
    expect(page.locator('#trainingStep')).to_be_hidden()
    click('#confirmDownload')
    expect(page.get_by_role('link', name='Continue to Training in Colab')).to_have_attribute(
        'href', 'https://colab.research.google.com/' + ('drive/' + notebook if width == 320 else ''))
    assert complete['classes.txt'].splitlines() == [b'disc', b'plate']
    assert complete['labels/OIP_imported_2.txt'] == b''
    assert complete['labels/OIP.txt'] == draft['labels/OIP.txt']
    # Reopen the download as a new student session.
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, 'w') as archive:
        for name, data in complete.items():
            archive.writestr(name, data)
    page.reload()
    page.locator('#zipImagesInput').set_input_files({'name':'Labeled_data.zip','mimeType':'application/zip','buffer':zipped.getvalue()})
    expect(page.locator('#completionCard')).to_contain_text('No-object images: 1')
    assert not errors, errors
    context.close()
    print(f'PASS {width}x{height} touch={touch}: overlapping classes, undo, explicit reclassification, resize, duplicate photos, draft, export and reopen', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable')
    parser.add_argument('--channel', default='chrome', choices=['chrome','msedge','chromium','webkit'])
    args = parser.parse_args()
    site = (Path(__file__).resolve().parents[1] / 'index.html').as_uri()
    with sync_playwright() as pw:
        options = {'executable_path':args.executable} if args.executable else {'channel':args.channel}
        browser = pw.webkit.launch() if args.channel == 'webkit' else pw.chromium.launch(**options)
        for dimensions in ((1440,900,False),(320,568,True),(390,844,True),(844,390,True),(820,1024,True)):
            check_session(browser,site,*dimensions)
        browser.close()
