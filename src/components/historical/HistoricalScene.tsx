import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { Focus, RotateCcw, Scan } from 'lucide-react';
import type { Ambulance, SimulationState } from '../../types';
import { BoroughGeometry, incidentColors, project, statusColors, zoneColors } from './geography';

interface Props { state: SimulationState; geography: BoroughGeometry; onSelect: (id: number) => void; }

function dispose(group: THREE.Object3D) {
  group.traverse(object => {
    const mesh = object as THREE.Mesh;
    mesh.geometry?.dispose();
    const materials = mesh.material ? (Array.isArray(mesh.material) ? mesh.material : [mesh.material]) : [];
    materials.forEach(material => { (material as THREE.MeshBasicMaterial).map?.dispose(); material.dispose(); });
  });
  group.clear();
}

const isVisibleIncident = (estado: string) => estado !== 'completado' && estado !== 'cancelado';

function targetYaw(ambulance: Ambulance, x: number, z: number) {
  if (ambulance.target_lat === undefined || ambulance.target_lng === undefined) return 0;
  const [tx, tz] = project(ambulance.target_lat, ambulance.target_lng);
  return Math.atan2(tx - x, tz - z);
}

function ambulanceModel(ambulance: Ambulance) {
  const [x, z] = project(ambulance.latitud, ambulance.longitud);
  const color = statusColors[ambulance.estado] || '#397fbe';
  const vehicle = new THREE.Group();
  vehicle.position.set(x, 1.02, z);
  vehicle.rotation.y = targetYaw(ambulance, x, z);

  const body = new THREE.Mesh(
    new THREE.BoxGeometry(.82, .38, 1.38),
    new THREE.MeshStandardMaterial({ color: '#f8fafc', roughness: .42 }),
  );
  body.position.y = .24;
  vehicle.add(body);

  const cab = new THREE.Mesh(
    new THREE.BoxGeometry(.72, .34, .46),
    new THREE.MeshStandardMaterial({ color: '#dbeafe', roughness: .32 }),
  );
  cab.position.set(0, .44, .37);
  vehicle.add(cab);

  const stripe = new THREE.Mesh(
    new THREE.BoxGeometry(.86, .09, 1.08),
    new THREE.MeshBasicMaterial({ color }),
  );
  stripe.position.set(0, .35, -.08);
  vehicle.add(stripe);

  const light = new THREE.Mesh(
    new THREE.BoxGeometry(.32, .08, .18),
    new THREE.MeshBasicMaterial({ color: ambulance.estado === 'en ruta' ? '#2563eb' : '#ef4444' }),
  );
  light.position.set(0, .67, .1);
  vehicle.add(light);

  const wheelMaterial = new THREE.MeshStandardMaterial({ color: '#111827', roughness: .7 });
  [[-.47, -.44], [.47, -.44], [-.47, .45], [.47, .45]].forEach(([wheelX, wheelZ]) => {
    const wheel = new THREE.Mesh(new THREE.CylinderGeometry(.12, .12, .08, 12), wheelMaterial);
    wheel.rotation.z = Math.PI / 2;
    wheel.position.set(wheelX, .08, wheelZ);
    vehicle.add(wheel);
  });

  return vehicle;
}

