/**
 * Created by Alain Dechorgnat on 12/13/13.
 */

var StatusApp = angular.module('StatusApp', ['D3Directives','ngCookies','ngAnimate','SfcsmCommons'])
    .filter('bytes', funcBytesFilter)
    .filter('duration', funcDurationFilter);

StatusApp.controller("statusCtrl", function ($rootScope, $scope, $http , $cookieStore) {
    $scope.journal = [];
    $scope.osdControl =0;
    $scope.statOK = true;
    $scope.ProjectTitle = ProjectTitle;

    $scope.refreshPG = true;
    $scope.refreshPGcontrolClass = "icon-pause";

    $scope.viewControlPanel = false;
    $scope.viewMonitorModule = testAndSetCookie('viewMonitorModule',true);
    $scope.viewCapacityModule = testAndSetCookie('viewCapacityModule',true);
    $scope.viewPoolModule = testAndSetCookie('viewPoolModule',true);
    $scope.viewOsdModule = testAndSetCookie('viewOsdModule',true);
    $scope.viewPgStatusModule = testAndSetCookie('viewPgStatusModule',true);
    $scope.viewMdsModule = testAndSetCookie('viewMdsModule',true);

    function testAndSetCookie(param,defaultValue) {
        var value = $cookieStore.get(param);
        if (typeof value ==="undefined") {
            $cookieStore.put(param,defaultValue);
            value = defaultValue;
        }
        return value;
    }

    //refresh data every x seconds
    refreshData();
    refreshPGData();
    setInterval(function () {
        refreshData()
    }, 5 * 1000);
    setInterval(function () {
        refreshPGData()
    }, 10 * 1000);
    
    // start refreshOSDData when fsid is available
    var waitForFsid = function ($rootScope, $http,$scope){
        typeof $rootScope.fsid !== "undefined"? startRefresh($rootScope, $http,$scope) : setTimeout(function () {waitForFsid($rootScope, $http,$scope)}, 1000);
        function startRefresh($rootScope, $http,$scope){
            refreshOSDData();
            HardwareList($rootScope);
            OperationlogList($rootScope);
            setInterval(function () {
                refreshOSDData()
            }, 5 * 1000);
        }
    }
    waitForFsid($rootScope, $http, $scope);

    function refreshPGData() {
        $scope.date = new Date();
        $http({method: "get", url: cephRestApiURL + "df.json",timeout:8000})
            .success(function (data, status) {
                $scope.nbPools = data.output.pools.length;;
            });
        $http({method: "get", url: cephRestApiURL + "pg/dump_stuck.json",timeout:8000})
            .success(function (data, status) {
                // fetching stuck pg list
                var pg_stats = data.output;
                var pools = [];
                for (var i = 0; i < pg_stats.length; i++) {
                    var pg = pg_stats[i];
                    //console.log(pg.pgid + " : " + pg.state)
                    var numPool = pg.pgid.split(".")[0];
                    pools[numPool] = false;
                }
                var cnt = 0;
                for (var i = 0; i < pools.length; i++) {
                    if (typeof pools[i] !== "undefined") {
                        ++cnt;
                    }
                }
                $scope.uncleanPools = cnt;
                if (typeof $scope.nbPools !== "undefined") $scope.cleanPools = $scope.nbPools -cnt;
            });
    };

    function refreshOSDData() {
        $scope.date = new Date();
        var filter = {
            "$select":{},
            "$template":{
                "stat":1
            }
        }
        $http({method: "post", url: sfcsmCtrlURL + $rootScope.fsid+"/osd", params :{"depth":1} ,data:filter,timeout:4000})
            .success(function (data, status) {
                if (data[0].stat == null)
                    $scope.osdControl ="-";
                else
                    $scope.osdControl = ((+$scope.date)-data[0].stat.timestamp)/1000 ;
                $scope.osdsInUp = 0;
                $scope.osdsInDown = 0;
                $scope.osdsOutUp = 0;
                $scope.osdsOutDown = 0;
                $scope.statOK = true;
                for (var i = 0; i < data.length; i++) {
                    if (!data[i].lost) {
                        if (data[i].stat ==null){
                            console.error("missing stat for "+data[i].node.name);
                            $scope.statOK = false;
                        }
                        else {
                            if (data[i].stat.in) {
                                if (data[i].stat.up) $scope.osdsInUp++; else $scope.osdsInDown++;
                            }
                            else {
                                if (data[i].stat.up) $scope.osdsOutUp++; else $scope.osdsOutDown++;
                            }
                        }
                    }
                }
        }).error (function (data, status){
                console.log("can't fetch osd info in mongo");
                $scope.statOK = false;
        });
    };

    function refreshData() {
        //console.log("refreshing data...");
        $scope.date = new Date();
        $http({ method: "get", url: cephRestApiURL + "status.json", timeout: 4000 })
            .success(function (data) {
                $scope.pgmap = data.output.pgmap;
                if ( typeof  data.output.pgmap.degraded_objects === "undefined" ) $scope.pgmap.degraded_objects=0;


                $scope.mdsmap = data.output.mdsmap;
                $scope.mdsmap.up_standby = data.output.mdsmap["up:standby"];
                $scope.percentUsed = $scope.pgmap.bytes_used / $scope.pgmap.bytes_total;


                if ($scope.refreshPG) $scope.pgsByState = $scope.pgmap.pgs_by_state;

                $scope.read = (data.output.pgmap.read_bytes_sec ? data.output.pgmap.read_bytes_sec : 0);
                $scope.write = (data.output.pgmap.write_bytes_sec ? data.output.pgmap.write_bytes_sec : 0);
                $scope.recovery = (data.output.pgmap.recovering_bytes_per_sec ? data.output.pgmap.recovering_bytes_per_sec : 0);

                var iopsdata = { read: $scope.read , write : $scope.write , recovery : $scope.recovery };
                //graph.series.addData(iopsdata);
                //yAxis.render();
                //graph.render();

                $scope.health = {};
                $scope.health.severity = data.output.health.overall_status;
                // there may be several messages under data.output.health.summary
                $scope.health.summary="";
                var i = 0;
                while(typeof data.output.health.summary[i] !== "undefined"){
                    if ($scope.health.summary!="") $scope.health.summary+=" | ";
                    $scope.health.summary += data.output.health.summary[i].summary;
                    i++;
                }
                if ($scope.health.summary==""){
                    if (data.output.health.detail[0])
                        $scope.health.summary = data.output.health.detail[0];
                    else
                        //remove HEALTH_ in severity
                        $scope.health.summary = $scope.health.severity.substring(7);
                }
                $rootScope.healthSeverity = $scope.health.severity;
                historise();

                $scope.mons = data.output.monmap.mons;

                for (var i = 0; i < $scope.mons.length; i++) {
                    var mon = $scope.mons[i];
                    mon.health = "HEALTH_UNKNOWN"; // default for styling purpose
                    mon.quorum = "out";          // default for styling purpose
                    for (var j = 0; j < data.output.quorum_names.length; j++) {
                        if (mon.name == data.output.quorum_names[j]) {
                            mon.quorum = "in";
                            break
                        }
                    }
                    if (data.output.health.timechecks.mons) //not always defined
                        for (var j = 0; j < data.output.health.timechecks.mons.length; j++) {
                            mon2 = data.output.health.timechecks.mons[j];
                            if (mon.name == mon2.name) {
                                for (key in mon2) mon[key] = mon2[key];
                                break
                            }
                        }
                    for (var j = 0; j < data.output.health.health.health_services[0].mons.length; j++) {
                        mon2 = data.output.health.health.health_services[0].mons[j];
                        if (mon.name == mon2.name) {
                            for (key in mon2) {
                                if (( key == "health") && (mon[key]+"" != "undefined"))
                                    mon[key] =healthCompare(mon[key],mon2[key]);
                                else
                                    mon[key] = mon2[key];
                            }
                            break
                        }
                    }
                }

                function healthCompare(h1,h2){
                    if ((h1 == "HEALTH_ERROR")||(h2 == "HEALTH_ERROR")) return "HEALTH_ERROR";
                    if ((h1 == "HEALTH_WARN")||(h2 == "HEALTH_WARN")) return "HEALTH_WARN";
                    if ((h1 == "HEALTH_OK")||(h2 == "HEALTH_OK")) return "HEALTH_OK";
                    return "HEALTH_UNKNOWN";
                }

                var osdmap = data.output.osdmap.osdmap;
                $scope.osdsUp = osdmap.num_up_osds;
                $scope.osdsIn = parseInt(osdmap.num_in_osds);
                $scope.osdsOut = osdmap.num_osds - osdmap.num_in_osds;
                $scope.osdsDown = $scope.osdsIn - $scope.osdsUp + $scope.osdsOut;
                $scope.osdsNearFull = osdmap.nearfull?1:0;
                $scope.osdsFull = osdmap.full?1:0;
            })
            .error(function (data) {
                $scope.health = {};
                $scope.health.severity = "HEALTH_WARN";
                $scope.health.summary = "Status not available";
            });
    }

    $scope.refreshPGcontrol = function(){
        $scope.refreshPG = !$scope.refreshPG;
        if ($scope.refreshPG)
            $scope.refreshPGcontrolClass = "icon-pause";
        else
            $scope.refreshPGcontrolClass = "icon-play";
    }

    $scope.badgeClass = function (type, count) {
        if ((count == 0) || (count + "" == "undefined"))
            return "health_status_HEALTH_UNKNOWN mybadge";
        else
            return "health_status_HEALTH_" + type + " mybadge";
    }

    $scope.showModule = function(module,view){
        $cookieStore.put(module,view);
        $scope[module]=view;
    }

    $scope.getPgmapMessage=function(){
        if (typeof  $scope.pgmap ==="undefined") return "";
        var message = "";
        if ((typeof  $scope.pgmap.degraded_objects !=="undefined" )&&($scope.pgmap.degraded_objects!=0)) {
            if (message != "") message += ", ";
            message += $scope.pgmap.degraded_objects + " objects degraded on " + $scope.pgmap.degraded_total + " (" + (100 * $scope.pgmap.degraded_objects / $scope.pgmap.degraded_total).toFixed(3) + "%)";
        }
        if ((typeof  $scope.pgmap.misplaced_objects !=="undefined" )&&($scope.pgmap.misplaced_objects!=0)) {
            if (message != "") message += ", ";
            message += $scope.pgmap.misplaced_objects +" objects misplaced on "+$scope.pgmap.misplaced_total +" ("+ (100*$scope.pgmap.misplaced_objects/$scope.pgmap.misplaced_total).toFixed(3) +"%)";
        }
        return message;
    }

    function historise() {
        if ($scope.last_health_summary + "" == "undefined") {
            $scope.last_health_summary = $scope.health.summary;
            $scope.journal.unshift({"date": new Date(), "summary": $scope.health.summary});
            return;
        }
        if ($scope.last_health_summary != $scope.health.summary) {
            $scope.journal.unshift({"date": new Date(), "summary": $scope.health.summary});
            $scope.last_health_summary = $scope.health.summary;
        }
    }

    /********************************首页 start******************************************/
    {
        var indexData = IndexData();
        if (!isNullOrEmpty(indexData)) {
            var data = indexData;
            $scope.itemData = data.output;
            //PG信息
            var pgmap = data.output.pgmap;
            $scope.PGbtyesUsed = funcBytes(pgmap.bytes_used);
            $scope.PGbtyesAvail = funcBytes(pgmap.bytes_avail);
            $scope.PGbtyesTotal = funcBytes(pgmap.bytes_total);
            //集群总数据
            $scope.CByte_used = funcBytes(pgmap.bytes_used);
            $scope.CObject_total = 0;
            $scope.CMisplaced_objects = 0;
            $scope.CDegraded_objects = 0;
            if ("misplaced_total" in pgmap){
                $scope.CObject_total = pgmap.misplaced_total;
            }
            if ("misplaced_objects" in pgmap){
                $scope.CMisplaced_objects = pgmap.misplaced_objects;
            }
            if ("degraded_objects" in pgmap){
                $scope.CDegraded_objects = pgmap.degraded_objects;
            }
            $scope.CAbnormal_objects = $scope.CMisplaced_objects + $scope.CDegraded_objects;
            $scope.CRecovering_bytes_per_sec = funcBytes(pgmap.recovering_bytes_per_sec);
            $scope.CRecovering_objects_per_sec = pgmap.recovering_objects_per_sec;
            $scope.CMisplaced_ratio = funcBytes(pgmap.misplaced_ratio);

            if ((isNum(pgmap.degraded_total)||isNum(pgmap.misplaced_total)) && isNum(pgmap.recovering_bytes_per_sec) && $scope.CRecovering_objects_per_sec != 0)
                $scope.CRecoverying_tm = parseInt($scope.CAbnormal_objects / $scope.CRecovering_objects_per_sec);

            //Health信息
            var health_services = data.output.health.health.health_services[0].mons;
            var mons = data.output.monmap.mons;
            if (mons.length > 0 && health_services.length > 0) {
                for (var i = 0; i < mons.length; i++) {
                    for (var j = 0; j < health_services.length; j++) {
                        mons[i]["health"] = health_services[j].health;
                        if (health_services[j].name == mons[i].name && !isNullOrEmpty(health_services[j].health_detail))
                            mons[i]['health_detail'] = health_services[j].health_detail;
                    }
                }
            }
            $scope.HealthMonmap = mons;
            $scope.HealthServices = health_services;
            $scope.HealthStatus = data.output.health.overall_status;
            $scope.HealthbytesMisc = funcBytes(health_services[0].store_stats.bytes_misc);
            $scope.HealthbytesSst = funcBytes(health_services[0].store_stats.bytes_sst);
            $scope.HealthbytesTotal = funcBytes(health_services[0].store_stats.bytes_total);
        } else {
            $http.get(indexCtrlURL).success(function (data) {
                $scope.itemData = data.output;
                //PG信息
                var pgmap = data.output.pgmap;
                $scope.PGbtyesUsed = funcBytes(pgmap.bytes_used);
                $scope.PGbtyesAvail = funcBytes(pgmap.bytes_avail);
                $scope.PGbtyesTotal = funcBytes(pgmap.bytes_total);
                //集群总数据
                $scope.CByte_used = funcBytes(pgmap.bytes_used);
                $scope.CObject_total = 0;
                $scope.CMisplaced_objects = 0;
                $scope.CDegraded_objects = 0;
                if ("misplaced_total" in pgmap){
                    $scope.CObject_total = pgmap.misplaced_total;
                }
                if ("misplaced_objects" in pgmap){
                    $scope.CMisplaced_objects = pgmap.misplaced_objects;
                }
                if ("degraded_objects" in pgmap){
                    $scope.CDegraded_objects = pgmap.degraded_objects;
                }
                $scope.CAbnormal_objects = $scope.CMisplaced_objects + $scope.CDegraded_objects;
                $scope.CRecovering_bytes_per_sec = funcBytes(pgmap.recovering_bytes_per_sec);
                $scope.CRecovering_objects_per_sec = pgmap.recovering_objects_per_sec;
                $scope.CMisplaced_ratio = funcBytes(pgmap.misplaced_ratio);

                if ((isNum(pgmap.degraded_total)||isNum(pgmap.misplaced_total)) && isNum(pgmap.recovering_bytes_per_sec) && $scope.CRecovering_objects_per_sec != 0)
                    $scope.CRecoverying_tm = parseInt($scope.CAbnormal_objects / $scope.CRecovering_objects_per_sec);

                //Health信息
                var health_services = data.output.health.health.health_services[0].mons;
                var mons = data.output.monmap.mons;
                if (mons.length > 0 && health_services.length > 0) {
                    for (var i = 0; i < mons.length; i++) {
                        for (var j = 0; j < health_services.length; j++) {
                            mons[i]["health"] = health_services[j].health;
                            if (health_services[j].name == mons[i].name && !isNullOrEmpty(health_services[j].health_detail))
                                mons[i]['health_detail'] = health_services[j].health_detail;
                        }
                    }
                }
                $scope.HealthMonmap = mons;
                $scope.HealthServices = health_services;
                $scope.HealthStatus = data.output.health.overall_status;
                $scope.HealthbytesMisc = funcBytes(health_services[0].store_stats.bytes_misc);
                $scope.HealthbytesSst = funcBytes(health_services[0].store_stats.bytes_sst);
                $scope.HealthbytesTotal = funcBytes(health_services[0].store_stats.bytes_total);
            });
        }
    }
    /********************************首页 end******************************************/

    //StorageManage
    {
        /********************************pool start******************************************/
        {
            PoolList();
            function PoolList() {
                //pool data
                $http.get(poolListCtrlURL).success(function (data) {
                    $scope.PoolData = data.pools;
                    $scope.PoolNum = data.pools.length;
                    $scope.poolUsed = funcBytes(data.bytes_used_total);
                    $scope.poolTotal = data.objects_total;
                });
            }

            $(".close").click(function () {
                $scope.pool_again_visible = false;  //默认隐藏再次点击提交pg_placement_num
                $scope.pool_again_pg_num = false;   //默认再次点击保存确认时，启用
            });
            $scope.pool_again_visible = false;  //默认隐藏再次点击提交pg_placement_num
            $scope.pool_again_pg_num = false;   //默认再次点击保存确认时，启用
            $scope.detailOperation = function (model, obj) {
                $scope.Operation = obj;
                $('#' + model).modal('toggle');
                if (!isNullOrEmpty(obj)) {
                    //获取详情pool
                    $http.get(poolGetCtrURL + obj.id).success(function (data) {
                        $scope.Pooldisabled = false;
                        $scope.PoolIsEdit = true;
                        $scope.poolDetail = data.output;
                        if(!isNullOrEmpty(data.output)) {
                            $scope.PoolOldPgNum = data.output.pg_num;
                            if (parseInt(data.output.pg_placement_num) != parseInt(data.output.pg_num)) {
                                if (parseInt(data.output.pg_placement_num) > parseInt(data.output.pg_num))
                                    $scope.placement_num_tips = 'pg_placement_num大于pg_num';
                                else if (parseInt(data.output.pg_placement_num) < parseInt(data.output.pg_num))
                                    $scope.placement_num_tips = 'pg_placement_num小于pg_num';
                            }
                        }
                    });
                } else {
                    $scope.Pooldisabled = true;
                    $scope.PoolIsEdit = false;
                    //pool default detail information
                    $scope.PoolOldPgNum = '0';
                    var poolDetail = '{"pg_num":"0","pg_placement_num":"0","size":"3","type":"replicated","min_size":"1","crush_ruleset":"0","crash_replay_interval":"0","quota_max_objects":"0","quota_max_bytes":"0"}';
                    poolDetail = eval('(' + poolDetail + ')');
                    $scope.poolDetail = poolDetail;
                }
            };
            //pool信息编辑提交
            $scope.poolEdit = function () {
                if (confirm("是否确认执行此操作？")) {
                    var pg_num = parseInt($("input[name=pg_num]").val());
                    var pg_placement_num = parseInt($("input[name=pg_placement_num]").val());
                    if (pg_placement_num != pg_num) {
                        $scope.placement_num_tips = 'pg_placement_num不等于pg_num';
                    } else {
                        $("#checkData").show().addClass('checkdata');
                        $(".pool_tips").html('数据处理中，请稍后…');
                        var _data = '';
                        var pool = '';
                        var isTrue = true;
                        var isEdit = true;

                        $.each($(".poolDetail input"), function () {
                            var dom = $(this);
                            var name = dom.attr('name');
                            var value = dom.val();

                            if ((name == 'pool_name' || name == 'pg_num') && isNullOrEmpty(value)) {
                                alert(name + '不能为空');
                                isTrue = false;
                            }
                            if (name == 'pool')
                                pool = value;
                            else if (name == 'isedit')
                                isEdit = value;
                            else
                                _data += '"' + name + '":"' + value + '",';
                        });
                        if (!isNullOrEmpty(_data)) {
                            _data = '{' + _data.substring(0, _data.length - 1) + '}';
                            _data = eval('(' + _data + ')');
                        }
                        if (!isNullOrEmpty(_data) && isTrue) {
                            var _method = 'put';
                            if (isEdit == 'false')
                                _method = 'post';
                            $http({
                                method: _method,
                                url: poolPutCtrURL + pool,
                                data: "json=" + JSON.stringify(_data),
                                headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                            }).success(function (data, status) {
                                $(".pool_tips").html('处理完成');
                                setTimeout(function () {
                                    $("#checkData").animate({
                                        opacity: "hide"
                                    }, "slow");
                                }, 100);
                                PoolList();
                                if ($scope.pool_again_visible) {
                                    $scope.pool_again_visible = false;   //隐藏
                                    $scope.pool_again_pg_num = false;    //启用
                                    $(".close").click();    //关闭弹出窗
                                } else {
                                    $scope.pool_again_visible = true;   //显示
                                    $scope.pool_again_pg_num = true;    //禁用
                                }
                            }).error(function (data, status) {
                                $(".pool_tips").html(data);
                                setTimeout(function () {
                                    $("#checkData").animate({
                                        opacity: "hide"
                                    }, "slow");
                                }, 1000);
                            });
                        }
                    }
                }
            };
            $scope.poolDel = function (pool) {
                if (confirm("确认删除吗")) {
                    $("#checkData").show().addClass('checkdata');
                    $(".pool_tips").html('数据处理中，请稍后…');
                    $http({
                        method: 'delete',
                        url: poolDelCtrURL + pool,
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                    }).success(function (data, status) {
                        setTimeout(function () {
                            $(".pool_tips").html('处理完成');
                            $("#checkData").animate({
                                opacity: "hide"
                            }, "slow");
                        }, 100);
                        PoolList();
                    }).error(function (data, status) {
                        alert(data);
                        setTimeout(function () {
                            $("#checkData").animate({
                                opacity: "hide"
                            }, "slow");
                        }, 1000);
                    });
                }
            };
        }
        /********************************pool end******************************************/

        /********************************monitor end******************************************/
        {
            MonitorList();
            function MonitorList() {
                //monitor data
                $http.get(monitorListCtrlURL).success(function (data) {
                    $scope.MonitorData = data;
                });
            }

            $scope.monitorEnable = function (model, obj) {
                if (!isNullOrEmpty(model) && !isNullOrEmpty(obj)) {
                    if (confirm("是否确认执行此操作？")) {
                        $("#checkData").show().addClass('checkdata');
                        $(".monitor_tips").html('数据处理中，请稍后…');
                        var _data = '{"optype":"N","operate":"' + obj + '","destip":"' + model.addr + '"}';
                        _data = eval('(' + _data + ')');

                        $http({
                            method: 'post',
                            url: monitordaemonsCtrlURL,
                            data: JSON.stringify(_data),
                            headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                        }).success(function (data) {
                            $(".monitor_tips").html('处理成功');
                            setTimeout(function () {
                                $("#checkData").animate({
                                    opacity: "hide"
                                }, "slow");
                            }, 500);
                            MonitorList();
                        }).error(function (data, status) {
                            $(".monitor_tips").html(data);
                            setTimeout(function () {
                                $("#checkData").animate({
                                    opacity: "hide"
                                }, "slow");
                            }, 5000);
                        });
                    }
                }
            };
        }
        /********************************monitor end******************************************/

        /********************************osd end******************************************/
        {
            OsdList();
            function OsdList() {
                //monitor data
                $http.get(osdListCtrlURL).success(function (data) {
                    $scope.OsdData = data;
                });
            }
            $scope.osdEnable = function (model, obj) {
                if (!isNullOrEmpty(model) && !isNullOrEmpty(obj)) {
                    if (confirm("是否确认执行此操作？")) {
                        $("#checkData").show().addClass('checkdata');
                        $(".osd_tips").html('数据处理中，请稍后…');
                        var _data = '{"optype":"N","operate":"' + obj + '","destip":"' + model.hostip + '","opvar":"osdid","opval":' + model.osdid + '}';
                        _data = eval('(' + _data + ')');
                        $http({
                            method: 'post',
                            url: osddaemonsCtrlURL,
                            data: JSON.stringify(_data),
                            headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                        }).success(function (data) {
                            $(".osd_tips").html('命令下划成功');
                            setTimeout(function () {
                                $("#checkData").animate({
                                    opacity: "hide"
                                }, "slow");
                            }, 500);
                            OsdList();
                        }).error(function (data, status) {
                            $(".osd_tips").html(data);
                            setTimeout(function () {
                                $("#checkData").animate({
                                    opacity: "hide"
                                }, "slow");
                            }, 5000);
                        });
                    }
                }
            };
            $scope.osdEdit = function (model, obj) {
                if (confirm("是否确认执行此操作？")) {
                    $("#checkData").show().addClass('checkdata');
                    $(".osd_tips").html('数据处理中，请稍后…');
                    var _data = '{"stat":"' + obj + '","osdid":"' + model.osdid + '"}';
                    _data = eval('(' + _data + ')');
                    $http({
                        method: 'post',
                        url: osdEditCtrlURL,
                        data: JSON.stringify(_data),
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                    }).success(function (data) {
                        $(".osd_tips").html('处理成功');
                        setTimeout(function () {
                            $("#checkData").animate({
                                opacity: "hide"
                            }, "slow");
                        }, 500);
                        OsdList();
                    }).error(function (data, status) {
                        $(".osd_tips").html(data);
                        setTimeout(function () {
                            $("#checkData").animate({
                                opacity: "hide"
                            }, "slow");
                        }, 5000);
                    });
                }
            };

            $scope.detailOsdOperation = function (model, obj) {
                $('#' + model).modal('toggle');
                $(".osd_state input[type=radio]").prop("checked", false);
                $scope.OsdID = obj.osdid;
            };

            $(".osd_state input").change(function(){
                var key = $(this).val();
                CephAlert('正在处理....');
                if(!isNullOrEmpty($scope.OsdID) || $scope.OsdID == '0') {
                    $http({
                        method: 'post',
                        url: osdEditCtrlURL,
                        data: '{"stat":"' + key + '","osdid":"' + $scope.OsdID + '"}',
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                    }).success(function (data) {
                        CephAlert('命令下划成功');
                        OsdList();
                    }).error(function (data, status) {
                        CephAlert(data, 5000, {"width": "350px"});
                    });
                }
            });

            $scope.osdDel = function () {
                if (confirm("确认删除吗")) {
                    alert('已触发删除操作');
                }
            };
        }
        /********************************osd end******************************************/

        /********************************cluster start******************************************/
        {
            ClusterList();
            function ClusterList() {
                //monitor data
                $http.get(clusterListCtrlURL).success(function (data) {
                    $scope.ClusterData = data;
                });
            }
            $scope.detailCluOperation = function (model, obj) {
                $('#' + model).modal('toggle');
                $(".clu_state input[type=checkbox]").prop("checked", false);
                //获取cluster状态
                var indexData = IndexData();
                $scope.itemData = indexData.output;  //刷新数据
                if(!isNullOrEmpty($scope.itemData.health.summary)) {
                    var summary = $scope.itemData.health.summary;
                    for (var i = 0; i < summary.length; i++) {
                        var summarys = summary[i].summary;
                        if(summarys.indexOf('flag') > -1) {
                            var arr = summarys.split(' ');
                            var states = arr[0].split(',');
                            for(var j = 0;j < states.length;j++) {
                                $("#cb_box_" + states[j]).prop('checked', true);
                            }
                        }
                    }
                }
            };

            $(".clu_state input").change(function(){
                var key = $(this).val();
                var operate = 'set';
                if(!$(this).is(':checked')){
                    operate = 'unset';
                }
                CephAlert('正在处理....');
                $http({
                    method: 'post',
                    url: clusterSetCtrlURL,
                    data: '{"operate":"' + operate + '","key":"' + key + '"}',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                }).success(function (data) {
                    CephAlert('命令下划成功');
                    OsdList();
                }).error(function (data, status) {
                    CephAlert(data);
                });
            });
        }
        /********************************cluster end******************************************/

        /********************************rgw start******************************************/
        {
            RgwList();
            function RgwList() {
                //monitor data
                $http.get(rgwListCtrlURL).success(function (data) {
                    $scope.RgwData = data;
                });
            }

            $scope.rgwEnable = function (model, obj) {
                if (confirm("是否确认执行此操作？")) {
                    $("#checkData").show().addClass('checkdata');
                    $(".rgw_tips").html('数据处理中，请稍后…');

                    var opvar = 'rgwtypeid';
                    var opval = model.radosgw_id;
                    if(obj == 'OP008') {
                        opvar = 'pid';
                        opval = model.pid;
                    }
                    var _data = '{"optype":"N","operate":"' + obj + '","destip":"' + model.hostip + '","opvar":"' + opval + '","opval":"' + opval + '"}';
                    _data = eval('(' + _data + ')');
                    $http({
                        method: 'post',
                        url: rgwEditCtrlURL,
                        data: JSON.stringify(_data),
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                    }).success(function (data) {
                        $(".rgw_tips").html('处理成功');
                        setTimeout(function () {
                            $("#checkData").animate({
                                opacity: "hide"
                            }, "slow");
                        }, 500);
                        OsdList();
                    }).error(function (data, status) {
                        $(".rgw_tips").html(data);
                        setTimeout(function () {
                            $("#checkData").animate({
                                opacity: "hide"
                            }, "slow");
                        }, 5000);
                    });
                }
            };
        }
        /********************************rgw end******************************************/

        /********************************hardware start******************************************/
        {
            //HardwareList();
            function HardwareList($rootScope) {
                //hardware data
                $http({method: "get", url: sfcsmCtrlURL + $rootScope.fsid + "/hosts"}).
                success(function (data, status) {
                    $scope.status = status;
                    data[0]['fsid'] = $rootScope.fsid;
                    $scope.HardwareData =  data;
                }).
                error(function (data, status, headers) {
                    //alert("refresh hosts failed with status "+status);
                    $scope.status = status;
                    $scope.HardwareData =  data || "Request failed";
                });
            }
            $scope.detailHWOperation = function(model, obj){
                $('#' + model).modal('toggle');
                $(".hw_mb_ul li").removeClass('hw_active');
                $(".mb_hw_div").hide();
                $(".hw_cpu_div").show();
                $(".hw_cpu").addClass('hw_active');

                var uri = sfcsmCtrlURL + obj.fsid +"/hosts?depth=2";
                $http({method: "post", data: '{"_id" : "' + obj._id + '"}', url: uri }).
                success(function (data, status) {
                    $scope.nic =  data[0].network_interfaces;
                    $scope.raid =  data[0].raids;
                    $scope.disk =  data[0].disks;
                    $scope.part =  data[0].partitions;
                    $scope.status = status;
                }).
                error(function (data, status) {
                    $scope.status = status;
                    $scope.hosts =  data || "Request failed";
                    $dialogs.error("<h3>Can't display hosts with id "+nicid+"</h3><br>"+$scope.HardwareData);
                });

                ToCpuStatus(obj.fsid, obj._id);
                ToSwapStatus(obj.fsid, obj._id);
                ToMemStatus(obj.fsid, obj._id);
            };
            /******硬件详情 begin******/
            {
                function ToCpuStatus(fsid, hostId) {
                    var data = '{"$select": {"host.$id": \"' + hostId + '\"},"$limit": 1,"$sort": {"sortkey": "timestamp","direction": -1}}';
                    var uri = sfcsmCtrlURL+fsid+"/cpustat";
                    $http({method: "post", data: data, url: uri }).
                    success(function (data, status) {
                        $scope.cpuStatusDetail =  data[0];
                        $scope.status = status;
                    }).
                    error(function (data, status) {
                        $scope.status = status;
                        $scope.hosts =  data || "Request failed";
                        $dialogs.error("<h3>Can't display hosts with id " + hostId + "</h3><br>"+$scope.HardwareData);
                    });
                }

                function ToSwapStatus(fsid, hostId) {
                    var data = '{"$select": {"host.$id": \"' + hostId + '\"},"$limit": 1,"$sort": {"sortkey": "timestamp","direction": -1}}';
                    var uri = sfcsmCtrlURL+fsid+"/swapstat";
                    $http({method: "post", data: data, url: uri }).
                    success(function (data, status) {
                        $scope.swapStatusDetail =  data[0];
                        $scope.status = status;
                    }).
                    error(function (data, status) {
                        $scope.status = status;
                        $scope.hosts =  data || "Request failed";
                        $dialogs.error("<h3>Can't display hosts with id " + hostId + "</h3><br>"+$scope.HardwareData);
                    });
                }

                function ToMemStatus(fsid, hostid) {
                    var data = '{"$select": {"host.$id": \"'+hostid+'\"},"$limit": 1,"$sort": {"sortkey": "timestamp","direction": -1}}';
                    var uri = sfcsmCtrlURL+fsid+"/memstat";
                    $http({method: "post", data: data, url: uri }).
                    success(function (data, status) {
                        $scope.memStatusDetail =  data[0];
                        $scope.status = status;
                    }).
                    error(function (data, status) {
                        $scope.status = status;
                        $scope.hosts =  data || "Request failed";
                        $dialogs.error("<h3>Can't display hosts with id "+hostid+"</h3><br>"+$scope.HardwareData);
                    });
                }

                $scope.hw_Detail = function($event, obj){
                    var data = '{"$select": {"_id": \"'+obj._id+'\"}}';
                    var uri = sfcsmCtrlURL+$rootScope.fsid+"/partitions?depth=1";
                    $http({method: "post", data: data, url: uri }).
                    success(function (data, status) {
                        $(".hw_Detail_data").remove();
                        var html = '<tr class="hw_Detail_data"><td title="total">' + funcBytes(data[0].stat.total)
                                 + '</td><td title="free">' + funcBytes(data[0].stat.free)
                                 + '</td><td title="used">' + funcBytes(data[0].stat.used) + '</td></tr>';
                        $(".hw_th").append('<tr class="hw_Detail_data"><td>total</td><td>free</td><td>used</td></tr>');
                        $($event.currentTarget).append(html);
                    }).
                    error(function (data, status, headers) {
                        $scope.status = status;
                        $scope.hosts =  data || "Request failed";
                        $dialogs.error("<h3>Can't display hosts with id "+$stateParams.hostId+"</h3><br>"+$scope.data);
                    });
                };
            }
            /******硬件详情 enb********/
        }
        /********************************hardware end******************************************/

        /********************************clulog start******************************************/
        {
            //ClulogList();
            //function ClulogList() {
                //monitor data
            //    $http.get(clulogListCtrlURL).success(function (data) {
            //        $scope.ClulogData = data;
            //    });
            //}
        }
        /********************************clulog end******************************************/

        /********************************syslog start******************************************/
        {
            SyslogList();
            function SyslogList() {
                //monitor data
                $http.get(syslogListCtrlURL).success(function (data) {
                    $scope.SyslogData = data;
                });
            }
            $scope.detailSysOperation = function(model, obj){
                $('#' + model).modal('show');
                $scope.SystemLogInfo = obj.info;
            };
        }
        /********************************syslog start******************************************/
    }
    //StorageService
    {
        /********************************usermanage start******************************************/
        {
            UsermanageList();
            function UsermanageList() {
                var data = '{"$sort": {"sortkey": "user_id","direction": 1}}';
                $http({method: "get", data: data, url: usermanageListCtrlURL }).
                success(function (data, status) {
                    $scope.UsermanageData = data;
                }).
                error(function (data, status, headers) {
                    $scope.UsermanageData = '{"result":null}';
                });
                $("#myModalUserManage").modal('hide');
            }

            $scope.showUserDetail = function(obj,event){
                $(".users").removeClass('click_style_1');
                $(event.target).addClass('click_style_1');
                $("#myModalUserManage").modal('hide');
                $scope.uid = obj.uid;
                $scope.UserDetailModel = obj;
                $scope.UserDetailEvent = event;
                $http.get(usermanageDetailCtrlURL + obj.uid).success(function (data) {
                    $(".user_detail").show();
                    $(".udo").hide();
                    $scope.UsermanageDetail = data;

                    if(!isNullOrEmpty(data)) {
                        $scope.UsermanageDetail_suspended = data.suspended == '1' ? 'true' : 'false';

                        if (!isNullOrEmpty(data.bucket_quota)) {
                            var html = '';
                            $.each(data.bucket_quota, function (key, value) {
                                html += '<tr><td>' + key + '</td><td>' + value + '</td></tr>';
                            });
                            $scope.UsermanageDetail_bucket_quota = html;
                        }

                        if (!isNullOrEmpty(data.user_quota)) {
                            var html = '';
                            $.each(data.user_quota, function (key, value) {
                                html += '<tr><td>' + key + '</td><td>' + value + '</td></tr>';
                            });
                            $scope.UsermanageDetail_user_quota = html;
                        }

                        if (!isNullOrEmpty(data.qos)) {
                            var html = '';
                            $.each(data.qos, function (key, value) {
                                html += '<tr><td>' + key + '</td><td>' + value + '</td></tr>';
                            });
                            $scope.UsermanageDetail_qos = html;
                        }
                    }
                });
            };
            //s3 key
            {
                $scope.createKey = function () {
                    var models = $(".s3Keys_model");
                    var isSubmit = true;
                    var _data = '';
                    $.each(models, function () {
                        var id = $(this).attr('id');
                        var value = $(this).val();
                        if (!isNullOrEmpty(value))
                            _data += '"' + id + '":"' + value + '",';
                        else
                            isSubmit = false;
                    });
                    if (isSubmit) {
                        _data = 'json={' + _data.substring(0, _data.length - 1) + '}';
                        $scope.uri = sfcsmCtrlURL + "S3/user/" + $scope.uid;
                        $http({
                            method: "put",
                            url: $scope.uri,
                            data: _data,
                            headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                        }).success(function (data, status) {
                            CephAlert('create key success');
                            $scope.showUserDetail($scope.UserDetailModel, $scope.UserDetailEvent);
                        }).error(function (data, status) {
                            CephAlert('create key exception');
                        });
                    }
                }
                $scope.removeKey = function (key) {
                    $scope.uri = sfcsmCtrlURL + "S3/user/" + encodeURIComponent($scope.uid) + "/key/" + encodeURIComponent(key);
                    if (confirm("确认删除" + key + "吗")) {
                        $http({method: "delete", url: $scope.uri}).success(function (data, status) {
                            CephAlert('delete key success');
                            $scope.showUserDetail($scope.UserDetailModel, $scope.UserDetailEvent);
                        }).error(function (data, status) {
                            CephAlert('delete key exception');
                        });
                    }
                    ;
                }
            }
            //subuser
            {
                $scope.createSubuser = function () {
                    $scope.uri = sfcsmCtrlURL+"S3/user/"+$scope.uid+"/subuser";
                    var _data = '{"uid":"' + $scope.uid + '","access":"' + $("#permission").val()
                                + '","generate_key":"' + $("#generate_swift_key").is(':checked')
                                + '","subuser":"' + $("#subuser_id").val()
                                + '","secret_key":"' + $("#swift_key").val() + '"}';
                    $http({method: "put", url: $scope.uri, data: "json="+_data, headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).
                    success(function (data, status) {
                        CephAlert('create subuser success');
                        $scope.showUserDetail($scope.UserDetailModel, $scope.UserDetailEvent);
                    }).
                    error(function (data, status) {
                        CephAlert('create subuser exception');
                    });
                };
                $scope.showSwiftkey = function(obj){
                    $scope.subuserModel = obj;
                    $(".udo").hide();
                    $(".userDetail_subusers_swiftkey").show();
                    $("#generate_swift_key_create").prop('checked','checked');
                    $("#uds_swift_key").prop('disabled', 'disabled').val('');
                }
                $scope.createSwiftKey = function () {
                    $scope.uri = sfcsmCtrlURL+"S3/user/"+$scope.uid+"/subuser/"+$scope.subuserModel.id+"/key";
                    var data = "";
                    if ($("#generate_swift_key_create").is(':checked')) {
                        data = 'generate_key=True&secret_key=';
                    }else {
                        data = 'generate_key=False&secret_key='+$("#uds_swift_key").val();
                    }
                    $http({method: "put", url: $scope.uri, data: data, headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).
                    success(function (data, status) {
                        CephAlert('create swift key exception');
                        $scope.showUserDetail($scope.UserDetailModel, $scope.UserDetailEvent);
                    }).
                    error(function (data, status) {
                        CephAlert('create swift key exception');
                    });
                };
                $scope.removeSubuser = function(obj){
                    $scope.uri = sfcsmCtrlURL+"S3/user/"+$scope.uid+"/subuser/"+encodeURIComponent(obj);
                    if (confirm("确认删除吗")) {
                        $http({method: "delete", url: $scope.uri }).
                        success(function (data, status) {
                            CephAlert('delete sub user success');
                            $scope.showUserDetail($scope.UserDetailModel, $scope.UserDetailEvent);
                        }).
                        error(function (data, status) {
                            CephAlert('delete sub user exception');
                        });
                    };
                }
                $scope.removeSwiftKey = function(subuser, key){
                    $scope.uri = sfcsmCtrlURL+"S3/user/"+$scope.uid+"/subuser/"+encodeURIComponent(subuser)+"/key";
                    if (confirm("确认删除" + key + "吗")) {
                        $http({method: "delete", url: $scope.uri }).
                        success(function (data, status) {
                            CephAlert('delete swift key success');
                            $scope.showUserDetail($scope.UserDetailModel, $scope.UserDetailEvent);
                        }).
                        error(function (data, status) {
                            CephAlert('delete swift key exception');
                        });
                    };
                }
            }
            //caps
            {
                $scope.deleteCapability = function (type, perm) {
                    if (confirm("确认删除" + perm + "吗")) {
                        $scope.uri = sfcsmCtrlURL + "S3/user/" + $scope.uid + "/caps";
                        $http({
                            method: "delete",
                            url: $scope.uri,
                            data: "type=" + type + "&perm=" + perm,
                            headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                        }).success(function (data, status) {
                            CephAlert('delete capability success');
                            $scope.showUserDetail($scope.UserDetailModel, $scope.UserDetailEvent);
                        }).error(function (data, status) {
                            CephAlert('delete capability exception');
                        });
                    }
                }
            }
            //usermanage
            {
                $scope.showUserManage = function(){
                    $(".udo").hide();
                    $(".userDetail_modify").show();
                    var models = $(".udm_model");
                    var data = $scope.UsermanageDetail;
                    $.each(models, function(){
                        var $model = $(this);
                        var id = $(this).attr('id');
                        $.each(data, function(key, value){
                            if(id == key && (id == 'suspended')){
                                if(value == '1')
                                    $("#suspended").prop("checked", true);
                                else
                                    $("#suspended").prop("checked", false);
                            }else {
                                if (id == key || (id == 'uid' && key == 'user_id'))
                                    $model.val(value);
                            }
                        });
                    });
                    //判断是否为空
                    var isNotNullOrEmpty = true;
                    $.each(models, function(){
                        var value = $(this).val();
                        if(isNullOrEmpty(value))
                            isNotNullOrEmpty = false;
                    });
                    var display_name = $("#display_name").val();
                    var email = $("#email").val();
                    if(!isNotNullOrEmpty || (!isNullOrEmpty(display_name) && !isNullOrEmpty(email)))
                        $(".udm_model_modify,.udm_model_reset").prop('disabled', 'disabled');
                    else
                        $(".udm_model_modify,.udm_model_reset").prop('disabled', false);

                }
                $scope.modifyUserManage = function () {
                    var data_info = '"display_name":"' + $("#display_name").val()
                                    + '","email":"' + $("#email").val()
                                    + '","max_buckets":"' + $("#max_buckets").val()
                                    + '","suspended":"' + $("#suspended").is(":checked")
                                    + '","user_id":"' + $scope.UsermanageDetail.user_id + '"';
                    var caps = JSON.stringify($scope.UsermanageDetail.caps);
                    var _data = '{' + data_info + (',"caps":' + caps) + '}';
                    _data = eval('(' + _data + ')');
                    $http({method: "put", url: usermanageDetailCtrlURL + $scope.UsermanageDetail.user_id, data: "json="+JSON.stringify(_data), headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).
                    success(function (data, status) {
                        CephAlert('user modification success');
                        $scope.showUserDetail($scope.UserDetailModel, $scope.UserDetailEvent);
                    }).
                    error(function (data, status) {
                        CephAlert('user modification exception');
                    });
                };
            }
            //quota qos
            {
                $scope.modifyQuota = function(model, quota_type){
                    var _data = '';
                    $.each($("." + model), function(){
                        var id = $(this).attr('id').replace('bucket_','').replace('user_quota_', '');
                        var value = $(this).val();
                        if(isNullOrEmpty(value))
                            value = '-1';
                        _data += '"' + id + '":"' + value + '",';
                    });
                    if(!isNullOrEmpty(_data)){
                        _data = '{' + _data + '"enabled":"' + $("." + model + '_enable').is(':checked') + '","quota_type":"' + quota_type + '"}';
                        _data = eval('(' + _data + ')');

                        $http({
                            method: 'POST',
                            url: sfcsmCtrlDomain + sfcsmCtrlURL + 'S3/user/' + $scope.UsermanageDetail.user_id + '/quota',
                            data: "json=" + JSON.stringify(_data),
                            headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                        }).success(function (data, status) {
                            CephAlert('modify ' + model + ' success');
                            $scope.showUserDetail($scope.UserDetailModel, $scope.UserDetailEvent);
                        }).error(function (data, status) {
                            CephAlert('modify ' + model + ' exception');
                        });
                    }
                };
                $scope.modifyQos = function(){
                    var _data = '';
                    $.each($(".qos_model"), function(){
                        var id = $(this).attr('id').replace('qos_','');
                        var value = $(this).val();
                        if(isNullOrEmpty(value))
                            value = '-1';
                        _data += '"' + id + '":"' + value + '",';
                    });
                    if(!isNullOrEmpty(_data)){
                        _data = '{' + _data + '"enabled":"true"}';
                        _data = eval('(' + _data + ')');

                        $http({
                            method: 'POST',
                            url: sfcsmCtrlDomain + sfcsmCtrlURL + 'S3/user/' + $scope.UsermanageDetail.user_id + '/qos',
                            data: "json=" + JSON.stringify(_data),
                            headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                        }).success(function (data, status) {
                            CephAlert('modify qos success');
                            $scope.showUserDetail($scope.UserDetailModel, $scope.UserDetailEvent);
                        }).error(function (data, status) {
                            CephAlert('modify qos exception');
                        });
                    }
                };
            }
            //add user
            {
                $scope.addUserManage = function () {
                    $scope.uri = sfcsmCtrlURL+"S3/user";
                    var _data = '';
                    var isCreateSwiftSubuser = $("#add_create_swift_subuser").is(":checked");
                    var isSubuserGenerateKey = $("#add_subuser_generate_key").is(":checked");
                    var isadd_generate_key = $("#add_generate_key").is(":checked");

                    $.each($(".add_model"), function(){
                        var $model = $(this);
                        var id = $model.attr('id').replace('add_', '');
                        var value = $model.val();
                        if($model.attr('type') == 'checkbox')
                            value = $model.is(':checked');

                        if(isadd_generate_key){
                            if(id == 'access_key' || id == 'secret_key')
                                value = '';
                        }
                        if(isSubuserGenerateKey){
                            if(id == 'subuser_generate_key' || id == 'subuser_secret_key')
                                value = '';
                        }
                        if(!isCreateSwiftSubuser){
                            if(id == 'create_swift_subuser'
                                || id == 'subuser' || id == 'subuser_access'
                                || id == 'subuser_generate_key' || id == 'subuser_secret_key')
                                value = '';
                        }

                        if(!isNullOrEmpty(value))
                            _data += '"' + id + '":"' + value + '",';
                    });
                    if(!isNullOrEmpty(_data)) {
                        _data = '{' + _data.substring(0, _data.length - 1) + '}';
                        _data = eval('(' + _data + ')');
                        $http({
                            method: "post",
                            url: $scope.uri,
                            data: "json=" + JSON.stringify(_data),
                            headers: {'Content-Type': 'application/x-www-form-urlencoded'}
                        }).success(function (data, status) {
                            CephAlert('add user success');
                            UsermanageList();
                            $(".userDetail_add").hide();
                        }).error(function (data, status) {
                            CephAlert('add user exception');
                        });
                    }
                };
                $scope.userDelete = function () {
                    if (confirm("确认删除" + $scope.UsermanageDetail.user_id + "吗")) {
                        $scope.uri = sfcsmCtrlURL + "S3/user/" + $scope.UsermanageDetail.user_id;
                        $http({method: "delete", url: $scope.uri}).success(function (data, status) {
                            CephAlert('delete user success');
                            UsermanageList();
                        }).error(function (data, status) {
                            $(".btn").removeAttr('disabled');
                            CephAlert('delete user exception');
                        });
                    }
                }
            }
        }
        /********************************usermanage end******************************************/

        /********************************bucketmanage start******************************************/
        {
            BucketmanageList();
            function BucketmanageList() {
                $http({method: "get", url: bucketmanageListCtrlURL, data:"stats=False"}).
                success(function (data, status) {
                    $scope.BucketmanageData = data;
                }).
                error(function (data, status, headers) {
                    $scope.BucketmanageData = '{"result":"null"}';
                });
            }
            $scope.showbucketDetail = function(bucket){
                $(".bucket_detail").show();
                $(".udo").hide();
                var uri = bucketmanageDetailCtrlURL+bucket;
                $http({method: "get", url: uri }).
                success(function (data, status) {
                    $scope.detailedBucket = data;
                }).
                error(function (data, status, headers) {
                    $scope.detailedBucket = '{"result":"null"}';
                });
            }
            $scope.createBucket = function(){
                var _data ="bucket=" + $("#bucket_name").val() + "&owner=" + $("#bucket_owner").val();
                $http({method: "PUT", url: bucketmanageListCtrlURL, data: _data, headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).
                success(function (data, status) {
                    $(".udo").hide();
                    CephAlert('create bucket success');
                    BucketmanageList();
                }).
                error(function (data, status) {
                    CephAlert('create bucket exception');
                });
            }
            $scope.deleteBucket = function(obj) {
                if (confirm("确认删除" + obj + "吗")) {
                    $http({method: "delete", url: bucketmanageDetailCtrlURL + obj}).success(function (data, status) {
                        $(".udo").hide();
                        CephAlert('delete bucket success');
                        BucketmanageList();
                    }).error(function (data, status) {
                        CephAlert('delete bucket exception');
                    });
                }
            }
        }
        /********************************bucketmanage end******************************************/
    }
    //StateAnalysis
    {
        /********************************capacity start******************************************/
        {
            CapacityList();
            function CapacityList() {
                //monitor data
                $http.get(capacityListCtrlURL).success(function (data) {
                    $scope.CapacityData = data;
                });
            }
        }
        /********************************capacity end******************************************/

        /********************************qualities start******************************************/
        {
            QualitiesList();
            function QualitiesList() {
                //monitor data
                $http.get(qualitiesListCtrlURL).success(function (data) {
                    $scope.QualitiesData = data;
                });
            }
        }
        /********************************qualities end******************************************/
    }
    /********************************operationlog start******************************************/
    {
        function OperationlogList($rootScope) {
            //monitor data
            var _data = '{"$limit": 50,"$sort": {"sortkey": "operateTime","direction": -1}}';
            $http({method: "post", url: sfcsmCtrlDomain + sfcsmCtrlURL + '/' + $rootScope.fsid + '/operationlog', data: _data}).success(function (data, status) {
                $scope.OperationlogList = data;
            }).error(function (data, status) {
                CephAlert('select log exception');
            });
        }
    }
    /********************************operationlog end******************************************/
    /********************************reglog end******************************************/
    {
        RegLog();
        function RegLog() {
            $http({method: "get", url: sfcsmCtrlURL + "sfcsm_user"}).success(function (data, status) {
                $scope.userList = data;
            }).error(function (data, status) {
                $scope.userList = '{"result":"null"}';
            });
        }

        $scope.addUser = function(){
            $(".udo,.user_detail").hide();
            $(".userDetail_add").show();
            $http({method: "get", url: sfcsmCtrlURL + "sfcsm_user_role"}).
            success(function (data) {
                $scope.sfcsmRoles =  data;
            }).
            error(function (data, status) {
                $scope.sfcsmRoles =  data;
            });
        }

        $scope.showRegLogUserDetail = function(){
            var model = $scope.detaileduser;
            $(".udo,.user_detail,.isnewpwd").hide();
            $(".userDetail_modify").show();
            $(".user_model_m").val('');
            $(".user_model_m_cb,.change_password").prop('checked', false);
            $("#user_m_name").val(model.name);
            $("#user_m_email").val(model.email);
            if(model.roles.length > 0 && jQuery.isArray(model.roles)) {
                for (var i = 0; i < model.roles.length; i++) {
                    $("#role_m_" + model.roles).prop('checked', true);
                }
            }else{
                $("#role_m_" + model.roles).prop('checked', true);
            }
        }

        $scope.showUserDetail = function(model){
            $(".user_detail").show();
            $(".udo").hide();
            $(".user_model").val('');
            //重构model.roles
            if(model.roles.length > 0 && jQuery.isArray(model.roles)) {
                var newModel = JSON.stringify(model);
                newModel = newModel.substring(1, newModel.length - 1);
                var roles = '';
                for (var i = 0; i < model.roles.length; i++) {
                    roles += model.roles + ','
                }
                if(!isNullOrEmpty(roles)){
                    roles = '{' + newModel + ',"roles":"' + roles.substring(0, roles.length - 1) + '"' + '}';
                    model = eval('(' + roles + ')');
                }
            }
            $scope.UserModel = model;
            $scope.detaileduser = model;

            $http({method: "get", url: sfcsmCtrlURL + "sfcsm_user_role"}).
            success(function (data) {
                $scope.sfcsmRoles =  data;
            }).
            error(function (data, status) {
                $scope.sfcsmRoles =  data;
            });
        }

        $scope.userDelete_user = function () {
            $http({method: "delete", url: sfcsmCtrlURL + "sfcsm_user/" + $scope.detaileduser.name }).
            success(function (data, status) {
                CephAlert('delete user success');
                RegLog();
                $(".user_detail").hide();
            }).
            error(function (data, status) {
                CephAlert('delete user exception');
            });
        }

        $scope.userCreate_user = function () {

            var _data = '';
            $.each($(".user_model"), function(){
                var $model = $(this);
                var id = $model.attr('id').replace('user_', '');
                var value = $model.val();
                if(!isNullOrEmpty(value))
                    _data += '"' + id + '":"' + value + '",';
            });
            _data += '"roles":[';
            var roles = '';
            $.each($(".user_model_cb"), function(){
                if($(this).is(':checked'))
                    roles += '"' + $(this).attr('id').replace('role_', '') + '",';
            });
            if(!isNullOrEmpty(roles))
                roles = roles.substring(0, roles.length - 1);
            _data += roles + ']';

            _data = eval('({' + _data + '})');

            $http({method: "post", url: sfcsmCtrlURL+ "sfcsm_user/"+$("#user_name").val(), data: JSON.stringify(_data), headers: {'Content-Type': 'application/json'}}).
            success(function (data, status) {
                CephAlert('add user success');
                RegLog();
                $(".userDetail_add").hide();
            }).
            error(function (data, status) {
                CephAlert('add user exception');
            });
        };

        $scope.userModify_user = function () {
            var _data = '';
            $.each($(".user_model_m"), function(){
                var $model = $(this);
                var id = $model.attr('id').replace('user_m_', '');
                var value = $model.val();
                if(!isNullOrEmpty(value))
                    _data += '"' + id + '":"' + value + '",';
            });
            _data += '"roles":[';
            var roles = '';
            $.each($(".user_model_m_cb"), function(){
                if($(this).is(':checked'))
                    roles += '"' + $(this).attr('id').replace('role_m_', '') + '",';
            });
            if(!isNullOrEmpty(roles))
                roles = roles.substring(0, roles.length - 1);
            _data += roles + ']';

            _data = eval('({' + _data + '})');

            $http({method: "put", url: sfcsmCtrlURL+ "sfcsm_user/"+$("#user_m_name").val(), data: JSON.stringify(_data), headers: {'Content-Type': 'application/json'}}).
            success(function (data, status) {
                CephAlert('modify user success');
                RegLog();
                $(".userDetail_modify").hide();
            }).
            error(function (data, status) {
                CephAlert('modify user exception');
            });
        };
    }
    /********************************reglog end******************************************/
})
    //绑定echartjs(首页)
    .directive('barCharts', ['$http',function ($http) {
        return {
            restrict: 'AE',
            scope: {source: '='},
            template: 'This is barCharts',
            controller: function ($scope) {},
            link: function (scope, element, attr) {
                if(scope.source == undefined) {
                    $http({method: "get", url: indexCtrlURL, timeout: 4000})
                        .success(function (data) {
                            Charts(data.output,scope, element, attr);
                        })
                        .error(function (data) {
                            $scope.health = {};
                            $scope.health.severity = "HEALTH_WARN";
                            $scope.health.summary = "Status not available";
                        });
                }else {
                    Charts(scope.source,scope, element, attr);
                }
            }
        };
        function Charts(itemData,scope, element, attr){
            //byte转TB
            var convertTB = function (data) {
                return (((data / 1024) / 1024));    //轩数据问题，暂转为MB，后生产数据大时再另外转
            };
            //个位时间前加0
            var timeFormat = function (hms) {
                var result;
                if(hms<10){
                    result = "0" + hms;
                }else{
                    result = hms;
                }
                return result;
            }
            //console.log(element);
            var chart = element[0];
            var id = attr['id'];

            if (id == 'StorageInfo1') {
                {
                    var res = itemData.pgmap;
                    var total = res.bytes_total;    //总空间
                    var used = res.bytes_used;      //已使用空间
                    var avail = res.bytes_avail;    //未用空间
                    var pgNum = res.num_pgs;        //pg总数
                    var readBPS = res.read_bytes_sec;   //读BPS
                    var WriteBPS = res.write_bytes_sec; //写BPS
                    var iops = res.op_per_sec;      //IOPS

                    //var parent = element['context'];
                    chart.style.width = '200px';
                    chart.style.height = '200px';
                    var myChart = echarts.init(chart);
                    var option = {
                        title: {
                            text: '',
                            x: 'center'
                        },
                        tooltip: {
                            trigger: 'item',
                            formatter: "{a} <br/>{b} : {c} ({d}%)",
                            position: {x: 0, y: 0}
                        },
                        legend: {
                            orient: 'vertical',
                            left: 'left',
                            data: ['已使用', '未用']
                        },
                        series: [
                            {
                                name: 'PG',
                                type: 'pie',
                                // radius: '55%',
                                radius: ['50%', '70%'],
                                // center: ['50%', '60%'],
                                avoidLabelOverlap: false,

                                data: [
                                    {value: convertTB(used).toFixed(2), name: '已使用'},
                                    {value: convertTB(avail).toFixed(2), name: '未用'}
                                ],
                                itemStyle: {
                                    normal: {
                                        label: {show: false},
                                        labelLine: {show: false}
                                    },
                                    emphasis: {
                                        shadowBlur: 10,
                                        shadowOffsetX: 0,
                                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                                    }
                                }
                            }
                        ]
                    };

                    myChart.setOption(option);
                    myChart.resize();
                }
            } else if (id == 'HealthInfo') {
                {
                    var res = itemData.health.health.health_services[0].mons[0];
                    var avail_percent = res.avail_percent;
                    var health = res.health;
                    var kb_avail = res.kb_avail;
                    var kb_total = res.kb_total;
                    var kb_used = res.kb_used;
                    var name = res.name;
                    var bytes_misc = res.store_stats.bytes_misc;
                    var bytes_sst = res.store_stats.bytes_sst;
                    var bytes_total = res.store_stats.bytes_total;

                    chart.style.width = '200px';
                    chart.style.height = '200px';
                    var myChart = echarts.init(chart);

                    var option = {
                        tooltip: {
                            trigger: 'item',
                            formatter: "{a} <br/>{b}: {c} ({d}%)",
                            position: {x: 0, y: 0}
                        },
                        legend: {
                            orient: 'vertical',
                            x: 'left',
                            data: ['Avail', 'Used']
                        },
                        normal: {
                            label: {}
                        },
                        series: [
                            {
                                name: name,
                                type: 'pie',
                                radius: ['50%', '70%'],
                                avoidLabelOverlap: false,
                                label: {
                                    normal: {
                                        show: false,
                                        position: 'center'
                                    },
                                    emphasis: {
                                        show: true,
                                        textStyle: {
                                            fontSize: '15',
                                            fontWeight: 'bold'
                                        }
                                    }
                                },
                                labelLine: {
                                    normal: {
                                        show: false
                                    }
                                },
                                data: [
                                    {value: funcBytes(kb_avail * 1021), name: 'Avail'},
                                    {value: funcBytes(kb_used * 1021), name: 'Used'}
                                ]
                            }
                        ]
                    };

                    myChart.setOption(option);
                    myChart.resize();
                }
            }else if (id == 'ClusterDataStatusRecovery') {
                {
                    var pgmap = itemData.pgmap;
                    var object_total = 0;
                    var misplaced_objects = 0;
                    var degraded_objects = 0;
                    if ("degraded_total" in pgmap){
                        var object_total = pgmap.degraded_total;
                    }
                    if ("misplaced_total" in pgmap){
                        var object_total = pgmap.misplaced_total;
                    }
                    if ("misplaced_objects" in pgmap){
                        misplaced_objects = pgmap.misplaced_objects;
                    }
                    if ("degraded_objects" in pgmap){
                        degraded_objects = pgmap.degraded_objects;
                    }
                    var normal_objects = object_total - misplaced_objects - degraded_objects;
                    var myChart = echarts.init(chart);
                    var option = {
                        title: {
                            text: '',
                            x: 'center'
                        },
                        tooltip: {
                            trigger: 'item',
                            formatter: "{a} <br/>{b} : {c} ({d}%)",
                            position: {x: 0, y: 0}
                        },
                        legend: {
                            orient: 'vertical',
                            left: 'left',
                            data: ['Normal Objects', 'Degraded Objects','Misplaced Objects']
                        },
                        series: [
                            {
                                name: 'Recovery Status',
                                type: 'pie',
                                radius: ['50%', '70%'],
                                center: ['50%', '60%'],
                                data: [
                                    {value: normal_objects, name: 'Normal Objects', itemStyle:{normal:{color:'#0099CC'}}},
                                    {value: degraded_objects, name: 'Degraded Objects', itemStyle:{normal:{color:'#FBB450'}}},
                                    {value: misplaced_objects, name: 'Misplaced Objects', itemStyle:{normal:{color:'#EE5F5B'}}}
                                ],
                                itemStyle: {
                                    normal: {
                                        label: {show: false},
                                        labelLine: {show: false}
                                    },
                                    emphasis: {
                                        shadowBlur: 10,
                                        shadowOffsetX: 0,
                                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                                    }
                                }
                            }
                        ]
                    };

                    myChart.setOption(option);
                    myChart.resize();
                }
            }else if (id == 'ClusterDataStatus') {
                {
                    var pgmap = itemData.pgmap;
                    var bytes_used =pgmap.bytes_used;
                    var myChart = echarts.init(chart);
                    var option = {
                        title: {
                            text: '',
                            x: 'center'
                        },
                        tooltip: {
                            trigger: 'item',
                            formatter: "{a} <br/>{b} : {c} ({d}%)",
                            position: {x: 0, y: 0}
                        },
                        legend: {
                            orient: 'vertical',
                            left: 'left',
                            data: ['总数据']
                        },
                        series: [
                            {
                                name: 'Cluster Data',
                                type: 'pie',
                                radius: ['50%', '70%'],
                                center: ['50%', '60%'],
                                data: [
                                    {value: bytes_used, name: '总数据'}
                                ],
                                itemStyle: {
                                    normal: {
                                        label: {show: false},
                                        labelLine: {show: false},
                                        color: '#0099CC'
                                    },

                                    emphasis: {
                                        shadowBlur: 10,
                                        shadowOffsetX: 0,
                                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                                    }
                                }
                            }
                        ]
                    };
                    myChart.setOption(option);
                    myChart.resize();
                }
            }else if (id == 'PGInfo1') {
                {
                    chart.style.width = '200px';
                    chart.style.height = '200px';
                    var myChart = echarts.init(chart);

                    var res = itemData.pgmap;
                    var _data = [];
                    var _dataName = [];
                    var _otherCount = 0;
                    for (var i = 0; i < res.pgs_by_state.length; i++) {
                        if (i < 5) {
                            _dataName.push(res.pgs_by_state[i]['state_name']);
                            _data.push({
                                value: res.pgs_by_state[i]['count'],
                                name: res.pgs_by_state[i]['state_name'],
                                itemStyle: {normal: {color: defaultColors[i]}}
                            });
                        } else if (i >= 5) {
                            _otherCount = _otherCount + res.pgs_by_state[i]['count'];
                        }
                    }
                    if (_otherCount > 0) {
                        _dataName.push('其它');
                        _data.push({value: _otherCount, name: '其它', itemStyle: {normal: {color: defaultColors[5]}}});
                    }

                    var option = {
                        title: {
                            text: '',
                            x: 'center'
                        },
                        tooltip: {
                            trigger: 'item',
                            formatter: "{a} <br/>{b} : {c} ({d}%)",
                            position: {x: 0, y: 0}
                        },
                        legend: {
                            orient: 'vertical',
                            left: 'left',
                            data: _dataName
                        },
                        series: [
                            {
                                name: 'Pool',
                                type: 'pie',
                                radius: '55%',
                                center: ['50%', '60%'],
                                data: _data,
                                itemStyle: {
                                    normal: {
                                        label: {show: false},
                                        labelLine: {show: false}
                                    },
                                    emphasis: {
                                        shadowBlur: 10,
                                        shadowOffsetX: 0,
                                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                                    }
                                }
                            }
                        ]
                    };
                    myChart.setOption(option);
                    myChart.resize();
                }
            }else if (id == 'PoolInfo') {
                {
                    chart.style.width = '200px';
                    chart.style.height = '200px';
                    var myChart = echarts.init(chart);

                    var poolData = IndexPoolData();
                    var poolName = [];
                    var _data = [];
                    for(var i = 0; i< poolData.pools.length; i++){
                        poolName.push(poolData.pools[i].name);
                        _data.push({value: poolData.pools[i].pg_num, name: poolData.pools[i].name});
                    }

                    var option = {
                        title: {
                            text: '',
                            x: 'center'
                        },
                        tooltip: {
                            trigger: 'item',
                            formatter: "{a} <br/>{b} : {c} ({d}%)",
                            position: {x: 0, y: 0}
                        },
                        legend: {
                            orient: 'vertical',
                            left: 'left',
                            data: poolName,
                            itemWidth:10,  //图例标记的图形宽度
                            itemHeight:10,
                        },
                        series: [
                            {
                                name: 'Pool',
                                type: 'pie',
                                radius: '55%',
                                center: ['50%', '60%'],
                                data: _data,
                                itemStyle: {
                                    normal: {
                                        label: {show: false},
                                        labelLine: {show: false}
                                    },
                                    emphasis: {
                                        shadowBlur: 10,
                                        shadowOffsetX: 0,
                                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                                    }
                                }
                            }
                        ]
                    };
                    myChart.setOption(option);
                    myChart.resize();
                }
            }else if(id == 'BPS'){
                {
                    // chart.style.width = '400px';
                    // chart.style.height = '200px';
                    var myChart = echarts.init(chart);
                    var data_read = [];
                    var data_write = [];
                    var timeDif = 0;
                    function refreshData(timeR) {
                        var now = new Date();
                        var endTp = now.getTime() - timeDif;
                        var startTp = endTp - timeR;
                        var req_parms = '{"$select":{"timestamp":{"$gt":' + startTp + ',"$lt":' + endTp + '}}}';
                        var resp_data = Ajax(resp_data, sfcsmCtrlDomain + sfcsmCtrlURL + itemData.fsid + '/clusterperf', req_parms, 'post')
                        // results = []
                        data_read.shift();
                        data_write.shift();
                        if(!isNullOrEmpty(resp_data) && resp_data.length > 0) {
                            for (var i = 0; i < resp_data.length; i++){
                                collectTmp = resp_data[i].timestamp;
                                collectTm = new Date(collectTmp);
                                if (!("read_bytes_sec" in resp_data[i]) && !("write_bytes_sec" in resp_data[i])){
                                    continue;
                                }
                                if (!("read_bytes_sec" in resp_data[i])) {
                                    resp_data[i].read_bytes_sec = 0;
                                }
                                if (!("write_bytes_sec" in resp_data[i])) {
                                    resp_data[i].write_bytes_sec = 0;
                                }
                                var years = collectTm.getFullYear();
                                var months = timeFormat(collectTm.getMonth() + 1);
                                var days = timeFormat(collectTm.getDate());
                                var hours = timeFormat(collectTm.getHours());
                                var minutes = timeFormat(collectTm.getMinutes());
                                var seconds = timeFormat(collectTm.getSeconds());
                                val =  [
                                    {
                                        name: collectTm,
                                        value: [
                                            [years, months, days].join('/') + ' ' + [hours, minutes, seconds].join(':')
                                            ,resp_data[i].read_bytes_sec
                                        ]},
                                    {
                                        name: collectTm,
                                        value: [
                                            [years, months, days].join('/') + ' ' + [hours, minutes, seconds].join(':')
                                            ,resp_data[i].write_bytes_sec
                                        ]}
                                ];
                                data_read.push(val[0]);
                                data_write.push(val[1]);
                            }
                        }else{
                            now = new Date(endTp);
                            var years = now.getFullYear();
                            var months = timeFormat(now.getMonth() + 1);
                            var days = timeFormat(now.getDate());
                            var hours = timeFormat(now.getHours());
                            var minutes = timeFormat(now.getMinutes());
                            var seconds = timeFormat(now.getSeconds());
                            val =  [
                                {
                                    name: now,
                                    value: [
                                        [years, months, days].join('/') + ' ' + [hours, minutes, seconds].join(':'),0]
                                },
                                {
                                    name: now,
                                    value: [
                                        [years, months, days].join('/') + ' ' + [hours, minutes, seconds].join(':'),0]
                                }
                            ];
                            data_read.push(val[0]);
                            data_write.push(val[1]);
                        }
                    }
                    var currTm = new Date($.ajax({async: false}).getResponseHeader("Date")) + (3600000 * 8);
                    var curTmp = new Date(currTm).getTime();
                    var nowlocalTmp = new Date().getTime();
                    timeDif = nowlocalTmp - curTmp;
                    refreshData(3600000);
                    var option = {
                        title: {
                            text: 'BPS',
                            x: 'left'
                        },
                        tooltip: {
                            trigger: 'axis'
                            // axisPointer: {
                            //     type: 'cross'
                            // },
                            // backgroundColor: 'rgba(245, 245, 245, 0.8)',
                            // borderWidth: 1,
                            // borderColor: '#ccc',
                            // padding: 10,
                            // textStyle: {
                            //     color: '#000'
                            // },
                            // position: function (pos, params, el, elRect, size) {
                            //     var obj = {top: 10};
                            //     obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
                            //     return obj;
                            // },
                            // extraCssText: 'width: 170px'
                        },
                        legend: {
                            data:['read','write'],
                            x: 'center'
                        },
                        toolbox: {
                            feature: {
                                dataZoom: {
                                    yAxisIndex: 'none'
                                },
                                restore:{},
                            }
                        },
                        dataZoom: [{
                            type: 'inside'
                        }],
                        xAxis : [
                            {
                                type : 'time',
                                boundaryGap : false,
                                axisLine: {onZero: true},
                            }
                        ],
                        yAxis : [
                            {
                                name : 'B/s',
                                type : 'value',
                                boundaryGap: [0, '100%'],
                                splitLine: {
                                    show: false
                                }
                            }
                        ],
                        series : [
                            {
                                name:'read',
                                type:'line',
                                symbolSize: false,
                                hoverAnimation: false,
                                data:data_read
                            },
                            {
                                name:'write',
                                type:'line',
                                symbolSize: false,
                                hoverAnimation: false,
                                data:data_write
                            }
                        ]
                    };
                    setInterval(function () {
                        refreshData(3000);
                        myChart.setOption(option);
                    }, 3000);
                    myChart.setOption(option);
                    myChart.resize();
                }
            }else if(id == 'OPS'){
                {
                    // chart.style.width = '400px';
                    // chart.style.height = '200px';
                    var myChart = echarts.init(chart);
                    var data = [];
                    var timeDif = 0;
                    function refreshData(timeR) {
                        var now = new Date();
                        var endTp = now.getTime() - timeDif;
                        var startTp = endTp - timeR;
                        var req_parms = '{"$select":{"timestamp":{"$gt":' + startTp + ',"$lt":' + endTp + '}}}';
                        var resp_data = Ajax(resp_data, sfcsmCtrlDomain + sfcsmCtrlURL + itemData.fsid + '/clusterperf', req_parms, 'post')
                        // results = []
                        data.shift();
                        if(!isNullOrEmpty(resp_data) && resp_data.length > 0) {
                            for (var i = 0; i < resp_data.length; i++){
                                collectTmp = resp_data[i].timestamp;
                                collectTm = new Date(collectTmp);
                                if (!("op_per_sec" in resp_data[i])) {
                                    continue;
                                    resp_data[i].op_per_sec = 0;
                                }
                                var years = collectTm.getFullYear();
                                var months = timeFormat(collectTm.getMonth() + 1);
                                var days = timeFormat(collectTm.getDate());
                                var hours = timeFormat(collectTm.getHours());
                                var minutes = timeFormat(collectTm.getMinutes());
                                var seconds = timeFormat(collectTm.getSeconds());
                                val =  {
                                        name: collectTm,
                                        value: [
                                            [years, months, days].join('/') + ' ' + [hours, minutes, seconds].join(':')
                                            ,resp_data[i].op_per_sec
                                        ]
                                };
                                data.push(val);
                            }
                        }else{
                            now = new Date(endTp);
                            var years = now.getFullYear();
                            var months = timeFormat(now.getMonth() + 1);
                            var days = timeFormat(now.getDate());
                            var hours = timeFormat(now.getHours());
                            var minutes = timeFormat(now.getMinutes());
                            var seconds = timeFormat(now.getSeconds());
                            val = {
                                    name: now,
                                    value: [
                                        [years, months, days].join('/') + ' ' + [hours, minutes, seconds].join(':'),0
                                    ]
                            };
                            data.push(val);
                        }
                    }
                    var currTm = new Date($.ajax({async: false}).getResponseHeader("Date")) + (3600000 * 8);
                    var curTmp = new Date(currTm).getTime();
                    var nowlocalTmp = new Date().getTime();
                    timeDif = nowlocalTmp - curTmp;
                    refreshData(3600000);
                    option = {
                        title: {
                            text: 'OPS'
                        },
                        tooltip: {
                            trigger: 'axis'
                            // axisPointer: {
                            //     type: 'cross'
                            // },
                            // backgroundColor: 'rgba(245, 245, 245, 0.8)',
                            // borderWidth: 1,
                            // borderColor: '#ccc',
                            // padding: 10,
                            // textStyle: {
                            //     color: '#000'
                            // },
                            // position: function (pos, params, el, elRect, size) {
                            //     var obj = {top: 10};
                            //     obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
                            //     return obj;
                            // },
                            // extraCssText: 'width: 170px'
                        },
                        xAxis: {
                            type: 'time',
                            splitLine: {
                                show: false
                            }
                        },
                        yAxis: {
                            name: 'operation/s',
                            type: 'value',
                            boundaryGap: [0, '100%'],
                            splitLine: {
                                show: false
                            }
                        },
                        toolbox: {
                            feature: {
                                dataZoom: {
                                    yAxisIndex: 'none'
                                },
                                restore:{},
                            }
                        },
                        dataZoom: [{
                            type: 'inside'
                            // start: 0,
                            // end: 100
                        }],
                        series: [
                            {
                                name: 'OPS',
                                type: 'line',
                                showSymbol: false,
                                hoverAnimation: false,
                                data: data
                            }
                        ]
                    };

                    setInterval(function () {
                        refreshData(3000);
                        myChart.setOption(option);
                    }, 3000);
                    myChart.setOption(option);
                    myChart.resize();
                }
            }
        }
    }]);

StatusApp.controller('ModalDemoCtrl', function ($scope, $modal, $log) {
    $scope.open = function (size) {

        var modalInstance = $modal.open({
            templateUrl: 'myModalContent.html',
            controller: 'ModalInstanceCtrl',
            size: size
        });

        modalInstance.result.then(function (selectedItem) {
            $scope.selected = selectedItem;
        }, function () {
            $log.info('Modal dismissed at: ' + new Date());
        });
    };
});

// Please note that $modalInstance represents a modal window (instance) dependency.
// It is not the same as the $modal service used above.

StatusApp.controller('ModalInstanceCtrl', function ($scope, $modalInstance, $http) {
    $scope.refresh = function () {
        $scope.details = ["fetching details ..."];
        $http({method: "get", url: cephRestApiURL + "health.json?detail",timeout:8000})
            .success(function (data, status) {
                $scope.details = data.output.detail;
                for (var i=0;i<$scope.details.length;i++){
                    var txt = $scope.details[i];
                    /(osd\.[0-9]+)/.exec(txt);
                    var osd = RegExp.$1;
                    if (osd != null) {
                        txt = txt.replace(osd, "<a href='osds.html?dispoMode=space&" + osd + "'>" + osd + "</a>");
                    }
                   /([0-9]+\.[0-9a-f]+)/.exec(txt);
                    var id = RegExp.$1;
                    if (id != null){
                        //$scope.details[i] = txt.replace(id,"<a href='pg.html?id="+id+"'>"+id+"</a>");
                        txt = txt.replace("pg "+id,"<a href='../ceph-rest-api/tell/"+id+"/query.json'>pg "+id+"</a>");
                        }
                     // ceph-rest-api/tell/<id>/query.json
                    $scope.details[i] = txt;

                }
            })
            .error(function (data, status) {
                $scope.details = ["details not available"];
            }
        );
    };
    $scope.refresh();

    $scope.close = function () {
        $modalInstance.dismiss('cancel');
    };
});

