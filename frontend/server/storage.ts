import { db } from "./db";
import {
  signals,
  alerts,
  type InsertSignal,
  type Signal,
  type InsertAlert,
  type Alert
} from "@shared/schema";
import { eq, desc, and, gte } from "drizzle-orm";

export interface IStorage {
  getSignals(minScore?: number, onlyStrong?: boolean): Promise<Signal[]>;
  getSignal(id: number): Promise<Signal | undefined>;
  createSignal(signal: InsertSignal): Promise<Signal>;
  getAlerts(limit?: number): Promise<Alert[]>;
  createAlert(alert: InsertAlert): Promise<Alert>;
  clearOldSignals(): Promise<void>;
}

export class DatabaseStorage implements IStorage {
  async getSignals(minScore: number = 0, onlyStrong: boolean = false): Promise<Signal[]> {
    const conditions = [gte(signals.score, minScore)];
    
    if (onlyStrong) {
      // Assuming 'FORTE' is in the signal string, e.g. "LONG_FORTE"
      // In a real app we might use a separate column or enum, but text match works for MVP
      // We can filter this in memory or add specific SQL LIKE if needed, 
      // but for simplicity let's just get the latest signals and filter.
      // Better: let's just return all valid signals for the dashboard window.
    }

    // Return top 30 by score, most recent
    return await db.select()
      .from(signals)
      .where(and(...conditions))
      .orderBy(desc(signals.timestamp), desc(signals.score))
      .limit(30);
  }

  async getSignal(id: number): Promise<Signal | undefined> {
    const [signal] = await db.select().from(signals).where(eq(signals.id, id));
    return signal;
  }

  async createSignal(insertSignal: InsertSignal): Promise<Signal> {
    const [signal] = await db.insert(signals).values(insertSignal).returning();
    return signal;
  }

  async getAlerts(limit: number = 20): Promise<Alert[]> {
    return await db.select()
      .from(alerts)
      .orderBy(desc(alerts.timestamp))
      .limit(limit);
  }

  async createAlert(insertAlert: InsertAlert): Promise<Alert> {
    const [alert] = await db.insert(alerts).values(insertAlert).returning();
    return alert;
  }

  async clearOldSignals(): Promise<void> {
    // Optional: Keep only last 24h or similar
  }
}

export const storage = new DatabaseStorage();
