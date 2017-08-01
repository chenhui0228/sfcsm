/**
 * Created by arid6405 on 2014/07/28.
 */

angular.module('hostsApp', ['ngRoute','ngTable','D3Directives','ui.bootstrap','dialogs','SfcsmCommons','ui.router'])
    .filter('bytes', funcBytesFilter)
    .config(function ($stateProvider,$urlRouterProvider) {
        $urlRouterProvider.otherwise('/','/aboutHosts');
        $stateProvider
            .state('aboutHosts',{
                url:'/aboutHosts',
                templateUrl:'partials/hosts/aboutHosts.html',
                controller: ListCtrl
            })
            .state('detailHost.cpuStatus',{
                url: '/cpuStatus/:hostId',
                templateUrl: 'partials/hosts/status/cpuStatus.html',
                controller: ToCpuStatus
            })
            .state('detailHost.swapStatus',{
                url: '/swapStatus/:hostId',
                templateUrl: 'partials/hosts/status/swapStatus.html',
                controller: ToSwapStatus
            })
            .state('detailHost.memStatus',{
                url: '/memStatus/:hostId',
                templateUrl: 'partials/hosts/status/memStatus.html',
                controller: ToMemStatus
            })
            .state('detailHost.nicStatus',{
                url: '/nicStatus/:nicid',
                templateUrl: 'partials/hosts/status/nicStatus.html',
                controller: ToNicStatus
            })
            .state('detailHost.diskStatus',{
                url: '/diskStatus/:diskid',
                templateUrl: 'partials/hosts/status/diskStatus.html',
                controller: ToDiskStatus
            })
            .state('detailHost.raidStatus',{
                url: '/raidStatus/:raidid',
                templateUrl: 'partials/hosts/status/raidStatus.html',
                controller: ToRaidStatus
            })
            .state('detailHost.partStatus',{
                url: '/partStatus/:partid',
                templateUrl: 'partials/hosts/status/partStatus.html',
                controller: ToPartStatus
            })
            .state('detailHost',{
                url: '/detailHost/:hostId',
                templateUrl: 'partials/hosts/detailHost.html',
                controller: DetailCtrl
            });

    })
    .directive('cpuDashboard',['$http',function($http) {
        return {
            restrict: 'AE',
            scope: {
                cpuDashboard: '=',
                hostId: '=',
                statusData: '=cpuStatusDetail'
            },
            //controller: CpuStatus,
            link: link,
        };

        function link(scope, element, attr) {

            var myChart = echarts.init(element[0]);
            scope.statusData = {};
            now = new Date();
            var startTime = getWeekStartDate(now);
            var endTime = now.getTime();
            var data = '{"$select": {"host.$id": \"'+scope.$parent.hostId+'\", "timestamp": {"$gt": '+startTime+',"$lt": '+endTime+'}},"$limit": 1,"$sort": {"sortkey": "timestamp","direction": -1}}';
            var uri = sfcsmCtrlURL+scope.$root.fsid+"/cpustat";
            $http({method: "post", data: data, url: uri }).
            success(function (data, status) {
                scope.statusData = data[0]
            }).
            error(function (data, status, headers) {
                scope.status = status;
                scope.hosts =  data || "Request failed";
                $dialogs.error("<h3>Can't display hosts with id "+$scope.$parent.hostId+"</h3><br>"+$scope.data);
            });

            // var resource = scope.cpuStatusDetail;
            // 指定图表的配置项和数据
            option = {
                tooltip : {
                    formatter: "{a} <br/>{b} : {c}%"
                },
                toolbox: {
                    show : true,
                    feature : {
                        mark : {show: true},
                        restore : {show: true},
                        saveAsImage : {show: true}
                    }
                },
                series : [
                    {
                        name:'业务指标',
                        type:'gauge',
                        detail : {formatter:'{value}%'},
                        data:[{value: scope.statusData.system, name: '完成率'}]
                    }
                ]
            };

            // clearInterval(timeTicket);
            // var timeTicket = setInterval(function (){
            //     option.series[0].data[0].value = (Math.random()*100).toFixed(2) - 0;
            //     myChart.setOption(option, true);
            // },2000);

            // 使用刚指定的配置项和数据显示图表。
            myChart.setOption(option, true);

            // 双向传值
            // scope.$watch('echart', function(n, o) {
            //  if (n === o || !n) return;
            //  myChart.setOption(n);
            // });

            //当浏览器窗口发生变化的时候调用div的resize方法
            window.addEventListener('resize', chartResize);

            scope.$on('$destory', function() {
                window.removeEventListener('resize', chartResize);
            })

            function chartResize() {
                myChart.resize();
            }
        }
    }]);

