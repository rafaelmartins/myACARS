$(function () {
    // Media fluid width.
    // based on http://css-tricks.com/fluid-width-youtube-videos/
    var $container = $("article"),
        $elements = $("article iframe, article img");
    $elements.each(function() {
        $(this).data('ratio', this.width / this.height)
               .removeAttr('height')
               .removeAttr('width');
    });
    $(window).resize(function() {
        var container_width = $container.width();
        $elements.each(function() {
            $(this).width(container_width)
                   .height(container_width / $(this).data('ratio'));
        });
    }).resize();
});

var plane_svg = "M 0,0 " +
    "M 1.9565564,41.694305 C 1.7174505,40.497708 1.6419973,38.448747 " +
    "1.8096508,37.70494 1.8936398,37.332056 2.0796653,36.88191 " +
    "2.222907,36.70461 2.4497603,36.423844 4.087816,35.47248 " +
    "14.917931,29.331528 l 12.434577,-7.050718 -0.04295,-7.613412 c " +
    "-0.03657,-6.4844888 -0.01164,-7.7625804 0.168134,-8.6194061 " +
    "0.276129,-1.3160905 0.762276,-2.5869575 1.347875,-3.5235502 l " +
    "0.472298,-0.7553719 1.083746,-0.6085497 c 1.194146,-0.67053522 " +
    "1.399524,-0.71738842 2.146113,-0.48960552 1.077005,0.3285939 2.06344," +
    "1.41299352 2.797602,3.07543322 0.462378,1.0469993 0.978731,2.7738408 " +
    "1.047635,3.5036272 0.02421,0.2570284 0.06357,3.78334 0.08732,7.836246 " +
    "0.02375,4.052905 0.0658,7.409251 0.09345,7.458546 0.02764,0.04929 " +
    "5.600384,3.561772 12.38386,7.805502 l 12.333598,7.715871 " +
    "0.537584,0.959688 c 0.626485,1.118378 0.651686,1.311286 " +
    "0.459287,3.516442 -0.175469,2.011604 -0.608966,2.863924 " +
    "-1.590344,3.127136 -0.748529,0.200763 -1.293144,0.03637 " +
    "-10.184829,-3.07436 C 48.007733,41.72562 44.793806,40.60197 " +
    "43.35084,40.098045 l -2.623567,-0.916227 -1.981212,-0.06614 c " +
    "-1.089663,-0.03638 -1.985079,-0.05089 -1.989804,-0.03225 " +
    "-0.0052,0.01863 -0.02396,2.421278 -0.04267,5.339183 -0.0395,6.147742 " +
    "-0.143635,7.215456 -0.862956,8.845475 l -0.300457,0.680872 " +
    "2.91906,1.361455 c 2.929379,1.366269 3.714195,1.835385 4.04589,2.41841 " +
    "0.368292,0.647353 0.594634,2.901439 0.395779,3.941627 -0.0705,0.368571 " +
    "-0.106308,0.404853 -0.765159,0.773916 L 41.4545,62.83158 " +
    "39.259237,62.80426 c -6.030106,-0.07507 -16.19508,-0.495041 " +
    "-16.870991,-0.697033 -0.359409,-0.107405 -0.523792,-0.227482 " +
    "-0.741884,-0.541926 -0.250591,-0.361297 -0.28386,-0.522402 -0.315075," +
    "-1.52589 -0.06327,-2.03378 0.23288,-3.033615 1.077963,-3.639283 " +
    "0.307525,-0.2204 4.818478,-2.133627 6.017853,-2.552345 " +
    "0.247872,-0.08654 0.247455,-0.102501 -0.01855,-0.711959 " +
    "-0.330395,-0.756986 -0.708622,-2.221756 -0.832676,-3.224748 " +
    "-0.05031,-0.406952 -0.133825,-3.078805 -0.185533,-5.937448 -0.0517," +
    "-2.858644 -0.145909,-5.208974 -0.209316,-5.222958 -0.06341,-0.01399 " +
    "-0.974464,-0.0493 -2.024551,-0.07845 L 23.247235,38.61921 " +
    "18.831373,39.8906 C 4.9432155,43.88916 4.2929558,44.057819 " +
    "3.4954426,43.86823 2.7487826,43.690732 2.2007966,42.916622 " +
    "1.9565564,41.694305 z";

function get_plane_icon(data) {
    var r = 255, g = 255, b = 0;
    var maxalt = 45000;
    var invalt = maxalt - data.altitude;

    if (invalt < 0) {
        invalt = 0;
    }
    var b = parseInt(255 / maxalt * invalt);

    return new ol.style.Icon({
        anchor: [32, 32],
        anchorXUnits: 'pixels',
        anchorYUnits: 'pixels',
        scale: 0.4,
        imgSize: [64, 64],
        src: "data:image/svg+xml;base64," + window.btoa(
            '<svg width="64px" height="64px" version="1.1" ' +
            'xmlns="http://www.w3.org/2000/svg">' +
            '<path d="' + plane_svg + '" stroke="#000000" ' +
            'stroke-width="2.5" fill="rgb(255,255,' + b + ')"/></svg>'
        ),
        rotation: data.heading * Math.PI / 180.0,
        opacity: 0.9,
        rotateWithView: true
    });
}

