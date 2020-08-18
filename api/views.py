"""Provides classes for handling API requests."""
# -*- coding: utf-8 -*-
from distutils.util import strtobool
import itertools
from itertools import chain
import logging
import json
from django.utils import timezone
from datetime import datetime, timedelta
from collections import Counter

import os
import io
import csv
import dateutil.parser
import requests
from cachetools.func import ttl_cache
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group
from django.contrib.gis.geos import GEOSGeometry, Polygon
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError as DjangoValidationError
from jobs.models import HDXExportRegion, PartnerExportRegion, Job, SavedFeatureSelection
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from api.serializers import (ConfigurationSerializer, ExportRunSerializer, ExportTaskSerializer,
                         HDXExportRegionListSerializer,
                         HDXExportRegionSerializer, JobGeomSerializer,
                         PartnerExportRegionListSerializer, PartnerExportRegionSerializer,
                         JobSerializer)
from tasks.models import ExportRun
from tasks.task_runners import ExportTaskRunner

from .permissions import IsHDXAdmin, IsOwnerOrReadOnly, IsMemberOfGroup
from .renderers import HOTExportApiRenderer

from hdx_exports.hdx_export_set import sync_region
from rtree import index

# Get an instance of a logger
LOG = logging.getLogger(__name__)

# controls how api responses are rendered
renderer_classes = (JSONRenderer, HOTExportApiRenderer)

DIR = os.path.dirname(os.path.abspath(__file__))
idx = index.Rtree(os.path.join(DIR,'reverse_geocode'))

def bbox_to_geom(s):
    try:
        return GEOSGeometry(Polygon.from_bbox(s.split(',')), srid=4326)
    except Exception:
        raise ValidationError({'bbox': 'Query bounding box is malformed.'})


class JobViewSet(viewsets.ModelViewSet):
    """
    ##Export API Endpoint.

    Main endpoint for export creation and managment. Provides endpoints
    for creating, listing and deleting export jobs.

    Updates to existing jobs are not supported as exports can be cloned.

    Request data should be posted as `application/json`.

    <code>
    curl -v -H "Content-Type: application/json" -H "Authorization: Token [your token]"
    --data @request.json http://EXPORT_TOOL_URL/api/jobs
    </code>

    To monitor the resulting export run retreive the `uid` value from the returned json
    and call http://export.hotosm.org/api/runs?job_uid=[the returned uid]
    """

    serializer_class = JobSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly)
    lookup_field = 'uid'
    filter_backends = (filters.OrderingFilter, filters.SearchFilter, )
    search_fields = ('name', 'description', 'event', 'user__username')
    ordering_fields = ('__all__',)
    ordering = ('-pinned','-updated_at')

    def get_queryset(self):
        user = self.request.user
        queryset = Job.objects
        all = strtobool(self.request.query_params.get('all', 'false')) or self.action != "list"
        bbox = self.request.query_params.get('bbox', None)
        before = self.request.query_params.get('before', None)
        after = self.request.query_params.get('after', None)
        pinned = self.request.query_params.get('pinned',None)

        if before is not None:
            queryset = queryset.filter(Q(created_at__lte=before))

        if after is not None:
            queryset = queryset.filter(Q(created_at__gte=after))

        if bbox is not None:
            bbox = bbox_to_geom(bbox)
            queryset = queryset.filter(Q(the_geom__within=bbox))

        if pinned:
            queryset = queryset.filter(Q(pinned=True))

        if not all:
            queryset = queryset.filter(Q(user_id=user.id))

        if user.is_superuser:
            return queryset

        return queryset

    def perform_create(self, serializer):
        if Job.objects.filter(
            created_at__gt=timezone.now() - timedelta(minutes=60), user=self.request.user
        ).count() > 5:
            raise ValidationError({"the_geom": ["You are rate limited to 5 exports per hour."]})
        job = serializer.save()
        task_runner = ExportTaskRunner()
        task_runner.run_task(job_uid=str(job.uid))

    @action(detail=True)
    def geom(self, request, uid=None):
        job = Job.objects.get(uid=uid)
        geom_serializer = JobGeomSerializer(job)
        return Response(geom_serializer.data)


