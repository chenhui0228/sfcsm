#-*- coding: UTF-8 -*-
#!/usr/bin/env python

# author 01107267
# licence: apache v2
# Alexis KOALLA: pymongo update for replicaset

# need package python-dev: sudo apt-get install python-dev
# need module psutil: download module tar.gz, unzip, python setup.py install
# need pip to install pymongo: http://www.pip-installer.org/en/latest/installing.html
# need pymongo module: download module, 


from pymongo import MongoClient
from pymongo import MongoReplicaSetClient
from pymongo.read_preferences import ReadPreference

import time
import datetime
from Queue import Queue
import re

# psutil to perform system command
import psutil
import pkg_resources
psutil_version = pkg_resources.get_distribution("psutil").version.split(".")[0]

# for ceph command call
import subprocess

import os
import sys
import traceback
import getopt
import socket
from daemon import Daemon

import httplib
import json
from StringIO import StringIO

from bson.dbref import DBRef 

from threading import Thread, Event, Condition

import signal
import sys
sys.path.append(os.path.split(sys.path[0])[0])
from sfcsmUtil.operate import Operate
# from bson.objectid import ObjectId
# db.col.find({"_id": ObjectId(obj_id_to_find)})

#configfile = "/opt/sfcsm/etc/sfcsm.conf"
configfile = "/home/workspace/sfcsm/sfcsm-template.conf"
runfile = "/var/run/sysprobe/sysprobe.pid"
logfile = "/var/log/sfcsm/sysprobe.log"


# load the conf (from json into file)
def load_conf():
    datasource = open(configfile, "r")
    data = json.load(datasource)
    
    datasource.close()
    return data


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


# mem
def pick_mem(hostname, db):
    print str(datetime.datetime.now()), "-- Pick Mem"  
    sys.stdout.flush()
    res = psutil.virtual_memory()
    # convert to base
    mem4db = {
        "timestamp": int(round(time.time() * 1000)),
        "total": res.total,
        "used": res.used,
        "free": res.free,
        "buffers": res.buffers,
        "cached": res.cached,
        "host": DBRef("hosts", hostname)
        }
    mem_id = db.memstat.insert(mem4db)
    db.hosts.update({"_id": hostname}, {"$set": {"mem": DBRef("memstat", mem_id)}})


# swap
def pick_swap(hostname, db):
    print str(datetime.datetime.now()), "-- Pick Swap"  
    sys.stdout.flush()
    res = psutil.swap_memory()
    # convert to base
    swap4db = {"timestamp": int(round(time.time() * 1000)),
               "total": res.total,
               "used": res.used,
               "free": res.free,
               "host": DBRef("hosts", hostname)
               }
    swap_id = db.swapstat.insert(swap4db)
    db.hosts.update({"_id": hostname}, {"$set": {"swap": DBRef("swapstat", swap_id)}})


# /var/lib/ceph/osd/$cluster-$id  
# partitions
def get_partitions(hostname):
    _partitions = psutil.disk_partitions()
    parts = []
    for p in _partitions:
        res = {"_id": hostname+":"+p.device,
               "dev": p.device,
               "mountpoint": p.mountpoint,
               "fs": p.fstype,
               "stat": None
            }
        parts.append(res)
    return parts
       


def pick_partitions_stat(hostname, db):
    print str(datetime.datetime.now()), "-- Pick Partition Stats"  
    sys.stdout.flush()
    _partitions = psutil.disk_partitions()
    for p in _partitions:
        # disk usage
        part_stat = psutil.disk_usage(p.mountpoint)
        
        res = {
               "timestamp": int(round(time.time() * 1000)),
               "total": part_stat.total,
               "used": part_stat.used,
               "free": part_stat.free,
               "partition": DBRef("partitions", hostname+":"+p.device)
               }
        partstat_id = db.partitionstat.insert(res)
        db.partitions.update({"_id": hostname+":"+p.device}, {"$set": {"stat": DBRef("partitionstat", partstat_id)}})


# osd_dirs = [f for f in os.listdir(ceph_osd_root_path) if re.match(clusterName+ r'-.*', f)
# and os.path.isdir(ceph_osd_root_path+'/'+f)]


# filter the hardware list according to the class
def filter_hw(hw, cl):
    res = []
    if "children" in hw:
        for child in hw["children"]:
            if child["class"] == cl:
                res.append(child)
                continue
            else:
                res.extend(filter_hw(child, cl))
    return res


def get_hw():  
    output = subprocess.Popen(['lshw', '-json'], stdout=subprocess.PIPE).communicate()[0]
    hw_io = StringIO(output)
    hw = json.load(hw_io)    
    return hw

