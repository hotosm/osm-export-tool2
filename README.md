OSM Export Tool
======

[![Join the chat at https://gitter.im/hotosm/osm-export-tool2](https://badges.gitter.im/hotosm/osm-export-tool2.svg)](https://gitter.im/hotosm/osm-export-tool2?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[![CircleCI](https://circleci.com/gh/hotosm/osm-export-tool2.svg?style=svg)](https://circleci.com/gh/hotosm/osm-export-tool2)

The **Export Tool** creates OpenStreetMap exports for GIS programs and mobile devices. It outputs files in various tabular formats based on an input area of interest polygon and a selection of OpenStreetMap tags. It is synchronized minutely with the main OSM database, so exports can be created to accompany real-time humanitarian mapping efforts. 

The latest version of the Export Tool is available at http://exports-prod.hotosm.org . All users are recommended to use this version.

The previous (version 2) iteration of the Export Tool is available at http://export.hotosm.org . This version is slower and less featureful than the newest version.

## Project Structure
This is a guide to the source code - useful if you'd like to contribute to the Export Tool, deploy the project on your own server, or re-use parts of the project.

`utils/`  contains Python classes responsible for downloading and transforming OSM data into each file format based on a GEOS geometry and a `FeatureSelection` object. Many of these are wrappers for GDAL/OGR commands. This module can be used independently of the web application for creating exports from the command line.

`feature_selection/` contains a parser for YAML feature selections that define how OSM data is mapped to tabular formats. More documentation on the YAML format is available at http://exports-prod.hotosm.org/v3/help/yaml .

`api/` is a Django web application that manages creating, viewing and searching exports, storing feature selections,  scheduling jobs, and user accounts via openstreetmap.org OAuth.

`ui/` is a React + ES6 frontend that communicates with the Django web application. It handles localization of the user interface, the OpenLayers-based map UI, and the Tag Tree feature selection wizard.

## Development Prerequisites

The Export Tool has several dependencies. As an alternative, use Docker to manage the project's environment, in which case you will need a Docker runtime. 

* Python 2.7, virtualenv, pip
* PostgreSQL 9+ and PostGIS
* GDAL/OGR
* RabbitMQ, a message queue
* node.js and yarn

## Overpass API

The Export tool queries an instance of the Overpass API for source data. Overpass:

* can efficiently perform spatial queries over a large amount of OSM data, including members of ways and relations.
* Has built in facilities to update OSM from minutely diffs.
* Can create lossless PBF-format exports, which are necessary for some file formats such as OSMand and Garmin .IMG mobile device maps.

Instructions on installing Overpass are available at https://github.com/drolbr/Overpass-API . Alternatively, Overpass can be run via Docker - see `ops/docker-overpass-api`.

* The export tool is configured with an Overpass URL via the environment variable `OVERPASS_API_URL`. This can be a public Overpass instance, a remote instance you manage yourself, or a local instance on your own computer. Public instances may have strict rate limits, so please use them lightly.
* To set up a local Overpass instance, start with a .pbf file. This can be the full planet .pbf from http://planet.openstreetmap.org or a region, e.g. pbfs available from http://download.geofabrik.de/ . 
* Optionally, configure Overpass to update itself minutely. 



## Development Step-By-Step Guide

### Create the database and role
<pre>
$ sudo -u postgres createuser -s -P hot
$ sudo -u postgres createdb -O hot hot_exports_dev
</pre>

You might need to update the <code>pg_hba.conf</code> file to allow localhost connections via tcp/ip or
allow trusted connections from localhost.

Create the exports schema

<pre>
$ psql -U hot -h localhost -d hot_exports_dev -c "CREATE SCHEMA exports AUTHORIZATION hot"
</pre>

#### Garmin

Download the latest version of the __mkgmap__ utility for making garmin IMG files from [http://www.mkgmap.org.uk/download/mkgmap.html](http://www.mkgmap.org.uk/download/mkgmap.html)

Download the latest version of the __splitter__ utility for splitting larger osm files into tiles. [http://www.mkgmap.org.uk/download/splitter.html](http://www.mkgmap.org.uk/download/splitter.html)

Create a directory and unpack the <code>mkgmap</code> and <code>splitter</code> archives into it.

#### OSMAnd OBF

For details on the OSMAnd Map Creator utility see [http://wiki.openstreetmap.org/wiki/OsmAndMapCreator](http://wiki.openstreetmap.org/wiki/OsmAndMapCreator)

Download the OSMAnd MapCreator from [http://download.osmand.net/latest-night-build/OsmAndMapCreator-main.zip](http://download.osmand.net/latest-night-build/OsmAndMapCreator-main.zip).
Unpack this into a directory somewhere.

### Checkout the HOT Export Tool source

In the hotosm project directory run:

<code>$ git clone git@github.com:hotosm/osm-export-tool2.git</code>

### Install the project's python dependencies

From the project directory, install the dependencies into your virtualenv:

<code>$ pip install -r requirements-dev.txt</code>

or

<code>$ pip install -r requirements.txt</code>


### Project Settings

TODO this should be updated to reflect environment variables laid out below.

Create a copy of <code>core/settings/dev_dodobas.py</code> and update to reflect your development environment. <code>core/settings/dev.py</code> exists for this purpose.

Look at <code>core/settings/project.py</code> and make sure you update or override the following configuration variables in your development settings:

**EXPORT_STAGING_ROOT** = 'path to a directory for staging export jobs'

**EXPORT_DOWNLOAD_ROOT** = 'path to a directory for storing export downloads'

**EXPORT_MEDIA_ROOT** = '/downloads/' (map this url in your webserver to EXPORT_DOWNLOAD_ROOT to serve the exported files)

**OSMAND_MAP_CREATOR_DIR** = 'path to directory where OsmAndMapCreator is installed'

**GARMIN_CONFIG** = 'absolute path to utils/conf/garmin_config.xml'

**OVERPASS_API_URL** = 'url of your local overpass api endpoint (see Overpass API below)'

Edit <code>core/settings/dev.py</code> to ensure that the database connection information is correct.

Update the <code>utils/conf/garmin_config.xml</code> file. Update the <code>garmin</code> and <code>splitter</code> elements to point to the
absolute location of the <code>mkgmap.jar</code> and <code>splitter.jar</code> utilites.

Set the active configuration (<code>you_settings_module</code> can be <code>dev</code> or the basename of your copy of <code>core/settings/dev_dodobas.py</code>):

<code>export DJANGO_SETTINGS_MODULE=core.settings.your_settings_module</code> (defaults to `core.settings.dev` in `manage.py`)

Once you've got all the dependencies installed, run <code>./manage.py migrate</code> to set up the database tables etc..
Then run <code>./manage.py runserver</code> to run the server.
You should then be able to browse to [http://localhost:8000/](http://localhost:8000/)

If you're running this in a virtual machine, use <code>./manage.py runserver 0.0.0.0:8000</code> to have Django listen on all interfaces and make it possible to connect from the VM host.

### Celery Workers

HOT Exports depends on the [Celery](http://celery.readthedocs.org/en/latest/index.html) distributed task queue. As export jobs are created
they are pushed to a Celery Worker for processing. At least two celery workers need to be started as follows:

From a 'hotosm' virtualenv directory (use screen), run:

<code>export DJANGO_SETTINGS_MODULE=core.settings.your_settings_module</code>

<code>$ celery -A core worker --loglevel debug --logfile=celery.log</code>.

This will start a celery worker which will process export tasks. An additional celery worker needs to be started to handle purging of expired unpublished
export jobs. From another hotosm virtualenv terminal session in the project top-level directory, run:

<code>export DJANGO_SETTINGS_MODULE=core.settings.your_settings_module</code>

<code>$ celery -A core beat --loglevel debug --logfile=celery-beat.log</code>

See the <code>CELERYBEAT_SCHEDULE</code> setting in <code>core/settings/celery.py</code>.

For more detailed information on Celery Workers see [here](http://celery.readthedocs.org/en/latest/userguide/workers.html)

For help with daemonizing Celery workers see [here](http://celery.readthedocs.org/en/latest/tutorials/daemonizing.html)

## Using Transifex service

To work with Transifex you need to create `~/.transifexrc`, and modify it's access privileges

`chmod 600 ~/.transifexrc`

Example `.transifexrc` file:

    [https://www.transifex.com]
    hostname = https://www.transifex.com
    password = my_super_password
    token =
    username = my_transifex_username

### Managing source files

To update source language (English) for Django templates run:

`python manage.py makemessages -l en`

To update source language for javascript files run:

`python manage.py makemessages -d djangojs -l en`


then, push the new source files to the Transifex service, it will overwrite the current source files

`tx push -s`

### Pulling latest changes from Transifex

When adding a new language, it's resource file does not exist in the project,
but it's ok as it will be automatically created when pulling new translations from the service. To add a local mapping:

`tx set -r osm-export-tool2.master -l hr locales/hr/LC_MESSAGES/django.po`

or for javascript files:

`tx set -r osm-export-tool2.djangojs -l hr locales/hr/LC_MESSAGES/djangojs.po`


Once there are some translation updates, pull the latest changes for mapped resources

For a specific language(s):

`tx pull -l fr,hr`

For all languages:

`tx pull`

Finally, compile language files

`python manage.py compilemessages`

## Environment Variables

* `BROKER_URL` - Celery broker URL. Defaults to `amqp://guest:guest@localhost:5672/`
* `DATABASE_URL` - Database URL. Defaults to `postgres:///exports`
* `DEBUG` - Whether to enable debug mode. Defaults to `False` (production).
* `DJANGO_ENV` - Django environment. Set to `development` to enable development tools.
* `EMAIL_HOST` - SMTP host. Optional.
* `EMAIL_HOST_USER` - SMTP username. Optional.
* `EMAIL_HOST_PASSWORD` = SMTP password. Optional.
* `EMAIL_PORT` = SMTP port. Optional.
* `EMAIL_USE_TLS` = Whether to use TLS when sending mail. Optional.
* `HOSTNAME` - Publicly-addressable hostname. Defaults to `export.hotosm.org`
* `OSM_API_KEY` - OSM API key. Optional (a default will be used).
* `OSM_API_SECRET` - OSM API secret. Optional (a default will be used).
* `OVERPASS_API_URL` - Overpass API URL. Defaults to `http://overpass-api.de/api/`
* `TASK_ERROR_EMAIL` - Email address to send task errors to. Defaults to `export-tool@hotosm.org`
* `USE_X_FORWARDED_HOST` - Whether Django is running behind a proxy. Defaults to `False`

## Paths

The following paths are siblings:

* `osm-export-tool2` - This app
* `export_staging` - Where exports are staged
* `export_downloads` - Where exports are stored for downloading. Should be mapped to `/downloads/` in the proxying web server
* `osmandmapcreator` - OsmAnd map creator
