/*
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
var showControllersOnly = false;
var seriesFilter = "";
var filtersOnlySampleSeries = true;

/*
 * Add header in statistics table to group metrics by category
 * format
 *
 */
function summaryTableHeader(header) {
    var newRow = header.insertRow(-1);
    newRow.className = "tablesorter-no-sort";
    var cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Requests";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 3;
    cell.innerHTML = "Executions";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 7;
    cell.innerHTML = "Response Times (ms)";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Throughput";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 2;
    cell.innerHTML = "Network (KB/sec)";
    newRow.appendChild(cell);
}

/*
 * Populates the table identified by id parameter with the specified data and
 * format
 *
 */
function createTable(table, info, formatter, defaultSorts, seriesIndex, headerCreator) {
    var tableRef = table[0];

    // Create header and populate it with data.titles array
    var header = tableRef.createTHead();

    // Call callback is available
    if(headerCreator) {
        headerCreator(header);
    }

    var newRow = header.insertRow(-1);
    for (var index = 0; index < info.titles.length; index++) {
        var cell = document.createElement('th');
        cell.innerHTML = info.titles[index];
        newRow.appendChild(cell);
    }

    var tBody;

    // Create overall body if defined
    if(info.overall){
        tBody = document.createElement('tbody');
        tBody.className = "tablesorter-no-sort";
        tableRef.appendChild(tBody);
        var newRow = tBody.insertRow(-1);
        var data = info.overall.data;
        for(var index=0;index < data.length; index++){
            var cell = newRow.insertCell(-1);
            cell.innerHTML = formatter ? formatter(index, data[index]): data[index];
        }
    }

    // Create regular body
    tBody = document.createElement('tbody');
    tableRef.appendChild(tBody);

    var regexp;
    if(seriesFilter) {
        regexp = new RegExp(seriesFilter, 'i');
    }
    // Populate body with data.items array
    for(var index=0; index < info.items.length; index++){
        var item = info.items[index];
        if((!regexp || filtersOnlySampleSeries && !info.supportsControllersDiscrimination || regexp.test(item.data[seriesIndex]))
                &&
                (!showControllersOnly || !info.supportsControllersDiscrimination || item.isController)){
            if(item.data.length > 0) {
                var newRow = tBody.insertRow(-1);
                for(var col=0; col < item.data.length; col++){
                    var cell = newRow.insertCell(-1);
                    cell.innerHTML = formatter ? formatter(col, item.data[col]) : item.data[col];
                }
            }
        }
    }

    // Add support of columns sort
    table.tablesorter({sortList : defaultSorts});
}

