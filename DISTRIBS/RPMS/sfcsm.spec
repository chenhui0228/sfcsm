Summary: sfcsm
Name: sfcsm
%define sfcsm_version 1.4.1
Version: %{sfcsm_version}
Release: 0
License: Apache License
Packager: chenhui
Distribution: Redhat
Vendor: sfcsmTeams
AutoReqProv: no
Source0: sfcsm.tar.gz
BuildRoot: %{_tmppath}/%{name}-root
BuildArch: noarch
Summary: install ceph probe and monitor clusters

%description
install  sysprobe scripts

%package common
Summary: common file beetwen all packages
Requires: python-bson
Requires: python-pymongo
%description common
install all conf files

%package sysprobe
Summary: monitor system
Requires: python-psutil
Requires: lshw
Requires: sysstat
Requires: sfcsm-common
%description sysprobe
install sysprobe scripts

%package cephprobe
Summary: monitoring  of ceph cluster
Requires: lshw
Requires: sfcsm-common
%description cephprobe
install ceph prob only

%package cephrestapi
Summary: allow ceph rest api compute
Requires: lshw
Requires: ceph
%description cephrestapi
install a ceph-rest-api start script

%package admviz
summary:  install interface  of sfcsm viz
Requires: sfcsm-common
Requires: httpd >= 2.4.0
Requires: python-flask
Requires: mod_wsgi
Requires: python-requests
Requires: python-simplejson
Requires: python-ceph

%description admviz
install the admin interface
Summary: allow ceph rest api compute

%package monitoring
Summary: monitoring  of ceph cluster
Requires: sfcsm-common
%description monitoring
install all check and include file  for  cpeh monitoring


%prep


%build
mkdir -p tmp/
cd tmp/
tar xvzf %{SOURCE0}

%install
mkdir -p %{buildroot}/opt/sfcsm/etc
mkdir -p %{buildroot}/opt/sfcsm/bin
mkdir -p %{buildroot}/opt/sfcsm/lib
mkdir -p %{buildroot}/opt/nrpe/etc/
mkdir -p %{buildroot}/opt/nrpe/libexec/
mkdir -p %{buildroot}/etc/init.d/
mkdir -p %{buildroot}/etc/logrotate.d/
mkdir -p %{buildroot}/var/www/sfcsm/
mkdir -p %{buildroot}/etc/httpd/conf.d/


cd tmp/sfcsm
install -m 600 sfcsmProbe/sysprobe.py %{buildroot}/opt/sfcsm/bin/
install -m 600 sfcsm-template.conf %{buildroot}/opt/sfcsm/etc/
install -m 600 sfcsmProbe/cephprobe.py %{buildroot}/opt/sfcsm/bin/
install -m 600 sfcsmProbe/daemon.py %{buildroot}/opt/sfcsm/bin/
install -m 700 DISTRIBS/confs/init.d/sysprobe %{buildroot}/etc/init.d/
install -m 700 DISTRIBS/confs/init.d/cephprobe %{buildroot}/etc/init.d/
install -m 700 DISTRIBS/confs/init.d/ceph-rest-api %{buildroot}/etc/init.d/
install -m 644 DISTRIBS/confs/logrotate/sfcsm  %{buildroot}/etc/logrotate.d/
install -m 644 DISTRIBS/confs/logrotate/cephrestapi  %{buildroot}/etc/logrotate.d/

install -m 644 DISTRIBS/confs/httpd/sfcsm.conf  %{buildroot}/etc/httpd/conf.d/

install -m 644 index.html  %{buildroot}/var/www/sfcsm/
for file in $(find sfcsmViz -type f); do
install -m 644 -D ${file}  %{buildroot}/var/www/sfcsm/${file#source/}
done

for file in $(find sfcsmCtrl -type f); do
install -m 644 -D ${file}  %{buildroot}/var/www/sfcsm/${file#source/}
done

install -m 644 sfcsmMonitor/nrpe/etc/nrpeceph.cfg  %{buildroot}/opt/nrpe/etc/
install -m 644 sfcsmMonitor/lib/libmongojuice.py %{buildroot}/opt/sfcsm/lib/

for file in $(find sfcsmMonitor/nrpe/libexec -type f); do
install -m 644 -D ${file}  %{buildroot}/opt/nrpe/libexec/${file#source/}
done

%clean
rm -rf $RPM_BUILD_ROOT

%files admviz
%defattr(-,root,root)
/var/www/sfcsm/index.html
/var/www/sfcsm/sfcsmCtrl/*
/var/www/sfcsm/sfcsmViz/*
/opt/sfcsm/lib/*
/opt/nrpe/etc/nrpeceph.cfg
/opt/nrpe/libexec/sfcsmMonitor/*
%config(noreplace) /etc/httpd/conf.d/sfcsm.conf

%files sysprobe
%defattr(-,root,root)
/opt/sfcsm/bin/sysprobe.py
/etc/init.d/sysprobe

%files common
%defattr(-,root,root)
/opt/sfcsm/bin/daemon.py
%config(noreplace)  /opt/sfcsm/etc/sfcsm-template.conf
/etc/logrotate.d/sfcsm
%files cephprobe
%defattr(-,root,root)
/opt/sfcsm/bin/cephprobe.py
/etc/init.d/cephprobe

%files cephrestapi
%defattr(-,root,root)
/etc/logrotate.d/cephrestapi
/etc/init.d/ceph-rest-api

#%files monitoring
#%defattr(-,root,root)
#/opt/sfcsm/lib/libmongojuice.py
#/opt/nrpe/libexec/*
#/opt/nrpe/etc/nrpeceph.cfg