export function HistoricalScene({ state, geography, onSelect }: Props) {
  const mount = useRef<HTMLDivElement>(null);
  const live = useRef({ state, onSelect }); live.current = { state, onSelect };
  const dynamic = useRef(new THREE.Group());
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const fitRef = useRef<(topdown?: boolean) => void>(() => {});
  const [error, setError] = useState(false);
  const labels = useRef(new Map<number, HTMLButtonElement>());
  const reset = () => {
    fitRef.current();
  };

  useEffect(() => {
    const host = mount.current!;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true }); }
    catch { setError(true); return; }
    const scene = new THREE.Scene(); scene.background = new THREE.Color('#e8f0f2');
    const camera = new THREE.PerspectiveCamera(43, 1, .1, 600); cameraRef.current = camera;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); host.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('aria-label', 'Territorio NYC 3D y unidades simuladas');
    const controls = new OrbitControls(camera, renderer.domElement); controlsRef.current = controls;
    controls.enableDamping = true; controls.minDistance = 35; controls.maxDistance = 240;
    controls.maxPolarAngle = Math.PI / 2.15;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x91a8b0, 2.8));
    const sun = new THREE.DirectionalLight(0xffffff, 2); sun.position.set(-30, 100, 60); scene.add(sun);
    const terrain = new THREE.Group(); scene.add(terrain, dynamic.current);
    geography.features.forEach(feature => {
      const zone = live.current.state.zones.find(z => z.nombre.toUpperCase() === feature.properties.boroname.toUpperCase());
      if (!zone) return;
      feature.geometry.coordinates.forEach(polygon => {
        const rings = polygon.map(ring => ring.map(([lng, lat]) => { const [x, z] = project(lat, lng); return new THREE.Vector2(x, -z); }));
        const shape = new THREE.Shape(rings[0]);
        rings.slice(1).forEach(ring => shape.holes.push(new THREE.Path(ring)));
        const geometry = new THREE.ExtrudeGeometry(shape, { depth: .55, bevelEnabled: false });
        geometry.rotateX(-Math.PI / 2);
        const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: zoneColors[zone.id], roughness: .85, transparent: true, opacity: .72 }));
        mesh.userData.zoneId = zone.id; terrain.add(mesh);
      });
    });
    const bounds = new THREE.Box3().setFromObject(terrain);
    const center = bounds.getCenter(new THREE.Vector3());
    const corners: THREE.Vector3[] = [];
    for (const x of [bounds.min.x, bounds.max.x]) for (const z of [bounds.min.z, bounds.max.z])
      corners.push(new THREE.Vector3(x, 0, z), new THREE.Vector3(x, 12, z));
    fitRef.current = (topdown = false) => {
      const direction = new THREE.Vector3(0, topdown ? 1 : 83, topdown ? .0001 : 70).normalize();
      let distance = 80;
      controls.target.copy(center);
      for (let step = 0; step < 30; step++) {
        camera.position.copy(center).addScaledVector(direction, distance);
        camera.lookAt(center); camera.updateMatrixWorld();
        if (corners.every(corner => { const p = corner.clone().project(camera); return Math.abs(p.x) < .88 && Math.abs(p.y) < .84; })) break;
        distance *= 1.06;
      }
      controls.update();
    };
    const resize = () => {
      const width = host.clientWidth, height = host.clientHeight;
      camera.aspect = width / height;
      camera.fov = width < 600 ? 60 : 43;
      camera.updateProjectionMatrix(); renderer.setSize(width, height); fitRef.current();
    };
    const observer = new ResizeObserver(resize); observer.observe(host); resize();
    let frame = 0;
    const render = () => {
      frame = requestAnimationFrame(render); controls.update(); renderer.render(scene, camera);
      const width = host.clientWidth, height = host.clientHeight;
      const placed: { x: number; y: number }[] = [];
      const projected = live.current.state.zones.map(zone => {
        const [x, z] = project(...zone.centroide);
        const demand = live.current.state.predictions.find(p => p.zona_id === zone.id)?.demanda_predicha_ml ?? 0;
        const point = new THREE.Vector3(x, Math.max(.5, demand * .17) + 1.5, z).project(camera);
        return { id: zone.id, x: (point.x + 1) * width / 2 - 65, y: (1 - point.y) * height / 2 - 52 };
      }).sort((a, b) => a.y - b.y);
      for (const point of projected) {
        const element = labels.current.get(point.id); if (!element) continue;
        const anchor = { x: Math.max(6, Math.min(width - 136, point.x)), y: Math.max(56, Math.min(height - 92, point.y)) };
        const candidates = [0, -62, 62, -124, 124, -186, 186, -248, 248].flatMap(dy => [0, -138, 138].map(dx => ({ x: anchor.x + dx, y: anchor.y + dy, cost: dx * dx + dy * dy })));
        const choice = candidates.sort((a, b) => a.cost - b.cost).find(p => p.x >= 6 && p.x <= width - 136 && p.y >= 56 && p.y <= height - 92
          && placed.every(previous => Math.abs(p.x - previous.x) >= 136 || Math.abs(p.y - previous.y) >= 60));
        const { x, y } = choice ?? anchor;
        placed.push({ x, y }); element.style.transform = `translate(${x}px, ${y}px)`;
      }
    };
    render();
    const raycaster = new THREE.Raycaster();
    let down = [0, 0];
    const pointerDown = (event: PointerEvent) => { down = [event.clientX, event.clientY]; };
    const click = (event: PointerEvent) => {
      if (Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 5) return;
      const rect = renderer.domElement.getBoundingClientRect();
      raycaster.setFromCamera(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1), camera);
      const hit = raycaster.intersectObjects(terrain.children).find(h => h.object.userData.zoneId);
      if (hit) live.current.onSelect(hit.object.userData.zoneId);
    };
    renderer.domElement.addEventListener('pointerdown', pointerDown);
    renderer.domElement.addEventListener('pointerup', click);
    return () => {
      cancelAnimationFrame(frame); observer.disconnect(); controls.dispose(); dispose(terrain); dispose(dynamic.current);
      renderer.dispose(); renderer.domElement.remove(); cameraRef.current = null; controlsRef.current = null;
    };
  }, [geography]);

  useEffect(() => {
    const group = dynamic.current; dispose(group);
    state.zones.forEach(zone => {
      const [x, z] = project(...zone.centroide);
      const demand = state.predictions.find(p => p.zona_id === zone.id)?.demanda_predicha_ml;
      const height = Math.max(.5, (demand ?? 0) * .17);
      const bar = new THREE.Mesh(new THREE.BoxGeometry(1.7, height, 1.7), new THREE.MeshStandardMaterial({ color: zoneColors[zone.id] }));
      bar.position.set(x, height / 2 + .6, z); group.add(bar);
      const base = new THREE.Mesh(new THREE.OctahedronGeometry(.9), new THREE.MeshStandardMaterial({ color: '#344554' }));
      base.position.set(x, 1, z); group.add(base);
    });
    state.incidents.filter(incident => isVisibleIncident(incident.estado)).slice(0, 360).forEach(incident => {
      const [x, z] = project(incident.latitud, incident.longitud);
      const color = incidentColors[incident.estado] || '#ef4444';
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(.34, .52, 28),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: .72, side: THREE.DoubleSide }),
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(x, .72, z);
      group.add(ring);
      const marker = new THREE.Mesh(
        new THREE.SphereGeometry(incident.estado === 'pendiente' ? .23 : .3, 14, 10),
        new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: .22, roughness: .38 }),
      );
      marker.position.set(x, incident.estado === 'pendiente' ? 1.1 : 1.35, z);
      group.add(marker);
      if (incident.prioridad === 'alta') {
        const mast = new THREE.Mesh(
          new THREE.CylinderGeometry(.05, .05, .9, 8),
          new THREE.MeshBasicMaterial({ color, transparent: true, opacity: .55 }),
        );
        mast.position.set(x, 1.52, z);
        group.add(mast);
      }
    });
    const activeUnits = state.ambulances.filter(a => a.estado !== 'disponible');
    activeUnits.forEach(a => {
      const [x, z] = project(a.latitud, a.longitud);
      group.add(ambulanceModel(a));
      if (a.target_lat !== undefined && a.target_lng !== undefined) {
        const [tx, tz] = project(a.target_lat, a.target_lng);
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(x, 1.15, z), new THREE.Vector3(tx, 1.15, tz)]),
          new THREE.LineBasicMaterial({ color: statusColors[a.estado], transparent: true, opacity: .3 }));
        group.add(line);
      }
    });
  }, [state, geography]);

  return <div className="relative h-[470px] md:h-[550px] w-full min-w-0 bg-[#e8f0f2]">
    <div ref={mount} className="absolute inset-0 touch-none" />
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {state.zones.map(zone => {
        const summary = state.simulation!.zone_summary.find(s => s.zone_id === zone.id)!;
        const demand = state.predictions.find(p => p.zona_id === zone.id)?.demanda_predicha_ml;
        return <button key={zone.id} ref={element => { if (element) labels.current.set(zone.id, element); else labels.current.delete(zone.id); }}
          onClick={() => onSelect(zone.id)} title={`Seleccionar ${zone.nombre}`} data-zone-label={zone.id}
          className="absolute top-0 left-0 w-[130px] text-left pointer-events-auto rounded border border-slate-200 bg-white/95 px-2 py-1.5 shadow-sm"
          style={{ borderTop: `3px solid ${zoneColors[zone.id]}` }}>
          <span className="block text-[11px] font-semibold text-slate-800">{zone.nombre} <span className="float-right font-mono">{demand?.toFixed(1) ?? '--'}/h</span></span>
          <span className="block text-[10px] text-slate-600 mt-0.5">{summary.available} libres · {summary.active} activas</span>
        </button>;
      })}
    </div>
    <div className="absolute top-3 right-3 flex gap-1 bg-white/95 p-1 rounded border border-slate-200">
      <button title="Restablecer camara" aria-label="Restablecer camara" onClick={reset} className="p-2 hover:bg-slate-100"><RotateCcw size={17} /></button>
      <button title="Vista cenital" aria-label="Vista cenital" onClick={() => fitRef.current(true)} className="p-2 hover:bg-slate-100"><Scan size={17} /></button>
      <button title="Centrar NYC" aria-label="Centrar NYC" onClick={() => controlsRef.current?.target.set(0, 0, 0)} className="p-2 hover:bg-slate-100"><Focus size={17} /></button>
    </div>
    <div className="absolute bottom-9 right-3 flex flex-wrap gap-2 rounded border border-slate-200 bg-white/95 px-2 py-1.5 text-[10px] text-slate-700 shadow-sm">
      <span className="inline-flex items-center gap-1"><i className="h-2 w-2 rounded-full bg-amber-500" /> espera</span>
      <span className="inline-flex items-center gap-1"><i className="h-2 w-2 rounded-full bg-blue-600" /> ruta</span>
      <span className="inline-flex items-center gap-1"><i className="h-2 w-2 rounded-full bg-red-600" /> escena</span>
      <span className="inline-flex items-center gap-1"><i className="h-2 w-2 rounded-full bg-violet-600" /> traslado</span>
    </div>
    {error && <p role="alert" className="absolute inset-x-4 top-20 bg-white p-4">WebGL no esta disponible. Usa la vista 2D.</p>}
    <span className="absolute bottom-2 left-3 text-[10px] text-slate-600 bg-white/90 px-2 py-1">Limites: NYC DCP 26b · Posiciones y trayectos aproximados</span>
  </div>;
}
