"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import * as THREE from "three";

const Globe = dynamic(() => import("react-globe.gl"), { ssr: false });


interface GlobeViewerProps {
  selectedRegion?: { lat: number; lng: number } | null;
  carbonData?: any;
}

export default function GlobeViewer({ selectedRegion, carbonData }: GlobeViewerProps) {
  const globeRef = useRef<any>(null);
  const [globeReady, setGlobeReady] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [regionScreenPos, setRegionScreenPos] = useState<{ x: number; y: number } | null>(null);
  // Focus globe on selected region when it changes
  // Handle auto-rotation and focus logic
  useEffect(() => {
    if (!globeReady || !globeRef.current) {
      console.log("[GlobeViewer] Globe not ready", { globeReady, globeRef: globeRef.current });
      return;
    }
    const globe = globeRef.current;
    if (typeof globe.controls === "function") {
      const controls = globe.controls();
      if (controls) {
        if (selectedRegion) {
          controls.autoRotate = false;
          console.log("[GlobeViewer] Auto-rotate OFF (region selected)");
        } else {
          controls.autoRotate = true;
          controls.autoRotateSpeed = 0.35;
          console.log("[GlobeViewer] Auto-rotate ON (no region selected)");
        }
      }
    }
    if (selectedRegion && typeof globe.pointOfView === "function") {
      globe.pointOfView({ lat: selectedRegion.lat, lng: selectedRegion.lng, altitude: 2 }, 1000);
      console.log("[GlobeViewer] Focusing on region", selectedRegion);
      
      // Calculate screen position of the region after focusing
      setTimeout(() => {
        if (typeof globe.getScreenCoords === "function") {
          const screenCoords = globe.getScreenCoords(selectedRegion.lat, selectedRegion.lng);
          if (screenCoords) {
            setRegionScreenPos({ x: screenCoords.x, y: screenCoords.y });
            console.log("[GlobeViewer] Region screen position:", screenCoords);
          }
        }
      }, 1100); // Wait for focus animation to complete
    } else {
      setRegionScreenPos(null);
    }
  }, [selectedRegion, globeReady]);

  // Remove old globeReady effect (now handled by onGlobeReady)
  // Set globeReady when Globe is mounted
  useEffect(() => {
    if (globeRef.current) setGlobeReady(true);
  }, [dimensions]);

  useEffect(() => {
    // Set initial dimensions on client
    const updateDimensions = () => {
      setDimensions({
        width: window.innerWidth * 0.5,
        height: window.innerHeight,
      });
    };
    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  // Add clouds once when globe is ready
  useEffect(() => {
    if (!globeReady || !globeRef.current) {
      console.log("[GlobeViewer] Globe not ready for clouds", { globeReady, globeRef: globeRef.current });
      return;
    }
    const globe = globeRef.current;
    // Make canvas background transparent (show only the globe)
    if (typeof globe.renderer === "function") {
      const renderer = globe.renderer();
      if (renderer) {
        renderer.setClearColor(0x000000, 0);
        if (renderer.domElement) renderer.domElement.style.background = "transparent";
      }
    }
    const CLOUDS_IMG_URL = "/clouds.png";
    const CLOUDS_ALT = 0.004;
    const CLOUDS_ROTATION_SPEED = -0.006;
    // Defensive: check getGlobeRadius and scene
    if (typeof globe.getGlobeRadius === "function" && typeof globe.scene === "function") {
      // Prevent duplicate clouds
      if (!globe.scene().getObjectByName("clouds-layer")) {
        new THREE.TextureLoader().load(CLOUDS_IMG_URL, (cloudsTexture) => {
          const clouds = new THREE.Mesh(
            new THREE.SphereGeometry(
              globe.getGlobeRadius() * (1 + CLOUDS_ALT),
              75,
              75
            ),
            new THREE.MeshPhongMaterial({
              map: cloudsTexture,
              transparent: true,
            })
          );
          clouds.name = "clouds-layer";
          globe.scene().add(clouds);
          console.log("[GlobeViewer] Clouds added");
          // Animate clouds
          const rotateClouds = () => {
            clouds.rotation.y += (CLOUDS_ROTATION_SPEED * Math.PI) / 180;
            requestAnimationFrame(rotateClouds);
          };
          rotateClouds();
        });
      } else {
        console.log("[GlobeViewer] Clouds already present");
      }
    } else {
      console.log("[GlobeViewer] Globe radius or scene not available");
    }
  }, [globeReady]);

  return (
    <div className="w-[50vw] h-screen max-w-full max-h-screen right-10 relative">
      {dimensions.width > 0 && dimensions.height > 0 && (
        <Globe
          ref={globeRef}
          globeImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/earth-blue-marble.jpg"
          bumpImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/earth-topology.png"
          backgroundColor="rgba(0,0,0,0)"
          width={dimensions.width}
          height={dimensions.height}
          onGlobeReady={() => {
            setGlobeReady(true);
            console.log('[GlobeViewer] Globe is now ready');
          }}
        />
      )}
      {/* Carbon Data Display */}
      {selectedRegion && carbonData && (
        <div className="absolute top-6 right-6 bg-black bg-opacity-80 text-white p-2 rounded-md shadow-lg max-w-xs text-xs" style={{ minWidth: '160px' }}>
          <div className="relative">
            {/* Dynamic Pointer line */}
            {regionScreenPos && (
              <>
                <svg
                  className="absolute -z-10"
                  style={{
                    width: '500px',
                    height: '500px',
                    top: '50%',
                    right: '100%',
                    transform: 'translate(0, -50%)',
                  }}
                >
                  <line
                    x1="400"
                    y1="200"
                    x2={Math.max(0, Math.min(400, regionScreenPos.x - dimensions.width * 0.5 + 200))}
                    y2={Math.max(0, Math.min(400, regionScreenPos.y - 32 + 200))}
                    stroke="white"
                    strokeWidth="2"
                  />
                  <circle
                    cx={Math.max(0, Math.min(400, regionScreenPos.x - dimensions.width * 0.5 + 200))}
                    cy={Math.max(0, Math.min(400, regionScreenPos.y - 32 + 200))}
                    r="4"
                    fill="white"
                  />
                </svg>
              </>
            )}
            
            {/* Carbon Data Content */}
            <div className="space-y-1 text-xs">
              <div className="font-bold text-base mb-1 text-center border-b border-gray-400 pb-1">
                {carbonData.region || 'Unknown Region'}
              </div>
              <div><span className="font-semibold">Provider:</span> <span className="text-gray-300">{carbonData.provider}</span></div>
              <div className="font-semibold text-green-500 text-center text-lg">
                {carbonData.co2_grams_per_hour !== 'N/A' 
                  ? `${parseFloat(carbonData.co2_grams_per_hour).toFixed(2)} g CO₂/hour` 
                  : 'CO₂ data not available'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}