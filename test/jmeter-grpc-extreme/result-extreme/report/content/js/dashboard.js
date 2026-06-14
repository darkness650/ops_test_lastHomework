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

    var data = {"OkPercent": 81.3941935483871, "KoPercent": 18.605806451612903};
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
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.7967774193548387, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [0.99625, 500, 1500, "CartService/GetCart"], "isController": false}, {"data": [0.9959, 500, 1500, "CartService/EmptyCart"], "isController": false}, {"data": [0.7847, 500, 1500, "PaymentService/Charge"], "isController": false}, {"data": [0.03345, 500, 1500, "ProductCatalogService/GetProduct"], "isController": false}, {"data": [0.7477, 500, 1500, "CheckoutService/PlaceOrder"], "isController": false}, {"data": [0.7253, 500, 1500, "CurrencyService/Convert"], "isController": false}, {"data": [0.99875, 500, 1500, "ShippingService/GetQuote"], "isController": false}, {"data": [0.9553, 500, 1500, "EmailService/SendOrderConfirmation"], "isController": false}, {"data": [0.693975, 500, 1500, "AdService/GetAds"], "isController": false}, {"data": [0.9998, 500, 1500, "ProductCatalogService/SearchProducts"], "isController": false}, {"data": [0.70335, 500, 1500, "RecommendationService/ListRecommendations"], "isController": false}, {"data": [0.9992, 500, 1500, "ProductCatalogService/ListProducts"], "isController": false}, {"data": [0.4519, 500, 1500, "CurrencyService/GetSupportedCurrencies"], "isController": false}, {"data": [0.94545, 500, 1500, "CartService/AddItem"], "isController": false}, {"data": [0.9989, 500, 1500, "ShippingService/ShipOrder"], "isController": false}]}, function(index, item){
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
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 155000, 28839, 18.605806451612903, 91.56454838709553, 0, 8213, 7.0, 68.0, 80.0, 348.9900000000016, 981.8204852093495, 434.73626069907203, 0.0], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["CartService/GetCart", 10000, 0, 0.0, 26.774600000000092, 1, 1714, 9.0, 61.0, 69.0, 225.9499999999989, 135.77916875992884, 4.508292712732013, 0.0], "isController": false}, {"data": ["CartService/EmptyCart", 10000, 0, 0.0, 27.20520000000005, 1, 1713, 9.0, 62.0, 70.0, 287.679999999993, 152.571594220588, 0.4469870924431289, 0.0], "isController": false}, {"data": ["PaymentService/Charge", 10000, 2055, 20.55, 88.08789999999979, 0, 3082, 42.0, 173.0, 230.0, 1031.0, 80.11985930952706, 4.25125831994664, 0.0], "isController": false}, {"data": ["ProductCatalogService/GetProduct", 10000, 9665, 96.65, 1.2633999999999987, 0, 502, 0.0, 1.0, 1.0, 46.98999999999978, 147.58187104296107, 4.810707802653522, 0.0], "isController": false}, {"data": ["CheckoutService/PlaceOrder", 5000, 0, 0.0, 627.1101999999994, 6, 8213, 453.0, 1274.0, 1563.749999999999, 6880.0, 33.53341604909292, 14.507132138425943, 0.0], "isController": false}, {"data": ["CurrencyService/Convert", 10000, 2547, 25.47, 162.9707, 0, 3236, 97.0, 349.0, 446.0, 1119.9799999999996, 149.2492761410107, 6.889340756619206, 0.0], "isController": false}, {"data": ["ShippingService/GetQuote", 10000, 0, 0.0, 31.638600000000007, 1, 1308, 14.0, 72.0, 83.0, 196.98999999999978, 66.29233594304162, 5.955952057382646, 0.0], "isController": false}, {"data": ["EmailService/SendOrderConfirmation", 10000, 0, 0.0, 201.8557000000003, 1, 1480, 143.5, 462.0, 600.9499999999989, 766.0, 69.93496048674733, 0.20488757955101755, 0.0], "isController": false}, {"data": ["AdService/GetAds", 20000, 5889, 29.445, 101.61344999999983, 0, 3037, 55.0, 195.0, 284.0, 1384.0, 168.90180049319326, 26.64020142595345, 0.0], "isController": false}, {"data": ["ProductCatalogService/SearchProducts", 10000, 0, 0.0, 18.39649999999987, 1, 1658, 6.0, 62.0, 69.0, 81.0, 161.9852917355104, 471.87707543655034, 0.0], "isController": false}, {"data": ["RecommendationService/ListRecommendations", 10000, 2858, 28.58, 140.03859999999983, 0, 3015, 53.0, 358.0, 385.0, 706.909999999998, 70.8707176368868, 4.983360330647333, 0.0], "isController": false}, {"data": ["ProductCatalogService/ListProducts", 10000, 0, 0.0, 18.727600000000116, 1, 1952, 6.0, 62.0, 69.0, 85.98999999999978, 65.2375298461699, 190.1062393173545, 0.0], "isController": false}, {"data": ["CurrencyService/GetSupportedCurrencies", 10000, 5325, 53.25, 121.46680000000005, 0, 3236, 1.0, 279.0, 380.0, 1640.2399999999834, 66.39929882340442, 8.58151930103118, 0.0], "isController": false}, {"data": ["CartService/AddItem", 10000, 500, 5.0, 32.48619999999996, 0, 3015, 10.0, 67.0, 74.0, 486.79999999999563, 63.35569789469016, 0.25036018704185914, 0.0], "isController": false}, {"data": ["ShippingService/ShipOrder", 10000, 0, 0.0, 31.5566999999999, 1, 1287, 14.0, 72.0, 85.0, 205.0, 150.2900598154438, 6.017473098079293, 0.0], "isController": false}]}, function(index, item){
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
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": [" 500/ 14 UNAVAILABLE", 28500, 98.82450847810257, 18.387096774193548], "isController": false}, {"data": [" 500/ 5 NOT_FOUND", 100, 0.3467526613266757, 0.06451612903225806], "isController": false}, {"data": [" 500/ 4 DEADLINE_EXCEEDED", 239, 0.8287388605707549, 0.15419354838709678], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 155000, 28839, " 500/ 14 UNAVAILABLE", 28500, " 500/ 4 DEADLINE_EXCEEDED", 239, " 500/ 5 NOT_FOUND", 100, "", "", "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["PaymentService/Charge", 10000, 2055, " 500/ 14 UNAVAILABLE", 2028, " 500/ 4 DEADLINE_EXCEEDED", 27, "", "", "", "", "", ""], "isController": false}, {"data": ["ProductCatalogService/GetProduct", 10000, 9665, " 500/ 14 UNAVAILABLE", 9565, " 500/ 5 NOT_FOUND", 100, "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["CurrencyService/Convert", 10000, 2547, " 500/ 14 UNAVAILABLE", 2520, " 500/ 4 DEADLINE_EXCEEDED", 27, "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["AdService/GetAds", 20000, 5889, " 500/ 14 UNAVAILABLE", 5808, " 500/ 4 DEADLINE_EXCEEDED", 81, "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["RecommendationService/ListRecommendations", 10000, 2858, " 500/ 14 UNAVAILABLE", 2822, " 500/ 4 DEADLINE_EXCEEDED", 36, "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["CurrencyService/GetSupportedCurrencies", 10000, 5325, " 500/ 14 UNAVAILABLE", 5262, " 500/ 4 DEADLINE_EXCEEDED", 63, "", "", "", "", "", ""], "isController": false}, {"data": ["CartService/AddItem", 10000, 500, " 500/ 14 UNAVAILABLE", 495, " 500/ 4 DEADLINE_EXCEEDED", 5, "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
