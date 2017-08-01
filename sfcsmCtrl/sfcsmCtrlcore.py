#-*- coding: UTF-8 -*-
# 01107267
# 03/24/2017


from flask import Flask, Response, redirect
from flask_login import (LoginManager, login_required, login_user,
                         current_user, logout_user, UserMixin)
from itsdangerous import URLSafeTimedSerializer
from datetime import timedelta
from datetime import datetime
from hashlib import md5
from bson.json_util import dumps
from SfcsmError import SfcsmError

from pymongo import MongoClient
from pymongo import MongoReplicaSetClient
from bson import ObjectId

version = "1.4.0"

app = Flask(__name__)
app.secret_key = "Mon Nov 30 17:20:29 2015"
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=14)

#Login_serializer used to encryt and decrypt the cookie token for the remember
#me option of flask-login
login_serializer = URLSafeTimedSerializer(app.secret_key)

login_manager = LoginManager()
login_manager.init_app(app)

from subprocess import CalledProcessError

import mongoJuiceCore
import time
import httplib

from poolsCtrl import PoolsCtrl,Pools
from osdsCtrl import OsdsCtrl,Osds
from monsCtrl import MonitorsCtrl,Monitors
from rbdCtrl import RbdCtrl
import subprocess
from StringIO import StringIO
#import probesCtrl

from S3Ctrl import S3Ctrl, S3Error
from S3ObjectCtrl import *

import sys
import os
sys.path.append(os.path.split(sys.path[0])[0])
from sfcsmUtil.OperateLog import OperateLog

def hash_pass(password):
    """
    Return the md5 hash of the password+salt
    """
    salted_password = password + app.secret_key
    return md5(salted_password).hexdigest()



# Load configuration from file
configfile = "/opt/sfcsm/etc/sfcsm.conf"
datasource = open(configfile, "r")
conf = json.load(datasource)
datasource.close()
client = None;
#ceph_rest_api = None

