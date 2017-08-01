# Alain Dechorgnat
# 05/19/2014

from flask import Flask, request, Response
import json
import requests
import re
from array import *
import sys
sys.path.append("..")
from sfcsmUtil.operate import Operate

class Monitors:
    """docstring for Osds"""
    def __init__(self):
        pass


class MonitorsCtrl:
    def __init__(self, conf):
        self.cluster_name = conf['cluster']
        ceph_rest_api_subfolder = conf.get("ceph_rest_api_subfolder", "")
        ceph_rest_api_subfolder = ceph_rest_api_subfolder.strip('/')
        if ceph_rest_api_subfolder != '':
            ceph_rest_api_subfolder = "/" + ceph_rest_api_subfolder
        self.cephRestApiUrl = "http://" + conf.get("ceph_rest_api", "") + ceph_rest_api_subfolder + "/api/v0.1/"
        pass

    def getCephRestApiUrl(self):
        return self.cephRestApiUrl

    def monsList(self):
        cephRestApiUrl = self.getCephRestApiUrl()
        stats = requests.get(cephRestApiUrl + 'status.json')
        if stats.status_code != 200:
            return Response(stats.raise_for_status())
        stats = json.loads(stats.content)['output']
        monmap = stats['monmap']['mons']
        # print monmap
        monHealth = stats['health']['health']['health_services'][0]['mons']
        # print monHealth
        mons = []
        for m in monmap:
            mon = {}
            mon['name'] = m['name']
            mon['rank'] = m['rank']
            reip = re.compile(r'(?<![\.\d])(?:\d{1,3}\.){3}\d{1,3}(?![\.\d])')
            mon['addr'] = reip.findall(m['addr'])[0]
            for i in monHealth:
                if m['name'] == i['name']:
                    mon['health'] = i['health']
                    if i.has_key('health_detail'):
                        mon['health_detail'] = i['health_detail']
            mons.append(mon)
        return Response(json.dumps(mons), mimetype='application/json')



