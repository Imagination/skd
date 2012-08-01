skd
===

[s]IMPLE [k]EY [d]ISTRIBUTION

Based on [django](https://www.djangoproject.com) and
[HTML 5 boilerplate](http://html5boilerplate.com).

Requirements
------------

  * Python >= 2.5
  * Django >= 1.4

Installation
------------

After installing the prerequisites, simply extract the skd root to a path
in your environment (i.e. /usr/local/skd).

Configuration
-------------

Copy the file "skd/local_settings.py.dist" to "skd/local_settings.py" and
change the values to match your environment.

After that create the initial database and root user by running

    python manage.py syncdb

to create the configured database and create the administration superuser.

For easy testing you can then use

    python manage.py runserver

from the skd root-directory to run a testing server using Django's
built-in development server. After that you can normally reach skd at

    http://127.0.0.1:8000

This is, however, not recommended as skd highly recommends running behind
a HTTPS-secured webserver. You can use skd's supplied wsgi-handler to run
skd using wsgi in webservers like
[apache](https://docs.djangoproject.com/en/1.4/howto/deployment/wsgi/modwsgi/)
or [lighttpd](http://redmine.lighttpd.net/projects/lighttpd2/wiki/Howto_WSGI).

Other deployment options are documented on
[the django site](https://docs.djangoproject.com/en/1.4/howto/deployment/).