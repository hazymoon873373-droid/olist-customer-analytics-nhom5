"""Validate private Power BI URLs and the HTTPS embedding boundary."""
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from powerbi_embed import secure_embed_url, can_embed, render_secure_powerbi
from streamlit.testing.v1 import AppTest

REPORT = '15d6ef88-37c3-4dd5-a819-f6e289569d99'
URL = 'https://app.powerbi.com/reportEmbed?reportId=' + REPORT


class PowerBIEmbedTests(unittest.TestCase):
    def test_private_report_is_normalized(self):
        parsed = urlsplit(secure_embed_url(URL))
        self.assertEqual(parsed.hostname,'app.powerbi.com')
        self.assertEqual(parse_qs(parsed.query),{'reportId':[REPORT],'autoAuth':['true']})

    def test_public_links_tokens_and_untrusted_hosts_rejected(self):
        for value in [
            'https://app.powerbi.com/view?r=public-code',
            URL.replace('https:', 'http:'), URL.replace('app.powerbi.com','app.powerbi.com.evil.example'),
            URL.replace('app.powerbi.com','attacker@app.powerbi.com'), URL+'#fragment',
            URL+'&access_token=secret',URL+'&reportId='+REPORT, URL.replace(REPORT,'invalid-id'),
            URL.replace('app.powerbi.com','app.powerbi.com:444'),URL+'&$filter=region',
        ]:
            with self.subTest(value=value),self.assertRaises(ValueError): secure_embed_url(value)

    def test_http_host_cannot_embed_secure_report(self):
        self.assertFalse(can_embed('http://localhost:8501'))
        self.assertTrue(can_embed('https://olist.example.com'))

    def test_missing_configuration_has_no_fake_iframe(self):
        app=AppTest.from_string('from powerbi_embed import render_secure_powerbi\nrender_secure_powerbi()')
        with patch.dict('os.environ',{'OLIST_POWERBI_EMBED_URL':''}): app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        self.assertFalse(app.get('iframe'))

    def test_render_on_http_only_offers_authenticated_link(self):
        with patch('powerbi_embed.st') as ui:
            ui.context.url='http://localhost:8501'
            render_secure_powerbi(URL)
        ui.iframe.assert_not_called()
        ui.link_button.assert_called_once()
        ui.warning.assert_called_once()

    def test_render_on_https_uses_only_validated_private_endpoint(self):
        with patch('powerbi_embed.st') as ui:
            ui.context.url='https://olist.example.com'
            render_secure_powerbi(URL)
        self.assertEqual(ui.iframe.call_args.args[0],secure_embed_url(URL))
        self.assertIn('Microsoft',ui.iframe.call_args.kwargs['alt'])

if __name__=='__main__': unittest.main()
