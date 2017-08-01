#-*- coding: UTF-8 -*-
# author 01107267
# date 2017-05-24
import time
class OperateLog:
    def writeOperateLog(operator, optype, destip, loginfo, opstatus, db):
        oplog = {}
        # oplog['operator'] = current_user
        oplog['operator'] = operator
        oplog['optype'] = optype
        oplog['destip'] = destip
        oplog['description'] = loginfo
        oplog['operateTime'] = int(round(time.time() * 1000))
        oplog['opstatus'] = opstatus
        db.operationlog.insert(oplog)