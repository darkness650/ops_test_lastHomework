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

    var data = {"OkPercent": 36.206896551724135, "KoPercent": 63.793103448275865};
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
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.3620689655172414, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [0.0, 500, 1500, "POST /cart - 缺少product_id"], "isController": false}, {"data": [0.0, 500, 1500, "POST /setCurrency - XSS注入"], "isController": false}, {"data": [1.0, 500, 1500, "GET /product/{id} - 有效ID1"], "isController": false}, {"data": [0.0, 500, 1500, "POST /bot - 无效JSON"], "isController": false}, {"data": [1.0, 500, 1500, "GET /product/{id} - 有效ID2"], "isController": false}, {"data": [1.0, 500, 1500, "GET / - 正常"], "isController": false}, {"data": [1.0, 500, 1500, "GET /logout - 正常"], "isController": false}, {"data": [0.0, 500, 1500, "GET /cart/empty - 错误方法"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart/checkout - zip_code非数字"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart/checkout - 无效email格式"], "isController": false}, {"data": [1.0, 500, 1500, "GET /product-meta/{ids} - SQL注入"], "isController": false}, {"data": [1.0, 500, 1500, "GET /_healthz - 正常"], "isController": false}, {"data": [0.0, 500, 1500, "POST /setCurrency - 缺少currency_code"], "isController": false}, {"data": [0.0, 500, 1500, "POST /bot - 正常JSON"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart/checkout - XSS注入email"], "isController": false}, {"data": [0.0, 500, 1500, "GET /product/{id} - 超长ID"], "isController": false}, {"data": [0.0, 500, 1500, "GET /product/{id} - 负数ID"], "isController": false}, {"data": [1.0, 500, 1500, "POST /cart - 正常添加"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart - SQL注入product_id"], "isController": false}, {"data": [1.0, 500, 1500, "GET /static/ - 正常(根)"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart - 缺少quantity"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart - quantity超大值"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart - quantity=0"], "isController": false}, {"data": [1.0, 500, 1500, "GET /robots.txt - 正常"], "isController": false}, {"data": [1.0, 500, 1500, "POST /setCurrency - EUR"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart/checkout - 空body"], "isController": false}, {"data": [1.0, 500, 1500, "GET /cart - 正常"], "isController": false}, {"data": [0.0, 500, 1500, "GET /static/ - 路径穿越"], "isController": false}, {"data": [1.0, 500, 1500, "HEAD /_healthz - HEAD方法"], "isController": false}, {"data": [0.0, 500, 1500, "POST /bot - 空body"], "isController": false}, {"data": [0.0, 500, 1500, "GET /product-meta/{ids} - 空ID"], "isController": false}, {"data": [1.0, 500, 1500, "HEAD / - HEAD方法"], "isController": false}, {"data": [0.0, 500, 1500, "POST /setCurrency - SQL注入"], "isController": false}, {"data": [0.0, 500, 1500, "POST /bot - XSS JSON"], "isController": false}, {"data": [0.0, 500, 1500, "GET /static/ - 路径穿越-1"], "isController": false}, {"data": [1.0, 500, 1500, "GET /static/ - 路径穿越-0"], "isController": false}, {"data": [0.0, 500, 1500, "GET /product/{id} - 不存在的ID"], "isController": false}, {"data": [1.0, 500, 1500, "POST /cart/empty - 正常"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart/checkout - 已过期信用卡"], "isController": false}, {"data": [0.0, 500, 1500, "GET /static/ - 不存在的文件"], "isController": false}, {"data": [0.0, 500, 1500, "GET /product-meta/{ids} - XSS注入"], "isController": false}, {"data": [0.0, 500, 1500, "GET /product/{id} - XSS注入ID"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart - quantity负数"], "isController": false}, {"data": [0.0, 500, 1500, "GET / - 带SQL注入参数"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart/checkout - 完整正常"], "isController": false}, {"data": [0.0, 500, 1500, "TRACE / - 非法方法"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart - quantity非数字"], "isController": false}, {"data": [1.0, 500, 1500, "POST /setCurrency - JPY"], "isController": false}, {"data": [1.0, 500, 1500, "GET /assistant - 正常"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart - 空body"], "isController": false}, {"data": [1.0, 500, 1500, "POST /_healthz - 错误方法"], "isController": false}, {"data": [1.0, 500, 1500, "GET /product-meta/{ids} - 有效ID"], "isController": false}, {"data": [1.0, 500, 1500, "POST /setCurrency - USD"], "isController": false}, {"data": [0.0, 500, 1500, "POST /setCurrency - 无效货币RMB"], "isController": false}, {"data": [0.0, 500, 1500, "GET /product/{id} - SQL注入ID"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart/checkout - 缺少信用卡号"], "isController": false}, {"data": [1.0, 500, 1500, "HEAD /cart - HEAD方法"], "isController": false}, {"data": [0.0, 500, 1500, "POST /cart/checkout - 缺少email"], "isController": false}]}, function(index, item){
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
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 2900, 1850, 63.793103448275865, 262.4303448275861, 0, 4099, 3.0, 69.0, 4003.0, 4018.0, 34.28787627988366, 103.35815663499965, 6.904684137719029], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["POST /cart - 缺少product_id", 50, 50, 100.0, 1.4400000000000002, 1, 3, 1.0, 2.0, 2.4499999999999957, 3.0, 10.248001639680261, 41.54243633428982, 2.101640961262554], "isController": false}, {"data": ["POST /setCurrency - XSS注入", 50, 50, 100.0, 1.1600000000000001, 0, 3, 1.0, 2.0, 2.0, 3.0, 10.32844453625284, 41.84835584073539, 2.622456620532948], "isController": false}, {"data": ["GET /product/{id} - 有效ID1", 50, 0, 0.0, 23.999999999999996, 7, 79, 10.0, 61.39999999999999, 68.14999999999998, 79.0, 10.183299389002038, 81.68358579429734, 1.2828570519348268], "isController": false}, {"data": ["POST /bot - 无效JSON", 50, 50, 100.0, 4015.7599999999998, 4006, 4023, 4016.0, 4021.0, 4022.45, 4023.0, 6.222000995520159, 32.313087201343954, 1.1727013595072175], "isController": false}, {"data": ["GET /product/{id} - 有效ID2", 50, 0, 0.0, 23.32, 7, 48, 29.0, 39.699999999999996, 44.79999999999998, 48.0, 10.235414534288639, 81.8377366939611, 1.2894223387922212], "isController": false}, {"data": ["GET / - 正常", 50, 0, 0.0, 29.52000000000001, 10, 93, 13.0, 82.29999999999998, 90.44999999999999, 93.0, 10.216591744993869, 107.27421332243563, 1.107462581732734], "isController": false}, {"data": ["GET /logout - 正常", 50, 0, 0.0, 3.6200000000000014, 2, 12, 3.0, 4.899999999999999, 8.349999999999987, 12.0, 10.195758564437194, 1.7225256168433931, 1.164945070350734], "isController": false}, {"data": ["GET /cart/empty - 错误方法", 50, 50, 100.0, 29.34, 1, 47, 31.0, 42.0, 45.89999999999999, 47.0, 10.185373803218578, 1.7207711601140763, 1.2035451466693827], "isController": false}, {"data": ["POST /cart/checkout - zip_code非数字", 50, 50, 100.0, 1.1800000000000002, 1, 3, 1.0, 2.0, 2.0, 3.0, 10.264832683227263, 42.08180430096489, 4.611155306918497], "isController": false}, {"data": ["POST /cart/checkout - 无效email格式", 50, 50, 100.0, 1.2400000000000007, 1, 3, 1.0, 2.0, 2.4499999999999957, 3.0, 10.260619741432382, 42.01443220295506, 4.549141955674123], "isController": false}, {"data": ["GET /product-meta/{ids} - SQL注入", 50, 0, 0.0, 32.779999999999994, 2, 83, 32.0, 64.8, 68.35, 83.0, 10.222858311183808, 1.5673718309139235, 1.397656409732161], "isController": false}, {"data": ["GET /_healthz - 正常", 50, 0, 0.0, 39.64, 2, 104, 33.0, 77.39999999999999, 99.79999999999998, 104.0, 10.05631536604988, 1.964124094931617, 1.168653836484312], "isController": false}, {"data": ["POST /setCurrency - 缺少currency_code", 50, 50, 100.0, 1.28, 1, 3, 1.0, 2.0, 2.4499999999999957, 3.0, 10.326311441553077, 41.84979734613796, 2.0773634345311858], "isController": false}, {"data": ["POST /bot - 正常JSON", 50, 50, 100.0, 2396.6400000000003, 147, 4055, 2597.0, 3849.8, 3993.0999999999995, 4055.0, 6.205783790492739, 32.228865427578505, 1.1817654679160978], "isController": false}, {"data": ["POST /cart/checkout - XSS注入email", 50, 50, 100.0, 1.2400000000000002, 0, 4, 1.0, 2.0, 2.0, 4.0, 10.264832683227263, 42.03168304762882, 4.821664570929993], "isController": false}, {"data": ["GET /product/{id} - 超长ID", 50, 50, 100.0, 2.660000000000001, 1, 6, 2.0, 4.0, 5.0, 6.0, 10.218679746576743, 57.34036506233395, 6.177112073370121], "isController": false}, {"data": ["GET /product/{id} - 负数ID", 50, 50, 100.0, 3.6799999999999997, 1, 27, 2.0, 8.899999999999999, 15.599999999999966, 27.0, 10.222858311183808, 52.39214884481701, 1.2079744684113678], "isController": false}, {"data": ["POST /cart - 正常添加", 50, 0, 0.0, 5.42, 4, 29, 5.0, 6.0, 7.8999999999999915, 29.0, 10.191602119853242, 1.761634350794945, 2.30903485527925], "isController": false}, {"data": ["POST /cart - SQL注入product_id", 50, 50, 100.0, 1.7799999999999998, 1, 3, 2.0, 2.0, 2.4499999999999957, 3.0, 10.256410256410257, 52.844551282051285, 2.4439102564102564], "isController": false}, {"data": ["GET /static/ - 正常(根)", 50, 0, 0.0, 52.06, 3, 104, 53.5, 101.8, 102.44999999999999, 104.0, 10.141987829614605, 5.229462474645031, 1.1687056288032456], "isController": false}, {"data": ["POST /cart - 缺少quantity", 50, 50, 100.0, 1.2000000000000002, 0, 3, 1.0, 2.0, 2.0, 3.0, 10.252204223908139, 41.54946047775272, 2.2126339194176747], "isController": false}, {"data": ["POST /cart - quantity超大值", 50, 50, 100.0, 1.2399999999999998, 0, 4, 1.0, 2.0, 3.0, 4.0, 10.254306808859722, 41.50791183859721, 2.413367129819524], "isController": false}, {"data": ["POST /cart - quantity=0", 50, 50, 100.0, 1.1800000000000004, 0, 3, 1.0, 2.0, 2.4499999999999957, 3.0, 10.254306808859722, 41.55798169606234, 2.3232413863822803], "isController": false}, {"data": ["GET /robots.txt - 正常", 50, 0, 0.0, 4.36, 2, 60, 3.0, 4.0, 6.8999999999999915, 60.0, 10.195758564437194, 2.2303221859706364, 1.2047722522430668], "isController": false}, {"data": ["POST /setCurrency - EUR", 50, 0, 0.0, 1.1400000000000003, 0, 3, 1.0, 2.0, 2.0, 3.0, 10.32844453625284, 2.219001755835571, 2.2593472423053087], "isController": false}, {"data": ["POST /cart/checkout - 空body", 50, 50, 100.0, 1.2200000000000002, 0, 7, 1.0, 2.0, 3.0, 7.0, 10.264832683227263, 45.68051029049476, 2.0850441387805376], "isController": false}, {"data": ["GET /cart - 正常", 50, 0, 0.0, 10.96, 7, 63, 8.0, 10.0, 46.94999999999995, 63.0, 10.187449062754686, 70.83779034229828, 1.1440982834148328], "isController": false}, {"data": ["GET /static/ - 路径穿越", 50, 50, 100.0, 71.40000000000002, 2, 142, 64.5, 124.9, 126.0, 142.0, 10.103051121438675, 4.46941616993332, 2.5454953020812288], "isController": false}, {"data": ["HEAD /_healthz - HEAD方法", 50, 0, 0.0, 15.48, 1, 66, 8.5, 43.49999999999999, 62.449999999999996, 66.0, 10.146103896103895, 1.9618443080357144, 1.1889965503246753], "isController": false}, {"data": ["POST /bot - 空body", 50, 50, 100.0, 4007.820000000001, 3999, 4021, 4008.0, 4014.9, 4018.45, 4021.0, 6.225874735400324, 32.333204924666916, 1.2038312476652968], "isController": false}, {"data": ["GET /product-meta/{ids} - 空ID", 50, 50, 100.0, 42.42, 1, 88, 56.0, 71.5, 85.89999999999999, 88.0, 10.227040294538762, 2.576734761709961, 1.238430660666803], "isController": false}, {"data": ["HEAD / - HEAD方法", 50, 0, 0.0, 28.619999999999997, 12, 55, 29.5, 37.0, 51.449999999999996, 55.0, 10.290183165260341, 1.7887232455237703, 1.1254887837003498], "isController": false}, {"data": ["POST /setCurrency - SQL注入", 50, 50, 100.0, 1.4199999999999995, 0, 9, 1.0, 2.0, 3.8999999999999915, 9.0, 10.330578512396695, 41.85700219524794, 2.4514947055785123], "isController": false}, {"data": ["POST /bot - XSS JSON", 50, 50, 100.0, 4027.62, 4003, 4099, 4012.0, 4095.9, 4098.0, 4099.0, 6.162948354492789, 32.00640561444595, 1.2939784142733886], "isController": false}, {"data": ["GET /static/ - 路径穿越-1", 50, 50, 100.0, 34.34, 1, 81, 31.5, 64.0, 66.89999999999999, 81.0, 10.156408693885842, 2.5589389092017063, 1.20012251167987], "isController": false}, {"data": ["GET /static/ - 路径穿越-0", 50, 0, 0.0, 36.919999999999995, 1, 69, 35.0, 62.0, 63.0, 69.0, 10.175010175010176, 1.9376240079365081, 1.3613050722425724], "isController": false}, {"data": ["GET /product/{id} - 不存在的ID", 50, 50, 100.0, 24.940000000000005, 2, 86, 25.0, 40.0, 60.74999999999985, 86.0, 10.252204223908139, 52.6226419930285, 1.291537446175928], "isController": false}, {"data": ["POST /cart/empty - 正常", 50, 0, 0.0, 5.1400000000000015, 2, 37, 4.0, 6.0, 15.749999999999936, 37.0, 10.195758564437194, 1.7225256168433931, 2.0411430719820554], "isController": false}, {"data": ["POST /cart/checkout - 已过期信用卡", 50, 50, 100.0, 1.1999999999999997, 0, 3, 1.0, 2.0, 3.0, 3.0, 10.266940451745379, 41.63926142197125, 4.612102156057495], "isController": false}, {"data": ["GET /static/ - 不存在的文件", 50, 50, 100.0, 32.22000000000001, 1, 72, 31.0, 64.9, 69.0, 72.0, 10.103051121438675, 2.5454953020812288, 1.4010090422307537], "isController": false}, {"data": ["GET /product-meta/{ids} - XSS注入", 50, 50, 100.0, 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0, 10.3498240529911, 12.199450812461187, 0.0], "isController": false}, {"data": ["GET /product/{id} - XSS注入ID", 50, 50, 100.0, 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0, 10.227040294538762, 12.00478753323788, 0.0], "isController": false}, {"data": ["POST /cart - quantity负数", 50, 50, 100.0, 1.1999999999999995, 0, 2, 1.0, 2.0, 2.0, 2.0, 10.254306808859722, 41.55798169606234, 2.3332553578753075], "isController": false}, {"data": ["GET / - 带SQL注入参数", 50, 50, 100.0, 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0, 10.317787866281469, 11.940018185101113, 0.0], "isController": false}, {"data": ["POST /cart/checkout - 完整正常", 50, 50, 100.0, 4.1000000000000005, 2, 30, 3.0, 5.0, 6.8999999999999915, 30.0, 10.199918400652795, 41.36744249796001, 4.581994594043247], "isController": false}, {"data": ["TRACE / - 非法方法", 50, 50, 100.0, 22.840000000000003, 1, 64, 21.0, 53.0, 61.0, 64.0, 10.271158586688578, 1.73526409716516, 1.1334383987263763], "isController": false}, {"data": ["POST /cart - quantity非数字", 50, 50, 100.0, 1.38, 1, 5, 1.0, 2.0, 3.0, 5.0, 10.258514567090685, 41.57503462248667, 2.3442308678703325], "isController": false}, {"data": ["POST /setCurrency - JPY", 50, 0, 0.0, 0.9799999999999999, 0, 2, 1.0, 1.8999999999999986, 2.0, 2.0, 10.32844453625284, 2.219001755835571, 2.2593472423053087], "isController": false}, {"data": ["GET /assistant - 正常", 50, 0, 0.0, 5.38, 3, 69, 4.0, 5.0, 6.0, 69.0, 10.18122581958868, 82.79205800753411, 1.1931124007330483], "isController": false}, {"data": ["POST /cart - 空body", 50, 50, 100.0, 1.4600000000000002, 1, 7, 1.0, 2.0, 3.4499999999999957, 7.0, 10.258514567090685, 42.04588441218712, 1.9935980457529752], "isController": false}, {"data": ["POST /_healthz - 错误方法", 50, 0, 0.0, 50.099999999999994, 0, 91, 61.0, 68.6, 79.19999999999993, 91.0, 10.17087062652563, 1.986498169243287, 2.0162956417819364], "isController": false}, {"data": ["GET /product-meta/{ids} - 有效ID", 50, 0, 0.0, 54.5, 3, 122, 45.0, 102.9, 108.94999999999996, 122.0, 10.123506782749544, 4.636645196396032, 1.3247557703988662], "isController": false}, {"data": ["POST /setCurrency - USD", 50, 0, 0.0, 4.539999999999999, 2, 63, 3.0, 4.899999999999999, 5.8999999999999915, 63.0, 10.197838058331634, 2.190941770344687, 2.230777075260045], "isController": false}, {"data": ["POST /setCurrency - 无效货币RMB", 50, 50, 100.0, 1.2400000000000004, 0, 6, 1.0, 2.0, 2.0, 6.0, 10.32844453625284, 41.84835584073539, 2.2593472423053087], "isController": false}, {"data": ["GET /product/{id} - SQL注入ID", 50, 50, 100.0, 23.279999999999998, 1, 47, 29.0, 41.699999999999996, 45.34999999999999, 47.0, 10.214504596527068, 52.60868871297242, 1.3466387895812055], "isController": false}, {"data": ["POST /cart/checkout - 缺少信用卡号", 50, 50, 100.0, 1.5200000000000005, 1, 8, 1.0, 2.0, 3.349999999999987, 8.0, 10.260619741432382, 41.58356633490663, 4.218477452288118], "isController": false}, {"data": ["HEAD /cart - HEAD方法", 50, 0, 0.0, 28.459999999999997, 20, 36, 29.0, 33.0, 34.89999999999999, 36.0, 10.271158586688578, 1.7854162387017254, 1.1635296836483155], "isController": false}, {"data": ["POST /cart/checkout - 缺少email", 50, 50, 100.0, 1.38, 1, 3, 1.0, 2.0, 2.4499999999999957, 3.0, 10.260619741432382, 42.044492612353785, 4.358759362815514], "isController": false}]}, function(index, item){
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
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": ["Non HTTP response code: java.net.URISyntaxException/Non HTTP response message: Illegal character in path at index 30: http://localhost/product-meta/&lt;script&gt;alert(1)&lt;/script&gt;", 50, 2.7027027027027026, 1.7241379310344827], "isController": false}, {"data": ["405/Method Not Allowed", 100, 5.405405405405405, 3.4482758620689653], "isController": false}, {"data": ["500/Internal Server Error", 450, 24.324324324324323, 15.517241379310345], "isController": false}, {"data": ["422/Unprocessable Entity", 950, 51.351351351351354, 32.758620689655174], "isController": false}, {"data": ["Non HTTP response code: java.net.URISyntaxException/Non HTTP response message: Illegal character in query at index 22: http://localhost/?q=1' OR '1'='1", 50, 2.7027027027027026, 1.7241379310344827], "isController": false}, {"data": ["404/Not Found", 200, 10.81081081081081, 6.896551724137931], "isController": false}, {"data": ["Non HTTP response code: java.net.URISyntaxException/Non HTTP response message: Illegal character in path at index 25: http://localhost/product/&lt;script&gt;alert(1)&lt;/script&gt;", 50, 2.7027027027027026, 1.7241379310344827], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 2900, 1850, "422/Unprocessable Entity", 950, "500/Internal Server Error", 450, "404/Not Found", 200, "405/Method Not Allowed", 100, "Non HTTP response code: java.net.URISyntaxException/Non HTTP response message: Illegal character in path at index 30: http://localhost/product-meta/&lt;script&gt;alert(1)&lt;/script&gt;", 50], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": ["POST /cart - 缺少product_id", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /setCurrency - XSS注入", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /bot - 无效JSON", 50, 50, "500/Internal Server Error", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["GET /cart/empty - 错误方法", 50, 50, "405/Method Not Allowed", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /cart/checkout - zip_code非数字", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /cart/checkout - 无效email格式", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /setCurrency - 缺少currency_code", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /bot - 正常JSON", 50, 50, "500/Internal Server Error", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /cart/checkout - XSS注入email", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["GET /product/{id} - 超长ID", 50, 50, "500/Internal Server Error", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["GET /product/{id} - 负数ID", 50, 50, "500/Internal Server Error", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /cart - SQL注入product_id", 50, 50, "500/Internal Server Error", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /cart - 缺少quantity", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /cart - quantity超大值", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /cart - quantity=0", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /cart/checkout - 空body", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["GET /static/ - 路径穿越", 50, 50, "404/Not Found", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /bot - 空body", 50, 50, "500/Internal Server Error", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["GET /product-meta/{ids} - 空ID", 50, 50, "404/Not Found", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /setCurrency - SQL注入", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /bot - XSS JSON", 50, 50, "500/Internal Server Error", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["GET /static/ - 路径穿越-1", 50, 50, "404/Not Found", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["GET /product/{id} - 不存在的ID", 50, 50, "500/Internal Server Error", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /cart/checkout - 已过期信用卡", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["GET /static/ - 不存在的文件", 50, 50, "404/Not Found", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["GET /product-meta/{ids} - XSS注入", 50, 50, "Non HTTP response code: java.net.URISyntaxException/Non HTTP response message: Illegal character in path at index 30: http://localhost/product-meta/&lt;script&gt;alert(1)&lt;/script&gt;", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["GET /product/{id} - XSS注入ID", 50, 50, "Non HTTP response code: java.net.URISyntaxException/Non HTTP response message: Illegal character in path at index 25: http://localhost/product/&lt;script&gt;alert(1)&lt;/script&gt;", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /cart - quantity负数", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["GET / - 带SQL注入参数", 50, 50, "Non HTTP response code: java.net.URISyntaxException/Non HTTP response message: Illegal character in query at index 22: http://localhost/?q=1' OR '1'='1", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /cart/checkout - 完整正常", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["TRACE / - 非法方法", 50, 50, "405/Method Not Allowed", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /cart - quantity非数字", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /cart - 空body", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /setCurrency - 无效货币RMB", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["GET /product/{id} - SQL注入ID", 50, 50, "500/Internal Server Error", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["POST /cart/checkout - 缺少信用卡号", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["POST /cart/checkout - 缺少email", 50, 50, "422/Unprocessable Entity", 50, "", "", "", "", "", "", "", ""], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
