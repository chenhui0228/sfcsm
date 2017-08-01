#-*- coding: UTF-8 -*-
# author 01107267
# date 2017-05-24
class Operate:
    def __init__(self):
        self.op_service_ceph_stop = 'service ceph stop'
        self.op_service_ceph_start = 'service ceph start'
        self.op_service_ceph_osd_stop = 'service ceph stop osd'
        self.op_service_ceph_osd_start = 'service ceph start osd'
        self.op_service_ceph_mon_stop = 'service ceph stop mon'
        self.op_service_ceph_mon_start = 'service ceph start mon'
        self.op_codes = {}
        self.op_codes['OP001'] = 'service ceph stop'
        self.op_codes['OP002'] = 'service ceph start'
        self.op_codes['OP003'] = 'service ceph stop osd'
        self.op_codes['OP004'] = 'service ceph start osd'
        self.op_codes['OP005'] = 'service ceph stop mon'
        self.op_codes['OP006'] = 'service ceph start mon'
        self.op_codes['OP007'] = '/bin/radosgw -n '
        self.op_codes['OP008'] = 'kill -9 '
        pass

    def insertDb(self):
        pass