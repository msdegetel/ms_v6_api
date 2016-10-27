import logging

from c2corg_api import DBSession
from c2corg_api.models.cache_version import CacheVersion
from c2corg_api.models.document import Document, DocumentLocale
from c2corg_api.models.route import ROUTE_TYPE, RouteLocale
from c2corg_api.models.user_profile import USERPROFILE_TYPE
from c2corg_api.views import cors_policy
from c2corg_api.views.validation import create_int_validator, \
    validate_document_type
from cornice.resource import resource, view
from pyramid.httpexceptions import HTTPNotFound
from sqlalchemy.sql.functions import func
from math import ceil

log = logging.getLogger(__name__)

# Search engines accept not more than 50000 urls per sitemap,
# see http://www.sitemaps.org/protocol.html
PAGES_PER_SITEMAP = 50000


validate_page = create_int_validator('i')


@resource(
    collection_path='/sitemaps', path='/sitemaps/{doc_type}/{i}',
    cors_policy=cors_policy)
class SitemapRest(object):

    def __init__(self, request):
        self.request = request

    @view()
    def collection_get(self):
        """ Returns the information needed to generate a sitemap index file.
        See: http://www.sitemaps.org/protocol.html

        The response consists of a list of URLs to request the information
        needed to generate the sitemap linked from the sitemap index.

        E.g.

            {
                "sitemaps": [
                    "/sitemaps/w/0",
                    "/sitemaps/a/0",
                    "/sitemaps/i/0",
                    "/sitemaps/i/1",
                    "/sitemaps/i/2",
                    "/sitemaps/i/3",
                    "/sitemaps/i/4",
                    "/sitemaps/i/5",
                    ...
                ]
            }
        """
        document_locales_per_type = DBSession. \
            query(Document.type, func.count().label('count')). \
            join(
                DocumentLocale,
                Document.document_id == DocumentLocale.document_id). \
            filter(Document.type != USERPROFILE_TYPE). \
            group_by(Document.type). \
            all()

        sitemaps = []
        for doc_type, count in document_locales_per_type:
            num_sitemaps = ceil(count / PAGES_PER_SITEMAP)
            sitemaps_for_type = [
                '/sitemaps/{}/{}'.format(doc_type, i)
                for i in range(0, num_sitemaps)
            ]
            sitemaps.extend(sitemaps_for_type)

        return {
            'sitemaps': sitemaps
        }

    @view(validators=[validate_page, validate_document_type])
    def get(self):
        """ Returns the information needed to generate a sitemap for a given
        type and sitemap page number.
        """
        doc_type = self.request.validated['doc_type']
        i = self.request.validated['i']

        fields = [
            Document.document_id, DocumentLocale.lang, DocumentLocale.title,
            CacheVersion.last_updated
        ]

        # include `title_prefix` for routes
        is_route = doc_type == ROUTE_TYPE
        if is_route:
            fields.append(RouteLocale.title_prefix)

        base_query = DBSession. \
            query(*fields). \
            select_from(Document). \
            join(DocumentLocale,
                 Document.document_id == DocumentLocale.document_id)

        if is_route:
            # joining on `RouteLocale.__table_` instead of `RouteLocale` to
            # avoid that SQLAlchemy create an additional join on DocumentLocale
            base_query = base_query. \
                join(RouteLocale.__table__,
                     DocumentLocale.id == RouteLocale.id)

        base_query = base_query. \
            join(CacheVersion,
                 Document.document_id == CacheVersion.document_id). \
            filter(Document.redirects_to.is_(None)). \
            filter(Document.type == doc_type). \
            order_by(Document.document_id, DocumentLocale.lang). \
            limit(PAGES_PER_SITEMAP). \
            offset(PAGES_PER_SITEMAP * i)

        document_locales = base_query.all()

        if not document_locales:
            raise HTTPNotFound()

        return {
            'pages': [
                self._format_page(locale, is_route)
                for locale in document_locales
            ]
        }

    def _format_page(self, document_locale, is_route):
        if not is_route:
            doc_id, lang, title, last_updated = document_locale
        else:
            doc_id, lang, title, last_updated, title_prefix = document_locale

        page = {
            'document_id': doc_id,
            'lang': lang,
            'title': title,
            'lastmod': last_updated.isoformat()
        }

        if is_route:
            page['title_prefix'] = title_prefix

        return page
