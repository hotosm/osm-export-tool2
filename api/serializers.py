"""
Provides serialization for API responses.

See `DRF serializer documentation  <http://www.django-rest-framework.org/api-guide/serializers/>`_
Used by the View classes api/views.py to serialize API responses as JSON or HTML.
See DEFAULT_RENDERER_CLASSES setting in core.settings.contrib for the enabled renderers.
"""
# -*- coding: utf-8 -*-
import logging

import django.core.exceptions
from django.contrib.auth.models import User
from django.db import transaction
from jobs.models import HDXExportRegion, Job, SavedFeatureSelection, validate_aoi, validate_mbtiles, PartnerExportRegion
from rest_framework import serializers
from rest_framework_gis import serializers as geo_serializers
from tasks.models import ExportRun, ExportTask

# Get an instance of a logger
LOG = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', )


class ExportTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportTask
        fields = ('uid', 'name', 'status', 'started_at', 'finished_at',
                  'duration', 'filesize_bytes', 'download_urls')


class ExportRunSerializer(serializers.ModelSerializer):
    tasks = ExportTaskSerializer(many=True, read_only=True)
    user = UserSerializer(
        read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = ExportRun
        lookup_field = 'uid'
        fields = ('uid', 'started_at', 'finished_at', 'duration',
                  'elapsed_time', 'user', 'size', 'status', 'tasks')


class ConfigurationSerializer(serializers.ModelSerializer):
    user = UserSerializer(
        read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = SavedFeatureSelection
        fields = ('uid', 'name', 'description', 'yaml', 'public', 'user','pinned')


class JobGeomSerializer(serializers.ModelSerializer):
    """ Since Job Geoms can be large, these are serialized separately,
    instead of nested within Jobs."""

    class Meta:
        model = Job
        fields = ('the_geom', )

class JobSerializer(serializers.ModelSerializer):
    user = UserSerializer(default=serializers.CurrentUserDefault())

    class Meta:
        model = Job
        fields = ('id', 'uid', 'user', 'name', 'description', 'event',
                  'export_formats', 'published', 'feature_selection',
                  'buffer_aoi', 'osma_link', 'created_at', 'area', 'the_geom',
                  'simplified_geom', 'mbtiles_source', 'mbtiles_minzoom', 'mbtiles_maxzoom','pinned','unfiltered')
        extra_kwargs = {
            'the_geom': {
                'write_only': True
            },
            'simplified_geom': {
                'read_only': True
            }
        }

    def validate(self,data):
        try:
            validate_aoi(data['the_geom'])
        except django.core.exceptions.ValidationError as e:
            raise serializers.ValidationError({'the_geom':e.messages[0]})

        try:
            validate_mbtiles(data)
        except django.core.exceptions.ValidationError as e:
            raise serializers.ValidationError({'mbtiles_source': e.messages[0]})

        return data

def validate_model(model):
    try:
        model.full_clean()
    except django.core.exceptions.ValidationError as e:
        raise serializers.ValidationError(e.message_dict)

class PartnerExportRegionListSerializer(serializers.ModelSerializer):
    export_formats = serializers.ListField()
    feature_selection = serializers.CharField()
    simplified_geom = geo_serializers.GeometryField(required=False)
    name = serializers.CharField()

    class Meta:  # noqa
        model = PartnerExportRegion
        fields = ('id', 'feature_selection',
                  'schedule_period', 'schedule_hour', 'export_formats',
                  'name', 'last_run', 'next_run',
                  'simplified_geom', 'job_uid', 'last_size','group_name')

class PartnerExportRegionSerializer(serializers.ModelSerializer):  # noqa
    export_formats = serializers.ListField()
    feature_selection = serializers.CharField()
    simplified_geom = geo_serializers.GeometryField(required=False)
    the_geom = geo_serializers.GeometryField()
    name = serializers.CharField()
    event = serializers.CharField()
    description = serializers.CharField()

    class Meta:  # noqa
        model = PartnerExportRegion
        fields = ('id', 'feature_selection',
                  'schedule_period', 'schedule_hour', 'export_formats',
                  'name', 'event', 'description', 'last_run', 'next_run',
                  'simplified_geom', 'job_uid',
                  'the_geom','group','planet_file')
        extra_kwargs = {
            'simplified_geom': {
                'read_only': True
            },
            'the_geom': {
                'write_only': True
            }
        }

    def create(self, validated_data):  # noqa
        def slice_dict(in_dict, wanted_keys):
            return dict((k, in_dict[k]) for k in wanted_keys if k in in_dict)

        job_dict = slice_dict(validated_data, [
            'the_geom', 'export_formats', 'feature_selection',
        ])
        job_dict['user'] = self.context['request'].user
        job_dict['name'] = validated_data.get('name')
        job_dict['event'] = validated_data.get('event') or ""
        job_dict['description'] = validated_data.get('description') or ""

        region_dict = slice_dict(validated_data, [
            'schedule_period', 'schedule_hour','group','planet_file'
        ])
        job = Job(**job_dict)
        job.hidden = True
        job.unlimited_extent = True
        validate_model(job)

        # check on creation that i'm a member of the group
        if not self.context['request'].user.groups.filter(name=region_dict['group'].name).exists():
            raise serializers.ValidationError({'group':'You are not a member of this group.'})

        with transaction.atomic():
            job.save()
            region_dict['job'] = job
            region = PartnerExportRegion(**region_dict)
            validate_model(region)
            region.save()
        return region

    def update(self, instance, validated_data):  # noqa
        def update_attrs(model, v_data, keys):
            for key in keys:
                if key in v_data:
                    setattr(model, key, v_data[key])

        # if re-assigning, check group membership
        if not self.context['request'].user.groups.filter(name= validated_data['group'].name).exists():
            raise serializers.ValidationError({'group':'You are not a member of this group.'})

        job = instance.job
        update_attrs(job, validated_data, [
            'the_geom', 'export_formats', 'feature_selection'
        ])
        job.name = validated_data.get('name')
        job.event = validated_data.get('event') or ""
        job.description = validated_data.get('description') or ""

        validate_model(job)
        update_attrs(instance, validated_data, [
            'schedule_period', 'schedule_hour', 'group','planet_file'
        ])
        validate_model(instance)
        with transaction.atomic():
            instance.save()
            job.save()
        return instance

class HDXExportRegionListSerializer(serializers.ModelSerializer):  # noqa
    """ The list serializer does not expose the Geom, as it can be large."""

    export_formats = serializers.ListField()
    dataset_prefix = serializers.CharField()
    feature_selection = serializers.CharField()
    simplified_geom = geo_serializers.GeometryField(required=False)
    name = serializers.CharField()
    buffer_aoi = serializers.BooleanField()

    class Meta:  # noqa
        model = HDXExportRegion
        fields = ('id', 'dataset_prefix', 'datasets', 'feature_selection',
                  'schedule_period', 'schedule_hour', 'export_formats',
                  'locations', 'name', 'last_run', 'next_run',
                  'simplified_geom', 'dataset_prefix', 'job_uid', 'license',
                  'subnational', 'extra_notes', 'is_private', 'buffer_aoi', 'last_size')


class HDXExportRegionSerializer(serializers.ModelSerializer):  # noqa
    """ Internally, an export region is a job model + an export region model
    but to API users, it appears as a single entity. """

    export_formats = serializers.ListField()
    dataset_prefix = serializers.CharField()
    feature_selection = serializers.CharField()
    simplified_geom = geo_serializers.GeometryField(required=False)
    the_geom = geo_serializers.GeometryField()
    name = serializers.CharField()
    buffer_aoi = serializers.BooleanField()

    class Meta:  # noqa
        model = HDXExportRegion
        fields = ('id', 'dataset_prefix', 'datasets', 'feature_selection',
                  'schedule_period', 'schedule_hour', 'export_formats',
                  'locations', 'name', 'last_run', 'next_run',
                  'simplified_geom', 'dataset_prefix', 'job_uid', 'license',
                  'subnational', 'extra_notes', 'is_private', 'buffer_aoi',
                  'the_geom','planet_file')
        extra_kwargs = {
            'simplified_geom': {
                'read_only': True
            },
            'the_geom': {
                'write_only': True
            }
        }

    def create(self, validated_data):  # noqa
        def slice_dict(in_dict, wanted_keys):
            return dict((k, in_dict[k]) for k in wanted_keys if k in in_dict)

        job_dict = slice_dict(validated_data, [
            'the_geom', 'export_formats', 'feature_selection', 'buffer_aoi'
        ])
        job_dict['user'] = self.context['request'].user
        job_dict['name'] = validated_data.get('dataset_prefix')
        job_dict['description'] = validated_data.get('name')

        region_dict = slice_dict(validated_data, [
            'extra_notes', 'is_private', 'locations', 'license',
            'schedule_period', 'schedule_hour', 'subnational','planet_file'
        ])
        job = Job(**job_dict)
        job.hidden = True
        job.unlimited_extent = True
        validate_model(job)
        with transaction.atomic():
            job.save()
            region_dict['job'] = job
            region = HDXExportRegion(**region_dict)
            validate_model(region)
            region.save()
        return region

    def update(self, instance, validated_data):  # noqa
        def update_attrs(model, v_data, keys):
            for key in keys:
                if key in v_data:
                    setattr(model, key, v_data[key])

        job = instance.job
        update_attrs(job, validated_data, [
            'the_geom', 'export_formats', 'feature_selection', 'buffer_aoi'
        ])
        job.name = validated_data.get('dataset_prefix')
        job.description = validated_data.get('name')

        validate_model(job)
        update_attrs(instance, validated_data, [
            'extra_notes', 'is_private', 'locations', 'license',
            'schedule_period', 'schedule_hour', 'subnational', 'planet_file'
        ])
        validate_model(instance)
        with transaction.atomic():
            instance.save()
            job.save()
        return instance
