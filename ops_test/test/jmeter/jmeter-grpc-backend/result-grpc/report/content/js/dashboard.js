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

    var data = {"OkPercent": 84.0, "KoPercent": 16.0};
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
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.84, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [1.0, 500, 1500, "Health/Check - RecommendationService (30083)"], "isController": false}, {"data": [1.0, 500, 1500, "ShippingService/GetQuote 获取运费报价"], "isController": false}, {"data": [1.0, 500, 1500, "CurrencyService/GetSupportedCurrencies 获取支持货币列表"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - CurrencyService (30088)"], "isController": false}, {"data": [1.0, 500, 1500, "ProductCatalogService/ListProducts 商品列表"], "isController": false}, {"data": [1.0, 500, 1500, "AdService/GetAds 获取广告"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - ProductCatalogService (30085)"], "isController": false}, {"data": [1.0, 500, 1500, "CartService/GetCart 查看购物车"], "isController": false}, {"data": [1.0, 500, 1500, "RecommendationService/ListRecommendations 获取推荐"], "isController": false}, {"data": [1.0, 500, 1500, "CurrencyService/Convert 货币换算"], "isController": false}, {"data": [1.0, 500, 1500, "PaymentService/Charge 信用卡扣款"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - CartService (30086)"], "isController": false}, {"data": [0.144, 500, 1500, "ProductCatalogService/GetProduct 商品详情"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - AdService (30090)"], "isController": false}, {"data": [1.0, 500, 1500, "CartService/AddItem 添加商品到购物车"], "isController": false}, {"data": [1.0, 500, 1500, "CartService/EmptyCart 清空购物车"], "isController": false}, {"data": [1.0, 500, 1500, "ShippingService/ShipOrder 创建运单"], "isController": false}, {"data": [1.0, 500, 1500, "EmailService/SendOrderConfirmation 发送订单确认邮件"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - PaymentService (30084)"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - EmailService (30081)"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - ShippingService (30089)"], "isController": false}, {"data": [1.0, 500, 1500, "ProductCatalogService/SearchProducts 搜索商品"], "isController": false}, {"data": [1.0, 500, 1500, "CheckoutService/PlaceOrder 提交订单"], "isController": false}, {"data": [1.0, 500, 1500, "Health/Check - CheckoutService (30082)"], "isController": false}]}, function(index, item){
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
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 16050, 2568, 16.0, 4.687476635514029, 0, 415, 2.0, 5.0, 12.0, 63.0, 34.74544899562922, 20.44461608578987, 0.0], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["Health/Check - RecommendationService (30083)", 100, 0, 0.0, 4.559999999999999, 1, 54, 3.0, 9.900000000000006, 12.0, 53.97999999999999, 1.5154959460483441, 0.036999412745320905, 0.0], "isController": false}, {"data": ["ShippingService/GetQuote 获取运费报价", 150, 0, 0.0, 20.9, 1, 415, 3.0, 66.0, 79.0, 411.94000000000005, 2.9955067398901645, 0.269127558662007, 0.0], "isController": false}, {"data": ["CurrencyService/GetSupportedCurrencies 获取支持货币列表", 600, 0, 0.0, 4.88833333333334, 1, 70, 3.0, 5.0, 12.0, 58.99000000000001, 8.980153859969468, 2.2362687834884905, 0.0], "isController": false}, {"data": ["Health/Check - CurrencyService (30088)", 100, 0, 0.0, 5.8100000000000005, 2, 67, 3.0, 10.800000000000011, 26.349999999999852, 66.89999999999995, 1.493205913095416, 0.03645522248768105, 0.0], "isController": false}, {"data": ["ProductCatalogService/ListProducts 商品列表", 3000, 0, 0.0, 3.4086666666666607, 1, 75, 2.0, 3.0, 5.0, 56.0, 26.96726174424249, 78.58428617658163, 0.0], "isController": false}, {"data": ["AdService/GetAds 获取广告", 600, 0, 0.0, 5.553333333333327, 2, 66, 3.0, 5.0, 14.0, 61.97000000000003, 9.000090000900009, 0.9228607911079111, 0.0], "isController": false}, {"data": ["Health/Check - ProductCatalogService (30085)", 100, 0, 0.0, 5.1000000000000005, 1, 63, 2.0, 10.400000000000034, 13.0, 62.909999999999954, 1.4872763508187457, 0.036310457783660786, 0.0], "isController": false}, {"data": ["CartService/GetCart 查看购物车", 1000, 0, 0.0, 5.778000000000003, 1, 133, 3.0, 5.0, 13.0, 65.98000000000002, 7.277331839054528, 0.24163015871860738, 0.0], "isController": false}, {"data": ["RecommendationService/ListRecommendations 获取推荐", 600, 0, 0.0, 5.558333333333336, 2, 68, 3.5, 6.0, 11.0, 60.98000000000002, 9.057697533287039, 0.8049321050089067, 0.0], "isController": false}, {"data": ["CurrencyService/Convert 货币换算", 600, 0, 0.0, 4.960000000000009, 1, 63, 3.0, 5.0, 11.0, 59.99000000000001, 8.971023593792053, 0.5859783835710655, 0.0], "isController": false}, {"data": ["PaymentService/Charge 信用卡扣款", 150, 0, 0.0, 19.113333333333333, 2, 210, 4.0, 68.9, 79.0, 182.4600000000005, 2.9567137112670503, 0.1790197754868722, 0.0], "isController": false}, {"data": ["Health/Check - CartService (30086)", 100, 0, 0.0, 6.81, 1, 217, 3.0, 10.0, 11.949999999999989, 215.50999999999925, 1.4933843075176967, 0.036459577820256266, 0.0], "isController": false}, {"data": ["ProductCatalogService/GetProduct 商品详情", 3000, 2568, 85.6, 1.763000000000002, 0, 70, 0.0, 2.0, 3.0, 54.0, 26.833871501534006, 1.679527824488591, 0.0], "isController": false}, {"data": ["Health/Check - AdService (30090)", 100, 0, 0.0, 5.310000000000001, 1, 60, 3.0, 12.0, 14.0, 59.97999999999999, 1.5273471507338903, 0.03728874879721412, 0.0], "isController": false}, {"data": ["CartService/AddItem 添加商品到购物车", 1000, 0, 0.0, 6.77899999999999, 2, 248, 3.0, 6.0, 13.949999999999932, 66.98000000000002, 7.313790884091042, 0.021427121730735472, 0.0], "isController": false}, {"data": ["CartService/EmptyCart 清空购物车", 1000, 0, 0.0, 5.551999999999995, 1, 127, 3.0, 5.0, 13.0, 64.0, 7.158093656497401, 0.020970977509269732, 0.0], "isController": false}, {"data": ["ShippingService/ShipOrder 创建运单", 150, 0, 0.0, 16.200000000000006, 1, 141, 3.0, 65.9, 85.44999999999999, 124.68000000000029, 2.9627873903768664, 0.11862722949751126, 0.0], "isController": false}, {"data": ["EmailService/SendOrderConfirmation 发送订单确认邮件", 150, 0, 0.0, 15.873333333333342, 1, 126, 3.0, 62.0, 73.34999999999997, 125.49000000000001, 3.0241935483870965, 0.008859942036290322, 0.0], "isController": false}, {"data": ["Health/Check - PaymentService (30084)", 100, 0, 0.0, 5.590000000000001, 2, 66, 3.0, 10.700000000000017, 12.949999999999989, 65.93999999999997, 1.480691779199242, 0.03614970164060649, 0.0], "isController": false}, {"data": ["Health/Check - EmailService (30081)", 100, 0, 0.0, 5.370000000000001, 2, 61, 3.0, 9.900000000000006, 15.849999999999966, 60.969999999999985, 1.4855750661080904, 0.03626892251240456, 0.0], "isController": false}, {"data": ["Health/Check - ShippingService (30089)", 100, 0, 0.0, 6.680000000000004, 1, 72, 2.0, 8.600000000000023, 53.94999999999999, 71.93999999999997, 1.4835474586832031, 0.03621942037800789, 0.0], "isController": false}, {"data": ["ProductCatalogService/SearchProducts 搜索商品", 3000, 0, 0.0, 3.2176666666666596, 0, 91, 2.0, 3.0, 6.0, 54.0, 26.85789487819945, 0.4983398463728413, 0.0], "isController": false}, {"data": ["CheckoutService/PlaceOrder 提交订单", 150, 0, 0.0, 22.793333333333344, 7, 217, 10.0, 69.9, 79.44999999999999, 185.38000000000056, 3.053124363932424, 1.3208340754121717, 0.0], "isController": false}, {"data": ["Health/Check - CheckoutService (30082)", 100, 0, 0.0, 6.259999999999999, 1, 67, 2.0, 8.600000000000023, 56.799999999999955, 66.96999999999998, 1.4759494044544152, 0.03603392100718787, 0.0], "isController": false}]}, function(index, item){
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
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": [" 500/ 14 UNAVAILABLE", 2468, 96.10591900311526, 15.376947040498443], "isController": false}, {"data": [" 500/ 5 NOT_FOUND", 100, 3.8940809968847354, 0.6230529595015576], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 16050, 2568, " 500/ 14 UNAVAILABLE", 2468, " 500/ 5 NOT_FOUND", 100, "", "", "", "", "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["ProductCatalogService/GetProduct 商品详情", 3000, 2568, " 500/ 14 UNAVAILABLE", 2468, " 500/ 5 NOT_FOUND", 100, "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
