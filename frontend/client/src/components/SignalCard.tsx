import { Signal } from "@shared/schema";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { TrendingUp, TrendingDown, Minus, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface SignalCardProps {
  signal: Signal;
  onClick?: () => void;
}

export function SignalCard({ signal, onClick }: SignalCardProps) {
  const isLong = signal.signal === "LONG_FORTE";
  const isShort = signal.signal === "SHORT_FRACO"; // Assuming types
  const isNeutral = signal.signal === "NEUTRO";

  return (
    <div 
      onClick={onClick}
      className="group relative overflow-hidden bg-card hover:bg-card/80 border border-border/50 rounded-xl p-4 transition-all duration-200 cursor-pointer hover:shadow-lg hover:border-primary/20"
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg",
            isLong ? "bg-green-500/20 text-green-500" : 
            isShort ? "bg-red-500/20 text-red-500" : 
            "bg-gray-500/20 text-gray-400"
          )}>
            {signal.symbol.substring(0, 1)}
          </div>
          <div>
            <h3 className="font-display font-bold text-lg leading-none">{signal.symbol}</h3>
            <span className="text-xs text-muted-foreground font-mono">
              {formatDistanceToNow(new Date(signal.timestamp), { addSuffix: true, locale: ptBR })}
            </span>
          </div>
        </div>
        
        <div className={cn(
          "px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1",
          isLong ? "bg-green-500/10 text-green-500 border border-green-500/20" : 
          isShort ? "bg-red-500/10 text-red-500 border border-red-500/20" : 
          "bg-gray-500/10 text-gray-400 border border-gray-500/20"
        )}>
          {isLong && <TrendingUp className="w-3 h-3" />}
          {isShort && <TrendingDown className="w-3 h-3" />}
          {isNeutral && <Minus className="w-3 h-3" />}
          {signal.signal.replace('_', ' ')}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <span className="text-[10px] uppercase text-muted-foreground font-semibold tracking-wider">Score</span>
          <div className="flex items-center gap-2 mt-1">
            <div className="h-2 flex-1 bg-secondary rounded-full overflow-hidden">
              <div 
                className={cn("h-full rounded-full", 
                  signal.score > 70 ? "bg-green-500" : 
                  signal.score < 30 ? "bg-red-500" : "bg-yellow-500"
                )} 
                style={{ width: `${signal.score}%` }} 
              />
            </div>
            <span className="font-mono text-sm font-bold">{signal.score}</span>
          </div>
        </div>
        <div>
          <span className="text-[10px] uppercase text-muted-foreground font-semibold tracking-wider">Probabilidade</span>
          <div className="mt-1 font-mono text-sm font-bold text-foreground">
            {(signal.probability * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs font-mono bg-background/50 rounded-lg p-2 border border-border/50">
        <div className="text-center">
          <span className="block text-muted-foreground text-[10px] mb-0.5">Entrada</span>
          <span className="font-semibold text-foreground">{signal.entry_price?.toFixed(4) || '-'}</span>
        </div>
        <ArrowRight className="w-3 h-3 text-muted-foreground" />
        <div className="text-center">
          <span className="block text-muted-foreground text-[10px] mb-0.5">Alvo</span>
          <span className="font-semibold text-green-500">{signal.target_price?.toFixed(4) || '-'}</span>
        </div>
        <div className="w-px h-6 bg-border mx-1" />
        <div className="text-center">
          <span className="block text-muted-foreground text-[10px] mb-0.5">Stop</span>
          <span className="font-semibold text-red-500">{signal.stop_loss?.toFixed(4) || '-'}</span>
        </div>
      </div>
    </div>
  );
}
