
setTimeout(function(){

    var mydownload = d3.select("#download-button");

    mydownload.on("click", function() {

        var download_csv = d3.select("#downloadable-csv").text();

        download(download_csv, "crossref.csv", "text/csv");

    })

}, 3000);
