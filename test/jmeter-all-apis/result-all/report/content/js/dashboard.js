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

    var data = {"OkPercent": 91.82539682539682, "KoPercent": 8.174603174603174};
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
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.7973639455782313, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [1.0, 500, 1500, "GET /logout 登出"], "isController": false}, {"data": [0.0, 500, 1500, "POST /setCurrency 设置货币"], "isController": false}, {"data": [0.0, 500, 1500, "POST /bot 聊天机器人"], "isController": false}, {"data": [0.9996078431372549, 500, 1500, "GET /_healthz 健康检查"], "isController": false}, {"data": [1.0, 500, 1500, "GET /robots.txt"], "isController": false}, {"data": [1.0, 500, 1500, "GET /static/icons/Hipster_NavLogo.svg"], "isController": false}, {"data": [0.4061574074074074, 500, 1500, "GET /product/{id} 随机商品详情"], "isController": false}, {"data": [1.0, 500, 1500, "4. GET /cart 查看购物车"], "isController": false}, {"data": [1.0, 500, 1500, "2. GET /product/OLJCESPC7Z 商品详情"], "isController": false}, {"data": [0.0, 500, 1500, "3. POST /cart 添加购物车"], "isController": false}, {"data": [1.0, 500, 1500, "GET /logout 登出-0"], "isController": false}, {"data": [1.0, 500, 1500, "GET /logout 登出-1"], "isController": false}, {"data": [1.0, 500, 1500, "6. POST /cart/empty 清空购物车-1"], "isController": false}, {"data": [1.0, 500, 1500, "6. POST /cart/empty 清空购物车-0"], "isController": false}, {"data": [1.0, 500, 1500, "GET /assistant 助手页面"], "isController": false}, {"data": [0.9975, 500, 1500, "GET /product-meta/{ids} 商品元数据API"], "isController": false}, {"data": [1.0, 500, 1500, "1. GET / 首页"], "isController": false}, {"data": [0.0, 500, 1500, "5. POST /cart/checkout 提交订单"], "isController": false}, {"data": [0.994375, 500, 1500, "GET / 首页"], "isController": false}, {"data": [1.0, 500, 1500, "6. POST /cart/empty 清空购物车"], "isController": false}]}, function(index, item){
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
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 35280, 2884, 8.174603174603174, 352.85289115646145, 1, 3357, 93.0, 1366.0, 1455.0, 1740.9800000000032, 50.95931488032217, 156.63967032533506, 11.319973026265425], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["GET /logout 登出", 200, 0, 0.0, 12.575000000000003, 10, 27, 12.0, 14.900000000000006, 15.949999999999989, 25.0, 4.1361624684617615, 43.93957680595194, 1.466520026781652], "isController": false}, {"data": ["POST /setCurrency 设置货币", 200, 200, 100.0, 2.465, 1, 8, 2.0, 3.0, 4.0, 5.990000000000009, 4.151789421240555, 16.493632192975173, 1.0298383915967784], "isController": false}, {"data": ["POST /bot 聊天机器人", 200, 200, 100.0, 4.384999999999999, 2, 47, 4.0, 5.0, 6.0, 32.850000000000136, 4.138216428719222, 21.135617111524933, 1.0628426960480033], "isController": false}, {"data": ["GET /_healthz 健康检查", 10200, 0, 0.0, 103.87049019607885, 1, 1366, 90.0, 181.0, 187.0, 284.0, 83.44240837696334, 9.759553439954189, 15.129049410994766], "isController": false}, {"data": ["GET /robots.txt", 200, 0, 0.0, 2.1700000000000004, 1, 5, 2.0, 3.0, 3.0, 4.0, 4.169359377931581, 0.5781728824866059, 0.7695399633096375], "isController": false}, {"data": ["GET /static/icons/Hipster_NavLogo.svg", 80, 0, 0.0, 3.374999999999999, 2, 10, 3.0, 4.0, 4.950000000000003, 10.0, 5.12656199935918, 29.56284043575777, 1.056352130727331], "isController": false}, {"data": ["GET /product/{id} 随机商品详情", 10800, 2184, 20.22222222222222, 926.3170370370343, 2, 3357, 1096.0, 1457.0, 1551.0, 2176.8799999999974, 15.6171597881272, 114.5646243359092, 3.7342680613175965], "isController": false}, {"data": ["4. GET /cart 查看购物车", 150, 0, 0.0, 14.886666666666663, 8, 29, 12.5, 23.0, 24.44999999999999, 28.49000000000001, 0.3922789050711202, 2.693531002128767, 0.0701045308867334], "isController": false}, {"data": ["2. GET /product/OLJCESPC7Z 商品详情", 150, 0, 0.0, 16.11999999999999, 8, 34, 14.0, 26.0, 28.0, 32.47000000000003, 0.3969157003974449, 3.154068906880931, 0.07635975876786782], "isController": false}, {"data": ["3. POST /cart 添加购物车", 150, 150, 100.0, 8.446666666666665, 2, 30, 6.0, 17.0, 19.44999999999999, 26.940000000000055, 0.39236509833977246, 1.576740605144691, 0.09809127458494311], "isController": false}, {"data": ["GET /logout 登出-0", 200, 0, 0.0, 2.239999999999999, 1, 14, 2.0, 3.0, 3.0, 5.990000000000009, 4.136932464577516, 0.836274433757369, 0.7473950253387114], "isController": false}, {"data": ["GET /logout 登出-1", 200, 0, 0.0, 10.135, 8, 25, 10.0, 12.0, 12.0, 22.940000000000055, 4.1363335539377895, 43.10524092850348, 0.7192938632321311], "isController": false}, {"data": ["6. POST /cart/empty 清空购物车-1", 150, 0, 0.0, 11.319999999999999, 8, 42, 10.0, 13.0, 22.44999999999999, 36.90000000000009, 0.39006225393572813, 4.064418212396699, 0.06818471040478061], "isController": false}, {"data": ["6. POST /cart/empty 清空购物车-0", 150, 0, 0.0, 10.273333333333337, 4, 31, 8.0, 19.0, 20.0, 28.960000000000036, 0.39003689749050263, 0.03466148210120677, 0.10398444630362032], "isController": false}, {"data": ["GET /assistant 助手页面", 200, 0, 0.0, 3.4100000000000015, 2, 6, 3.0, 4.0, 5.0, 6.0, 4.110827920743238, 33.0993908266875, 0.7547223135739538], "isController": false}, {"data": ["GET /product-meta/{ids} 商品元数据API", 10800, 0, 0.0, 123.6732407407401, 1, 1634, 91.0, 194.0, 274.0, 373.0, 15.672116112966934, 4.816483193469371, 3.823932844982456], "isController": false}, {"data": ["1. GET / 首页", 150, 0, 0.0, 18.786666666666665, 10, 37, 17.0, 27.0, 30.0, 36.49000000000001, 0.39872302306479784, 4.161048548515288, 0.06487036683847199], "isController": false}, {"data": ["5. POST /cart/checkout 提交订单", 150, 150, 100.0, 10.239999999999998, 3, 21, 9.0, 18.0, 19.0, 21.0, 0.3899537514850739, 1.704143591695025, 0.13556985891473272], "isController": false}, {"data": ["GET / 首页", 800, 0, 0.0, 30.95250000000003, 8, 723, 14.0, 47.89999999999998, 87.74999999999966, 534.98, 8.423712751395177, 87.84188427924607, 1.4215015267979363], "isController": false}, {"data": ["6. POST /cart/empty 清空购物车", 150, 0, 0.0, 21.713333333333342, 13, 59, 19.5, 31.0, 35.0, 54.92000000000007, 0.39002675583545027, 4.098708905805938, 0.17216024769299174], "isController": false}]}, function(index, item){
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
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": ["500/Internal Server Error", 2384, 82.6629680998613, 6.757369614512472], "isController": false}, {"data": ["422/Unprocessable Entity", 500, 17.337031900138697, 1.417233560090703], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 35280, 2884, "500/Internal Server Error", 2384, "422/Unprocessable Entity", 500, "", "", "", "", "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": ["POST /setCurrency 设置货币", 200, 200, "422/Unprocessable Entity", 200, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /bot 聊天机器人", 200, 200, "500/Internal Server Error", 200, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["GET /product/{id} 随机商品详情", 10800, 2184, "500/Internal Server Error", 2184, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["3. POST /cart 添加购物车", 150, 150, "422/Unprocessable Entity", 150, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["5. POST /cart/checkout 提交订单", 150, 150, "422/Unprocessable Entity", 150, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
