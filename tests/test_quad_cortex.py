"""Offline inventory and QC compatibility contracts."""
import unittest
from types import SimpleNamespace

from tools.import_quad_cortex import parse_device_list


class InventoryParserTests(unittest.TestCase):
    def test_native_and_plugin_requirements_remain_distinct(self):
        html = '''<table aria-label="Guitar amps"><thead><tr>
        <th>Name<span aria-hidden="true">i</span></th><th>Based on</th><th>Added in CorOS</th>
        </tr></thead><tbody><tr><td>Clean &amp; Bright</td><td>Example</td><td>1.0.0</td></tr></tbody></table>
        <table aria-label="Plugin devices"><tr><th>Device category</th><th>Name</th>
        <th>Added in CorOS</th><th>Required plugin</th></tr><tr><td>Guitar amps</td>
        <td>Clean &amp; Bright</td><td>3.0.0</td><td><a href="/plugins/x">Example X</a></td></tr></table>'''
        rows = parse_device_list(html)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['name'], 'Clean & Bright')
        self.assertEqual(rows[0]['kind'], 'native')
        self.assertEqual(rows[1]['required_plugin'], 'Example X')
        self.assertNotEqual(rows[0]['id'], rows[1]['id'])

    def test_same_plugin_block_name_can_belong_to_distinct_plugins(self):
        html = '<table aria-label="Plugin devices"><tr><th>Device category</th><th>Name</th><th>Added in CorOS</th><th>Required plugin</th></tr>'
        html += ''.join(f'<tr><td>Compressor</td><td>Compressor</td><td>4.1.0</td><td>{plugin}</td></tr>' for plugin in ('Example X', 'Another X'))
        rows = parse_device_list(html + '</table>')
        self.assertEqual(len({row['id'] for row in rows}), 2)

    def test_changed_markup_and_missing_requirements_fail_closed(self):
        for html in ('<p>No inventory</p>',
                     '<table aria-label="Guitar amps"><tr><th>Name</th></tr><tr><td>X</td></tr></table>',
                     '<table aria-label="Plugin devices"><tr><th>Name</th><th>Added in CorOS</th></tr><tr><td>X</td><td>3.0.0</td></tr></table>'):
            with self.subTest(html=html), self.assertRaises(ValueError):
                parse_device_list(html)

    def test_announced_models_are_not_treated_as_released(self):
        rows = parse_device_list('<table aria-label="Announced devices that have not yet been released"><tr><th>Device Category</th><th>Based On</th><th>Device Name</th></tr><tr><td>Bass amps</td><td>Example</td><td>Future amp</td></tr></table>')
        self.assertEqual(rows[0]['kind'], 'announced')
        self.assertIsNone(rows[0]['added_in'])


class QuadCortexRecipeTests(unittest.TestCase):
    def test_snapshot_is_complete_and_requirements_are_preserved(self):
        from quad_cortex import load_catalog, eligible_native
        rows = load_catalog()['devices']
        self.assertEqual(len(rows), 689)
        self.assertEqual(len({r['id'] for r in rows}), len(rows))
        self.assertEqual(sum(r['kind'] == 'announced' for r in rows), 57)
        self.assertTrue(all(r['required_plugin'] for r in rows if r['kind'] == 'plugin'))
        self.assertFalse(any(eligible_native(r, '4.1.1') for r in rows if r['kind'] != 'native'))
        late = next(r for r in rows if r['kind'] == 'native' and r['name'] == 'Dumbbell ODS')
        self.assertFalse(eligible_native(late, '3.2.0'))
        self.assertTrue(eligible_native(late, '3.3.0'))

    def test_recipes_use_official_native_blocks_and_safe_routes(self):
        from quad_cortex import recipes, load_catalog
        f = SimpleNamespace(saturation=.4, brightness=.5, body=.5, compression=.4, ambience=.3, modulation=.1)
        rows = {r['id']: r for r in load_catalog()['devices']}
        for route in ('frfr', 'power_amp_cab', 'amp_front'):
            result = recipes(f, route, 'ko')
            self.assertEqual(len(result), 3)
            for recipe in result:
                self.assertEqual(recipe['amp_included'], route != 'amp_front')
                self.assertEqual(recipe['cabinet_included'], route == 'frfr')
                for block in recipe['blocks']:
                    self.assertEqual(rows[block['catalog_id']]['kind'], 'native')
                    self.assertEqual(block['model'], rows[block['catalog_id']]['name'])
                    self.assertEqual(block['parameters'], {})  # no fabricated TMP knobs
                    self.assertEqual(block['parameter_status'], 'device_defaults_unverified')

    def test_invalid_firmware_and_routes_are_rejected(self):
        from quad_cortex import recipes, eligible_native
        with self.assertRaises(ValueError):
            eligible_native({'kind': 'native', 'added_in': '1.0.0'}, 'unknown')
        with self.assertRaises(ValueError):
            recipes(None, 'arbitrary', 'en')

    def test_older_coros_omits_unavailable_optional_delay(self):
        from quad_cortex import recipes, load_catalog, validate_firmware
        features = SimpleNamespace(saturation=.4, brightness=.5, body=.5, compression=.4, ambience=.3, modulation=.1)
        versions = {row['added_in'] for row in load_catalog()['devices'] if row['added_in']}
        for version in versions:
            for route in ('frfr', 'power_amp_cab', 'amp_front'):
                with self.subTest(version=version, route=route):
                    result = recipes(features, route, 'en', version)
                    self.assertEqual(len(result), 3)
                    for recipe in result:
                        self.assertTrue(all(validate_firmware(block['added_in']) <= validate_firmware(version)
                                            for block in recipe['blocks']))
                        if validate_firmware(version) < (2, 1, 0):
                            self.assertTrue(any('Delay' in note for note in recipe['limitations']))


if __name__ == '__main__':
    unittest.main()
