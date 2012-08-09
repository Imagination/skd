#
# [s][k][d] virtual appliance build file
#
from os import mkdir, chdir, unlink
import os
import shutil
import tarfile
import logging

from dist_config import *

import urllib

def download(url, filename = None):
    webFile = urllib.urlopen(url)

    if filename:
        localFile = open(filename, 'w')
    else:
        localFile = open(url.split('/')[-1], 'w')
    localFile.write(webFile.read())
    webFile.close()
    localFile.close()

logging.basicConfig(
    level=logging.DEBUG
)

logging.info("Starting distribution build")

# Cleanup

logging.info("Removing previous build")

shutil.rmtree("skd_distrib", True)

mkdir("skd_distrib")
chdir("skd_distrib")

# Cleanup

try:

    unlink("install.sh")

except OSError:

    pass

install = open("install.sh", "w")

install.writelines(
    "# [s][k][d] virtual appliance installation\n"
    "\n"
    "cd %s\n" % (base_path,)
)

logging.info("Getting additional deb-packages")

# Create tar.gz packages

# Additional DEB-Packages

# Cleanup

try:

    unlink("additional_deb.tar.gz")

except OSError:

    pass

shutil.rmtree("additional_deb", True)

# Create path

mkdir("additional_deb")
chdir("additional_deb")

# Download files

for package in deb_packages:
    logging.debug("Getting %s" % (package,))

    download(package)

chdir("..")

# Create tarfile

logging.info("Building tar.gz-file of additional deb-Packages")

additional_deb = tarfile.open("additional_deb.tar.gz", "w:gz")
additional_deb.add("additional_deb")
additional_deb.close()

# Remove working directory

shutil.rmtree("additional_deb", True)

logging.info("Writing install script for additional deb-Packages")

# Write install-Script

install.writelines(
    os.linesep.join(
        [
            "tar xzf additional_deb.tar.gz",
            "cd additional_deb",
            "",
            "dpkg -i *.deb",
            "",
            "cd ..\n"
        ]
    )
)

logging.info("Installation welcome screen")

# Show Install-Dialog

install.writelines(
    "dialog --title \"%(title)s\" --msgbox \"%(text)s\" 0 0\n" % {
        "title": welcome_dialog_title,
        "text": welcome_dialog_text
    }
)

logging.info("Building skd_contrib")

# skd_contrib

chdir("..")
skd_contrib = tarfile.open("skd_distrib/skd_contrib.tar.gz", "w:gz")
skd_contrib.add("skd_contrib")
chdir("skd_distrib")

install.writelines("tar xzf skd_contrib.tar.gz\n\n")

logging.info("Building additional packages")

# Packages

for package in packages:

    logging.info("Building %s" % (package["name"]))

    logging.debug("Downloading %s" % (package["url"]))

    filename = None

    if "filename" in package:
        filename = package["filename"]

    download(package["url"], filename)

    ext = "tar.gz"

    if "ext" in package:
        ext = package["ext"]

    logging.debug("Writing install script")

    install.writelines(
        "# %(name)s %(version)s\n\n"
        "tar xzf %(name)s-%(version)s.%(ext)s\n"
        "rm %(name)s-%(version)s.%(ext)s\n"
        "cd %(name)s-%(version)s\n"
        % {
            "name": package["name"],
            "version": package["version"],
            "ext": ext
        }
    )

    if package["type"] == "python":

        # Python module installation

        install.writelines(
            "%(python)s setup.py install"
            % {
                "python": python_path
            }
        )

    else:

        # Generic installation

        install.writelines(
            os.linesep.join(package["build"])
        )

    install.writelines(
        "\n"
        "cd ..\n"
        "rm -fr %(name)s-%(version)s\n\n"
        % {
            "name": package["name"],
            "version": package["version"]
        }
    )

# Postbuild

logging.info("Writing postbuild")

install.writelines(
    os.linesep.join(post_build)
)

install.writelines("\n")

# Cleanup

logging.info("Writing cleanup")

install.writelines(
    "# Cleanup\n"
    "\n"
    "rm -r /%s\n" % (base_path)
)

# Finish dialog

logging.info("Writing Finish-Screen")

install.writelines(
    "dialog --title \"%(title)s\" --msgbox \"%(text)s\" 0 0\n" % {
        "title": finish_dialog_title,
        "text": finish_dialog_text
    }
)

# Close Installscript

install.close()

# Finish

chdir("..")

# Tar skd_distrib

logging.info("Tarring distribution")

skd_distrib = tarfile.open("skd_distrib.tar.gz", "w:gz")
skd_distrib.add("skd_distrib")
skd_distrib.close()

logging.info("Removing work directory")

shutil.rmtree("skd_distrib", True)

logging.info("Done")