# get a field value from global conf according to the specifpsutil_versionied ceph conf
def ceph_conf_global(cephConfPath, field):
    p = subprocess.Popen(
        args=[
            'ceph-conf',
            '-c',
            cephConfPath,
            '--show-config-value',
            field
            ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option %s: %s' % (field, errdata))
    return outdata.rstrip()

def getfsid():
    ceph_conf_file = conf.get("ceph_conf", "/etc/ceph/ceph.conf")
    fsid = ceph_conf_global(ceph_conf_file, 'fsid')
    return fsid

def getCephRestApi():
    ceph_rest_api = conf.get("ceph_rest_api", '127.0.0.1:5000')
    return ceph_rest_api

def getCephRestApiSubfolder():
    ceph_rest_api_subfolder = conf.get("ceph_rest_api_subfolder", '')
    if ceph_rest_api_subfolder != '' and not ceph_rest_api_subfolder.startswith('/'):
        ceph_rest_api_subfolder = '/' + ceph_rest_api_subfolder
    return ceph_rest_api_subfolder

def getDbClient():
    is_mongo_replicat = conf.get("is_mongo_replicat", 0)
    mongodb_set = "'" + conf.get("mongodb_set", None) + "'"
    mongodb_replica_set = conf.get("mongodb_replicaSet", None)
    mongodb_read_preference = conf.get("mongodb_read_preference", None)
    mongodb_host = conf.get("mongodb_host", None)
    mongodb_port = conf.get("mongodb_port", None)
    if is_mongo_replicat == 1:
        # print "replicat set connexion"
        client = MongoReplicaSetClient(eval(mongodb_set), replicaSet=mongodb_replica_set,
                                       read_preference=eval(mongodb_read_preference))
    else:
        # print "no replicat set"
        client = MongoClient(mongodb_host, mongodb_port)
    return client

client = getDbClient()

# control sfcsm users  collection in mongo
# dbsfcsm = mongoJuiceCore.getClient(conf, 'sfcsm')
dbsfcsm = client['sfcsm']
fsid = getfsid()
dbcluster = client[fsid]
if dbsfcsm.sfcsm_users.count() == 0:
    print "list users is empty: populating with default users"
    user = {"name":"sfcsmAdm",
            "password": hash_pass("sf01107267."),
            "roles":["admin"],
            "createTime":int(round(time.time() * 1000)),
            "creator":"system"}
    dbsfcsm.sfcsm_users.insert(user)
    user = {"name":"guest",
            "password": hash_pass(""),
            "roles":["general"],
            "createTime": int(round(time.time() * 1000)),
            "creator": "system"}
    dbsfcsm.sfcsm_users.insert(user)


#
# Security
# User类作为系统用户类，用户名，用户类型，创建时间，创建人
#
class User(UserMixin):

    def __init__(self, name, password, roles, createTime, creator):
        self.id = name
        self.password = password
        self.roles = roles
        self.createTime = createTime
        self.creator = creator

    @staticmethod
    def get(userid):
        """
        Static method to search the database and see if userid exists.  If it
        does exist then return a User Object.  If not then return None as
        required by Flask-Login.
        """
        u = dbsfcsm.sfcsm_users.find_one({"name":userid})
        if u:
            return User(u['name'], u['password'], u['roles'], u['createTime'], u['creator'])
        return None


    def get_auth_token(self):
        """
        Encode a secure token for cookie
        """
        data = [str(self.id), self.password]
        return login_serializer.dumps(data)

@app.route("/syslogs/<string:_id>", methods=["DELETE"])
def delete_syslog_from_db(_id):
    oplog = {}
    # oplog['operator'] = current_user
    oplog['operator'] = "test"
    oplog['description '] = 'delete syslog, _id is' + _id
    oplog['optype'] = 'N'
    oplog['destip'] = 'all'
    syslog = dbcluster.syslog.find({"_id": ObjectId(_id)})
    if syslog.count() !=0:
        if syslog[0]['handle_status'] == 0:
            return Response('this is a warning, can not delete, please deal with the warning first', status=601)
        dbcluster.syslog.remove({"_id":ObjectId(_id)})
        if dbcluster.syslog.find({"_id": ObjectId(_id)}).count() != 0:
            return Response('delete fail', status=600)
        else:
            oplog['operateTime'] = int(round(time.time() * 1000))
            dbcluster.operationlog.insert(oplog)
            return Response('success', status=200)
    else:
        return Response('delete fail, document is not found', status=600)

# @app.route("/syslogs/<string:_id>", methods=["PUT"])
# def update_syslog_from_db(_id):
#     oplog = {}
#     # oplog['operator'] = current_user
#     oplog['operator'] = "test"
#     oplog['description '] = 'delete syslog, _id is' + _id
#     oplog['optype'] = 'N'
#     oplog['destip'] = 'all'
#     syslog = dbcluster.syslog.find({"_id":ObjectId(_id)})
#     if syslog.count() !=0:
#         syslog[0]['']
#         dbcluster.syslog.remove({"_id":ObjectId(_id)})
#         if dbcluster.syslog.find({"_id": ObjectId(_id)}).count() != 0:
#             return Response('delete fail', status=600)
#         else:
#             oplog['operateTime'] = int(round(time.time() * 1000))
#             dbcluster.operationlog.insert(oplog)
#             return Response('success', status=200)
#     else:
#         return Response('update fail, document is not found', status=600)

@app.route("/syslogs/", methods=["GET"])
def get_syslog_from_db():
    curr_time = datetime.now()
    five_day_before = curr_time - timedelta(days=5)
    timestamp = int(time.mktime(five_day_before.timetuple())*1000)
    syslogs = dbcluster.syslog.find({"occurs_time":{"$gt":timestamp}}).sort([("handle_status", 1),("log_level", -1),("occurs_time", -1)])
    return Response(dumps(syslogs), mimetype='application/json')

@app.route("/radosgws/", methods=["GET"])
def get_rgwclients_from_db():
    rgw_clients_num = conf.get("radosgw_clients", 1)
    rgw_clients = dbcluster.radosgwprocess.find().limit(rgw_clients_num).sort([("timestamp" , -1)])
    return Response(dumps(rgw_clients), mimetype='application/json')

def get_ceph_version():
    try:
        args = ['ceph',
                '--version']
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        if p.returncode != 0:
            return "not found"
        ceph_version = re.search('[0-9]*\.[0-9]*\.[0-9]*', output)
        if ceph_version:
            return ceph_version.group(0)
        return "not found"
    except:
        return '0.0.0 (could not be found on sfcsm server - Please consider to install Ceph on it)'

def get_ceph_version_name(ceph_version):
    major, minor, revision = ceph_version.split(".")
    if major == '10':
        return 'Jewel'
    if major == '9':
        return 'Infernalis'
    if major == '0':
        minor = int(minor)
        if minor == 94:
            return 'Hammer'
        if minor > 87:
            return 'Hammer (pre-version)'
        if minor == 87:
            return 'Giant'
        if minor > 80:
            return 'Giant (pre-version)'
        if minor == 80:
            return 'Firefly'
        if minor > 72:
            return 'Firefly (pre-version)'
        if minor == 72:
            return 'Emperor'
        if minor > 67:
            return 'Emperor (pre-version)'
        if minor == 67:
            return 'Dumpling'
        if minor == 0:
            return 'Unavailable'
        return 'Really too old'


@login_manager.user_loader
def load_user(userid):
    """
    Flask-Login user_loader callback.
    The user_loader function asks this function to get a User Object or return
    None based on the userid.
    The userid was stored in the session environment by Flask-Login.
    user_loader stores the returned User object in current_user during every
    flask request.
    """
    return User.get(userid)


@login_manager.token_loader
def load_token(token):
    """
    Flask-Login token_loader callback.
    The token_loader function asks this function to take the token that was
    stored on the users computer process it to check if its valid and then
    return a User Object if its valid or None if its not valid.
    """

    #The Token itself was generated by User.get_auth_token.  So it is up to
    #us to known the format of the token data itself.

    #The Token was encrypted using itsdangerous.URLSafeTimedSerializer which
    #allows us to have a max_age on the token itself.  When the cookie is stored
    #on the users computer it also has a exipry date, but could be changed by
    #the user, so this feature allows us to enforce the exipry date of the token
    #server side and not rely on the users cookie to exipre.
    max_age = app.config["REMEMBER_COOKIE_DURATION"].total_seconds()

    #Decrypt the Security Token, data = [username, hashpass]
    data = login_serializer.loads(token, max_age=max_age)

    #Find the User
    user = User.get(data[0])

    #Check Password and return user or None
    if user and data[1] == user.password:
        return user
    return None


@app.route("/login/", methods=["GET", "POST"])
def login_page():
    """
    Web Page to Display Login Form and process form.
    """
    if request.method == "POST":
        user = User.get(request.form['name'])
        # If we found a user based on username then compare that the submitted
        # password matches the password in the database.  The password is stored
        # is a slated hash format, so you must hash the password before comparing
        # it.
        if user and hash_pass(request.form['password']) == user.password:
            login_user(user, remember=True)
            return redirect(request.args.get("next") or "/sfcsmViz/index.html")
        else:
            return redirect('/sfcsmViz/login.html?result=failed')
    return redirect("/sfcsmViz/login.html", code=302)


@app.route('/logout')
def logout():
    logout_user()
    return redirect("/sfcsmViz/login.html", code=302)


#
# global management
#
@app.route('/conf.json', methods=['GET'])
@login_required  # called by every page, so force to be identified
def conf_manage():
    #force platform field to invite admin to give a name to this instance
    conf['platform'] = conf.get('platform')
    if conf['platform'] is None or conf['platform'] == "":
        conf['platform'] = "fill 'platform' field in sfcsm.conf"
    ceph_version = get_ceph_version()
    if 'admin' in current_user.roles:
        conf['version'] = version
        conf['ceph_version'] = ceph_version
        conf['ceph_version_name'] = get_ceph_version_name(ceph_version)
        conf['roles'] = current_user.roles
        conf['username']= current_user.id
        return Response(json.dumps(conf), mimetype='application/json')
    else:
        conflite = {}
        conflite['version'] = version
        conflite['ceph_version'] = ceph_version
        conflite['ceph_version_name'] = get_ceph_version_name(ceph_version)
        conflite['roles'] = current_user.roles
        conflite['platform'] = conf.get('platform')
        conflite['cluster'] = conf.get('cluster')
        conflite['username']= current_user.id
        try:
            conflite['influxdb_endpoint'] = conf.get('influxdb_endpoint')
        except:
            pass
        return Response(json.dumps(conflite), mimetype='application/json')


@app.route('/flags', methods=['POST','PUT'])
# /<string:op>/<string:key>/<string:destip>
def set_cluster_flags():
    ceph_rest_api = getCephRestApi()
    ceph_rest_api_subfolder = getCephRestApiSubfolder()
    restapi = httplib.HTTPConnection(ceph_rest_api)
    data = json.loads(request.data)
    oplog = {}
    # oplog['operator'] = current_user
    oplog['operator'] = "test"
    oplog['description '] = data['key'] + ' flag(s) ' + data['operate']
    oplog['optype'] = 'N'
    oplog['destip'] = 'all'

    try:
        restapi.connect()
        restapi.request("PUT", ceph_rest_api_subfolder + "/api/v0.1/osd/" + data['operate'] + "?key=" + data['key'])
        r1=restapi.getresponse()
    except Exception, e:
        print str(datetime.datetime.now()), "-- error (Status) failed to connect to ceph rest api: ", e.message
        restapi.close()
        raise e

    if r1.status != 200:
        print str(datetime.datetime.now()), "-- error (Status) failed to connect to ceph rest api: ", r1.status, r1.reason
        # oplog['operator'] = current_user
        oplog['operateTime'] = int(round(time.time() * 1000))
        oplog['opstatus'] = 2
        dbcluster.operationlog.insert(oplog)
        restapi.close()
        return Response(r1.reason, r1.status)
    else:
        # oplog['operator'] = current_user
        oplog['operateTime'] = int(round(time.time() * 1000))
        oplog['opstatus'] = 1
        dbcluster.operationlog.insert(oplog)
        restapi.close()
        return Response('ok', status=200)

#
# sfcsm users management
#
@app.route('/sfcsm_user/', methods=['GET'])
def sfcsm_user_list():
    return Response(dumps(dbsfcsm.sfcsm_users.find()))

# 平台用户管理
@app.route('/sfcsm_user/<id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def sfcsm_user_manage(id):
    if request.method == 'GET':
        # user info
        return  Response(dumps(dbsfcsm.sfcsm_users.find_one({"name":id})))

    elif request.method == 'POST':
        # user creation
        if 'admin' not in current_user.roles:
            return Response("Not enough permissions to do this", status=403)
        if dbsfcsm.sfcsm_users.find_one({"name":id}):
            return Response("This user already exists", status=403)
        user = json.loads(request.data)
        user['password']= hash_pass(user['password'])
        if user['roles'] != 'admin':
            user['roles'] = 'general'
        user['creator'] = current_user.id
        if 'email' not in user:
            user['email'] = ''
        user['createTime'] = int(round(time.time() * 1000))
        dbsfcsm.sfcsm_users.insert(user)
        loginfo = "Create new user "+str(id)
        OperateLog.writeOperateLog("test", "N", "all", loginfo, 1, dbcluster)
        return Response('ok', status=201)

    elif request.method == 'PUT':
        # user modification
        if 'admin' not in current_user.roles:
            return Response("Not enough permissions to do this", status=403)
        print 'old', dumps(dbsfcsm.sfcsm_users.find_one({"name":id}))
        user = json.loads(request.data)
        if 'newpassword' in user:
            user['password']= hash_pass(user['newpassword'])
            del user['newpassword']
        # del user['_id']

        print 'rep', dumps(user)
        # newuser = dbsfcsm.sfcsm_users.save({"name":id}, user)
        newuser = dbsfcsm.sfcsm_users.update({"name": id}, user)
        print 'new', dumps(dbsfcsm.sfcsm_users.find_one({"name":id}))
        loginfo = "Modify user info " + str(id)
        OperateLog.writeOperateLog("test", "N", "all", loginfo, 1, dbcluster)
        return Response('ok')

    elif request.method == 'DELETE':
        # user deletion
        if 'admin' not in current_user.roles:
            return Response("Not enough permissions to do this", status=403)
        if current_user.id == id:
            return Response("You can't delete yourself", status=403)
        else:
            dbsfcsm.sfcsm_users.remove({"name":id})
            loginfo = "Remove user " + str(id)
            OperateLog.writeOperateLog("test", "N", "all", loginfo, 1, dbcluster)
            return Response('ok')


@app.route('/sfcsm_user_role/', methods=['GET'])
def sfcsm_user_role_list():
    # roles = ["admin","admin_rgw","admin_rbd","admin_pool","general"]
    roles = ["admin", "general"]
    return Response(dumps(roles), mimetype='application/json')


#
# mongoDB query facility
#
@app.route('/<db>/<collection>', methods=['GET', 'POST'])
def find(db, collection):
    return mongoJuiceCore.find(conf, db, collection)


@app.route('/<db>', methods=['POST'])
def full(db):
    return mongoJuiceCore.full(conf, db)


#
# Pools management
#
@app.route('/poolList/', methods=['GET'])
def pool_list():
    try:
        return PoolsCtrl(conf).pool_list()
    except SfcsmError as e:
        return Response(e.message, e.status)


@app.route('/pools/', methods=['GET', 'POST'])
@app.route('/pools/<int:id>', methods=['GET', 'DELETE', 'PUT'])
def pool_manage(id=None):
    try:
        return PoolsCtrl(conf).pool_manage(id, dbcluster)
    except SfcsmError as e:
        return Response(e.message, e.status)


@app.route('/pools/<int:id>/snapshot', methods=['POST'])
def makesnapshot(id):
    try:
        return PoolsCtrl(conf).makesnapshot(id)
    except SfcsmError as e:
        return Response(e.message, e.status)


@app.route('/pools/<int:id>/snapshot/<namesnapshot>', methods=['DELETE'])
def removesnapshot(id, namesnapshot):
    try:
        return PoolsCtrl(conf).removesnapshot(id, namesnapshot)
    except SfcsmError as e:
        return Response(e.message, e.status)

@app.route('/mons/', methods=['GET'])
def monStatus():
    try:
        return MonitorsCtrl(conf).monsList()
    except SfcsmError as e:
        return Response(e.message, e.status)
    return

@app.route('/daemons/', methods=['POST'])
def daemonService():
    data = json.loads(request.data)
    oplog = {}
    # oplog['operator'] = current_user
    oplog['operator'] = "test"
    # oplog['description '] = data['key'] + ' flag(s) ' + data['operate']
    oplog['optype'] = data['optype']
    oplog['operate'] = data['operate']
    if data.has_key('opvar') and data.has_key('opval'):
        oplog['opvar'] = data['opvar']
        oplog['opval'] = data['opval']
    oplog['operateTime'] = int(round(time.time() * 1000))
    oplog['destip'] = data['destip']
    oplog['opstatus'] = 0
    dbcluster.operationlog.insert(oplog)
    return Response('operation is send successfully', status=200)

#
# Probes management
#
#@app.route('/probes/<string:probe_type>/<string:probe_name>/<string:action>', methods=['POST'])
#def actionOnProbe(probe_type, probe_name, action):
    # print "Calling  probesCtrl.action_on_probe() method", action
#    try:
#        return Response(probesCtrl.action_on_probe(probe_type, probe_name, action), mimetype='application/json')
#    except CalledProcessError, e:
#        return Response(e.output, status=500)
#

#
# Osds management
#

@app.route('/cluster/', methods=['GET'])
def get_cluster():
    # ceph_rest_api = getCephRestApi()
    sfcsmRestApiUrl = "http://" + conf.get("ceph_rest_api", "") + "/sfcsmCtrl/" + fsid + "/"
    result = requests.get(sfcsmRestApiUrl + "cluster")
    result = json.loads(result.content)
    clusters = []
    for r in result:
        cluster = {}
        cluster['fsid'] = r['_id']
        cluster['name'] = r['name']
        cluster['election_epoch'] = r['election_epoch']
        cluster['health'] = r['health']
        cluster['num_osds'] = r['osdmap_info']['num_osds']
        cluster['num_mons'] = len(r['monmap']['mons'])
        cluster['num_pgs'] = r['pgmap']['num_pgs']
        cluster['bytes_total'] = r['pgmap']['bytes_total']
        cluster['bytes_used'] = r['pgmap']['bytes_used']
        cluster['bytes_avail'] = r['pgmap']['bytes_avail']
        clusters.append(cluster)
    return Response(json.dumps(clusters), mimetype='application/json')

@app.route('/osds', methods=['PUT'])
def osds_manage(id=None):
    return OsdsCtrl.osds_manage(id)

@app.route('/osds/stat/', methods=['POST'])
def osds_stat_set():
    try:
        return OsdsCtrl(conf, fsid).set_osd_status(dbcluster)
    except SfcsmError as e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)


@app.route('/osdsList/', methods=['GET'])
def osds_list():
    try:
        return OsdsCtrl(conf,fsid).get_osds()
    except SfcsmError as e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

#
# Object storage management
#
# This method return a S3 Object that id is "objId".
# An exception is trhown if the object does not exist or there an issue
@app.route('/S3/object', methods=['GET'])
def getObjectStructure():
    Log.debug("Calling  getObjectStructure() method")
    try:
        return Response(S3ObjectCtrl(conf).getObjectStructure(),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

# User management
@app.route('/S3/user', methods=['GET'])
def listUser():
    try:
        return Response(S3Ctrl(conf).listUsers(),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user', methods=['POST'])
def createUser():
    try:
        return Response(S3Ctrl(conf).createUser(OperateLog,dbcluster),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>', methods=['GET'])
def getUser(uid):
    try:
        return Response(S3Ctrl(conf).getUser(uid),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>', methods=['PUT'])
def modifyUser(uid):
    try:
        return Response(S3Ctrl(conf).modifyUser(uid,OperateLog,dbcluster),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>', methods=['DELETE'])
def removeUser(uid):
    try:
        return Response(S3Ctrl(conf).removeUser(uid,OperateLog,dbcluster),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)


@app.route('/S3/user/<string:uid>/key/<string:key>', methods=['DELETE'])
def removeUserKey(uid,key):
    try:
        return Response(S3Ctrl(conf).removeUserKey(uid,key,OperateLog,dbcluster),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/subuser', methods=['PUT'])
def createSubuser(uid):
    try:
        return Response(S3Ctrl(conf).createSubuser(uid,OperateLog,dbcluster),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/subuser/<string:subuser>', methods=['DELETE'])
def deleteSubuser(uid, subuser):
    try:
        return Response(S3Ctrl(conf).deleteSubuser(uid, subuser,OperateLog,dbcluster),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)


@app.route('/S3/user/<string:uid>/subuser/<string:subuser>/key', methods=['PUT'])
def createSubuserKey(uid, subuser):
    Log.debug("createSubuserKey")
    try:
        return Response(S3Ctrl(conf).createSubuserKey(uid, subuser,OperateLog,dbcluster),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/subuser/<string:subuser>/key', methods=['DELETE'])
def deleteSubuserKey(uid, subuser):
    Log.debug("deleteSubuserKey")
    try:
        return Response(S3Ctrl(conf).deleteSubuserKey(uid, subuser,OperateLog,dbcluster),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/caps', methods=['PUT', 'POST'])
def saveCapability(uid):
    Log.debug("saveCapability")
    try:
        return Response(S3Ctrl(conf).saveCapability(uid,OperateLog,dbcluster),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/caps', methods=['DELETE'])
def deleteCapability(uid):
    Log.debug("deleteCapability")
    try:
        return Response(S3Ctrl(conf).deleteCapability(uid,OperateLog,dbcluster),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/qos', methods=['PUT', 'POST'])
def saveQos(uid):
    Log.debug("saveQos")
    try:
        # passkey = json.loads(request.form['passkey'])
        # ak = passkey.get("access_key",None)
        # sk = passkey.get("secret_key", None)
        return Response(S3Ctrl(conf).setUserQoS(uid,OperateLog,dbcluster), mimetype='application/json')
    except S3Error, e:
        Log.err(e.__str__())
    return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/quota', methods=['PUT', 'POST'])
def saveQuota(uid):
    Log.debug("saveQuota")
    try:
        # passkey = json.loads(request.form['passkey'])
        # ak = passkey.get("access_key",None)
        # sk = passkey.get("secret_key", None)
        return Response(S3Ctrl(conf).setUserQuota(uid,OperateLog,dbcluster), mimetype='application/json')
    except S3Error, e:
        Log.err(e.__str__())
    return Response(e.reason, status=e.code)

# bucket management

@app.route('/S3/user/<string:uid>/buckets', methods=['GET'])
def getUserBuckets(uid,bucket=None):
    try:
        return Response(S3Ctrl(conf).getUserBuckets(uid),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)


@app.route('/S3/bucket', methods=['PUT'])
def createBucket():
    try:
        return Response(S3Ctrl(conf).createBucket(OperateLog,dbcluster), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)


@app.route('/S3/bucket', methods=['GET'])
def getBuckets():
    try:
        return Response(S3Ctrl(conf).getBucketInfo(None), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/bucket/<string:bucket>', methods=['GET'])
def getBucketInfo(bucket=None):
    try:
        return Response(S3Ctrl(conf).getBucketInfo(bucket), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/bucket/<string:bucket>', methods=['DELETE'])
def deleteBucket(bucket):
    try:
        return Response(S3Ctrl(conf).deleteBucket(bucket,OperateLog,dbcluster), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/bucket/<string:bucket>/link', methods=['DELETE','PUT'])
def linkBucket(bucket):
    try:
        uid = request.form['uid']
        if request.method =='PUT':
            return Response(S3Ctrl(conf).linkBucket(uid, bucket,OperateLog,dbcluster), mimetype='application/json')
        else:
            return Response(S3Ctrl(conf).unlinkBucket(uid, bucket,OperateLog,dbcluster), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/bucket/<string:bucketName>/list', methods=['GET'])
def listBucket(bucketName):
    try:
        return Response(S3Ctrl(conf).listBucket(bucketName), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

