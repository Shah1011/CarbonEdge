"use client";

import { useState, useEffect, ChangeEvent, FormEvent } from "react";
import ForecastChart, { ForecastData } from "./components/ForecastChart";
import GlobeViewer from "./components/GlobeViewer";

// ═══════════════════════════════════════════════════════════════════════════
// Types & Interfaces
// ═══════════════════════════════════════════════════════════════════════════

interface ProviderFlags {
  aws: boolean;
  azure: boolean;
  gcp: boolean;
}

interface FormState {
  vcpuRam: string;
  storage: string;
  utilization: number;
  providers: ProviderFlags;
  searchCheapest: boolean;
  searchLowestCO2: boolean;
}

type AppMode = "decision" | "forecast";

interface ForecastRegionSummary {
  group_id: string;
  provider: string;
  region: string;
  summary: {
    forecast_avg_gCO2: number;
    recent_avg_gCO2: number;
    trend: "increasing" | "decreasing" | "stable";
    prediction_days: number;
    unit: string;
  };
}

interface RegionCoords {
  [region: string]: { lat: number; lng: number };
}

interface CarbonEmissions {
  gco2_per_kwh?: number;
  co2_grams_per_hour?: number;
  [key: string]: any;
}

interface Instance {
  instance_type: string;
  region: string;
  price_usd_per_hour: number;
  actual_vcpus?: number;
  actual_ram_gb?: number;
  storage_type?: string;
  instance_storage_gb?: number;
  carbon_emissions?: CarbonEmissions;
  carbon_forecast?: any;
  [key: string]: any;
}

interface ProviderData {
  instances: Instance[];
  [key: string]: any;
}

interface Results {
  [provider: string]: ProviderData;
}

interface SelectedRegion {
  lat: number;
  lng: number;
}

