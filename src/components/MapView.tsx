import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Ambulance, DemandPrediction, EMSBase, Hospital, Incident, RelocationRecommendation, Zone } from '../types';
import { METRO_CENTER } from '../services/cityData';
import { Eye, Layers, RefreshCw, ShieldAlert, Sparkles, Truck, Box, Map, Columns, Maximize2 } from 'lucide-react';
import { DigitalTwin3D } from './DigitalTwin3D';

interface MapViewProps {
  zones: Zone[];
  bases: EMSBase[];
  hospitals: Hospital[];
  ambulances: Ambulance[];
  incidents: Incident[];
  predictions: DemandPrediction[];
  relocations: RelocationRecommendation[];
  selectedZone: Zone | null;
  onSelectZone: (zone: Zone | null) => void;
  selectedAmbulance: Ambulance | null;
  onSelectAmbulance: (ambulance: Ambulance | null) => void;
}

export const MapView: React.FC<MapViewProps> = ({
  zones,
  bases,
  hospitals,
  ambulances,
  incidents,
  predictions,
  relocations,
  selectedZone,
  onSelectZone,
  selectedAmbulance,
  onSelectAmbulance,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // View Dimension: 2D GIS, 3D WebGL Digital Twin, or Split
  const [viewDimension, setViewDimension] = useState<'2d' | '3d' | 'split'>('3d');

  // Layer groups references
  const zonesLayerRef = useRef<L.LayerGroup | null>(null);
  const basesLayerRef = useRef<L.LayerGroup | null>(null);
  const hospitalsLayerRef = useRef<L.LayerGroup | null>(null);
  const ambulancesLayerRef = useRef<L.LayerGroup | null>(null);
  const incidentsLayerRef = useRef<L.LayerGroup | null>(null);
  const routesLayerRef = useRef<L.LayerGroup | null>(null);
  const relocationsLayerRef = useRef<L.LayerGroup | null>(null);

  // Map display controls
  const [colorMode, setColorMode] = useState<'quintil' | 'riesgo'>('quintil');
  const [layerVisibility, setLayerVisibility] = useState({
    zones: true,
    ambulances: true,
    incidents: true,
    hospitals: true,
    bases: true,
    routes: true,
    relocations: true,
  });

  // Quintile color palette
  const getQuintileColor = (quintile: number): string => {
    switch (quintile) {
      case 1:
        return '#e11d48'; // Rose-600 (Highest vulnerability)
      case 2:
        return '#f97316'; // Orange-500
      case 3:
        return '#eab308'; // Yellow-500
      case 4:
        return '#06b6d4'; // Cyan-500
      case 5:
        return '#4f46e5'; // Indigo-600 (Lowest vulnerability)
      default:
        return '#64748b';
    }
  };

  // Risk color palette
  const getRiskColor = (zoneId: number): string => {
    const pred15 = predictions.find((p) => p.zona_id === zoneId && p.horizonte_min === 15);
    if (!pred15) return '#10b981';
    if (pred15.nivel_riesgo === 'alto') return '#ef4444';
    if (pred15.nivel_riesgo === 'medio') return '#f59e0b';
    return '#10b981';
  };

  // Ambulance status colors
  const getAmbulanceStatusColor = (status: Ambulance['estado']): string => {
    switch (status) {
      case 'disponible':
        return '#10b981'; // Emerald
      case 'en ruta':
        return '#0284c7'; // Sky
      case 'en escena':
        return '#f59e0b'; // Amber
      case 'trasladando':
        return '#8b5cf6'; // Violet
      case 'en hospital':
        return '#ec4899'; // Pink
      case 'reubicándose':
        return '#06b6d4'; // Cyan
      default:
        return '#64748b';
    }
  };

  // Initialize Leaflet Map
  useEffect(() => {
    if (viewDimension === '3d') return; // Don't init Leaflet if pure 3D
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: METRO_CENTER,
      zoom: 12,
      zoomControl: true,
    });

    // Clean, crisp basemap tiles (CartoDB Positron for academic GIS look)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    // Initialize layer groups
    zonesLayerRef.current = L.layerGroup().addTo(map);
    routesLayerRef.current = L.layerGroup().addTo(map);
    relocationsLayerRef.current = L.layerGroup().addTo(map);
    basesLayerRef.current = L.layerGroup().addTo(map);
    hospitalsLayerRef.current = L.layerGroup().addTo(map);
    incidentsLayerRef.current = L.layerGroup().addTo(map);
    ambulancesLayerRef.current = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;

    // Handle container resize
    const resizeObserver = new ResizeObserver(() => {
      map.invalidateSize();
    });
    resizeObserver.observe(mapContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [viewDimension]);

  // Update Zones Layer
  useEffect(() => {
    if (!zonesLayerRef.current) return;
    zonesLayerRef.current.clearLayers();

    if (!layerVisibility.zones) return;

    zones.forEach((zone) => {
      const fillColor = colorMode === 'quintil' ? getQuintileColor(zone.quintil_socioeconomico) : getRiskColor(zone.id);
      const isSelected = selectedZone?.id === zone.id;

      const polygon = L.polygon(zone.poligono as any, {
        color: isSelected ? '#0f172a' : fillColor,
        weight: isSelected ? 3 : 1.5,
        fillColor: fillColor,
        fillOpacity: isSelected ? 0.45 : 0.22,
        dashArray: isSelected ? undefined : '3, 3',
      });

      const pred15 = predictions.find((p) => p.zona_id === zone.id && p.horizonte_min === 15);

      const popupContent = `
        <div class="p-2 min-w-[200px] text-slate-900 font-sans">
          <div class="flex items-center justify-between border-b pb-1 mb-1.5">
            <span class="font-bold text-sm">${zone.nombre}</span>
            <span class="text-xs font-mono font-bold px-1.5 py-0.5 bg-slate-100 rounded">${zone.codigo}</span>
          </div>
          <div class="text-xs space-y-1">
            <div class="flex justify-between">
              <span class="text-slate-500">Quintil:</span>
              <span class="font-semibold text-rose-600">Q${zone.quintil_socioeconomico} (Vulnerab. ${(zone.nivel_vulnerabilidad * 100).toFixed(0)}%)</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Población:</span>
              <span class="font-semibold">${zone.poblacion.toLocaleString()} hab.</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Ingreso prom.:</span>
              <span class="font-semibold">$${zone.ingreso_promedio} / mes</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Demanda hist.:</span>
              <span class="font-semibold">${zone.demanda_historica_diaria} llamadas/día</span>
            </div>
            ${
              pred15
                ? `
              <div class="mt-1 pt-1 border-t flex justify-between items-center">
                <span class="text-slate-500">Riesgo 15m:</span>
                <span class="font-bold uppercase px-1.5 py-0.5 rounded text-[10px] ${
                  pred15.nivel_riesgo === 'alto'
                    ? 'bg-red-100 text-red-700'
                    : pred15.nivel_riesgo === 'medio'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-emerald-100 text-emerald-700'
                }">${pred15.nivel_riesgo} (${pred15.demanda_predicha_ml} ll.)</span>
              </div>
            `
                : ''
            }
          </div>
        </div>
      `;

      polygon.bindPopup(popupContent);
      polygon.on('click', () => onSelectZone(zone));
      polygon.addTo(zonesLayerRef.current!);
    });
  }, [zones, colorMode, layerVisibility.zones, selectedZone, predictions, viewDimension]);

  // Update Bases Layer (Realistic SVG)
  useEffect(() => {
    if (!basesLayerRef.current) return;
    basesLayerRef.current.clearLayers();

    if (!layerVisibility.bases) return;

    bases.forEach((base) => {
      const baseIcon = L.divIcon({
        className: 'custom-ems-base-icon',
        html: `
          <div class="relative group cursor-pointer">
            <div class="w-10 h-10 rounded-xl bg-slate-900 border-2 border-cyan-400 shadow-xl flex flex-col items-center justify-center text-white transition-all transform hover:scale-110">
              <svg class="w-5 h-5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v4M12 14v4M16 14v4"/>
              </svg>
              <span class="text-[8px] font-mono font-bold text-cyan-300">BASE</span>
            </div>
            <div class="absolute -bottom-1 -right-1 px-1 py-0.2 rounded bg-cyan-600 text-white text-[8px] font-mono font-bold shadow">
              B${base.id}
            </div>
          </div>
        `,
        iconSize: [40, 40],
        iconAnchor: [20, 20],
      });

      const marker = L.marker([base.latitud, base.longitud], { icon: baseIcon });
      marker.bindPopup(`
        <div class="p-2 text-slate-900 font-sans">
          <div class="font-bold text-sm text-slate-900 flex items-center space-x-1">
            <span>🏛️</span>
            <span>${base.nombre}</span>
          </div>
          <div class="text-xs text-cyan-700 font-mono font-semibold mt-0.5">${base.codigo}</div>
          <p class="text-xs text-slate-600 mt-1">${base.descripcion}</p>
          <div class="mt-2 text-xs font-semibold text-slate-700 bg-slate-100 p-1.5 rounded">Capacidad de flota: ${base.capacidad} ambulancias</div>
        </div>
      `);
      marker.addTo(basesLayerRef.current!);
    });
  }, [bases, layerVisibility.bases, viewDimension]);

  // Update Hospitals Layer (Realistic Medical Center SVG)
  useEffect(() => {
    if (!hospitalsLayerRef.current) return;
    hospitalsLayerRef.current.clearLayers();

    if (!layerVisibility.hospitals) return;

    hospitals.forEach((hosp) => {
      const occupancyRatio = hosp.capacidad > 0 ? hosp.ocupacion / hosp.capacidad : 0;
      const isHighOccupancy = occupancyRatio > 0.8;

      const hospIcon = L.divIcon({
        className: 'custom-hospital-icon',
        html: `
          <div class="relative group cursor-pointer">
            <div class="w-11 h-11 rounded-2xl ${
              isHighOccupancy ? 'bg-rose-700' : 'bg-indigo-700'
            } border-2 border-white shadow-2xl flex flex-col items-center justify-center text-white transition-all transform hover:scale-110">
              <!-- Glowing Red Cross Sign -->
              <svg class="w-6 h-6 text-white drop-shadow" viewBox="0 0 24 24" fill="currentColor">
                <path d="M10 3h4v6h6v4h-6v6h-4v-6H4v-4h6V3z"/>
              </svg>
              <div class="absolute -bottom-1 -right-1 px-1 py-0.2 rounded-full bg-slate-900 text-white text-[9px] font-mono border border-white">
                N${hosp.nivel_trauma}
              </div>
            </div>
            <!-- Occupancy Mini Progress Pill -->
            <div class="absolute -top-2 left-1/2 -translate-x-1/2 px-1.5 py-0.2 rounded-full bg-slate-900 text-[8px] font-mono font-bold text-white shadow whitespace-nowrap">
              ${Math.round(occupancyRatio * 100)}%
            </div>
          </div>
        `,
        iconSize: [44, 44],
        iconAnchor: [22, 22],
      });

      const marker = L.marker([hosp.latitud, hosp.longitud], { icon: hospIcon });
      marker.bindPopup(`
        <div class="p-2 text-slate-900 font-sans min-w-[220px]">
          <div class="font-bold text-sm text-slate-900 flex items-center space-x-1.5">
            <span class="text-rose-600 font-bold">✚</span>
            <span>${hosp.nombre}</span>
          </div>
          <div class="text-xs text-indigo-700 font-semibold mt-0.5">Especialidad Trauma: Nivel ${hosp.nivel_trauma}</div>
          <div class="mt-2 text-xs space-y-1.5">
            <div class="flex justify-between">
              <span class="text-slate-500">Ocupación Camas:</span>
              <span class="font-bold ${isHighOccupancy ? 'text-rose-600' : 'text-slate-700'}">${hosp.ocupacion} / ${hosp.capacidad} (${Math.round(occupancyRatio * 100)}%)</span>
            </div>
            <div class="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
              <div class="h-2 rounded-full ${isHighOccupancy ? 'bg-rose-500' : 'bg-indigo-500'}" style="width: ${Math.min(100, occupancyRatio * 100)}%"></div>
            </div>
            <div class="flex justify-between pt-1">
              <span class="text-slate-500">Demora triage:</span>
              <span class="font-semibold">${hosp.tiempo_espera_min} min</span>
            </div>
          </div>
        </div>
      `);
      marker.addTo(hospitalsLayerRef.current!);
    });
  }, [hospitals, layerVisibility.hospitals, viewDimension]);

  // Update Incidents Layer (Realistic Pulsing Emergency Beacon SVG)
  useEffect(() => {
    if (!incidentsLayerRef.current) return;
    incidentsLayerRef.current.clearLayers();

    if (!layerVisibility.incidents) return;

    const activeIncidents = incidents.filter(
      (i) => i.estado === 'pendiente' || i.estado === 'despachado' || i.estado === 'en_atencion' || i.estado === 'trasladando'
    );

    activeIncidents.forEach((inc) => {
      const priorityColor =
        inc.prioridad === 'alta' ? '#ef4444' : inc.prioridad === 'media' ? '#f59e0b' : '#3b82f6';

      const isPending = inc.estado === 'pendiente';

      const incIcon = L.divIcon({
        className: 'custom-incident-icon',
        html: `
          <div class="relative flex items-center justify-center cursor-pointer">
            <!-- Pulsing Emergency Radar Waves -->
            <div class="absolute w-10 h-10 rounded-full animate-ping opacity-75" style="background-color: ${priorityColor}"></div>
            <div class="w-8 h-8 rounded-full shadow-2xl flex items-center justify-center text-white text-xs border-2 border-white relative z-10" style="background-color: ${priorityColor}">
              <svg class="w-4 h-4 text-white animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              </svg>
            </div>
            <div class="absolute -bottom-2 px-1 rounded bg-slate-900 text-white text-[8px] font-mono font-bold uppercase z-20">
              ${inc.prioridad}
            </div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const marker = L.marker([inc.latitud, inc.longitud], { icon: incIcon });
      marker.bindPopup(`
        <div class="p-2 text-slate-900 font-sans min-w-[220px]">
          <div class="flex items-center justify-between border-b pb-1 mb-1.5">
            <span class="font-bold text-sm uppercase flex items-center space-x-1">
              <span>🚨</span>
              <span>${inc.tipo}</span>
            </span>
            <span class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded text-white" style="background-color: ${priorityColor}">
              ${inc.prioridad}
            </span>
          </div>
          <div class="text-xs space-y-1">
            <div class="flex justify-between">
              <span class="text-slate-500">ID Incidente:</span>
              <span class="font-mono font-semibold">${inc.id}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Estado:</span>
              <span class="font-semibold uppercase text-slate-800">${inc.estado}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Tiempo llamada:</span>
              <span class="font-semibold">Minuto ${inc.tiempo_llamada}</span>
            </div>
            ${
              inc.tiempo_respuesta_min
                ? `
              <div class="flex justify-between">
                <span class="text-slate-500">Tiempo respuesta:</span>
                <span class="font-bold text-indigo-700">${inc.tiempo_respuesta_min} min</span>
              </div>
            `
                : ''
            }
          </div>
        </div>
      `);
      marker.addTo(incidentsLayerRef.current!);
    });
  }, [incidents, layerVisibility.incidents, viewDimension]);

  // Update Ambulances Layer (Realistic Emergency Vehicle SVG with Flashing Strobe)
  useEffect(() => {
    if (!ambulancesLayerRef.current) return;
    ambulancesLayerRef.current.clearLayers();

    if (!layerVisibility.ambulances) return;

    ambulances.forEach((amb) => {
      const color = getAmbulanceStatusColor(amb.estado);
      const isSelected = selectedAmbulance?.id === amb.id;
      const isEmergency = amb.estado === 'en ruta' || amb.estado === 'trasladando';

      const ambIcon = L.divIcon({
        className: 'custom-ambulance-icon',
        html: `
          <div class="relative flex flex-col items-center justify-center cursor-pointer transition-transform ${
            isSelected ? 'scale-125 z-50' : 'hover:scale-110 z-30'
          }">
            <!-- Realistic Ambulance Van Badge with Flashing Roof Strobes -->
            <div class="relative flex items-center px-2 py-1 rounded-lg bg-slate-900 border-2 ${
              isSelected ? 'border-sky-400 ring-2 ring-sky-400' : 'border-white'
            } shadow-2xl space-x-1.5">
              <!-- Ambulance Icon -->
              <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/>
                <path d="M15 18H9"/>
                <path d="M19 18h2a1 1 0 0 0 1-1v-3.28a1 1 0 0 0-.684-.948l-1.923-.641a1 1 0 0 1-.578-.502l-1.539-2.564A1 1 0 0 0 16.415 8H14v10Z"/>
                <circle cx="7" cy="18" r="2"/>
                <circle cx="17" cy="18" r="2"/>
              </svg>
              <!-- Ambulance ID -->
              <span class="font-mono text-[11px] font-bold text-white">${amb.codigo}</span>
              <!-- Status Dot -->
              <span class="w-2 h-2 rounded-full ${isEmergency ? 'animate-ping' : ''}" style="background-color: ${color}"></span>
            </div>

            <!-- Speed & Status Pill -->
            <div class="mt-0.5 px-1.5 py-0.2 rounded-full text-[8px] font-mono font-bold text-white shadow-md uppercase" style="background-color: ${color}">
              ${amb.estado} ${amb.velocidad_kmh > 0 ? `• ${amb.velocidad_kmh}km/h` : ''}
            </div>
          </div>
        `,
        iconSize: [80, 42],
        iconAnchor: [40, 21],
      });

      const marker = L.marker([amb.latitud, amb.longitud], { icon: ambIcon });
      marker.on('click', () => onSelectAmbulance(amb));
      marker.bindPopup(`
        <div class="p-2 text-slate-900 font-sans min-w-[210px]">
          <div class="flex items-center justify-between border-b pb-1 mb-1.5">
            <span class="font-bold text-sm flex items-center space-x-1">
              <span>🚑</span>
              <span>${amb.codigo}</span>
            </span>
            <span class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded text-white" style="background-color: ${color}">
              ${amb.estado}
            </span>
          </div>
          <div class="text-xs space-y-1">
            <div class="flex justify-between">
              <span class="text-slate-500">Base asignada:</span>
              <span class="font-semibold">Base ${amb.base_id}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Velocidad media:</span>
              <span class="font-semibold">${amb.velocidad_kmh} km/h</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Atenciones hoy:</span>
              <span class="font-semibold">${amb.incidentes_atendidos} emergencias</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Odómetro:</span>
              <span class="font-semibold">${amb.kilometraje_total.toFixed(1)} km</span>
            </div>
            ${
              amb.incidente_asignado_id
                ? `
              <div class="mt-1 pt-1 border-t text-indigo-700 font-semibold">
                Asignada a: ${amb.incidente_asignado_id}
              </div>
            `
                : ''
            }
          </div>
        </div>
      `);
      marker.addTo(ambulancesLayerRef.current!);
    });
  }, [ambulances, layerVisibility.ambulances, selectedAmbulance, viewDimension]);

  // Update Dynamic Dispatch & Relocation Route Polylines
  useEffect(() => {
    if (!routesLayerRef.current || !relocationsLayerRef.current) return;
    routesLayerRef.current.clearLayers();
    relocationsLayerRef.current.clearLayers();

    // 1. Dispatch routes (Ambulance -> Incident)
    if (layerVisibility.routes) {
      ambulances.forEach((amb) => {
        if (amb.estado === 'en ruta' && amb.target_lat && amb.target_lng) {
          const polyline = L.polyline(
            [
              [amb.latitud, amb.longitud],
              [amb.target_lat, amb.target_lng],
            ],
            {
              color: '#0284c7',
              weight: 3.5,
              opacity: 0.85,
              dashArray: '6, 6',
            }
          );
          polyline.addTo(routesLayerRef.current!);
        } else if (amb.estado === 'trasladando' && amb.target_lat && amb.target_lng) {
          const polyline = L.polyline(
            [
              [amb.latitud, amb.longitud],
              [amb.target_lat, amb.target_lng],
            ],
            {
              color: '#8b5cf6',
              weight: 4,
              opacity: 0.9,
              dashArray: '4, 4',
            }
          );
          polyline.addTo(routesLayerRef.current!);
        }
      });
    }

    // 2. Relocation vectors
    if (layerVisibility.relocations) {
      relocations.forEach((rec) => {
        const amb = ambulances.find((a) => a.id === rec.ambulancia_id);
        if (amb) {
          const polyline = L.polyline(
            [
              [amb.latitud, amb.longitud],
              [rec.lat_destino, rec.lng_destino],
            ],
            {
              color: '#06b6d4',
              weight: 3,
              opacity: 0.8,
              dashArray: '8, 8',
            }
          );
          polyline.bindTooltip(`Reubicación preventiva: ${rec.ambulancia_codigo} ➔ ${rec.zona_destino_nombre}`, {
            sticky: true,
          });
          polyline.addTo(relocationsLayerRef.current!);
        }
      });
    }
  }, [ambulances, relocations, layerVisibility.routes, layerVisibility.relocations, viewDimension]);

  return (
    <div className="space-y-3" id="ems-viewport-container">
      {/* Viewport Dimension Switcher Header */}
      <div className="flex items-center justify-between bg-white px-4 py-2.5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 text-sm font-bold text-slate-800">
            <span className="p-1 rounded-lg bg-indigo-50 text-indigo-600">
              {viewDimension === '3d' ? <Box className="w-4 h-4" /> : <Map className="w-4 h-4" />}
            </span>
            <span>Visualización de Flota y Territorio</span>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg text-xs font-semibold">
            <button
              onClick={() => setViewDimension('3d')}
              className={`px-3 py-1.5 rounded-md flex items-center space-x-1.5 transition-all ${
                viewDimension === '3d' ? 'bg-indigo-600 text-white font-bold shadow' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              <span>Gemelo Digital 3D</span>
            </button>
            <button
              onClick={() => setViewDimension('2d')}
              className={`px-3 py-1.5 rounded-md flex items-center space-x-1.5 transition-all ${
                viewDimension === '2d' ? 'bg-indigo-600 text-white font-bold shadow' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Map className="w-3.5 h-3.5" />
              <span>Mapa Cartográfico 2D</span>
            </button>
            <button
              onClick={() => setViewDimension('split')}
              className={`px-3 py-1.5 rounded-md flex items-center space-x-1.5 transition-all ${
                viewDimension === 'split' ? 'bg-indigo-600 text-white font-bold shadow' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Vista Dividida (2D + 3D)</span>
            </button>
          </div>
        </div>

        {/* Status badges */}
        <div className="flex items-center space-x-3 text-xs">
          <span className="flex items-center space-x-1 text-slate-500 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
            <span>{ambulances.filter((a) => a.estado === 'disponible').length} Ambs Disponibles</span>
          </span>
          <span className="flex items-center space-x-1 text-slate-500 font-mono">
            <span className="w-2 h-2 rounded-full bg-sky-500 inline-block animate-pulse"></span>
            <span>{ambulances.filter((a) => a.estado === 'en ruta' || a.estado === 'trasladando').length} En Despacho</span>
          </span>
        </div>
      </div>

      {/* Render 3D View, 2D View, or Split View */}
      {viewDimension === '3d' && (
        <DigitalTwin3D
          zones={zones}
          bases={bases}
          hospitals={hospitals}
          ambulances={ambulances}
          incidents={incidents}
          predictions={predictions}
          relocations={relocations}
          selectedZone={selectedZone}
          onSelectZone={onSelectZone}
          selectedAmbulance={selectedAmbulance}
          onSelectAmbulance={onSelectAmbulance}
          colorMode={colorMode}
        />
      )}

      {viewDimension === '2d' && (
        <div className="relative w-full h-[640px] rounded-xl overflow-hidden border border-slate-200 shadow-sm bg-slate-100 flex flex-col" id="ems-map-wrapper">
          {/* Floating Map Controls & Legends */}
          <div className="absolute top-3 left-3 z-[1000] bg-white/95 backdrop-blur-xs p-2.5 rounded-xl border border-slate-200 shadow-md max-w-xs text-xs space-y-2.5">
            <div className="flex items-center justify-between font-bold text-slate-800 border-b border-slate-100 pb-1.5">
              <div className="flex items-center space-x-1.5">
                <Layers className="w-4 h-4 text-indigo-600" />
                <span>Capas Cartográficas</span>
              </div>
              <span className="text-[10px] font-mono text-slate-500">20 ZONAS</span>
            </div>

            {/* Color Mode Switcher */}
            <div className="space-y-1">
              <span className="text-[11px] font-semibold text-slate-600">Colorear Zonas Por:</span>
              <div className="grid grid-cols-2 gap-1">
                <button
                  onClick={() => setColorMode('quintil')}
                  className={`px-2 py-1 rounded text-center font-medium transition-colors ${
                    colorMode === 'quintil'
                      ? 'bg-indigo-600 text-white font-bold'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  Socioeconómico (Q1-Q5)
                </button>
                <button
                  onClick={() => setColorMode('riesgo')}
                  className={`px-2 py-1 rounded text-center font-medium transition-colors ${
                    colorMode === 'riesgo'
                      ? 'bg-indigo-600 text-white font-bold'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  Riesgo Predicho
                </button>
              </div>
            </div>

            {/* Layer Checkboxes */}
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] text-slate-700 pt-1 border-t border-slate-100">
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.ambulances}
                  onChange={(e) => setLayerVisibility({ ...layerVisibility, ambulances: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-0"
                />
                <span>🚑 Ambulancias</span>
              </label>
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.incidents}
                  onChange={(e) => setLayerVisibility({ ...layerVisibility, incidents: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-0"
                />
                <span>🚨 Llamadas</span>
              </label>
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.hospitals}
                  onChange={(e) => setLayerVisibility({ ...layerVisibility, hospitals: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-0"
                />
                <span>🏥 Hospitales</span>
              </label>
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.bases}
                  onChange={(e) => setLayerVisibility({ ...layerVisibility, bases: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-0"
                />
                <span>🏛️ Bases EMS</span>
              </label>
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.routes}
                  onChange={(e) => setLayerVisibility({ ...layerVisibility, routes: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-0"
                />
                <span>🛣️ Rutas Despacho</span>
              </label>
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.relocations}
                  onChange={(e) => setLayerVisibility({ ...layerVisibility, relocations: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-0"
                />
                <span>🔄 Reubicaciones</span>
              </label>
            </div>
          </div>

          {/* Floating Bottom Legend */}
          <div className="absolute bottom-3 left-3 z-[1000] bg-white/95 backdrop-blur-xs p-2.5 rounded-xl border border-slate-200 shadow-md text-xs">
            <div className="text-[11px] font-bold text-slate-800 mb-1">
              {colorMode === 'quintil' ? 'Quintil Socioeconómico' : 'Nivel de Riesgo Predicho'}
            </div>
            {colorMode === 'quintil' ? (
              <div className="flex items-center space-x-2 text-[10px]">
                <span className="flex items-center space-x-1"><span className="w-3 h-3 rounded bg-rose-600 inline-block"></span><span>Q1 (Mayor Vulnerab.)</span></span>
                <span className="flex items-center space-x-1"><span className="w-3 h-3 rounded bg-orange-500 inline-block"></span><span>Q2</span></span>
                <span className="flex items-center space-x-1"><span className="w-3 h-3 rounded bg-yellow-500 inline-block"></span><span>Q3</span></span>
                <span className="flex items-center space-x-1"><span className="w-3 h-3 rounded bg-cyan-500 inline-block"></span><span>Q4</span></span>
                <span className="flex items-center space-x-1"><span className="w-3 h-3 rounded bg-indigo-600 inline-block"></span><span>Q5 (Mayor Riqueza)</span></span>
              </div>
            ) : (
              <div className="flex items-center space-x-3 text-[10px]">
                <span className="flex items-center space-x-1"><span className="w-3 h-3 rounded bg-emerald-500 inline-block"></span><span>Riesgo Bajo</span></span>
                <span className="flex items-center space-x-1"><span className="w-3 h-3 rounded bg-amber-500 inline-block"></span><span>Riesgo Medio</span></span>
                <span className="flex items-center space-x-1"><span className="w-3 h-3 rounded bg-rose-500 inline-block"></span><span>Riesgo Alto</span></span>
              </div>
            )}
          </div>

          {/* Leaflet Map DOM Element */}
          <div ref={mapContainerRef} className="w-full h-full" id="leaflet-map-canvas" />
        </div>
      )}

      {viewDimension === 'split' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="h-[580px]">
            <DigitalTwin3D
              zones={zones}
              bases={bases}
              hospitals={hospitals}
              ambulances={ambulances}
              incidents={incidents}
              predictions={predictions}
              relocations={relocations}
              selectedZone={selectedZone}
              onSelectZone={onSelectZone}
              selectedAmbulance={selectedAmbulance}
              onSelectAmbulance={onSelectAmbulance}
              colorMode={colorMode}
            />
          </div>
          <div className="relative h-[580px] rounded-xl overflow-hidden border border-slate-200 shadow-sm bg-slate-100">
            <div ref={mapContainerRef} className="w-full h-full" />
          </div>
        </div>
      )}
    </div>
  );
};
