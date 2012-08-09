skd
===

[s]IMPLE [k]EY [d]ISTRIBUTION

Appliance Branch
----------------

In this branch the configuration files for a virtual appliance (currently
supported in OVA-format built using VMware Studio) with python, django,
a https-configured lighttpd and skd are held.

Use python makedist.py in the skd_dist-directory  to download the currently
used packages and build a tar.gz-file to be deployed and unpacked in / in the
 virtual appliance.

Building in VMware Studio
-------------------------

To build the appliance in VMware Studio, you first have to create a new
template for Ubuntu 10.4.4 and download the appropriate ISO for it.

To do this. Copy the vmware-studio/templates/044_amd64 directory into
/opt/vmware/etc/build/templates/ubuntu/10 of your VMware Studio appliance,
 download the ISO-file ubuntu-10.04.4-server-amd64.iso with the md5sum of
 9b218654cdcdf9722171648c52f8a088 from any Ubuntu mirror and put it into
 /opt/vmware/depot/ISO

Now create a directory /opt/vmware/www/ubuntu_skd and copy the
distribution-tar.gz-file ("skd_distrib.tar.gz") into it. Name it with a version
number (like skd-dist-1.0b.tar.gz) to avoid conversion into .deb-format.

Finally copy the skd-profile vmware-studio/profile/skd.xml to
/opt/vmware/var/lib/build/profiles in your VMware Studio appliance,
fire up the web interface of it and build the profile.

After building you can download the OVA-file from the web interface.