class ConfigurationViewSet(viewsets.ModelViewSet):
    """ API endpoints for stored YAML configurations.
    Note that these are mutable - a configuration can be edited."""

    serializer_class = ConfigurationSerializer
    permission_classes = (IsOwnerOrReadOnly,
                          permissions.IsAuthenticatedOrReadOnly)
    lookup_field = 'uid'
    filter_backends = (filters.OrderingFilter, filters.SearchFilter, )
    search_fields = ('name', 'description')
    ordering_fields = ('__all__')
    ordering = ('-pinned')

    def get_queryset(self):
        user = self.request.user
        queryset = SavedFeatureSelection.objects.filter(deleted=False).order_by('-pinned','name')
        pinned = self.request.query_params.get('pinned',None)
        all = strtobool(self.request.query_params.get('all', 'false')) or self.action != "list"

        if not all:
            queryset = queryset.filter(Q(user_id=user.id))
        if pinned:
            queryset = queryset.filter(Q(pinned=True))

        return queryset.filter(Q(user_id=user.id) | Q(public=True))


class ExportRunViewSet(viewsets.ModelViewSet):
    """
    Export Run API Endpoint.

    Poll this endpoint for querying export runs.
    """
    serializer_class = ExportRunSerializer
    permission_classes = (permissions.AllowAny, )
    lookup_field = 'uid'

    def create(self, request, format='json'):
        """
        runs the job.
        """
        if ExportRun.objects.filter(created_at__gt=timezone.now()-timedelta(minutes=1),user=request.user).count() >= 1:
            return Response({'status': 'RATE_LIMITED'}, status=status.HTTP_400_BAD_REQUEST)
        job_uid = request.query_params.get('job_uid', None)
        task_runner = ExportTaskRunner()
        task_runner.run_task(job_uid=job_uid, user=request.user)
        return Response({'status': 'OK'}, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        return ExportRun.objects.all().order_by('-started_at')

    def retrieve(self, request, uid=None, *args, **kwargs):
        """
        Get a single Export Run.
        """
        queryset = ExportRun.objects.filter(uid=uid)
        serializer = self.get_serializer(
            queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        """
        List the Export Runs for a single Job.
        """
        job_uid = self.request.query_params.get('job_uid', None)
        queryset = self.filter_queryset(
            ExportRun.objects.filter(job__uid=job_uid).order_by('-started_at'))
        serializer = self.get_serializer(
            queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class HDXExportRegionViewSet(viewsets.ModelViewSet):
    """ API endpoint for HDX regions.
    Viewing and editing these is limited to a set of admins."""

    ordering_fields = '__all__'
    ordering = ('job__description',)
    permission_classes = (IsHDXAdmin, )
    filter_backends = (filters.OrderingFilter, filters.SearchFilter, )
    search_fields = ('job__name', 'job__description')

    def get_queryset(self):
        queryset = HDXExportRegion.objects.filter(deleted=False)
        schedule_period = self.request.query_params.get('schedule_period', None)
        if schedule_period not in [None,'any']:
            queryset = queryset.filter(Q(schedule_period=schedule_period))

        return queryset.prefetch_related(
            'job__runs__tasks').defer('job__the_geom')

    def get_serializer_class(self):
        if self.action == "list":
            return HDXExportRegionListSerializer

        return HDXExportRegionSerializer

    def perform_create(self, serializer):
        serializer.save()
        if settings.SYNC_TO_HDX:
            sync_region(serializer.instance)
        else:
            print("Stubbing interaction with HDX API.")

    def perform_update(self, serializer):
        serializer.save()
        if settings.SYNC_TO_HDX:
            sync_region(serializer.instance)
        else:
            print("Stubbing interaction with HDX API.")


class PartnerExportRegionViewSet(viewsets.ModelViewSet):
    # get only Regions that belong to the user's Groups.
    ordering_fields = '__all__'
    ordering = ('job__description',)
    filter_backends = (filters.OrderingFilter, filters.SearchFilter, )
    search_fields = ('job__name', 'job__description')
    permission_classes = (IsMemberOfGroup,)

    def get_queryset(self):
        group_ids = self.request.user.groups.values_list('id')
        return PartnerExportRegion.objects.filter(deleted=False,group_id__in=group_ids).prefetch_related(
            'job__runs__tasks').defer('job__the_geom')

    def get_serializer_class(self):
        if self.action == "list":
            return PartnerExportRegionListSerializer

        return PartnerExportRegionSerializer


@require_http_methods(['GET'])
def permalink(request, uid):
    try:
        job = Job.objects.filter(uid=uid).first()
        if not job:
            return HttpResponseNotFound()
        run = job.runs.filter(status='COMPLETED').latest('finished_at')
        serializer = ExportTaskSerializer(run.tasks.all(),many=True)
        return HttpResponse(JSONRenderer().render(serializer.data))
    except ExportRun.DoesNotExist:
        return HttpResponse(JSONRenderer().render({}))
    except DjangoValidationError:
        return HttpResponseNotFound()



@require_http_methods(['GET'])
def stats(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    before = request.GET.get('before',timezone.now())
    after = request.GET.get('after',timezone.now() - timedelta(days=1))
    period = request.GET.get('period','day')
    is_csv = (request.GET.get('csv',False) == 'true')

    def toWeek(dt):
        sunday = dt.strftime('%Y-%U-0')
        return datetime.strptime(sunday, '%Y-%U-%w').strftime('%Y-%m-%d')

    def toDay(dt):
        return dt.strftime('%Y-%m-%d')

    def toMonth(dt):
        return dt.strftime('%Y-%m')

    if period == 'day':
        period_fn = toDay
    elif period == 'week':
        period_fn = toWeek
    elif period == 'month':
        period_fn = toMonth

    users = User.objects.only('date_joined').filter(date_joined__gte=after,date_joined__lte=before).order_by('-date_joined')

    grouped_users_by_period = {}
    for gu in itertools.groupby(users, lambda u:period_fn(u.date_joined)):
        grouped_users_by_period[gu[0]] = len(list(gu[1]))

    queryset = Job.objects.only('created_at','the_geom').order_by('-created_at')
    if before:
        queryset = queryset.filter(Q(created_at__lte=before))
    if after:
        queryset = queryset.filter(Q(created_at__gte=after))

    grouped_jobs = itertools.groupby(queryset,lambda j:period_fn(j.created_at))

    geoms = []
    periods = []
    for x in grouped_jobs:
        top_regions = Counter()
        jobs_in_group = list(x[1])
        for j in jobs_in_group:
            centroid = j.the_geom.centroid
            geoms.append([centroid.x,centroid.y])
            result = next(idx.nearest((centroid.x,centroid.y),1,objects=True))
            top_regions[result.object[2]] += 1

        users_in_period = grouped_users_by_period.get(x[0],0)

        top_regions_string = ' '.join(["{0}:{1}".format(x[0],x[1]) for x in top_regions.most_common(5)])
        periods.append({'start_date':x[0],'jobs_count':len(jobs_in_group),'users_count':users_in_period,'top_regions':top_regions_string})

    if is_csv:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['start_date','jobs_count','users_count','top_regions'])
        for period in periods:
            writer.writerow([period['start_date'],period['jobs_count'],period['users_count'],period['top_regions']])
        return HttpResponse(output.getvalue())
    else:
        return HttpResponse(json.dumps({'periods':periods,'geoms':geoms}))

@require_http_methods(['GET'])
@login_required()
def request_geonames(request):
    """Geocode with GeoNames."""
    payload = {
        'maxRows': 20,
        'username': 'osm_export_tool',
        'style': 'full',
        'q': request.GET.get('q')
    }

    geonames_url = getattr(settings, 'GEONAMES_API_URL')

    if geonames_url:
        response = requests.get(geonames_url, params=payload).json()
        assert (isinstance(response, dict))
        return JsonResponse(response)
    else:
        return JsonResponse(
            {
                'error': 'A url was not provided for geonames'
            },
            status=500, )


@ttl_cache(ttl=60)
@require_http_methods(['GET'])
@login_required()
def get_overpass_timestamp(request):
    """
    Endpoint to show the last OSM update timestamp on the Create page.
    this sometimes fails, returning a HTTP 200 but empty content.
    """
    r = requests.get('{}timestamp'.format(settings.OVERPASS_API_URL))
    return JsonResponse({'timestamp': dateutil.parser.parse(r.content)})

@login_required()
def get_overpass_status(request):
    r = requests.get('{}status'.format(settings.OVERPASS_API_URL))
    return HttpResponse(r.content)


@require_http_methods(['GET'])
@login_required()
def get_user_permissions(request):
    user = request.user
    permissions = []

    if user.is_superuser:
        permissions = Permission.objects.all().values_list(
            'content_type__app_label', 'codename')
    else:
        permissions = chain(
            user.user_permissions.all().values_list('content_type__app_label',
                                                    'codename'),
            Permission.objects.filter(group__user=user).values_list(
                'content_type__app_label', 'codename'))

    return JsonResponse({
        "username": user.username,
        "permissions":
        list(map(lambda pair: ".".join(pair), (set(permissions))))
    })

# get a list of partner organizations and their numeric IDs.
# this can be exposed to the public.
@require_http_methods(['GET'])
@login_required()
def get_groups(request):
    groups = [{'id':g.id,'name':g.name} for g in Group.objects.filter(is_partner=True)]
    return JsonResponse({'groups':groups})
