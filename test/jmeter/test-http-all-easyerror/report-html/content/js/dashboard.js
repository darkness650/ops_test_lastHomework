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
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 2900, 1850, 63.793103448275865, 275.35482758620697, 0, 4247, 5.0, 93.0, 3997.0, 4160.0, 34.10320334916976, 102.79977469101321, 6.867495825297521], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["POST /cart - 缺少product_id", 50, 50, 100.0, 1.9599999999999995, 1, 3, 2.0, 3.0, 3.0, 3.0, 10.168802115110841, 41.22138435529795, 2.0853988712629654], "isController": false}, {"data": ["POST /setCurrency - XSS注入", 50, 50, 100.0, 1.7199999999999998, 1, 5, 2.0, 2.0, 3.4499999999999957, 5.0, 10.245901639344261, 41.513912013319676, 2.601498463114754], "isController": false}, {"data": ["GET /product/{id} - 有效ID1", 50, 0, 0.0, 35.48, 10, 114, 18.5, 76.8, 94.69999999999997, 114.0, 10.185373803218578, 81.73523757384396, 1.283118379507028], "isController": false}, {"data": ["POST /bot - 无效JSON", 50, 50, 100.0, 4131.900000000001, 4022, 4213, 4130.0, 4164.9, 4175.95, 4213.0, 6.014675808973896, 31.23637300012029, 1.1336254210273065], "isController": false}, {"data": ["GET /product/{id} - 有效ID2", 50, 0, 0.0, 24.800000000000004, 7, 78, 27.0, 43.0, 59.149999999999885, 78.0, 10.252204223908139, 81.94354559667829, 1.291537446175928], "isController": false}, {"data": ["GET / - 正常", 50, 0, 0.0, 74.56, 16, 154, 74.0, 113.0, 124.44999999999999, 154.0, 10.256410256410257, 107.6923076923077, 1.1117788461538463], "isController": false}, {"data": ["GET /logout - 正常", 50, 0, 0.0, 51.88, 3, 104, 51.0, 75.39999999999999, 85.49999999999996, 104.0, 10.111223458038422, 1.7082438068756318, 1.1552862740141556], "isController": false}, {"data": ["GET /cart/empty - 错误方法", 50, 50, 100.0, 27.44, 1, 108, 29.0, 62.0, 64.44999999999999, 108.0, 10.080645161290322, 1.7030777469758065, 1.1911699848790323], "isController": false}, {"data": ["POST /cart/checkout - zip_code非数字", 50, 50, 100.0, 1.86, 1, 7, 2.0, 3.0, 5.0, 7.0, 10.32204789430223, 42.31636431668043, 4.636857452518579], "isController": false}, {"data": ["POST /cart/checkout - 无效email格式", 50, 50, 100.0, 1.6800000000000006, 1, 3, 2.0, 2.8999999999999986, 3.0, 3.0, 10.32204789430223, 42.26596369219653, 4.576376703137902], "isController": false}, {"data": ["GET /product-meta/{ids} - SQL注入", 50, 0, 0.0, 27.360000000000003, 2, 89, 16.0, 64.8, 67.89999999999999, 89.0, 10.183299389002038, 1.5613066446028512, 1.3922479633401221], "isController": false}, {"data": ["GET /_healthz - 正常", 50, 0, 0.0, 69.32000000000001, 3, 129, 77.0, 118.69999999999999, 124.89999999999999, 129.0, 10.197838058331634, 1.9917652457678974, 1.185100321231899], "isController": false}, {"data": ["POST /setCurrency - 缺少currency_code", 50, 50, 100.0, 2.1, 1, 11, 2.0, 3.8999999999999986, 4.449999999999996, 11.0, 10.252204223908139, 41.54946047775272, 2.0624551466065206], "isController": false}, {"data": ["POST /bot - 正常JSON", 50, 50, 100.0, 2494.8000000000006, 238, 4154, 2694.5, 3947.9, 4049.35, 4154.0, 6.13195977434388, 31.845470781211677, 1.1677071835908757], "isController": false}, {"data": ["POST /cart/checkout - XSS注入email", 50, 50, 100.0, 1.58, 1, 4, 1.0, 3.0, 3.0, 4.0, 10.326311441553077, 42.283421752375055, 4.850542776745147], "isController": false}, {"data": ["GET /product/{id} - 超长ID", 50, 50, 100.0, 3.5, 2, 12, 3.0, 5.0, 6.449999999999996, 12.0, 10.260619741432382, 57.57570413502975, 6.202464472604145], "isController": false}, {"data": ["GET /product/{id} - 负数ID", 50, 50, 100.0, 8.559999999999995, 1, 68, 3.0, 17.0, 59.24999999999998, 68.0, 10.273268954181221, 52.650503390178756, 1.2139311947811793], "isController": false}, {"data": ["POST /cart - 正常添加", 50, 0, 0.0, 20.160000000000004, 5, 61, 21.0, 37.699999999999996, 41.449999999999996, 61.0, 10.119409026512852, 1.7491556618093504, 2.292678607569318], "isController": false}, {"data": ["POST /cart - SQL注入product_id", 50, 50, 100.0, 2.7, 1, 9, 2.0, 4.0, 6.0, 9.0, 10.175010175010176, 52.42515008140008, 2.4245141432641435], "isController": false}, {"data": ["GET /static/ - 正常(根)", 50, 0, 0.0, 66.06000000000002, 6, 117, 62.5, 102.0, 105.79999999999998, 117.0, 10.068465565847765, 5.191552557390254, 1.1602333366894886], "isController": false}, {"data": ["POST /cart - 缺少quantity", 50, 50, 100.0, 1.8400000000000005, 1, 3, 2.0, 3.0, 3.0, 3.0, 10.17087062652563, 41.219837011798205, 2.1950804770138324], "isController": false}, {"data": ["POST /cart - quantity超大值", 50, 50, 100.0, 1.88, 1, 7, 2.0, 3.0, 3.4499999999999957, 7.0, 10.172939979654121, 41.17855099186165, 2.3942173194303153], "isController": false}, {"data": ["POST /cart - quantity=0", 50, 50, 100.0, 1.68, 1, 4, 2.0, 2.0, 3.0, 4.0, 10.172939979654121, 41.228223550356056, 2.3048067141403865], "isController": false}, {"data": ["GET /robots.txt - 正常", 50, 0, 0.0, 52.13999999999999, 25, 105, 50.0, 80.8, 98.89999999999999, 105.0, 10.094891984655765, 2.2082576216434484, 1.1928534474056127], "isController": false}, {"data": ["POST /setCurrency - EUR", 50, 0, 0.0, 2.0200000000000005, 1, 8, 2.0, 4.0, 5.0, 8.0, 10.252204223908139, 2.2026220012302646, 2.242669673979906], "isController": false}, {"data": ["POST /cart/checkout - 空body", 50, 50, 100.0, 2.04, 1, 5, 2.0, 3.0, 3.8999999999999915, 5.0, 10.326311441553077, 45.954102772614625, 2.0975320115654688], "isController": false}, {"data": ["GET /cart - 正常", 50, 0, 0.0, 56.519999999999996, 11, 128, 57.5, 72.9, 95.29999999999994, 128.0, 10.07658202337767, 70.03106421301895, 1.131647395203547], "isController": false}, {"data": ["GET /static/ - 路径穿越", 50, 50, 100.0, 84.26000000000002, 5, 127, 89.0, 126.0, 127.0, 127.0, 9.940357852882704, 4.397443464214711, 2.5045042246520874], "isController": false}, {"data": ["HEAD /_healthz - HEAD方法", 50, 0, 0.0, 41.42, 1, 84, 39.5, 72.69999999999999, 78.44999999999999, 84.0, 10.38637307852098, 2.0083026069796426, 1.2171530951391774], "isController": false}, {"data": ["POST /bot - 空body", 50, 50, 100.0, 4032.720000000001, 3993, 4178, 4006.0, 4134.4, 4161.35, 4178.0, 6.035731530661517, 31.34572292974408, 1.167065276436504], "isController": false}, {"data": ["GET /product-meta/{ids} - 空ID", 50, 50, 100.0, 46.79999999999999, 1, 84, 60.5, 65.9, 70.24999999999997, 84.0, 10.150223304912707, 2.5573804811205845, 1.2291286033292732], "isController": false}, {"data": ["HEAD / - HEAD方法", 50, 0, 0.0, 51.17999999999999, 12, 193, 41.0, 95.69999999999999, 137.34999999999974, 193.0, 10.421008753647353, 1.8114644122551062, 1.1397978324301792], "isController": false}, {"data": ["POST /setCurrency - SQL注入", 50, 50, 100.0, 2.7199999999999998, 1, 39, 2.0, 3.0, 7.249999999999979, 39.0, 10.248001639680261, 41.52242070608732, 2.4318988266038124], "isController": false}, {"data": ["POST /bot - XSS JSON", 50, 50, 100.0, 4106.78, 3985, 4247, 4095.0, 4183.0, 4191.45, 4247.0, 6.110228522546743, 31.732612580960527, 1.282909308933154], "isController": false}, {"data": ["GET /static/ - 路径穿越-1", 50, 50, 100.0, 46.72, 1, 88, 58.5, 72.6, 74.89999999999999, 88.0, 10.0, 2.51953125, 1.181640625], "isController": false}, {"data": ["GET /static/ - 路径穿越-0", 50, 0, 0.0, 37.400000000000006, 2, 68, 38.0, 63.9, 65.44999999999999, 68.0, 10.062386798148522, 1.9161771734755484, 1.3462372962366673], "isController": false}, {"data": ["GET /product/{id} - 不存在的ID", 50, 50, 100.0, 24.820000000000007, 2, 91, 23.0, 60.9, 74.89999999999999, 91.0, 10.273268954181221, 52.73076330388329, 1.29419110848572], "isController": false}, {"data": ["POST /cart/empty - 正常", 50, 0, 0.0, 50.739999999999995, 4, 95, 50.5, 88.8, 93.44999999999999, 95.0, 10.084711577248891, 1.7037647488906817, 2.0189119856797095], "isController": false}, {"data": ["POST /cart/checkout - 已过期信用卡", 50, 50, 100.0, 1.7800000000000005, 1, 4, 2.0, 3.0, 3.4499999999999957, 4.0, 10.324179227751394, 41.87140266880033, 4.637814887466447], "isController": false}, {"data": ["GET /static/ - 不存在的文件", 50, 50, 100.0, 28.68, 1, 87, 22.0, 63.0, 65.89999999999999, 87.0, 10.084711577248891, 2.5408745966115367, 1.398465863251311], "isController": false}, {"data": ["GET /product-meta/{ids} - XSS注入", 50, 50, 100.0, 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0, 10.187449062754686, 12.008057635493072, 0.0], "isController": false}, {"data": ["GET /product/{id} - XSS注入ID", 50, 50, 100.0, 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0, 10.395010395010395, 12.201955561330562, 0.0], "isController": false}, {"data": ["POST /cart - quantity负数", 50, 50, 100.0, 1.8399999999999999, 1, 4, 2.0, 3.0, 3.0, 4.0, 10.172939979654121, 41.228223550356056, 2.3147412258392674], "isController": false}, {"data": ["GET / - 带SQL注入参数", 50, 50, 100.0, 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0, 10.656436487638533, 12.331911365089514, 0.0], "isController": false}, {"data": ["POST /cart/checkout - 完整正常", 50, 50, 100.0, 16.62, 3, 60, 15.0, 35.8, 42.39999999999995, 60.0, 10.195758564437194, 41.35057159971452, 4.580125917618271], "isController": false}, {"data": ["TRACE / - 非法方法", 50, 50, 100.0, 22.34, 1, 71, 12.5, 64.8, 70.44999999999999, 71.0, 10.649627263045794, 1.7992046059637912, 1.1752030085197018], "isController": false}, {"data": ["POST /cart - quantity非数字", 50, 50, 100.0, 1.7799999999999998, 1, 4, 2.0, 3.0, 3.4499999999999957, 4.0, 10.172939979654121, 41.228223550356056, 2.3246757375381484], "isController": false}, {"data": ["POST /setCurrency - JPY", 50, 0, 0.0, 1.7400000000000004, 1, 5, 1.0, 3.0, 4.449999999999996, 5.0, 10.252204223908139, 2.2026220012302646, 2.242669673979906], "isController": false}, {"data": ["GET /assistant - 正常", 50, 0, 0.0, 51.660000000000004, 27, 106, 52.0, 66.8, 69.44999999999999, 106.0, 10.13993104846887, 82.45625570371121, 1.1882731697424458], "isController": false}, {"data": ["POST /cart - 空body", 50, 50, 100.0, 1.9200000000000002, 1, 7, 2.0, 3.0, 4.8999999999999915, 7.0, 10.172939979654121, 41.69514560020346, 1.9769678280773144], "isController": false}, {"data": ["POST /_healthz - 错误方法", 50, 0, 0.0, 30.740000000000006, 1, 84, 30.0, 63.0, 65.0, 84.0, 10.32204789430223, 2.016024979355904, 2.0462653540462425], "isController": false}, {"data": ["GET /product-meta/{ids} - 有效ID", 50, 0, 0.0, 49.02000000000001, 3, 122, 39.0, 102.9, 114.69999999999997, 122.0, 10.135819987837015, 4.642284740523008, 1.3263670687208595], "isController": false}, {"data": ["POST /setCurrency - USD", 50, 0, 0.0, 5.1, 3, 30, 4.0, 6.0, 12.14999999999997, 30.0, 10.193679918450561, 2.1900484199796124, 2.22986748216106], "isController": false}, {"data": ["POST /setCurrency - 无效货币RMB", 50, 50, 100.0, 1.7200000000000002, 1, 6, 2.0, 3.0, 3.0, 6.0, 10.25010250102501, 41.53093288745387, 2.242209922099221], "isController": false}, {"data": ["GET /product/{id} - SQL注入ID", 50, 50, 100.0, 22.16, 2, 75, 22.0, 35.8, 37.449999999999996, 75.0, 10.235414534288639, 52.71638306038895, 1.3493954708290687], "isController": false}, {"data": ["POST /cart/checkout - 缺少信用卡号", 50, 50, 100.0, 1.9199999999999997, 1, 6, 2.0, 3.0, 4.0, 6.0, 10.319917440660475, 41.82388415892673, 4.242856682146543], "isController": false}, {"data": ["HEAD /cart - HEAD方法", 50, 0, 0.0, 36.35999999999999, 14, 99, 30.5, 62.29999999999999, 79.04999999999995, 99.0, 10.201999591920016, 1.7733944603142218, 1.1556952662721893], "isController": false}, {"data": ["POST /cart/checkout - 缺少email", 50, 50, 100.0, 2.1, 1, 8, 2.0, 3.0, 4.449999999999996, 8.0, 10.317787866281469, 42.27874793644243, 4.383044650226991], "isController": false}]}, function(index, item){
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
