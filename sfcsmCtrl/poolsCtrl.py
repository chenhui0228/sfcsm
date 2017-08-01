# -*- coding: UTF-8 -*-
# chenhui 01107267
# 05/25/2017

from flask import request, Response
import json
import requests
import time
from OperateLog import OperateLog
from array import *
import subprocess
from StringIO import StringIO
from SfcsmError import SfcsmError
import sys
# sys.path.append("../..")
# from sfcsmUtil.OperateLog import OperateLog

class Pools:
    """docstring for pools"""
    def __init__(self):
        pass

    def newpool_attribute(self, jsonform):
        jsondata = json.loads(jsonform)
        self.name = None
        self.pg_num = None
        self.pgp_num = None
        self.type = None
        self.size = None
        self.min_size = None
        self.crash_replay_interval = None
        self.crush_ruleset = None
        self.erasure_code_profile = None
        self.quota_max_objects = None
        self.quota_max_bytes = None
        if jsondata.has_key('pool_name'):
            self.name = jsondata['pool_name']
        if jsondata.has_key('pg_num'):
            self.pg_num = jsondata['pg_num']
        if jsondata.has_key('pg_placement_num'):
            self.pgp_num = jsondata['pg_placement_num']
        if jsondata.has_key('type'):
            self.type = jsondata['type']
        if jsondata.has_key('size'):
            self.size = jsondata['size']
        if jsondata.has_key('min_size'):
            self.min_size = jsondata['min_size']
        if jsondata.has_key('crash_replay_interval'):
            self.crash_replay_interval = jsondata['crash_replay_interval']
        if jsondata.has_key('crush_ruleset'):
            self.crush_ruleset = jsondata['crush_ruleset']
        if jsondata.has_key('erasure_code_profile'):
            self.erasure_code_profile = jsondata['erasure_code_profile']
        if jsondata.has_key('quota_max_objects'):
            self.quota_max_objects = jsondata['quota_max_objects']
        if jsondata.has_key('quota_max_bytes'):
            self.quota_max_bytes = jsondata['quota_max_bytes']

    def savedpool_attribute(self, ind, jsonfile):
        r = jsonfile.json()
        self.name = r['output']['pools'][ind]['pool_name']
        self.pg_num = r['output']['pools'][ind]['pg_num']
        self.pgp_num = r['output']['pools'][ind]['pg_placement_num']
        self.type = r['output']['pools'][ind]['type']
        self.size = r['output']['pools'][ind]['size']
        self.min_size = r['output']['pools'][ind]['min_size']
        self.crash_replay_interval = r['output']['pools'][ind]['crash_replay_interval']
        self.crush_ruleset = r['output']['pools'][ind]['crush_ruleset']
        self.erasure_code_profile = r['output']['pools'][ind]['erasure_code_profile']
        self.quota_max_objects = r['output']['pools'][ind]['quota_max_objects']
        self.quota_max_bytes = r['output']['pools'][ind]['quota_max_bytes']

    # create a pool
    def register(self):
        uri = self.cephRestApiUrl+'osd/pool/create?pool='+self.name+'&pool_type='+self.type+'&pg_num='+str(self.pg_num)+'&pgp_num='+str(self.pgp_num)
        if self.erasure_code_profile != "" and self.erasure_code_profile is not None:
            uri += '&erasure_code_profile='+self.erasure_code_profile
        register_pool = requests.put(uri)
        # if newpool.register().status_code != 200:
        # #     return 'Error '+str(r.status_code)+' on creating pools'
        # else:
        return register_pool


def writeOperateLog1(operator, optype, destip, description, opstatus, db):
    oplog = {}
    # oplog['operator'] = current_user
    oplog['operator'] = operator
    oplog['optype'] = optype
    oplog['destip'] = destip
    oplog['description'] = description
    oplog['operateTime'] = int(round(time.time() * 1000))
    oplog['opstatus'] = opstatus
    db.operationlog.insert(oplog)

