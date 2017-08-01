sfcsm
========

**Sfcsm** is  a [Ceph](http://ceph.com) admin and supervision interface. It  relies on API provided by ceph. We also use  mongoDB to store real time metrics and history metrics.

Manual installation is fully described in the [sfcsm wiki](https://github.com/sfcsm/sfcsm/wiki)

All modules have been packaged: see [sfcsm packaging](https://github.com/sfcsm/sfcsm-packaging)

![sfcsm architecture](https://github.com/sfcsm/sfcsm/raw/master/documentation/sfcsm-platform.png)

The main folders are:

**documentation** contains diagram of sfcsm architecture, datamodel...

**sfcsmViz** : GUI to visualize Ceph cluster status (dashboard), relations between Ceph cluster objects and to manage some elements of a ceph cluster like flags, pools, erasure code profiles, rados gateway users and buckets...

**sfcsmCtrl** : server part of sfcsmViz. It provides a REST API, orchestrating calls to ceph rest API's, Rados gateway administration API and command lines

**sfcsmProbe** : probes to collect information about the cluster (Ceph and system info)

**sfcsmMonitor** : for supervision of Ceph (to be developed) 

Here is the dashboard screenshot and an object storage user management screenshot. Other screenshots can be found [there](https://github.com/sfcsm/sfcsm/tree/master/screenshots)

![dashboard](https://raw.github.com/sfcsm/sfcsm/master/screenshots/Screenshot-Status.png)
![Object storage user management](https://raw.github.com/sfcsm/sfcsm/master/screenshots/Screenshot-S3userManagement.png)

what do we plan in Sfcsm?
============================

- Extend or replace Ceph Rest API request by command lines
- Improve S3/swift features : zones and regions management
- Improve probes operations

Other ideas:
- Simulation : impact calculation in case of crushmap update (storage capacity, bandwidth,..)
