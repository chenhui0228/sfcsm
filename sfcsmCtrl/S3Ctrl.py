#-*- coding: UTF-8 -*-
# chenhui 01107267
# 2017/5/25
__author__ = 'alain.dechorgnat@orange.com'

from flask import Flask, request, Response
from S3.bucket import S3Bucket, S3Error
from S3.user import  S3User
from Log import Log
import json

class S3Ctrl:

    def __init__(self,conf,access_key=None, secret_key=None):
        self.admin = conf.get("radosgw_admin", "admin")
        self.key = conf.get("radosgw_key", "")
        # if access_key is None:
        #     self.key = conf.get("radosgw_key", "")
        # else:
        #     self.key = access_key
        # if secret_key is None:
        #     self.secret = conf.get("radosgw_secret", "")
        # else:
        #     self.secret = secret_key
        self.secret = conf.get("radosgw_secret", "")
        self.radosgw_url = conf.get("radosgw_url", "127.0.0.1")
        self.secure = self.radosgw_url.startswith("https://")

        if not self.radosgw_url.endswith('/'):
            self.radosgw_url += '/'
        self.url = self.radosgw_url + self.admin
        #print "config url: "+self.url
        #print "config admin: "+self.admin
        #print "config key: "+self.key
        #print "config secret: "+self.secret

    def getAdminConnection(self):
        return S3Bucket(self.admin, access_key=self.key, secret_key=self.secret , base_url= self.url, secure= self.secure)

    def getBucket(self,bucketName):
        return S3Bucket(bucketName, access_key=self.key, secret_key=self.secret , base_url= self.radosgw_url +bucketName, secure= self.secure)

    def listUsers(self):
        Log.debug( "list users from rgw api")
        return S3User.list(self.getAdminConnection())

    def createUser(self,operateLog, db):
        Log.debug( "user creation")
        jsonform = request.form['json']
        user = S3User.create(jsonform,self.getAdminConnection())
        loginfo = "Create s3 user " + str(json.loads(jsonform)['uid'])
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return user

    def modifyUser(self, uid, operateLog, db):
        Log.debug( "modify user with uid "+ uid)
        jsonform = request.form['json']
        user = S3User.modify(uid, jsonform, self.getAdminConnection())
        loginfo = "modify user with uid "+ uid
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return user

    def getUser(self, uid):
        Log.debug( "get user with uid "+ uid)
        return S3User.view(uid,self.getAdminConnection())

    def removeUser(self, uid, operateLog, db):
        Log.debug( "remove user with uid "+ uid)
        userinfo = S3User.remove(uid,self.getAdminConnection())
        loginfo = "remove user with uid "+ uid
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return userinfo

    def removeUserKey(self, uid, key, operateLog, db):
        Log.debug( "remove key for user with uid "+ uid)
        userinfo = S3User.removeKey(key,self.getAdminConnection())
        loginfo = "remove key for user with uid "+ uid
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return userinfo

    def createSubuser(self, uid, operateLog, db):
        Log.debug( "create subuser for user with uid "+ uid)
        jsonform = request.form['json']
        subusers = S3User.createSubuser(uid,jsonform,self.getAdminConnection())
        loginfo = "create subuser for user with uid "+ uid
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return subusers

    def saveCapability(self, uid, operateLog, db):
        capType = request.form['type']
        capPerm = request.form['perm']
        Log.debug( "saveCapability "+capType+"="+capPerm+" for user with uid "+ uid)
        caps = S3User.saveCapability(uid, capType, capPerm, self.getAdminConnection())
        loginfo = "saveCapability "+capType+"="+capPerm+" for user with uid "+ uid
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return caps

    def deleteCapability(self, uid, operateLog, db):
        capType = request.form['type']
        capPerm = request.form['perm']
        Log.debug( "deleteCapability "+capType+"="+capPerm+" for user with uid "+ uid)
        caps = S3User.deleteCapability(uid, capType, capPerm, self.getAdminConnection())
        loginfo = "deleteCapability "+capType+"="+capPerm+" for user with uid "+ uid
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return caps

    def deleteSubuser(self, uid, subuser, operateLog, db):
        Log.debug( "delete subuser "+subuser+" for user with uid "+ uid)
        subuser = S3User.deleteSubuser(uid, subuser, self.getAdminConnection())
        loginfo = "delete subuser "+subuser+" for user with uid "+ uid
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return subuser

    def createSubuserKey(self, uid, subuser, operateLog, db):
        Log.debug( "create key for subuser "+subuser+" for user with uid "+ uid)
        generate_key = request.form['generate_key']
        secret_key = request.form['secret_key']
        key = S3User.createSubuserKey(uid, subuser, generate_key, secret_key, self.getAdminConnection())
        loginfo = "create key for subuser "+subuser+" for user with uid "+ uid
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return key

    def deleteSubuserKey(self, uid, subuser, operateLog, db):
        Log.debug( "delete key for subuser "+subuser+" for user with uid "+ uid)
        subuserkey = S3User.deleteSubuserKey(uid, subuser, self.getAdminConnection())
        loginfo = "delete key for subuser "+subuser+" for user with uid "+ uid
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return subuserkey

    def getUserBuckets(self, uid):
        Log.debug( "getBuckets for uid " + uid)
        jsonform = None
        return S3User.getBuckets(uid,jsonform,self.getAdminConnection())


