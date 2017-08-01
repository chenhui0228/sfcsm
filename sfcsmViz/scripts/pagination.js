$(function(){
    var pagination = {
        row: 10,
        page: 1,
        rows: [10, 20, 30, 50, 150, 200, 500],
        init: function(){
            pagination.loadRows();
        },
        //加载下拉列页码
        loadRows: function(){
            var html = '';
            //根据配置项加载页码
            if(pagination.rows.length > 0) {
                $(".cp_select_s").html(html);
                for(var i = 0;i<pagination.rows.length;i++) {
                    html += '<option value="' + pagination.rows[i] + '">' + pagination.rows[i] + '</option>';
                }
                $(".cp_select_s").html(html);
            }
        }
    };
    pagination.init();
});