function refreshHosts($rootScope, $http, $scope, $templateCache) {
    //while (typeof $rootScope.fsid === 'undefined')  ;
    $http({method: "get", url: sfcsmCtrlURL + $rootScope.fsid + "/hosts", cache: $templateCache}).
        success(function (data, status) {
            $scope.date = new Date();
            $scope.status = status;
            $scope.hosts =  data;
            $scope.tableParams.reload();
        }).
        error(function (data, status, headers) {
            //alert("refresh hosts failed with status "+status);
            $scope.status = status;
            $scope.hosts =  data || "Request failed";
        });
}

function ListCtrl($rootScope, $scope,$http, $filter, ngTableParams, $location, $state) {
    $scope.tableParams = new ngTableParams({
        page: 1,            // show first page
        count: 20,          // count per page
        sorting: {
            _id: 'asc'     // initial sorting
        }
    }, {
        counts: [], // hide page counts control
        total: 1,  // value less than count hide pagination
        getData: function ($defer, params) {
            // use build-in angular filter
            $scope.orderedData = params.sorting() ?
                $filter('orderBy')($scope.hosts, params.orderBy()) :
                data;
            $defer.resolve($scope.orderedData.slice((params.page() - 1) * params.count(), params.page() * params.count()));
        }
    });

    // start refresh when fsid is available
    var waitForFsid = function ($rootScope, $http,$scope){
        typeof $rootScope.fsid !== "undefined"? startRefreshHost($rootScope, $http,$scope) : setTimeout(function () {waitForFsid($rootScope, $http,$scope)}, 1000);
        function startRefreshHost($rootScope, $http,$scope){
            /*$rootScope.fsid = "97e331ce-52a0-4292-9227-362c830ecfa3";*/
            refreshHosts($rootScope, $http,$scope);
            setInterval(function(){
                refreshHosts($rootScope,$http, $scope)
            }, 10000);
        }
    }
    waitForFsid($rootScope, $http,$scope);

    var data;

    $scope.showDetail = function (hostId) {
        //$location.path('/detailHost/'+hostid);
        $state.go('detailHost',{hostId:hostId});
    }


}