# bucket management

    def createBucket(self, operateLog, db):
        bucket = request.form['bucket']
        owner = request.form['owner']
        Log.debug( "createBucket "+bucket+" for user "+owner)
        print "\n--- info user for owner ---"
        userInfo = self.getUser(owner)
        print userInfo
        userInfo = json.loads(userInfo)
        keys = userInfo.get('keys')
        print "keys = ",keys
        access_key = keys[0].get('access_key')
        secret_key = keys[0].get('secret_key')
        # print access_key
        # print secret_key

        print "\n--- create bucket for owner ---"
        mybucket = S3Bucket(bucket, access_key=access_key, secret_key=secret_key , base_url= self.radosgw_url+bucket)
        res = mybucket.put_bucket()
        loginfo = "create bucket "+bucket+" for user "+owner
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return 'OK'


    def getBucketInfo (self, bucket):
        myargs = []
        stats = request.form.get('stats', None)
        if stats is not None:
            myargs.append(("stats",stats))
        if bucket is not None:
            myargs.append(("bucket",bucket))

        conn = self.getAdminConnection()
        request2= conn.request(method="GET", key="bucket", args= myargs)
        res = conn.send(request2)
        info = res.read()
        print info
        return info

    def linkBucket (self,uid, bucket, operateLog, db):
        conn = self.getAdminConnection()
        myargs = [("bucket",bucket),("uid",uid)]
        request= conn.request(method="PUT", key="bucket", args= myargs)
        res = conn.send(request)
        info = res.read()
        loginfo = "link bucket " + bucket + " for user " + str(uid)
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        print info
        return info

    def listBucket (self, bucketName):
        myargs = []
        if bucketName is not None:
            myargs.append(("bucket",bucketName))
        conn = self.getAdminConnection()
        request2= conn.request(method="GET", key="bucket", args= myargs)
        res = conn.send(request2)
        bucketInfo = json.loads(res.read())
        print bucketInfo
        owner = bucketInfo.get('owner')
        userInfo = self.getUser(owner)
        print userInfo
        userInfo = json.loads(userInfo)
        keys = userInfo.get('keys')
        print keys
        access_key = keys[0].get('access_key')
        secret_key = keys[0].get('secret_key')
        bucket = S3Bucket(bucketName, access_key=access_key, secret_key=secret_key , base_url= self.radosgw_url+bucketName, secure= self.secure)
        list = []
        for (key, modify, etag, size) in bucket.listdir():
            obj = {}
            obj['name'] = key
            obj['size'] = size
            list.append(obj)
            print "%r (%r) is size %r, modified %r" % (key, etag, size, modify)
        return json.dumps(list)

    def unlinkBucket (self,uid, bucket, operateLog, db):
        conn = self.getAdminConnection()
        myargs = [("bucket",bucket),("uid",uid)]
        request= conn.request(method="POST", key="bucket", args= myargs)
        res = conn.send(request)
        info = res.read()
        loginfo = "unlink bucket " + bucket + " for user " + str(uid)
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        print info
        return info

    def deleteBucket (self,bucket, operateLog, db):
        conn = self.getAdminConnection()
        myargs = [("bucket",bucket),("purge-objects","True")]
        request= conn.request(method="DELETE", key="bucket", args= myargs)
        res = conn.send(request)
        info = res.read()
        loginfo = "delete bucket " + bucket
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        print info
        return info

    def setUserQuota(self, uid, operateLog, db):
        conn = self.getAdminConnection()
        jsonform = request.form['json']
        info = S3User.setUserQuota(uid, conn, json.loads(jsonform))
        loginfo = "set quota for " + str(uid)
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return info

    def setUserQoS(self, uid, operateLog, db):
        conn = self.getAdminConnection()
        jsonform = request.form['json']
        info = S3User.setUserQos(uid, conn, json.loads(jsonform))
        loginfo = "set qos for " + str(uid)
        operateLog.writeOperateLog("test", "N", "all", loginfo, 1, db)
        return info