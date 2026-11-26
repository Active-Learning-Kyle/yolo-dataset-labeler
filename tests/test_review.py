import argparse
import io
import struct
import zipfile
import zlib
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

def solid_png(width, height):
    def chunk(name, data):
        payload = name + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    pixels = (b'\x00' + bytes((52, 107, 171)) * width) * height
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
            + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))


def confirm_no_object(page):
    options = page.locator('#photoOptions')
    if not options.evaluate('details => details.open'):
        options.locator('summary').click()
    options.get_by_role('button', name='Confirm no object').click()
    page.locator('#savePhotoBtn').click()


def check_unlabeled_review(browser, site):
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    page.goto(site)
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        archive.writestr('classes.txt', 'bolt\n')
        for name in ('a.png', 'b.png', 'c.png'):
            archive.writestr('images/' + name, solid_png(400, 300))
        archive.writestr('labels/c.txt', '')
    page.locator('#zipImagesInput').set_input_files(
        {'name': 'review.zip', 'mimeType': 'application/zip', 'buffer': data.getvalue()})
    page.get_by_role('button', name='Label remaining photos (2)').click()
    expect(page.locator('#frameName')).to_have_text('a.png')
    canvas = page.locator('#canvas')
    expect(canvas).to_be_visible()
    rect = canvas.bounding_box()
    page.mouse.move(rect['x'] + 30, rect['y'] + 30)
    page.mouse.down()
    page.mouse.move(rect['x'] + 130, rect['y'] + 140)
    page.mouse.up()
    expect(page.locator('#saveState')).to_contain_text('Unsaved draft')
    expect(page.locator('#imageList .current')).to_have_text('a.pngUnlabeled')
    expect(page.locator('#imageCount')).to_have_text('2')
    expect(page.locator('#progressText')).to_contain_text('Reviewed 1 · Remaining 2')

    expect(page.locator('#nextBtn')).to_be_disabled()
    page.locator('#savePhotoBtn').click()
    expect(page.locator('#imageCount')).to_have_text('1')
    page.locator('#nextBtn').click()
    expect(page.locator('#frameName')).to_have_text('b.png')
    expect(page.locator('.toolbar').get_by_role('button', name='Confirm no object')).to_have_count(0)
    expect(page.locator('#noObjectBtn')).to_be_hidden()
    confirm_no_object(page)
    expect(page.locator('#saveState')).to_contain_text('Saved')
    expect(page.locator('#imageCount')).to_have_text('0')
    page.locator('#statusFilter').select_option('all')
    page.locator('#prevBtn').click()
    expect(page.locator('#frameName')).to_have_text('a.png')
    expect(page.locator('#boxList .box-row')).to_have_count(1)

    page.get_by_role('button', name='Finish & exit', exact=True).click()
    expect(page.locator('#reviewExportTitle')).to_be_focused()
    expect(page.locator('#completionCard')).to_contain_text('No-object images: 2')
    expect(page.locator('#remainingBtn')).to_be_hidden()
    with page.expect_download() as pending:
        page.locator('#trainingZipBtn').click()
    with zipfile.ZipFile(pending.value.path()) as archive:
        assert len(archive.read('labels/a.txt').split()) == 5
        assert archive.read('labels/b.txt') == b''
    page.close()
    print('PASS explicit save, unlabeled filter, navigation and completed export')


