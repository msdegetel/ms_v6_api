import json

from c2corg_api.models.area import Area, ArchiveArea
from shapely.geometry import shape, Point

from c2corg_api.models.document import (
    DocumentGeometry, ArchiveDocumentLocale, DocumentLocale)
from c2corg_api.views.document import DocumentRest

from c2corg_api.tests.views import BaseDocumentTestRest


class TestAreaRest(BaseDocumentTestRest):

    def setUp(self):  # noqa
        self.set_prefix_and_model(
            "/areas", Area, ArchiveArea, ArchiveDocumentLocale)
        BaseDocumentTestRest.setUp(self)
        self._add_test_data()

    def test_get_collection(self):
        self.get_collection()

    def test_get_collection_paginated(self):
        self.app.get("/areas?offset=invalid", status=400)

        self.assertResultsEqual(
            self.get_collection({'offset': 0, 'limit': 0}), [], 4)

        self.assertResultsEqual(
            self.get_collection({'offset': 0, 'limit': 1}),
            [self.area4.document_id], 4)
        self.assertResultsEqual(
            self.get_collection({'offset': 0, 'limit': 2}),
            [self.area4.document_id, self.area3.document_id], 4)
        self.assertResultsEqual(
            self.get_collection({'offset': 1, 'limit': 2}),
            [self.area3.document_id, self.area2.document_id], 4)

        self.assertResultsEqual(
            self.get_collection(
                {'after': self.area3.document_id, 'limit': 1}),
            [self.area2.document_id], -1)

    def test_get_collection_lang(self):
        self.get_collection_lang()

    def test_get(self):
        body = self.get(self.area1)
        self._assert_geometry(body)

    def test_get_lang(self):
        self.get_lang(self.area1)

    def test_get_new_lang(self):
        self.get_new_lang(self.area1)

    def test_get_404(self):
        self.get_404()

    def test_post_error(self):
        body = self.post_error({})
        errors = body.get('errors')
        self.assertEqual(len(errors), 3)
        self.assertCorniceRequired(errors[0], 'locales')
        self.assertCorniceRequired(errors[1], 'geometry')
        self.assertCorniceRequired(errors[2], 'area_type')

    def test_post_missing_title(self):
        body_post = {
            'area_type': 'range',
            'geometry': {
                'geom': '{"type": "Point", "coordinates": [635956, 5723604]}'
            },
            'locales': [
                {'culture': 'en'}
            ]
        }
        body = self.post_missing_title(body_post)
        errors = body.get('errors')
        self.assertEqual(len(errors), 2)
        self.assertCorniceRequired(errors[0], 'locales.0.title')
        self.assertCorniceRequired(errors[1], 'locales')

    def test_post_non_whitelisted_attribute(self):
        body = {
            'area_type': 'range',
            'protected': True,
            'geometry': {
                'id': 5678, 'version': 6789,
                'geom': '{"type": "Point", "coordinates": [635956, 5723604]}'
            },
            'locales': [
                {'culture': 'en', 'title': 'Chartreuse'}
            ]
        }
        self.post_non_whitelisted_attribute(body)

    def test_post_missing_content_type(self):
        self.post_missing_content_type({})

    def test_post_success(self):
        body = {
            'area_type': 'range',
            'geometry': {
                'id': 5678, 'version': 6789,
                'geom': '{"type": "Point", "coordinates": [635956, 5723604]}'
            },
            'locales': [
                {'culture': 'en', 'title': 'Chartreuse'}
            ]
        }
        body, doc = self.post_success(body)
        self._assert_geometry(body)

        version = doc.versions[0]

        archive_map = version.document_archive
        self.assertEqual(archive_map.area_type, 'range')

        archive_locale = version.document_locales_archive
        self.assertEqual(archive_locale.culture, 'en')
        self.assertEqual(archive_locale.title, 'Chartreuse')

        archive_geometry = version.document_geometry_archive
        self.assertEqual(archive_geometry.version, doc.geometry.version)
        self.assertIsNotNone(archive_geometry.geom)

    def test_put_wrong_document_id(self):
        body = {
            'document': {
                'document_id': '-9999',
                'version': self.area1.version,
                'area_type': 'range',
                'locales': [
                    {'culture': 'en', 'title': 'Chartreuse',
                     'version': self.locale_en.version}
                ]
            }
        }
        self.put_wrong_document_id(body)

    def test_put_wrong_document_version(self):
        body = {
            'document': {
                'document_id': self.area1.document_id,
                'version': -9999,
                'area_type': 'range',
                'locales': [
                    {'culture': 'en', 'title': 'Chartreuse',
                     'version': self.locale_en.version}
                ]
            }
        }
        self.put_wrong_version(body, self.area1.document_id)

    def test_put_wrong_locale_version(self):
        body = {
            'document': {
                'document_id': self.area1.document_id,
                'version': self.area1.version,
                'area_type': 'range',
                'locales': [
                    {'culture': 'en', 'title': 'Chartreuse',
                     'version': -9999}
                ]
            }
        }
        self.put_wrong_version(body, self.area1.document_id)

    def test_put_wrong_ids(self):
        body = {
            'document': {
                'document_id': self.area1.document_id,
                'version': self.area1.version,
                'area_type': 'range',
                'locales': [
                    {'culture': 'en', 'title': 'Chartreuse',
                     'version': self.locale_en.version}
                ]
            }
        }
        self.put_wrong_ids(body, self.area1.document_id)

    def test_put_no_document(self):
        self.put_put_no_document(self.area1.document_id)

    def test_put_success_all(self):
        body = {
            'message': 'Update',
            'document': {
                'document_id': self.area1.document_id,
                'version': self.area1.version,
                'area_type': 'admin_limits',
                'geometry': {
                    'version': self.area1.geometry.version,
                    'geom': '{"type": "Point", "coordinates": [1, 2]}'
                },
                'locales': [
                    {'culture': 'en', 'title': 'New title',
                     'version': self.locale_en.version}
                ]
            }
        }
        (body, map1) = self.put_success_all(body, self.area1)

        self.assertEquals(map1.area_type, 'admin_limits')
        locale_en = map1.get_locale('en')
        self.assertEquals(locale_en.title, 'New title')

        # version with culture 'en'
        versions = map1.versions
        version_en = versions[2]
        archive_locale = version_en.document_locales_archive
        self.assertEqual(archive_locale.title, 'New title')

        archive_document_en = version_en.document_archive
        self.assertEqual(archive_document_en.area_type, 'admin_limits')

        archive_geometry_en = version_en.document_geometry_archive
        self.assertEqual(archive_geometry_en.version, 2)

        # version with culture 'fr'
        version_fr = versions[3]
        archive_locale = version_fr.document_locales_archive
        self.assertEqual(archive_locale.title, 'Chartreuse')

    def test_put_success_figures_only(self):
        body = {
            'message': 'Changing figures',
            'document': {
                'document_id': self.area1.document_id,
                'version': self.area1.version,
                'area_type': 'admin_limits',
                'locales': [
                    {'culture': 'en', 'title': 'Chartreuse',
                     'version': self.locale_en.version}
                ]
            }
        }
        (body, area) = self.put_success_figures_only(body, self.area1)

        self.assertEquals(area.area_type, 'admin_limits')

    def test_put_success_lang_only(self):
        body = {
            'message': 'Changing lang',
            'document': {
                'document_id': self.area1.document_id,
                'version': self.area1.version,
                'area_type': 'range',
                'locales': [
                    {'culture': 'en', 'title': 'New title',
                     'version': self.locale_en.version}
                ]
            }
        }
        (body, area) = self.put_success_lang_only(body, self.area1)

        self.assertEquals(
            area.get_locale('en').title, 'New title')

    def test_put_success_new_lang(self):
        """Test updating a document by adding a new locale.
        """
        body = {
            'message': 'Adding lang',
            'document': {
                'document_id': self.area1.document_id,
                'version': self.area1.version,
                'area_type': 'range',
                'locales': [
                    {'culture': 'es', 'title': 'Chartreuse'}
                ]
            }
        }
        (body, area) = self.put_success_new_lang(body, self.area1)

        self.assertEquals(area.get_locale('es').title, 'Chartreuse')

    def _assert_geometry(self, body):
        self.assertIsNotNone(body.get('geometry'))
        geometry = body.get('geometry')
        self.assertIsNotNone(geometry.get('version'))
        self.assertIsNotNone(geometry.get('geom'))

        geom = geometry.get('geom')
        point = shape(json.loads(geom))
        self.assertIsInstance(point, Point)
        self.assertAlmostEqual(point.x, 635956)
        self.assertAlmostEqual(point.y, 5723604)

    def _add_test_data(self):
        self.area1 = Area(area_type='range')

        self.locale_en = DocumentLocale(culture='en', title='Chartreuse')
        self.locale_fr = DocumentLocale(culture='fr', title='Chartreuse')

        self.area1.locales.append(self.locale_en)
        self.area1.locales.append(self.locale_fr)

        self.area1.geometry = DocumentGeometry(
            geom='SRID=3857;POINT(635956 5723604)')

        self.session.add(self.area1)
        self.session.flush()

        user_id = self.global_userids['contributor']
        DocumentRest(None)._create_new_version(self.area1, user_id)

        self.area2 = Area(area_type='range')
        self.session.add(self.area2)
        self.area3 = Area(area_type='range')
        self.session.add(self.area3)
        self.area4 = Area(area_type='admin_limits')
        self.area4.locales.append(DocumentLocale(
            culture='en', title='Isère'))
        self.area4.locales.append(DocumentLocale(
            culture='fr', title='Isère'))
        self.session.add(self.area4)
        self.session.flush()