function DetailCtrl($rootScope, $scope, $http, $dialogs, $state, $stateParams) {
    $scope.detailedHost={};
    $scope.detailedHost._id = $stateParams.hostId;
    var data ={
        "_id" : $stateParams.hostId
        // "_id" : 'devstr-1'
    }
    var uri = sfcsmCtrlURL + $rootScope.fsid+"/hosts?depth=2";
    //测试用
    // var uri = sfcsmCtrlURL + "97e331ce-52a0-4292-9227-362c830ecfa3"+"/hosts?depth=2";
    $http({method: "post", data: data, url: uri }).
        success(function (data, status) {
            $scope.detailedHost =  data[0];
            $scope.status = status;
            DetailDataPrepare($scope);
        }).
        error(function (data, status, headers) {
            $scope.status = status;
            $scope.hosts =  data || "Request failed";
            $dialogs.error("<h3>Can't display hosts with id "+$stateParams.hostId+"</h3><br>"+$scope.data);
        });
    $scope.showCpuStatus = function (hostId) {
        $state.go('detailHost.cpuStatus',{hostId:hostId});
    }
    $scope.showMemStatus = function (hostId) {
        $state.go('detailHost.memStatus',{hostId:hostId});
    }
    $scope.showNicStatus = function (nicid) {
        // nic = JSON.stringify(nic);
        $state.go('detailHost.nicStatus',{nicid:nicid});
    }
    $scope.showDiskStatus = function (diskid) {
        // disk = JSON.stringify(disk);
        $state.go('detailHost.diskStatus',{diskid:diskid});
    }
    $scope.showRaidStatus = function (raidid) {
        // raid = JSON.stringify(raid);
        $state.go('detailHost.raidStatus',{raidid:raidid});
    }
    $scope.showPartitionStatus = function (partid) {
        // part = JSON.stringify(part);
        $state.go('detailHost.partStatus',{partid:partid});
    }
    $scope.showSwapStatus = function (hostId) {
        $state.go('detailHost.swapStatus',{hostId:hostId});
    }
}
function ToCpuStatus($rootScope, $scope, $stateParams, $http, $dialogs) {
    $scope.hostId = $stateParams.hostId;
    var data = '{"$select": {"host.$id": \"'+$stateParams.hostId+'\"},"$limit": 1,"$sort": {"sortkey": "timestamp","direction": -1}}';
    var uri = sfcsmCtrlURL+$rootScope.fsid+"/cpustat";
    $http({method: "post", data: data, url: uri }).
    success(function (data, status) {
        $scope.cpuStatusDetail =  data[0];
        $scope.status = status;
    }).
    error(function (data, status, headers) {
        $scope.status = status;
        $scope.hosts =  data || "Request failed";
        $dialogs.error("<h3>Can't display hosts with id "+$stateParams.hostId+"</h3><br>"+$scope.data);
    });
}

function ToSwapStatus($rootScope, $scope, $stateParams, $http, $dialogs) {
    $scope.hostId = $stateParams.hostId;
    var data = '{"$select": {"host.$id": \"'+$stateParams.hostId+'\"},"$limit": 1,"$sort": {"sortkey": "timestamp","direction": -1}}';
    var uri = sfcsmCtrlURL+$rootScope.fsid+"/swapstat";
    $http({method: "post", data: data, url: uri }).
    success(function (data, status) {
        $scope.swapStatusDetail =  data[0];
        $scope.status = status;
    }).
    error(function (data, status, headers) {
        $scope.status = status;
        $scope.hosts =  data || "Request failed";
        $dialogs.error("<h3>Can't display hosts with id "+$stateParams.hostId+"</h3><br>"+$scope.data);
    });
}

function ToNicStatus($rootScope, $scope, $stateParams, $http, $dialogs) {
    var data = '{"$select": {"_id": \"'+$stateParams.nicid+'\"}}';
    var uri = sfcsmCtrlURL+$rootScope.fsid+"/net?depth=1";
    $http({method: "post", data: data, url: uri }).
    success(function (data, status) {
        $scope.nic =  data[0];
        $scope.status = status;
    }).
    error(function (data, status, headers) {
        $scope.status = status;
        $scope.hosts =  data || "Request failed";
        $dialogs.error("<h3>Can't display hosts with id "+$scope.nic._id+"</h3><br>"+$scope.data);
    });
}

function ToDiskStatus($rootScope, $scope, $stateParams, $http, $dialogs) {
    var reqData = '{"$select": {"_id": \"'+$stateParams.diskid+'\"}}';
    var uri = sfcsmCtrlURL+$rootScope.fsid+"/disks?depth=3";
    $http({method: "post", data: reqData, url: uri }).
    success(function (data, status) {
        $scope.disk = data[0];
    }).
    error(function (data, status, headers) {
        $scope.status = status;
        $scope.hosts =  data || "Request failed";
        $dialogs.error("<h3>Can't display hosts with id "+$scope.disk._id+"</h3><br>"+$scope.data);
    });
    // data = '{"$select": {"disk.$id": \"'+$scope.disk._id+'\"},"$limit": 1,"$sort": {"sortkey": "timestamp","direction": -1}}';
}

