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
    }
  }, [selectedRegion, globeReady]);

  // Remove old globeReady effect (now handled by onGlobeReady)
  // Set globeReady when Globe is mounted
  useEffect(() => {
    if (globeRef.current) setGlobeReady(true);
  }, [dimensions]);

  useEffect(() => {
    // Set initial dimensions on client — full width on mobile, half on desktop
    const updateDimensions = () => {
      const isMobile = window.innerWidth < 768;
      setDimensions({
        width: isMobile ? window.innerWidth : window.innerWidth * 0.5,
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
    <div className="w-full h-screen max-w-full max-h-screen relative">
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
    </div>
  );
}