interface SelectedCarbonData {
  region: string;
  provider: string;
  vcpus?: number;
  ram_gb?: number;
  storage_type?: string;
  storage_gb?: number;
  carbon_emissions?: CarbonEmissions;
  co2_grams_per_hour?: number | string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════════════════

const VCPU_RAM_OPTIONS = [
  { label: "1 vCPU · 2 GB", value: "1-2" },
  { label: "2 vCPUs · 4 GB", value: "2-4" },
  { label: "4 vCPUs · 8 GB", value: "4-8" },
  { label: "4 vCPUs · 16 GB", value: "4-16" },
  { label: "8 vCPUs · 32 GB", value: "8-32" },
  { label: "16 vCPUs · 64 GB", value: "16-64" },
  { label: "32 vCPUs · 128 GB", value: "32-128" },
];

const loadRegionCoords = async (): Promise<RegionCoords> => {
  try {
    const response = await fetch("/api/region-coordinates");
    if (response.ok) return await response.json();
  } catch (error) {
    console.error("Failed to load region coordinates:", error);
  }
  return {
    centralus: { lat: 41.5908, lng: -93.6208 },
    "us-east-1": { lat: 39.0438, lng: -77.4874 },
    "us-west-1": { lat: 37.3382, lng: -121.8863 },
    "us-west-2": { lat: 45.5152, lng: -122.6784 },
    "us-east-2": { lat: 39.9612, lng: -82.9988 },
  };
};

// ═══════════════════════════════════════════════════════════════════════════
// Sub-Components
// ═══════════════════════════════════════════════════════════════════════════

function ModeToggle({ mode, setMode }: { mode: AppMode; setMode: (m: AppMode) => void }) {
  return (
    <div className="flex bg-slate-800/60 rounded-xl p-1 gap-1 border border-slate-700/50 backdrop-blur-sm">
      <button
        type="button"
        onClick={() => setMode("decision")}
        className={`flex-1 px-3 sm:px-5 py-2 sm:py-2.5 rounded-lg text-sm font-medium transition-all duration-300 ${
          mode === "decision"
            ? "bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/25"
            : "text-slate-400 hover:text-white hover:bg-slate-700/50"
        }`}
      >
        <span className="flex items-center justify-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Decision
        </span>
      </button>
      <button
        type="button"
        onClick={() => setMode("forecast")}
        className={`flex-1 px-3 sm:px-5 py-2 sm:py-2.5 rounded-lg text-sm font-medium transition-all duration-300 ${
          mode === "forecast"
            ? "bg-gradient-to-r from-emerald-600 to-emerald-500 text-white shadow-lg shadow-emerald-500/25"
            : "text-slate-400 hover:text-white hover:bg-slate-700/50"
        }`}
      >
        <span className="flex items-center justify-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          Forecast
        </span>
      </button>
    </div>
  );
}

function ProviderChip({
  provider,
  checked,
  onChange,
}: {
  provider: string;
  checked: boolean;
  onChange: () => void;
}) {
  const colorClasses: Record<string, { checked: string; unchecked: string }> = {
    aws: {
      checked: "bg-orange-500/20 border-orange-500/50 text-orange-400",
      unchecked: "bg-slate-800/40 border-slate-700/50 text-slate-500 hover:border-slate-600",
    },
    azure: {
      checked: "bg-blue-500/20 border-blue-500/50 text-blue-400",
      unchecked: "bg-slate-800/40 border-slate-700/50 text-slate-500 hover:border-slate-600",
    },
    gcp: {
      checked: "bg-red-500/20 border-red-500/50 text-red-400",
      unchecked: "bg-slate-800/40 border-slate-700/50 text-slate-500 hover:border-slate-600",
    },
  };

  const colors = colorClasses[provider.toLowerCase()] || colorClasses.aws;

  return (
    <button
      type="button"
      onClick={onChange}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all duration-200 ${
        checked ? colors.checked : colors.unchecked
      }`}
    >
      <img
        src={`/${provider.toLowerCase()}.png`}
        alt={provider}
        className="w-5 h-5 object-contain"
        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
      />
      <span className="text-sm font-bold uppercase">{provider}</span>
      {checked && (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      )}
    </button>
  );
}

function InputField({
  label,
  icon,
  children,
}: {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
        {icon}
        {label}
      </label>
      {children}
    </div>
  );
}

function ResultCard({
  instance,
  provider,
  rank,
  onClick,
  onViewForecast,
  isEcoOptimized,
  isCheapest,
  isLowestCO2,
}: {
  instance: Instance;
  provider: string;
  rank: number;
  onClick: () => void;
  onViewForecast: () => void;
  isEcoOptimized?: boolean;
  isCheapest?: boolean;
  isLowestCO2?: boolean;
}) {
  const providerName =
    provider === "aws" ? "Amazon Web Services" :
    provider === "azure" ? "Microsoft Azure" :
    provider === "gcp" ? "Google Cloud" : provider;

  const trendColor =
    instance.carbon_forecast?.trend === "decreasing" ? "text-emerald-400" :
    instance.carbon_forecast?.trend === "increasing" ? "text-red-400" : "text-amber-400";

  return (
    <div
      className="group relative bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5 transition-all duration-300"
    >
      {/* Rank Badge */}
      <div className="absolute -top-2 -left-2 w-8 h-8 bg-gradient-to-br from-slate-700 to-slate-800 border border-slate-600 rounded-full flex items-center justify-center text-xs font-bold text-slate-300">
        {rank}
      </div>

      {/* Status Badges */}
      <div className="absolute -top-2 right-3 flex gap-1.5">
        {isEcoOptimized && (
          <span className="px-2.5 py-1 bg-gradient-to-r from-emerald-600 to-teal-600 text-white text-xs font-semibold rounded-full shadow-lg">
            Eco-Optimized
          </span>
        )}
        {isCheapest && !isEcoOptimized && (
          <span className="px-2.5 py-1 bg-gradient-to-r from-blue-600 to-cyan-600 text-white text-xs font-semibold rounded-full shadow-lg">
            Cheapest
          </span>
        )}
        {isLowestCO2 && !isEcoOptimized && (
          <span className="px-2.5 py-1 bg-gradient-to-r from-green-600 to-emerald-600 text-white text-xs font-semibold rounded-full shadow-lg">
            Lowest CO₂
          </span>
        )}
      </div>

      {/* Header */}
      <div className="flex items-start gap-4 mb-4 mt-2">
        <img
          src={`/${provider.toLowerCase()}.png`}
          alt={provider}
          className="w-10 h-10 object-contain"
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-white truncate">{instance.instance_type}</h3>
          <p className="text-sm text-slate-400">{providerName}</p>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-slate-900/50 rounded-lg px-3 py-2">
          <p className="text-xs text-slate-500 mb-0.5">Region</p>
          <p className="text-sm font-medium text-slate-200 truncate">{instance.region}</p>
        </div>
        <div className="bg-slate-900/50 rounded-lg px-3 py-2">
          <p className="text-xs text-slate-500 mb-0.5">Price</p>
          <p className="text-sm font-semibold text-blue-400">${instance.price_usd_per_hour?.toFixed(4)}/hr</p>
        </div>
        <div className="bg-slate-900/50 rounded-lg px-3 py-2">
          <p className="text-xs text-slate-500 mb-0.5">CO₂ Emission</p>
          <p className="text-sm font-medium text-emerald-400">
            {instance.carbon_emissions?.co2_grams_per_hour?.toFixed(2) ?? "N/A"} g/hr
          </p>
        </div>
        <div className="bg-slate-900/50 rounded-lg px-3 py-2">
          <p className="text-xs text-slate-500 mb-0.5">Specs</p>
          <p className="text-sm font-medium text-slate-200">
            {instance.vcpus ?? instance.actual_vcpus ?? "?"} vCPU · {instance.ram_gb ?? instance.actual_ram_gb ?? "?"} GB
          </p>
        </div>
      </div>

      {/* Forecast Badge */}
      {instance.carbon_forecast && (
        <div className={`flex items-center gap-2 text-xs mb-3 ${trendColor}`}>
          <span>
            {instance.carbon_forecast.trend === "decreasing" ? "↓" :
             instance.carbon_forecast.trend === "increasing" ? "↑" : "→"}
          </span>
          <span>
            7d Forecast: {instance.carbon_forecast.forecast_avg_gCO2} {instance.carbon_forecast.unit}
          </span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          onClick={onClick}
          className="hidden md:flex flex-1 px-3 py-2 bg-slate-700/50 hover:bg-slate-700 border border-slate-600/50 rounded-lg text-slate-300 hover:text-white text-sm font-medium transition-all items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Globe
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onViewForecast();
          }}
          className="flex-1 px-3 py-2 bg-emerald-600/10 hover:bg-emerald-600/20 border border-emerald-600/30 rounded-lg text-emerald-400 hover:text-emerald-300 text-sm font-medium transition-all flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Forecast
        </button>
      </div>
    </div>
  );
}

function ForecastRegionCard({
  region,
  rank,
  onClick,
  onViewForecast,
}: {
  region: ForecastRegionSummary;
  rank: number;
  onClick: () => void;
  onViewForecast: () => void;
}) {
  const providerName =
    region.provider.toLowerCase() === "aws" ? "Amazon Web Services" :
    region.provider.toLowerCase() === "azure" ? "Microsoft Azure" :
    region.provider.toLowerCase() === "gcp" ? "Google Cloud" : region.provider;

  const trendColor =
    region.summary.trend === "decreasing" ? "text-emerald-400 bg-emerald-500/10" :
    region.summary.trend === "increasing" ? "text-red-400 bg-red-500/10" : "text-amber-400 bg-amber-500/10";

  const trendIcon =
    region.summary.trend === "decreasing" ? "↓" :
    region.summary.trend === "increasing" ? "↑" : "→";

  return (
    <div
      className="group relative bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5 transition-all duration-300"
    >
      {/* Rank Badge */}
      <div className={`absolute -top-2 -left-2 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
        rank === 1 ? "bg-gradient-to-br from-emerald-500 to-teal-600 text-white" : "bg-gradient-to-br from-slate-700 to-slate-800 border border-slate-600 text-slate-300"
      }`}>
        {rank === 1 ? "★" : rank}
      </div>

      {rank === 1 && (
        <span className="absolute -top-2 right-3 px-2.5 py-1 bg-gradient-to-r from-emerald-600 to-teal-600 text-white text-xs font-semibold rounded-full shadow-lg">
          Most Eco-Friendly
        </span>
      )}

      {/* Header */}
      <div className="flex items-start gap-4 mb-4 mt-2">
        <img
          src={`/${region.provider.toLowerCase()}.png`}
          alt={region.provider}
          className="w-10 h-10 object-contain"
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-white truncate">{region.region}</h3>
          <p className="text-sm text-slate-400">{providerName}</p>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-slate-900/50 rounded-lg px-3 py-2">
          <p className="text-xs text-slate-500 mb-0.5">Forecast Avg</p>
          <p className="text-sm font-semibold text-emerald-400">
            {region.summary.forecast_avg_gCO2} <span className="text-xs text-slate-500">{region.summary.unit}</span>
          </p>
        </div>
        <div className="bg-slate-900/50 rounded-lg px-3 py-2">
          <p className="text-xs text-slate-500 mb-0.5">Recent Avg</p>
          <p className="text-sm font-medium text-slate-300">
            {region.summary.recent_avg_gCO2} <span className="text-xs text-slate-500">{region.summary.unit}</span>
          </p>
        </div>
      </div>

      {/* Trend */}
      <div className="flex items-center gap-2 mb-3">
        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${trendColor}`}>
          {trendIcon} {region.summary.trend}
        </span>
        <span className="text-xs text-slate-500">{region.summary.prediction_days}-day forecast</span>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          onClick={onClick}
          className="hidden md:flex flex-1 px-3 py-2 bg-slate-700/50 hover:bg-slate-700 border border-slate-600/50 rounded-lg text-slate-300 hover:text-white text-sm font-medium transition-all items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Globe
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onViewForecast();
          }}
          className="flex-1 px-3 py-2 bg-emerald-600/10 hover:bg-emerald-600/20 border border-emerald-600/30 rounded-lg text-emerald-400 hover:text-emerald-300 text-sm font-medium transition-all flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Forecast
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════════════════════

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const [form, setForm] = useState<FormState>({
    vcpuRam: "",
    storage: "",
    utilization: 50,
    providers: { aws: true, azure: true, gcp: true },
    searchCheapest: false,
    searchLowestCO2: false,
  });
  const [showForm, setShowForm] = useState(true);
  const [results, setResults] = useState<Results | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<SelectedRegion | null>(null);
  const [selectedCarbonData, setSelectedCarbonData] = useState<SelectedCarbonData | null>(null);
  const [regionCoords, setRegionCoords] = useState<RegionCoords>({});
  const [loading, setLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [forecastData, setForecastData] = useState<ForecastData | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [showForecastModal, setShowForecastModal] = useState(false);
  const [appMode, setAppMode] = useState<AppMode>("decision");
  const [forecastRegions, setForecastRegions] = useState<ForecastRegionSummary[]>([]);
  const [forecastRegionsLoading, setForecastRegionsLoading] = useState(false);
  const [forecastLoadingProgress, setForecastLoadingProgress] = useState(0);
  const [mobileShowGlobe, setMobileShowGlobe] = useState(false);

  useEffect(() => {
    setMounted(true);
    loadRegionCoords().then(setRegionCoords);
  }, []);

  const fetchForecast = async (provider: string, region: string) => {
    setForecastLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/forecast`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, region }),
      });
      if (res.ok) {
        const json = await res.json();
        if (!json.error) setForecastData(json as ForecastData);
        else setForecastData(null);
      }
    } catch {
      setForecastData(null);
    } finally {
      setForecastLoading(false);
    }
  };

  const fetchAllForecasts = async () => {
    setForecastRegionsLoading(true);
    setForecastLoadingProgress(0);
    setForecastRegions([]);
    setForecastData(null);
    setSelectedRegion(null);
    setSelectedCarbonData(null);
    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setForecastLoadingProgress(prev => {
          if (prev >= 90) return prev;
          return Math.min(90, prev + Math.random() * 15);
        });
      }, 200);

      const selectedProviders = (Object.keys(form.providers) as Array<keyof ProviderFlags>).filter((p) => form.providers[p]);
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/forecasts/all`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ providers: selectedProviders }),
      });
      
      clearInterval(progressInterval);
      setForecastLoadingProgress(100);
      
      if (res.ok) {
        const json = await res.json();
        if (json.regions) setForecastRegions(json.regions);
      }
      
      await new Promise(resolve => setTimeout(resolve, 300)); // Brief pause to show 100%
    } catch {
      // ignore
    } finally {
      setForecastRegionsLoading(false);
      setForecastLoadingProgress(0);
      setShowForm(false);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    if (name in form.providers) {
      const checked = (e.target as HTMLInputElement).checked;
      setForm((prev) => ({ ...prev, providers: { ...prev.providers, [name]: checked } }));
    } else if (name === "utilization") {
      setForm((prev) => ({ ...prev, utilization: Number(value) }));
    } else if (name === "searchCheapest" || name === "searchLowestCO2") {
      const checked = (e.target as HTMLInputElement).checked;
      setForm((prev) => ({ ...prev, [name]: checked }));
    } else {
      setForm((prev) => ({ ...prev, [name]: value }));
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    let vcpus = 0, ram = 0;
    if (form.vcpuRam) {
      const [vcpuStr, ramStr] = form.vcpuRam.split("-");
      vcpus = parseInt(vcpuStr, 10);
      ram = parseInt(ramStr, 10);
    }
    try {
      setLoading(true);
      setLoadingProgress(0);
      
      // Simulate progress
      const progressInterval = setInterval(() => {
        setLoadingProgress(prev => {
          if (prev >= 90) return prev;
          return Math.min(90, prev + Math.random() * 15);
        });
      }, 200);

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/pricing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ vcpus, ram, storage: form.storage, utilization: form.utilization / 100 }),
      });
      
      clearInterval(progressInterval);
      setLoadingProgress(100);
      
      if (!res.ok) throw new Error("API error");
      const data = await res.json();
      const providerKeys = Object.keys(form.providers) as Array<keyof ProviderFlags>;
      const selectedProviders = providerKeys.filter((prov) => form.providers[prov]);
      let filtered: Record<string, any> = {};
      for (const prov of selectedProviders) {
        if (data[prov]) filtered[prov] = data[prov];
      }
      if (selectedProviders.length === 0) {
        alert("Please select at least one provider.");
        setLoading(false);
        setLoadingProgress(0);
        return;
      }
      
      await new Promise(resolve => setTimeout(resolve, 300)); // Brief pause to show 100%
      setResults(filtered);
      setShowForm(false);
    } catch (err) {
      alert("Failed to fetch pricing: " + err);
    } finally {
      setLoading(false);
      setLoadingProgress(0);
    }
  };

  const handleNewSearch = () => {
    setShowForm(true);
    setResults(null);
    setForecastRegions([]);
    setSelectedRegion(null);
    setSelectedCarbonData(null);
    setForecastData(null);
  };

  const handleCardClick = (instance: Instance, provider: string) => {
    const coords = regionCoords[instance.region];
    if (coords) {
      setSelectedRegion(coords);
      setSelectedCarbonData({
        region: instance.region,
        provider: provider.toUpperCase(),
        vcpus: instance.actual_vcpus,
        ram_gb: instance.actual_ram_gb,
        storage_type: instance.storage_type,
        carbon_emissions: instance.carbon_emissions,
        co2_grams_per_hour: instance.carbon_emissions?.co2_grams_per_hour || "N/A",
      });
      // On mobile, show globe when region is selected
      if (window.innerWidth < 768) setMobileShowGlobe(true);
    }
  };

  const handleViewForecast = async (provider: string, region: string) => {
    setForecastLoading(true);
    setShowForecastModal(true);
    setForecastData(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/forecast`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, region }),
      });
      if (res.ok) {
        const json = await res.json();
        if (!json.error) setForecastData(json as ForecastData);
        else setForecastData(null);
      }
    } catch {
      setForecastData(null);
    } finally {
      setForecastLoading(false);
    }
  };

  const handleForecastCardClick = (fr: ForecastRegionSummary) => {
    const coords = regionCoords[fr.region];
    if (coords) {
      setSelectedRegion(coords);
      setSelectedCarbonData({
        region: fr.region,
        provider: fr.provider.toUpperCase(),
        co2_grams_per_hour: `${fr.summary.forecast_avg_gCO2} ${fr.summary.unit} (7d avg)`,
      });
      if (window.innerWidth < 768) setMobileShowGlobe(true);
    }
  };

  // Get sorted instances for results
  const getSortedInstances = (): Array<{ instance: Instance; provider: string }> => {
    if (!results) return [];
    let allInstances: Array<{ instance: Instance; provider: string }> = [];
    Object.entries(results).forEach(([provider, data]) => {
      if (data.instances) {
        data.instances.forEach((inst) => allInstances.push({ instance: inst, provider }));
      }
    });

    if (form.searchCheapest && form.searchLowestCO2) {
      const prices = allInstances.map((i) => i.instance.price_usd_per_hour ?? 0);
      const co2s = allInstances.map((i) => i.instance.carbon_emissions?.co2_grams_per_hour ?? 0);
      const minPrice = Math.min(...prices), maxPrice = Math.max(...prices);
      const minCO2 = Math.min(...co2s), maxCO2 = Math.max(...co2s);
      return allInstances
        .map((item) => {
          const normPrice = maxPrice > minPrice ? (item.instance.price_usd_per_hour - minPrice) / (maxPrice - minPrice) : 0;
          const co2 = item.instance.carbon_emissions?.co2_grams_per_hour ?? 0;
          const normCO2 = maxCO2 > minCO2 ? (co2 - minCO2) / (maxCO2 - minCO2) : 0;
          return { ...item, _score: normPrice + normCO2 };
        })
        .sort((a, b) => a._score - b._score)
        .slice(0, 9);
    } else if (form.searchCheapest) {
      return allInstances.sort((a, b) => a.instance.price_usd_per_hour - b.instance.price_usd_per_hour).slice(0, 9);
    } else if (form.searchLowestCO2) {
      return allInstances
        .sort((a, b) => {
          const aCO2 = a.instance.carbon_emissions?.co2_grams_per_hour ?? Infinity;
          const bCO2 = b.instance.carbon_emissions?.co2_grams_per_hour ?? Infinity;
          return aCO2 - bCO2;
        })
        .slice(0, 9);
    }
    return allInstances.slice(0, 12);
  };

  if (!mounted) return <div className="w-screen h-screen bg-slate-900" />;

  return (
    <div className="flex flex-col md:flex-row w-screen h-screen overflow-hidden relative z-[1]">
      {/* Left Panel (mobile: full-width overlay, desktop: sidebar) */}
      <div className={`
        ${mobileShowGlobe ? 'hidden' : 'flex'}
        w-full md:w-[480px] md:min-w-[420px] md:flex flex-col h-full
        border-b md:border-b-0 md:border-r border-slate-800/50
        bg-slate-900/80 md:bg-slate-900/30 backdrop-blur-xl
        relative z-10
      `}>
        {/* Header */}
        <div className="px-4 sm:px-6 py-4 sm:py-5 border-b border-slate-800/50">
          <div className="flex items-center gap-3 mb-3 sm:mb-4">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/25 flex-shrink-0">
              <svg className="w-5 h-5 sm:w-6 sm:h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="min-w-0">
              <h1 className="text-lg sm:text-xl font-bold text-white">CarbonEdge</h1>
              <p className="text-[10px] sm:text-xs text-slate-500 truncate">Multi Cloud Cost & Eco Efficiency Optimization</p>
            </div>
          </div>
          <ModeToggle mode={appMode} setMode={setAppMode} />
        </div>

        {/* Scrollable Content */}
        <div className={`flex-1 px-4 sm:px-6 py-4 ${!showForm ? 'overflow-y-auto' : ''}`}>
          {showForm ? (
            <form onSubmit={appMode === "decision" ? handleSubmit : (e) => { e.preventDefault(); fetchAllForecasts(); }} className="space-y-5">
              {appMode === "decision" ? (
                <>
                  <div className="space-y-1">
                    <h2 className="text-lg font-semibold text-white">Configure Resources</h2>
                  </div>

                  <InputField
                    label="Compute Configuration"
                    icon={<svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" /></svg>}
                  >
                    <select
                      name="vcpuRam"
                      value={form.vcpuRam}
                      onChange={handleChange}
                      required
                      className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                    >
                      <option value="">Select configuration...</option>
                      {VCPU_RAM_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </InputField>

                  <InputField
                    label="Storage (GB)"
                    icon={<svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" /></svg>}
                  >
                    <input
                      type="number"
                      name="storage"
                      value={form.storage}
                      onChange={handleChange}
                      min="1"
                      placeholder="e.g., 100"
                      required
                      className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                    />
                  </InputField>

                  <InputField
                    label={`Utilization Factor: ${form.utilization}%`}
                    icon={<svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
                  >
                    <input
                      type="range"
                      name="utilization"
                      min="0"
                      max="100"
                      value={form.utilization}
                      onChange={handleChange}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                  </InputField>

                  <div className="space-y-3">
                    <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                      <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
                      Cloud Providers
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {(["aws", "azure", "gcp"] as const).map((provider) => (
                        <ProviderChip
                          key={provider}
                          provider={provider}
                          checked={form.providers[provider]}
                          onChange={() => setForm((prev) => ({ ...prev, providers: { ...prev.providers, [provider]: !prev.providers[provider] } }))}
                        />
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3 pt-2">
                    <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                      <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
                      Optimization Filters
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <label className="flex flex-col gap-2 p-3 bg-slate-800/30 border border-slate-700/50 rounded-xl cursor-pointer hover:bg-slate-800/50 transition-colors">
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            name="searchCheapest"
                            checked={form.searchCheapest}
                            onChange={handleChange}
                            className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500/50"
                          />
                          <p className="text-sm font-medium text-slate-200">Lowest Price</p>
                        </div>
                      </label>
                      <label className="flex flex-col gap-2 p-3 bg-slate-800/30 border border-slate-700/50 rounded-xl cursor-pointer hover:bg-slate-800/50 transition-colors">
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            name="searchLowestCO2"
                            checked={form.searchLowestCO2}
                            onChange={handleChange}
                            className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-emerald-500 focus:ring-emerald-500/50"
                          />
                          <p className="text-sm font-medium text-slate-200">Lowest CO₂</p>
                        </div>
                      </label>
                    </div>
                  </div>

                  {!loading ? (
                    <button
                      type="submit"
                      className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/25 transition-all duration-300 flex items-center justify-center gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      Find Optimal Instances
                    </button>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-400">Searching for instances...</span>
                        <span className="text-blue-400 font-semibold">{Math.round(loadingProgress)}%</span>
                      </div>
                      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
                        <div 
                          className="h-full bg-gradient-to-r from-blue-600 to-cyan-500 transition-all duration-300 ease-out rounded-full"
                          style={{ width: `${loadingProgress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="space-y-1">
                    <h2 className="text-lg font-semibold text-white">Carbon Forecast Explorer</h2>
                    <p className="text-sm text-slate-500">View 7-day carbon intensity forecasts for all regions</p>
                  </div>

                  <div className="space-y-3">
                    <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                      <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
                      Filter by Provider
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {(["aws", "azure", "gcp"] as const).map((provider) => (
                        <ProviderChip
                          key={provider}
                          provider={provider}
                          checked={form.providers[provider]}
                          onChange={() => setForm((prev) => ({ ...prev, providers: { ...prev.providers, [provider]: !prev.providers[provider] } }))}
                        />
                      ))}
                    </div>
                  </div>

                  {!forecastRegionsLoading ? (
                    <button
                      type="submit"
                      className="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/25 transition-all duration-300 flex items-center justify-center gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                      Get Eco-Optimized Forecasts
                    </button>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-400">Loading forecasts...</span>
                        <span className="text-emerald-400 font-semibold">{Math.round(forecastLoadingProgress)}%</span>
                      </div>
                      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
                        <div 
                          className="h-full bg-gradient-to-r from-emerald-600 to-teal-500 transition-all duration-300 ease-out rounded-full"
                          style={{ width: `${forecastLoadingProgress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </>
              )}
            </form>
          ) : (
            /* Results View */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-white">
                    {appMode === "decision" ? "Results" : "Eco-Optimized Regions"}
                  </h2>
                  <p className="text-sm text-slate-500">
                    {appMode === "decision"
                      ? `Found ${getSortedInstances().length} matching instances`
                      : `${forecastRegions.length} regions with forecast data`}
                  </p>
                </div>
                <button
                  onClick={handleNewSearch}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors"
                >
                  New Search
                </button>
              </div>

              <div className="space-y-3">
                {appMode === "decision"
                  ? getSortedInstances().map((item, idx) => (
                      <ResultCard
                        key={`${item.provider}-${item.instance.instance_type}-${idx}`}
                        instance={item.instance}
                        provider={item.provider}
                        rank={idx + 1}
                        onClick={() => handleCardClick(item.instance, item.provider)}
                        onViewForecast={() => handleViewForecast(item.provider, item.instance.region)}
                        isEcoOptimized={form.searchCheapest && form.searchLowestCO2 && idx === 0}
                        isCheapest={form.searchCheapest && !form.searchLowestCO2 && idx === 0}
                        isLowestCO2={form.searchLowestCO2 && !form.searchCheapest && idx === 0}
                      />
                    ))
                  : forecastRegions.map((fr, idx) => (
                      <ForecastRegionCard
                        key={fr.group_id}
                        region={fr}
                        rank={idx + 1}
                        onClick={() => handleForecastCardClick(fr)}
                        onViewForecast={() => handleViewForecast(fr.provider, fr.region)}
                      />
                    ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - Globe (mobile: fullscreen overlay, desktop: right side) */}
      <div className={`
        ${mobileShowGlobe ? 'fixed inset-0 z-30' : 'hidden'}
        md:relative md:flex md:flex-1 md:items-center md:justify-end md:overflow-hidden md:z-auto
      `}>
        <GlobeViewer selectedRegion={selectedRegion} carbonData={selectedCarbonData} />
        {/* Mobile globe close button */}
        {mobileShowGlobe && (
          <button
            onClick={() => setMobileShowGlobe(false)}
            className="md:hidden fixed top-4 right-4 z-40 p-3 bg-slate-900/80 backdrop-blur-md border border-slate-700/50 rounded-full text-white shadow-lg"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Mobile Globe Toggle FAB */}
      {!mobileShowGlobe && (
        <button
          onClick={() => setMobileShowGlobe(true)}
          className="md:hidden fixed bottom-6 right-6 z-40 p-4 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-full text-white shadow-lg shadow-emerald-500/30 active:scale-95 transition-transform"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      )}

      {/* Forecast Modal */}
      {showForecastModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => {
            setShowForecastModal(false);
            setForecastData(null);
          }}
        >
          <div 
            className="relative w-full h-full sm:w-[90vw] sm:max-w-6xl sm:h-[85vh] bg-slate-900 border border-slate-800 sm:rounded-2xl shadow-2xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between p-4 sm:p-6 border-b border-slate-800">
              <div className="min-w-0 flex-1">
                <h3 className="text-lg sm:text-2xl font-bold text-white">Carbon Intensity Forecast</h3>
                {forecastData && (
                  <>
                    <p className="text-sm text-slate-400 mt-1">
                      {forecastData.region}
                    </p>
                    <p className="text-xs text-slate-500">
                      {forecastData.provider.toUpperCase()}
                    </p>
                  </>
                )}
              </div>
              <button
                onClick={() => {
                  setShowForecastModal(false);
                  setForecastData(null);
                }}
                className="p-2 rounded-lg bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 text-slate-400 hover:text-white transition-colors"
                aria-label="Close forecast"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-hidden p-4 sm:p-6">
              {forecastLoading ? (
                <div className="h-full flex flex-col items-center justify-center gap-4">
                  <svg className="animate-spin w-12 h-12 text-emerald-500" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-slate-400 text-lg">Loading forecast data...</p>
                </div>
              ) : forecastData ? (
                <div className="h-full">
                  <ForecastChart data={forecastData} onClose={() => {
                    setShowForecastModal(false);
                    setForecastData(null);
                  }} />
                </div>
              ) : (
                <div className="h-full flex items-center justify-center">
                  <p className="text-slate-500">No forecast data available</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
