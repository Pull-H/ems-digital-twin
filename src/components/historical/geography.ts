import type { FeatureCollection, MultiPolygon } from 'geojson';

export type BoroughGeometry = FeatureCollection<MultiPolygon, { boroname: string }>;
export const zoneColors: Record<number, string> = { 1: '#d67b28', 2: '#21877b', 3: '#bd4f70', 4: '#487fc2', 5: '#8c78ad' };
export const statusColors: Record<string, string> = {
  disponible: '#159677', asignada: '#397fbe', 'en ruta': '#397fbe', 'en escena': '#d48c25',
  trasladando: '#9962b0', 'en hospital': '#c45278',
};
export const incidentColors: Record<string, string> = {
  pendiente: '#f59e0b',
  despachado: '#2563eb',
  en_atencion: '#dc2626',
  trasladando: '#7c3aed',
  cancelado: '#64748b',
};
// Local geographic projection for visual comparison, not a road routing model.
export const project = (lat: number, lng: number): [number, number] => [(lng + 73.98) * 150, -(lat - 40.71) * 198];
