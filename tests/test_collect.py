import copy
import contextlib
import io
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('collector', ROOT / 'scripts/collect.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
spec2 = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build.py')
b = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(b)


def item(**updates):
    return {'id':'/123/test', 'title':['Harbour study'], 'rights':['http://creativecommons.org/publicdomain/zero/1.0/'], 'year':['1925','unknown'], 'dataProvider':['Example museum'], 'country':['Netherlands'], 'edmPreview':['https://example.org/image.jpg'], **updates}


def config():
    return {'rows_per_collection':10,'request_interval_seconds':2,'collections':[{'id':'a','title':'First place','query':'example','note':'Keyword matches.'}]}


class CollectorTests(unittest.TestCase):
    def test_recognizes_only_open_rights_and_rejects_mixed(self):
        self.assertEqual(c.normalize(item())['rights'][0]['label'],'CC0')
        self.assertIsNone(c.normalize(item(rights=['https://creativecommons.org/licenses/by-nc/4.0/'])))
        self.assertIsNone(c.normalize(item(rights=['https://creativecommons.org/licenses/by/4.0/','https://rightsstatements.org/vocab/InC/1.0/'])))
        self.assertIsNone(c.normalize(item(rights=['https://creativecommons.org.evil.example/publicdomain/zero/1.0/'])))

    def test_only_safe_public_links(self):
        for url in ['javascript:alert(1)','http://example.org/x','https://user:password@example.org','https://example.org/?wskey=secret','https://example.org/?api_key=secret']:
            self.assertEqual(c.safe_url(url),'')
        self.assertEqual(c.safe_url('https://example.org/x'),'https://example.org/x')

    def test_whitelist_does_not_retain_echoed_credentials(self):
        result=c.normalize(item(apikey='SECRET',params={'wskey':'SECRET'}),'SECRET')
        self.assertNotIn('SECRET',json.dumps(result))
        self.assertNotIn('apikey',result)
        with self.assertRaises(ValueError):
            c.normalize(item(title=['SECRET']),'SECRET')

    def test_date_and_geography_are_not_inferred(self):
        result=c.normalize(item())
        self.assertEqual(result['years'],[1925])
        self.assertEqual(result['providerCountries'],['Netherlands'])
        self.assertEqual(result['places'],[])
        self.assertNotIn('latitude',result)

    def test_dedup_and_configuration_expansion(self):
        cfg=config(); cfg['collections'].append({'id':'new-town','title':'New town','query':'another town','note':'A newly configured collection.'})
        payload={'success':True,'items':[item()],'totalResults':25,'apikey':'SECRET'}
        result=c.collect(cfg,'SECRET',lambda *args:payload,lambda delay:None)
        self.assertEqual(len(result['records']),1)
        self.assertEqual(result['records'][0]['collections'],['a','new-town'])
        self.assertEqual(result['requests'],2)
        self.assertEqual(result['collections'][1]['totalMatches'],25)
        self.assertNotIn('SECRET',json.dumps(result))

    def test_empty_overall_fails(self):
        with self.assertRaisesRegex(ValueError,'No reusable records'):
            c.collect(config(),'SECRET',lambda *args:{'items':[],'totalResults':0},lambda delay:None)

    def test_bad_limits_fail(self):
        for rows in [0,101,True]:
            cfg=config();cfg['rows_per_collection']=rows
            with self.assertRaises(ValueError): c.validate_config(cfg)

    def test_http_error_never_echoes_key_or_body(self):
        with patch.object(c,'build_opener') as opener:
            opener.return_value.open.side_effect=HTTPError('https://api.europeana.eu?wskey=SECRET',429,'SECRET',{},None)
            with self.assertRaises(ValueError) as caught: c.fetch('town',5,'SECRET')
            self.assertIn('429',str(caught.exception))
            self.assertNotIn('SECRET',str(caught.exception))

    def test_echoed_key_never_reaches_published_files_or_logs(self):
        key = 'FAKE_EUROPEANA_CANARY_824692'
        payload = {'success': True, 'apikey': key, 'params': {'wskey': key},
                   'items': [item(apikey=key)], 'totalResults': 1}
        logs = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
            root = Path(tmp)
            (root / 'web').mkdir()
            (root / 'web/index.html').write_text('<meta name="robots" content="noindex">')
            (root / 'data').mkdir()
            with patch.object(c, 'build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
                capture = c.collect(config(), key, c.fetch, lambda delay: None)
            (root / 'data/europeana.json').write_text(json.dumps(capture))
            b.build(root, True)
            for path in (root / 'dist').rglob('*'):
                if path.is_file():
                    self.assertNotIn(key.encode(), path.read_bytes(), str(path.relative_to(root)))
            self.assertNotIn(key, logs.getvalue())

    def test_unsuccessful_json_echo_is_not_logged(self):
        key = 'FAKE_EUROPEANA_ERROR_CANARY_59637'
        for payload in ({'success': False, 'apikey': key, 'error': key},
                        {'success': True, 'items': key, 'apikey': key}):
            with patch.object(c, 'build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
                with self.assertRaises(ValueError) as caught:
                    c.fetch('town', 5, key)
                self.assertNotIn(key, str(caught.exception))

    def test_key_in_header_not_query(self):
        with patch.object(c,'build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.read.return_value=b'{"success":true,"items":[],"totalResults":0}'
            c.fetch('a town',5,'SECRET')
            request=opener.return_value.open.call_args.args[0]
            self.assertNotIn('SECRET',request.full_url)
            self.assertEqual(request.get_header('X-api-key'),'SECRET')
            self.assertIn('reusability=open',request.full_url)

    def test_unconfigured_build_and_release_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'web').mkdir();(root/'web/index.html').write_text('<meta name="robots" content="noindex">')
            b.build(root)
            self.assertIsNone(json.loads((root/'dist/data/europeana.json').read_text())['capturedAt'])
            self.assertFalse((root/'dist/sitemap.xml').exists())
            with self.assertRaises(ValueError): b.build(root,True)


if __name__=='__main__':unittest.main()
