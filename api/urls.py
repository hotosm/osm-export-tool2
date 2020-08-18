# -*- coding: utf-8 -*-
"""API url configuration."""

from django.urls import re_path
from rest_framework.routers import DefaultRouter

from .views import (
    ConfigurationViewSet, ExportRunViewSet, HDXExportRegionViewSet, PartnerExportRegionViewSet,
    JobViewSet, permalink, get_overpass_timestamp, get_user_permissions, request_geonames,
    get_overpass_status, get_groups, stats
)

router = DefaultRouter(trailing_slash=False)
router.register(r'jobs', JobViewSet, basename='jobs')
router.register(r'runs', ExportRunViewSet, basename='runs')
router.register(
    r'configurations', ConfigurationViewSet, basename='configurations')
router.register(
    r'hdx_export_regions',
    HDXExportRegionViewSet,
    basename='hdx_export_regions')
router.register(
    r'partner_export_regions',
    PartnerExportRegionViewSet,
    basename='partner_export_regions')

app_name = 'api'
urlpatterns = router.urls
urlpatterns += [
    re_path(r'^permalink/(?P<uid>[a-z0-9\-]+)$', permalink),
    re_path(r'^request_geonames$', request_geonames),
    re_path(r'^overpass_timestamp$', get_overpass_timestamp),
    re_path(r'^overpass_status$', get_overpass_status),
    re_path(r'^permissions$', get_user_permissions),
    re_path(r'^groups$', get_groups),
    re_path(r'^stats$', stats)
]