$(document).ready(function() {

    // Customize table sorter default options
    $.extend( $.tablesorter.defaults, {
        theme: 'blue',
        cssInfoBlock: "tablesorter-no-sort",
        widthFixed: true,
        widgets: ['zebra']
    });

    var data = {"OkPercent": 91.94444444444444, "KoPercent": 8.055555555555555};
    var dataset = [
        {
            "label" : "FAIL",
            "data" : data.KoPercent,
            "color" : "#FF6347"
        },
        {
            "label" : "PASS",
            "data" : data.OkPercent,
            "color" : "#9ACD32"
        }];
    $.plot($("#flot-requests-summary"), dataset, {
        series : {
            pie : {
                show : true,
                radius : 1,
                label : {
                    show : true,
                    radius : 3 / 4,
                    formatter : function(label, series) {
                        return '<div style="font-size:8pt;text-align:center;padding:2px;color:white;">'
                            + label
                            + '<br/>'
                            + Math.round10(series.percent, -2)
                            + '%</div>';
                    },
                    background : {
                        opacity : 0.5,
                        color : '#000'
                    }
                }
            }
        },
        legend : {
            show : true
        }
    });

    // Creates APDEX table
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.6884722222222223, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [0.0, 500, 1500, "3. POST 添加购物车 /cart"], "isController": false}, {"data": [1.0, 500, 1500, "GET 商品元数据 /product-meta/{ids}"], "isController": false}, {"data": [1.0, 500, 1500, "4. GET 查看购物车 /cart"], "isController": false}, {"data": [1.0, 500, 1500, "GET robots.txt"], "isController": false}, {"data": [0.0, 500, 1500, "GET 首页 /"], "isController": false}, {"data": [0.757, 500, 1500, "GET 随机商品详情 /product/{id}"], "isController": false}, {"data": [0.0, 500, 1500, "1. GET 首页 /"], "isController": false}, {"data": [1.0, 500, 1500, "GET 健康检查 /_healthz"], "isController": false}, {"data": [0.0, 500, 1500, "6. POST 清空购物车 /cart/empty"], "isController": false}, {"data": [0.0, 500, 1500, "5. POST 提交订单 /cart/checkout"], "isController": false}, {"data": [1.0, 500, 1500, "2. GET 商品详情 /product/OLJCESPC7Z"], "isController": false}, {"data": [1.0, 500, 1500, "6. POST 清空购物车 /cart/empty-0"], "isController": false}, {"data": [0.0, 500, 1500, "6. POST 清空购物车 /cart/empty-1"], "isController": false}]}, function(index, item){
        switch(index){
            case 0:
                item = item.toFixed(3);
                break;
            case 1:
            case 2:
                item = formatDuration(item);
                break;
        }
        return item;
    }, [[0, 0]], 3);

    // Create statistics table
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 3600, 290, 8.055555555555555, 870.2263888888876, 1, 7447, 5.0, 3713.0, 3742.0, 4013.99, 4.790922798271541, 19.648581082126398, 0.9566510068922747], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["3. POST 添加购物车 /cart", 100, 100, 100.0, 6.829999999999999, 3, 20, 6.0, 10.0, 11.949999999999989, 19.969999999999985, 0.1913677820856792, 0.7690218977368847, 0.0478419455214198], "isController": false}, {"data": ["GET 商品元数据 /product-meta/{ids}", 600, 0, 0.0, 3.705, 1, 74, 3.0, 5.0, 6.949999999999932, 19.980000000000018, 12.103851041939844, 4.574404641826875, 2.3876737406951647], "isController": false}, {"data": ["4. GET 查看购物车 /cart", 100, 0, 0.0, 12.75, 8, 46, 11.0, 18.0, 19.94999999999999, 45.83999999999992, 0.19173690628666967, 1.3175246453825917, 0.034265482275840385], "isController": false}, {"data": ["GET robots.txt", 600, 0, 0.0, 3.156666666666666, 1, 70, 2.0, 4.0, 6.0, 22.99000000000001, 12.057150895243453, 1.6719877218013384, 2.2253921085947392], "isController": false}, {"data": ["GET 首页 /", 500, 0, 0.0, 3737.186000000004, 3704, 4280, 3709.0, 3799.0, 3878.0, 4184.250000000001, 5.523763229412934, 57.60141456671601, 0.9321350449634327], "isController": false}, {"data": ["GET 随机商品详情 /product/{id}", 500, 90, 18.0, 257.1780000000003, 2, 7447, 11.0, 31.0, 1641.5499999999997, 6273.080000000005, 5.645379821154368, 41.80466606519849, 1.0860740476244242], "isController": false}, {"data": ["1. GET 首页 /", 100, 0, 0.0, 3759.68, 3706, 4020, 3713.0, 4012.0, 4017.85, 4019.99, 0.19129420091629923, 1.9963343248749414, 0.031122669797515087], "isController": false}, {"data": ["GET 健康检查 /_healthz", 600, 0, 0.0, 3.1666666666666656, 1, 53, 2.0, 5.0, 8.949999999999932, 18.0, 12.091411067671597, 1.4417590735963888, 2.1714946243601627], "isController": false}, {"data": ["6. POST 清空购物车 /cart/empty", 100, 0, 0.0, 3747.6199999999994, 3709, 4022, 3715.0, 3849.9, 3893.0, 4021.96, 0.19178360672086472, 2.0154134686750242, 0.08465448265413168], "isController": false}, {"data": ["5. POST 提交订单 /cart/checkout", 100, 100, 100.0, 6.440000000000001, 3, 20, 5.0, 11.0, 12.949999999999989, 19.969999999999985, 0.19126822307995395, 0.8358645491042909, 0.06649559318014024], "isController": false}, {"data": ["2. GET 商品详情 /product/OLJCESPC7Z", 100, 0, 0.0, 15.390000000000006, 9, 172, 13.0, 18.900000000000006, 20.94999999999999, 170.52999999999923, 0.19335403510535862, 1.5370890501676377, 0.03719799308179262], "isController": false}, {"data": ["6. POST 清空购物车 /cart/empty-0", 100, 0, 0.0, 6.8900000000000015, 4, 25, 6.0, 10.0, 12.0, 24.97999999999999, 0.193157585684705, 0.017165371384089995, 0.05149611415226999], "isController": false}, {"data": ["6. POST 清空购物车 /cart/empty-1", 100, 0, 0.0, 3740.5599999999995, 3703, 4013, 3707.5, 3843.9, 3888.0, 4012.99, 0.19179280239971155, 1.998466017192307, 0.03352628088823083], "isController": false}]}, function(index, item){
        switch(index){
            // Errors pct
            case 3:
                item = item.toFixed(2) + '%';
                break;
            // Mean
            case 4:
            // Mean
            case 7:
            // Median
            case 8:
            // Percentile 1
            case 9:
            // Percentile 2
            case 10:
            // Percentile 3
            case 11:
            // Throughput
            case 12:
            // Kbytes/s
            case 13:
            // Sent Kbytes/s
                item = item.toFixed(2);
                break;
        }
        return item;
    }, [[0, 0]], 0, summaryTableHeader);

    // Create error table
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": ["500/Internal Server Error", 90, 31.03448275862069, 2.5], "isController": false}, {"data": ["422/Unprocessable Entity", 200, 68.96551724137932, 5.555555555555555], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 3600, 290, "422/Unprocessable Entity", 200, "500/Internal Server Error", 90, "", "", "", "", "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": ["3. POST 添加购物车 /cart", 100, 100, "422/Unprocessable Entity", 100, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["GET 随机商品详情 /product/{id}", 500, 90, "500/Internal Server Error", 90, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["5. POST 提交订单 /cart/checkout", 100, 100, "422/Unprocessable Entity", 100, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
