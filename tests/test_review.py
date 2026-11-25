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
    page.get_by_role('button',name='Download Labeled_data.zip',exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('Export blocked')
    reset()
    upload({**img,'images/b.png':sample,'labels/b.txt':''})
    expect(page.locator('#datasetName')).to_contain_text('review')
    ambiguous = io.BytesIO()
    with zipfile.ZipFile(ambiguous, 'w') as z:
        for name, value in {'classes.txt':'blue_disc\n', 'images/x.png':sample,
                            'images/X.jpg':sample, 'labels/x.txt':''}.items():
            z.writestr(name, value)
    page.locator('#zipInput').set_input_files({
        'name':'ambiguous.zip', 'mimeType':'application/zip', 'buffer':ambiguous.getvalue()})
    expect(page.get_by_role('alert')).to_contain_text('one matching image')
    expect(page.locator('#summaryStats .stat').first).to_have_text('2Images')
    page.get_by_text('Start Labeling',exact=True).click()
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    page.locator('#nextBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('No Object')
    page.locator('#prevBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    page.locator('#noObjectBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('No Object')
    page.locator('#undoBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    page.locator('#redoBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('No Object')
    page.locator('#undoBtn').click()
    expect(page.locator('#imageList .current')).to_contain_text('Unlabeled')
    page.locator('#statusFilter').select_option('background')
    expect(page.locator('#imageList button')).to_have_count(1)
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
        browser.close()