def get_raid_adp():
    p = subprocess.Popen(
        '/opt/MegaRAID/MegaCli/MegaCli64 -AdpCount',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option, %s', errdata)
    countinfo = outdata.rstrip()
    adpcount = re.search("Controller Count: [0-9]+", countinfo)
    if adpcount:
        return int(adpcount.group().split(': ')[1])
    else:
        return -1

def get_bbu_properties(adapter = '0'):
    p = subprocess.Popen(
        '/opt/MegaRAID/MegaCli/MegaCli64 -AdpBbuCmd -GetBbuProperties -a' + adapter,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option')
    bbuinfo = outdata.rstrip()
    learn_period = re.search("Auto Learn Period[: 0-9a-zA-Z-/,]+", bbuinfo)
    next_learn_time = re.search("Next Learn time:[: 0-9a-zA-Z-/,]+", bbuinfo)
    auto_learn_mode = re.search("Auto-Learn Mode:[: 0-9a-zA-Z-/,]+", bbuinfo)
    properties = {}
    if learn_period:
        properties["bbu_auto_learn_period"] = learn_period.group().split(": ")[1].strip()
    if next_learn_time:
        properties["bbu_next_learn_time"] = next_learn_time.group().split(": ")[1].strip()
    if auto_learn_mode:
        properties["bbu_auto_learn_mode"] = auto_learn_mode.group().split(": ")[1].strip()
    return properties

def get_bbu_designinfo(adapter = '0'):
    p = subprocess.Popen(
        '/opt/MegaRAID/MegaCli/MegaCli64 -AdpBbuCmd -GetBbuDesignInfo -a' + adapter,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option')
    bbuinfo = outdata.rstrip()
    date_of_manufacture = re.search("Date of Manufacture[: a-zA-Z0-9/,]+", bbuinfo)
    manufacture_name = re.search("Manufacture Name[: a-zA-Z0-9/,]+", bbuinfo)
    designinfo = {}
    if date_of_manufacture:
        designinfo["bbu_date_of_manufacture"] = date_of_manufacture.group().split(": ")[1].strip()
    if manufacture_name:
        designinfo["bbu_manufacture_name"] = manufacture_name.group().split(": ")[1].strip()
    return designinfo

def get_bbu_status(adapter = '0'):
    p = subprocess.Popen(
        '/opt/MegaRAID/MegaCli/MegaCli64 -AdpBbuCmd -GetBbustatus -a' + adapter,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option')
    bbuinfo = outdata.rstrip()
    voltage = re.search("Voltage[: a-zA-Z0-9.]+", bbuinfo)
    current = re.search("Current[: a-zA-Z0-9.]+", bbuinfo)
    temperature = re.search("Temperature[: a-zA-Z0-9.]+", bbuinfo)
    battery_state = re.search("Battery State[: a-zA-Z0-9.]+", bbuinfo)
    charger_status = re.search("Charger Status[: a-zA-Z0-9.]+", bbuinfo)
    remaining_capacity = re.search("Remaining Capacity:[ a-zA-Z0-9.]+", bbuinfo)
    full_charge_capacity = re.search("Full Charge Capacity[: a-zA-Z0-9.]+", bbuinfo)
    statusinfo = {}
    if voltage:
        statusinfo["bbu_voltage"] = voltage.group().split(": ")[1].strip()
    if current:
        statusinfo["bbu_current"] = current.group().split(": ")[1].strip()
    if temperature:
        statusinfo["bbu_temperature"] = temperature.group().split(": ")[1].strip()
    if battery_state:
        statusinfo["bbu_battery_state"] = battery_state.group().split(": ")[1].strip()
    if charger_status:
        statusinfo["bbu_charger_status"] = charger_status.group().split(": ")[1].strip()
    if remaining_capacity:
        statusinfo["bbu_remaining_capacity"] = remaining_capacity.group().split(": ")[1].strip()
    if full_charge_capacity:
        statusinfo["bbu_full_charge_capacity"] = full_charge_capacity.group().split(": ")[1].strip()
    return statusinfo

def get_raid_info(adapter = '0'):
    p = subprocess.Popen(
        '/opt/MegaRAID/MegaCli/MegaCli64 -AdpAllInfo -a' + adapter,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option')
    raidinfo = outdata.rstrip()
    product = re.search("Product Name[ :a-zA-Z0-9-_]+", raidinfo)
    serial_no = re.search("Serial No[ :a-zA-Z0-9-_]+", raidinfo)
    bbu = re.findall("(BBU[ :a-zA-Z0-9-_]+)", raidinfo)
    memory_size = re.search("Memory Size[ :a-zA-Z0-9-_]+", raidinfo)
    mfg_date = re.search("Mfg. Date[ :a-zA-Z0-9-/,]+", raidinfo)
    raid = {}
    raid["adapter"] = adapter
    if product:
        raid["product"] = product.group(0).split(": ")[1].strip()
    if serial_no:
        raid["serial_no"] = serial_no.group(0).split(": ")[1].strip()
    if mfg_date:
        raid["manufacture_date"] = mfg_date.group(0).split(": ")[1].strip()
    if memory_size:
        raid["memory_size"] = memory_size.group(0).split(": ")[1].strip()
    if bbu:
        raid["bbu_hw_config"] = bbu[0].split(": ")[1].strip()
        raid["bbu_operation_support"] = bbu[1].split(": ")[1].strip()
    designinfo = get_bbu_designinfo(adapter)
    raid.update(designinfo)
    return raid

def get_hpraid_info(slot=0):
    p = subprocess.Popen(
        # 'ctrl all show config detail | grep -i -A'+str(lines)+' \"array: '+logical_name+'\"',
        'cat /root/ssacli.txt | egrep -A46 -i \"smart array (.*)\"',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option %s', errdata)
    hpraidinfo = outdata.strip()
    product = re.search("Smart Array(.*)", hpraidinfo)
    slot = re.search("Slot:(.*)", hpraidinfo)
    serial_number = re.search("Serial Number:(.*)", hpraidinfo)
    cache_serial_number = re.search("Cache Serial Number:(.*)", hpraidinfo)
    controller_status = re.search("Controller Status:(.*)", hpraidinfo)
    cache_status = re.search("Cache Status:(.*)", hpraidinfo)
    cache_size = re.search("Total Cache Size:(.*)", hpraidinfo)
    cache_size_available = re.search("Total Cache Memory(.*)", hpraidinfo)
    drive_write_cache = re.search("Drive Write Cache(.*)", hpraidinfo)
    no_battery_w_cache = re.search("No-Battery Write Cache(.*)", hpraidinfo)
    bc_count = re.search("Battery/Capacitor Count(.*)", hpraidinfo)
    bc_status = re.search("Battery/Capacitor Status(.*)", hpraidinfo)
    contorller_temperature = re.search("Controller Temperature(.*)", hpraidinfo)
    cache_temperature = re.search("Cache Module Temperature(.*)", hpraidinfo)
    capacitor_temperature = re.search("Capacitor Temperature(.*)", hpraidinfo)
    raid = {}
    raid["vender"] = "HP"
    if slot:
        raid["slot"] = slot.group().split(": ")[1].strip()
        raid["adapter"] = raid["slot"]
    if serial_number:
        raid["serial_no"] = serial_number.group().split(": ")[1].strip()
    if product:
        raid["product"] = product.group().split(" ")[2].strip()
    if cache_serial_number:
        raid["cache_serial_no"] = cache_serial_number.group().split(": ")[1].strip()
    if controller_status:
        raid["controller_status"] = controller_status.group().split(": ")[1].strip()
    if cache_status:
        raid["cache_status"] = cache_status.group().split(": ")[1].strip()
    if cache_size:
        raid["cache_size"] = cache_size.group().split(": ")[1].strip()
    if cache_size_available:
        raid["cache_size_available"] = cache_size_available.group().split(": ")[1].strip()
    if cache_serial_number:
        raid["drive_write_cache"] = drive_write_cache.group().split(": ")[1].strip()
    if controller_status:
        raid["no_battery_w_cache"] = no_battery_w_cache.group().split(": ")[1].strip()
    if bc_count:
        raid["battery_capacitor_count"] = bc_count.group().split(": ")[1].strip()
    if bc_status:
        raid["battery_capacitor_status"] = bc_status.group().split(": ")[1].strip()
    if contorller_temperature:
        raid["contorller_temperature"] = contorller_temperature.group().split(": ")[1].strip()
    if cache_temperature:
        raid["cache_temperature"] = cache_temperature.group().split(": ")[1].strip()
    if capacitor_temperature:
        raid["capacitor_temperature"] = capacitor_temperature.group().split(": ")[1].strip()
    return raid

def get_hw_raids(hostname):
    adapter_num = get_raid_adp()
    raids = []
    if (adapter_num > 0):
        for i in range(0, adapter_num):
            curr_raid = get_raid_info(str(i))
            curr_raid["_id"] = hostname + ":" + str(i)
            curr_raid["bbustat"] = None
            raids.append(curr_raid)
    raid_vendor = checkRaidVendor()
    if raid_vendor.upper() == "HP":
        curr_raid = get_hpraid_info()
        curr_raid["_id"] = hostname + ":" + curr_raid['slot']
        curr_raid["bbustat"] = None
        raids.append(curr_raid)
    return raids



#01107267
def get_disk_plmap(hostname, db, logical_name, target_id, adapter ='0'):
    pdisks = []
    p1 = subprocess.Popen(
        '/opt/MegaRAID/MegaCli/MegaCli64 -CfgDsply -a' + adapter + ' | egrep -n \"DISK GROUP: ' + target_id + '\" | awk \'{print $1}\' | grep -o \'[0-9]*\'',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p1.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option %s: %s' % (target_id, errdata))
    start_line = outdata.rstrip()

    p2 = subprocess.Popen(
        '/opt/MegaRAID/MegaCli/MegaCli64 -CfgDsply -a' + adapter + ' | egrep -n \"(DISK GROUP|Exit Code): \" | awk \'{print $1}\' | grep -o \'[0-9]*\' | grep -A1 '+start_line+' | grep -v '+start_line,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p2.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option %s: %s' % (target_id, errdata))
    end_line = outdata.rstrip()
    lines = int(end_line) - int(start_line) - 1

    p = subprocess.Popen(
        '/opt/MegaRAID/MegaCli/MegaCli64 -CfgDsply -a' + adapter + ' | egrep -A'+str(lines)+' \"DISK GROUP: ' + target_id + '\"',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option %s: %s' % (target_id, errdata))
    diskinfo = outdata.rstrip()
    num_pds = re.search("Number of PDs[: 0-9]+", diskinfo).group().split(': ')[1]

    enclosure_device_id = re.findall("Enclosure Device ID[: 0-9]+", diskinfo)
    slot_number = re.findall("Slot Number[: 0-9]+", diskinfo)
    device_id = re.findall("Device Id[: 0-9]+", diskinfo)
    raid_level = re.search("RAID Level(.*)", diskinfo).group().split(': ')[1]
    current_cache_policy = re.search("Current Cache Policy[: a-zA-Z./,]+", diskinfo).group().split(': ')[1]
    current_access_policy = re.search("Current Access Policy[: a-zA-Z/]+", diskinfo).group().split(': ')[1]
    disk_cache_policy = re.search("Disk Cache Policy[: a-zA-Z]+", diskinfo).group().split(': ')[1]
    media_type = re.findall("Media Type[: a-zA-Z]+", diskinfo)
    disk_raid_info = {}
    if raid_level:
        disk_raid_info['raid_level'] = raid_level
    if current_cache_policy:
        disk_raid_info['current_cache_policy'] = current_cache_policy
    if current_access_policy:
        disk_raid_info['current_access_policy'] = current_access_policy
    if disk_cache_policy:
        disk_raid_info['disk_cache_policy'] = disk_cache_policy
    i = 0
    while i < int(num_pds):
        disk_plmap = {}
        disk_smart = {}
        disk_plmap['adapter'] = adapter
        if enclosure_device_id:
            disk_plmap['enclosure_device_id'] = enclosure_device_id[i].split(': ')[1]
        if slot_number:
            disk_plmap['slot_number'] = slot_number[i].split(': ')[1]
        if device_id:
            disk_plmap['device_id'] = device_id[i].split(': ')[1]
            disk_smart = get_disk_smart(logical_name, disk_plmap['device_id'])
        if media_type:
            disk_plmap['media_type'] = media_type[i].split(': ')[1]
        doc_id = 'NA'
        if int(num_pds) == 1:
            doc_id = hostname+":"+logical_name
        else:
            doc_id = hostname+":"+logical_name+":"+str(i)
        i = i + 1
        pd = {
            "_id": doc_id,
            "vender": disk_smart['vender'],
            "product": disk_smart['product'],
            "serial_number": disk_smart['serial_number'],
            "size": long(disk_smart['user_capacity']),
            "enclosure_device_id": disk_plmap['enclosure_device_id'],
            "slot_number": disk_plmap['slot_number'],
            "device_id": disk_plmap['device_id'],
            "media_type": disk_plmap['media_type'],
            "logical_name": logical_name,
            "smart": None
        }
        db.pdisks.update({'_id': pd['_id']}, pd, upsert=True)
        pdisks.append(pd)
    return pdisks, disk_raid_info

#01107267
def get_disk_smart(logical_name,device_id):
    shellStr = ''
    if device_id == 'unknown':
        shellStr = 'smartctl -a ' + logical_name
    else:
        shellStr = 'smartctl -a -d  megaraid,' + device_id + ' ' + logical_name
    p = subprocess.Popen(shellStr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option %s, %s: %s' % (logical_name, device_id, errdata))
    smartinfo = outdata.rstrip()
    disk_smart = {}
    vendor = re.search("Vendor:[ a-zA-Z0-9-]+", smartinfo)
    product = re.search("Product:[ a-zA-Z0-9-_]+", smartinfo)
    revision = re.search("(Revision|Version):[ a-zA-Z0-9-_.]+", smartinfo)
    user_capacity = re.search("User Capacity:(.*)", smartinfo)
    device_model = re.search("Device Model:[ a-zA-Z0-9-_]+", smartinfo)
    serial_number = re.search("Serial (number|Number):[ a-zA-Z0-9-_]+", smartinfo)
    smart_support = re.search("SMART support is:[ ]+Available", smartinfo)
    smart_enabled = re.search("SMART support is:[ ]+Enabled", smartinfo)
    smart_health_status = re.search("SMART (Health Status|overall-health)[ :a-zA-Z-]+", smartinfo)
    power_on_hours = re.search("Power_On_Hours[ a-zA-Z0-9-_]+", smartinfo)
    if power_on_hours is None:
        power_on_hours = re.search("(number of hours powered up|hours powered up)[ 0-9.=]+", smartinfo)
        if power_on_hours:
            power_on_hours = power_on_hours.group().split('= ')[1]
    else:
        power_on_hours = re.search("[0-9.]+$", power_on_hours.group(0).strip())
        if power_on_hours:
            power_on_hours = power_on_hours.group()
    read_error_rate = re.search("Raw_Read_Error_Rate[ a-zA-Z0-9-_]+", smartinfo)
    read_errors = re.search("read:[ 0-9.]+", smartinfo)
    write_error_rate = re.search("Write_Error_Rate[ a-zA-Z0-9-_]+", smartinfo)
    write_errors = re.search("write:[ 0-9.]+", smartinfo)
    verify_errors = re.search("verify:[ 0-9.]+", smartinfo)
    non_medium_error_count = re.search("Non-medium error count:[ 0-9.]+", smartinfo)
    media_wearout_indicator = re.search("Media_Wearout_Indicator[ a-zA-Z0-9-_]+", smartinfo)
    if vendor:
        disk_smart['vender'] = vendor.group().split(': ')[1].strip()
    if product:
        disk_smart['product'] = product.group().split(': ')[1].strip()
    if device_model:
        disk_smart['product'] = device_model.group().split(': ')[1].strip().split(' ')[1]
        disk_smart['vender'] = device_model.group().split(': ')[1].strip().split(' ')[0]
        disk_smart['device_model'] = device_model.group().split(': ')[1].strip()
    if revision:
        disk_smart['revision'] = revision.group().split(': ')[1].strip()
    if serial_number:
        disk_smart['serial_number'] = serial_number.group().split(': ')[1].strip()
    if smart_support:
        disk_smart['smart_support'] = smart_support.group().split(': ')[1].strip()
    if smart_enabled:
        disk_smart['smart_enabled'] = smart_enabled.group().split(': ')[1].strip()
    if smart_health_status:
        disk_smart['smart_health_status'] = smart_health_status.group().split(': ')[1]
    if user_capacity:
        str = user_capacity.group().split(': ')[1].strip().split(' ')[0]
        disk_smart['user_capacity'] = str.replace(',','')
    if power_on_hours:
        disk_smart['power_on_hours'] = power_on_hours
    if read_error_rate:
        read_error_rate = re.sub("[ ]+", " ", read_error_rate.group(0).strip())
        disk_smart['read_error_rate'] = read_error_rate.split(' ')[2]
    if read_errors:
        read_errors = re.sub("[ ]+", " ", read_errors.group().split(': ')[1].strip())
        disk_smart['read_errors_correct_ecc_fast'] = read_errors.split(' ')[0]
        disk_smart['read_errors_correct_ecc_delayed'] = read_errors.split(' ')[1]
        disk_smart['read_by_reread'] = read_errors.split(' ')[2]
        disk_smart['read_total_errors_corrected'] = read_errors.split(' ')[3]
        disk_smart['read_correction_algorithm_invocations'] = read_errors.split(' ')[4]
        disk_smart['read_gigabytes_processed'] = read_errors.split(' ')[5]
        disk_smart['read_total_uncorrected_errors'] = read_errors.split(' ')[6]
    if write_error_rate:
        write_error_rate = re.sub("[ ]+", " ", write_error_rate.group(0).strip())
        disk_smart['write_error_rate'] = write_error_rate.split(' ')[2]
    if write_errors:
        write_errors = re.sub("[ ]+", " ", write_errors.group().split(': ')[1].strip())
        disk_smart['write_errors_correct_ecc_fast'] = write_errors.split(' ')[0]
        disk_smart['write_errors_correct_ecc_delayed'] = write_errors.split(' ')[1]
        disk_smart['write_by reread'] = write_errors.split(' ')[2]
        disk_smart['write_total_errors_corrected'] = write_errors.split(' ')[3]
        disk_smart['write_correction_algorithm_invocations'] = write_errors.split(' ')[4]
        disk_smart['write_gigabytes_processed'] = write_errors.split(' ')[5]
        disk_smart['write_total_uncorrected_errors'] = write_errors.split(' ')[6]
    if non_medium_error_count:
        disk_smart['non-medium_error_count'] = non_medium_error_count.group().split(': ')[1].strip()
    if media_wearout_indicator:
        media_wearout_indicator = re.sub("[ ]+", " ", media_wearout_indicator.group(0).strip())
        disk_smart['media_wearout_indicator'] = media_wearout_indicator.split(' ')[2]
    return disk_smart

def checkRaidVendor():
    p = subprocess.Popen(
        'cat /proc/scsi/scsi | grep -i -m 1 vendor | awk \'{print $2}\'',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option')
    vendor = outdata.strip()
    return vendor

def get_hp_disk(hostname, db, logical_name):
    pdisks = []
    logical_name = str(logical_name).replace("/dev/sd","")
    p1 = subprocess.Popen(
        # 'ctrl all show config detail | grep -n -i \"array: '+logical_name+'\" | grep -o \'[0-9]*\'',
        'cat /root/ssacli.txt | egrep -n -i \"array: ' + logical_name + '\" | egrep -o \'[0-9]*\'',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p1.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option, %s',errdata)
    start_line = outdata.strip()
    p2 = subprocess.Popen(
        # 'ctrl all show config detail | grep -n -i \"array: \" | grep -o \'[0-9]*\' | grep -A1 '+start_line+' | grep -v '+start_line,
        'cat /root/ssacli.txt | egrep -n -i \"array: \" | egrep -o \'[0-9]*\' | egrep -A1 ' + start_line + ' | egrep -v ' + start_line,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p2.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option %s',errdata)
    end_line = outdata.strip()
    if len(end_line) == 0:
        end_line = str(int(start_line) + 53)
    lines = int(end_line) - int(start_line) - 1
    p = subprocess.Popen(
        # 'ctrl all show config detail | grep -i -A'+str(lines)+' \"array: '+logical_name+'\"',
        'cat /root/ssacli.txt | egrep -i -A' + str(lines) + ' \"array: ' + logical_name + '\"',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option %s', errdata)
    hpdiskinfo = outdata.strip()
    hp_disk = {}
    num_pds = len(re.findall("Mirror Group(.*)", hpdiskinfo))
    if num_pds == 0:
        num_pds = 1
    raid_level = re.search("Fault Tolerance:(.*)", hpdiskinfo)
    ssd_smart_path = re.search("SSD Smart Path:(.*)", hpdiskinfo)
    status = re.findall("Status:(.*)", hpdiskinfo)
    size = re.findall("Size:(.*)", hpdiskinfo)
    pbb = re.findall("physicaldrive(.*)", hpdiskinfo)
    model = re.findall("Model:(.*)", hpdiskinfo)
    serial_number = re.findall("Serial Number:(.*)", hpdiskinfo)
    caching = re.search("Caching:(.*)", hpdiskinfo)
    hpdisk_raid_info = {}
    if raid_level:
        hpdisk_raid_info["raid_level"] = "RAID"+raid_level.group().split(": ")[1].strip()
    if len(status) > 0:
        hpdisk_raid_info["ldisk_status"] = status[0]
    if caching:
        hpdisk_raid_info["disk_cache_policy"] = caching.group().split(": ")[1].strip()
    i = 0
    while i < num_pds:
        if num_pds == 1:
            num_pds = 0
        hpdisk_plmap = {}
        if model:
            model[i] = re.sub("[ ]+", " ", model[i])
            hpdisk_plmap['vendor'] = model[i].strip().split(" ")[0].strip()
            hpdisk_plmap['product'] = model[i].strip().split(" ")[1].strip()
        if size:
            unit = size[2*i+3].strip().split(" ")[1]
            if unit == "GB":
                hpdisk_plmap['size'] = int(size[2 * i + 3].strip().split(" ")[0]) * 1024 * 1024 * 1024
            if unit == "TB":
                hpdisk_plmap['size'] = int(size[2 * i + 3].strip().split(" ")[0]) * 1024 * 1024 * 1024 * 1024
        if ssd_smart_path:
            if ssd_smart_path.group().split(": ")[1].strip() == "enable":
                hpdisk_plmap['media_type'] = "Solid State Device"
            else:
                hpdisk_plmap['media_type'] = "Hard Disk Device"
        if pbb:
            hpdisk_plmap["port"] = pbb[num_pds+i].split(":")[0].strip()
            hpdisk_plmap["box"] = pbb[num_pds+i].split(":")[1].strip()
            hpdisk_plmap["bay"] = pbb[num_pds+i].split(":")[2].strip()
        if serial_number:
            hpdisk_plmap["serial_number"] = serial_number[i].strip()
        doc_id = 'NA'
        if num_pds == 0:
            doc_id = hostname + ":" + "/dev/sd" + logical_name
        elif num_pds > 1:
            doc_id = hostname + ":" + "/dev/sd" + logical_name + ":" + str(i)
        i = i + 1
        pd = {
            "_id": doc_id,
            "vender": hpdisk_plmap['vendor'],
            "product": hpdisk_plmap['product'],
            "serial_number": hpdisk_plmap['serial_number'],
            "size": hpdisk_plmap['size'],
            "port": hpdisk_plmap['port'],
            "box": hpdisk_plmap['box'],
            "bay": hpdisk_plmap['bay'],
            "media_type": hpdisk_plmap['media_type'],
            "logical_name": "/dev/sd"+logical_name,
            "smart": None,
            "device_id": 'unknown'
        }
        db.pdisks.update({'_id': pd['_id']}, pd, upsert=True)
        pdisks.append(pd)
    return pdisks, hpdisk_raid_info

def get_hw_disk(hostname, hw, db):
    local_disks = []
    physical_disks = []
    # the disks
    disks = filter_hw(hw, "disk")
    raid_vendor = checkRaidVendor()
    #print disks
    for disk in disks:
        if disk['id'].startswith('disk'): 
            logname = "NA"
            if "logicalname" in disk:
                if isinstance(disk['logicalname'], list):
                    logname = disk['logicalname'][0]
                else:
                    logname = disk['logicalname']
            else:
                continue
            description = "NA"
            if "description" in disk: 
                description = disk["description"]          
            physid = "NA"
            if "physid" in disk:
                physid = disk["physid"]
            targetid = "NA"
            adapter = 'NA'
            if "businfo" in disk:
                adapter = disk["businfo"].split(':')[0].split('@')[1]
                targetid = disk["businfo"].split(':')[1].split('.')[1]
            adapter_num = get_raid_adp()
            if "version" in disk:
                diskversion = disk["version"]         
            serial = "NA"
            if "serial" in disk:
                serial = disk["serial"]        
            disksize = 0
            if "size" in disk:    
                if disk["units"] == "bytes":
                    disksize = disk["size"]
            # other units ?
            #get disk lp map
            disk_raid_info = {}
            if (int(adapter) < adapter_num):
                curr_pdisks, disk_raid_info = get_disk_plmap(hostname, db, logname, targetid, adapter)
                physical_disks.extend(curr_pdisks)
            if raid_vendor.upper() == "HP":
                curr_pdisks, disk_raid_info = get_hp_disk(hostname, db, logname)
                physical_disks.extend(curr_pdisks)
            d = {"_id": hostname+":"+logname,
                 "description": description,
                 "physical_id": physid,
                 "adapter": adapter,
                 "target_id": targetid,
                 "logical_name": logname,
                 "version": diskversion,
                 "size": disksize,
                 "raid_level": disk_raid_info['raid_level'] if disk_raid_info.has_key('raid_level') else 'NA',
                 "current_cache_policy": disk_raid_info['current_cache_policy'] if disk_raid_info.has_key('current_cache_policy') else 'NA',
                 "current_access_policy": disk_raid_info['current_access_policy'] if disk_raid_info.has_key('current_access_policy') else 'NA',
                 "disk_cache_policy": disk_raid_info['disk_cache_policy'] if disk_raid_info.has_key('disk_cache_policy') else 'NA',
                 "physical_disks": [DBRef("pdisks",  n["_id"]) for n in curr_pdisks],
                 "stat": None,
                 }
            local_disks.append(d)
    return local_disks, physical_disks

def get_radosgw_typeid():
    p = subprocess.Popen(
        "ps aux | grep radosgw | grep -v grep |awk '{print $2,$NF}'",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        syslog = {}
        syslog['description'] = ''
        raise RuntimeError('unable to get conf option')
    if outdata.strip():
        rgwtypeid = outdata.strip().split(" ")[1]
        rgwpid = outdata.strip().split(" ")[0]
        return rgwtypeid, rgwpid
    return None, None

def get_radosgw_perf(rgwtypeid):
    cmd = 'ceph daemon '+rgwtypeid+' perf dump -f json '+rgwtypeid
    p = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option ',errdata)
    rgwperf = json.loads(outdata.strip())
    # rgwtypeid_ = str(rgwtypeid).replace('.','_')
    # rgwperf[rgwtypeid_] = rgwperf[rgwtypeid]
    rgwperf['rgw_perf'] = rgwperf[rgwtypeid]
    del rgwperf[rgwtypeid]
    return rgwperf

def get_radosgw_process(rgwid):
    p = subprocess.Popen(
        'netstat -p | grep tcp | grep radosgw',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to get conf option')
    rgwprocessinfo = outdata.strip()
    close_wait = re.findall("[ :0-9a-zA-Z-]+CLOSE_WAIT[ 0-9]+/radosgw", rgwprocessinfo)
    rgwprocess = {}
    curRgwid, rgwprocess["pid"] = get_radosgw_typeid()
    if curRgwid is None or curRgwid == '':
        rgwprocess["radosgw_id"] = rgwid
    else:
        rgwprocess["radosgw_id"] = curRgwid
    rgwprocess["close_wait"] = 0
    if rgwprocess["pid"] and rgwprocess["pid"] != "":
        rgwperf = get_radosgw_perf(rgwprocess["radosgw_id"])
        rgwprocess.update(rgwperf)
    if close_wait:
        rgwprocess["close_wait"] = len(close_wait)
    return rgwprocess

def get_network_info(interface):
    output = subprocess.Popen(['ip', 'addr', 'show', 'dev', interface], stdout=subprocess.PIPE).communicate()[0].rsplit('\n')
    mtu = re.findall('mtu ([0-9]+) ', output[0])[0]
    link_ha = re.findall('link/(\w+) ([0-9a-fA-F:]+) ', output[1])[0]
    inet = None
    inet6 = None
    for line in output[2:]:   
        if not inet:
            tinet = re.findall('inet ([0-9\.]+)/([0-9]+) ', line)
            if tinet:
                inet = {"addr": tinet[0][0], "mask": tinet[0][1]}
                continue
        if not inet6:
            tinet6 = re.findall('inet6 ([0-9a-fA-F:]+)/([0-9]+) ', line)
            if (tinet6):
                inet6 = {"addr": tinet6[0][0], "mask": tinet6[0][1]}
        if inet and inet6:
            break  
    return {"mtu":int(mtu), "link": link_ha[0], "HWaddr": link_ha[1], "inet": inet, "inet6": inet6}

            

def get_hw_net(hostname, hw):
    local_nets = []
    # the disks
    nets = filter_hw(hw, "network")
    for net in nets:
        if net['id'].startswith('network'): 
            logname = "NA"
            if "logicalname" in net:
              if isinstance(net['logicalname'], list):
                  logname = net['logicalname'][0]
              else:
                  logname = net['logicalname']    
            else :
              continue
            description = "NA"
            if "description" in net: 
                description = net["description"]          
            product = "NA"
            if "product" in net: 
                product = net["product"]
            vendor = "NA"
            if "vendor" in net: 
                vendor = net["vendor"]          
            physid = "NA"
            if "physid" in net:
                physid = net["physid"]         
            netversion = "NA"
            if "version" in net:
                netversion = net["version"]         
            serial = "NA"
            if "serial" in net:
                serial = net["serial"]        
            netsize = 0
            if "size" in net:    
                if net["units"] == "bit/s":
                    netsize = net["size"]
            netcapacity = 0
            if "capacity" in net:    
                if net["units"] == "bit/s":
                    netcapacity = net["capacity"]
                # other units ?                  
            d = {"_id": hostname+":"+logname,
                 "description": description,
                 "product": product,
                 "manufacturer": vendor,
                 "physical_id": physid,
                 "logical_name": logname,
                 "version": netversion,
                 "serial_number": serial,
                 "size": netsize,
                 "capacity": netcapacity,
                 "stat": None
                 }
            d_info = get_network_info(logname)
            d.update(d_info)
            local_nets.append(d)
    return local_nets

def get_hw_cpu(hostname, hw):
    local_cpus = []
    # the cpus
    cpus = filter_hw(hw, "processor")
    for cpu in cpus:
        if cpu['id'].startswith('cpu'): 
            description = "NA"
            if "description" in cpu: 
                description = cpu["description"]          
            product = "NA"
            if "product" in cpu: 
                product = cpu["product"]
            vendor = "NA"
            if "vendor" in cpu: 
                vendor = cpu["vendor"]          
            physid = "NA"
            if "physid" in cpu:
                physid = cpu["physid"]         
            cpuversion = "NA"
            if "version" in cpu:
                cpuversion = cpu["version"]          
            frequency = 0
            if "size" in cpu:    
                if cpu["units"] == "Hz":
                    frequency = cpu["size"]
            capacity = 0
            if "capacity" in cpu:    
                if cpu["units"] == "Hz":
                    capacity = cpu["capacity"]
            cpuwidth = 0
            if "width" in cpu:    
                cpuwidth = cpu["width"]
            cores = 0
            enabledcores = 0
            threads = 0
            if "configuration" in cpu:   
                config = cpu["configuration"]
                if "cores" in config:
                    cores = int(config["cores"])
                if "enabledcores" in config:
                    enabledcores = int(config["enabledcores"])
                if "threads" in config:
                    threads = int(config["threads"])

            c = {"_id": hostname+":"+physid,
                 "description": description,
                 "product": product,
                 "manufacturer": vendor,
                 "physical_id": physid,
                 "version": cpuversion,
                 "capacity": capacity,
                 "frequency": frequency,
                 "width": cpuwidth,
                 "cores": cores,
                 "enabledcores": enabledcores,
                 "threads": threads,
                 "stat": None
                 }
            local_cpus.append(c)
    return local_cpus

# get type of the host,type: M-monitor, O-osd, R-radosgw
def get_host_type(hostname):
    type = ''
    for s in ['ceph-mon','ceph-osd','radosgw']:
        p = subprocess.Popen(
            'ps aux | grep '+s+' | wc -l',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        outdata, errdata = p.communicate()
        if len(errdata):
            raise RuntimeError('unable to get conf option')
        if (int(outdata.strip()) != 0   ):
            if s == 'ceph-mon':
                type = type + 'M'
            elif s == 'ceph-osd':
                type = type + 'O'
            else:
                type = type + 'R'
    return type

def init_host(hostname, db):
    hw = get_hw()
    hw_disks, hw_pdisks = get_hw_disk(hostname, hw, db)
    for d in hw_disks:
        db.disks.update({'_id': d['_id']}, d, upsert=True)
      
    partitions = get_partitions(hostname)
    for p in partitions:
        db.partitions.update({'_id': p['_id']}, p, upsert=True)
           
    hw_nets = get_hw_net(hostname, hw)
    for n in hw_nets:
        db.net.update({'_id': n['_id']}, n, upsert=True)
       
    hw_cpus = get_hw_cpu(hostname, hw)
    for c in hw_cpus:
        db.cpus.update({'_id': c['_id']}, c, upsert=True)

    hw_raids = get_hw_raids(hostname)
    for r in hw_raids:
        db.raids.update({'_id': r['_id']}, r, upsert=True)
    host_type = get_host_type(hostname)
    host__ = {'_id': hostname, #fqdn
              "hostip": socket.gethostbyname(hostname),
              "type": host_type,
              "timestamp": int(round(time.time() * 1000)),
              "mem": None,
              "swap": None,
              "disks": [DBRef("disks",  d["_id"]) for d in hw_disks],
              "raids": [DBRef("raids", r["_id"]) for r in hw_raids],
              "partitions": [DBRef("partitions",  p["_id"]) for p in partitions],
              "cpus": [DBRef("cpus",  c["_id"]) for c in hw_cpus],
              "cpus_stat": None,
              "network_interfaces": [DBRef("net",  n["_id"]) for n in hw_nets]
              }

    db.hosts.update({'_id': hostname}, host__, upsert=True)
    return hw_disks, hw_pdisks, partitions, hw_nets, hw_cpus, hw_raids



disk_stat_hdr = ["rrqm_s", "wrqm_s", "r_s" , "w_s", "rkB_s", "wkB_s"]

def pick_rgw_process(db, hostname):
    print str(datetime.datetime.now()), "-- Pick Rgw process"
    sys.stdout.flush()
    currRgw = db.radosgwprocess.find({"hostname":hostname}).limit(1).sort([("timestamp" , -1)])
    radosgwprocess = get_radosgw_process(currRgw[0]['radosgw_id'])
    rgwprocess = {}
    if radosgwprocess:
        # rgwprocess["host"] = DBRef("hosts", hostname)
        rgwprocess["hostname"] = hostname
        rgwprocess["hostip"] = socket.gethostbyname(hostname)
        rgwprocess["timestamp"] = int(round(time.time() * 1000))
        rgwprocess.update(radosgwprocess)
        rgwprocess_id = db.radosgwprocess.insert(rgwprocess)
        db.hosts.update({"_id": hostname}, {"$set": {"radosgwprocess": DBRef("radosgwprocess", rgwprocess_id)}})

#raid bbu stat
def pick_raid_bbu_stat(db, hw_raids):
    print str(datetime.datetime.now()), "-- Pick RAID BBU Stats"
    sys.stdout.flush()
    for r in hw_raids:
        adapter = r["adapter"]
        properties = get_bbu_properties(adapter)
        status = get_bbu_status(adapter)
        raid_bbu_stat = {}
        if properties and status:
            raid_bbu_stat["raids"] = DBRef("raids", r['_id'])
            raid_bbu_stat["timestamp"] = int(round(time.time() * 1000))
            raid_bbu_stat.update(properties)
            raid_bbu_stat.update(status)
            raid_bbu_stat_id = db.raidbbustat.insert(raid_bbu_stat)
            db.raids.update({"_id": r["_id"]}, {"$set": {"bbustat": DBRef("raidbbustat", raid_bbu_stat_id)}})


# disk stat
def pick_disk_stat(db, hw_disks):
    print str(datetime.datetime.now()), "-- Pick Disk Stats"  
    sys.stdout.flush()
    p = subprocess.Popen(args=['iostat', '-dx']+[d["logical_name"] for d in hw_disks], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    if len(errdata):
        raise RuntimeError('unable to run iostat: %s' % errdata)
    lines = outdata.rstrip().splitlines()
    for d in hw_disks:
        dev = re.findall('.*/([a-zA-Z0-9]+)', d['logical_name'])[0]
        iostat = [line for line in lines if re.match(dev+'.*', line)]
        if iostat:
            lineio = iostat[0].split()[1:]
            diskstat = dict([(k, float(v.replace(',', '.'))) for k, v in zip(disk_stat_hdr, lineio)])
            diskstat["disk"] = DBRef("disks", d["_id"])
            diskstat["timestamp"] = int(round(time.time() * 1000)) 
            disk_stat_id = db.diskstat.insert(diskstat)
            db.disks.update({"_id": d["_id"]}, {"$set": {"stat": DBRef("diskstat", disk_stat_id)}})
           
#pick disk smart
def pick_disks_smart(db, hw_pdisks):
    print str(datetime.datetime.now()), "-- Pick Disks Smart"
    sys.stdout.flush()
    for pd in hw_pdisks:
        logname = pd["logical_name"]
        #targetid = d["target_id"]
        deviceid = pd["device_id"]
        disk_smart = get_disk_smart(logname, deviceid)
        if disk_smart:
            disks_smart = {}
            disks_smart["pdisk"] = DBRef("pdisks", pd['_id'])
            disks_smart["timestamp"] = int(round(time.time() * 1000))
            disks_smart.update(disk_smart)
            disk_smart_id = db.disksmart.insert(disks_smart)
            db.pdisks.update({"_id": pd["_id"]}, {"$set": {"smart": DBRef("disksmart", disk_smart_id)}})



# net stat
def pick_net_stat(db, hw_nets):
    print str(datetime.datetime.now()), "-- Pick Net Stats"  
    sys.stdout.flush()
    netio = psutil.net_io_counters(pernic=True)
    for n in hw_nets:
        net_interface = n["logical_name"]
        netstat = netio[net_interface]
        if netstat:
            network_interface_stat = {"network_interface": DBRef("net", n['_id']),
                                      "timestamp": int(round(time.time() * 1000)),
                                      "rx": {"packets": netstat.packets_recv,
                                             "errors": netstat.errin,
                                             "dropped": netstat.dropin,
                                             "bytes": netstat.bytes_recv
                                             },
                                      "tx": {"packets": netstat.packets_sent,
                                             "errors": netstat.errout,
                                             "dropped": netstat.dropout,
                                             "bytes": netstat.bytes_sent
                                            }
                                      }
            network_interface_stat_id = db.netstat.insert(network_interface_stat)
            db.net.update({"_id": n["_id"]}, {"$set": {"stat": DBRef("netstat", network_interface_stat_id)}})
     
# transform a set of object attributes to dict      
def objToDict(obj, attrs):
    dict_res = {}
    for attr in attrs :
        if hasattr(obj, attr) :
            dict_res[attr] = getattr(obj, attr)
    return dict_res
            
# cpu stat
def pick_cpu_stat(hostname, db):
    print str(datetime.datetime.now()), "-- Pick CPU Stats"  
    sys.stdout.flush()
    cputimes = psutil.cpu_times_percent()
    cpus_stat = objToDict(cputimes, ["user", "system", "idle", "iowait", "irq", "softirq", "steal", "guest", "guest_nice"])
    cpus_stat["timestamp"] = int(round(time.time() * 1000))
    cpus_stat["host"] = DBRef("hosts",  hostname)
                 
    cpus_stat_hostx_id = db.cpustat.insert(cpus_stat)
    db.hosts.update({"_id": hostname}, {"$set": {"stat": DBRef("cpus_stat", cpus_stat_hostx_id)}})
        

def pick_ceph_processes_v2(hostname, db):
    # Compatibility with psutil V2.x
    print str(datetime.datetime.now()), "-- Pick Ceph Processes V2"
    sys.stdout.flush()
    iterP = psutil.process_iter()
    ceph_procs = [p for p in iterP if p.name().startswith('ceph-')]
    
    for ceph_proc in ceph_procs:
        # print ceph_proc, " ", ceph_proc.cmdline()[1:]
        options, remainder = getopt.getopt(ceph_proc.cmdline()[1:], 'ic:f', ['cluster=', 'id', 'config', 'pid-file'])
        clust = None
        id = None
        
        for opt, arg in options:
            if opt in ("-i", "--id"):
                id = arg
            elif opt in '--cluster':
                clust = arg
        
        if db.name == clust:    
            p_db = {"timestamp": int(round(time.time() * 1000)),
                    "host": DBRef("hosts",  hostname),
                    "pid": ceph_proc.pid,
                    "mem_rss": ceph_proc.memory_info_ex().rss,
                    "mem_vms": ceph_proc.memory_info_ex().vms,
                    "mem_shared": ceph_proc.memory_info_ex().shared,
                    "num_threads": ceph_proc.num_threads(),
                    "cpu_times_user": ceph_proc.cpu_times().user,
                    "cpu_times_system": ceph_proc.cpu_times().system,
                    }

            if ceph_proc.name() == 'ceph-osd':
                # osd       
                p_db["osd"] = DBRef("osd", id)
                procid = db.processstat.insert(p_db)
                db.osd.update({'_id': id}, {"$set": {"process": DBRef("process", procid)}})
            elif ceph_proc.name() == 'ceph-mon':
                # mon 
                p_db["mon"] = DBRef("mon", id)
                procid = db.processstat.insert(p_db)
                db.mon.update({'_id': id}, {"$set": {"process": DBRef("process", procid)}})
           

def pick_ceph_processes_v1(hostname, db):
    # Compatibility with psutil V1.x
    print str(datetime.datetime.now()), "-- Pick Ceph Processes V1"
    sys.stdout.flush()
    iter_p = psutil.process_iter()
    ceph_procs = [p for p in iter_p if p.name.startswith('ceph-')]

    for ceph_proc in ceph_procs:
        options, remainder = getopt.getopt(ceph_proc.cmdline[1:], 'i:f', ['cluster=', 'pid-file'])

        clust = None
        id = None

        for opt, arg in options:
            if opt == '-i':
                id = arg
            elif opt in  '--cluster':
                clust = arg

        if db.name == clust:
            p_db = {"timestamp": int(round(time.time() * 1000)),
                    "host": DBRef("hosts",  hostname),
                    "pid": ceph_proc.pid,
                    "mem_rss": ceph_proc.get_ext_memory_info().rss,
                    "mem_vms": ceph_proc.get_ext_memory_info().vms,
                    "mem_shared": ceph_proc.get_ext_memory_info().shared,
                    "num_threads": ceph_proc.get_num_threads(),
                    "cpu_times_user": ceph_proc.get_cpu_times().user,
                    "cpu_times_system": ceph_proc.get_cpu_times().system,
                    }

            if ceph_proc.name == 'ceph-osd':
                # osd
                p_db["osd"] = DBRef("osd", id)
                procid = db.processstat.insert(p_db)
                db.osd.update({'_id': id}, {"$set": {"process": DBRef("process", procid)}})
            elif ceph_proc.name == 'ceph-mon':
                # mon
                p_db["mon"] = DBRef("mon", id)
                procid = db.processstat.insert(p_db)
                db.mon.update({'_id': id}, {"$set": {"process": DBRef("process", procid)}})

# delete the oldest stats
# window in second
def drop_stat(db, collection, window):
    before = int((time.time() - window) * 1000)
    print str(datetime.datetime.now()), "-- drop Stats:", collection, "before", before       
    db[collection].remove({"timestamp": {"$lt": before}})


def heart_beat(hostname, db):
    beat = {"timestamp": int(round(time.time() * 1000)),}
    db.sysprobe.update({'_id': hostname}, {"$set": beat}, upsert=True)

reQueue = Queue()
con = Condition()

def execShell(db, op):
    operateCode = op['operate']
    opCodes = Operate().op_codes
    shellCmd = ''
    shellOpt = ''
    if opCodes.has_key(operateCode):
        shellCmd = opCodes[operateCode]
    if op.has_key('opvar') and op.has_key('opval'):
        if op['opvar'] == 'osdid':
            shellOpt = '.'+str(op['opval'])
        else:
            shellOpt = str(op['opval'])
    print('%s -- %s%s'%(str(datetime.datetime.now()),str(shellCmd),str(shellOpt)))
    p = subprocess.Popen(
        str(shellCmd) + str(shellOpt),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outdata, errdata = p.communicate()
    op['cmdline'] = str(shellCmd) + str(shellOpt)
    if len(errdata):
        # raise RuntimeError('unable to exec command: %s.%s, %s'%(str(shellCmd),str(shellOpt),errdata))
        op['description'] = str(shellCmd) + str(shellOpt) + '\n' + outdata.strip() + errdata.strip()
        print('unable to exec command: %s%s, %s'%(str(shellCmd),str(shellOpt),errdata.strip()))
        op['opstatus'] = int(2)
    else:
        if operateCode == 'OP008':
            op['description'] = 'stop radosgw process with kill command'
        else:
            op['description'] = str(shellCmd) + str(shellOpt) + '\n' + outdata.strip() + errdata.strip()
        print(outdata.strip())
        op['opstatus'] = int(1)
    op['operateTime'] = int(round(time.time() * 1000))
    db.operationlog.update({'_id':op['_id']}, op)

def getOperationFromDb(db, hostip):
    print str(datetime.datetime.now()), "-- Pick get operation from db"
    result = db.operationlog.find({"destip":hostip, "opstatus":0}).sort([("operateTime",1)])
    for op in result:
        reQueue.put(op)

def operationExec(db):
    print str(datetime.datetime.now()), "-- Pick exec operation"
    while not reQueue.empty():
        op = reQueue.get()
        execShell(db, op)
    pass

class OperationProducer(Thread):
    def __init__(self, event, function, args=[]):
        Thread.__init__(self)
        self.stopped = event
        # self.function = function
        self.args = args
    def run(self):
        global reQueue
        while True:
            if con.acquire():
                if reQueue.empty():
                    getOperationFromDb(*self.args)
                    con.notify()
                else:
                    con.wait()
                con.release()
                time.sleep(1)

class OperationConsumer(Thread):
    def __init__(self, event, function, args=[]):
        Thread.__init__(self)
        self.stopped = event
        # self.function = function
        self.args = args
    def run(self):
        global reQueue
        while True:
            if con.acquire():
                if reQueue.empty():
                    con.wait()
                else:
                    operationExec(*self.args)
                    con.notify()
                con.release()
                time.sleep(1)

class Repeater(Thread):
    #period in second
    def __init__(self, event, function, args=[], period=5.0):
        Thread.__init__(self)
        self.stopped = event
        self.period = period
        self.function = function
        self.args = args

    def run(self):
        while not self.stopped.wait(self.period):
            try:
                # call a function
                self.function(*self.args)
            except Exception, e:
                # try later
                print str(datetime.datetime.now()), "-- WARNING : "+self.function.__name__ + " did not worked : ", e
                exc_type, exc_value, exc_traceback = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_traceback)
                pass


def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)


# ceph probe 
# cephClient = httplib.HTTPConnection("localhost", port)

# gethostname -> hn
# if hn is mon of rank 0 -> update db


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg        


evt = Event()
   
   
def handler(signum, frame):
    print 'Signal handler called with signal', signum
    evt.set()
    
    
class SysProbeDaemon(Daemon):
    def __init__(self, pidfile):
        Daemon.__init__(self, pidfile, stdout=logfile, stderr=logfile)
        
    def run(self):
        print str(datetime.datetime.now())
        print "SysProbe loading"
        # load conf
        data = load_conf()
        cluster_name = data.get("cluster", "ceph")
        print "cluster = ", cluster_name
        
        ceph_conf_file = data.get("ceph_conf", "/etc/ceph/ceph.conf")
        print "cephConf = ", ceph_conf_file
        
        fsid = ceph_conf_global(ceph_conf_file, 'fsid')
        print "fsid = ", fsid
        
        hb_refresh = data.get("hb_refresh", 5)
        print "hb_refresh = ", hb_refresh
        
        mem_refresh = data.get("mem_refresh", 60)
        print "mem_refresh = ", mem_refresh
        
        mem_window = data.get("mem_window", 1200)
        print "mem_window = ", mem_window
        
        swap_refresh = data.get("swap_refresh", 600)
        print "swap_refresh = ", swap_refresh
        
        swap_window = data.get("swap_window", 3600)
        print "swap_window = ", swap_window
        
        disk_refresh = data.get("disk_refresh", 60)
        print "disk_refresh = ", disk_refresh

        disk_smart_refresh = data.get("disk_smart_refresh", 86400)
        print "disk_smart_refresh = ", disk_smart_refresh

        raid_bbu_refresh = data.get("raid_bbu_refresh", 86400)
        print "raid_bbu_refresh = ", raid_bbu_refresh

        disk_window = data.get("disk_window", 1200)
        print "disk_window = ", disk_window

        disk_smart_window = data.get("disk_smart_window", 3456000)
        print "disk_smart_window = ", disk_smart_window

        raid_bbu_window = data.get("raid_bbu_window", 3456000)
        print "raid_bbu_window = ", raid_bbu_window

        partition_refresh = data.get("partition_refresh", 60)
        print "partition_refresh = ", partition_refresh
        
        partition_window = data.get("partition_window", 1200)
        print "partition_window = ", partition_window
        
        cpu_refresh = data.get("cpu_refresh", 60)
        print "cpu_refresh = ", cpu_refresh

        rgwprocess_refresh = data.get("rgwprocess_refresh", 60)
        print "rgwprocess_refresh = ", rgwprocess_refresh

        rgwprocess_window = data.get("rgwprocess_window", 60)
        print "rgwprocess_window = ", rgwprocess_window
        
        cpu_window = data.get("cpu_window", 1200)
        print "cpu_window = ", cpu_window
        
        net_refresh = data.get("net_refresh", 30)
        print "net_refresh = ", net_refresh
        
        net_window = data.get("net_window", 1200)
        print "net_window = ", net_window       
        
        process_refresh = data.get("process_refresh", 60)
        print "process_refresh = ", process_refresh
        
        process_window = data.get("process_window", 1200)
        print "process_window = ", process_window

        operation_window = data.get("operation_window", 604800)
        print "operation_window = ", operation_window
        
        mongodb_host = data.get("mongodb_host", None)
        print "mongodb_host = ", mongodb_host
        
        mongodb_port = data.get("mongodb_port", None)
        print "mongodb_port = ", mongodb_port

        is_mongo_replicat = data.get("is_mongo_replicat", 0)
        print "is_mongo_replicat = ", is_mongo_replicat

        mongodb_set = "'"+data.get("mongodb_set", None)+"'"
        print "mongodb_set = ", mongodb_set

        mongodb_replica_set =data.get("mongodb_replicaSet", None)
        print "mongodb_replicaSet = ", mongodb_replica_set

        mongodb_read_preference = data.get("mongodb_read_preference", None)
        print "mongodb_read_preference = ", mongodb_read_preference

        is_mongo_authenticate = data.get("is_mongo_authenticate", 0)
        print "is_mongo_authenticate", is_mongo_authenticate

        mongodb_user = data.get("mongodb_user", "cephdefault")
        print "mongodb_user = ", mongodb_user

        mongodb_passwd = data.get("mongodb_passwd", None)
        print "mongodb_passwd = ", mongodb_passwd


        # end conf extraction

        print "version psutil = ", psutil_version, " (", psutil.__version__, ")"
        if (psutil.__version__ < "1.2.1") :
            print "ERROR : update your psutil to a earlier version (> 1.2.1)"
            sys.exit(2)
            
        sys.stdout.flush()
        
        #hostname = socket.gethostname()
        hostname = socket.getfqdn()
        hostip = socket.gethostbyname(hostname)
        print "hostname = ", hostname
    
        if is_mongo_replicat == 1:
            print "replicat set connexion"
            client = MongoReplicaSetClient(eval(mongodb_set), replicaSet=mongodb_replica_set, read_preference=eval(mongodb_read_preference))
        else:
            print "no replicat set"
            client = MongoClient(mongodb_host, mongodb_port)

        db = client[fsid]

        if is_mongo_authenticate == 1:
            print "authentication  to database"
            db.authenticate(mongodb_user, mongodb_passwd)
        else:
            print "no authentication" 

        
        
        HWdisks, HWpdisks, partitions, HWnets, HWcpus, HWraids = init_host(hostname, db)
                
        data["_id"] = hostname   
        db.sysprobe.remove({'_id': hostname})
        db.sysprobe.insert(data)
        
        hb_thread = None    
        if hb_refresh > 0:
            hb_thread = Repeater(evt, heart_beat, [hostname, db], hb_refresh)
            hb_thread.start()
        
        cpu_thread = None    
        if cpu_refresh > 0:
            cpu_thread = Repeater(evt, pick_cpu_stat, [hostname, db], cpu_refresh)
            cpu_thread.start()

        rgwprocess_thread = None
        if rgwprocess_refresh > 0:
            rgwprocess_thread = Repeater(evt, pick_rgw_process, [db, hostname], rgwprocess_refresh)
            rgwprocess_thread.start()

        net_thread = None
        if net_refresh > 0:
            net_thread = Repeater(evt, pick_net_stat, [db, HWnets], net_refresh)
            net_thread.start()
        
        mem_thread = None
        if mem_refresh > 0:
            mem_thread = Repeater(evt, pick_mem, [hostname, db], mem_refresh)
            mem_thread.start()
        
        swap_thread = None
        if swap_refresh > 0: 
            swap_thread = Repeater(evt, pick_swap, [hostname, db], swap_refresh)
            swap_thread.start()

        smart_thread = None
        if disk_smart_refresh > 0:
            smart_thread = Repeater(evt, pick_disks_smart, [db, HWpdisks], disk_smart_refresh)
            smart_thread.start()

        raid_bbu_thread = None
        if raid_bbu_refresh > 0:
            raid_bbu_thread = Repeater(evt, pick_raid_bbu_stat, [db, HWraids], raid_bbu_refresh)
            raid_bbu_thread.start()

        disk_thread = None
        if disk_refresh > 0:
            disk_thread = Repeater(evt, pick_disk_stat, [db, HWdisks], disk_refresh)
            disk_thread.start()
        
        part_thread = None
        if partition_refresh > 0:
            part_thread = Repeater(evt, pick_partitions_stat, [hostname, db], partition_refresh)
            part_thread.start()

        # operation_thread = None
        # if operation_refresh > 0:
        #     operation_thread = Repeater(evt, pick_operation_process,[db, hostip, operation_refresh, operation_thread], operation_refresh)
        #     operation_thread.start()

        getOperation_thread = OperationProducer(evt, getOperationFromDb,[db, hostip])
        getOperation_thread.start()

        execOperation_thread = OperationConsumer(evt, operationExec,[db])
        execOperation_thread.start()

        process_thread = None
        if process_refresh > 0:
            if psutil_version == "1":
                process_thread = Repeater(evt, pick_ceph_processes_v1, [hostname, db], process_refresh)
            else:
                process_thread = Repeater(evt, pick_ceph_processes_v2, [hostname, db], process_refresh)
            process_thread.start()



        # drop thread
        cpu_db_drop_thread = None    
        if cpu_window > 0:
            cpu_db_drop_thread = Repeater(evt, drop_stat, [db, "cpustat", cpu_window], cpu_window)
            cpu_db_drop_thread.start()

        rgwprocess_db_drop_thread = None
        if rgwprocess_window > 0:
            rgwprocess_db_drop_thread = Repeater(evt, drop_stat, [db, "rgwprocess",rgwprocess_window], rgwprocess_window)
            rgwprocess_db_drop_thread.start()

        net_db_drop_thread = None
        if net_window > 0:
            net_db_drop_thread = Repeater(evt, drop_stat, [db, "netstat", net_window], net_window)
            net_db_drop_thread.start()
        
        mem_db_drop_thread = None
        if mem_window > 0:
            mem_db_drop_thread = Repeater(evt, drop_stat, [db, "memstat", mem_window], mem_window)
            mem_db_drop_thread.start()
        
        swap_db_drop_thread = None
        if swap_window > 0: 
            swap_db_drop_thread = Repeater(evt, drop_stat, [db, "swapstat", swap_window], swap_window)
            swap_db_drop_thread.start()
        
        disk_db_drop_thread = None
        if disk_window > 0:
            disk_db_drop_thread = Repeater(evt, drop_stat, [db, "diskstat", disk_window], disk_window)
            disk_db_drop_thread.start()

        operation_db_drop_thread = None
        if operation_window > 0:
            operation_db_drop_thread = Repeater(evt, drop_stat, [db, "operationlog", operation_window], operation_window)
            operation_db_drop_thread

        disk_smart_db_drop_thread = None
        if disk_smart_window > 0:
            disk_db_drop_thread = Repeater(evt, drop_stat, [db, "disksmart", disk_smart_window], disk_smart_window)
            disk_db_drop_thread.start()

        raid_bbu_db_drop_thread = None
        if raid_bbu_window > 0:
            raid_bbu_db_drop_thread = Repeater(evt, drop_stat, [db, "raidbbustat", raid_bbu_window], raid_bbu_window)
            raid_bbu_db_drop_thread.start()

        part_db_drop_thread = None
        if partition_window > 0:
            part_db_drop_thread = Repeater(evt, drop_stat, [db, "partitionstat", partition_window], partition_window)
            part_db_drop_thread.start()
        
        process_db_drop_thread = None
        if process_window > 0:
            process_db_drop_thread = Repeater(evt, drop_stat, [db, "processstat", process_window], process_window)
            process_db_drop_thread.start()
        
        signal.signal(signal.SIGTERM, handler)
        
        while not evt.isSet(): 
            evt.wait(600)
        
        print str(datetime.datetime.now())
        print "SysProbe stopped"
   

if __name__ == "__main__":   
    ensure_dir(logfile)
    ensure_dir(runfile)
    daemon = SysProbeDaemon(runfile)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'status' == sys.argv[1]:
            daemon.status()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart|status" % sys.argv[0]
        sys.exit(2)
