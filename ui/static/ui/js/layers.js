var Layers = {};

Layers.OSM = new OpenLayers.Layer.OSM("OpenStreetMap");

Layers.HOT = new OpenLayers.Layer.XYZ("Humanitarian DM",
                ["http://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
                 "http://b.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
                 "http://c.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png"],
                {crossOriginKeyword: null}
            );