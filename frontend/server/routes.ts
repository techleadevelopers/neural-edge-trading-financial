import type { Express } from "express";
import type { Server } from "http";
import { storage } from "./storage";
import { api } from "@shared/routes";
import { z } from "zod";
import { InsertSignal } from "@shared/schema";

// --- SIMULATED DATA COLLECTION & SIGNAL ENGINE ---
// In a real app, this would be in separate services. 
// For this MVP, we will simulate the "Worker" that runs every 60s.

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "LTCUSDT", "MATICUSDT", "AVAXUSDT"];

function generateMockSignal(symbol: string): InsertSignal {
  const regimes = ["BULL", "BEAR", "CHOP"];
  const regime = regimes[Math.floor(Math.random() * regimes.length)];
  
  const rsi = 30 + Math.random() * 40; // 30-70
  const vol_z = (Math.random() * 4) - 2; // -2 to 2
  
  // Determine Signal based on simple logic (Simulating "Strategies")
  let signalType = "NEUTRO";
  let reasons: string[] = [];
  let score = 50;

  // Strategy 1: RSI Extremes
  if (rsi > 65) {
    signalType = "SHORT_FRACO";
    reasons.push("RSI Alto");
    score += 10;
  } else if (rsi < 35) {
    signalType = "LONG_FRACO";
    reasons.push("RSI Baixo");
    score += 10;
  }

  // Strategy 2: Volume Spikes
  if (vol_z > 1.5) {
    score += 15;
    reasons.push("Volume Alto");
  }

  // Upgrade based on Score/Regime
  if (score > 75) {
    signalType = signalType.replace("FRACO", "FORTE");
  }

  const price = 100 + Math.random() * 1000;

  return {
    symbol,
    signal: signalType,
    score: Math.floor(score),
    probability: 0.4 + Math.random() * 0.4, // 40-80%
    regime,
    rsi: parseFloat(rsi.toFixed(2)),
    vol_z: parseFloat(vol_z.toFixed(2)),
    upper_wick: parseFloat(Math.random().toFixed(3)),
    ret_15: parseFloat(((Math.random() * 2) - 1).toFixed(2)),
    cooldown_min: Math.floor(Math.random() * 10),
    entry_price: parseFloat(price.toFixed(2)),
    stop_loss: parseFloat((price * 0.98).toFixed(2)),
    target_price: parseFloat((price * 1.05).toFixed(2)),
    reasons: reasons
  };
}

async function updateSignals() {
  console.log("Updating signals...");
  for (const symbol of SYMBOLS) {
    // Generate a signal
    const signalData = generateMockSignal(symbol);
    
    // Save to DB
    await storage.createSignal(signalData);
    
    // Check for alerts
    if (signalData.signal.includes("FORTE")) {
      await storage.createAlert({
        type: "NEW_SIGNAL",
        message: `Sinal FORTE detectado em ${symbol} (${signalData.signal})`
      });
    }
  }
}

// Start background loop
setInterval(updateSignals, 60 * 1000); 
// Run once immediately
setTimeout(updateSignals, 5000);


export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  app.get(api.signals.list.path, async (req, res) => {
    const minScore = req.query.minScore ? Number(req.query.minScore) : 0;
    const onlyStrong = req.query.onlyStrong === 'true';
    
    const signals = await storage.getSignals(minScore, onlyStrong);
    res.json(signals);
  });

  app.get(api.signals.latest.path, async (req, res) => {
    res.json({ lastUpdate: new Date().toISOString() });
  });

  app.get(api.signals.get.path, async (req, res) => {
    const signal = await storage.getSignal(Number(req.params.id));
    if (!signal) {
      return res.status(404).json({ message: 'Signal not found' });
    }
    res.json(signal);
  });

  app.get(api.alerts.list.path, async (req, res) => {
    const alerts = await storage.getAlerts();
    res.json(alerts);
  });
  
  // latest route moved up

  return httpServer;
}
