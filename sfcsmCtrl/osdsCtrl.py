# Alain Dechorgnat
# 05/19/2014

from flask import Flask, request, Response
import json
import time
import requests
from array import *


def getCephRestApiUrl(request):
    # discover ceph-rest-api URL
    return request.url_root.replace("sfcsmCtrl","ceph-rest-api")

class Osds:
    """docstring for Osds"""
    def __init__(self):
        pass


class OsdsCtrl:
    def __init__(self,conf,fsid):
        self.cluster_name = conf['cluster']
        ceph_rest_api_subfolder = conf.get("ceph_rest_api_subfolder", "")
        ceph_rest_api_subfolder = ceph_rest_api_subfolder.strip('/')
        if ceph_rest_api_subfolder != '':
            ceph_rest_api_subfolder = "/" + ceph_rest_api_subfolder
        self.cephRestApiUrl = "http://"+conf.get("ceph_rest_api", "")+ceph_rest_api_subfolder+"/api/v0.1/"
        self.sfcsmRestApiUrl = "http://"+conf.get("ceph_rest_api", "")+"/sfcsmCtrl/"+fsid+"/"
        pass

    def getCephRestApiUrl(self):
        return self.cephRestApiUrl
    def getSfcsmRestApiUrl(self):
        return self.sfcsmRestApiUrl

    def get_osds(self):
        sfcsmRestApiUrl = self.getSfcsmRestApiUrl()
        result = requests.get(sfcsmRestApiUrl+'osd?depth=1')
        result = json.loads(result.content)
        osds = []
        for r in result:
            osd = {}
            osd['name'] = r['node']['name']
            osd['osdid'] = r['node']['_id']
            osd['hostip'] = r['host']['hostip']
            osd['hostname'] = r['host']['_id']
            osd['up'] = r['stat']['up']
            osd['in'] = r['stat']['in']
            osd['partition'] = r['partition']['dev']
            osd['mountpoint'] = r['partition']['mountpoint']
            osd['weight'] = r['stat']['weight']
            osds.append(osd)
        return Response(json.dumps(osds), mimetype='application/json')

    def set_osd_status(self, db):
        data = request.data
        data = json.loads(data)
        cephRestApiUrl = self.getCephRestApiUrl()
        oplog = {}
        # oplog['operator'] = current_user
        oplog['operator'] = "test"
        oplog['description '] = 'make osd' + data['osdid'] +' '+ data['stat']
        oplog['optype'] = 'N'
        oplog['destip'] = 'all'
        r = requests.put(cephRestApiUrl+'osd/'+data['stat']+'?ids='+data['osdid'])
        oplog['operateTime'] = int(round(time.time() * 1000))
        if r.status_code == 200:
            oplog['opstatus'] = 1
            db.operationlog.insert(oplog)
            return Response('success', status=r.status_code)
        else:
            oplog['opstatus'] = 2
            db.operationlog.insert(oplog)
            return Response(r.reason, status=r.status_code)


    def osds_manage(id):
        cephRestApiUrl = getCephRestApiUrl(request);
        action = request.form.get("action","none");
        if action == "reweight-by-utilisation" :
            print "reweight-by-utilisation"
            r = requests.put(cephRestApiUrl+'osd/reweight-by-utilization')
            print str(r.content)
            return str(r.content)
        else :
            print "unknown command"
