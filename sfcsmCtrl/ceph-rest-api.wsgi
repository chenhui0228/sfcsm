# Launching ceph-rest-api with Apache
# author Chen Hui 01107267
# inspired by Wido den Hollander wsgi script

import json
import ceph_rest_api
import os, sys

# change dir for sfcsmCtrl folder
abspath = os.path.dirname(__file__)
sys.path.append(abspath)
os.chdir(abspath)

from Log import Log

# Load sfcsm configuration from file
sfcsm_config_file = "/opt/sfcsm/etc/sfcsm.conf"
datasource = open(sfcsm_config_file, "r")
sfcsm_config = json.load(datasource)
datasource.close()

ceph_config_file=sfcsm_config.get("ceph_conf", "/etc/ceph/ceph.conf").encode('ascii', 'ignore')
ceph_cluster_name="ceph"
ceph_client_name=None
ceph_client_id="restapi"
args=None

application = ceph_rest_api.generate_app(ceph_config_file, ceph_cluster_name, ceph_client_name, ceph_client_id, args)