function ToRaidStatus($rootScope, $scope, $stateParams, $http, $dialogs) {
    // $scope.raid = JSON.parse($stateParams.raid);
    var data = '{"$select": {"_id": \"'+$stateParams.raidid+'\"}}';
    var uri = sfcsmCtrlURL+$rootScope.fsid+"/raids?depth=1";
    $http({method: "post", data: data, url: uri }).
    success(function (data, status) {
        $scope.raid =  data[0];
        $scope.status = status;
    }).
    error(function (data, status, headers) {
        $scope.status = status;
        $scope.hosts =  data || "Request failed";
        $dialogs.error("<h3>Can't display hosts with id "+$stateParams.hostId+"</h3><br>"+$scope.data);
    });
}

function ToMemStatus($rootScope, $scope, $stateParams, $http, $dialogs) {
    $scope.hostId = $stateParams.hostId;
    var data = '{"$select": {"host.$id": \"'+$stateParams.hostId+'\"},"$limit": 1,"$sort": {"sortkey": "timestamp","direction": -1}}';
    var uri = sfcsmCtrlURL+$rootScope.fsid+"/memstat";
    $http({method: "post", data: data, url: uri }).
    success(function (data, status) {
        $scope.memStatusDetail =  data[0];
        $scope.status = status;
    }).
    error(function (data, status, headers) {
        $scope.status = status;
        $scope.hosts =  data || "Request failed";
        $dialogs.error("<h3>Can't display hosts with id "+$stateParams.hostId+"</h3><br>"+$scope.data);
    });
}

function ToPartStatus($rootScope, $scope, $stateParams, $http, $dialogs) {
    // $scope.part = JSON.parse($stateParams.part);
    var data = '{"$select": {"_id": \"'+$stateParams.partid+'\"}}';
    var uri = sfcsmCtrlURL+$rootScope.fsid+"/partitions?depth=1";
    $http({method: "post", data: data, url: uri }).
    success(function (data, status) {
        $scope.part =  data[0];
        $scope.status = status;
    }).
    error(function (data, status, headers) {
        $scope.status = status;
        $scope.hosts =  data || "Request failed";
        $dialogs.error("<h3>Can't display hosts with id "+$stateParams.hostId+"</h3><br>"+$scope.data);
    });
}

function CpuStatus($rootScope, $scope, $http, $dialogs) {
    now = new Date();
    var startTime = getWeekStartDate(now);
    var endTime = now.getTime();
    var data = '{"$select": {"host.$id": \"'+$scope.$parent.hostId+'\","limit": 1, "timestamp": {"$gt": '+startTime+',"$lt": '+endTime+'}},"$sort": {"sortkey": "timestamp","direction": -1}}';
    var uri = sfcsmCtrlURL+$rootScope.fsid+"/cpustat";
    $http({method: "post", data: data, url: uri }).
    success(function (data, status) {
        $scope.cpuStatusDetail =  data[0];
        $scope.status = status;
        //$scope.option = FormatData(data[0]);
    }).
    error(function (data, status, headers) {
        $scope.status = status;
        $scope.hosts =  data || "Request failed";
        $dialogs.error("<h3>Can't display hosts with id "+$scope.$parent.hostId+"</h3><br>"+$scope.data);
        });
    //return $scope.cpuStatusDetail;
}

function DetailDataPrepare($scope) {
    $scope.td_base = new Array(0,1,2,3);
    var disks = $scope.detailedHost.disks;
    var raids = $scope.detailedHost.raids;
    var cpus = $scope.detailedHost.cpus;
    var nics = $scope.detailedHost.network_interfaces;
    var partitions = $scope.detailedHost.partitions;
    // var swaps =
    len = Math.ceil(disks.length/4);
    $scope.tr_disks = new Array();
    for (var i=0; i<len; i++){
        $scope.tr_disks[i]=i;
    }
    len = Math.ceil(raids.length/4);
    $scope.tr_raids = new Array();
    for (var i=0; i<len; i++){
        $scope.tr_raids[i]=i;
    }
    len= Math.ceil(cpus.length/4);
    $scope.tr_cpus = new Array();
    for (var i=0; i<len; i++){
        $scope.tr_cpus[i]=i;
    }
    $scope.tr_nics = new Array();
    len = Math.ceil(nics.length/4);
    for (var i=0; i<len; i++){
        $scope.tr_nics[i]=i;
    }
    $scope.tr_partitions = new Array();
    len = Math.ceil(partitions.length/4);
    for (var i=0; i<len; i++){
        $scope.tr_partitions[i]=i;
    }
}

