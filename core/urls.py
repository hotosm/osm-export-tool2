# -*- coding: utf-8 -*-
"""
HOT Export Tool URL Configuration
"""
from django.conf import settings
from django.urls import include, re_path
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import TemplateView, RedirectView
from django.views.i18n import JavaScriptCatalog
from ui.views import (authorized, login, logout, redirect_to_v3, v3)

urlpatterns = []

urlpatterns += i18n_patterns(
    re_path(r'^$', redirect_to_v3, name='index'),
    re_path(r'^v3/', v3, name="v3"),
    re_path(r'^login/$', login, name="login"),
    re_path(r'^logout$', logout, name='logout'),
    re_path(r'^email/$', view=TemplateView.as_view(template_name='osm/email.html'),
        name='require_email'),
)

urlpatterns += [
    re_path(r'^authorized', authorized, name="authorized"),
]

urlpatterns += i18n_patterns(
    re_path(r'^admin/login/', RedirectView.as_view(pattern_name='login', permanent=False)),
    re_path(r'^admin/', admin.site.urls),
)

# OAuth client urls
urlpatterns += i18n_patterns(
    re_path('^osm/', include('social_django.urls', namespace='osm')),
    re_path('^osm/email_verify_sent/$', TemplateView.as_view(
        template_name='osm/email_verify_sent.html'), name='email_verify_sent'),
    re_path('^osm/error$', TemplateView.as_view(template_name='osm/error.html'),
        name='login_error')
)

# OAuth provider urls
urlpatterns += [
    re_path(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]

# don't apply i18n patterns here.. api uses Accept-Language header
urlpatterns += [
    re_path(r'^api/', include('api.urls', namespace='api')),
    re_path(r'^api/', include('rest_framework.urls', namespace='rest_framework')),
]

# i18n for js
js_info_dict = {
    'packages': ('hot_osm',),
}

urlpatterns += [
    re_path(r'^jsi18n/$', JavaScriptCatalog.as_view(packages=['hot_osm']), name='javascript-catalog'),
    re_path(r'^i18n/', include('django.conf.urls.i18n')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
