from django.contrib import sitemaps
from django.urls import reverse


class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'weekly'

    def items(self):
        return ['main', 'about', 'contact', 'terms', 'storage_terms', 'tutorials', 'signup', 'login', 'profile']

    def location(self, item):
        return reverse(item)