function getWeekStartDate(now) {
    var dayOfWeek = now.getDay();
    dayOfWeek = dayOfWeek != 0 ? dayOfWeek - 1 : 6;
    var weekStartDate = new Date(now-dayOfWeek*86400000);
    weekStartDate.setHours(0);
    weekStartDate.setMinutes(0);
    weekStartDate.setSeconds(0);
    weekStartDate.setMilliseconds(0);
    return weekStartDate.getTime();

}

//格局化日期：yyyy-MM-dd
function formatDate(date) {
    var myyear = date.getFullYear();
    var mymonth = date.getMonth()+1;
    var myweekday = date.getDate();

    if(mymonth < 10){
        mymonth = "0" + mymonth;
    }
    if(myweekday < 10){
        myweekday = "0" + myweekday;
    }
    return (myyear+"-"+mymonth + "-" + myweekday);
}

// //获得某月的天数
// function getMonthDays(myMonth){
//     var monthStartDate = new Date(nowYear, myMonth, 1);
//     var monthEndDate = new Date(nowYear, myMonth + 1, 1);
//     var days = (monthEndDate - monthStartDate)/(1000 * 60 * 60 * 24);
//     return days;
// }
//
// //获得本季度的开端月份
// function getQuarterStartMonth(){
//     var quarterStartMonth = 0;
//     if(nowMonth<3){
//         quarterStartMonth = 0;
//     }
//     if(2<nowMonth && nowMonth<6){
//         quarterStartMonth = 3;
//     }
//     if(5<nowMonth && nowMonth<9){
//         quarterStartMonth = 6;
//     }
//     if(nowMonth>8){
//         quarterStartMonth = 9;
//     }
//     return quarterStartMonth;
// }
//
// //获得本周的开端日期
// function getWeekStartDate() {
//     var weekStartDate = new Date(nowYear, nowMonth, nowDay - nowDayOfWeek);
//     return formatDate(weekStartDate);
// }
//
// //获得本周的停止日期
// function getWeekEndDate() {
//     var weekEndDate = new Date(nowYear, nowMonth, nowDay + (6 - nowDayOfWeek));
//     return formatDate(weekEndDate);
// }
//
// //获得本月的开端日期
// function getMonthStartDate(){
//     var monthStartDate = new Date(nowYear, nowMonth, 1);
//     return formatDate(monthStartDate);
// }
//
// //获得本月的停止日期
// function getMonthEndDate(){
//     var monthEndDate = new Date(nowYear, nowMonth, getMonthDays(nowMonth));
//     return formatDate(monthEndDate);
// }
//
// //获得上月开端时候
// function getLastMonthStartDate(){
//     var lastMonthStartDate = new Date(nowYear, lastMonth, 1);
//     return formatDate(lastMonthStartDate);
// }
//
// //获得上月停止时候
// function getLastMonthEndDate(){
//     var lastMonthEndDate = new Date(nowYear, lastMonth, getMonthDays(lastMonth));
//     return formatDate(lastMonthEndDate);
// }
//
// //获得本季度的开端日期
// function getQuarterStartDate(){
//
//     var quarterStartDate = new Date(nowYear, getQuarterStartMonth(), 1);
//     return formatDate(quarterStartDate);
// }
//
// //或的本季度的停止日期
// function getQuarterEndDate(){
//     var quarterEndMonth = getQuarterStartMonth() + 2;
//     var quarterStartDate = new Date(nowYear, quarterEndMonth, getMonthDays(quarterEndMonth));
//     return formatDate(quarterStartDate);
// }