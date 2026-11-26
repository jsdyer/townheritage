"""Exercise synthetic records in an isolated copy; fixtures never enter dist/."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


def fixture():
    records=[]
    for index,title in enumerate(['Harbour study','<img src=x onerror=alert(1)>']):
        records.append({'id':f'/test/{index}','title':title,'type':'IMAGE','years':[1925] if not index else [],'dateText':[],'institutions':['Example museum'],'creators':['A. Example'],'description':['A synthetic test record.'],'aggregators':['Test source'],'providerCountries':['Netherlands'],'places':['Test place'],'rights':[{'label':'CC0','url':'https://creativecommons.org/publicdomain/zero/1.0/'}],'thumbnail':'','source':'https://example.org/record','original':'','europeana':'https://www.europeana.eu/item/test/0','collections':['test-place']})
    return {'version':1,'capturedAt':'2026-11-25T12:00:00+00:00','requests':1,'collections':[{'id':'test-place','title':'Test place','query':'test place','note':'Synthetic test only.','included':2,'totalMatches':10}],'records':records}


def main():
    with tempfile.TemporaryDirectory() as temporary:
        site=Path(temporary)/'townheritage'
        shutil.copytree(ROOT/'dist',site)
        (site/'data/europeana.json').write_text(json.dumps(fixture()))
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temporary))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch()
                page=browser.new_page(viewport={'width':1280,'height':1000})
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/townheritage/')
                page.locator('.card').first.wait_for()
                assert page.locator('.card').count()==2
                assert page.locator('meta[name="robots"]').get_attribute('content')=='noindex,nofollow,noarchive'
                page.locator('#query').fill('Harbour')
                assert page.locator('.card').count()==1
                page.get_by_role('button',name='Save Harbour study',exact=True).click()
                assert page.locator('#saved-count').inner_text()=='1'
                page.reload()
                page.locator('.card').first.wait_for()
                assert page.locator('#saved-count').inner_text()=='1'
                page.get_by_role('button',name='Open Harbour study',exact=True).click()
                assert page.locator('#record-dialog').is_visible()
                assert 'keyword match' in page.locator('#record-content').inner_text().lower()
                page.locator('#close-dialog').click()
                page.locator('#reset').click()
                page.locator('#query').fill('<img')
                assert page.locator('.card').count()==1
                assert page.locator('.card img').count()==0
                page.locator('#reset').click()
                page.get_by_role('button',name='1920s (1)',exact=True).click()
                assert page.locator('.card').count()==1
                assert 'decade=1920' in page.url
                page.locator('#saved-toggle').click()
                assert page.locator('.card').count()==1
                with page.expect_download() as download:
                    page.locator('#export').click()
                assert download.value.suggested_filename=='town-heritage-citations.txt'
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                assert not errors,errors
                browser.close()
        finally:
            server.shutdown()
    print('Browser checks passed: filtering, rights, saved records, citations, safe text, subpath and mobile layout')


if __name__=='__main__':main()
