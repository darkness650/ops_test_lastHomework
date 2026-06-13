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

    var data = {"OkPercent": 81.42679127725857, "KoPercent": 18.573208722741434};
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
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.8126168224299065, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [1.0, 500, 1500, "ShippingService/GetQuote 获取运费报价"], "isController": false}, {"data": [1.0, 500, 1500, "CurrencyService/GetSupportedCurrencies 获取支持货币列表"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - CurrencyService (7000)"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - CartService (7070)"], "isController": false}, {"data": [1.0, 500, 1500, "ProductCatalogService/ListProducts 商品列表"], "isController": false}, {"data": [1.0, 500, 1500, "AdService/GetAds 获取广告"], "isController": false}, {"data": [0.994, 500, 1500, "CartService/GetCart 查看购物车"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - ShippingService (50052)"], "isController": false}, {"data": [1.0, 500, 1500, "RecommendationService/ListRecommendations 获取推荐"], "isController": false}, {"data": [1.0, 500, 1500, "CurrencyService/Convert 货币换算"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - ProductCatalogService (3550)"], "isController": false}, {"data": [1.0, 500, 1500, "PaymentService/Charge 信用卡扣款"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - PaymentService (50051)"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - RecommendationService (8080)"], "isController": false}, {"data": [0.13633333333333333, 500, 1500, "ProductCatalogService/GetProduct 商品详情"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - EmailService (5000)"], "isController": false}, {"data": [0.995, 500, 1500, "CartService/AddItem 添加商品到购物车"], "isController": false}, {"data": [0.995, 500, 1500, "CartService/EmptyCart 清空购物车"], "isController": false}, {"data": [1.0, 500, 1500, "ShippingService/ShipOrder 创建运单"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - CheckoutService (5050)"], "isController": false}, {"data": [1.0, 500, 1500, "EmailService/SendOrderConfirmation 发送订单确认邮件"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - AdService (9555)"], "isController": false}, {"data": [0.8665, 500, 1500, "ProductCatalogService/SearchProducts 搜索商品"], "isController": false}, {"data": [1.0, 500, 1500, "CheckoutService/PlaceOrder 提交订单"], "isController": false}]}, function(index, item){
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
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 16050, 2981, 18.573208722741434, 28.109408099688515, 0, 5003, 15.0, 53.0, 62.0, 95.0, 32.93881998986182, 19.374628668676515, 0.0], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["ShippingService/GetQuote 获取运费报价", 150, 0, 0.0, 28.073333333333334, 1, 101, 25.0, 61.900000000000006, 74.24999999999994, 94.88000000000011, 3.066167903354388, 0.27547602256699577, 0.0], "isController": false}, {"data": ["CurrencyService/GetSupportedCurrencies 获取支持货币列表", 600, 0, 0.0, 40.70666666666671, 1, 108, 42.0, 64.89999999999998, 71.94999999999993, 83.99000000000001, 8.534729235714998, 2.125347612409496, 0.0], "isController": false}, {"data": ["Health/Check - CurrencyService (7000)", 100, 0, 0.0, 20.44, 1, 104, 22.0, 38.900000000000006, 46.94999999999999, 103.47999999999973, 1.4270424545130218, 0.03483990367463432, 0.0], "isController": false}, {"data": ["Health/Check - CartService (7070)", 100, 0, 0.0, 19.410000000000018, 1, 82, 18.5, 46.900000000000006, 64.0, 81.96999999999998, 1.4436472303627885, 0.03524529371002901, 0.0], "isController": false}, {"data": ["ProductCatalogService/ListProducts 商品列表", 3000, 0, 0.0, 11.615333333333295, 1, 94, 6.0, 28.0, 32.0, 50.98999999999978, 23.67349515482466, 68.98604447460623, 0.0], "isController": false}, {"data": ["AdService/GetAds 获取广告", 600, 0, 0.0, 30.430000000000007, 1, 122, 27.0, 65.0, 76.0, 104.99000000000001, 8.479127215171985, 0.8694417554619711, 0.0], "isController": false}, {"data": ["CartService/GetCart 查看购物车", 1000, 0, 0.0, 44.38099999999993, 2, 851, 32.0, 65.0, 75.94999999999993, 572.7500000000002, 6.904932884052367, 0.22926534966580123, 0.0], "isController": false}, {"data": ["Health/Check - ShippingService (50052)", 100, 0, 0.0, 19.23999999999999, 1, 83, 18.5, 43.50000000000003, 48.94999999999999, 82.90999999999995, 1.4497165804085301, 0.03539347120138013, 0.0], "isController": false}, {"data": ["RecommendationService/ListRecommendations 获取推荐", 600, 0, 0.0, 32.7183333333334, 2, 120, 32.0, 58.89999999999998, 65.0, 92.91000000000008, 8.491246939613083, 0.754593233891397, 0.0], "isController": false}, {"data": ["CurrencyService/Convert 货币换算", 600, 0, 0.0, 41.78499999999999, 2, 123, 43.0, 66.89999999999998, 75.94999999999993, 89.99000000000001, 8.660758105026126, 0.5653738380149542, 0.0], "isController": false}, {"data": ["Health/Check - ProductCatalogService (3550)", 100, 0, 0.0, 22.130000000000003, 1, 123, 22.0, 52.80000000000001, 57.0, 122.82999999999991, 1.435152628482039, 0.03503790596879978, 0.0], "isController": false}, {"data": ["PaymentService/Charge 信用卡扣款", 150, 0, 0.0, 27.97333333333334, 2, 109, 25.0, 60.60000000000002, 68.24999999999994, 104.41000000000008, 3.1693711967545637, 0.19189552167849896, 0.0], "isController": false}, {"data": ["Health/Check - PaymentService (50051)", 100, 0, 0.0, 21.239999999999995, 1, 75, 22.0, 39.0, 50.849999999999966, 74.88999999999994, 1.4507260884072477, 0.03541811739275508, 0.0], "isController": false}, {"data": ["Health/Check - RecommendationService (8080)", 100, 0, 0.0, 23.1, 1, 88, 24.0, 47.0, 52.89999999999998, 87.73999999999987, 1.4273479874393378, 0.034847362974593205, 0.0], "isController": false}, {"data": ["ProductCatalogService/GetProduct 商品详情", 3000, 2591, 86.36666666666666, 4.068333333333325, 0, 89, 0.0, 15.0, 30.0, 57.0, 24.039424656436555, 1.4558172277535157, 0.0], "isController": false}, {"data": ["Health/Check - EmailService (5000)", 100, 0, 0.0, 18.63, 1, 80, 20.0, 33.0, 46.74999999999994, 79.75999999999988, 1.438993855496237, 0.0351316859252011, 0.0], "isController": false}, {"data": ["CartService/AddItem 添加商品到购物车", 1000, 0, 0.0, 45.08600000000004, 2, 791, 33.0, 63.0, 79.0, 536.2800000000007, 6.877011525871318, 0.020147494704701126, 0.0], "isController": false}, {"data": ["CartService/EmptyCart 清空购物车", 1000, 0, 0.0, 44.06000000000002, 2, 794, 33.0, 64.0, 77.0, 604.1600000000017, 6.858710562414266, 0.020093878600823043, 0.0], "isController": false}, {"data": ["ShippingService/ShipOrder 创建运单", 150, 0, 0.0, 28.833333333333325, 1, 94, 26.0, 64.60000000000002, 73.89999999999998, 91.45000000000005, 3.205539171688678, 0.12834678324144122, 0.0], "isController": false}, {"data": ["Health/Check - CheckoutService (5050)", 100, 0, 0.0, 19.91000000000001, 1, 93, 22.0, 36.900000000000006, 55.59999999999991, 92.8099999999999, 1.4438556721870084, 0.03525038262175313, 0.0], "isController": false}, {"data": ["EmailService/SendOrderConfirmation 发送订单确认邮件", 150, 0, 0.0, 10.60666666666667, 1, 106, 3.0, 38.80000000000001, 54.89999999999998, 91.72000000000025, 3.2059502436522185, 0.00939243235444986, 0.0], "isController": false}, {"data": ["Health/Check - AdService (9555)", 100, 0, 0.0, 21.26000000000001, 1, 72, 21.0, 42.0, 48.94999999999999, 71.97999999999999, 1.4370500237113255, 0.03508422909451478, 0.0], "isController": false}, {"data": ["ProductCatalogService/SearchProducts 搜索商品", 3000, 390, 13.0, 48.29333333333341, 0, 5003, 13.0, 45.0, 53.0, 79.98999999999978, 25.907854397858287, 0.5042839042057083, 0.0], "isController": false}, {"data": ["CheckoutService/PlaceOrder 提交订单", 150, 0, 0.0, 36.36666666666665, 6, 338, 30.0, 63.0, 72.44999999999999, 274.25000000000114, 3.1628220807152196, 1.3682911931219162, 0.0], "isController": false}]}, function(index, item){
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
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": [" 500/ 14 UNAVAILABLE", 2868, 96.20932572962093, 17.869158878504674], "isController": false}, {"data": [" 500/ 5 NOT_FOUND", 100, 3.354579000335458, 0.6230529595015576], "isController": false}, {"data": [" 500/ 4 DEADLINE_EXCEEDED", 13, 0.43609527004360954, 0.08099688473520249], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 16050, 2981, " 500/ 14 UNAVAILABLE", 2868, " 500/ 5 NOT_FOUND", 100, " 500/ 4 DEADLINE_EXCEEDED", 13, "", "", "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["ProductCatalogService/GetProduct 商品详情", 3000, 2591, " 500/ 14 UNAVAILABLE", 2491, " 500/ 5 NOT_FOUND", 100, "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["ProductCatalogService/SearchProducts 搜索商品", 3000, 390, " 500/ 14 UNAVAILABLE", 377, " 500/ 4 DEADLINE_EXCEEDED", 13, "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
