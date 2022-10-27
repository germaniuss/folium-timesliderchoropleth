from itertools import repeat
from folium.elements import JSCSSMixin
from folium.features import GeoJson
from folium.features import GeoJsonTooltip
from folium.features import GeoJsonDetail
from folium.features import GeoJsonPopup
from folium.features import Tooltip
from folium.features import Popup

from jinja2 import Template

class TimeSliderChoropleth(JSCSSMixin, GeoJson):
    """
    Creates a TimeSliderChoropleth plugin to append into a map with Map.add_child.

    Parameters
    ----------
    data: file, dict or str.
        The GeoJSON data you want to plot.
        * If file, then data will be read in the file and fully
        embedded in Leaflet's JavaScript.
        * If dict, then data will be converted to JSON and embedded
        in the JavaScript.
        * If str, then data will be passed to the JavaScript as-is.
        * If `__geo_interface__` is available, the `__geo_interface__`
        dictionary will be serialized to JSON and
        reprojected if `to_crs` is available.
    style_function: function, default None
        Function mapping a GeoJson Feature to a style dict.
        The style dict must contain all timestamps
    highlight_function: function, default None
        Function mapping a GeoJson Feature to a style dict for mouse events.
        The style dict must contain all timestamps
    name : string, default None
        The name of the Layer, as it will appear in LayerControls
    overlay : bool, default True
        Adds the layer as an optional overlay (True) or the base layer (False).
    control : bool, default True
        Whether the Layer will be included in LayerControls
    show: bool, default True
        Whether the layer will be shown on opening (only for overlays).
    smooth_factor: float, default None
        How much to simplify the polyline on each zoom level. More means
        better performance and smoother look, and less means more accurate
        representation. Leaflet defaults to 1.0.
    tooltips: dictionary, default None
        The dictionary must contain all timestamps 
        and each value can be GeoJsonTooltip, Tooltip, str or list(Tooltip), list(str) 
        if the tooltip for each feature is controlled individually
        Display a text when hovering over the object. Can utilize the data,
        see folium.GeoJsonTooltip for info on how to do that.
    popup: GeoJsonPopup, optional
        Show a different popup for each feature by passing a GeoJsonPopup object.
    marker: Circle, CircleMarker or Marker, optional
        If your data contains Point geometry, you can format the markers by passing a Circle,
        CircleMarker or Marker object with your wanted options. The `style_function` and
        `highlight_function` will also target the marker object you passed.
    embed: bool, default True
        Whether to embed the data in the html file or not. Note that disabling
        embedding is only supported if you provide a file link or URL.
    zoom_on_click: bool, default False
        Set to True to enable zooming in on a geometry when clicking on it.
    """
    _template = Template(u"""
        {% macro script(this, kwargs) %}
        
        var {{ this.get_name() }}_timestamp_list = {{ this.timestamps|tojson }};
        var {{ this.get_name() }}_timestamp = {{ this.get_name() }}_timestamp_list[0];
        {%- if this.tooltips != None %}
        var {{ this.get_name() }}_tooltips = {{ this.tooltips | tojson }};
        {%- endif %}

        // insert time slider
        d3.select("body").insert("p", ":first-child").append("input")
            .attr("type", "range")
            .attr("width", "100px")
            .attr("min", 0)
            .attr("max", {{ this.get_name() }}_timestamp_list.length - 1)
            .attr("value", 0)
            .attr("id", "{{ this.get_name() }}_slider")
            .attr("step", "1")
            .style('align', 'center');

        // insert time slider output BEFORE time slider (text on top of slider)
        d3.select("body").insert("p", ":first-child").append("output")
            .attr("width", "100")
            .attr("id", "{{ this.get_name() }}_slider_value")
            .style('font-size', '18px')
            .style('text-align', 'center')
            .style('font-weight', '500%');

        // function to update time slider value and reset the style map
        {{ this.get_name() }}_set_timestamp = (time) => {
            {{ this.get_name() }}_timestamp = time
            d3.select("output#{{ this.get_name() }}_slider_value").text(new Date(parseInt(time)*1000).toUTCString());
            {{ this.get_name() }}.resetStyle();
            {%- if this.tooltips != None %}
            let tooltips = {{ this.get_name() }}_tooltips[time];
            if (tooltips.type === "list") {
                idx = 0;
                {{ this.get_name() }}.eachLayer(function (layer) {
                    tooltip = tooltips.tooltip[idx]
                    layer.unbindTooltip();
                    layer.bindTooltip(`<div style=${tooltip.style}>${tooltip.text}</div>`, tooltip.options);
                    idx += 1;
                });
            } else {
                {{ this.get_name() }}.unbindTooltip();
                {{ this.get_name() }}.bindTooltip(tooltips.tooltip, tooltips.options);
            }
            {%- endif %}
        }
        
        d3.select("#{{ this.get_name() }}_slider").on("input", function() {
            {{ this.get_name() }}_set_timestamp({{ this.get_name() }}_timestamp_list[this.value])
        });
        
        {%- if this.style %}
        function {{ this.get_name() }}_styler(feature) {
            switch({{ this.feature_identifier }}) {
                {%- for style, ids_list in this.style_map.items() if not style == 'default' %}
                {% for id_val in ids_list %}case {{ id_val|tojson }}: {% endfor %}
                    return {{ style }}[{{ this.get_name() }}_timestamp];
                {%- endfor %}
                default:
                    return {{ this.style_map['default'] }}[{{ this.get_name() }}_timestamp];
            }
        }
        {%- endif %}
        {%- if this.highlight %}
        function {{ this.get_name() }}_highlighter(feature) {
            switch({{ this.feature_identifier }}) {
                {%- for style, ids_list in this.highlight_map.items() if not style == 'default' %}
                {% for id_val in ids_list %}case {{ id_val|tojson }}: {% endfor %}
                    return {{ style }}[{{ this.get_name() }}_timestamp];
                {%- endfor %}
                default:
                    return {{ this.highlight_map['default'] }}[{{ this.get_name() }}_timestamp];
            }
        }
        {%- endif %}

        {%- if this.marker %}
        function {{ this.get_name() }}_pointToLayer(feature, latlng) {
            var opts = {{ this.marker.options | tojson | safe }};
            {% if this.marker._name == 'Marker' and this.marker.icon %}
            const iconOptions = {{ this.marker.icon.options | tojson | safe }}
            const iconRootAlias = L{%- if this.marker.icon._name == "Icon" %}.AwesomeMarkers{%- endif %}
            opts.icon = new iconRootAlias.{{ this.marker.icon._name }}(iconOptions)
            {% endif %}
            {%- if this.style_function %}
            let style = {{ this.get_name()}}_styler(feature)
            Object.assign({%- if this.marker.icon -%}opts.icon.options{%- else -%} opts {%- endif -%}, style)
            {% endif %}
            return new L.{{this.marker._name}}(latlng, opts)
        }
        {%- endif %}

        function {{this.get_name()}}_onEachFeature(feature, layer) {
            layer.on({
                {%- if this.highlight %}
                mouseout: function(e) {
                    if(typeof e.target.setStyle === "function"){
                        {{ this.get_name() }}.resetStyle(e.target);
                    }
                },
                mouseover: function(e) {
                    if(typeof e.target.setStyle === "function"){
                        const highlightStyle = {{ this.get_name() }}_highlighter(e.target.feature)
                        e.target.setStyle(highlightStyle);
                    }
                },
                {%- endif %}
                {%- if this.zoom_on_click %}
                click: function(e) {
                    if (typeof e.target.getBounds === 'function') {
                        {{ this.parent_map.get_name() }}.fitBounds(e.target.getBounds());
                    }
                    else if (typeof e.target.getLatLng === 'function'){
                        let zoom = {{ this.parent_map.get_name() }}.getZoom()
                        zoom = zoom > 12 ? zoom : zoom + 1
                        {{ this.parent_map.get_name() }}.flyTo(e.target.getLatLng(), zoom)
                    }
                }
                {%- endif %}
            });
        };
        var {{ this.get_name() }} = L.geoJson(null, {
            {%- if this.smooth_factor is not none  %}
                smoothFactor: {{ this.smooth_factor|tojson }},
            {%- endif %}
                onEachFeature: {{ this.get_name() }}_onEachFeature,
            {% if this.style %}
                style: {{ this.get_name() }}_styler,
            {%- endif %}
            {%- if this.marker %}
                pointToLayer: {{ this.get_name() }}_pointToLayer
            {%- endif %}
        });

        function {{ this.get_name() }}_add (data) {
            {{ this.get_name() }}
                .addData(data)
                .addTo({{ this._parent.get_name() }});
        }
        {%- if this.embed %}
            {{ this.get_name() }}_add({{ this.data|tojson }});
        {%- else %}
            $.ajax({{ this.embed_link|tojson }}, {dataType: 'json', async: false})
                .done({{ this.get_name() }}_add);
        {%- endif %}
        
        {{ this.get_name() }}_set_timestamp({{ this.get_name() }}_timestamp)

        {% endmacro %}
        """)

    default_js = [
        ('d3v4',
         'https://d3js.org/d3.v4.min.js')
    ]

    def __init__(self, data, timestamps, style_function=None, highlight_function=None,  # noqa
                 name=None, overlay=True, control=True, show=True,
                 smooth_factor=None, tooltips=None, embed=True, popup=None,
                 zoom_on_click=False, marker=None):
        
        super(TimeSliderChoropleth, self).__init__(data, style_function=style_function, highlight_function=highlight_function, # noqa
                 name=name, overlay=overlay, control=control, show=show,
                 smooth_factor=smooth_factor, embed=embed, popup=popup,
                 zoom_on_click=zoom_on_click, marker=marker)
        
        # Make set of ordered timestamps.
        self.numregions = len(self.data['features'])
        self.timestamps = sorted(list(set(timestamps)))
        self.tooltips = None
        
        if tooltips is not None:
            self.tooltips = {unix: 
                {'type': 'single', 'tooltip': Template(GeoJsonDetail.base_template).render(this=tooltip), 'options': Template(u"""{{ this.tooltip_options | tojson | safe }}""").render(this=tooltip)}
                    if isinstance(tooltip, (GeoJsonTooltip, Tooltip))
                else {'type': 'list', 
                    'tooltip': [{
                        'text': each.text,
                        'options': each.options,
                        'style': each.style if hasattr(each, 'style') else None
                        } for each in map(lambda x: 
                            (Tooltip(x) if not isinstance(x, Tooltip) else x), 
                            (tooltip if isinstance(tooltip, list) else repeat(tooltip, self.numregions))
                        )]}
                    if isinstance(tooltip, list) or tooltip is not None
                else {'type': 'single', 'tooltip': None, 'options': None}
                for unix, tooltip in tooltips.items()
            }