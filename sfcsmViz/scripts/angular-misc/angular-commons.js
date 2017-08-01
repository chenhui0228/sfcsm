/**
 * Created by Alain Dechorgnat on 1/14/14.
 */
//默认十种颜色
var defaultColors = ['#B95784','#00FF66','#FFBBBB','#95D1E5','#0099CC','#2F4554','#8DD6FF','#843DA9','#3D45A9','#32323A'];
//项目名称
var ProjectTitle = 'Ceph-Object';
var sfcsmCtrlURL = '/sfcsmCtrl/';
var sfcsmCtrlDomain = 'http://10.202.16.216:8087';
var cephRestApiURL = '/ceph-rest-api/';
//var cephRestApiURL = '/ceph_rest_api/';
//dashboard
var indexCtrlURL = 'http://10.202.16.216:8087/ceph_rest_api/api/v0.1/status.json';
//StorageManage
{
    //pool集合数据
    var poolListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'poolList';
    var poolPutCtrURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'pools/';
    var poolGetCtrURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'pools/';
    var poolDelCtrURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'pools/';
    //默认pool的类型
    var poolDetailTypes = ['replicated', 'erasure'];
    //monitor(list)
    var monitorListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'mons/';
    //monitor(enable)
    var monitordaemonsCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'daemons/';
    //osd
    var osdListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'osdsList/';
    var osddaemonsCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'daemons/';
    var osdEditCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'osds/stat/';
    //cluster
    var clusterListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'cluster/';
    var clusterSetCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'flags';
    //rgw
    var rgwListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'radosgws/';
    var rgwEditCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'daemons/';
    //hardware
    var hardwareListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'osdsList/';
    //clulog
    var clulogListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'osdsList/';
    //syslog
    var syslogListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'syslogs/';
}
//StorageService
{
    //usermanage
    var usermanageListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'S3/user';
    var usermanageDetailCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'S3/user/';
    //bucketmanage
    var bucketmanageListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'S3/bucket';
    var bucketmanageDetailCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'S3/bucket/';
}
//StateAnalysis
{
    //capacity
    var capacityListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'osdsList/';
    //qualities
    var qualitiesListCtrlURL = sfcsmCtrlDomain + sfcsmCtrlURL + 'osdsList/';
}

function funcBytes (bytes, precision) {
    if (isNaN(parseFloat(bytes)) || !isFinite(bytes)) return '-';
    if (typeof precision === 'undefined') precision = 1;
    var units = ['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'];
    var number = 0;
    if (bytes>0) number = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, Math.floor(number))).toFixed(precision) + ' ' + units[number];
}

//判断是否为数字（包含小数点）
function isNum(num){
    return /^[0-9]+.?[0-9]+$/.test(num)
}

//判断是否为空
function isNullOrEmpty(obj) {
    var result = false;
    if (obj == null || obj == '' || obj == undefined || obj.length <= 0)
        result = true;
    return result;
}
//首页数据
function IndexData(){
    var res = Ajax(res, indexCtrlURL, '', '', '',  false);
    return res;
}
//首页pool数据
function IndexPoolData(){
    var res = Ajax(res, poolListCtrlURL, '', '', '',  false);
    return res;
}

///ajax数据交互
///result: 返回结果
///_url: 访问地址
///_params: 地址参数
///_type: 提交数据类型： get(默认), post
///_dataType: 返回数据类型
///_async: 是否异步, true, false(默认)
function Ajax(result, _url, _params, _type, _dataType, _async){
    if(isNullOrEmpty((_type)))
        _type = 'get';
    if(isNullOrEmpty(_dataType))
        _dataType = 'json';
    if(isNullOrEmpty(_async))
        _async = false;
    $.ajax({
        type: _type,
        url: _url,
        data: _params,
        dataType: _dataType,
        async: _async,
        success: function (data) {
            result = data;
        },
        error: function (err) {
            result = '{"code":"-1", "msg":"' + err + '"}';
        }
    });
    return result;
}
//ceph提示
//content: 显示内容
//hideTime: 自动隐藏，毫秒单位
//css: jquey添加样式方式，例：{"color":"red","width:":"200px"}
function CephAlert(content, hideTime, css){
    $('#myModalTips').modal('show');
    $(".tips_text").html(content);
    if(!isNullOrEmpty((hideTime))){
        setTimeout(function(){
            $('#myModalTips').modal('hide');
        }, hideTime);
    }else{
        //默认一秒后隐藏
        setTimeout(function(){
            $('#myModalTips').modal('hide');
        }, 1000);
    }
    if(!isNullOrEmpty(css)){
        $('#myModalTips').css(css);
    }
}
function funcBytesFilter () {
    return funcBytes;
}

