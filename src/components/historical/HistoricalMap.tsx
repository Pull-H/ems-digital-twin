import { useEffect, useRef } from 'react';
import L from 'leaflet';
import type { SimulationState } from '../../types';
import { BoroughGeometry, incidentColors, statusColors, zoneColors } from './geography';

const isVisibleIncident = (estado: string) => estado !== 'completado' && estado !== 'cancelado';

function ambulanceIcon(color: string) {
  return L.divIcon({
    className: '',
    iconSize: [22, 26],
    iconAnchor: [11, 13],
    html: `<div style="
      width:22px;height:26px;position:relative;transform:translateY(-2px);
      filter:drop-shadow(0 2px 3px rgba(15,23,42,.25));">
      <div style="position:absolute;left:3px;top:6px;width:16px;height:14px;border:1px solid #0f172a;border-radius:3px;background:#f8fafc;"></div>
      <div style="position:absolute;left:5px;top:3px;width:12px;height:7px;border:1px solid #0f172a;border-radius:3px 3px 1px 1px;background:#dbeafe;"></div>
      <div style="position:absolute;left:4px;top:12px;width:14px;height:3px;border-radius:2px;background:${color};"></div>
      <div style="position:absolute;left:9px;top:1px;width:4px;height:3px;border-radius:2px;background:#ef4444;"></div>
      <div style="position:absolute;left:2px;top:18px;width:5px;height:5px;border-radius:50%;background:#111827;"></div>
      <div style="position:absolute;right:2px;top:18px;width:5px;height:5px;border-radius:50%;background:#111827;"></div>
    </div>`,
  });
}

export function HistoricalMap({ state, geography, onSelect }: { state: SimulationState; geography: BoroughGeometry; onSelect: (id: number) => void }) {
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const live = useRef({ state, onSelect }); live.current = { state, onSelect };
  useEffect(() => {
    const map = L.map(host.current!, { preferCanvas: true }); mapRef.current = map;
    const boundaries = L.geoJSON(geography, {
      style: feature => {
        const zone = live.current.state.zones.find(z => z.nombre.toUpperCase() === feature?.properties.boroname.toUpperCase());
        return { color: zoneColors[zone?.id ?? 1], weight: 1.5, fillOpacity: .3 };
      },
      onEachFeature: (feature, layer) => {
        const zone = live.current.state.zones.find(z => z.nombre.toUpperCase() === feature.properties.boroname.toUpperCase());
        if (zone) { layer.bindTooltip(zone.nombre); layer.on('click', () => { live.current.onSelect(zone.id); layer.openTooltip(); }); }
      },
    }).addTo(map);
    map.fitBounds(boundaries.getBounds(), { padding: [18, 18] });
    map.attributionControl.addAttribution('Limites: NYC DCP 26b | Posiciones aproximadas');
    layerRef.current = L.layerGroup().addTo(map);
    const observer = new ResizeObserver(() => { map.invalidateSize(); map.fitBounds(boundaries.getBounds(), { padding: [18, 18] }); });
    observer.observe(host.current!);
    return () => { observer.disconnect(); map.remove(); mapRef.current = null; };
  }, [geography]);
  useEffect(() => {
    const layer = layerRef.current; if (!layer) return; layer.clearLayers();
    state.zones.forEach(zone => {
      const summary = state.simulation!.zone_summary.find(s => s.zone_id === zone.id)!;
      L.circleMarker(zone.centroide, { radius: 8, color: zoneColors[zone.id], weight: 2, fillColor: '#ffffff', fillOpacity: 1 })
        .bindTooltip(`${zone.nombre}: ${summary.available} libres, ${summary.active} activas, ${summary.pending} en espera`)
        .on('click', () => live.current.onSelect(zone.id)).addTo(layer);
    });
    state.incidents.filter(incident => isVisibleIncident(incident.estado)).slice(0, 600).forEach(incident => {
      const color = incidentColors[incident.estado] || '#ef4444';
      L.circleMarker([incident.latitud, incident.longitud], {
        radius: incident.prioridad === 'alta' ? 5 : 3.8,
        color,
        fillColor: color,
        fillOpacity: .78,
        opacity: .9,
        weight: 1.2,
      })
        .bindTooltip(`${incident.id}: ${incident.estado}, prioridad ${incident.prioridad}`)
        .addTo(layer);
    });
    state.ambulances.filter(a => a.estado !== 'disponible').forEach(a => {
      const color = statusColors[a.estado] || '#397fbe';
      L.marker([a.latitud, a.longitud], { icon: ambulanceIcon(color) })
        .bindTooltip(`${a.codigo}: ${a.estado} (simulado)`).addTo(layer);
      if (a.target_lat !== undefined && a.target_lng !== undefined)
        L.polyline([[a.latitud, a.longitud], [a.target_lat, a.target_lng]], { color, opacity: .35, weight: 1, dashArray: '4 4' }).addTo(layer);
    });
  }, [state, geography]);
  return <div ref={host} className="h-[470px] md:h-[550px] w-full min-w-0 z-0" style={{ background: '#e8f0f2' }} aria-label="Mapa NYC 2D" />;
}