var map = null;
var source = null;
var plane = null;
var route = null;

var chart = null;
var altitude_list = [];
var ground_speed_list = [];

function initialize_flight(geojson_url, data) {
    source = new ol.source.Vector({
        format: new ol.format.GeoJSON(),
        url: geojson_url
    })

    var view = new ol.View({
        center: [0, 0],
        zoom: 5,
        maxZoom: 18
    })

    map = new ol.Map({
        target: 'map',
        interactions: ol.interaction.defaults({
            mouseWheelZoom: false
        }),
        layers: [
            new ol.layer.Tile({
                source: new ol.source.OSM(),
                name: 'osm',
                title: 'OpenStreetMap',
                type: 'base'
            }),
            new ol.layer.Vector({
                source: source,
                style: function(feature) {
                    switch (feature.getGeometry().getType()) {
                    case 'Point':
                        switch (feature.get('type')) {
                        case 'airport-origin':
                            var color = 'green';
                            break;
                        case 'airport-destination':
                            var color = 'red';
                            break;
                        case 'plane':
                            return new ol.style.Style({
                                image: get_plane_icon(data)
                            });
                        default:
                            var color = 'black';
                        }
                        return new ol.style.Style({
                            image: new ol.style.Circle({
                                radius: 3,
                                fill: new ol.style.Fill({
                                    color: color,
                                }),
                                stroke: new ol.style.Stroke({
                                    color: 'black',
                                    width: 1
                                })
                            })
                        });
                    case 'LineString':
                        return new ol.style.Style({
                            stroke: new ol.style.Stroke({
                                color: '#000033',
                                width: 2
                            })
                        });
                    }
                }
            })
        ],
        view: view,
        controls: [
            new ol.control.Zoom(),
            new ol.control.Attribution({
                collapsed: false
            }),
            new ol.control.ScaleLine({
                units: 'nautical'
            })
        ],
        loadTilesWhileAnimating: true,
        loadTilesWhileInteracting: true
    });

    var change_key = source.on('change', function(e) {
        if (source.getState() == 'ready') {
            source.forEachFeature(function(feature) {
                if (feature.get('type') === 'plane') {
                    plane = feature;
                }
                if (feature.get('type') === 'route') {
                    route = feature;
                    view.fit(feature.getGeometry().getExtent(), map.getSize());
                    var flight_data = feature.get('flight_data');
                    altitude_list = flight_data[0];
                    ground_speed_list = flight_data[1];
                    chart = c3.generate({
                        bindto: '#flight_data',
                        data: {
                            columns: [
                                altitude_list,
                                ground_speed_list
                            ],
                            axes: {
                                'Ground Speed': 'y2'
                            }
                        },
                        axis: {
                            x: {
                                show: false
                            },
                            y: {
                                tick: {
                                    format: function (d) {
                                        return d + ' ft';
                                    }
                                },
                                label: {
                                    text: 'Altitude'
                                }
                            },
                            y2: {
                                show: true,
                                tick: {
                                    format: function (d) {
                                        return d + ' kts';
                                    }
                                },
                                label: {
                                    text: 'Ground Speed'
                                }
                            }
                        },
                        point: {
                            show: false
                        }
                    });
                }
            });
            ol.Observable.unByKey(change_key);
        }
    });
}

var live_initialized = null;

function refresh_live() {

    function update_flight(data) {
        if (!live_initialized) {
            $("#not-live").hide();
            $("#live-details").show();
            initialize_flight(data.geojson_url, data);
            $("#flight-title").html(data.html_title);
            $("#origin").html(data.origin);
            $("#destination").html(data.destination);
            $("#aircraft").html(data.aircraft);
            $("#flight-level").html('FL' + data.flight_level);
            if (data.ofp_url !== null) {
                $("ofp").show();
                $("ofp-url").attr("href", data.ofp_url);
            }
            live_initialized = true;
        }
        if (plane !== null && chart !== null) {
            route.getGeometry().appendCoordinate(
                ol.proj.fromLonLat([
                    data.longitude,
                    data.latitude,
                ])
            );
            plane.getGeometry().setCoordinates(
                ol.proj.fromLonLat([
                    data.longitude,
                    data.latitude,
                ])
            );
            var style = plane.getStyle();
            if (style === null) {
                style = new ol.style.Style({
                    image: get_plane_icon(data)
                });
                plane.setStyle(style);
            }
            else {
                style.setImage(get_plane_icon(data));
            }
            altitude_list.push(data.altitude);
            ground_speed_list.push(data.ground_speed);
            chart.load({
                columns: [
                    altitude_list,
                    ground_speed_list,
                ]
            });
        }
        $("#route").html(data.route);
    }

    $.getJSON('/live/json/', function(data) {
        if (live_initialized === null) {
            if (data.live) {
                update_flight(data);
            }
            else {
                $("#live-details").hide();
                $("#ofp-url").hide();
                $("#not-live").show();
                live_initialized = false;
            }
        }
        else {
            if (!data.live) {
                if (live_initialized) {
                    $("#live-details").hide();
                    $("#ofp-url").hide();
                    $("#not-live").show();
                    live_initialized = false;
                }
            }
            else {
                update_flight(data);
            }
        }
    });
}


function initialize_live() {
    refresh_live();
    window.setInterval(refresh_live, 15000);
}
