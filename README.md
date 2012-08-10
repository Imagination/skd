skd
===

[s]IMPLE [k]EY [d]ISTRIBUTION

Based on [django](https://www.djangoproject.com) and
[HTML 5 boilerplate](http://html5boilerplate.com). Requires
[Paramiko](http://www.lag.net/paramiko/).

Requirements
------------

  * Python >= 2.5
  * Django >= 1.4
  * Paramiko >= 1.7.7.2

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

Virtual Appliance
-----------------

skd is also available as a virtual appliance in the OVA-format, mostly used
within VMware environments. If you have one, grab the ova-file and deploy it
inside a VMware workstation or using the vSphere client. It's fairly easy.

When it boots up, it compiles all dependencies needed for skd and installs
them on an appropriate place.

During this installation process you will be asked for a "Django superuser".
That will be your skd administrator, so answer the question with "yes" and
add the details.

Please note, that the english keyboard is used during the setup. So beware if
you're using another keyboard layout!

After the installation finished, use a web browser and start the skd setup at

https://<the name or ip of your virtual machine>/setup

Log in using the details you provided at the superuser-screen and you're good
to go.