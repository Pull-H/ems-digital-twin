import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import * as THREE from 'three';
import {
  Ambulance,
  DemandPrediction,
  EMSBase,
  Hospital,
  Incident,
  RelocationRecommendation,
  Zone,
} from '../types';
import { METRO_CENTER } from '../services/cityData';
import {
  Camera,
  Maximize2,
  Minimize2,
  Moon,
  Sun,
  Eye,
  Crosshair,
  Layers,
  Compass,
  Sparkles,
  Truck,
  RotateCcw,
  Sliders,
  Shield,
  Activity,
  AlertTriangle,
  Building,
} from 'lucide-react';

interface DigitalTwin3DProps {
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
  colorMode?: 'quintil' | 'riesgo';
}

// Coordinate transform parameters
const CENTER_LAT = METRO_CENTER[0]; // -8.11
const CENTER_LNG = METRO_CENTER[1]; // -79.03
const SCALE_X = 1400; // longitude scale to 3D world units
const SCALE_Z = 1400; // latitude scale to 3D world units

export function latLngTo3D(lat: number, lng: number, y: number = 0): THREE.Vector3 {
  const x = (lng - CENTER_LNG) * SCALE_X;
  const z = -(lat - CENTER_LAT) * SCALE_Z;
  return new THREE.Vector3(x, y, z);
}