def validate_review(browser, site):
    page = browser.new_page(viewport={'width':820, 'height':1024}, has_touch=True)
    page.goto(site)
    sample = solid_png(400, 300)
    def upload(entries):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            for name, content in entries.items():
                z.writestr(name, content)
        page.locator('#zipImagesInput').set_input_files({'name':'review.zip','mimeType':'application/zip','buffer':data.getvalue()})
    def reset():
        page.reload()
    page.locator('#photosInput').set_input_files({
        'name':'sample.heic', 'mimeType':'image/heic', 'buffer':b'sample'})
    expect(page.get_by_role('alert')).to_contain_text('Choose JPG')
    img = {'images/a.png':sample, 'classes.txt':'blue_disc\n'}
    upload({})
    expect(page.get_by_role('alert')).to_contain_text('No supported images')
    expect(page.locator('#landing')).to_be_visible()
    upload({**img,'labels/missing.txt':''})
    expect(page.get_by_role('alert')).to_contain_text('matching image')
    upload({**img,'labels/a.txt':'7 0.5 0.5 0.2 0.2'})
    expect(page.locator('#summaryIssues')).to_contain_text('a.png')
    expect(page.locator('#trainingZipBtn')).to_be_hidden()
    page.get_by_role('button', name='Review invalid files').click()
    expect(page.locator('#statusFilter')).to_have_value('invalid')
    reset()
    upload({**img,'images/b.png':sample,'labels/b.txt':''})
    expect(page.locator('#datasetName')).to_contain_text('review')
    ambiguous = io.BytesIO()
    with zipfile.ZipFile(ambiguous, 'w') as z:
        for name, value in {'classes.txt':'blue_disc\n', 'images/x.png':sample,
                            'images/X.jpg':sample, 'labels/x.txt':''}.items():
            z.writestr(name, value)
    with page.expect_file_chooser() as picker:
        page.get_by_role('button', name='Import labeled ZIP').click()
    picker.value.set_files({
        'name':'ambiguous.zip', 'mimeType':'application/zip', 'buffer':ambiguous.getvalue()})
    expect(page.get_by_role('alert')).to_contain_text('one matching image')
    expect(page.locator('#summaryStats .stat').first).to_have_text('2Images')
    expect(page.locator('#summaryDraftBtn')).to_be_hidden()
    page.locator('#classList input').fill('disc')
    page.locator('#saveClassesBtn').click()
    with page.expect_download() as draft:
        page.locator('#summaryDraftBtn').click()
    assert draft.value.suggested_filename == 'Labeler-draft.zip'
    page.locator('#confirmDownload').click()
    expect(page.locator('#summaryDraftBtn')).to_be_hidden()
    page.get_by_role('button',name='Label remaining photos (1)',exact=True).click()
    expect(page.locator('#statusFilter')).to_have_value('unlabeled')
    expect(page.locator('#imageList .image-item')).to_have_count(1)
    page.locator('#backSetupBtn').click()
    page.get_by_role('button', name='Exit to review').click()
    page.get_by_role('button',name='Review all photos',exact=True).click()
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    expect(page.locator('#nextBtn')).to_be_disabled()
    confirm_no_object(page)
    page.locator('#nextBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('No Object')
    page.locator('#prevBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('No Object')
    page.locator('#undoBtn').click()
    expect(page.locator('#saveState')).to_contain_text('Unsaved draft')
    page.locator('#redoBtn').click()
    expect(page.locator('#savePhotoBtn')).to_be_disabled()
    page.locator('#undoBtn').click()
    page.locator('#savePhotoBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    page.locator('#statusFilter').select_option('background')
    expect(page.locator('#imageList .image-item')).to_have_count(1)
    expect(page.locator('#imageList')).to_contain_text('b.png')
    page.locator('#statusFilter').select_option('all')
    page.locator('#canvas').scroll_into_view_if_needed()
    cdp = page.context.new_cdp_session(page)
    def drag(points):
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[points[0]]})
        for pt in points[1:]:
            cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[pt]})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    def points(fractions):
        r=page.locator('#canvasWrap').bounding_box()
        return [{'x':r['x']+x*r['width'],'y':r['y']+y*r['height']} for x,y in fractions]
    drag(points([(.30,.42),(.38,.48),(.46,.55)]))
    expect(page.locator('#boxList button').filter(has_text='Delete')).to_have_count(1)
    page.locator('#zoomIn').tap()
    expect(page.locator('#zoomFit')).to_have_text('150%')
    page.locator('#panTool').tap()
    drag(points([(.63,.62),(.55,.55),(.42,.48)]))
    assert page.locator('#canvasWrap').evaluate('e => e.scrollTop + e.scrollLeft')>0
    expect(page.locator('#boxList button').filter(has_text='Delete')).to_have_count(1)
    page.locator('#zoomFit').tap()
    for w,h in [(820,1024),(1024,820)]:
        page.set_viewport_size({'width':w,'height':h})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.close()
    print('PASS format hint, rejected ambiguous merge, empty ZIP, orphan label, invalid class, blocked export, background undo, status filter, touch-drag box and pan, portrait/landscape bounds',flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check label review, export guards and touch controls.')
    parser.add_argument('--channel', default='chrome', choices=['chrome', 'msedge', 'chromium'])
    parser.add_argument('--executable', help='Optional path to a local browser binary.')
    args = parser.parse_args()
    site = (Path(__file__).resolve().parents[1] / 'index.html').as_uri()
    with sync_playwright() as pw:
        launch = {'executable_path': args.executable} if args.executable else {'channel': args.channel}
        browser = pw.chromium.launch(**launch)
        validate_review(browser, site)
        check_unlabeled_review(browser, site)
        browser.close()
