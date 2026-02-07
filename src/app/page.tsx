"use client";


import { useState, useEffect, ChangeEvent, FormEvent } from "react";
import GlassSurface from "./components/GlassSurface";

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

interface RegionCoords {
  [region: string]: {
    lat: number;
    lng: number;
  };
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
  [key: string]: any;
}

interface ProviderData {
  instances: Instance[];
  [key: string]: any;
}

interface Results {
  [provider: string]: ProviderData;
}

interface ExpandedCards {
  [key: string]: boolean;
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

// Recursively pretty-print objects/arrays for card details
interface PrettyObjectProps {
  value: any;
  level?: number;
}

function PrettyObject({ value, level = 0 }: PrettyObjectProps) {
  const [open, setOpen] = useState(level === 0); // root open by default
  if (value === null) return <span className="text-gray-500">null</span>;
  if (typeof value !== 'object') return <span>{String(value)}</span>;
  if (Array.isArray(value)) {
    return (
      <div className={`ml-${level * 2} pl-2 border-l border-gray-200 bg-gray-50 rounded`}>[
        {value.length === 0 ? <span className="text-gray-400">empty</span> :
          value.map((v, i) => (
            <div key={i} className="ml-2">
              <PrettyObject value={v} level={level + 1} />
            </div>
          ))}
        ]
      </div>
    );
  }
  // Object
  const keys = Object.keys(value);
  return (
    <div className={`ml-${level * 2} pl-2 border-l border-gray-200 bg-gray-50 rounded mt-1`}>
      <button type="button" className="text-xs text-blue-600 underline mb-1" onClick={() => setOpen(o => !o)}>
        {open ? 'Collapse' : 'Expand'}
      </button>
      {open && (
        <div>
          {keys.length === 0 ? <span className="text-gray-400">empty</span> :
            keys.map(k => (
              <div key={k} className="flex items-start">
                <span className="font-semibold text-xs text-gray-700 mr-1">{k}:</span>
                <span className="flex-1 text-xs"><PrettyObject value={value[k]} level={level + 1} /></span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
import GlobeViewer from "./components/GlobeViewer";

// Load region coordinates from YAML file
const loadRegionCoords = async (): Promise<RegionCoords> => {
  try {
    const response = await fetch('/api/region-coordinates');
    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.error('Failed to load region coordinates:', error);
  }
  
  // Fallback coordinates if API fails
  return {
    "centralus": { lat: 41.5908, lng: -93.6208 },
    "attdetroit1": { lat: 42.3314, lng: -83.0458 },
    "us-east-1": { lat: 39.0438, lng: -77.4874 },
    "us-west-1": { lat: 37.3382, lng: -121.8863 },
    "us-west-2": { lat: 45.5152, lng: -122.6784 },
    "us-east-2": { lat: 39.9612, lng: -82.9988 },
    "malaysiawest": { lat: 3.1390, lng: 101.6869 },
    "US West (Oregon)": { lat: 45.5152, lng: -122.6784 },
    "US East (N. Virginia)": { lat: 39.0438, lng: -77.4874 },
    "US East (Ohio)": { lat: 39.9612, lng: -82.9988 },
    "US West (N. California)": { lat: 37.3382, lng: -121.8863 },
    "US Central": { lat: 41.5908, lng: -93.6208 },
    "Malaysia West": { lat: 3.1390, lng: 101.6869 },
    "us-gov-west-1": { lat: 45.5231, lng: -122.6765 },
    "AWS GovCloud (US-West)": { lat: 45.5231, lng: -122.6765 },
  };
};

interface VcpuRamOption {
  label: string;
  value: string;
}

const VCPU_RAM_OPTIONS: VcpuRamOption[] = [
  { label: "1 vCPU, 2 GB RAM", value: "1-2" },
  { label: "2 vCPUs, 4 GB RAM", value: "2-4" },
  { label: "4 vCPUs, 8 GB RAM", value: "4-8" },
  { label: "4 vCPUs, 16 GB RAM", value: "4-16" },
  { label: "8 vCPUs, 32 GB RAM", value: "8-32" },
  { label: "16 vCPUs, 64 GB RAM", value: "16-64" },
  { label: "32 vCPUs, 128 GB RAM", value: "32-128" },
];

export default function Home(): JSX.Element {
    const [mounted, setMounted] = useState(false);
    const [glassSize, setGlassSize] = useState({ width: 400, height: 400 });
    useEffect(() => {
      setMounted(true);
      function updateSize() {
        const w = Math.min(440, Math.max(300, window.innerWidth * 0.5));
        const h = Math.min(580, Math.max(540, window.innerHeight * 0.55));
        setGlassSize({ width: w, height: h });
      }
      updateSize();
      window.addEventListener('resize', updateSize);
      return () => window.removeEventListener('resize', updateSize);
    }, []);
  const [form, setForm] = useState<FormState>({
    vcpuRam: "",
    storage: "",
    utilization: 50,
    providers: {
      aws: true,
      azure: true,
      gcp: true,
    },
    searchCheapest: false,
    searchLowestCO2: false,
  });
  const [accordionOpen, setAccordionOpen] = useState<boolean>(true);
  const [results, setResults] = useState<Results | null>(null);
  const [expandedCards, setExpandedCards] = useState<ExpandedCards>({});
  const [selectedRegion, setSelectedRegion] = useState<SelectedRegion | null>(null);
  const [selectedCarbonData, setSelectedCarbonData] = useState<SelectedCarbonData | null>(null);
  const [regionCoords, setRegionCoords] = useState<RegionCoords>({});
  const [loading, setLoading] = useState<boolean>(false);

  // Load region coordinates on component mount
  useEffect(() => {
    loadRegionCoords().then(coords => {
      setRegionCoords(coords);
    });
  }, []);

  const toggleCard = (key: string): void => {
    setExpandedCards((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
    const { name, value, type } = e.target;
    if (name in form.providers) {
      const checked = (e.target as HTMLInputElement).checked;
      setForm((prev) => ({
        ...prev,
        providers: {
          ...prev.providers,
          [name]: checked,
        },
      }));
    } else if (name === "utilization") {
      setForm((prev) => ({
        ...prev,
        utilization: Number(value),
      }));
    } else if (name === "searchCheapest" || name === "searchLowestCO2") {
      const checked = (e.target as HTMLInputElement).checked;
      setForm((prev) => ({
        ...prev,
        [name]: checked,
      }));
    } else {
      setForm((prev) => ({
        ...prev,
        [name]: value,
      }));
    }
  };

  const handleSubmit = async (e: FormEvent): Promise<void> => {
    e.preventDefault();
    let vcpus = 0, ram = 0;
    if (form.vcpuRam) {
      const [vcpuStr, ramStr] = form.vcpuRam.split("-");
      vcpus = parseInt(vcpuStr, 10);
      ram = parseInt(ramStr, 10);
    }
    const payload = {
      vcpus,
      ram,
      storage: form.storage,
      utilization: form.utilization / 100,
    };
    try {
      setLoading(true);
      const res = await fetch("http://localhost:8000/api/pricing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("API error");
      const data = await res.json();
      const providerKeys = Object.keys(form.providers) as Array<keyof typeof form.providers>;
      const selectedProviders = providerKeys.filter((prov) => form.providers[prov]);
      let filtered: Record<string, any> = {};
      for (const prov of selectedProviders) {
        if (data[prov]) filtered[prov] = data[prov];
      }
      if (selectedProviders.length === 0) {
        alert("Please select at least one provider.");
        setLoading(false);
        return;
      }
      setResults(filtered);
      setAccordionOpen(false);
    } catch (err) {
      alert("Failed to fetch pricing: " + err);
    } finally {
      setLoading(false);
    }
  };

    return (
      <div className="flex w-screen h-screen">
        <div className="flex-1 flex flex-col justify-center items-center p-2 overflow-y-auto ml-14 h-full">
          {mounted && accordionOpen && (
            <GlassSurface
              borderRadius={32}
              width={glassSize.width}
              height={glassSize.height}
              className="p-6 shadow-2xl mt-0 max-w-2xl w-full"
            >
                <div
                  className="overflow-hidden transition-all duration-500 ease-in-out w-full"
                  style={{ willChange: 'max-height, opacity' }}
                >
                  <form
                    onSubmit={handleSubmit}
                    className="w-full"
                  >
                <h2 className="text-xl font-bold mb-6 text-white">Select Resource</h2>
                <div className="mb-3">
                  <label className="block mb-2 font-semibold text-white text-sm" htmlFor="vcpuRam">
                    vCPU and RAM configuration
                  </label>
                  <select
                    id="vcpuRam"
                    name="vcpuRam"
                    value={form.vcpuRam}
                    onChange={handleChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 text-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
                  >
                    <option value="">Select configuration</option>
                    {VCPU_RAM_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                  <div className="flex-1 mb-3">
                    <label className="block mb-2 font-semibold text-white text-sm" htmlFor="storage">
                      Storage (in GB)
                    </label>
                    <input
                      type="number"
                      id="storage"
                      name="storage"
                      value={form.storage}
                      onChange={handleChange}
                      min="1"
                      placeholder="e.g. 100"
                      className="w-full px-3 py-2 border border-gray-300 text-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
                      required
                    />
                </div>
                <div className="mb-2">
                  <label className="block mb-2 font-semibold text-white text-sm" htmlFor="utilization">
                    Utilization Factor ({form.utilization}%)
                  </label>
                  <input
                    type="range"
                    id="utilization"
                    name="utilization"
                    min="0"
                    max="100"
                    value={form.utilization}
                    onChange={handleChange}
                    className="w-full accent-blue-600"
                  />
                </div>
                <div className="mb-3">
                  <span className="block mb-2 font-semibold text-white">Providers</span>
                  <div className="flex gap-4 mt-2">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        name="aws"
                        checked={form.providers.aws}
                        onChange={handleChange}
                        className="accent-blue-600"
                      />
                      <span className="text-white">AWS</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        name="azure"
                        checked={form.providers.azure}
                        onChange={handleChange}
                        className="accent-blue-600"
                      />
                      <span className="text-white">Azure</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        name="gcp"
                        checked={form.providers.gcp}
                        onChange={handleChange}
                        className="accent-blue-600"
                      />
                      <span className="text-white">GCP</span>
                    </label>
                  </div>
                  {/* Toggles for cheapest and lowest CO2 */}
                  <div className="flex flex-col gap-4 mt-4">
                    <div className="flex items-center gap-3">
                      <span className="text-white">Search for cheapest instance</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          name="searchCheapest"
                          checked={form.searchCheapest}
                          onChange={handleChange}
                          className="sr-only peer"
                          role="switch"
                          aria-checked={form.searchCheapest}
                        />
                        <div
                          className="group peer bg-white rounded-full duration-300 w-10 h-5 ring-2 ring-gray-400 peer-checked:ring-blue-600 after:duration-300 after:bg-gray-400 peer-checked:after:bg-blue-600 after:rounded-full after:absolute after:h-4 after:w-4 after:top-0.5 after:left-0.5 after:flex after:justify-center after:items-center peer-checked:after:translate-x-5 peer-hover:after:scale-95"
                        ></div>
                      </label>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-white">Search for lowest CO2 emission</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          name="searchLowestCO2"
                          checked={form.searchLowestCO2}
                          onChange={handleChange}
                          className="sr-only peer"
                          role="switch"
                          aria-checked={form.searchLowestCO2}
                        />
                        <div
                          className="group peer bg-white rounded-full duration-300 w-10 h-5 ring-2 ring-gray-400 peer-checked:ring-blue-600 after:duration-300 after:bg-gray-400 peer-checked:after:bg-blue-600 after:rounded-full after:absolute after:h-4 after:w-4 after:top-0.5 after:left-0.5 after:flex after:justify-center after:items-center peer-checked:after:translate-x-5 peer-hover:after:scale-95"
                        ></div>
                      </label>
                    </div>
                  </div>
                </div>
                <button
                  type="submit"
                  className="w-full mt-4 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition flex items-center justify-center"
                  disabled={loading}
                >
                  {loading && (
                    <span className="w-5 h-5 border-4 border-t-blue-500 border-gray-300 rounded-full animate-spin mr-2 inline-block align-middle"></span>
                  )}
                  {loading ? "Searching..." : "Search"}
                </button>
                </form>
              </div>
          </GlassSurface>
          )}
          {/* Results Grid */}
          {!accordionOpen && results && (
              <GlassSurface
                borderRadius={24}
                width={glassSize.width}
                height={glassSize.height * 1.1}
                className="p-6 shadow-2xl"
              >
              <div className="w-full">
                <div className="max-h-[60vh] overflow-y-auto scrollbar-none" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
                  {form.searchCheapest || form.searchLowestCO2 ? (
                    // Stack of 3 cheapest, 3 lowest CO2, or best combined when both toggles are on
                    (() => {
                      let stackInstances: any[] = [];
                      Object.entries(results).forEach(([provider, providerData]) => {
                        const data = providerData as any;
                        if (data.instances && data.instances.length > 0) {
                          let sorted;
                          if (form.searchCheapest && form.searchLowestCO2) {
                            // Sort by combined normalized score
                            const prices = data.instances.map((i: { price_usd_per_hour: any; }) => i.price_usd_per_hour ?? 0);
                            interface InstanceWithCarbon extends Instance {
                              carbon_emissions?: CarbonEmissions;
                            }

                            const co2s: number[] = (data.instances as InstanceWithCarbon[]).map((i: InstanceWithCarbon) => i.carbon_emissions?.co2_grams_per_hour ?? 0);
                            const minPrice = Math.min(...prices);
                            const maxPrice = Math.max(...prices);
                            const minCO2 = Math.min(...co2s);
                            const maxCO2 = Math.max(...co2s);
                            sorted = [...data.instances].map(i => {
                              const normPrice = maxPrice > minPrice ? (i.price_usd_per_hour - minPrice) / (maxPrice - minPrice) : 0;
                              const co2 = i.carbon_emissions?.co2_grams_per_hour ?? 0;
                              const normCO2 = maxCO2 > minCO2 ? (co2 - minCO2) / (maxCO2 - minCO2) : 0;
                              return { ...i, _score: normPrice + normCO2 };
                            }).sort((a, b) => a._score - b._score);
                          } else if (form.searchCheapest) {
                            sorted = [...data.instances].sort((a, b) => a.price_usd_per_hour - b.price_usd_per_hour);
                          } else {
                            sorted = [...data.instances].sort((a, b) => {
                              const aCO2 = a.carbon_emissions?.co2_grams_per_hour ?? Number.POSITIVE_INFINITY;
                              const bCO2 = b.carbon_emissions?.co2_grams_per_hour ?? Number.POSITIVE_INFINITY;
                              return aCO2 - bCO2;
                            });
                          }
                          sorted.slice(0, 3).forEach((instance: any, idx: number) => {
                            stackInstances.push({ ...instance, provider, providerIdx: idx });
                          });
                        }
                      });
                      // Sort all by selected logic
                      if (form.searchCheapest && form.searchLowestCO2) {
                        // Combined score sort
                        const prices = stackInstances.map(i => i.price_usd_per_hour ?? 0);
                        const co2s = stackInstances.map(i => i.carbon_emissions?.co2_grams_per_hour ?? 0);
                        const minPrice = Math.min(...prices);
                        const maxPrice = Math.max(...prices);
                        const minCO2 = Math.min(...co2s);
                        const maxCO2 = Math.max(...co2s);
                        stackInstances = stackInstances.map(i => {
                          const normPrice = maxPrice > minPrice ? (i.price_usd_per_hour - minPrice) / (maxPrice - minPrice) : 0;
                          const co2 = i.carbon_emissions?.co2_grams_per_hour ?? 0;
                          const normCO2 = maxCO2 > minCO2 ? (co2 - minCO2) / (maxCO2 - minCO2) : 0;
                          return { ...i, _score: normPrice + normCO2 };
                        }).sort((a, b) => a._score - b._score);
                      } else if (form.searchCheapest) {
                        stackInstances.sort((a, b) => a.price_usd_per_hour - b.price_usd_per_hour);
                      } else {
                        stackInstances.sort((a, b) => {
                          const aCO2 = a.carbon_emissions?.co2_grams_per_hour ?? Number.POSITIVE_INFINITY;
                          const bCO2 = b.carbon_emissions?.co2_grams_per_hour ?? Number.POSITIVE_INFINITY;
                          if (aCO2 !== bCO2) {
                            return aCO2 - bCO2;
                          }
                          // If carbon values are equal, sort by price
                          const aPrice = a.price_usd_per_hour ?? Number.POSITIVE_INFINITY;
                          const bPrice = b.price_usd_per_hour ?? Number.POSITIVE_INFINITY;
                          return aPrice - bPrice;
                        });
                      }
                      return (
                        <div className="flex flex-col">
                          <div className="flex flex-col gap-4 items-center w-full overflow-y-auto max-h-full" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
                            {stackInstances.map((instance, idx) => {
                            const provider = instance.provider;
                            const cardKey = provider + instance.instance_type + idx;
                            const mainFields = [
                              ["region", instance.region],
                              ["price_usd_per_hour", instance.price_usd_per_hour],
                              ["carbon_emission", instance.carbon_emissions?.gco2_per_kwh ?? (instance.carbon_emissions?.co2_grams_per_hour ? instance.carbon_emissions.co2_grams_per_hour : 'N/A')],
                            ];
                            const restFields = Object.entries(instance).filter(
                              ([k]) => !["region", "price_usd_per_hour", "carbon_emission", "co2_grams_per_hour", "provider", "providerIdx"].includes(k)
                            );
                            const handleCardClick = () => {
                              const coords = regionCoords[instance.region];
                              console.log('[HandleCardClick] Looking for region:', instance.region);
                              console.log('[HandleCardClick] Available regionCoords:', Object.keys(regionCoords));
                              console.log('[HandleCardClick] Found coords:', coords);
                              if (coords) {
                                setSelectedRegion(coords);
                                setSelectedCarbonData({
                                  region: instance.region,
                                  provider: provider.toUpperCase(),
                                  vcpus: instance.actual_vcpus,
                                  ram_gb: instance.actual_ram_gb,
                                  storage_type: instance.storage_type,
                                  carbon_emissions: instance.carbon_emissions,
                                  co2_grams_per_hour: instance.carbon_emissions?.co2_grams_per_hour || 'N/A'
                                });
                              } else {
                                console.warn('[HandleCardClick] No coordinates found for region:', instance.region);
                              }
                            };
                            return (
                              <div
                                key={cardKey}
                                className="bg-white rounded-xl shadow-md p-5 border border-gray-200 cursor-pointer w-full max-w-2xl"
                                onClick={handleCardClick}
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <div className="font-semibold flex items-center gap-4 justify-center">
                                    <img
                                      src={`/${provider.toLowerCase()}.png`}
                                      alt={provider.toUpperCase() + ' logo'}
                                      style={{ height: '2em', width: '2em', minWidth: '2em', minHeight: '2em', maxWidth: '2em', maxHeight: '2em', objectFit: 'contain', display: 'inline-block' }}
                                      className="inline align-middle"
                                      width={32}
                                      height={32}
                                      onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                                      />
                                    <span className="align-middle flex flex-col items-start h-full">
                                      <span>{instance.instance_type}</span>
                                      <span className="text-xs text-gray-500 mt-0.5">
                                        {provider === 'azure' ? 'Microsoft Azure' : provider === 'aws' ? 'Amazon Web Services' : provider === 'gcp' ? 'Google Cloud' : provider}
                                      </span>
                                    </span>
                                  </div>
                                      {/* Label for the first card */}
                                      {idx === 0 && (
                                        (form.searchCheapest && form.searchLowestCO2) ? (
                                          <span className="bg-green-600 text-white text-xs font-bold px-3 py-1 rounded-full mr-2">Eco-Optimized</span>
                                        ) : (form.searchCheapest && !form.searchLowestCO2) ? (
                                          <span className="bg-green-600 text-white text-xs font-bold px-3 py-1 rounded-full mr-2">Cheapest</span>
                                        ) : (!form.searchCheapest && form.searchLowestCO2) ? (
                                          <span className="bg-green-600 text-white text-xs font-bold px-3 py-1 rounded-full mr-2">Carbon-efficient</span>
                                        ) : null
                                      )}
                                  <button
                                    className="focus:outline-none"
                                    onClick={e => { e.stopPropagation(); setExpandedCards(prev => ({ ...prev, [cardKey]: !prev[cardKey] })); }}
                                    aria-label={expandedCards[cardKey] ? 'Collapse details' : 'Expand details'}
                                    type="button"
                                  >
                                    <span className={`inline-block transform transition-transform ${expandedCards[cardKey] ? 'rotate-90' : ''}`}> 
                                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24">
                                        <path d="M12 2a10 10 0 1 0 10 10A10.011 10.011 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8.009 8.009 0 0 1-8 8z" fill="#2563eb"/>
                                        <path d="M12 12.586 8.707 9.293l-1.414 1.414L12 15.414l4.707-4.707-1.414-1.414L12 12.586z" fill="#2563eb"/>
                                      </svg>
                                    </span>
                                  </button>
                                </div>
                                {mainFields.map(([k, v]) => (
                                  <div key={k} className="text-sm text-gray-700">
                                    {k === "price_usd_per_hour"
                                      ? <><span className="font-semibold">Price:</span><span> ${v}/hour</span></>
                                      : k === "carbon_emission"
                                      ? <><span className="font-semibold">Carbon Emission:</span> <span>{v} gCO₂/kWh</span></>
                                      : <><span className="font-semibold">{k.charAt(0).toUpperCase() + k.slice(1)}:</span> {String(v)}</>}
                                  </div>
                                ))}
                                {expandedCards[cardKey] && (
                                  <div className="mt-2 border-t pt-2">
                                    {restFields.length > 0 ? restFields.map(([k, v]) => (
                                      <div key={k} className="text-sm text-gray-700 mb-1">
                                        <span className="font-semibold">{k}:</span>{' '}
                                        {typeof v === 'object' && v !== null
                                          ? <PrettyObject value={v} />
                                          : <span>{String(v)}</span>}
                                      </div>
                                    )) : <div className="text-xs text-gray-400">No more details.</div>}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                        </div>
                      );
                    })()
                  ) : (
                    <div className="flex flex-col gap-4 items-center w-full overflow-y-auto max-h-full" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
                      {Object.entries(results).flatMap(([provider, providerData]) => {
                        const data = providerData as any;
                        if (!data.instances || data.instances.length === 0) {
                          return [
                            <div key={provider} className="bg-white rounded-xl shadow-md p-5 border border-gray-200 w-full max-w-2xl">
                              <div className="font-bold text-lg mb-2 flex items-center gap-2">
                                <img
                                  src={`/${provider.toLowerCase()}.png`}
                                  alt={provider.toUpperCase() + ' logo'}
                                  style={{ height: '1.25em', width: 'auto', display: 'inline-block', verticalAlign: 'middle' }}
                                  className="inline align-middle"
                                  onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                                />
                                {provider.toUpperCase()}
                              </div>
                              <div className="text-gray-500">No results found.</div>
                            </div>
                          ];
                        }
                        return data.instances.map((instance: any, idx: number) => {
                          const cardKey = provider + idx;
                          const mainFields = [
                            ["instance_type", instance.instance_type],
                            ["region", instance.region],
                            ["price_usd_per_hour", instance.price_usd_per_hour],
                          ];
                          const restFields = Object.entries(instance).filter(
                            ([k]) => !["instance_type", "region", "price_usd_per_hour"].includes(k)
                          );
                          const handleCardClick = () => {
                            const coords = regionCoords[instance.region];
                            console.log('[HandleCardClick Stack] Looking for region:', instance.region);
                            console.log('[HandleCardClick Stack] Available regionCoords:', Object.keys(regionCoords));
                            console.log('[HandleCardClick Stack] Found coords:', coords);
                            if (coords) {
                              setSelectedRegion(coords);
                              setSelectedCarbonData({
                                region: instance.region,
                                provider: provider.toUpperCase(),
                                vcpus: instance.actual_vcpus,
                                ram_gb: instance.actual_ram_gb,
                                storage_type: instance.storage_type,
                                storage_gb: instance.instance_storage_gb || 0,
                                carbon_emissions: instance.carbon_emissions,
                                co2_grams_per_hour: instance.carbon_emissions?.co2_grams_per_hour || 'N/A'
                              });
                            } else {
                              console.warn('[HandleCardClick Stack] No coordinates found for region:', instance.region);
                            }
                          };
                          return (
                            <div
                              key={cardKey}
                              className="bg-white rounded-xl shadow-md p-5 border border-gray-200 cursor-pointer w-full max-w-2xl"
                              onClick={handleCardClick}
                            >
                              <div className="flex items-center justify-between mb-2">
                                <div className="font-semibold flex items-center gap-2 justify-center">
                                  <img
                                    src={`/${provider.toLowerCase()}.png`}
                                    alt={provider.toUpperCase() + ' logo'}
                                    style={{ height: '1.25em', width: 'auto', display: 'inline-block', verticalAlign: 'middle' }}
                                    className="inline align-middle"
                                    onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                                  />
                                  <div>
                                    {provider.toUpperCase()}
                                  </div>
                                </div>
                                <button
                                  className="focus:outline-none"
                                  onClick={e => { e.stopPropagation(); setExpandedCards(prev => ({ ...prev, [cardKey]: !prev[cardKey] })); }}
                                  aria-label={expandedCards[cardKey] ? 'Collapse details' : 'Expand details'}
                                  type="button"
                                >
                                  <span className={`inline-block transform transition-transform ${expandedCards[cardKey] ? 'rotate-90' : ''}`}>▶</span>
                                </button>
                              </div>
                              {mainFields.map(([k, v]) => (
                                <div key={k} className="text-sm text-gray-700"><span className="font-semibold">{k}:</span> {String(v)}</div>
                              ))}
                              {expandedCards[cardKey] && (
                                <div className="mt-2 border-t pt-2">
                                  {restFields.length > 0 ? restFields.map(([k, v]) => (
                                    <div key={k} className="text-sm text-gray-700"><span className="font-semibold">{k}:</span> {typeof v === 'object' ? JSON.stringify(v) : String(v)}</div>
                                  )) : <div className="text-xs text-gray-400">No more details.</div>}
                                </div>
                              )}
                            </div>
                          );
                        });
                      })}
                    </div>
                  )}
                </div>
              <button
                className="mt-6 w-full px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition"
                onClick={() => {
                  setAccordionOpen(true);
                  setSelectedRegion(null);
                  setSelectedCarbonData(null);
                }}
              >
                New Search
              </button>
            </div>
            </GlassSurface>
          )}
        </div>
        <div className="flex-1 flex justify-center items-center bg-transparent">
          <GlobeViewer selectedRegion={selectedRegion} carbonData={selectedCarbonData} />
        </div>
      </div>
    );
  };