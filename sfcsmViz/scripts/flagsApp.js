/**
 * Created by Alain Dechorgnat on 9/19/14.
 */
var FlagsApp = angular.module('FlagsApp', ['SfcsmCommons']);

FlagsApp.controller("flagsCtrl", function ($rootScope, $scope, $http, $dialogs) {
    var apiURL = '/ceph-rest-api/';

    refreshData();
    setInterval(function(){
        refreshData();
    }, 10000);

    $scope.flagList = [
        {name:'full',minVersion:'Hammer',description:'if set, no data writes'},
        {name:'pause',minVersion:'Firefly',description:'if set, no IO requests will be sent to any OSD'},
        {name:'noup',minVersion:'Firefly',description:'prevent OSDs from getting marked up'},
        {name:'nodown',minVersion:'Firefly',description:'prevent OSDs from getting marked down'},
        {name:'noout',minVersion:'Firefly',description:'prevent OSDs from getting marked out'},
        {name:'noin',minVersion:'Firefly',description:'prevent OSDs from getting marked in<br><em>noin and noout prevent booting OSDs from being marked in (allocated data) or protect OSDs from eventually being marked out (regardless of what the current value for mon osd down out interval is).<br>noup, noout, and nodown are temporary in the sense that once the flags are cleared, the action they were blocking should occur shortly after.<br>The noin flag, on the other hand, prevents OSDs from being marked in on boot, and any daemons that started while the flag was set will remain that way.</em>'},
        {name:'nobackfill',minVersion:'Firefly',description:'block osd backfill'},
        {name:'norebalance',minVersion:'Hammer',description:'block osd backfill unless pg is degraded'},
        {name:'norecover',minVersion:'Firefly',description:'block osd recovery and backfill'},
        {name:'noscrub',minVersion:'Firefly',description:'block periodic scrub'},
        {name:'nodeep-scrub',minVersion:'Firefly',description:'block periodic deep-scrub'},
        {name:'notieragent',minVersion:'Firefly',description:'this will pause tiering agent work'},
        {name:'sortbitwise',minVersion:'Infernalis',description:'use bitwise hobject_t sort'}
    ];

    function refreshData() {
        //
        $scope.date = new Date();
        $http({method: "get", url: apiURL + "osd/dump.json",timeout:4000})
            .success(function (data, status){
                console.log("refreshing flags...");
                $scope.status = "";
                $scope.flags = data.output.flags;
                $scope.setFlagList = $scope.flags.split(',');
                $scope.status = "";
            })
            .error(function (data) {
                $scope.status = "Flags not found";
            });
    }

    $scope.isAvailable=function(flag){
        var version = $rootScope.conf.ceph_version_name;
        return version >= flag.minVersion;
    }

    $scope.isSet=function(flag){
        flag = flag.name;
        if (flag=="pause") flag='pauserd';
        var rep = $.inArray(flag, $scope.setFlagList) > -1
        return rep;
    }

    $scope.setFlag=function(flag){
        if ($rootScope.hasRole('admin')) {
            $http({method: "put", url: apiURL + "osd/set?key=" + flag.name, timeout: 4000})
                .success(function () {
                    refreshData();
                })
                .error(function (data) {
                    $dialogs.error("<h3>Flag not set: "+ flag.name +"</h3><br>"+data.status);
                })
        }
    }

    $scope.unsetFlag=function(flag){
        if ($rootScope.hasRole('admin')) {
            $http({method: "put", url: apiURL + "osd/unset?key=" + flag.name, timeout: 4000})
                .success(function () {
                    refreshData();
                })
                .error(function (data) {
                    $dialogs.error("<h3>Flag not unset: "+ flag.name +"</h3><br>"+data.status);
                })
        }
    }
});