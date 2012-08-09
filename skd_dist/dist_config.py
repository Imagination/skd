# [s][k][d] Appliance distribution configuration file

# Additional Debian-Packages to install

# Mirror used
deb_mirror = "http://ftp-stud.hs-esslingen.de/pub/Mirrors/ubuntu"

# Pool-Subdirectory (where the packages live
deb_pool = "%s/pool" % (deb_mirror,)

# URLS to debian packages to download
deb_packages = [
    "%s/main/n/ncurses/libncurses5-dev_5.7+20090803-2ubuntu3_amd64.deb" % (deb_pool,),
    "%s/main/o/openssl/libssl-dev_0.9.8k-7ubuntu8.13_amd64.deb" % (deb_pool,),
    "%s/main/r/readline6/libreadline-dev_6.1-1_amd64.deb" % (deb_pool,),
    "%s/main/p/pcre3/libpcre3-dev_7.8-3build1_amd64.deb" % (deb_pool,),
    "%s/main/s/sqlite3/libsqlite3-dev_3.6.22-1_amd64.deb" % (deb_pool,),
    "%s/main/b/bzip2/libbz2-dev_1.0.5-4ubuntu0.2_amd64.deb" % (deb_pool,),
    "%s/main/p/pcre3/libpcrecpp0_7.8-3build1_amd64.deb" % (deb_pool,),
    "%s/main/o/openssl/libssl0.9.8_0.9.8k-7ubuntu8.13_amd64.deb" % (deb_pool,),
    "%s/universe/d/dialog/dialog_1.1-20080819-1_amd64.deb" % (deb_pool,),
    "%s/main/r/readline6/libreadline6-dev_6.1-1_amd64.deb" % (deb_pool,),
    "%s/main/z/zlib/zlib1g-dev_1.2.3.3.dfsg-15ubuntu1_amd64.deb" % (deb_pool,)
]

# Base path where the skd distribution will be extracted
base_path = "/skd_distrib"

# Path to the contrib directory
contrib_path = "%s/skd_contrib" % (base_path,)

# Packages to install
# Supply a name, a type, a version and an url
# Use "generic" as the type to supply a "build"-Script, that is started within
# the extracted package.
# Use "Python" to do the common "python setup.py build"
# Optionally you can supply a "filename" and "ext" command if the filename
# isn't the last part of the url and the file extenstion isn't "tar.gz"
packages = \
    [
        {
            "name": "lighttpd",
            "type": "generic",
            "version": "1.4.31",
            "url": "http://download.lighttpd.net/lighttpd/releases-1.4.x/lighttpd-1.4.31.tar.gz",
            "build": [
                "./configure --prefix=/usr/local/lighttpd --with-openssl",
                "make",
                "make install",
                "mkdir -p /usr/local/lighttpd/etc/lighttpd",
                "mkdir -p /usr/local/lighttpd/www/htdocs",
                "cp -r %s/lighttpd/conf/* /usr/local/lighttpd/etc/lighttpd" % (contrib_path,),
                "cp %s/lighttpd/init/lighttpd /etc/init.d" % (contrib_path,),
                "groupadd lighttpd",
                "useradd -g lighttpd lighttpd",
                "mkdir /var/log/lighttpd",
                "chown lighttpd:lighttpd /var/log/lighttpd",
                "cp %s/lighttpd/logrotate/* /etc/logrotate.d" % (contrib_path,)
            ]
        },
            {
            "name": "Python",
            "type": "generic",
            "version": "2.7.3",
            "url": "http://www.python.org/ftp/python/2.7.3/Python-2.7.3.tgz",
            "ext": "tgz",
            "build": [
                "./configure --prefix=/usr/local/python-2.7",
                "make",
                "make install",
                "cd .."
            ]
        },
            {
            "name": "setuptools",
            "type": "python",
            "version": "0.6c11",
            "url": "http://pypi.python.org/packages/source/s/setuptools/setuptools-0.6c11.tar.gz#md5=7df2a529a074f613b509fb44feefe74e"
        },
        {
            "name": "flup",
            "type": "python",
            "version": "1.0.2",
            "url": "http://www.saddi.com/software/flup/dist/flup-1.0.2.tar.gz"
        },
        {
            "name": "pycrypto",
            "type": "python",
            "version": "2.6",
            "url": "ftp://ftp.dlitz.net/pub/dlitz/crypto/pycrypto/pycrypto-2.6.tar.gz"
        },
        {
            "name": "paramiko",
            "type": "python",
            "version": "1.7.7.1",
            "url": "http://www.lag.net/paramiko/download/paramiko-1.7.7.1.tar.gz"
        },
        {
            "name": "Django",
            "type": "python",
            "version": "1.4.1",
            "url": "https://www.djangoproject.com/download/1.4.1/tarball/",
            "filename": "Django-1.4.1.tar.gz"
        },
        {
            "name": "skd",
            "type": "generic",
            "version": "1.0b",
            "url": "https://github.com/dploeger/skd/tarball/master",
            "build": [
                "mkdir /usr/local/skd",
                "cp -r * /usr/local/skd",
                "cp %s/skd/local_settings.py /usr/local/skd/skd" % (contrib_path,),
                "cd /usr/local/skd",
                "export LC_ALL=en_US",
                "/usr/local/python-2.7/bin/python manage.py syncdb",
                "cp %s/skd/skd-fcgid /etc/init.d" % (contrib_path,)
            ]
        }
    ]

# Post-Build script.
post_build = [
    "# SSL-Certificate",
    "cp %s/skd/openssl.cnf /etc/ssl" % (contrib_path),
    "mkdir /usr/local/lighttpd/etc/ssl",
    "cd /usr/local/lighttpd/etc/ssl",
    "openssl genrsa -out server.key 1024",
    "openssl req -new -batch -key server.key -out server.csr",
    "openssl x509 -req -days 365 -in server.csr -out server.crt -signkey server.key",
    "cat server.key server.crt > server.pem",
    "",
    "# Start",
    "/etc/init.d/skd-fcgid start",
    "/etc/init.d/lighttpd start",
    "",
    "# Startup",
    "",
    "update-rc.d skd-fcgid defaults",
    "update-rc.d lighttpd defaults"
]

# Path to python-executable to be used in "python"-packages
python_path = "/usr/local/python-2.7/bin/python"

# Dialog titles

welcome_dialog_title = "[s][k][d]"
welcome_dialog_text = "\\n".join(
    [
        "Welcome to the skd virtual Appliance",
        "====================================",
        "",
        "The appliance will now be set up. This might take a while.",
        "At one time the installation process will ask you about a Django "
        "superuser. This will be the user you log into skd with and will be "
        "your skd administrator."
    ]
)

finish_dialog_title = welcome_dialog_title
finish_dialog_text = "\\n".join(
    [
        "Installation completed",
        "======================",
        "",
        "The appliance installation has finished. You can now visit the "
        "skd basic setup at https://<skd-host>/setup"
    ]
)