class PoolsCtrl:
    def __init__(self,conf):
        self.cluster_name = conf['cluster']
        ceph_rest_api_subfolder = conf.get("ceph_rest_api_subfolder", "")
        ceph_rest_api_subfolder = ceph_rest_api_subfolder.strip('/')
        if ceph_rest_api_subfolder != '':
            ceph_rest_api_subfolder = "/" + ceph_rest_api_subfolder
        self.cephRestApiUrl = "http://"+conf.get("ceph_rest_api", "")+ceph_rest_api_subfolder+"/api/v0.1/"
        pass

    def getCephRestApiUrl(self):
        return self.cephRestApiUrl

    # 根据pools json数组中key pool对应的value值，确定pool在pools json中的位置
    def getindice(self,id, jsondata):
        r = jsondata.content
        r = json.loads(r)
        mypoolsnum = array('i',[])
        for i in r['output']['pools']:
            mypoolsnum.append(i[u'pool'])
        if id not in  mypoolsnum:
            return "Pool not found"
    
        else:
            for i in range(len(mypoolsnum)):
                if mypoolsnum[i]==id:
                    id=i
            return id
    
    # 根据确定的数组下标在pools中取出对应pool的name
    def getpoolname(self,ind, jsondata):
    
        r = jsondata.json()
        poolname = r['output']['pools'][ind]['pool_name']
    
        return str(poolname)
    
    # 检查pool：①检查pool_id（poolnum）是否存在；②检查pool name是否已经存在
    def checkpool(self,pool_id, jsondata):
        skeleton = {}
        if isinstance(pool_id, int):
            ind = self.getindice(pool_id, jsondata)
            id = ind
            if id == "Pool id not found":
                skeleton['status'] = 'ERROR'
                skeleton['errorMessage'] = "Pool id " + str(pool_id) + "not found"
                # result = json.dumps(skeleton)
                #return Response(result, mimetype='application/json')
                return skeleton
            else:
                skeleton['status'] = 'OK'
                # result = json.dumps(skeleton)
                #return Response(result, mimetype='application/json')
                return skeleton
        if isinstance(pool_id, str):
            # r = jsondata.content
            r = jsondata
            mypoolsname = []
            # for i in r['output']:
            for i in r:
                mypoolsname.append(i[u'poolname'])
            if pool_id not in  mypoolsname:
                skeleton['status'] = 'OK'
                # result = json.dumps(skeleton)
                #return Response(result, mimetype='application/json')
                return skeleton
            else:
                skeleton['status'] = 'ERROR'
                skeleton['errorMessage'] = pool_id+' already exits. Please enter a new pool name'
                # result = json.dumps(skeleton)
                #return Response(result, mimetype='application/json')
                return skeleton
    
    # 获取集群所有pool，返回含所有pool的json字符串
    def pool_list1(self):
        args = ['ceph',
                'osd',
                'lspools',
                '--format=json',
                '--cluster='+ self.cluster_name ]
        output = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
        # output_io = StringIO(output)
        return json.loads(output.strip())

    def pool_list(self):
        cephRestApiUrl = self.getCephRestApiUrl()
        df = requests.get(cephRestApiUrl+'df.json?detail=detail')
        if df.status_code != 200:
            return Response(df.raise_for_status())
        osd_dump = requests.get(cephRestApiUrl+'osd/dump.json')
        pl = {}
        bytesUsedTotal = 0
        objectTotal = 0
        pools = []
        if osd_dump.status_code != 200:
            return Response(osd_dump.raise_for_status())
        ro = json.loads(osd_dump.content)['output']
        rd = json.loads(df.content)['output']
        for p in json.loads(df.content)['output']['pools']:
            pool = {}
            poolId = p['id']
            ind = self.getindice(poolId, osd_dump)
            pool['id'] = p['id']
            pool['name'] = p['name']
            pool['bytes_used'] = p['stats']['bytes_used']
            pool['objects'] = p['stats']['objects']
            pool['pg_num'] = ro['pools'][ind]['pg_num']
            pool['type'] = ro['pools'][ind]['type']
            pool['size'] = ro['pools'][ind]['size']
            pools.append(pool)
        pl['pools'] = pools
        pl['bytes_used_total'] = rd['stats']['total_used_bytes']
        pl['objects_total'] = rd['stats']['total_objects']
        return Response(json.dumps(pl), mimetype='application/json')



    #
    # @app.route('/pools/', methods=['GET','POST'])
    # @app.route('/pools/<int:id>', methods=['GET','DELETE','PUT'])
    def pool_manage(self,id,db):
        cephRestApiUrl = self.getCephRestApiUrl()

        if request.method == 'GET':
            if id == None:
                # 和pool_list方法功能一样
                r = requests.get(cephRestApiUrl+'osd/lspools.json')
    
                if r.status_code != 200:
                    return Response(r.raise_for_status())
                else:
                    r = r.content
                    return Response(r, mimetype='application/json')
    
            else:
                # 根据pool id 获取指定的pool信息
                data = requests.get(cephRestApiUrl+'osd/dump.json')
                if data.status_code != 200:
                    raise SfcsmError( data.status_code, 'Error '+str(data.status_code)+' on the request getting pools: '+data.content)
                else:

                    ind = self.getindice(id, data)
                    id = ind
                    skeleton = {'status':'','output':{}}
                    if id == "Pool id not found":
                        skeleton['status'] = id
                        result = json.dumps(skeleton)
                        return Response(result, mimetype='application/json')
    
                    else:
    
                        r = data.content
                        r = json.loads(r)
                        #r = data.json()
                        skeleton['status'] = r['status']
                        skeleton['output'] = r['output']['pools'][id]
    
                        result = json.dumps(skeleton)
                        return Response(result, mimetype='application/json')
    
        elif request.method =='POST':
            # create  a pool
            jsonform = request.form['json']
            newpool = Pools()
            newpool.cephRestApiUrl = cephRestApiUrl
            newpool.newpool_attribute(jsonform)
            r = self.checkpool(str(newpool.name), self.pool_list1())
            if r['status'] != "OK":
                return Response(json.dumps(r), mimetype='application/json')
            rep = newpool.register()
            if rep.status_code == 200:
                loginfo = "create a pool, pool name is " + json.loads(jsonform)['pool_name']
                OperateLog().writeOperateLog("test", "N", "all", loginfo, 1, db)
            else:
                raise SfcsmError(rep.status_code, rep.content)
            jsondata = requests.get(cephRestApiUrl+'osd/dump.json')
            #取出json格式内容
            r = jsondata.content
            #json转为字典类型
            r = json.loads(r)
            #r = jsondata.json()
            nbpool = len(r['output']['pools'])
            poolcreated = Pools()
            poolcreated.savedpool_attribute(nbpool-1, jsondata)
            # set pool parameter
    
            var_name= ['size', 'min_size', 'crash_replay_interval','crush_ruleset']
            param_to_set_list = [newpool.size, newpool.min_size, newpool.crash_replay_interval, newpool.crush_ruleset]
            default_param_list = [poolcreated.size, poolcreated.min_size, poolcreated.crash_replay_interval, poolcreated.crush_ruleset]
    
            for i in range(len(default_param_list)):
                if param_to_set_list[i] != default_param_list[i] and param_to_set_list[i] != None:
                    r = requests.put(cephRestApiUrl+'osd/pool/set?pool='+str(poolcreated.name)+'&var='+var_name[i]+'&val='+str(param_to_set_list[i]))
                    if r.status_code == 200:
                        loginfo = "set pool [" + str(poolcreated.name) + "] parameter [" + var_name[i] + "] , the value is [" + str(param_to_set_list[i]) + "]."
                        OperateLog().writeOperateLog("test", "N", "all", loginfo, 1, db)
                    else:
                        raise SfcsmError(r.status_code, r.content)
                else:
                    pass
    
            # set object or byte limit on pool
    
            field_name = ['max_objects','max_bytes']
            param_to_set = [newpool.quota_max_objects, newpool.quota_max_bytes]
            default_param = [poolcreated.quota_max_objects, poolcreated.quota_max_bytes]
    
            for i in range(len(default_param)):
                if param_to_set[i] != default_param[i] and param_to_set[i] != None:
                    r = requests.put(cephRestApiUrl+'osd/pool/set-quota?pool='+str(poolcreated.name)+'&field='+field_name[i]+'&val='+str(param_to_set[i]))
                    if r.status_code == 200:
                        loginfo = "set object or byte limit on  pool [" + str(poolcreated.name) + "] parameter [" + field_name[i] + "] , the value is [" + str(param_to_set[i]) + "]."
                        OperateLog().writeOperateLog("test", "N", "all", loginfo, 1, db)
                    else:
                        raise SfcsmError(r.status_code, r.content)
                else:
                    pass
            return Response("success", status=200)
    
        elif request.method == 'DELETE':
            data = requests.get(cephRestApiUrl+'osd/dump.json')
            # if data.status_code != 200:
            #     return 'Error '+str(r.status_code)+' on the request getting pools'
            # else:
            #r = data.json()
            r = data.content
            r = json.loads(r)
    
            # data = requests.get('http://localhost:8080/ceph-rest-api/osd/dump.json')
            ind = self.getindice(id, data)
            id = ind
    
            poolname = r['output']['pools'][id]['pool_name']
            poolname = str(poolname)
            delete_request = requests.put(cephRestApiUrl+'osd/pool/delete?pool='+poolname+'&pool2='+poolname+'&sure=--yes-i-really-really-mean-it')
            if delete_request.status_code == 200:
                loginfo = "delete a pool [" + poolname + "]."
                OperateLog().writeOperateLog("test", "N", "all", loginfo, 1, db)
            else:
                raise SfcsmError(delete_request.status_code, delete_request.content)
            # print("Delete code ", delete_request.status_code)
            # print("Delete message ",delete_request.content)
            return "pool has been deleted"
    
        else:
    
            jsonform = request.form['json']
            newpool = Pools()
            newpool.newpool_attribute(jsonform)
    
            data = requests.get(cephRestApiUrl+'osd/dump.json')
            if data.status_code != 200:
                raise SfcsmError( data.status_code, 'Error '+str(data.status_code)+' on the request getting pools: '+data.content)
            else:
                #r = data.json()
                r = data.content
                r = json.loads(r)
                ind = self.getindice(id, data)
                savedpool = Pools()
                savedpool.savedpool_attribute(ind, data)
    
                # rename the poolname
    
                if str(newpool.name) != str(savedpool.name) and newpool.name != None:
                    r = requests.put(cephRestApiUrl+'osd/pool/rename?srcpool='+str(savedpool.name)+'&destpool='+str(newpool.name))
                    if r.status_code == 200:
                        loginfo = "rename pool, old name is [" + str(savedpool.name) + "], new name is [" + str(newpool.name) + "]"
                        OperateLog().writeOperateLog("test", "N", "all", loginfo, 1, db)
                    else:
                        raise SfcsmError(r.status_code, r.content)
    
                # set pool parameter
    
                var_name= ['pg_num','size', 'min_size', 'crash_replay_interval','crush_ruleset','pgp_num']
                param_to_set_list = [newpool.pg_num, newpool.size, newpool.min_size, newpool.crash_replay_interval, newpool.crush_ruleset, newpool.pgp_num]
                default_param_list = [savedpool.pg_num, savedpool.size, savedpool.min_size, savedpool.crash_replay_interval, savedpool.crush_ruleset, savedpool.pgp_num]

                message = ""
                for i in range(len(default_param_list)):
                    if param_to_set_list[i] != default_param_list[i] and param_to_set_list[i] != None:
                        r = requests.put(cephRestApiUrl+'osd/pool/set?pool='+str(newpool.name)+'&var='+var_name[i]+'&val='+str(param_to_set_list[i]))
                        if r.status_code == 200:
                            loginfo = "modify pool [" + str(newpool.name) + "] parameter [" + var_name[i] + "] , the value is [" + str(param_to_set_list[i]) + "]."
                            OperateLog().writeOperateLog("test", "N", "all", loginfo, 1, db)
                        else:
                            raise SfcsmError(r.status_code, r.content)
                    else:
                        pass
    
                # set object or byte limit on pool
    
                field_name = ['max_objects','max_bytes']
                param_to_set = [newpool.quota_max_objects, newpool.quota_max_bytes]
                default_param = [savedpool.quota_max_objects, savedpool.quota_max_bytes]
    
                for i in range(len(default_param)):
                    if param_to_set[i] != default_param[i] and param_to_set[i] != None:
                        r = requests.put(cephRestApiUrl+'osd/pool/set-quota?pool='+str(newpool.name)+'&field='+field_name[i]+'&val='+str(param_to_set[i]))
                        if r.status_code == 200:
                            loginfo = "modify object or byte limit on  pool [" + str(newpool.name) + "] parameter [" + field_name[i] + "] , the value is [" + str(param_to_set[i]) + "]."
                            OperateLog().writeOperateLog("test", "N", "all", loginfo, 1, db)
                        else:
                            raise SfcsmError(r.status_code, r.content)
                        # if r.status_code != 200:
                        #     message= message+ "Can't set "+ field_name[i]+ " to "+ str(param_to_set[i])+ " : "+ r.content+"<br>"
                    else:
                        pass

                return message
    
    
    # @app.route('/pools/<int:id>/snapshot', methods=['POST'])
    def makesnapshot(self,id):
        cephRestApiUrl = self.getCephRestApiUrl();
        data = requests.get(cephRestApiUrl+'osd/dump.json')
        #r = data.json()
        r = data.content
        r = json.loads(r)
        ind = self.getindice(id,data)
        id = ind
    
        poolname = r['output']['pools'][id]['pool_name']
    
        jsondata = request.form['json']
        jsondata = json.loads(jsondata)
        snap = jsondata['snapshot_name']
        r = requests.put(cephRestApiUrl+'osd/pool/mksnap?pool='+str(poolname)+'&snap='+str(snap))
        if r.status_code != 200:
                raise SfcsmError(r.status_code, r.content)
        return r.content
    
    
    # @app.route('/pools/<int:id>/snapshot/<namesnapshot>', methods=['DELETE'])
    def removesnapshot(self,id, namesnapshot):
        cephRestApiUrl = self.getCephRestApiUrl();
        data = requests.get(cephRestApiUrl+'osd/dump.json')
        #r = data.json()
        r = data.content
        r = json.loads(r)
        ind = self.getindice(id,data)
        id = ind
    
        poolname = r['output']['pools'][id]['pool_name']
    
        r = requests.put(cephRestApiUrl+'osd/pool/rmsnap?pool='+str(poolname)+'&snap='+str(namesnapshot))
        if r.status_code != 200:
                raise SfcsmError(r.status_code, r.content)
        return r.content