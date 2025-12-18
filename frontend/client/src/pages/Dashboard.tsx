import { useState } from "react";
import { useSignals, useLatestSignalUpdate } from "@/hooks/use-signals";
import { useAlerts } from "@/hooks/use-alerts";
import { SignalCard } from "@/components/SignalCard";
import { AlertsPanel } from "@/components/AlertsPanel";
import { SignalDetailModal } from "@/components/SignalDetailModal";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { Signal } from "@shared/schema";
import { Search, RefreshCw, Filter, ListFilter, LayoutGrid } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

export default function Dashboard() {
  const [minScore, setMinScore] = useState<number>(50);
  const [onlyStrong, setOnlyStrong] = useState<boolean>(false);
  const [search, setSearch] = useState<string>("");
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const { data: signals, isLoading, refetch } = useSignals({ 
    minScore, 
    onlyStrong 
  });
  
  const { data: alerts, isLoading: alertsLoading } = useAlerts();
  const { data: latestUpdate } = useLatestSignalUpdate();

  // Client-side filtering for search (since backend search isn't in schema yet)
  const filteredSignals = signals?.filter(s => 
    s.symbol.toLowerCase().includes(search.toLowerCase())
  ) || [];

  return (
    <div className="min-h-screen bg-background text-foreground flex overflow-hidden font-body">
      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden mr-0 md:mr-80 transition-all duration-300">
        
        {/* Header */}
        <header className="px-8 py-6 bg-card/30 backdrop-blur-md border-b border-border z-10 sticky top-0">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-white/60">
                PAINEL DE SINAIS CRIPTO
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-[10px] font-bold text-green-500 uppercase tracking-wide">Sistema Online</span>
                </div>
                <span className="text-xs text-muted-foreground font-mono">
                  Última atualização: {latestUpdate ? format(new Date(latestUpdate.lastUpdate), "HH:mm:ss", { locale: ptBR }) : "--:--"}
                </span>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
               <Button 
                variant="outline" 
                size="sm" 
                onClick={() => refetch()}
                className="hidden md:flex gap-2 text-xs font-semibold bg-background/50 hover:bg-background/80"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Atualizar
              </Button>
            </div>
          </div>
        </header>

        {/* Filters Bar */}
        <div className="px-8 py-4 bg-background/50 border-b border-border/50">
          <div className="flex flex-col lg:flex-row gap-6 items-start lg:items-center justify-between">
            <div className="relative w-full max-w-md group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
              <Input 
                placeholder="Buscar moeda (ex: BTC, ETH)..." 
                className="pl-9 h-10 bg-card border-border hover:border-primary/50 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all rounded-xl"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <div className="flex flex-wrap items-center gap-6 w-full lg:w-auto">
              <div className="flex items-center gap-3 bg-card px-4 py-2 rounded-xl border border-border">
                <Switch 
                  id="strong-mode" 
                  checked={onlyStrong}
                  onCheckedChange={setOnlyStrong}
                />
                <Label htmlFor="strong-mode" className="text-sm cursor-pointer font-medium">Somente Fortes</Label>
              </div>

              <div className="flex items-center gap-4 bg-card px-4 py-2 rounded-xl border border-border min-w-[200px]">
                <Label className="text-xs font-bold text-muted-foreground uppercase whitespace-nowrap">Score Min: {minScore}</Label>
                <Slider 
                  value={[minScore]} 
                  onValueChange={(vals) => setMinScore(vals[0])} 
                  max={100} 
                  step={5}
                  className="w-32"
                />
              </div>

              <div className="flex bg-card p-1 rounded-lg border border-border">
                <button 
                  onClick={() => setViewMode("grid")}
                  className={cn("p-2 rounded-md transition-all", viewMode === "grid" ? "bg-primary/20 text-primary" : "text-muted-foreground hover:text-foreground")}
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
                <button 
                  onClick={() => setViewMode("list")}
                  className={cn("p-2 rounded-md transition-all", viewMode === "list" ? "bg-primary/20 text-primary" : "text-muted-foreground hover:text-foreground")}
                >
                  <ListFilter className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Signals Grid/List */}
        <main className="flex-1 overflow-y-auto p-8 scroll-smooth">
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-48 rounded-xl bg-card border border-border animate-pulse" />
              ))}
            </div>
          ) : filteredSignals.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-50">
              <Filter className="w-16 h-16 mb-4 stroke-1" />
              <h3 className="text-xl font-bold">Nenhum sinal encontrado</h3>
              <p>Tente ajustar seus filtros de busca</p>
            </div>
          ) : (
            <div className={cn(
              "grid gap-6 pb-20",
              viewMode === "grid" ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5" : "grid-cols-1"
            )}>
              <AnimatePresence>
                {filteredSignals.map((signal, index) => (
                  <motion.div
                    key={signal.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ delay: index * 0.05, duration: 0.3 }}
                  >
                    <SignalCard 
                      signal={signal} 
                      onClick={() => setSelectedSignal(signal)}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </main>
      </div>

      {/* Side Panel (Desktop Only) */}
      <div className="hidden md:block">
        <AlertsPanel alerts={alerts || []} isLoading={alertsLoading} />
      </div>

      {/* Modal */}
      <SignalDetailModal 
        signal={selectedSignal} 
        isOpen={!!selectedSignal} 
        onClose={() => setSelectedSignal(null)} 
      />
    </div>
  );
}
