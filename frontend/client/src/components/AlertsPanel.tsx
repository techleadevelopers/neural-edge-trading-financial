import { Alert } from "@shared/schema";
import { Bell, Info } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface AlertsPanelProps {
  alerts: Alert[];
  isLoading: boolean;
}

export function AlertsPanel({ alerts, isLoading }: AlertsPanelProps) {
  return (
    <div className="h-full flex flex-col bg-card border-l border-border/50 w-80 fixed right-0 top-0 bottom-0 z-20 shadow-2xl">
      <div className="p-6 border-b border-border/50 bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2 text-primary mb-1">
          <Bell className="w-5 h-5 fill-current" />
          <h2 className="font-display font-bold text-lg tracking-tight">Alertas Recentes</h2>
        </div>
        <p className="text-xs text-muted-foreground">Monitoramento em tempo real</p>
      </div>

      <ScrollArea className="flex-1 p-4">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse flex gap-3">
                <div className="w-2 h-2 mt-2 rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-muted rounded w-3/4" />
                  <div className="h-3 bg-muted rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="text-center py-10 text-muted-foreground">
            <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Nenhum alerta recente</p>
          </div>
        ) : (
          <div className="space-y-6">
            {alerts.map((alert) => (
              <div key={alert.id} className="relative pl-4 group">
                <div className={cn(
                  "absolute left-0 top-1.5 w-2 h-2 rounded-full ring-4 ring-background",
                  alert.type === "NEW_SIGNAL" ? "bg-primary" : "bg-yellow-500"
                )} />
                <div className="border-l-2 border-border absolute left-[3px] top-4 bottom-[-24px] group-last:hidden" />
                
                <p className="text-sm font-medium text-foreground leading-relaxed">
                  {alert.message}
                </p>
                <span className="text-xs text-muted-foreground font-mono mt-1 block">
                  {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true, locale: ptBR })}
                </span>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