function funcDurationFilter(){
    return function (duration){
        if (duration == "-") return "not available"
        var sign= (duration >=0 ? "":"- ");
        duration = Math.abs(Math.floor(duration));
        var minutes = Math.floor(duration / 60);
        var str =duration-(60*minutes)+"s"
        if (minutes == 0) return sign+str;
        var hours = Math.floor(minutes/ 60);
        var str =minutes-(60*hours)+"m "+str;
        if (hours==0) return sign+str;
        var days = Math.floor(hours/ 24);
        var str =hours-(24*days)+"h "+str;
        if (days==0) return sign+str;
        return sign+days+"d "+str;
    }
}

function funcPrettifyArrayFilter(){
    return function (string){
        string = string.toString().replace(/,/g, ", ");;
        return string;
    }
}


function resizeBlocks(blockNames){
    var height = window.innerHeight-250;
    for(var i= 0; i < blockNames.length; i++){
    var block = document.querySelector(blockNames[i]);
    //console.log(blockNames[i]);
    block.style.maxHeight = height+"px";
    }
}

function getMenu(){
    var navList = angular.module('navList', []);

    navList.controller('navCtrl', ['$scope', '$location', function ($scope, $location) {
        $scope.navClass = function (page) {
            var currentRoute = $location.path().substring(1) || 'home';
            return page === currentRoute ? 'active' : '';
        };
    }]);
}


angular.module('SfcsmCommons', ['ngTable','dialogs','ui.bootstrap'])
    .controller('overallStatusCtrl', function ($rootScope, $scope, $http, $window) {
        $rootScope.roles = [];
        $scope.ProjectTitle = ProjectTitle;

        $rootScope.hasRole=function(role){
            if ($.inArray('admin',$rootScope.roles)!=-1) return true;
            return ($.inArray(role,$rootScope.roles)!=-1);
        }

        $http({method: "get", url: sfcsmCtrlURL + "conf.json",timeout:4000})
            .success(function (data) {
                $rootScope.conf = data;
                $rootScope.roles=data.roles;
                $rootScope.useInfluxDB = (typeof $rootScope.conf.influxdb_endpoint !=='undefined')&&($rootScope.conf.influxdb_endpoint != "");
            })
            .error(function(data,status){
                if (status==401) $window.location.assign("login.html");
                console.log (data);
            });
        refreshData();
        setInterval(function () {
            refreshData()
        }, 10 * 1000)
        function refreshData(){
            $http({method: "get", url: cephRestApiURL + "status.json",timeout:4000})
            .success(function (data) {
                $rootScope.fsid = data.output.fsid;
                $scope.overallStatus = {};
                $scope.overallStatus.severity = data.output.health.overall_status;
                $scope.overallStatus.summary="";
                var i = 0;
                while(typeof data.output.health.summary[i] !== "undefined"){
                    if ($scope.overallStatus.summary!="") $scope.overallStatus.summary+=" | ";
                    $scope.overallStatus.summary += data.output.health.summary[i].summary;
                    i++;
                    }
                if ($scope.overallStatus.summary==""){
                    if (data.output.health.detail[0])
                    $scope.overallStatus.summary = data.output.health.detail[0];
                    else
                    //remove HEALTH_ in severity
                    $scope.overallStatus.summary = $scope.overallStatus.severity.substring(7);
                    }
                })
            .error(function (data) {
                $scope.overallStatus = {};
                $scope.overallStatus.severity = "HEALTH_WARN";
                $scope.overallStatus.summary = "Status not available";
                });
        }
});

function getPoolList($http, $scope) {
    $http({method: "get", url: sfcsmCtrlURL + "poolList/"}).
        success(function (data, status) {
            $scope.poolList =  data;
        }).
        error(function (data, status) {
            console.error("can't retrieve pool list")
        });
}

function getPoolNum(poolName, $scope) {
    for (var i in $scope.poolList){
        var pool = $scope.poolList[i];
        if (poolName == pool.poolname) return ''+pool.poolnum;
    }
    return '';
}