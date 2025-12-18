import { Signal } from "@shared/schema";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceLine
} from "recharts";
import { ArrowDown, ArrowUp, Target, ShieldAlert, Zap } from "lucide-react";

interface SignalDetailModalProps {
  signal: Signal | null;
  isOpen: boolean;
  onClose: () => void;
}

export function SignalDetailModal({ signal, isOpen, onClose }: SignalDetailModalProps) {
  if (!signal) return null;

  // Mock data for chart visualization
  const mockData = [
    { name: '1', price: signal.entry_price ? signal.entry_price * 0.98 : 100 },
    { name: '2', price: signal.entry_price ? signal.entry_price * 0.99 : 102 },
    { name: '3', price: signal.entry_price || 105 },
    { name: '4', price: signal.entry_price ? signal.entry_price * 1.01 : 108 },
    { name: '5', price: signal.entry_price ? signal.entry_price * 1.02 : 104 },
    { name: '6', price: signal.target_price || 110 },
  ];

  const isLong = signal.signal.includes("LONG");

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl bg-card border-border shadow-2xl">
        <DialogHeader>
          <div className="flex justify-between items-start pr-8">
            <div>
              <DialogTitle className="text-3xl font-display font-bold flex items-center gap-3">
                {signal.symbol}
                <Badge variant={isLong ? "default" : "destructive"} className="ml-2 font-mono text-xs uppercase tracking-wider">
                  {signal.signal.replace("_", " ")}
                </Badge>
              </DialogTitle>
              <p className="text-muted-foreground text-sm mt-1 font-mono">
                {format(new Date(signal.timestamp), "dd 'de' MMMM, HH:mm", { locale: ptBR })}
              </p>
            </div>
            <div className="text-right">
              <span className="block text-xs uppercase text-muted-foreground font-bold tracking-wider">Score</span>
              <span className="text-2xl font-mono font-bold text-primary">{signal.score}/100</span>
            </div>
          </div>
        </DialogHeader>

        <div className="grid grid-cols-3 gap-4 my-6">
          <div className="bg-background/50 p-4 rounded-xl border border-border/50 text-center">
            <div className="flex items-center justify-center gap-2 text-muted-foreground text-xs uppercase font-bold mb-2">
              <Zap className="w-4 h-4" /> Entrada
            </div>
            <span className="text-xl font-mono font-bold">{signal.entry_price?.toFixed(4) || "-"}</span>
          </div>
          <div className="bg-green-500/10 p-4 rounded-xl border border-green-500/20 text-center">
            <div className="flex items-center justify-center gap-2 text-green-500 text-xs uppercase font-bold mb-2">
              <Target className="w-4 h-4" /> Alvo
            </div>
            <span className="text-xl font-mono font-bold text-green-500">{signal.target_price?.toFixed(4) || "-"}</span>
          </div>
          <div className="bg-red-500/10 p-4 rounded-xl border border-red-500/20 text-center">
            <div className="flex items-center justify-center gap-2 text-red-500 text-xs uppercase font-bold mb-2">
              <ShieldAlert className="w-4 h-4" /> Stop
            </div>
            <span className="text-xl font-mono font-bold text-red-500">{signal.stop_loss?.toFixed(4) || "-"}</span>
          </div>
        </div>

        <div className="h-64 w-full bg-background/30 rounded-xl border border-border/50 p-4 mb-6">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={mockData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
              <XAxis dataKey="name" hide />
              <YAxis domain={['auto', 'auto']} hide />
              <Tooltip 
                contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', color: 'hsl(var(--foreground))' }}
                itemStyle={{ color: 'hsl(var(--primary))' }}
              />
              <ReferenceLine y={signal.entry_price || 0} stroke="hsl(var(--muted-foreground))" strokeDasharray="3 3" label="Entry" />
              <ReferenceLine y={signal.target_price || 0} stroke="hsl(var(--color-success))" label="Target" />
              <ReferenceLine y={signal.stop_loss || 0} stroke="hsl(var(--color-danger))" label="Stop" />
              <Line 
                type="monotone" 
                dataKey="price" 
                stroke={isLong ? "hsl(var(--color-success))" : "hsl(var(--color-danger))"} 
                strokeWidth={2} 
                dot={false} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="space-y-4">
          <h4 className="font-bold text-sm uppercase tracking-wider text-muted-foreground border-b border-border pb-2">
            Indicadores Técnicos
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground block text-xs">RSI (14)</span>
              <span className="font-mono font-bold">{signal.rsi?.toFixed(2) || "-"}</span>
            </div>
            <div>
              <span className="text-muted-foreground block text-xs">Vol Z-Score</span>
              <span className="font-mono font-bold">{signal.vol_z?.toFixed(2) || "-"}</span>
            </div>
            <div>
              <span className="text-muted-foreground block text-xs">Regime</span>
              <Badge variant="outline" className="font-mono text-xs">{signal.regime}</Badge>
            </div>
            <div>
              <span className="text-muted-foreground block text-xs">Cooldown</span>
              <span className="font-mono font-bold">{signal.cooldown_min}m</span>
            </div>
          </div>
          
          <div className="pt-2">
             <h4 className="font-bold text-sm uppercase tracking-wider text-muted-foreground mb-2">
              Motivos da Entrada
            </h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-foreground/80">
              {signal.reasons && Array.isArray(signal.reasons) ? (
                signal.reasons.map((reason, i) => (
                  <li key={i}>{reason}</li>
                ))
              ) : (
                <li className="text-muted-foreground italic">Nenhuma razão detalhada disponível</li>
              )}
            </ul>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