export const DigitalTwin3D: React.FC<DigitalTwin3DProps> = ({
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
  colorMode = 'quintil',
}) => {
  const mountRef = useRef<HTMLDivElement>(null);

  // Settings & Modes
  const [lightingMode, setLightingMode] = useState<'day' | 'sunset' | 'night'>('night');
  const [cameraMode, setCameraMode] = useState<'isometric' | 'topdown' | 'follow' | 'cinematic'>('isometric');
  const [showBuildingDetails, setShowBuildingDetails] = useState<boolean>(true);
  const [showRoutes3D, setShowRoutes3D] = useState<boolean>(true);
  const [showLabels3D, setShowLabels3D] = useState<boolean>(true);
  const [hoveredObject, setHoveredObject] = useState<{ type: string; title: string; subtitle: string; status?: string; color?: string } | null>(null);

  // Three.js internal references
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Groups for dynamic objects
  const ambulancesGroupRef = useRef<THREE.Group>(new THREE.Group());
  const hospitalsGroupRef = useRef<THREE.Group>(new THREE.Group());
  const basesGroupRef = useRef<THREE.Group>(new THREE.Group());
  const incidentsGroupRef = useRef<THREE.Group>(new THREE.Group());
  const routesGroupRef = useRef<THREE.Group>(new THREE.Group());
  const terrainGroupRef = useRef<THREE.Group>(new THREE.Group());
  const buildingsGroupRef = useRef<THREE.Group>(new THREE.Group());
  const particlesGroupRef = useRef<THREE.Group>(new THREE.Group());

  // Lights refs for dynamic theme
  const dirLightRef = useRef<THREE.DirectionalLight | null>(null);
  const hemiLightRef = useRef<THREE.HemisphereLight | null>(null);
  const ambientLightRef = useRef<THREE.AmbientLight | null>(null);

  // Camera animation targets
  const cameraPosTarget = useRef<THREE.Vector3>(new THREE.Vector3(0, 55, 65));
  const cameraLookAtTarget = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0));
  const currentCameraLookAt = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0));

  // Mouse interaction & Orbit drag
  const isDragging = useRef<boolean>(false);
  const previousMousePosition = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const orbitAngles = useRef<{ theta: number; phi: number; radius: number }>({
    theta: Math.PI / 4,
    phi: Math.PI / 3.2,
    radius: 80,
  });

  // Strobe clock
  const clockRef = useRef<THREE.Clock>(new THREE.Clock());

  // Quintile color mapper
  const getQuintileHex = (quintile: number): number => {
    switch (quintile) {
      case 1: return 0xe11d48; // Rose-600
      case 2: return 0xf97316; // Orange-500
      case 3: return 0xeab308; // Yellow-500
      case 4: return 0x06b6d4; // Cyan-500
      case 5: return 0x4f46e5; // Indigo-600
      default: return 0x64748b;
    }
  };

  // Status color mapper
  const getStatusHex = (status: Ambulance['estado']): number => {
    switch (status) {
      case 'disponible': return 0x10b981; // Emerald
      case 'en ruta': return 0x0284c7; // Sky
      case 'en escena': return 0xf59e0b; // Amber
      case 'trasladando': return 0x8b5cf6; // Violet
      case 'en hospital': return 0xec4899; // Pink
      case 'reubicándose': return 0x06b6d4; // Cyan
      default: return 0x94a3b8;
    }
  };

  // -------------------------------------------------------------
  // BUILD PROCEDURAL REALISTIC 3D AMBULANCE MESH
  // -------------------------------------------------------------
  const createAmbulanceMesh = (amb: Ambulance, isSelected: boolean) => {
    const group = new THREE.Group();
    group.name = `ambulance_${amb.id}`;

    const statusHex = getStatusHex(amb.estado);
    const isEmergencyRun = amb.estado === 'en ruta' || amb.estado === 'trasladando';

    // 1. Vehicle Body (White with emergency gloss finish)
    const bodyGeo = new THREE.BoxGeometry(1.6, 1.1, 3.2);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0xf8fafc,
      roughness: 0.25,
      metalness: 0.2,
    });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = 0.85;
    body.castShadow = true;
    body.receiveShadow = true;
    group.add(body);

    // 2. Driver Cab / Hood Front extension
    const cabGeo = new THREE.BoxGeometry(1.56, 0.8, 1.1);
    const cabMat = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, roughness: 0.3 });
    const cab = new THREE.Mesh(cabGeo, cabMat);
    cab.position.set(0, 0.65, 1.8);
    cab.castShadow = true;
    group.add(cab);

    // 3. Windshield and Side Windows (Dark tinted glass with reflective properties)
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: 0x0f172a,
      roughness: 0.1,
      metalness: 0.9,
      transmission: 0.3,
      transparent: true,
      opacity: 0.85,
    });

    const frontWindshieldGeo = new THREE.PlaneGeometry(1.4, 0.65);
    const frontWindshield = new THREE.Mesh(frontWindshieldGeo, glassMat);
    frontWindshield.position.set(0, 1.15, 1.6);
    frontWindshield.rotation.x = -0.35;
    group.add(frontWindshield);

    // 4. Reflective Side Stripes & Medical Star of Life
    const stripeGeo = new THREE.BoxGeometry(1.64, 0.25, 3.0);
    const stripeMat = new THREE.MeshStandardMaterial({
      color: 0xdc2626, // Bright Red EMS stripe
      roughness: 0.3,
      metalness: 0.1,
    });
    const stripe = new THREE.Mesh(stripeGeo, stripeMat);
    stripe.position.y = 0.8;
    group.add(stripe);

    // Yellow fluorescent accent stripe
    const yellowStripeGeo = new THREE.BoxGeometry(1.65, 0.08, 2.9);
    const yellowStripeMat = new THREE.MeshStandardMaterial({
      color: 0xfacc15,
      roughness: 0.3,
    });
    const yellowStripe = new THREE.Mesh(yellowStripeGeo, yellowStripeMat);
    yellowStripe.position.y = 0.62;
    group.add(yellowStripe);

    // 5. Wheels (4 rubber tires with metallic rims)
    const wheelGeo = new THREE.CylinderGeometry(0.32, 0.32, 0.25, 16);
    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.8 });
    const rimMat = new THREE.MeshStandardMaterial({ color: 0xcbd5e1, metalness: 0.8, roughness: 0.2 });

    const wheelPositions = [
      { x: 0.85, y: 0.32, z: 1.3 },
      { x: -0.85, y: 0.32, z: 1.3 },
      { x: 0.85, y: 0.32, z: -1.0 },
      { x: -0.85, y: 0.32, z: -1.0 },
    ];

    wheelPositions.forEach((pos) => {
      const wheel = new THREE.Mesh(wheelGeo, wheelMat);
      wheel.rotation.z = Math.PI / 2;
      wheel.position.set(pos.x, pos.y, pos.z);
      wheel.castShadow = true;

      // Rim
      const rimGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.26, 12);
      const rim = new THREE.Mesh(rimGeo, rimMat);
      wheel.add(rim);

      group.add(wheel);
    });

    // 6. Roof Siren Lightbar (Emissive Strobe Bars)
    const barBaseGeo = new THREE.BoxGeometry(1.2, 0.12, 0.3);
    const barBaseMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8 });
    const barBase = new THREE.Mesh(barBaseGeo, barBaseMat);
    barBase.position.set(0, 1.46, 0.9);
    group.add(barBase);

    // Red strobe light left
    const redLightGeo = new THREE.BoxGeometry(0.45, 0.15, 0.25);
    const redLightMat = new THREE.MeshStandardMaterial({
      color: 0xef4444,
      emissive: isEmergencyRun ? 0xef4444 : 0x7f1d1d,
      emissiveIntensity: isEmergencyRun ? 2.5 : 0.4,
      roughness: 0.1,
    });
    const redLight = new THREE.Mesh(redLightGeo, redLightMat);
    redLight.position.set(-0.35, 1.55, 0.9);
    redLight.name = 'siren_red';
    group.add(redLight);

    // Blue strobe light right
    const blueLightGeo = new THREE.BoxGeometry(0.45, 0.15, 0.25);
    const blueLightMat = new THREE.MeshStandardMaterial({
      color: 0x3b82f6,
      emissive: isEmergencyRun ? 0x3b82f6 : 0x1e3a8a,
      emissiveIntensity: isEmergencyRun ? 2.5 : 0.4,
      roughness: 0.1,
    });
    const blueLight = new THREE.Mesh(blueLightGeo, blueLightMat);
    blueLight.position.set(0.35, 1.55, 0.9);
    blueLight.name = 'siren_blue';
    group.add(blueLight);

    // 7. Headlights (Bright warm LED points)
    const headlightMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      emissive: 0xfffbeb,
      emissiveIntensity: 2.0,
    });
    const hlLeft = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.15, 0.05), headlightMat);
    hlLeft.position.set(-0.55, 0.65, 2.36);
    group.add(hlLeft);

    const hlRight = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.15, 0.05), headlightMat);
    hlRight.position.set(0.55, 0.65, 2.36);
    group.add(hlRight);

    // 8. Ground Status Halo / Selection Ring
    const haloGeo = new THREE.RingGeometry(1.6, 2.0, 32);
    const haloMat = new THREE.MeshBasicMaterial({
      color: isSelected ? 0x38bdf8 : statusHex,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: isSelected ? 0.85 : 0.45,
    });
    const halo = new THREE.Mesh(haloGeo, haloMat);
    halo.rotation.x = -Math.PI / 2;
    halo.position.y = 0.04;
    group.add(halo);

    // 9. Floating 3D Code Canvas Tag Billboard
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 80;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = isSelected ? 'rgba(15, 23, 42, 0.95)' : 'rgba(30, 41, 59, 0.88)';
      ctx.roundRect(4, 4, 248, 72, 14);
      ctx.fill();
      ctx.lineWidth = 4;
      ctx.strokeStyle = isSelected ? '#38bdf8' : '#ffffff';
      ctx.stroke();

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 26px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`🚑 ${amb.codigo}`, 128, 38);

      ctx.fillStyle = isEmergencyRun ? '#fbbf24' : '#a7f3d0';
      ctx.font = 'bold 18px monospace';
      ctx.fillText(`${amb.estado.toUpperCase()} • ${amb.velocidad_kmh}km/h`, 128, 62);
    }

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(0, 3.2, 0);
    sprite.scale.set(4.2, 1.4, 1);
    group.add(sprite);

    // Set position in 3D city space
    const pos = latLngTo3D(amb.latitud, amb.longitud);
    group.position.copy(pos);

    // Calculate heading / orientation
    if (amb.target_lat && amb.target_lng) {
      const targetPos = latLngTo3D(amb.target_lat, amb.target_lng);
      group.lookAt(targetPos.x, group.position.y, targetPos.z);
    }

    group.userData = {
      type: 'ambulance',
      id: amb.id,
      codigo: amb.codigo,
      estado: amb.estado,
      ambulance: amb,
    };

    return group;
  };

  // -------------------------------------------------------------
  // BUILD PROCEDURAL REALISTIC 3D HOSPITAL COMPLEX
  // -------------------------------------------------------------
  const createHospitalMesh = (hosp: Hospital) => {
    const group = new THREE.Group();
    group.name = `hospital_${hosp.id}`;

    const occupancyRate = hosp.capacidad > 0 ? hosp.ocupacion / hosp.capacidad : 0;
    const isCritical = occupancyRate > 0.85;

    // 1. Foundation Base Plaza
    const plazaGeo = new THREE.BoxGeometry(10, 0.4, 10);
    const plazaMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.8 });
    const plaza = new THREE.Mesh(plazaGeo, plazaMat);
    plaza.position.y = 0.2;
    plaza.receiveShadow = true;
    group.add(plaza);

    // 2. Main Medical Tower (Multi-story architectural tower)
    const towerGeo = new THREE.BoxGeometry(6.5, 7.5, 5.5);
    const towerMat = new THREE.MeshStandardMaterial({
      color: 0xf1f5f9,
      roughness: 0.35,
      metalness: 0.15,
    });
    const tower = new THREE.Mesh(towerGeo, towerMat);
    tower.position.set(0, 4.15, 0);
    tower.castShadow = true;
    tower.receiveShadow = true;
    group.add(tower);

    // Glass curtain wall windows
    const windowMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x0284c7,
      emissiveIntensity: 0.4,
      roughness: 0.1,
      metalness: 0.9,
    });

    const windowGeo = new THREE.BoxGeometry(5.8, 5.5, 0.1);
    const frontWindows = new THREE.Mesh(windowGeo, windowMat);
    frontWindows.position.set(0, 4.2, 2.8);
    group.add(frontWindows);

    const backWindows = new THREE.Mesh(windowGeo, windowMat);
    backWindows.position.set(0, 4.2, -2.8);
    group.add(backWindows);

    // 3. Emergency Trauma ER Wing (Lower block with ambulance drive-in canopy)
    const erWingGeo = new THREE.BoxGeometry(4.5, 2.8, 4.0);
    const erWingMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.4 });
    const erWing = new THREE.Mesh(erWingGeo, erWingMat);
    erWing.position.set(4.5, 1.6, 1.0);
    erWing.castShadow = true;
    group.add(erWing);

    // ER Entrance Bay Canopy
    const canopyGeo = new THREE.BoxGeometry(3.5, 0.2, 2.5);
    const canopyMat = new THREE.MeshStandardMaterial({ color: 0xdc2626, metalness: 0.4, roughness: 0.3 });
    const canopy = new THREE.Mesh(canopyGeo, canopyMat);
    canopy.position.set(4.5, 2.5, 3.2);
    group.add(canopy);

    // 4. Rooftop Helipad with glowing landing lights
    const helipadGeo = new THREE.CylinderGeometry(2.4, 2.4, 0.15, 32);
    const helipadMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.9 });
    const helipad = new THREE.Mesh(helipadGeo, helipadMat);
    helipad.position.set(0, 8.0, 0);
    group.add(helipad);

    // Helipad Yellow Perimeter Ring
    const heliRingGeo = new THREE.RingGeometry(2.0, 2.25, 32);
    const heliRingMat = new THREE.MeshBasicMaterial({ color: 0xfacc15, side: THREE.DoubleSide });
    const heliRing = new THREE.Mesh(heliRingGeo, heliRingMat);
    heliRing.rotation.x = -Math.PI / 2;
    heliRing.position.set(0, 8.09, 0);
    group.add(heliRing);

    // Glowing Red Cross Sign atop rooftop
    const crossBarMat = new THREE.MeshStandardMaterial({
      color: 0xef4444,
      emissive: 0xef4444,
      emissiveIntensity: 1.8,
      roughness: 0.2,
    });
    const crossV = new THREE.Mesh(new THREE.BoxGeometry(0.5, 2.0, 0.3), crossBarMat);
    const crossH = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.5, 0.3), crossBarMat);
    const crossSign = new THREE.Group();
    crossSign.add(crossV);
    crossSign.add(crossH);
    crossSign.position.set(0, 9.8, 0);
    group.add(crossSign);

    // 5. 3D Live Floating Billboard (Hospital Stats & ER Triage Queue)
    const canvas = document.createElement('canvas');
    canvas.width = 320;
    canvas.height = 130;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
      ctx.roundRect(6, 6, 308, 118, 16);
      ctx.fill();
      ctx.lineWidth = 4;
      ctx.strokeStyle = isCritical ? '#f43f5e' : '#6366f1';
      ctx.stroke();

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 22px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`🏥 ${hosp.nombre}`, 160, 36);

      ctx.fillStyle = '#a5b4fc';
      ctx.font = 'bold 16px sans-serif';
      ctx.fillText(`TRAUMA NIVEL ${hosp.nivel_trauma} • Espera: ${hosp.tiempo_espera_min}m`, 160, 62);

      // Occupancy Progress Bar
      ctx.fillStyle = '#334155';
      ctx.roundRect(24, 76, 272, 18, 9);
      ctx.fill();

      ctx.fillStyle = isCritical ? '#f43f5e' : occupancyRate > 0.65 ? '#f59e0b' : '#10b981';
      ctx.roundRect(24, 76, Math.max(12, 272 * Math.min(1, occupancyRate)), 18, 9);
      ctx.fill();

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 14px monospace';
      ctx.fillText(`Camas: ${hosp.ocupacion}/${hosp.capacidad} (${Math.round(occupancyRate * 100)}%)`, 160, 114);
    }

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(0, 12.8, 0);
    sprite.scale.set(6.4, 2.6, 1);
    group.add(sprite);

    // Set position
    const pos = latLngTo3D(hosp.latitud, hosp.longitud);
    group.position.copy(pos);

    group.userData = {
      type: 'hospital',
      id: hosp.id,
      nombre: hosp.nombre,
      hospital: hosp,
    };

    return group;
  };

  // -------------------------------------------------------------
  // BUILD PROCEDURAL REALISTIC 3D EMS DISPATCH BASE
  // -------------------------------------------------------------
  const createBaseMesh = (base: EMSBase) => {
    const group = new THREE.Group();
    group.name = `base_${base.id}`;

    // 1. Concrete Ground Base
    const groundGeo = new THREE.BoxGeometry(8, 0.3, 8);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.8 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.position.y = 0.15;
    ground.receiveShadow = true;
    group.add(ground);

    // 2. Command Headquarters Building
    const hqGeo = new THREE.BoxGeometry(5.2, 3.2, 5.0);
    const hqMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.4 });
    const hq = new THREE.Mesh(hqGeo, hqMat);
    hq.position.set(0, 1.75, 0);
    hq.castShadow = true;
    group.add(hq);

    // Garage Roll-up Bay Doors for Ambulances
    const bayMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.6, roughness: 0.3 });
    for (let i = 0; i < 3; i++) {
      const bay = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.8, 0.1), bayMat);
      bay.position.set(-1.6 + i * 1.6, 1.0, 2.55);
      group.add(bay);
    }

    // 3. Radio Antenna Tower with Blinking Beacon
    const mastGeo = new THREE.CylinderGeometry(0.08, 0.18, 6.5, 8);
    const mastMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.9 });
    const mast = new THREE.Mesh(mastGeo, mastMat);
    mast.position.set(2.0, 6.4, -1.8);
    group.add(mast);

    // Blinking Red Safety Beacon atop tower
    const beaconGeo = new THREE.SphereGeometry(0.3, 16, 16);
    const beaconMat = new THREE.MeshStandardMaterial({
      color: 0xef4444,
      emissive: 0xef4444,
      emissiveIntensity: 2.5,
    });
    const beacon = new THREE.Mesh(beaconGeo, beaconMat);
    beacon.position.set(2.0, 9.7, -1.8);
    group.add(beacon);

    // 4. Floating 3D Base Badge
    const canvas = document.createElement('canvas');
    canvas.width = 240;
    canvas.height = 80;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
      ctx.roundRect(4, 4, 232, 72, 12);
      ctx.fill();
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#38bdf8';
      ctx.stroke();

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 20px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`🏛️ ${base.nombre}`, 120, 34);

      ctx.fillStyle = '#38bdf8';
      ctx.font = 'bold 15px monospace';
      ctx.fillText(`BASE EMS • Cap: ${base.capacidad} Ambs`, 120, 60);
    }

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(0, 5.8, 0);
    sprite.scale.set(4.5, 1.5, 1);
    group.add(sprite);

    // Set position
    const pos = latLngTo3D(base.latitud, base.longitud);
    group.position.copy(pos);

    group.userData = {
      type: 'base',
      id: base.id,
      nombre: base.nombre,
      base: base,
    };

    return group;
  };

  // -------------------------------------------------------------
  // BUILD PROCEDURAL REALISTIC 3D INCIDENT EMERGENCY BEACONS
  // -------------------------------------------------------------
  const createIncidentMesh = (inc: Incident) => {
    const group = new THREE.Group();
    group.name = `incident_${inc.id}`;

    const priorityHex = inc.prioridad === 'alta' ? 0xef4444 : inc.prioridad === 'media' ? 0xf59e0b : 0x3b82f6;

    // 1. Holographic Ground Pulsing Ring
    const ringGeo = new THREE.RingGeometry(1.2, 2.2, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: priorityHex,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.6,
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.05;
    ring.name = 'pulse_ring';
    group.add(ring);

    // 2. Vertical Emergency Light Pillar / Laser Cone
    const columnGeo = new THREE.CylinderGeometry(0.1, 1.2, 7.0, 16, 1, true);
    const columnMat = new THREE.MeshBasicMaterial({
      color: priorityHex,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide,
    });
    const column = new THREE.Mesh(columnGeo, columnMat);
    column.position.y = 3.5;
    group.add(column);

    // 3. Floating Holographic Diamond / Icon
    const diamondGeo = new THREE.OctahedronGeometry(0.8, 0);
    const diamondMat = new THREE.MeshStandardMaterial({
      color: priorityHex,
      emissive: priorityHex,
      emissiveIntensity: 1.8,
      metalness: 0.5,
      roughness: 0.1,
    });
    const diamond = new THREE.Mesh(diamondGeo, diamondMat);
    diamond.position.y = 5.5;
    diamond.name = 'floating_diamond';
    group.add(diamond);

    // 4. Floating 3D Incident HUD
    const canvas = document.createElement('canvas');
    canvas.width = 240;
    canvas.height = 90;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = 'rgba(15, 23, 42, 0.94)';
      ctx.roundRect(4, 4, 232, 82, 14);
      ctx.fill();
      ctx.lineWidth = 3;
      ctx.strokeStyle = inc.prioridad === 'alta' ? '#ef4444' : '#f59e0b';
      ctx.stroke();

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 20px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`🚨 ${inc.tipo.toUpperCase()}`, 120, 34);

      ctx.fillStyle = inc.prioridad === 'alta' ? '#fca5a5' : '#fde68a';
      ctx.font = 'bold 15px monospace';
      ctx.fillText(`PRIORIDAD: ${inc.prioridad.toUpperCase()}`, 120, 58);

      ctx.fillStyle = '#94a3b8';
      ctx.font = '13px sans-serif';
      ctx.fillText(`Estado: ${inc.estado}`, 120, 76);
    }

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(0, 8.2, 0);
    sprite.scale.set(4.2, 1.6, 1);
    group.add(sprite);

    // Set position
    const pos = latLngTo3D(inc.latitud, inc.longitud);
    group.position.copy(pos);

    group.userData = {
      type: 'incident',
      id: inc.id,
      tipo: inc.tipo,
      prioridad: inc.prioridad,
      incident: inc,
    };

    return group;
  };

  // -------------------------------------------------------------
  // BUILD PROCEDURAL 3D CITY ZONES & BUILDINGS
  // -------------------------------------------------------------
  const buildCityBuildings = () => {
    buildingsGroupRef.current.clear();
    terrainGroupRef.current.clear();

    // 1. City Ground Grid Mesh
    const groundGeo = new THREE.PlaneGeometry(160, 160, 32, 32);
    const groundMat = new THREE.MeshStandardMaterial({
      color: lightingMode === 'night' ? 0x090d16 : 0xe2e8f0,
      roughness: 0.85,
      metalness: 0.1,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.05;
    ground.receiveShadow = true;
    terrainGroupRef.current.add(ground);

    // 2. Zone Footprints and Buildings
    zones.forEach((zone) => {
      const center3D = latLngTo3D(zone.centroide[0], zone.centroide[1]);
      const zoneColorHex = colorMode === 'quintil' ? getQuintileHex(zone.quintil_socioeconomico) : 0x10b981;

      // Zone Boundary Flat Disc / Tile
      const zoneGeo = new THREE.CylinderGeometry(8.5, 8.5, 0.08, 24);
      const zoneMat = new THREE.MeshStandardMaterial({
        color: zoneColorHex,
        roughness: 0.6,
        metalness: 0.1,
        transparent: true,
        opacity: lightingMode === 'night' ? 0.35 : 0.25,
      });
      const zoneTile = new THREE.Mesh(zoneGeo, zoneMat);
      zoneTile.position.set(center3D.x, 0.02, center3D.z);
      zoneTile.receiveShadow = true;
      terrainGroupRef.current.add(zoneTile);

      // Zone Perimeter Glowing Ring
      const ringGeo = new THREE.RingGeometry(8.3, 8.5, 24);
      const ringMat = new THREE.MeshBasicMaterial({
        color: zoneColorHex,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.6,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(center3D.x, 0.07, center3D.z);
      terrainGroupRef.current.add(ring);

      // Generate realistic 3D buildings around zone
      const numBuildings = 6 + (zone.id % 5) * 2;
      for (let b = 0; b < numBuildings; b++) {
        const angle = (b / numBuildings) * Math.PI * 2 + (zone.id * 0.4);
        const dist = 2.5 + ((b * 37) % 5);
        const bx = center3D.x + Math.cos(angle) * dist;
        const bz = center3D.z + Math.sin(angle) * dist;

        const height = 2.5 + ((zone.id * 7 + b * 13) % 12);
        const width = 1.4 + ((b * 3) % 1.5);
        const depth = 1.4 + ((b * 5) % 1.5);

        const bGeo = new THREE.BoxGeometry(width, height, depth);
        const bMat = new THREE.MeshStandardMaterial({
          color: lightingMode === 'night' ? 0x1e293b : 0xcbd5e1,
          roughness: 0.4,
          metalness: 0.3,
        });

        const building = new THREE.Mesh(bGeo, bMat);
        building.position.set(bx, height / 2, bz);
        building.castShadow = true;
        building.receiveShadow = true;
        buildingsGroupRef.current.add(building);

        // Window lighting accents in night mode
        if (lightingMode === 'night' && (b % 2 === 0)) {
          const winGeo = new THREE.BoxGeometry(width * 1.02, height * 0.8, depth * 1.02);
          const winMat = new THREE.MeshBasicMaterial({
            color: b % 3 === 0 ? 0x38bdf8 : 0xfde047,
            transparent: true,
            opacity: 0.25,
          });
          const win = new THREE.Mesh(winGeo, winMat);
          win.position.set(bx, height / 2, bz);
          buildingsGroupRef.current.add(win);
        }
      }
    });
  };

  // -------------------------------------------------------------
  // INITIALIZE THREE.JS ENGINE & RENDER LOOP
  // -------------------------------------------------------------
  useEffect(() => {
    if (!mountRef.current) return;
    const container = mountRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(lightingMode === 'night' ? 0x050811 : lightingMode === 'sunset' ? 0x1e1b4b : 0xf8fafc);
    scene.fog = new THREE.FogExp2(lightingMode === 'night' ? 0x050811 : 0xf1f5f9, 0.007);
    sceneRef.current = scene;

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
    camera.position.set(0, 60, 75);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // 3. Renderer with Anti-Aliasing, Shadows and Tone Mapping
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Lights
    const ambientLight = new THREE.AmbientLight(
      lightingMode === 'night' ? 0x1e293b : 0xffffff,
      lightingMode === 'night' ? 0.6 : 0.8
    );
    scene.add(ambientLight);
    ambientLightRef.current = ambientLight;

    const hemiLight = new THREE.HemisphereLight(
      lightingMode === 'night' ? 0x38bdf8 : 0xffffff,
      lightingMode === 'night' ? 0x090d16 : 0x94a3b8,
      lightingMode === 'night' ? 0.5 : 0.6
    );
    hemiLight.position.set(0, 50, 0);
    scene.add(hemiLight);
    hemiLightRef.current = hemiLight;

    const dirLight = new THREE.DirectionalLight(
      lightingMode === 'sunset' ? 0xf97316 : 0xffffff,
      lightingMode === 'night' ? 1.2 : 1.8
    );
    dirLight.position.set(45, 75, 45);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 10;
    dirLight.shadow.camera.far = 250;
    dirLight.shadow.camera.left = -60;
    dirLight.shadow.camera.right = 60;
    dirLight.shadow.camera.top = 60;
    dirLight.shadow.camera.bottom = -60;
    scene.add(dirLight);
    dirLightRef.current = dirLight;

    // 5. Add Groups to Scene
    scene.add(terrainGroupRef.current);
    scene.add(buildingsGroupRef.current);
    scene.add(basesGroupRef.current);
    scene.add(hospitalsGroupRef.current);
    scene.add(ambulancesGroupRef.current);
    scene.add(incidentsGroupRef.current);
    scene.add(routesGroupRef.current);
    scene.add(particlesGroupRef.current);

    // Initial City Building
    buildCityBuildings();

    // 6. Raycaster for Interaction
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onPointerMove = (e: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      // Handle Orbit Dragging
      if (isDragging.current) {
        const deltaX = e.clientX - previousMousePosition.current.x;
        const deltaY = e.clientY - previousMousePosition.current.y;

        orbitAngles.current.theta -= deltaX * 0.008;
        orbitAngles.current.phi = Math.max(0.1, Math.min(Math.PI / 2.1, orbitAngles.current.phi - deltaY * 0.008));

        previousMousePosition.current = { x: e.clientX, y: e.clientY };
      }
    };

    const onPointerDown = (e: MouseEvent) => {
      isDragging.current = true;
      previousMousePosition.current = { x: e.clientX, y: e.clientY };
    };

    const onPointerUp = (e: MouseEvent) => {
      isDragging.current = false;

      // Click Selection Raycast
      const rect = renderer.domElement.getBoundingClientRect();
      const clickMouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );
      raycaster.setFromCamera(clickMouse, camera);

      const clickableGroups = [
        ...ambulancesGroupRef.current.children,
        ...hospitalsGroupRef.current.children,
        ...basesGroupRef.current.children,
        ...incidentsGroupRef.current.children,
      ];

      const intersects = raycaster.intersectObjects(clickableGroups, true);
      if (intersects.length > 0) {
        // Find top group with userData
        let curr: THREE.Object3D | null = intersects[0].object;
        while (curr && !curr.userData?.type && curr.parent) {
          curr = curr.parent;
        }

        if (curr && curr.userData) {
          if (curr.userData.type === 'ambulance') {
            onSelectAmbulance(curr.userData.ambulance);
          } else if (curr.userData.type === 'hospital') {
            // Find closest zone
            const zone = zones.find((z) => z.id === curr?.userData.hospital.zona_id) || null;
            if (zone) onSelectZone(zone);
          }
        }
      }
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      orbitAngles.current.radius = Math.max(20, Math.min(140, orbitAngles.current.radius + e.deltaY * 0.05));
    };

    const dom = renderer.domElement;
    dom.addEventListener('pointermove', onPointerMove);
    dom.addEventListener('pointerdown', onPointerDown);
    dom.addEventListener('pointerup', onPointerUp);
    dom.addEventListener('wheel', onWheel, { passive: false });

    // 7. Animation Loop
    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate);
      const elapsedTime = clockRef.current.getElapsedTime();

      // Animate Siren Strobes on Ambulances
      const isRedPhase = Math.floor(elapsedTime * 8) % 2 === 0;
      ambulancesGroupRef.current.children.forEach((ambGroup) => {
        const redLight = ambGroup.getObjectByName('siren_red') as THREE.Mesh;
        const blueLight = ambGroup.getObjectByName('siren_blue') as THREE.Mesh;
        if (redLight && blueLight) {
          (redLight.material as THREE.MeshStandardMaterial).emissiveIntensity = isRedPhase ? 3.5 : 0.2;
          (blueLight.material as THREE.MeshStandardMaterial).emissiveIntensity = isRedPhase ? 0.2 : 3.5;
        }
      });

      // Animate Incidents (Pulse Ring & Floating Diamond)
      incidentsGroupRef.current.children.forEach((incGroup) => {
        const pulseRing = incGroup.getObjectByName('pulse_ring') as THREE.Mesh;
        const diamond = incGroup.getObjectByName('floating_diamond') as THREE.Mesh;

        if (pulseRing) {
          const scale = 1.0 + ((elapsedTime * 1.5) % 1) * 0.8;
          pulseRing.scale.set(scale, scale, 1);
          (pulseRing.material as THREE.MeshBasicMaterial).opacity = 0.8 * (1 - ((elapsedTime * 1.5) % 1));
        }

        if (diamond) {
          diamond.rotation.y = elapsedTime * 2;
          diamond.position.y = 5.5 + Math.sin(elapsedTime * 3) * 0.4;
        }
      });

      // Camera Positioning Logic
      if (cameraMode === 'follow' && selectedAmbulance) {
        const ambPos = latLngTo3D(selectedAmbulance.latitud, selectedAmbulance.longitud);
        cameraLookAtTarget.current.copy(ambPos);
        cameraPosTarget.current.set(ambPos.x, ambPos.y + 12, ambPos.z + 18);
      } else if (cameraMode === 'topdown') {
        cameraLookAtTarget.current.set(0, 0, 0);
        cameraPosTarget.current.set(0, 95, 0.01);
      } else if (cameraMode === 'cinematic') {
        const angle = elapsedTime * 0.15;
        cameraLookAtTarget.current.set(0, 0, 0);
        cameraPosTarget.current.set(Math.cos(angle) * 75, 45, Math.sin(angle) * 75);
      } else {
        // Isometric Orbit
        const { theta, phi, radius } = orbitAngles.current;
        const x = radius * Math.sin(phi) * Math.sin(theta);
        const y = radius * Math.cos(phi);
        const z = radius * Math.sin(phi) * Math.cos(theta);
        cameraPosTarget.current.set(x, y, z);
        cameraLookAtTarget.current.set(0, 0, 0);
      }

      // Smooth Camera Interpolation (Damping)
      camera.position.lerp(cameraPosTarget.current, 0.06);
      currentCameraLookAt.current.lerp(cameraLookAtTarget.current, 0.08);
      camera.lookAt(currentCameraLookAt.current);

      renderer.render(scene, camera);
    };

    animate();

    // Resize Handler
    const handleResize = () => {
      if (!mountRef.current || !renderer || !camera) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      dom.removeEventListener('pointermove', onPointerMove);
      dom.removeEventListener('pointerdown', onPointerDown);
      dom.removeEventListener('pointerup', onPointerUp);
      dom.removeEventListener('wheel', onWheel);
      renderer.dispose();
    };
  }, [lightingMode]);

  // -------------------------------------------------------------
  // REBUILD DYNAMIC LAYERS (Ambulances, Hospitals, Bases, Incidents)
  // -------------------------------------------------------------
  useEffect(() => {
    // 1. Rebuild Ambulances
    ambulancesGroupRef.current.clear();
    ambulances.forEach((amb) => {
      const isSelected = selectedAmbulance?.id === amb.id;
      const mesh = createAmbulanceMesh(amb, isSelected);
      ambulancesGroupRef.current.add(mesh);
    });

    // 2. Rebuild Hospitals
    hospitalsGroupRef.current.clear();
    hospitals.forEach((hosp) => {
      const mesh = createHospitalMesh(hosp);
      hospitalsGroupRef.current.add(mesh);
    });

    // 3. Rebuild Bases
    basesGroupRef.current.clear();
    bases.forEach((base) => {
      const mesh = createBaseMesh(base);
      basesGroupRef.current.add(mesh);
    });

    // 4. Rebuild Incidents
    incidentsGroupRef.current.clear();
    const activeIncidents = incidents.filter(
      (i) => i.estado === 'pendiente' || i.estado === 'despachado' || i.estado === 'en_atencion' || i.estado === 'trasladando'
    );
    activeIncidents.forEach((inc) => {
      const mesh = createIncidentMesh(inc);
      incidentsGroupRef.current.add(mesh);
    });

    // 5. Rebuild 3D Trajectory Arcs
    routesGroupRef.current.clear();
    if (showRoutes3D) {
      ambulances.forEach((amb) => {
        if (amb.target_lat && amb.target_lng && (amb.estado === 'en ruta' || amb.estado === 'trasladando')) {
          const start = latLngTo3D(amb.latitud, amb.longitud, 0.8);
          const end = latLngTo3D(amb.target_lat, amb.target_lng, 0.8);
          const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
          mid.y += Math.min(12, start.distanceTo(end) * 0.25); // Parabolic elevation arc

          const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
          const points = curve.getPoints(32);
          const geo = new THREE.BufferGeometry().setFromPoints(points);

          const isTransport = amb.estado === 'trasladando';
          const lineMat = new THREE.LineBasicMaterial({
            color: isTransport ? 0x8b5cf6 : 0x0284c7,
            linewidth: 3,
          });

          const routeLine = new THREE.Line(geo, lineMat);
          routesGroupRef.current.add(routeLine);
        }
      });
    }
  }, [ambulances, hospitals, bases, incidents, relocations, selectedAmbulance, showRoutes3D]);

  // Lighting theme update
  useEffect(() => {
    if (!sceneRef.current) return;
    const scene = sceneRef.current;
    scene.background = new THREE.Color(lightingMode === 'night' ? 0x050811 : lightingMode === 'sunset' ? 0x1e1b4b : 0xf8fafc);
    scene.fog = new THREE.FogExp2(lightingMode === 'night' ? 0x050811 : 0xf1f5f9, 0.007);

    if (ambientLightRef.current) {
      ambientLightRef.current.color.setHex(lightingMode === 'night' ? 0x1e293b : 0xffffff);
      ambientLightRef.current.intensity = lightingMode === 'night' ? 0.6 : 0.9;
    }

    if (dirLightRef.current) {
      dirLightRef.current.color.setHex(lightingMode === 'sunset' ? 0xf97316 : 0xffffff);
      dirLightRef.current.intensity = lightingMode === 'night' ? 1.2 : 1.8;
    }

    buildCityBuildings();
  }, [lightingMode, colorMode]);

  return (
    <div className="relative w-full h-[660px] rounded-2xl overflow-hidden border border-slate-700/80 shadow-2xl bg-slate-950 flex flex-col font-sans select-none" id="digital-twin-3d-wrapper">
      {/* 3D Canvas Mount Point */}
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Top Floating Glass Command Bar */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none z-20">
        {/* Left: Branding & Status Badge */}
        <div className="pointer-events-auto flex items-center space-x-2 bg-slate-900/85 backdrop-blur-md px-3.5 py-2 rounded-xl border border-slate-700/80 shadow-lg text-white">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></div>
          <div>
            <div className="text-xs font-bold tracking-wide flex items-center space-x-1.5">
              <span>GEMELO DIGITAL 3D &bull; WEBGL ENGINE</span>
              <span className="px-1.5 py-0.2 rounded bg-indigo-500/30 text-indigo-300 font-mono text-[10px] border border-indigo-500/40">
                REAL-TIME
              </span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono">
              Flota: {ambulances.length} Ambs | Hospitales: {hospitals.length} | LLamadas Activas: {incidents.filter(i => i.estado === 'pendiente' || i.estado === 'despachado').length}
            </div>
          </div>
        </div>

        {/* Right: Lighting and Camera Mode Controls */}
        <div className="pointer-events-auto flex items-center space-x-2">
          {/* Lighting Mode Selector */}
          <div className="flex items-center bg-slate-900/85 backdrop-blur-md p-1 rounded-xl border border-slate-700/80 shadow-lg text-xs">
            <button
              onClick={() => setLightingMode('night')}
              className={`px-2.5 py-1.5 rounded-lg flex items-center space-x-1.5 font-medium transition-all ${
                lightingMode === 'night' ? 'bg-indigo-600 text-white font-bold shadow' : 'text-slate-400 hover:text-white'
              }`}
              title="Modo Noche Táctica Digital Twin"
            >
              <Moon className="w-3.5 h-3.5" />
              <span>Noche</span>
            </button>
            <button
              onClick={() => setLightingMode('sunset')}
              className={`px-2.5 py-1.5 rounded-lg flex items-center space-x-1.5 font-medium transition-all ${
                lightingMode === 'sunset' ? 'bg-amber-600 text-white font-bold shadow' : 'text-slate-400 hover:text-white'
              }`}
              title="Atardecer Urbano"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Atardecer</span>
            </button>
            <button
              onClick={() => setLightingMode('day')}
              className={`px-2.5 py-1.5 rounded-lg flex items-center space-x-1.5 font-medium transition-all ${
                lightingMode === 'day' ? 'bg-sky-600 text-white font-bold shadow' : 'text-slate-400 hover:text-white'
              }`}
              title="Luz Solar Diurna"
            >
              <Sun className="w-3.5 h-3.5" />
              <span>Día</span>
            </button>
          </div>

          {/* Camera Perspective Presets */}
          <div className="flex items-center bg-slate-900/85 backdrop-blur-md p-1 rounded-xl border border-slate-700/80 shadow-lg text-xs">
            <button
              onClick={() => {
                setCameraMode('isometric');
                orbitAngles.current = { theta: Math.PI / 4, phi: Math.PI / 3.2, radius: 80 };
              }}
              className={`px-2.5 py-1.5 rounded-lg font-medium transition-all ${
                cameraMode === 'isometric' ? 'bg-slate-700 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Isométrica 45°
            </button>
            <button
              onClick={() => setCameraMode('topdown')}
              className={`px-2.5 py-1.5 rounded-lg font-medium transition-all ${
                cameraMode === 'topdown' ? 'bg-slate-700 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Cenital Táctica
            </button>
            <button
              onClick={() => setCameraMode('follow')}
              disabled={!selectedAmbulance}
              className={`px-2.5 py-1.5 rounded-lg flex items-center space-x-1 font-medium transition-all ${
                cameraMode === 'follow'
                  ? 'bg-rose-600 text-white font-bold'
                  : selectedAmbulance
                  ? 'text-slate-400 hover:text-white'
                  : 'text-slate-600 cursor-not-allowed'
              }`}
              title={selectedAmbulance ? `Seguir a ${selectedAmbulance.codigo}` : 'Selecciona una ambulancia para seguirla'}
            >
              <Crosshair className="w-3.5 h-3.5" />
              <span>Seguimiento {selectedAmbulance ? selectedAmbulance.codigo : ''}</span>
            </button>
            <button
              onClick={() => setCameraMode('cinematic')}
              className={`px-2.5 py-1.5 rounded-lg font-medium transition-all ${
                cameraMode === 'cinematic' ? 'bg-slate-700 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Órbita 360°
            </button>
          </div>
        </div>
      </div>

      {/* Floating 3D Navigation & Gesture Helper */}
      <div className="absolute bottom-3 left-3 pointer-events-none z-20">
        <div className="pointer-events-auto bg-slate-900/85 backdrop-blur-md px-3.5 py-2.5 rounded-xl border border-slate-700/80 shadow-lg text-slate-300 text-xs space-y-1">
          <div className="font-bold text-white text-[11px] flex items-center space-x-1.5">
            <Compass className="w-3.5 h-3.5 text-indigo-400" />
            <span>Controles de Navegación 3D</span>
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px] text-slate-400">
            <span>🖱️ Arrastrar Click Izq: <b>Rotar Órbita</b></span>
            <span>⚙️ Rueda Ratón: <b>Zoom In / Out</b></span>
            <span>👆 Click Objeto: <b>Inspeccionar Estado</b></span>
            <span>🚗 Seguir Vehículo: <b>Cámara Chase</b></span>
          </div>
        </div>
      </div>

      {/* Selected Unit / Hospital 3D Holographic HUD Inspector */}
      {selectedAmbulance && (
        <div className="absolute bottom-3 right-3 pointer-events-auto z-20 bg-slate-900/90 backdrop-blur-md p-3.5 rounded-2xl border border-indigo-500/50 shadow-2xl text-white text-xs max-w-sm w-80 animate-in fade-in slide-in-from-bottom-2">
          <div className="flex items-center justify-between border-b border-slate-700/80 pb-2 mb-2">
            <div className="flex items-center space-x-2">
              <span className="p-1.5 rounded-lg bg-indigo-600/30 text-indigo-400 border border-indigo-500/30 font-mono text-sm">
                🚑
              </span>
              <div>
                <span className="font-bold text-sm text-white">{selectedAmbulance.codigo}</span>
                <div className="text-[10px] text-slate-400">Base Asignada: Base {selectedAmbulance.base_id}</div>
              </div>
            </div>
            <span
              className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider text-white"
              style={{ backgroundColor: '#' + getStatusHex(selectedAmbulance.estado).toString(16).padStart(6, '0') }}
            >
              {selectedAmbulance.estado}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="p-2 rounded-lg bg-slate-800/60 border border-slate-700/50">
              <span className="text-slate-400 text-[10px] block">Velocidad Actual</span>
              <span className="font-mono font-bold text-sm text-cyan-400">{selectedAmbulance.velocidad_kmh} km/h</span>
            </div>
            <div className="p-2 rounded-lg bg-slate-800/60 border border-slate-700/50">
              <span className="text-slate-400 text-[10px] block">Odómetro Total</span>
              <span className="font-mono font-bold text-sm text-emerald-400">{selectedAmbulance.kilometraje_total.toFixed(1)} km</span>
            </div>
            <div className="p-2 rounded-lg bg-slate-800/60 border border-slate-700/50">
              <span className="text-slate-400 text-[10px] block">Emergencias Atendidas</span>
              <span className="font-mono font-bold text-sm text-amber-400">{selectedAmbulance.incidentes_atendidos}</span>
            </div>
            <div className="p-2 rounded-lg bg-slate-800/60 border border-slate-700/50">
              <span className="text-slate-400 text-[10px] block">Misión Activa</span>
              <span className="font-mono font-semibold text-slate-200 truncate block">
                {selectedAmbulance.incidente_asignado_id || 'En Espera'}
              </span>
            </div>
          </div>

          <div className="mt-2.5 pt-2 border-t border-slate-700/60 flex items-center justify-between">
            <button
              onClick={() => setCameraMode('follow')}
              className="w-full py-1.5 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center justify-center space-x-1.5 transition-colors shadow-md"
            >
              <Crosshair className="w-3.5 h-3.5" />
              <span>Bloquear Cámara en Ambulancia</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
