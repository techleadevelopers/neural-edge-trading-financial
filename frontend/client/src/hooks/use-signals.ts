import { useQuery } from "@tanstack/react-query";
import { api, type SignalQueryParams } from "@shared/routes";

export function useSignals(params?: SignalQueryParams) {
  const queryString = params 
    ? new URLSearchParams(
        Object.entries(params).reduce((acc, [key, val]) => {
          if (val !== undefined) acc[key] = String(val);
          return acc;
        }, {} as Record<string, string>)
      ).toString() 
    : '';

  return useQuery({
    queryKey: [api.signals.list.path, params],
    queryFn: async () => {
      const url = `${api.signals.list.path}?${queryString}`;
      const res = await fetch(url, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch signals");
      return api.signals.list.responses[200].parse(await res.json());
    },
    // Poll every 30 seconds for new signals
    refetchInterval: 30000, 
  });
}

export function useSignal(id: number) {
  return useQuery({
    queryKey: [api.signals.get.path, id],
    queryFn: async () => {
      // Use direct URL construction instead of buildUrl if it's simpler here or import buildUrl
      // Importing buildUrl from shared routes is cleaner
      const res = await fetch(api.signals.get.path.replace(':id', String(id)), { credentials: "include" });
      if (res.status === 404) return null;
      if (!res.ok) throw new Error("Failed to fetch signal");
      return api.signals.get.responses[200].parse(await res.json());
    },
    enabled: !!id,
  });
}

export function useLatestSignalUpdate() {
  return useQuery({
    queryKey: [api.signals.latest.path],
    queryFn: async () => {
      const res = await fetch(api.signals.latest.path, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch latest update time");
      return api.signals.latest.responses[200].parse(await res.json());
    },
    refetchInterval: 15000,
  });
}
