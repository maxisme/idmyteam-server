from django.contrib import sitemaps
from django.urls import reverse

from idmyteamserver.urls import PUBLIC_URL_NAMES


class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = "weekly"

    def items(self):
        return PUBLIC_URL_NAMES

    def location(self, item):
        return reverse(item)
